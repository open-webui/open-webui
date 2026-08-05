import logging
import re
import time
from typing import Any, Optional
from urllib.parse import quote

import jwt
from open_webui.env import (
    FORWARD_SESSION_INFO_HEADER_CHAT_ID,
    FORWARD_SESSION_INFO_HEADER_MESSAGE_ID,
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

# {{USER_SECRET:<slot>}} resolves to a value the user stored for the connection,
# never to anything the admin or another user provided.
USER_SECRET_PLACEHOLDER_PATTERN = re.compile(r'\{\{USER_SECRET:([A-Za-z0-9_\-]{1,64})\}\}')

HOP_BY_HOP_HEADERS = ('host', 'content-length', 'connection', 'transfer-encoding', 'te', 'trailer', 'upgrade')


def get_reserved_header_names() -> frozenset[str]:
    """Header names that a per-user secret must never be able to set.

    Hop-by-hop headers plus the headers Open WebUI itself uses to tell the tool
    server who the caller is — taken from the configured names, since those are
    deployment specific.
    """
    return frozenset(
        name.strip().lower()
        for name in (
            *HOP_BY_HOP_HEADERS,
            'cookie',
            FORWARD_USER_INFO_HEADER_USER_NAME,
            FORWARD_USER_INFO_HEADER_USER_ID,
            FORWARD_USER_INFO_HEADER_USER_EMAIL,
            FORWARD_USER_INFO_HEADER_USER_ROLE,
            FORWARD_USER_INFO_HEADER_JWT,
            FORWARD_SESSION_INFO_HEADER_CHAT_ID,
            FORWARD_SESSION_INFO_HEADER_MESSAGE_ID,
        )
        if name
    )


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


def get_user_secret_slots(value: Any) -> set[str]:
    """Collect the ``{{USER_SECRET:<slot>}}`` slot names referenced by a template."""
    if value is None:
        return set()
    return {match.group(1) for match in USER_SECRET_PLACEHOLDER_PATTERN.finditer(str(value))}


def _resolve_user_secrets(value: str, user_secrets: dict, quote_value: bool = False) -> tuple[str, bool]:
    """Substitute ``{{USER_SECRET:<slot>}}`` in a template.

    Runs in a single pass, so a secret that happens to contain a placeholder is
    never expanded again. Returns the resolved value and whether every referenced
    slot actually had a value.
    """
    resolved = True

    def replace(match) -> str:
        nonlocal resolved
        slot_value = user_secrets.get(match.group(1))
        if slot_value is None or slot_value == '':
            resolved = False
            return ''
        slot_value = str(slot_value)
        return quote(slot_value, safe='') if quote_value else slot_value

    return USER_SECRET_PLACEHOLDER_PATTERN.sub(replace, value), resolved


def interpolate_user_secrets_in_url(url: str, user_secrets: dict | None) -> str:
    """Resolve user secrets used in a connection URL, percent-encoding the values."""
    if not url or '{{USER_SECRET:' not in url:
        return url
    resolved_url, _ = _resolve_user_secrets(url, user_secrets or {}, quote_value=True)
    return resolved_url


async def get_custom_headers(
    custom_headers: dict,
    user=None,
    metadata: dict = None,
    request=None,
    user_secrets: dict | None = None,
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
    user_secrets: dict | None = None,
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
    }

    user_secrets = user_secrets or {}

    parsed_headers = {}
    for key, value in custom_headers.items():
        if not isinstance(value, str):
            value = str(value)
        for token, val in template_vars.items():
            value = value.replace(token, val)

        # Secrets are resolved last so that a secret value that happens to contain a
        # placeholder is never expanded again.
        value, resolved = _resolve_user_secrets(value, user_secrets)
        if not resolved:
            # Sending 'Authorization: Bearer ' with the value missing tells the server
            # nothing useful and reads as a malformed credential; drop the header instead.
            log.debug('Dropping header %s: it references a user secret that is not set', key)
            continue

        parsed_headers[key] = value

    return parsed_headers
