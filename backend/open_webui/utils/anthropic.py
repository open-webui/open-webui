import logging

import aiohttp

from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)
from open_webui.models.users import UserModel
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


def is_anthropic_url(url: str) -> bool:
    """Check if the URL is an Anthropic API endpoint."""
    return "api.anthropic.com" in url


async def get_anthropic_models(url: str, key: str, user: UserModel = None) -> dict:
    """
    Fetch models from Anthropic's /v1/models endpoint with pagination.
    Normalizes the response to OpenAI format.
    """
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    all_models = []
    after_id = None

    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            while True:
                params = {"limit": 1000}
                if after_id:
                    params["after_id"] = after_id

                async with session.get(
                    f"{url}/models",
                    headers=headers,
                    params=params,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    if response.status != 200:
                        error_detail = f"HTTP Error: {response.status}"
                        try:
                            res = await response.json()
                            if "error" in res:
                                error_detail = f"External Error: {res['error']}"
                        except Exception:
                            pass
                        return {"object": "list", "data": [], "error": error_detail}

                    data = await response.json()

                    for model in data.get("data", []):
                        all_models.append({
                            "id": model.get("id"),
                            "object": "model",
                            "created": 0,
                            "owned_by": "anthropic",
                            "name": model.get("display_name", model.get("id")),
                        })

                    if not data.get("has_more", False):
                        break
                    after_id = data.get("last_id")

    except Exception as e:
        log.error(f"Anthropic connection error: {e}")
        return None

    return {"object": "list", "data": all_models}
