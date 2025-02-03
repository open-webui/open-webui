import logging
import uuid
import jwt

from datetime import UTC, datetime, timedelta
from typing import Optional, Union, List, Dict

from open_webui.models.users import Users
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import WEBUI_SECRET_KEY
from open_webui.storage.redis_client import redis_client

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from authlib.oidc.core import UserInfo
import requests
logging.getLogger("passlib").setLevel(logging.ERROR)

log = logging.getLogger(__name__)

SESSION_SECRET = WEBUI_SECRET_KEY
ALGORITHM = "HS256"

##############
# Auth Utils
##############

bearer_security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password) if hashed_password else None


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


def get_organization_name(siret: str):
    org = requests.get(f"https://recherche-entreprises.api.gouv.fr/search?q={siret}&page=1&per_page=1")
    return org.json()["results"][0]["nom_complet"] if org.json()["results"] else ""


def get_http_authorization_cred(auth_header: str):
    try:
        scheme, credentials = auth_header.split(" ")
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    except Exception:
        raise ValueError(ERROR_MESSAGES.INVALID_TOKEN)


async def get_current_user(request: Request):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise credentials_exception

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, SESSION_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        if user_id is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    user = Users.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_verified_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "Could not validate credentials")
    return user


async def get_admin_user(user=Depends(get_current_user)):
    if not user or user.role != "admin":
        raise HTTPException(401, "Admin privileges required")
    return user
