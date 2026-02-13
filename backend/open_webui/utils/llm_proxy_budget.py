import asyncio
import logging
import time
import requests
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from open_webui.env import (
    LLM_PROXY_BUDGET_ENFORCE,
    LLM_PROXY_API_BASE_URL,
    LLM_PROXY_API_KEY,
    LLM_PROXY_BUDGET_ENDPOINT,
    LLM_PROXY_BUDGET_HTTP_METHOD,
    LLM_PROXY_BUDGET_TIMEOUT,
    LLM_PROXY_BUDGET_CACHE_TTL,
    LLM_PROXY_BUDGET_JSON_PATH_SPEND,
    LLM_PROXY_BUDGET_JSON_PATH_MAX_BUDGET,
    LLM_PROXY_BUDGET_JSON_PATH_BUDGET_RESET_AT,
    LLM_PROXY_BUDGET_QUERY_PARAM,
    LLM_PROXY_BUDGET_AUTH_HEADER,
    LLM_PROXY_BUDGET_EXCEEDED_MSG,
    LLM_PROXY_BUDGET_BLOCK_ADMINS,
)

log = logging.getLogger(__name__)

# In-memory cache: user_id -> (timestamp, is_over_budget)
_budget_cache: dict[str, Tuple[float, bool]] = {}


def _resolve_json_path(data: dict, path: str) -> Any:
    """Resolve a dot-separated JSON path against a dict.

    Example: _resolve_json_path({"user_info": {"spend": 3.5}}, "user_info.spend") -> 3.5
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _fetch_user_budget_info(user_id: str) -> Optional[dict]:
    """Fetch user budget info from the LLM proxy."""
    if not LLM_PROXY_API_BASE_URL:
        log.warning("LLM_PROXY_BUDGET_ENFORCE is enabled but LLM_PROXY_API_BASE_URL is not set")
        return None

    if not LLM_PROXY_API_KEY:
        log.warning("LLM_PROXY_BUDGET_ENFORCE is enabled but LLM_PROXY_API_KEY is not set")
        return None

    try:
        url = f"{LLM_PROXY_API_BASE_URL.rstrip('/')}{LLM_PROXY_BUDGET_ENDPOINT}"

        headers = {
            LLM_PROXY_BUDGET_AUTH_HEADER: LLM_PROXY_API_KEY,
            "accept": "application/json",
        }

        if LLM_PROXY_BUDGET_HTTP_METHOD == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(
                url,
                headers=headers,
                json={LLM_PROXY_BUDGET_QUERY_PARAM: user_id},
                timeout=LLM_PROXY_BUDGET_TIMEOUT,
            )
        else:
            response = requests.get(
                url,
                headers=headers,
                params={LLM_PROXY_BUDGET_QUERY_PARAM: user_id},
                timeout=LLM_PROXY_BUDGET_TIMEOUT,
            )

        if response.status_code == 200:
            return response.json()
        else:
            log.error(
                f"Failed to fetch budget info from LLM proxy: {response.status_code} - {response.text}"
            )
            return None

    except Exception as e:
        log.error(f"Error fetching budget info from LLM proxy: {e}")
        return None


def _check_budget_exceeded(data: dict) -> bool:
    """Check if the user has exceeded their budget based on the proxy response.

    Returns True if the user is over budget, False otherwise.
    If max_budget is None/null, the user has no budget limit -> not exceeded.
    If budget_reset_at is set and is in the past, LiteLLM should have already
    reset the spend. We trust the current spend value from the proxy.
    """
    spend = _resolve_json_path(data, LLM_PROXY_BUDGET_JSON_PATH_SPEND)
    max_budget = _resolve_json_path(data, LLM_PROXY_BUDGET_JSON_PATH_MAX_BUDGET)
    budget_reset_at_str = _resolve_json_path(data, LLM_PROXY_BUDGET_JSON_PATH_BUDGET_RESET_AT)

    if max_budget is None:
        return False

    try:
        max_budget = float(max_budget)
    except (TypeError, ValueError):
        log.warning(f"Invalid max_budget value: {max_budget}")
        return False

    if spend is None:
        return False

    try:
        spend = float(spend)
    except (TypeError, ValueError):
        log.warning(f"Invalid spend value: {spend}")
        return False

    # If budget_reset_at is in the past, LiteLLM should have reset the spend.
    # However, if LiteLLM hasn't reset it yet (race condition), we give the
    # user the benefit of the doubt and don't block them.
    if budget_reset_at_str:
        try:
            reset_at = datetime.fromisoformat(budget_reset_at_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if reset_at <= now:
                log.debug(
                    f"Budget reset_at ({budget_reset_at_str}) is in the past, "
                    f"spend may not be reset yet — allowing request"
                )
                return False
        except (TypeError, ValueError) as e:
            log.warning(f"Could not parse budget_reset_at '{budget_reset_at_str}': {e}")

    if spend >= max_budget:
        log.info(
            f"User budget exceeded: spend={spend}, max_budget={max_budget}"
        )
        return True

    return False


def check_user_budget(user_id: str) -> bool:
    """Check if a user has exceeded their LLM proxy budget.

    Uses an in-memory cache to avoid hitting the proxy on every request.

    Returns True if the user is over budget, False otherwise.
    On errors, returns False (fail-open: don't block users due to proxy issues).
    """
    if not LLM_PROXY_BUDGET_ENFORCE:
        return False

    if not user_id:
        return False

    # Check cache
    now = time.time()
    if user_id in _budget_cache:
        cached_time, cached_result = _budget_cache[user_id]
        if now - cached_time < LLM_PROXY_BUDGET_CACHE_TTL:
            return cached_result

    try:
        data = _fetch_user_budget_info(user_id)
        if data is None:
            # Fail-open: if we can't reach the proxy, don't block the user
            return False

        is_over = _check_budget_exceeded(data)
        _budget_cache[user_id] = (now, is_over)
        return is_over

    except Exception as e:
        log.error(f"Unexpected error checking user budget: {e}")
        return False


async def enforce_budget(user_dict: Optional[dict]) -> None:
    """Check user budget and raise an exception if exceeded.

    This is the main entry point called from the middleware.
    It raises an Exception with the configured message if the user is over budget.
    If budget enforcement is disabled or the user has no budget, this is a no-op.
    """
    if not LLM_PROXY_BUDGET_ENFORCE:
        return

    if not user_dict:
        return

    # Skip admins unless explicitly configured to block them
    if not LLM_PROXY_BUDGET_BLOCK_ADMINS:
        user_role = user_dict.get("role", "")
        if user_role == "admin":
            return

    user_id = user_dict.get("id")
    if not user_id:
        return

    try:
        is_over = await asyncio.to_thread(check_user_budget, user_id)
    except Exception as e:
        log.error(f"Error in budget enforcement: {e}")
        return

    if is_over:
        raise Exception(LLM_PROXY_BUDGET_EXCEEDED_MSG)
