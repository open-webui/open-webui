from urllib.parse import quote


def include_user_info_headers(headers, user):
    return {
        **headers,
        "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
        "X-OpenWebUI-User-Id": user.id,
        "X-OpenWebUI-User-Email": user.email,
        "X-OpenWebUI-User-Role": user.role,
    }
