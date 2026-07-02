import logging
import time
from typing import Any, Optional
from urllib.parse import quote

import jwt
from open_webui.env import (
    FORWARD_USER_INFO_HEADER_JWT,
    FORWARD_USER_INFO_HEADER_JWT_EXPIRES_SECONDS,
    FORWARD_USER_INFO_HEADER_JWT_SECRET,
    FORWARD_USER_INFO_HEADER_USER_EMAIL,
    FORWARD_USER_INFO_HEADER_USER_ID,
    FORWARD_USER_INFO_HEADER_USER_NAME,
    FORWARD_USER_INFO_HEADER_USER_ROLE,
)

log = logging.getLogger(__name__)


def _mint_forward_user_jwt(user: Any) -> str:
    now = int(time.time())
    payload = {
        'sub': str(user.id),
        'email': str(user.email),
        'name': str(user.name),
        'role': str(user.role),
        'iss': 'open-webui',
        'iat': now,
        'exp': now + FORWARD_USER_INFO_HEADER_JWT_EXPIRES_SECONDS,
    }
    return jwt.encode(payload, FORWARD_USER_INFO_HEADER_JWT_SECRET, algorithm='HS256')


def include_user_info_headers(headers: dict, user: Optional[Any] = None) -> dict:
    """
    Forward user identity to external backends: signed JWT in
    FORWARD_USER_INFO_HEADER_JWT if FORWARD_USER_INFO_HEADER_JWT_SECRET is set;
    otherwise the legacy X-OpenWebUI-User-* headers.
    """
    if user is None:
        return headers

    if FORWARD_USER_INFO_HEADER_JWT_SECRET:
        try:
            token = _mint_forward_user_jwt(user)
            return {**headers, FORWARD_USER_INFO_HEADER_JWT: token}
        except Exception:
            log.exception(
                'Failed to mint %s; falling back to plain user-info headers.',
                FORWARD_USER_INFO_HEADER_JWT,
            )

    return {
        **headers,
        FORWARD_USER_INFO_HEADER_USER_NAME: quote(user.name.strip(), safe=' '),
        FORWARD_USER_INFO_HEADER_USER_ID: user.id,
        FORWARD_USER_INFO_HEADER_USER_EMAIL: user.email.strip(),
        FORWARD_USER_INFO_HEADER_USER_ROLE: user.role,
    }


def get_custom_headers(custom_headers: dict, user=None, metadata: dict = None, request=None) -> dict:
    if not custom_headers or not isinstance(custom_headers, dict):
        return {}

    metadata = metadata or {}

    # UA from the live request; fall back to metadata for detached RAG/tool calls.
    user_agent = ''
    if request is not None:
        try:
            user_agent = request.headers.get('user-agent', '') or ''
        except Exception:
            user_agent = ''
    if not user_agent:
        user_agent = metadata.get('user_agent', '') or ''

    # Extract user_message info for tree mapping
    user_message = metadata.get('user_message') or {}
    user_message_id = metadata.get('user_message_id', '') or (user_message.get('id', '') if user_message else '')
    user_message_parent_id = user_message.get('parentId', '') if user_message else ''

    template_vars = {
        '{{CHAT_ID}}': metadata.get('chat_id', '') or '',
        '{{MESSAGE_ID}}': metadata.get('message_id', '') or '',
        '{{USER_MESSAGE_ID}}': user_message_id or '',
        '{{USER_MESSAGE_PARENT_ID}}': user_message_parent_id or '',
        '{{FILE_ID}}': metadata.get('file_id', '') or '',
        '{{FILE_NAME}}': metadata.get('file_name', '') or '',
        '{{FILE_CONTENT_TYPE}}': metadata.get('file_content_type', '') or '',
        '{{TASK}}': metadata.get('task', '') or '',
        '{{USER_ID}}': (user.id if user else '') or '',
        '{{USER_NAME}}': (user.name.strip() if user else '') or '',
        '{{USER_EMAIL}}': (user.email.strip() if user else '') or '',
        '{{USER_ROLE}}': (user.role if user else '') or '',
        '{{USER_AGENT}}': user_agent,
    }

    parsed_headers = {}
    for key, value in custom_headers.items():
        if not isinstance(value, str):
            value = str(value)
        for token, val in template_vars.items():
            value = value.replace(token, val)
        parsed_headers[key] = value

    return parsed_headers
