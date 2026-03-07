import time
from typing import Optional

from open_webui.env import MCP_TOOL_SPECS_CACHE_TTL

# Cache: {(scope_id, server_id): {"tool_specs": [...], "cached_at": float}}
# scope_id is user_id when per_user=True, or "__global__" when per_user=False
_cache: dict[tuple[str, str], dict] = {}

_GLOBAL_SCOPE = "__global__"


def _make_key(user_id: str, server_id: str, per_user: bool) -> tuple[str, str]:
    return (user_id if per_user else _GLOBAL_SCOPE, server_id)


def get_cached_specs(
    user_id: str, server_id: str, per_user: bool = True
) -> Optional[list[dict]]:
    """Return cached tool specs if fresh, else None."""
    key = _make_key(user_id, server_id, per_user)
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.monotonic() - entry["cached_at"] > MCP_TOOL_SPECS_CACHE_TTL:
        _cache.pop(key, None)
        return None
    return entry["tool_specs"]


def set_cached_specs(
    user_id: str, server_id: str, tool_specs: list[dict], per_user: bool = True
) -> None:
    """Store tool specs in the cache."""
    key = _make_key(user_id, server_id, per_user)
    _cache[key] = {
        "tool_specs": tool_specs,
        "cached_at": time.monotonic(),
    }


def invalidate_all() -> None:
    """Clear the entire MCP tool spec cache."""
    _cache.clear()
