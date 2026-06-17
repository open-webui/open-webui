import logging
import time
from typing import Any
from urllib.parse import quote

import jwt
from open_webui.env import (
    ENABLE_FORWARD_CLIENT_USER_AGENT,
    FORWARD_CLIENT_HEADERS,
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


def include_user_info_headers(headers: dict, user: Any | None = None) -> dict:
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
        FORWARD_USER_INFO_HEADER_USER_NAME: quote(user.name, safe=' '),
        FORWARD_USER_INFO_HEADER_USER_ID: user.id,
        FORWARD_USER_INFO_HEADER_USER_EMAIL: user.email,
        FORWARD_USER_INFO_HEADER_USER_ROLE: user.role,
    }


def _has_header(headers: dict, header_name: str) -> bool:
    return any(header.lower() == header_name.lower() for header in headers)


def include_client_headers(headers: dict, request: Any | None = None) -> dict:
    """
    Forward selected inbound client headers to backend requests.

    Existing outbound headers take precedence (case-insensitive), so explicit
    custom or caller-provided header values are not overwritten. User-Agent is
    controlled by ENABLE_FORWARD_CLIENT_USER_AGENT; additional headers are
    controlled by the FORWARD_CLIENT_HEADERS allow-list.
    """
    if request is None:
        return headers

    header_names = [*FORWARD_CLIENT_HEADERS]
    if ENABLE_FORWARD_CLIENT_USER_AGENT:
        header_names.append('User-Agent')

    forwarded_headers = headers
    for header_name in header_names:
        if _has_header(forwarded_headers, header_name):
            continue

        header_value = request.headers.get(header_name)
        if not header_value:
            continue

        if forwarded_headers is headers:
            forwarded_headers = {**headers}
        forwarded_headers[header_name] = header_value

    return forwarded_headers


def include_client_user_agent_header(headers: dict, request: Any | None = None) -> dict:
    """Forward the inbound client's User-Agent to backend requests when enabled."""
    return include_client_headers(headers, request)


def get_custom_headers(custom_headers: dict, user=None, metadata: dict = None) -> dict:
    if not custom_headers or not isinstance(custom_headers, dict):
        return {}

    metadata = metadata or {}
    template_vars = {
        '{{CHAT_ID}}': metadata.get('chat_id', '') or '',
        '{{MESSAGE_ID}}': metadata.get('message_id', '') or '',
        '{{USER_ID}}': (user.id if user else '') or '',
        '{{USER_NAME}}': (user.name if user else '') or '',
        '{{USER_EMAIL}}': (user.email if user else '') or '',
        '{{USER_ROLE}}': (user.role if user else '') or '',
    }

    parsed_headers = {}
    for key, value in custom_headers.items():
        if not isinstance(value, str):
            value = str(value)
        for token, val in template_vars.items():
            value = value.replace(token, val)
        parsed_headers[key] = value

    return parsed_headers
