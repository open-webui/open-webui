import asyncio
import contextlib
import pytest

from open_webui.socket.utils import InMemoryTTLStore
from open_webui.socket import main as socket_main


@pytest.mark.asyncio
async def test_inmemory_ttl_basic_expiry():
    store = InMemoryTTLStore()
    store.setex("key1", 1, "value")
    assert store.get("key1") == "value"
    await asyncio.sleep(1.1)
    assert store.get("key1") is None


@pytest.mark.asyncio
async def test_inmemory_ttl_scan_iter():
    store = InMemoryTTLStore()
    store.setex("sess:a", 5, "foo")
    store.setex("sess:b", 5, "bar")
    store.setex("other", 5, "baz")

    found = []
    async for k in store.scan_iter(match="sess:*"):
        found.append(k)
    assert set(found) == {"sess:a", "sess:b"}
