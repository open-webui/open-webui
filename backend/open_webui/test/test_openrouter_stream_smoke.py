import asyncio

import pytest


async def _fake_stream():
    await asyncio.sleep(0.05)
    yield "data: first-chunk"
    await asyncio.sleep(0.01)
    yield "data: second-chunk"


def test_stream_smoke_first_chunk_and_clean_end():
    async def _runner():
        stream = _fake_stream()

        first_chunk = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
        assert "first-chunk" in first_chunk

        second_chunk = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
        assert "second-chunk" in second_chunk

        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()

    asyncio.run(_runner())
