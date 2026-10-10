"""MFA endpoints; challenges never authorize ordinary application requests."""

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from open_webui.env import WEBUI_AUTH_COOKIE_SAME_SITE, WEBUI_AUTH_COOKIE_SECURE
from open_webui.models.auths import (
    MfaChallengeForm,
    MfaChallengeResponse,
    MfaEnrollmentResponse,
    MfaFactorForm,
    MfaRecoveryCodesResponse,
    MfaRecoveryForm,
    MfaSetupResponse,
    MfaStatusResponse,
    MfaVerifyForm,
    SessionUserResponse,
)
from open_webui.models.config import Config
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.utils import mfa
from open_webui.utils.auth import create_session_response, get_human_user
from open_webui.utils.misc import parse_duration
from open_webui.utils.rate_limit import RateLimiter
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

ip_limiter = RateLimiter(limit=100, window=900)
CHALLENGE_COOKIE = 'mfa_challenge'


class MfaRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def protected(request: Request):
            try:
                if request.method == 'POST' and (await mfa.get_mfa_config()).ENABLE_MFA:
                    ip = request.client.host if request.client else 'unknown'
                    if await ip_limiter.is_limited(
                        getattr(request.app.state, 'redis', None), 'mfa:ip:' + mfa.token_hash(ip)
                    ):
                        raise HTTPException(
                            429, 'Too many attempts. Please try again later.', headers={'Retry-After': '900'}
                        )
                response = await handler(request)
            except RequestValidationError:
                response = JSONResponse({'detail': 'Invalid authentication request.'}, status_code=422)
            except HTTPException as error:
                response = JSONResponse({'detail': error.detail}, status_code=error.status_code, headers=error.headers)
            except (SQLAlchemyError, ValidationError):
                response = JSONResponse({'detail': 'Authentication is temporarily unavailable.'}, status_code=503)
            response.headers['Cache-Control'] = 'no-store'
            return response

        return protected


router = APIRouter(route_class=MfaRoute)


def clear_challenge_cookie(response: Response):
    response.delete_cookie(CHALLENGE_COOKIE, path='/api/v1/auths/mfa')


async def finish_login(request, response, user, auth, challenge):
    result = await create_session_response(
        request,
        user,
        response=response,
        set_cookie=True,
        source=challenge.auth_method,
        auth=auth,
        mfa_verified=True,
        auth_time=challenge.auth_time,
    )
    if challenge.oauth_session_id:
        session = await OAuthSessions.get_session_by_id(challenge.oauth_session_id)
        if session and session.user_id == user.id:
            expires_delta = parse_duration(await Config.get('auth.jwt_expiry'))
            response.set_cookie(
                'oauth_session_id',
                session.id,
                httponly=True,
                secure=WEBUI_AUTH_COOKIE_SECURE,
                samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                max_age=int(expires_delta.total_seconds()) if expires_delta else None,
            )
    clear_challenge_cookie(response)
    return result


@router.get('/status', response_model=MfaStatusResponse)
async def get_mfa_status(request: Request, user=Depends(get_human_user)):
    auth = await mfa.get_auth(user.id)
    state = auth.mfa
    return {
        'enabled': bool(state and state.secret),
        'required': mfa.is_mfa_required(request.state.claims.get('auth_method', ''), await mfa.get_mfa_config()),
        'recovery_codes_remaining': len(state.recovery_hashes) if state else 0,
    }


@router.post('/challenge', response_model=MfaChallengeResponse)
async def get_mfa_challenge(request: Request, response: Response):
    # Cookie-only bootstrap is browser-only and must not be driven cross-origin.
    origin = request.headers.get('origin')
    configured = await Config.get('webui.url')
    expected = urlsplit(configured or str(request.base_url))
    if origin != f'{expected.scheme}://{expected.netloc}':
        raise HTTPException(403, 'Invalid request origin.')
    token = request.cookies.get(CHALLENGE_COOKIE, '')
    try:
        _, _, _, challenge, _ = await mfa.load_challenge(token, {'enroll', 'verify', 'recover'})
    except HTTPException:
        clear_challenge_cookie(response)
        return JSONResponse(
            {'detail': 'This authentication step expired. Please start again.'},
            status_code=401,
            headers={'Set-Cookie': response.headers.get('set-cookie', '')},
        )
    clear_challenge_cookie(response)
    return mfa.challenge_response(token, challenge)


@router.post('/enroll/start', response_model=MfaSetupResponse)
async def start_mfa_enrollment(form_data: MfaChallengeForm):
    return await mfa.start_mfa_enrollment(form_data.challenge_token.get_secret_value())


@router.post('/enroll/confirm', response_model=MfaEnrollmentResponse | MfaRecoveryCodesResponse)
async def confirm_mfa_enrollment(request: Request, response: Response, form_data: MfaVerifyForm):
    user, auth, challenge, codes = await mfa.confirm_mfa_enrollment(
        form_data.challenge_token.get_secret_value(), form_data.code.get_secret_value(), request=request
    )
    from open_webui.socket.main import disconnect_user_sessions

    await disconnect_user_sessions(user.id)
    if challenge.type == 'replace':
        return {'recovery_codes': codes}
    return {**(await finish_login(request, response, user, auth, challenge)), 'recovery_codes': codes}


@router.post('/verify', response_model=SessionUserResponse)
async def verify_mfa_challenge(request: Request, response: Response, form_data: MfaVerifyForm):
    user, auth, challenge = await mfa.verify_mfa_challenge(
        form_data.challenge_token.get_secret_value(),
        form_data.code.get_secret_value(),
        form_data.recovery,
        request=request,
    )
    return await finish_login(request, response, user, auth, challenge)


@router.post('/replace', response_model=MfaChallengeResponse)
async def start_mfa_replacement(request: Request, form_data: MfaFactorForm, user=Depends(get_human_user)):
    return await mfa.manage_mfa(
        user.id,
        request.state.claims,
        form_data.code.get_secret_value(),
        form_data.recovery,
        replace=True,
        request=request,
    )


@router.post('/recovery/codes', response_model=MfaRecoveryCodesResponse)
async def regenerate_mfa_recovery_codes(request: Request, form_data: MfaFactorForm, user=Depends(get_human_user)):
    result = await mfa.manage_mfa(
        user.id,
        request.state.claims,
        form_data.code.get_secret_value(),
        form_data.recovery,
        replace=False,
        request=request,
    )
    from open_webui.socket.main import disconnect_user_sessions

    await disconnect_user_sessions(user.id)
    return result


@router.post('/recover', response_model=MfaChallengeResponse)
async def redeem_mfa_reset_token(form_data: MfaRecoveryForm):
    return await mfa.redeem_mfa_reset_token(
        form_data.challenge_token.get_secret_value(), form_data.reset_token.get_secret_value()
    )
