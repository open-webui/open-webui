from urllib.parse import quote
import os


def include_user_info_headers(headers, user):
    return {
        **headers,
        os.environ.get("FORWARD_USER_INFO_NAME", "X-OpenWebUI-User-Name"): quote(user.name, safe=" "),
        os.environ.get("FORWARD_USER_INFO_ID", "X-OpenWebUI-User-Id"): user.id,
        os.environ.get("FORWARD_USER_INFO_EMAIL", "X-OpenWebUI-User-Email"): user.email,
        os.environ.get("FORWARD_USER_INFO_ROLE", "X-OpenWebUI-User-Role"): user.role,
    }
