from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import uuid
from datetime import datetime, timedelta
from threading import Lock
from time import monotonic
from typing import Union

import bcrypt
import jwt
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    ENABLE_OTEL,
    ENABLE_PASSWORD_VALIDATION,
    LICENSE_BLOB,
    PASSWORD_HASH_ALGORITHM,
    PASSWORD_VALIDATION_HINT,
    PASSWORD_VALIDATION_REGEX_PATTERN,
    REDIS_KEY_PREFIX,
    STATIC_DIR,
    TRUSTED_SIGNATURE_KEY,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_SECRET_KEY,
    pk,
)
from open_webui.models.auths import Auths
from open_webui.models.config import Config
from open_webui.models.users import Users
from open_webui.utils.access_control import has_permission
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.misc import parse_duration
from pytz import UTC
from redis.exceptions import RedisError

log = logging.getLogger(__name__)

SESSION_SECRET = WEBUI_SECRET_KEY
ALGORITHM = 'HS256'
PASSWORD_BCRYPT_MAX_BYTES = 72

##############
# Auth Utils
##############


def verify_signature(payload: str, signature: str) -> bool:
    """
    Verifies the HMAC signature of the received payload.
    """
    try:
        expected_signature = base64.b64encode(
            hmac.new(TRUSTED_SIGNATURE_KEY, payload.encode(), hashlib.sha256).digest()
        ).decode()

        # Compare securely to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)

    except Exception:
        return False


def override_static(path: str, content: str):
    # Ensure path is safe
    if '/' in path or '..' in path:
        log.error(f'Invalid path: {path}')
        return

    file_path = os.path.join(STATIC_DIR, path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'wb') as f:
        f.write(base64.b64decode(content))  # Convert Base64 back to raw binary


def get_license_data(app, key):
    def data_handler(data):
        for k, v in data.items():
            if k == 'resources':
                # LICENSE covers these Open WebUI branding assets.
                # Do not alter, remove, obscure, or replace them except as LICENSE permits:
                # https://docs.openwebui.com/license.
                for p, c in v.items():
                    globals().get('override_static', lambda a, b: None)(p, c)
            elif k == 'count':
                setattr(app.state, 'USER_COUNT', v)
            elif k == 'name':
                # LICENSE covers this Open WebUI product name.
                # Do not alter, remove, obscure, or replace it except as LICENSE permits:
                # https://docs.openwebui.com/license.
                setattr(app.state, 'WEBUI_NAME', v)
            elif k == 'metadata':
                setattr(app.state, 'LICENSE_METADATA', v)

    def handler(u):
        try:
            res = requests.post(
                f'{u}/api/v1/license/',
                json={'key': key, 'version': '1'},
                timeout=5,
            )
        except Exception as ex:
            log.error(f'License: retrieval issue from {u}: {ex}')
            return False

        if getattr(res, 'ok', False):
            payload = getattr(res, 'json', lambda: {})()
            data_handler(payload)
            return True
        else:
            log.error(f'License: retrieval issue: {getattr(res, "text", "unknown error")}')

    if key:
        us = [
            'https://api.openwebui.com',
            'https://licenses.api.openwebui.com',
        ]
        try:
            for u in us:
                if handler(u):
                    return True
        except Exception as ex:
            log.exception(f'License: Uncaught Exception: {ex}')

    try:
        if LICENSE_BLOB:
            nl = 12
            kb = hashlib.sha256((key.replace('-', '').upper()).encode()).digest()

            def nt(b):
                return b[:nl], b[nl:]

            lb = base64.b64decode(LICENSE_BLOB)
            ln, lt = nt(lb)

            aesgcm = AESGCM(kb)
            p = JSONCodec.loads(aesgcm.decrypt(ln, lt, None))
            pk.verify(base64.b64decode(p['s']), p['p'].encode())

            pb = base64.b64decode(p['p'])
            pn, pt = nt(pb)

            data = JSONCodec.loads(aesgcm.decrypt(pn, pt, None).decode())

            exp = data.get('exp')
            if exp:
                if isinstance(exp, str):
                    from datetime import date

                    exp = date.fromisoformat(exp)
                if exp < datetime.now().date():
                    return False

            data_handler(data)
            return True
    except Exception as e:
        log.error(f'License: {e}')

    return False


bearer_security = HTTPBearer(auto_error=False)


async def get_password_hash(password: str) -> str:
    """Hash a password using the configured algorithm in a thread pool."""
    if PASSWORD_HASH_ALGORITHM == 'argon2':
        from argon2 import PasswordHasher

        return await asyncio.to_thread(PasswordHasher().hash, password)
    if PASSWORD_HASH_ALGORITHM == 'bcrypt':
        return (await asyncio.to_thread(bcrypt.hashpw, password.encode('utf-8'), bcrypt.gensalt())).decode('utf-8')

    raise ValueError(f'Unsupported PASSWORD_HASH_ALGORITHM: {PASSWORD_HASH_ALGORITHM}')


def validate_password(password: str) -> bool:
    # bcrypt only accepts 72 bytes; reject long new passwords instead of storing an unusable hash.
    if PASSWORD_HASH_ALGORITHM == 'bcrypt' and len(password.encode('utf-8')) > PASSWORD_BCRYPT_MAX_BYTES:
        raise Exception(
            ERROR_MESSAGES.PASSWORD_TOO_LONG,
        )

    if ENABLE_PASSWORD_VALIDATION:
        if not PASSWORD_VALIDATION_REGEX_PATTERN.match(password):
            raise Exception(ERROR_MESSAGES.INVALID_PASSWORD(PASSWORD_VALIDATION_HINT))

    return True


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password using the algorithm encoded in its hash."""
    if not hashed_password:
        return False

    if hashed_password.startswith('$argon2'):
        from argon2 import PasswordHasher
        from argon2.exceptions import InvalidHashError, VerificationError

        try:
            return await asyncio.to_thread(PasswordHasher().verify, hashed_password, plain_password)
        except (InvalidHashError, VerificationError):
            return False

    password_bytes = plain_password.encode('utf-8')[:PASSWORD_BCRYPT_MAX_BYTES]
    try:
        return await asyncio.to_thread(
            bcrypt.checkpw,
            password_bytes,
            hashed_password.encode('utf-8'),
        )
    except ValueError:
        return False


# Let the one who signed this token be remembered at every gate,
# and may the claims therein honor the creator long after
# the session has closed.
def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    payload = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        payload.update({'exp': expire})

    jti = str(uuid.uuid4())
    payload.update({'jti': jti, 'iat': datetime.now(UTC)})

    encoded_jwt = jwt.encode(payload, SESSION_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    try:
        decoded = jwt.decode(token, SESSION_SECRET, algorithms=[ALGORITHM])
        return decoded
    except Exception:
        return None


class RateLimitFilter(logging.Filter):
    """Limit a logger to one record per interval per process."""

    def __init__(self, interval=60):
        super().__init__()
        self.interval = interval
        self.next_allowed = float('-inf')
        self.lock = Lock()

    def filter(self, record):
        with self.lock:
            now = monotonic()
            if now < self.next_allowed:
                return False
            self.next_allowed = now + self.interval
        return True


revocation_log = logging.getLogger(f'{__name__}.revocation')
revocation_log.addFilter(RateLimitFilter())


async def is_valid_token(decoded, redis=None) -> bool:
    """Check persistent account revocation, then optional Redis per-token revocation.

    Database failures fail closed. Redis failures retain the existing availability policy.
    """
    from open_webui.utils.mfa import get_auth, get_mfa_config, is_mfa_required

    auth = await get_auth(decoded.get('id', ''))
    if decoded.get('session_stamp') != auth.session_stamp:
        return False
    token_type = decoded.get('typ', 'session')
    if token_type not in {'session', 'automation', 'subagent'}:
        return False
    if token_type == 'session':
        config = await get_mfa_config()
        if is_mfa_required(decoded.get('auth_method', ''), config):
            if (
                decoded.get('mfa_verified') is not True
                or not auth.mfa
                or not auth.mfa.secret
                or auth.mfa.reset_required
            ):
                return False
    if not redis:
        return True

    try:
        # Per-token revocation
        jti = decoded.get('jti')
        if jti:
            revoked = await redis.get(f'{REDIS_KEY_PREFIX}:auth:token:{jti}:revoked')
            if revoked:
                return False

        # Per-user revocation (password change, OIDC back-channel logout)
        user_id = decoded.get('id')
        if user_id:
            revoked_at = await redis.get(f'{REDIS_KEY_PREFIX}:auth:user:{user_id}:revoked_at')
            if revoked_at:
                try:
                    revoked_at_ts = int(revoked_at)
                    token_iat = decoded.get('iat')
                    # No iat means legacy token — reject since we can't verify issue time
                    if token_iat is None or token_iat <= revoked_at_ts:
                        return False
                except (ValueError, TypeError):
                    pass
    except RedisError as e:
        revocation_log.warning('Revocation check failed; accepting token: %s', e)

    return True


async def invalidate_token(request, token):
    decoded = decode_token(token)

    # If token is invalid/expired, nothing to revoke
    if not decoded:
        return

    # Require Redis to store revoked tokens
    if request.app.state.redis:
        jti = decoded.get('jti')
        exp = decoded.get('exp')

        if jti and exp:
            ttl = exp - int(datetime.now(UTC).timestamp())  # Calculate time-to-live for the token

            if ttl > 0:
                # Revoked tokens must not be able to disconnect newer sessions.
                if not await is_valid_token(decoded, request.app.state.redis):
                    return

                # Store the revoked token in Redis with an expiration time
                await request.app.state.redis.set(
                    f'{REDIS_KEY_PREFIX}:auth:token:{jti}:revoked',
                    '1',
                    ex=ttl,
                )

                user_id = decoded.get('id')
                if user_id:
                    from open_webui.socket.main import disconnect_user_sessions

                    await disconnect_user_sessions(user_id)


async def revoke_user_tokens(request, user_id: str):
    """Persist account-wide revocation, whether or not Redis is configured."""
    from open_webui.internal.db import get_async_db
    from open_webui.socket.main import disconnect_user_sessions

    async with get_async_db() as db:
        await Auths.revoke_sessions_by_user_id(user_id, db=db)
        await db.commit()
    await disconnect_user_sessions(user_id)


def extract_token_from_auth_header(auth_header: str):
    return auth_header[len('Bearer ') :]


def create_api_key():
    key = str(uuid.uuid4()).replace('-', '')
    return f'sk-{key}'


def get_http_authorization_cred(auth_header: str | None):
    if not auth_header:
        return None
    try:
        scheme, credentials = auth_header.split(' ')
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    except Exception:
        return None


async def get_current_user(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    auth_token: HTTPAuthorizationCredentials = Depends(bearer_security),
    # NOTE: We intentionally do NOT use Depends(get_session) here.
    # Sessions are managed internally with short-lived context managers.
    # This ensures connections are released immediately after auth queries,
    # not held for the entire request duration (e.g., during 30+ second LLM calls).
):
    token = None

    if auth_token is not None:
        token = auth_token.credentials

    if token is None and 'token' in request.cookies:
        token = request.cookies.get('token')

    # Fallback to request.state.token (set by middleware, e.g. for x-api-key)
    if token is None and hasattr(request.state, 'token') and request.state.token:
        token = request.state.token.credentials

    if token is None:
        raise HTTPException(status_code=401, detail='Not authenticated')

    # auth by api key
    if token.startswith('sk-'):
        user = await get_current_user_by_api_key(request, token)

        # Add user info to current span
        if ENABLE_OTEL:
            from opentelemetry import trace

            current_span = trace.get_current_span()
            if current_span:
                current_span.set_attribute('client.user.id', user.id)
                current_span.set_attribute('client.user.email', user.email)
                current_span.set_attribute('client.user.role', user.role)
                current_span.set_attribute('client.auth.type', 'api_key')

        # Scope-backed, so outer middleware (audit) can reuse the resolved user
        request.state.user = user
        request.state.auth_type = 'api_key'
        return user

    # auth by jwt token
    try:
        try:
            data = decode_token(token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token',
            )

        if data is not None and 'id' in data:
            if not await is_valid_token(data, getattr(request.app.state, 'redis', None)):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid token',
                )

            user = await Users.get_user_by_id(data['id'])
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ERROR_MESSAGES.INVALID_TOKEN,
                )
            else:
                if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
                    trusted_email = request.headers.get(WEBUI_AUTH_TRUSTED_EMAIL_HEADER, '').lower()
                    if trusted_email and user.email != trusted_email:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='User mismatch. Please sign in again.',
                        )

                # Add user info to current span
                if ENABLE_OTEL:
                    from opentelemetry import trace

                    current_span = trace.get_current_span()
                    if current_span:
                        current_span.set_attribute('client.user.id', user.id)
                        current_span.set_attribute('client.user.email', user.email)
                        current_span.set_attribute('client.user.role', user.role)
                        current_span.set_attribute('client.auth.type', 'jwt')

                # Refresh the user's last active timestamp
                # Fire-and-forget via asyncio.create_task to avoid blocking
                asyncio.create_task(Users.update_last_active_by_id(user.id))

            # Scope-backed, so outer middleware (audit) can reuse the resolved user
            request.state.user = user
            request.state.auth_type = 'jwt'
            request.state.claims = data
            return user
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )
    except Exception as e:
        # Delete the token cookie
        if request.cookies.get('token'):
            response.delete_cookie('token')

        if request.cookies.get('oauth_id_token'):
            response.delete_cookie('oauth_id_token')

        # Delete OAuth session if present
        if request.cookies.get('oauth_session_id'):
            response.delete_cookie('oauth_session_id')

        raise e


async def get_current_user_by_api_key(request, api_key: str):
    # Each function call manages its own short-lived session internally
    user = await Users.get_user_by_api_key(api_key)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )

    config_values = await Config.get_many(
        'auth.enable_api_keys',
        'user.permissions',
        'auth.api_key.endpoint_restrictions',
        'auth.api_key.allowed_endpoints',
    )

    if not config_values.get('auth.enable_api_keys'):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED)

    if user.role != 'admin':
        user_permissions = config_values.get('user.permissions')
        if not await has_permission(
            user.id,
            'features.api_keys',
            user_permissions,
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED)

    # Enforce endpoint restrictions — checked here (not in middleware)
    # so it applies regardless of how the API key was transported
    # (Authorization header, cookie, x-api-key header, etc.).
    if config_values.get('auth.api_key.endpoint_restrictions'):
        allowed_endpoints = config_values.get('auth.api_key.allowed_endpoints', '')
        allowed_paths = [path.strip() for path in str(allowed_endpoints).split(',') if path.strip()]
        request_path = request.scope['path']  # Use raw ASGI path — not spoofable via Host header (CVE-2026-48710)
        is_allowed = any(request_path == allowed or request_path.startswith(allowed + '/') for allowed in allowed_paths)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

    # Add user info to current span
    if ENABLE_OTEL:
        from opentelemetry import trace

        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute('client.user.id', user.id)
            current_span.set_attribute('client.user.email', user.email)
            current_span.set_attribute('client.user.role', user.role)
            current_span.set_attribute('client.auth.type', 'api_key')

    await Users.update_last_active_by_id(user.id)
    return user


VERIFIED_USER_ROLES = {'user', 'admin'}


def get_verified_user(user=Depends(get_current_user)):
    if user.role not in VERIFIED_USER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


async def get_verified_user_by_token(token: str, redis=None):
    """Resolve a verified user from a raw token, for WebSocket handshakes that run outside the HTTP dependency chain."""
    decoded = decode_token(token)
    if decoded is None or 'id' not in decoded or not await is_valid_token(decoded, redis):
        return None

    user = await Users.get_user_by_id(decoded['id'])
    if user is None or user.role not in VERIFIED_USER_ROLES:
        return None

    return user


async def get_verified_user_by_id(user_id: str | None):
    if not user_id:
        return None

    user = await Users.get_user_by_id(user_id)
    if user is None or user.role not in VERIFIED_USER_ROLES:
        return None

    return user


async def get_optional_verified_user_from_request(request: Request):
    token = None
    auth_token = get_http_authorization_cred(request.headers.get('Authorization'))
    if auth_token:
        token = auth_token.credentials
    if token is None:
        token = request.cookies.get('token')
    if token is None and getattr(request.state, 'token', None):
        token = request.state.token.credentials
    if not token:
        return None

    try:
        if token.startswith('sk-'):
            user = await get_current_user_by_api_key(request, token)
            return user if user.role in VERIFIED_USER_ROLES else None

        return await get_verified_user_by_token(token, getattr(request.app.state, 'redis', None))
    except HTTPException:
        return None


def get_admin_user(user=Depends(get_current_user)):
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


async def create_admin_user(email: str, password: str, name: str = 'Admin'):
    """
    Create an admin user from environment variables.
    Used for headless/automated deployments.
    Returns the created user or None if creation failed.
    """

    if not email or not password:
        return None

    if await Users.has_users():
        log.debug('Users already exist, skipping admin creation')
        return None

    log.info('Creating admin account from environment variables: %s', email)
    try:
        hashed = await get_password_hash(password)
        user = await Auths.insert_new_auth(
            email=email.lower(),
            password=hashed,
            name=name,
            role='admin',
        )
        if user:
            log.info('Admin account created successfully: %s', email)
            return user
        else:
            log.error('Failed to create admin account from environment variables')
            return None
    except Exception as e:
        log.error(f'Error creating admin account: {e}')
        return None


async def create_signin_response(
    request,
    user,
    db=None,
    response=None,
    set_cookie=False,
    source='password',
    auth=None,
    *,
    oauth_session_id=None,
    provider=None,
):
    """Gate every human login before issuing an application credential."""
    from open_webui.utils.mfa import get_auth, get_mfa_config, is_mfa_required, start_mfa_login

    auth = auth or await get_auth(user.id)
    current = await get_auth(user.id)
    if current.session_stamp != auth.session_stamp or current.password != auth.password:
        raise HTTPException(409, 'Authentication changed. Please sign in again.')
    config = await get_mfa_config()
    if config.ENABLE_MFA and user.role not in {'admin', 'user'}:
        return {'next_step': 'pending'}
    if is_mfa_required(source, config):
        return await start_mfa_login(current, source, oauth_session_id=oauth_session_id, provider=provider)
    return await create_session_response(
        request, user, db, response, set_cookie=set_cookie, source=source, auth=current
    )


async def create_session_response(
    request,
    user,
    db=None,
    response=None,
    set_cookie=False,
    source='password',
    *,
    auth,
    mfa_verified=False,
    auth_time=None,
):
    """Issue a completed human session using the credential snapshot that authorized it."""
    import time

    from open_webui.env import WEBUI_AUTH_COOKIE_SAME_SITE, WEBUI_AUTH_COOKIE_SECURE
    from open_webui.events import EVENTS, publish_event
    from open_webui.utils.access_control import get_permissions
    from open_webui.utils.mfa import get_auth, get_mfa_config, is_mfa_required

    current = await get_auth(user.id)
    if current.session_stamp != auth.session_stamp:
        raise HTTPException(409, 'Authentication changed. Please sign in again.')
    if is_mfa_required(source, await get_mfa_config()) and not mfa_verified:
        raise HTTPException(401, 'Authenticator verification is required.')
    expires_delta = parse_duration(await Config.get('auth.jwt_expiry'))
    expires_at = int(time.time()) + int(expires_delta.total_seconds()) if expires_delta else None
    token = create_token(
        {
            'id': user.id,
            'typ': 'session',
            'auth_method': source,
            'auth_time': auth_time or int(time.time()),
            'session_stamp': auth.session_stamp,
            'mfa_verified': mfa_verified,
        },
        expires_delta=expires_delta,
    )
    if set_cookie and response is not None:
        response.set_cookie(
            'token',
            token,
            httponly=True,
            secure=WEBUI_AUTH_COOKIE_SECURE,
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            max_age=int(expires_delta.total_seconds()) if expires_delta else None,
        )
    await publish_event(
        request,
        EVENTS.AUTH_LOGIN,
        actor=user,
        subject_id=user.id,
        subject_type='user',
        source=source,
        data={'auth_method': source},
    )
    return {
        'token': token,
        'token_type': 'Bearer',
        'expires_at': expires_at,
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'role': user.role,
        'profile_image_url': f'/api/v1/users/{user.id}/profile/image',
        'permissions': await get_permissions(user.id, await Config.get('user.permissions'), db=db),
    }


async def get_human_user(request: Request, user=Depends(get_current_user)):
    if request.state.auth_type != 'jwt' or request.state.claims.get('typ', 'session') != 'session':
        raise HTTPException(403, 'A human session is required.')
    return user
