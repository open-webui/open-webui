"""Ephemeral key store for realtime negotiate/start handoff."""


import json
import logging
import time
from typing import Optional

from open_webui.env import (
    REDIS_KEY_PREFIX,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_CLUSTER,
    WEBSOCKET_REDIS_URL,
    WEBSOCKET_SENTINEL_HOSTS,
    WEBSOCKET_SENTINEL_PORT,
)
from open_webui.utils.redis import get_redis_connection, get_sentinels_from_env

log = logging.getLogger(__name__)

EPHEMERAL_KEY_DEFAULT_TTL = 300

if WEBSOCKET_MANAGER == "redis":
    _ephemeral_key_store = get_redis_connection(
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=get_sentinels_from_env(
            WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT
        ),
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
        async_mode=True,
    )
else:
    _ephemeral_key_store: dict = {}


def _ephemeral_key_store_key(call_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}:rt_ephemeral_key:{call_id}"


def _ephemeral_key_expiry(entry: dict) -> float:
    expires_at = float(entry.get("expires_at") or 0)
    if expires_at > 0:
        return expires_at
    return float(entry.get("minted_at", 0)) + EPHEMERAL_KEY_DEFAULT_TTL


def _purge_stale_ephemeral_keys() -> None:
    if not isinstance(_ephemeral_key_store, dict):
        return

    now = time.time()
    stale_keys = [
        key
        for key, value in _ephemeral_key_store.items()
        if _ephemeral_key_expiry(value) <= now
    ]
    for key in stale_keys:
        _ephemeral_key_store.pop(key, None)


async def store_ephemeral_key(call_id: str, value: str, extra: dict = None) -> None:
    """Store a minted ephemeral key keyed by call_id for later sideband use."""
    entry = {"value": value, "minted_at": time.time()}
    if extra:
        entry.update(extra)
    expires_at = _ephemeral_key_expiry(entry)
    if expires_at <= time.time():
        expires_at = time.time() + EPHEMERAL_KEY_DEFAULT_TTL
    entry["expires_at"] = expires_at

    if WEBSOCKET_MANAGER == "redis":
        ttl_seconds = max(1, int(expires_at - time.time()))
        await _ephemeral_key_store.set(
            _ephemeral_key_store_key(call_id),
            json.dumps(entry),
            ex=ttl_seconds,
        )
        return

    _purge_stale_ephemeral_keys()
    _ephemeral_key_store[call_id] = entry


async def pop_ephemeral_key(call_id: str) -> Optional[dict]:
    """Pop and return the full key entry for a call_id, or None."""
    entry = None

    if WEBSOCKET_MANAGER == "redis":
        raw_entry = await _ephemeral_key_store.execute_command(
            "GETDEL", _ephemeral_key_store_key(call_id)
        )
        if raw_entry:
            if isinstance(raw_entry, (bytes, bytearray)):
                raw_entry = raw_entry.decode("utf-8")
            try:
                entry = json.loads(raw_entry)
            except (TypeError, ValueError):
                entry = None
    else:
        _purge_stale_ephemeral_keys()
        entry = _ephemeral_key_store.pop(call_id, None)

    if not isinstance(entry, dict):
        return None

    if _ephemeral_key_expiry(entry) <= time.time():
        return None

    return entry
