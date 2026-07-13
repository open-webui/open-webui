"""Behavioral tests for the streaming per-chunk idle timeout (aiohttp sock_read).

sock_read must abort a stalled stream, leave an active stream untouched, and be
a no-op when unset. Self-contained (only aiohttp + pytest).
"""

import asyncio

import aiohttp
from aiohttp import web
from aiohttp.test_utils import unused_port

# Outlasts the longest client timeout used against it; short so cleanup doesn't block.
_STALL_SECONDS = 3


async def _stall_handler(request):
    """Emit one chunk, then hang — simulates a stalled upstream."""
    resp = web.StreamResponse()
    resp.headers['Content-Type'] = 'text/event-stream'
    await resp.prepare(request)
    await resp.write(b'data: chunk-0\n\n')
    await asyncio.sleep(_STALL_SECONDS)
    return resp


async def _steady_handler(request):
    """Emit 8 chunks 0.5s apart — active stream, never idle longer than 0.5s."""
    resp = web.StreamResponse()
    resp.headers['Content-Type'] = 'text/event-stream'
    await resp.prepare(request)
    for i in range(8):
        await resp.write(f'data: chunk-{i}\n\n'.encode())
        await asyncio.sleep(0.5)
    await resp.write_eof()
    return resp


async def _serve():
    port = unused_port()
    app = web.Application()
    app.add_routes(
        [
            web.get('/stall', _stall_handler),
            web.get('/steady', _steady_handler),
        ]
    )
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', port)
    await site.start()
    return runner, f'http://127.0.0.1:{port}'


async def _run_stall_trips_on_idle():
    runner, base = await _serve()
    try:
        timeout = aiohttp.ClientTimeout(total=10, sock_read=1)
        loop = asyncio.get_event_loop()
        start = loop.time()
        got_first_chunk = False
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{base}/stall', timeout=timeout) as resp:
                async for _ in resp.content:
                    got_first_chunk = True
        return None, loop.time() - start, got_first_chunk
    except asyncio.TimeoutError:
        return 'timeout', loop.time() - start, got_first_chunk
    finally:
        await runner.cleanup()


async def _run_steady_completes():
    runner, base = await _serve()
    try:
        timeout = aiohttp.ClientTimeout(total=10, sock_read=1)
        chunks = 0
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{base}/steady', timeout=timeout) as resp:
                async for line in resp.content:
                    if line.strip():
                        chunks += 1
        return chunks
    finally:
        await runner.cleanup()


async def _run_unset_ignores_idle():
    runner, base = await _serve()
    try:
        # sock_read=None (unset default): only total trips, not idle.
        timeout = aiohttp.ClientTimeout(total=2, sock_read=None)
        loop = asyncio.get_event_loop()
        start = loop.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{base}/stall', timeout=timeout) as resp:
                async for _ in resp.content:
                    pass
        return None, loop.time() - start
    except asyncio.TimeoutError:
        return 'timeout', loop.time() - start
    finally:
        await runner.cleanup()


def test_stalled_stream_trips_sock_read_before_total():
    kind, elapsed, got_first_chunk = asyncio.run(_run_stall_trips_on_idle())
    assert kind == 'timeout'
    # Tripped by the 1s idle cap, well before the 10s total.
    assert 0.8 <= elapsed <= 5.0, elapsed
    assert got_first_chunk is True


def test_active_stream_is_not_interrupted_by_idle_cap():
    chunks = asyncio.run(_run_steady_completes())
    # Idle gaps (0.5s) never exceed sock_read (1s), so all 8 chunks arrive.
    assert chunks == 8


def test_unset_sock_read_does_not_trip_on_idle():
    kind, elapsed = asyncio.run(_run_unset_ignores_idle())
    # Bounded only by total (2s), not idle.
    assert kind == 'timeout'
    assert elapsed >= 1.8, elapsed
