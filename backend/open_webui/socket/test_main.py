import asyncio
import contextlib
import pytest

from open_webui.socket.utils import InMemoryTTLStore
from open_webui.socket import main as socket_main


@pytest.mark.asyncio
async def test_periodic_session_ttl_cleanup_removes_stale_sessions(monkeypatch):
    """Simulate local mode cleanup removing stale sessions from SESSION_POOL."""

    # Force local mode
    socket_main.WEBSOCKET_MANAGER = "local"

    # Prepare pools
    socket_main.SESSION_POOL = {
        "stale": {"id": 1},
        "active": {"id": 2},
    }
    socket_main.USER_POOL = {1: ["stale"], 2: ["active"]}

    store = InMemoryTTLStore()
    prefix = f"{socket_main.REDIS_KEY_PREFIX}:sid:"
    store.setex(prefix + "active", 30, 1)
    socket_main.SESSION_EXPIRY_POOL = store

    # Mock YDOC cleanup
    async def dummy_remove(_sid):
        return None

    monkeypatch.setattr(
        socket_main.YDOC_MANAGER, "remove_user_from_all_documents", dummy_remove
    )

    # Stop loop after first sleep
    async def limited_sleep(duration):
        if duration == 0:
            return
        raise asyncio.CancelledError

    monkeypatch.setattr(asyncio, "sleep", limited_sleep)

    with contextlib.suppress(asyncio.CancelledError):
        await socket_main.periodic_session_ttl_cleanup()

    assert "stale" not in socket_main.SESSION_POOL
    assert 1 not in socket_main.USER_POOL
    assert "active" in socket_main.SESSION_POOL
