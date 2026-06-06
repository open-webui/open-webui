from urllib.parse import quote

from open_webui.env import (
    FORWARD_USER_INFO_HEADER_USER_NAME,
    FORWARD_USER_INFO_HEADER_USER_ID,
    FORWARD_USER_INFO_HEADER_USER_EMAIL,
    FORWARD_USER_INFO_HEADER_USER_ROLE,
)


def include_user_info_headers(headers, user):
    return {
        **headers,
        FORWARD_USER_INFO_HEADER_USER_NAME: quote(user.name, safe=' '),
        FORWARD_USER_INFO_HEADER_USER_ID: user.id,
        FORWARD_USER_INFO_HEADER_USER_EMAIL: user.email,
        FORWARD_USER_INFO_HEADER_USER_ROLE: user.role,
    }


def get_custom_headers(custom_headers: dict, user=None, metadata: dict = None) -> dict:
    if not custom_headers or not isinstance(custom_headers, dict):
        return {}

    metadata = metadata or {}
    template_vars = {
        '{{CHAT_ID}}': metadata.get('chat_id', '') or '',
        '{{MESSAGE_ID}}': metadata.get('message_id', '') or '',
        '{{USER_ID}}': (user.id if user else '') or '',
        '{{USER_NAME}}': (user.name if user else '') or '',
    }

    parsed_headers = {}
    for key, value in custom_headers.items():
        if not isinstance(value, str):
            value = str(value)
        for token, val in template_vars.items():
            value = value.replace(token, val)
        parsed_headers[key] = value

    return parsed_headers
