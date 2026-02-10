import logging
import uuid
import jwt
import base64
import hmac
import hashlib
import requests
import os
import bcrypt

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import json


from datetime import datetime, timedelta
import pytz
from pytz import UTC
from typing import Optional, Union, List, Dict

from opentelemetry import trace


from open_webui.utils.access_control import has_permission
from open_webui.models.users import Users
from open_webui.models.auths import Auths


from open_webui.constants import ERROR_MESSAGES

from open_webui.env import (
    ENABLE_PASSWORD_VALIDATION,
    OFFLINE_MODE,
    LICENSE_BLOB,
    PASSWORD_VALIDATION_REGEX_PATTERN,
    REDIS_KEY_PREFIX,
    pk,
    WEBUI_SECRET_KEY,
    TRUSTED_SIGNATURE_KEY,
    STATIC_DIR,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
)

from fastapi import BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


log = logging.getLogger(__name__)

SESSION_SECRET = WEBUI_SECRET_KEY
ALGORITHM = "HS256"

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
    if "/" in path or ".." in path:
        log.error(f"Invalid path: {path}")
        return

    file_path = os.path.join(STATIC_DIR, path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(base64.b64decode(content))  # Convert Base64 back to raw binary


def get_license_data(app, key):
    def data_handler(data):
        for k, v in data.items():
            if k == "resources":
                for p, c in v.items():
                    globals().get("override_static", lambda a, b: None)(p, c)
            elif k == "count":
                setattr(app.state, "USER_COUNT", v)
            elif k == "name":
                setattr(app.state, "WEBUI_NAME", v)
            elif k == "metadata":
                setattr(app.state, "LICENSE_METADATA", v)

    def handler(u):
        res = requests.post(
            f"{u}/api/v1/license/",
            json={"key": key, "version": "1"},
            timeout=5,
        )

        if getattr(res, "ok", False):
            payload = getattr(res, "json", lambda: {})()
            data_handler(payload)
            return True
        else:
            log.error(
                f"License: retrieval issue: {getattr(res, 'text', 'unknown error')}"
            )

    if key:
        us = [
            "https://api.openwebui.com",
            "https://licenses.api.openwebui.com",
        ]
        try:
            for u in us:
                if handler(u):
                    return True
        except Exception as ex:
            log.exception(f"License: Uncaught Exception: {ex}")

    try:
        if LICENSE_BLOB:
            nl = 12
            kb = hashlib.sha256((key.replace("-", "").upper()).encode()).digest()

            def nt(b):
                return b[:nl], b[nl:]

            lb = base64.b64decode(LICENSE_BLOB)
            ln, lt = nt(lb)

            aesgcm = AESGCM(kb)
            p = json.loads(aesgcm.decrypt(ln, lt, None))
            pk.verify(base64.b64decode(p["s"]), p["p"].encode())

            pb = base64.b64decode(p["p"])
            pn, pt = nt(pb)

            data = json.loads(aesgcm.decrypt(pn, pt, None).decode())
            if not data.get("exp") and data.get("exp") < datetime.now().date():
                return False

            data_handler(data)
            return True
    except Exception as e:
        log.error(f"License: {e}")

    return False


bearer_security = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def validate_password(password: str) -> bool:
    # The password passed to bcrypt must be 72 bytes or fewer. If it is longer, it will be truncated before hashing.
    if len(password.encode("utf-8")) > 72:
        raise Exception(
            ERROR_MESSAGES.PASSWORD_TOO_LONG,
        )

    if ENABLE_PASSWORD_VALIDATION:
        if not PASSWORD_VALIDATION_REGEX_PATTERN.match(password):
            raise Exception(ERROR_MESSAGES.INVALID_PASSWORD())

    return True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return (
        bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
        if hashed_password
        else None
    )


def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    payload = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        payload.update({"exp": expire})

    jti = str(uuid.uuid4())
    payload.update({"jti": jti})

    encoded_jwt = jwt.encode(payload, SESSION_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, SESSION_SECRET, algorithms=[ALGORITHM])
        return decoded
    except Exception:
        return None


async def is_valid_token(request, decoded) -> bool:
    # Require Redis to check revoked tokens
    if request.app.state.redis:
        jti = decoded.get("jti")

        if jti:
            revoked = await request.app.state.redis.get(
                f"{REDIS_KEY_PREFIX}:auth:token:{jti}:revoked"
            )
            if revoked:
                return False

    return True


async def invalidate_token(request, token):
    decoded = decode_token(token)

    # If token is invalid/expired, nothing to revoke
    if not decoded:
        return

    # Require Redis to store revoked tokens
    if request.app.state.redis:
        jti = decoded.get("jti")
        exp = decoded.get("exp")

        if jti and exp:
            ttl = exp - int(
                datetime.now(UTC).timestamp()
            )  # Calculate time-to-live for the token

            if ttl > 0:
                # Store the revoked token in Redis with an expiration time
                await request.app.state.redis.set(
                    f"{REDIS_KEY_PREFIX}:auth:token:{jti}:revoked",
                    "1",
                    ex=ttl,
                )


def extract_token_from_auth_header(auth_header: str):
    return auth_header[len("Bearer ") :]


def create_api_key():
    key = str(uuid.uuid4()).replace("-", "")
    return f"sk-{key}"


def get_http_authorization_cred(auth_header: Optional[str]):
    if not auth_header:
        return None
    try:
        scheme, credentials = auth_header.split(" ")
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

    if token is None and "token" in request.cookies:
        token = request.cookies.get("token")

    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # auth by api key
    if token.startswith("sk-"):
        user = get_current_user_by_api_key(request, token)

        # Add user info to current span
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("client.user.id", user.id)
            current_span.set_attribute("client.user.email", user.email)
            current_span.set_attribute("client.user.role", user.role)
            current_span.set_attribute("client.auth.type", "api_key")

        return user

    # auth by jwt token
    try:
        try:
            data = decode_token(token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        if data is not None and "id" in data:
            if data.get("jti") and not await is_valid_token(request, data):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                )

            user = Users.get_user_by_id(data["id"])
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ERROR_MESSAGES.INVALID_TOKEN,
                )
            else:
                if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
                    trusted_email = request.headers.get(
                        WEBUI_AUTH_TRUSTED_EMAIL_HEADER, ""
                    ).lower()
                    if trusted_email and user.email != trusted_email:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User mismatch. Please sign in again.",
                        )

                # Add user info to current span
                current_span = trace.get_current_span()
                if current_span:
                    current_span.set_attribute("client.user.id", user.id)
                    current_span.set_attribute("client.user.email", user.email)
                    current_span.set_attribute("client.user.role", user.role)
                    current_span.set_attribute("client.auth.type", "jwt")

                # Refresh the user's last active timestamp asynchronously
                # to prevent blocking the request
                if background_tasks:
                    background_tasks.add_task(Users.update_last_active_by_id, user.id)
            return user
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )
    except Exception as e:
        # Delete the token cookie
        if request.cookies.get("token"):
            response.delete_cookie("token")

        if request.cookies.get("oauth_id_token"):
            response.delete_cookie("oauth_id_token")

        # Delete OAuth session if present
        if request.cookies.get("oauth_session_id"):
            response.delete_cookie("oauth_session_id")

        raise e


def get_current_user_by_api_key(request, api_key: str):
    # Each function call manages its own short-lived session internally
    user = Users.get_user_by_api_key(api_key)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )

    if not request.state.enable_api_keys or (
        user.role != "admin"
        and not has_permission(
            user.id,
            "features.api_keys",
            request.app.state.config.USER_PERMISSIONS,
        )
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED
        )

    # Add user info to current span
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute("client.user.id", user.id)
        current_span.set_attribute("client.user.email", user.email)
        current_span.set_attribute("client.user.role", user.role)
        current_span.set_attribute("client.auth.type", "api_key")

    Users.update_last_active_by_id(user.id)
    return user


def get_verified_user(user=Depends(get_current_user)):
    if user.role not in {"user", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


def get_admin_user(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


def create_admin_user(email: str, password: str, name: str = "Admin"):
    """
    Create an admin user from environment variables.
    Used for headless/automated deployments.
    Returns the created user or None if creation failed.
    """

    if not email or not password:
        return None

    if Users.has_users():
        log.debug("Users already exist, skipping admin creation")
        return None

    log.info(f"Creating admin account from environment variables: {email}")
    try:
        hashed = get_password_hash(password)
        user = Auths.insert_new_auth(
            email=email.lower(),
            password=hashed,
            name=name,
            role="admin",
        )
        if user:
            log.info(f"Admin account created successfully: {email}")
            return user
        else:
            log.error("Failed to create admin account from environment variables")
            return None
    except Exception as e:
        log.error(f"Error creating admin account: {e}")
        return None
