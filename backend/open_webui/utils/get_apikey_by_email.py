import os

import requests
from open_webui.models.users import Users


def get_api_key_by_email(user):
    url = os.environ.get("OPENAI_API_BASE_URL", "https://api.aibrary.dev/v0")
    secret = os.environ.get("SECRET_EMAIL_APIKEY")
    if not secret:
        raise ValueError("add SECRET_EMAIL_APIKEY in env")
    response = requests.post(
        f"{url}/auth/api-key",
        headers={"Authorization": f"Bearer {secret}"},
        json={"email": user.email},
    )
    response.raise_for_status()
    api_key = response.json()["api_key"]
    success = Users.update_user_api_key_by_id(user.id, api_key)
    return api_key, success
