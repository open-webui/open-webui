import hashlib
from urllib.parse import quote

from open_webui.env import WEBUI_SECRET_KEY


def generate_safety_identifier(user_id: str) -> str:
    salted_value = f"{WEBUI_SECRET_KEY}{user_id}".encode('utf-8')
    hash_object = hashlib.sha256(salted_value)
    return hash_object.hexdigest()


def include_user_info_headers(headers, user):
    return {
        **headers,
        "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
        "X-OpenWebUI-User-Id": user.id,
        "X-OpenWebUI-User-Email": user.email,
        "X-OpenWebUI-User-Role": user.role,
    }
