import logging
import uuid
import json
from datetime import UTC, datetime, timedelta
from typing import Optional, Union

import jwt
import tiktoken
from tiktoken import Encoding

from open_webui.apps.webui.models.users import Users
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import WEBUI_SECRET_KEY
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

logging.getLogger("passlib").setLevel(logging.ERROR)

SESSION_SECRET = WEBUI_SECRET_KEY
ALGORITHM = "HS256"

##############
# Auth Utils
##############

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
    return auth_header[len("Bearer "):]


def create_api_key():
    key = str(uuid.uuid4()).replace("-", "")
    return f"sk-{key}"


def get_http_authorization_cred(auth_header: str):
    try:
        scheme, credentials = auth_header.split(" ")
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    except Exception:
        raise ValueError(ERROR_MESSAGES.INVALID_TOKEN)


def get_current_user(
        request: Request,
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
        return get_current_user_by_api_key(token)

    # auth by jwt token
    data = decode_token(token)
    if data is not None and "id" in data:
        user = Users.get_user_by_id(data["id"])
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.INVALID_TOKEN,
            )
        else:
            Users.update_user_last_active_by_id(user.id)
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
        Users.update_user_last_active_by_id(user.id)

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


def prompt_tokens(encoding: Encoding, messages) -> int:
    count = sum(len(encoding.encode(msg['content'])) for msg in messages)
    return count


async def completion_tokens(encoding: Encoding, data: bytes):
    total_tokens = 0
    # 将bytes解码为字符串
    decoded_data = data.decode("utf-8")

    # 逐行处理解码后的数据
    for line in decoded_data.splitlines():
        # 检查数据是否以 'data: ' 开头
        if line.startswith("data: "):
            # 移除 'data: '，并解析为 JSON 对象
            json_data = line[len("data: "):]
            if json_data == '[DONE]':
                break
            try:
                # 解析 JSON
                parsed_data = json.loads(json_data)
                # 从JSON中的'delta'字段中提取'content'
                if 'choices' in parsed_data and parsed_data['choices']:
                    delta = parsed_data['choices'][0].get('delta', {})
                    content = delta.get('content', "")
                    # 对内容进行分词（以空格分词，这里可以根据实际需要修改）
                    total_tokens += len(encoding.encode(content))
            except json.JSONDecodeError:
                continue  # 如果解析失败，跳过这行数据

    return total_tokens
