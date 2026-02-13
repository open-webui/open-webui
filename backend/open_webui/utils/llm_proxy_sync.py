import asyncio
import logging
import requests
from typing import Optional

from open_webui.env import (
    LLM_PROXY_SYNC_USERS,
    LLM_PROXY_API_BASE_URL,
    LLM_PROXY_API_KEY,
    LLM_PROXY_SYNC_USER_ALIAS,
    LLM_PROXY_SYNC_TIMEOUT,
    LLM_PROXY_SYNC_ENDPOINT,
    LLM_PROXY_SYNC_KEY_USER_ID,
    LLM_PROXY_SYNC_KEY_USER_EMAIL,
    LLM_PROXY_SYNC_KEY_USER_ALIAS,
)

log = logging.getLogger(__name__)

# In-memory cache to avoid redundant syncs per process lifetime
_synced_users: set = set()


def sync_user_to_llm_proxy(user: dict) -> bool:
    """Sync a user to the configured LLM proxy (e.g. LiteLLM).

    Calls the proxy's user creation endpoint. If the user already exists
    (HTTP 409), the sync is considered successful.

    Args:
        user: User dict with id, email, name, role fields.

    Returns:
        True if sync successful or skipped, False on error.
    """
    if not LLM_PROXY_SYNC_USERS:
        return True

    if not LLM_PROXY_API_BASE_URL:
        log.warning("LLM_PROXY_SYNC_USERS is enabled but LLM_PROXY_API_BASE_URL is not set")
        return False

    if not LLM_PROXY_API_KEY:
        log.warning("LLM_PROXY_SYNC_USERS is enabled but LLM_PROXY_API_KEY is not set")
        return False

    user_id = user.get("id")
    user_email = user.get("email")

    if not user_id or not user_email:
        return False

    cache_key = f"{user_id}:{user_email}"
    if cache_key in _synced_users:
        return True

    try:
        payload = {
            LLM_PROXY_SYNC_KEY_USER_ID: user_id,
            LLM_PROXY_SYNC_KEY_USER_EMAIL: user_email,
        }

        if LLM_PROXY_SYNC_USER_ALIAS and "name" in user:
            payload[LLM_PROXY_SYNC_KEY_USER_ALIAS] = user["name"]

        headers = {
            "Authorization": f"Bearer {LLM_PROXY_API_KEY}",
            "Content-Type": "application/json",
            "accept": "application/json",
        }

        url = f"{LLM_PROXY_API_BASE_URL.rstrip('/')}{LLM_PROXY_SYNC_ENDPOINT}"

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=LLM_PROXY_SYNC_TIMEOUT,
        )

        if response.status_code in [200, 201, 409]:
            log.info(f"Synced user to LLM proxy: {user_email} ({user_id})")
            _synced_users.add(cache_key)
            return True
        else:
            log.error(
                f"Failed to sync user to LLM proxy: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        log.error(f"Error syncing user to LLM proxy: {e}")
        return False


async def maybe_sync_user(user_dict: Optional[dict]) -> None:
    """Convenience wrapper: sync user if enabled and user dict is provided.

    This is the main entry point called from the middleware. It never raises —
    sync failures are logged but do not block the chat request.
    The blocking HTTP call is offloaded to a thread so it cannot stall the
    async event loop.
    """
    if not LLM_PROXY_SYNC_USERS:
        return

    if not user_dict:
        return

    try:
        await asyncio.to_thread(sync_user_to_llm_proxy, user_dict)
    except Exception as e:
        log.error(f"Unexpected error in LLM proxy user sync: {e}")
