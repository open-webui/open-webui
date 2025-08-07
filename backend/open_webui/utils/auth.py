import logging
import uuid
import jwt
import base64
import hmac
import hashlib
import requests
import os
import pyotp
import secrets
import qrcode
import io
import json


from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import json


from datetime import datetime, timedelta
import pytz
from pytz import UTC
from typing import Optional, Union, List, Dict

from opentelemetry import trace

from open_webui.models.users import Users

from open_webui.constants import ERROR_MESSAGES

from open_webui.env import (
    OFFLINE_MODE,
    LICENSE_BLOB,
    pk,
    WEBUI_SECRET_KEY,
    TRUSTED_SIGNATURE_KEY,
    STATIC_DIR,
    SRC_LOG_LEVELS,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
)

from fastapi import BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext


logging.getLogger("passlib").setLevel(logging.ERROR)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OAUTH"])

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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return (
        pwd_context.verify(plain_password, hashed_password) if hashed_password else None
    )


def get_password_hash(password):
    return pwd_context.hash(password)


def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    payload = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        payload.update({"exp": expire})

    encoded_jwt = jwt.encode(payload, SESSION_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, SESSION_SECRET, algorithms=[ALGORITHM])
        return decoded
    except Exception:
        return None


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


def get_current_user(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    auth_token: HTTPAuthorizationCredentials = Depends(bearer_security),
):
    token = None

    if auth_token is not None:
        token = auth_token.credentials

    if token is None and "token" in request.cookies:
        token = request.cookies.get("token")

    if token is None:
        raise HTTPException(status_code=403, detail="Not authenticated")

    # auth by api key
    if token.startswith("sk-"):
        if not request.state.enable_api_key:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED
            )

        if request.app.state.config.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS:
            allowed_paths = [
                path.strip()
                for path in str(
                    request.app.state.config.API_KEY_ALLOWED_ENDPOINTS
                ).split(",")
            ]

            # Check if the request path matches any allowed endpoint.
            if not any(
                request.url.path == allowed
                or request.url.path.startswith(allowed + "/")
                for allowed in allowed_paths
            ):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED
                )

        user = get_current_user_by_api_key(token)

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
        data = decode_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if data is not None and "id" in data:
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
                    # Delete the token cookie
                    response.delete_cookie("token")
                    # Delete OAuth token if present
                    if request.cookies.get("oauth_id_token"):
                        response.delete_cookie("oauth_id_token")
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
                background_tasks.add_task(Users.update_user_last_active_by_id, user.id)
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )


def get_current_user_by_api_key(api_key: str):
    user = Users.get_user_by_api_key(api_key)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )
    else:
        # Add user info to current span
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("client.user.id", user.id)
            current_span.set_attribute("client.user.email", user.email)
            current_span.set_attribute("client.user.role", user.role)
            current_span.set_attribute("client.auth.type", "api_key")

        Users.update_user_last_active_by_id(user.id)

    return user


def get_verified_user(user=Depends(get_current_user)):
    if user.role not in {"user", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user

##############
# TOTP Utils
##############

def generate_totp_secret() -> str:
    """
    Generate a new TOTP secret key for a user.
    Returns a base32-encoded secret string.
    """
    return pyotp.random_base32()


def generate_totp_qr_code(uri: str) -> str:
    """
    Generate a QR code image (as base64 string) for TOTP setup.
    
    Args:
        uri: The complete TOTP URI (otpauth://totp/...)
    
    Returns:
        Base64-encoded PNG image of the QR code
    """
    
    # Generate QR code with settings specifically for Google Authenticator
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=4
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 with proper data URL prefix
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    # Return with data URL prefix
    return f"data:image/png;base64,{img_str}"


def verify_totp_code(totp_secret: str, user_code: str, window: int = 1) -> bool:
    """
    Verify a TOTP code against the user's secret.
    
    Args:
        totp_secret: The user's TOTP secret key
        user_code: The 6-digit code entered by the user
        window: Time window tolerance (default: 1 = ±30 seconds)
    
    Returns:
        True if code is valid, False otherwise
    """
    if not totp_secret or not user_code:
        return False
    
    try:
        # Remove any spaces or formatting from the code
        clean_code = user_code.replace(" ", "").replace("-", "")
        
        # Verify the code is 6 digits
        if not clean_code.isdigit() or len(clean_code) != 6:
            return False
        
        totp = pyotp.TOTP(totp_secret)
        return totp.verify(clean_code, valid_window=window)
    except Exception as e:
        return False
    

def generate_backup_codes(count: int = 8) -> List[str]:
    """
    Generate backup recovery codes for TOTP.
    
    Args:
        count: Number of backup codes to generate (default: 8)
    
    Returns:
        List of backup codes (each is 8 characters)
    """
    codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric code
        code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
        codes.append(code)
    return codes


def verify_backup_code(stored_codes: str, user_code: str) -> tuple[bool, str]:
    """
    Verify a backup code and remove it from the stored codes.
    
    Args:
        stored_codes: JSON string of remaining backup codes
        user_code: The backup code entered by the user
    
    Returns:
        Tuple of (is_valid, updated_codes_json)
    """
    if not stored_codes or not user_code:
        return False, stored_codes
    
    try:
        codes_list = json.loads(stored_codes) if stored_codes else []
        clean_code = user_code.upper().replace(" ", "").replace("-", "")
        
        if clean_code in codes_list:
            # Remove the used code
            codes_list.remove(clean_code)
            updated_codes = json.dumps(codes_list)
            return True, updated_codes
        
        return False, stored_codes
    except Exception as e:
        log.error(f"Backup code verification error: {e}")
        return False, stored_codes


def hash_backup_codes(codes: List[str]) -> str:
    """
    Convert backup codes list to JSON string for database storage.
    
    Args:
        codes: List of backup codes
    
    Returns:
        JSON string of the codes
    """
    return json.dumps(codes)


def get_admin_user(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user
