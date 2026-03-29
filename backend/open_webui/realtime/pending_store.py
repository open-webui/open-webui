"""Cross-worker pending text message store.

In multi-worker mode, the HTTP POST that triggers text-to-realtime routing
can land on any worker, but the realtime sideband runs on the Socket.IO-
owning worker.  This store uses Redis so any worker can *push* a pending
text message and the sideband worker can *drain* them.

In single-worker mode, a plain in-memory list is used instead.
"""

import json
import logging
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

# ---------------------------------------------------------------------------
# Dual-mode store: Redis list in MW mode, dict of lists in SW mode
# ---------------------------------------------------------------------------

_redis_client = None

if WEBSOCKET_MANAGER == "redis":
    _redis_client = get_redis_connection(
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=get_sentinels_from_env(
            WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT
        ),
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
        async_mode=True,
    )
    log.info("Pending text store: Redis mode")
else:
    _store: dict[str, list[dict]] = {}
    log.info("Pending text store: in-memory mode")

_KEY_PREFIX = f"{REDIS_KEY_PREFIX}:rt:pending_text:"
_NOTIFY_CHANNEL = f"{REDIS_KEY_PREFIX}:rt:pending_notify"
_TTL_SECONDS = 600


async def push_pending_text(session_id: str, message: dict) -> None:
    """Append a pending text message for *session_id*."""
    if _redis_client is not None:
        key = f"{_KEY_PREFIX}{session_id}"
        await _redis_client.rpush(key, json.dumps(message))
        await _redis_client.expire(key, _TTL_SECONDS)
    else:
        _store.setdefault(session_id, []).append(message)


async def drain_pending_texts(session_id: str) -> list[dict]:
    """Atomically drain all pending text messages for *session_id*.

    Returns the messages in FIFO order.  After this call the store is
    empty for that session_id.
    """
    if _redis_client is not None:
        key = f"{_KEY_PREFIX}{session_id}"
        pipe = _redis_client.pipeline()
        pipe.lrange(key, 0, -1)
        pipe.delete(key)
        results = await pipe.execute()
        raw_items = results[0] or []
        messages = []
        for raw in raw_items:
            try:
                messages.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                log.warning("Failed to decode pending text message")
        return messages
    else:
        return _store.pop(session_id, [])


async def cleanup_pending_texts(session_id: str) -> None:
    """Remove any pending texts for a session (e.g. on disconnect)."""
    if _redis_client is not None:
        await _redis_client.delete(f"{_KEY_PREFIX}{session_id}")
    else:
        _store.pop(session_id, None)


async def notify_pending_text(session_id: str) -> None:
    """Notify the sideband worker that pending text is available.
    """
    if _redis_client is not None:
        await _redis_client.publish(_NOTIFY_CHANNEL, session_id)
    else:
        from open_webui.realtime.session_service import session_manager
        session = session_manager.get_session(session_id)
        if (
            session
            and session.is_ready
            and not session.assistant_responding
            and not session.tool_executing
            and session.ws
        ):
            pending = await drain_pending_texts(session_id)
            if pending:
                from open_webui.realtime.sideband import _flush_pending_to_ws
                from open_webui.socket.main import sio
                await _flush_pending_to_ws(
                    session, pending, "immediate_pending", sio=sio
                )
