"""Shared aiohttp ClientSession pool.

Instead of creating a new ClientSession (and TCPConnector) per request,
callers acquire a long-lived session from this module.  The pool manages
a single TCPConnector with configurable limits, enabling TCP/SSL connection
reuse, shared DNS cache, and bounded concurrency.

All pool parameters are configurable via environment variables:
    - AIOHTTP_POOL_CONNECTIONS (default 100) — max total connections
    - AIOHTTP_POOL_CONNECTIONS_PER_HOST (default 30) — per-host limit
    - AIOHTTP_POOL_DNS_TTL (default 300) — DNS cache TTL in seconds

Usage:
    from open_webui.utils.session_pool import get_session, cleanup_response

    session = await get_session()
    r = await session.request(...)
    # When done with the *response* (not the session):
    await cleanup_response(r)

IMPORTANT: Callers must NOT close the shared session.  Only the response
needs cleanup.  The session is closed once during application shutdown
via ``close_session()``.
"""

import asyncio
import logging
from typing import Optional

import aiohttp

from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_POOL_CONNECTIONS,
    AIOHTTP_POOL_CONNECTIONS_PER_HOST,
    AIOHTTP_POOL_DNS_TTL,
)

log = logging.getLogger(__name__)

_session: Optional[aiohttp.ClientSession] = None


async def get_session() -> aiohttp.ClientSession:
    """Return the shared aiohttp ClientSession, creating it lazily."""
    global _session
    if _session is None or _session.closed:
        connector_kwargs = {
            'ttl_dns_cache': AIOHTTP_POOL_DNS_TTL,
            'enable_cleanup_closed': True,
        }
        if AIOHTTP_POOL_CONNECTIONS is not None:
            connector_kwargs['limit'] = AIOHTTP_POOL_CONNECTIONS
        else:
            connector_kwargs['limit'] = 0  # aiohttp: 0 = unlimited
        if AIOHTTP_POOL_CONNECTIONS_PER_HOST is not None:
            connector_kwargs['limit_per_host'] = AIOHTTP_POOL_CONNECTIONS_PER_HOST
        else:
            connector_kwargs['limit_per_host'] = 0  # aiohttp: 0 = unlimited
        connector = aiohttp.TCPConnector(**connector_kwargs)
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        _session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=True,
        )
        log.info(
            'Created shared aiohttp session pool (limit=%s, per_host=%s, dns_ttl=%d)',
            AIOHTTP_POOL_CONNECTIONS or 'unlimited',
            AIOHTTP_POOL_CONNECTIONS_PER_HOST or 'unlimited',
            AIOHTTP_POOL_DNS_TTL,
        )
    return _session


async def close_session():
    """Close the shared session.  Called during application shutdown."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        log.info('Closed shared aiohttp session pool')
        _session = None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession] = None,
):
    """Release and close an aiohttp response, optionally closing the session.

    When using the shared pool, ``session`` should be ``None`` (the pool
    session is never closed per-request).  When a caller creates its own
    one-off session, pass it here to close it after the response.
    """
    if response:
        if not response.closed:
            # aiohttp 3.9+ made ClientResponse.close() synchronous (returns None).
            # Older versions returned a coroutine.  Handle both gracefully.
            result = response.close()
            if result is not None:
                await result
    if session:
        if not session.closed:
            result = session.close()
            if result is not None:
                await result


async def stream_wrapper(response, session=None, content_handler=None):
    """Wrap a stream to ensure cleanup happens even if streaming is interrupted.

    This is more reliable than BackgroundTask which may not run if the client
    disconnects.  When using the shared pool, ``session`` should be ``None``.
    """
    try:
        stream = content_handler(response.content) if content_handler else response.content
        async for chunk in stream:
            yield chunk
    finally:
        await cleanup_response(response, session)


async def prefetch_stream_bytes(
    response: aiohttp.ClientResponse,
    buffer_bytes: int = 2048,
    timeout_ms: int = 500,
) -> list[bytes]:
    """Read initial bytes from a streaming response with a combined byte/time budget.

    Used for the failover "buffer window" — we want to catch an upstream that
    200s-then-dies before we've returned a StreamingResponse to the client.

    Returns the list of raw byte chunks read. Exits early once either
    ``buffer_bytes`` are buffered or ``timeout_ms`` elapses (whichever first),
    so a slow-but-alive provider doesn't block failover indefinitely.

    Raises aiohttp.ClientError / OSError on network failure — caller is expected
    to map that to a retryable-provider signal.
    """
    chunks: list[bytes] = []
    bytes_so_far = 0
    deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000)

    while bytes_so_far < buffer_bytes:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            chunk = await asyncio.wait_for(response.content.readany(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        if not chunk:
            break  # EOF — upstream closed before the window elapsed
        chunks.append(chunk)
        bytes_so_far += len(chunk)

    return chunks


async def prefetched_stream_wrapper(
    response,
    prefetched_chunks: list[bytes],
    session=None,
    content_handler=None,
    leading_events: Optional[list[bytes]] = None,
):
    """Like ``stream_wrapper`` but prepends optional leading events and already-read chunks.

    Used in tandem with ``prefetch_stream_bytes``. ``content_handler`` is only
    applied to the *continuation* of the stream (the bytes still in
    ``response.content``); the prefetched bytes are emitted as-is because
    they were already removed from the underlying StreamReader.
    """
    try:
        if leading_events:
            for event in leading_events:
                yield event
        for chunk in prefetched_chunks:
            yield chunk
        stream = content_handler(response.content) if content_handler else response.content
        async for chunk in stream:
            yield chunk
    finally:
        await cleanup_response(response, session)
