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
        FORWARD_USER_INFO_HEADER_USER_NAME: quote(user.name, safe=" "),
        FORWARD_USER_INFO_HEADER_USER_ID: user.id,
        FORWARD_USER_INFO_HEADER_USER_EMAIL: user.email,
        FORWARD_USER_INFO_HEADER_USER_ROLE: user.role,
    }
