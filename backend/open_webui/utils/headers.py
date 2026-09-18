import logging
import re
import time
from string import punctuation
from typing import Any, Optional
from urllib.parse import quote

import jwt
from open_webui.env import (
    FORWARD_USER_INFO_HEADER_AUTH_TYPE,
    FORWARD_USER_INFO_HEADER_JWT,
    FORWARD_USER_INFO_HEADER_JWT_EXPIRES_SECONDS,
    FORWARD_USER_INFO_HEADER_JWT_SECRET,
    FORWARD_USER_INFO_HEADER_USER_EMAIL,
    FORWARD_USER_INFO_HEADER_USER_ID,
    FORWARD_USER_INFO_HEADER_USER_NAME,
    FORWARD_USER_INFO_HEADER_USER_ROLE,
)
from open_webui.models.groups import Groups

log = logging.getLogger(__name__)

USER_GROUPS_PLACEHOLDERS = ('{{USER_GROUPS}}', '{{USER_GROUP_IDS}}')
USER_SECRET_PATTERN = re.compile(r'\{\{USER_SECRET:([A-Za-z_][A-Za-z0-9_.-]*)\}\}')

# These headers can alter the transport or bypass Open WebUI's identity boundary.
# User-provided secrets must never be allowed to populate them.
USER_SECRET_FORBIDDEN_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
    'upgrade',
    'host',
    'content-length',
    'cookie',
    'set-cookie',
}


def normalize_bearer_token(token: Any) -> str:
    return token.strip() if isinstance(token, str) else token or ''


def bearer_auth_header(token: Any) -> dict[str, str]:
    token = normalize_bearer_token(token)
    return {'Authorization': f'Bearer {token}'} if token else {}


def get_json_bearer_headers(token: Any = '') -> dict[str, str]:
    return {'Content-Type': 'application/json', **bearer_auth_header(token)}


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


def include_user_info_headers(headers: dict, user: Optional[Any] = None, *, request=None) -> dict:
    """
    Forward user identity to external backends: signed JWT in
    FORWARD_USER_INFO_HEADER_JWT if FORWARD_USER_INFO_HEADER_JWT_SECRET is set;
    otherwise the legacy X-OpenWebUI-User-* headers.
    Include the verified incoming auth type when a request provides it.
    """
    if user is None:
        return headers

    auth_type = getattr(getattr(request, 'state', None), 'auth_type', None)
    if auth_type in ('api_key', 'jwt'):
        headers = {**headers, FORWARD_USER_INFO_HEADER_AUTH_TYPE: auth_type}

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


def custom_headers_require_user_groups(custom_headers: Optional[dict]) -> bool:
    if not custom_headers or not isinstance(custom_headers, dict):
        return False
    return any(
        placeholder in str(value) for value in custom_headers.values() for placeholder in USER_GROUPS_PLACEHOLDERS
    )


async def get_user_groups_for_custom_headers(
    custom_headers: Optional[dict], user: Optional[Any] = None
) -> Optional[list]:
    """Fetch the user's groups only when a header value actually references a groups placeholder."""
    if user is None or not custom_headers_require_user_groups(custom_headers):
        return None

    try:
        return await Groups.get_groups_by_member_id(user.id)
    except Exception:
        log.exception('Failed to resolve user groups for custom headers')
        return None


def custom_headers_require_user_secrets(custom_headers: Optional[dict]) -> bool:
    if not custom_headers or not isinstance(custom_headers, dict):
        return False
    return any(USER_SECRET_PATTERN.search(str(value)) for value in custom_headers.values())


def _validate_user_secret_header_names(custom_headers: dict) -> None:
    for key in custom_headers:
        normalized_key = str(key).strip().lower()
        if (
            normalized_key in USER_SECRET_FORBIDDEN_HEADERS
            or normalized_key.startswith('forward_')
            or normalized_key.startswith('x-forwarded-')
        ):
            raise ValueError(f'User secrets cannot be used in the {key} header')


async def get_custom_headers(
    custom_headers: dict,
    user=None,
    metadata: dict = None,
    request=None,
    user_secrets: Optional[dict[str, str]] = None,
) -> dict:
    user_groups = await get_user_groups_for_custom_headers(custom_headers, user)
    return parse_custom_headers(
        custom_headers,
        user,
        metadata,
        request=request,
        user_groups=user_groups,
        user_secrets=user_secrets,
    )


def parse_custom_headers(
    custom_headers: dict,
    user=None,
    metadata: dict = None,
    request=None,
    user_groups: Optional[list] = None,
    user_secrets: Optional[dict[str, str]] = None,
) -> dict:
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
        '{{USER_GROUPS}}': ','.join(group.name.strip() for group in user_groups) if user_groups else '',
        '{{USER_GROUP_IDS}}': ','.join(group.id for group in user_groups) if user_groups else '',
        '{{USER_AGENT}}': user_agent,
        '{{AUTH_TYPE}}': getattr(getattr(request, 'state', None), 'auth_type', None) or '',
    }

    parsed_headers = {}
    if user_secrets is not None and custom_headers_require_user_secrets(custom_headers):
        _validate_user_secret_header_names(custom_headers)

    for key, value in custom_headers.items():
        if USER_SECRET_PATTERN.search(str(key)):
            raise ValueError('User secrets may only be used in header values')
        if not isinstance(value, str):
            value = str(value)
        for token, val in template_vars.items():
            value = value.replace(token, val)

        def replace_user_secret(match):
            secret_name = match.group(1)
            secret_value = (user_secrets or {}).get(secret_name)
            if not isinstance(secret_value, str) or not secret_value:
                raise ValueError(f'Missing user secret: {secret_name}')
            return secret_value

        value = USER_SECRET_PATTERN.sub(replace_user_secret, value)
        # Encode Unicode and controls after substitution; preserve ASCII header syntax and existing escapes.
        parsed_headers[key] = quote(value, safe=punctuation + ' \t')

    return parsed_headers
