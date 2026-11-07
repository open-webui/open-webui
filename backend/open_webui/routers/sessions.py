"""Persistent sessions for native clients, using existing human authentication."""

import base64
import hashlib
import hmac
import time
from datetime import timedelta
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from open_webui.models.auth_sessions import AuthSession, AuthSessions
from open_webui.models.config import Config
from open_webui.models.users import Users
from open_webui.routers.mfa import MfaRoute
from open_webui.utils.auth import (
    ALGORITHM,
    SESSION_SECRET,
    create_token,
    decode_token,
    get_human_user,
    is_valid_token,
)
from open_webui.utils.misc import parse_duration
from open_webui.utils.rate_limit import RateLimiter
from pydantic import BaseModel, ConfigDict, Field, field_validator

router = APIRouter(route_class=MfaRoute)
limiter = RateLimiter(limit=30, window=60)
PROOF_KEYS = ('auth_time', 'auth_method', 'session_stamp', 'mfa_verified')


class SessionForm(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)


class AuthorizationRequest(SessionForm):
    redirect_uri: str = Field(max_length=2048)
    state: str = Field(min_length=32, max_length=256, pattern=r'^[A-Za-z0-9_-]+$')
    code_challenge: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]+$')

    @field_validator('redirect_uri')
    @classmethod
    def loopback(cls, value):
        parsed = urlsplit(value)
        try:
            port = parsed.port
        except ValueError:
            raise ValueError('Invalid callback port') from None
        if (
            parsed.scheme != 'http'
            or parsed.hostname != '127.0.0.1'
            or not port
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError('A loopback callback is required')
        return value


class ExchangeForm(BaseModel):
    session_id: UUID
    code: str = Field(max_length=8192)
    code_verifier: str = Field(min_length=43, max_length=128, pattern=r'^[A-Za-z0-9._~-]+$')
    redirect_uri: str = Field(max_length=2048)


class RefreshForm(BaseModel):
    refresh_token: str = Field(max_length=8192)
    request_id: UUID | None = None


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()


async def throttle(request):
    ip = request.client.host if request.client else 'unknown'
    if await limiter.is_limited(getattr(request.app.state, 'redis', None), 'sessions:' + digest(ip)):
        raise HTTPException(429, 'Too many login attempts. Try again shortly.')


async def idle_expiry():
    duration = parse_duration(await Config.get('auth.session_expiry'))
    if duration is None or duration.total_seconds() < 1:
        raise ValueError('SESSION_EXPIRES_IN must be at least 1 second')
    return int(time.time()) + int(duration.total_seconds())


async def verify_proof(claims, request):
    # Codes and refresh tokens are never passed to ordinary API authentication.
    proof = {key: claims.get(key) for key in PROOF_KEYS}
    user_id = claims.get('id')
    if not user_id or not isinstance(proof['auth_time'], int) or not proof['auth_method']:
        raise HTTPException(401, 'Sign in again.')
    if not await is_valid_token(
        {'id': user_id, 'typ': 'session', 'iat': claims.get('iat'), **proof}, getattr(request.app.state, 'redis', None)
    ):
        raise HTTPException(401, 'Sign in again.')
    user = await Users.get_user_by_id(user_id)
    if not user or user.role not in ('user', 'admin'):
        raise HTTPException(403, 'Account approval is required.')
    return proof


def credentials(row, proof, refresh_issued_at=None):
    now = int(time.time())
    access_expiry = min(now + 900, row.expires_at)
    access = create_token(
        {'id': row.user_id, 'sid': row.id, 'typ': 'session', **proof},
        timedelta(seconds=access_expiry - now),
    )
    refresh = jwt.encode(
        {
            'id': row.user_id,
            'sid': row.id,
            'typ': 'refresh',
            **proof,
            'jti': row.refresh_token_id,
            'iat': now if refresh_issued_at is None else refresh_issued_at,
            'exp': row.expires_at,
        },
        SESSION_SECRET,
        algorithm=ALGORITHM,
    )
    return {
        'session_id': row.id,
        'token': access,
        'token_type': 'Bearer',
        'expires_at': access_expiry,
        'refresh_token': refresh,
        'refresh_expires_at': row.expires_at,
    }


@router.post('')
async def create_session(form: SessionForm, request: Request, user=Depends(get_human_user)):
    await throttle(request)
    proof = await verify_proof(request.state.claims, request)
    row = await AuthSessions.create(
        user_id=user.id,
        data={'name': form.name},
        expires_at=await idle_expiry(),
        refresh_token_id=str(uuid4()),
    )
    return credentials(row, proof)


@router.post('/requests')
async def authorization_request(form: AuthorizationRequest, request: Request):
    await throttle(request)
    row = await AuthSessions.create(
        data={
            'name': form.name,
            'authorization': {
                'redirect_uri': form.redirect_uri,
                'state': form.state,
                'code_challenge': form.code_challenge,
            },
        },
        expires_at=int(time.time()) + 600,
    )
    return {'session_id': row.id}


@router.post('/exchange')
async def exchange(form: ExchangeForm, request: Request):
    await throttle(request)
    claims = decode_token(form.code)
    row = await AuthSessions.get(str(form.session_id))
    authorization = row.data.get('authorization', {}) if row else {}
    if (
        not claims
        or claims.get('typ') != 'session_code'
        or claims.get('sid') != str(form.session_id)
        or not row
        or row.refresh_token_id is not None
        or row.expires_at <= time.time()
        or claims.get('id') != row.user_id
        or not authorization.get('code_hash')
        or not hmac.compare_digest(authorization['code_hash'], digest(form.code))
        or authorization.get('redirect_uri') != form.redirect_uri
        or not hmac.compare_digest(authorization.get('code_challenge', ''), challenge(form.code_verifier))
    ):
        raise HTTPException(401, 'Invalid or expired login code.')
    proof = await verify_proof(claims, request)
    values = dict(
        refresh_token_id=str(uuid4()),
        expires_at=await idle_expiry(),
        data={key: value for key, value in row.data.items() if key != 'authorization'},
    )
    if not await AuthSessions.change(
        row.id,
        [
            AuthSession.refresh_token_id.is_(None),
            AuthSession.user_id == row.user_id,
            AuthSession.data['authorization']['code_hash'].as_string() == authorization['code_hash'],
            AuthSession.expires_at > int(time.time()),
        ],
        **values,
    ):
        raise HTTPException(401, 'Login code has already been consumed.')
    return credentials(row.model_copy(update=values), proof)


@router.post('/refresh')
async def refresh(form: RefreshForm, request: Request):
    await throttle(request)
    claims = decode_token(form.refresh_token)
    if not claims or claims.get('typ') != 'refresh' or not claims.get('jti') or not claims.get('sid'):
        raise HTTPException(401, 'Invalid refresh token.')
    proof = await verify_proof(claims, request)
    session_id, token_id = claims['sid'], claims['jti']
    row = await AuthSessions.get(session_id)
    if not row or row.user_id != claims.get('id') or row.expires_at <= time.time():
        raise HTTPException(401, 'Session expired or revoked.')
    if row.refresh_token_id == token_id:
        issued_at = int(time.time())
        data = {key: value for key, value in row.data.items() if key != 'refresh_retry'}
        if form.request_id:
            data['refresh_retry'] = {
                'token_hash': digest(form.refresh_token),
                'request_hash': digest(str(form.request_id)),
                'issued_at': issued_at,
            }
        values = dict(refresh_token_id=str(uuid4()), expires_at=await idle_expiry(), data=data)
        if await AuthSessions.change(
            row.id,
            [
                AuthSession.user_id == claims['id'],
                AuthSession.refresh_token_id == token_id,
                AuthSession.expires_at > int(time.time()),
            ],
            **values,
        ):
            return credentials(row.model_copy(update=values), proof, issued_at)
        # Another worker may have completed the same request while we were rotating.
        row = await AuthSessions.get(session_id)

    retry = row.data.get('refresh_retry', {}) if row else {}
    if (
        row
        and row.user_id == claims['id']
        and row.refresh_token_id is not None
        and row.expires_at > time.time()
        and form.request_id
        and hmac.compare_digest(retry.get('token_hash', ''), digest(form.refresh_token))
        and hmac.compare_digest(retry.get('request_hash', ''), digest(str(form.request_id)))
    ):
        # Only the last rotation is recoverable; token verification still enforces its original expiry.
        return credentials(row, proof, retry['issued_at'])
    raise HTTPException(401, 'Invalid refresh token. Sign in again.')


@router.get('')
async def list_sessions(user=Depends(get_human_user)):
    return await AuthSessions.list(user.id)


@router.get('/{session_id}/request')
async def request_info(session_id: UUID, user=Depends(get_human_user)):
    row = await AuthSessions.get(str(session_id))
    if not row or row.refresh_token_id is not None or row.expires_at <= time.time():
        raise HTTPException(404, 'Login request expired.')
    return {'name': row.data['name'], 'expires_at': row.expires_at}


@router.post('/{session_id}/authorize')
async def authorize(session_id: UUID, request: Request, user=Depends(get_human_user)):
    await throttle(request)
    proof = await verify_proof(request.state.claims, request)
    row = await AuthSessions.get(str(session_id))
    authorization = row.data.get('authorization', {}) if row else {}
    if (
        not row
        or row.refresh_token_id is not None
        or row.user_id is not None
        or row.expires_at <= time.time()
        or not authorization
        or authorization.get('code_hash')
    ):
        raise HTTPException(409, 'Login request expired or already authorized.')
    code = create_token({'typ': 'session_code', 'id': user.id, 'sid': row.id, **proof}, timedelta(seconds=60))
    if not await AuthSessions.change(
        row.id,
        [
            AuthSession.refresh_token_id.is_(None),
            AuthSession.user_id.is_(None),
            AuthSession.data['authorization']['code_hash'].as_string().is_(None),
            AuthSession.expires_at > int(time.time()),
        ],
        user_id=user.id,
        data={**row.data, 'authorization': {**authorization, 'code_hash': digest(code)}},
    ):
        raise HTTPException(409, 'Login request changed.')
    callback = urlsplit(authorization['redirect_uri'])
    return {
        'redirect_uri': urlunsplit(callback._replace(query=urlencode({'code': code, 'state': authorization['state']})))
    }


@router.delete('/{session_id}')
async def revoke(session_id: UUID, user=Depends(get_human_user)):
    if not await AuthSessions.revoke(str(session_id), user.id):
        raise HTTPException(404, 'Session not found.')
    return {'status': True}
