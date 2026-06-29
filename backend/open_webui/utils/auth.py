from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Union

import bcrypt
import jwt
import pytz
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    ENABLE_OTEL,
    ENABLE_PASSWORD_VALIDATION,
    LICENSE_BLOB,
    OFFLINE_MODE,
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
from pytz import UTC

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
                for p, c in v.items():
                    globals().get('override_static', lambda a, b: None)(p, c)
            elif k == 'count':
                setattr(app.state, 'USER_COUNT', v)
            elif k == 'name':
                setattr(app.state, 'WEBUI_NAME', v)
            elif k == 'metadata':
                setattr(app.state, 'LICENSE_METADATA', v)

    def handler(u):
        res = requests.post(
            f'{u}/api/v1/license/',
            json={'key': key, 'version': '1'},
            timeout=5,
        )

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
            p = json.loads(aesgcm.decrypt(ln, lt, None))
            pk.verify(base64.b64decode(p['s']), p['p'].encode())

            pb = base64.b64decode(p['p'])
            pn, pt = nt(pb)

            data = json.loads(aesgcm.decrypt(pn, pt, None).decode())

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


async def is_valid_token(decoded, redis=None) -> bool:
    """
    Check whether a JWT has been revoked. Two mechanisms:
    1. Per-token (jti) — used by user-initiated sign-out (known jti).
    2. Per-user (revoked_at) — used by OIDC back-channel logout when
       individual jti values are unknown; rejects tokens with iat <= revoked_at.
    """
    if redis:
        # Per-token revocation
        jti = decoded.get('jti')
        if jti:
            revoked = await redis.get(f'{REDIS_KEY_PREFIX}:auth:token:{jti}:revoked')
            if revoked:
                return False

        # Per-user revocation (OIDC back-channel logout)
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
                # Store the revoked token in Redis with an expiration time
                await request.app.state.redis.set(
                    f'{REDIS_KEY_PREFIX}:auth:token:{jti}:revoked',
                    '1',
                    ex=ttl,
                )


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
                import asyncio

                asyncio.create_task(Users.update_last_active_by_id(user.id))
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

    user_permissions = await Config.get('user.permissions')
    enable_endpoint_restrictions = await Config.get('auth.api_key.endpoint_restrictions')
    allowed_endpoints = await Config.get('auth.api_key.allowed_endpoints', '')

    if not request.state.enable_api_keys or (
        user.role != 'admin'
        and not await has_permission(
            user.id,
            'features.api_keys',
            user_permissions,
        )
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED)

    # Enforce endpoint restrictions — checked here (not in middleware)
    # so it applies regardless of how the API key was transported
    # (Authorization header, cookie, x-api-key header, etc.).
    if enable_endpoint_restrictions:
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


def get_verified_user(user=Depends(get_current_user)):
    if user.role not in {'user', 'admin'}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


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

    log.info(f'Creating admin account from environment variables: {email}')
    try:
        hashed = await get_password_hash(password)
        user = await Auths.insert_new_auth(
            email=email.lower(),
            password=hashed,
            name=name,
            role='admin',
        )
        if user:
            log.info(f'Admin account created successfully: {email}')
            return user
        else:
            log.error('Failed to create admin account from environment variables')
            return None
    except Exception as e:
        log.error(f'Error creating admin account: {e}')
        return None
