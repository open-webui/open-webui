"""
Pure-ASGI replacements for the project's previous
`@app.middleware('http')` / `BaseHTTPMiddleware` middlewares.

Why this matters
----------------
Starlette's `BaseHTTPMiddleware` (which `@app.middleware('http')` is
sugar for) runs the downstream app inside an `anyio` task group. When
the wrapper exits — for any reason: response complete, client
disconnect, an outer middleware bailing out — the task group cancels
the inner task. That `CancelledError` then propagates into whatever
the inner task was doing, including in-flight DB queries, embedding
calls and disk I/O.

In Open WebUI this surfaces as:

* SQLAlchemy logging multi-page `NotImplementedError:
  terminate_force_close()` tracebacks at ERROR every time a request is
  cancelled mid-DB-call (the aiosqlite connector cleanup path).
* Spurious cancellations cascading through the four stacked
  `@app.middleware('http')` wrappers.

Pure ASGI middleware does not introduce a cancel scope around the
downstream app, so client disconnects propagate the way ASGI was
designed to (via `receive()` returning `http.disconnect`) instead of
being injected as `CancelledError` into arbitrary `await` points.

Reference: https://www.starlette.io/middleware/#limitations
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Awaitable, Callable, MutableMapping
from urllib.parse import parse_qs, urlencode

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from open_webui.internal.db import ScopedSession
from open_webui.utils.auth import get_http_authorization_cred

log = logging.getLogger(__name__)


class CommitSessionMiddleware:
    """Commit and release the thread-local sync `ScopedSession` after each
    HTTP request.

    Most requests now use the async session; the sync ScopedSession is
    only touched by startup, healthchecks, and a handful of legacy
    helpers. The middleware is still required for those paths so that
    PostgreSQL connections do not accumulate as "idle in transaction"
    and so that any pending sync work is flushed before the response
    is finalised.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        finally:
            # Always release the connection back to the pool. Commit
            # any pending work; if commit itself fails, still remove
            # the session so the connection is not leaked.
            try:
                ScopedSession.commit()
            except Exception:
                ScopedSession.rollback()
                raise
            finally:
                ScopedSession.remove()


class AuthTokenMiddleware:
    """Extract the bearer/cookie/x-api-key credential and stash it on
    `request.state.token`.

    Routes that depend on `get_verified_user` etc. read this state.
    Also exposes `request.state.enable_api_keys` (snapshotted at request
    entry from runtime config) and stamps an `X-Process-Time` response
    header.
    """

    def __init__(self, app: ASGIApp, *, fastapi_app) -> None:
        self.app = app
        self._fastapi_app = fastapi_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        start_time = time.monotonic()
        request = Request(scope)

        token = get_http_authorization_cred(request.headers.get('Authorization'))
        if token is None:
            cookie_token = request.cookies.get('token')
            if cookie_token:
                token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=cookie_token)
        if token is None:
            api_key = request.headers.get('x-api-key')
            if api_key:
                token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=api_key)

        request.state.token = token
        request.state.enable_api_keys = self._fastapi_app.state.config.ENABLE_API_KEYS

        async def send_with_timing(message: Message) -> None:
            if message['type'] == 'http.response.start':
                process_time = int(time.monotonic() - start_time)
                headers = MutableHeaders(scope=message)
                headers['X-Process-Time'] = str(process_time)
            await send(message)

        await self.app(scope, receive, send_with_timing)


class WebsocketUpgradeGuardMiddleware:
    """Reject HTTP requests to `/ws/socket.io` that claim
    `transport=websocket` but lack the proper `Upgrade`/`Connection`
    headers.

    Works around https://github.com/miguelgrinberg/python-engineio/issues/367
    where engineio mishandles such requests.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        path = scope.get('path', '')
        if '/ws/socket.io' in path:
            query_string = scope.get('query_string', b'').decode('latin-1', errors='replace')
            query_params = parse_qs(query_string)
            if query_params.get('transport', [''])[0] == 'websocket':
                headers = _scope_headers(scope)
                upgrade = headers.get('upgrade', '').lower()
                connection_tokens = [
                    token.strip() for token in headers.get('connection', '').lower().split(',')
                ]
                if upgrade != 'websocket' or 'upgrade' not in connection_tokens:
                    response = JSONResponse(
                        status_code=400,
                        content={'detail': 'Invalid WebSocket upgrade request'},
                    )
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)


class RedirectMiddleware:
    """Rewrites a couple of legacy entry-points to the SPA's own routes:

    * ``GET /watch?v=ID`` (YouTube) → ``/?youtube=ID``
    * ``GET /?shared=…`` (PWA share-target) → ``/?youtube=…`` /
      ``/?load-url=…`` / ``/?q=…``
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http' or scope.get('method', '').upper() != 'GET':
            await self.app(scope, receive, send)
            return

        path = scope.get('path', '')
        query_string = scope.get('query_string', b'').decode('latin-1', errors='replace')
        query_params = parse_qs(query_string)

        redirect_params: dict[str, str] = {}
        if path.endswith('/watch') and 'v' in query_params and query_params['v']:
            redirect_params['youtube'] = query_params['v'][0]

        if 'shared' in query_params and query_params['shared']:
            text = query_params['shared'][0]
            if text:
                url_match = re.match(r'https://\S+', text)
                if url_match:
                    # Local import: youtube loader pulls heavy deps and is
                    # only needed when a share-target actually contains a
                    # YouTube URL.
                    from open_webui.retrieval.loaders.youtube import _parse_video_id

                    youtube_video_id = _parse_video_id(url_match[0])
                    if youtube_video_id:
                        redirect_params['youtube'] = youtube_video_id
                    else:
                        redirect_params['load-url'] = url_match[0]
                else:
                    redirect_params['q'] = text

        if redirect_params:
            redirect_url = f'/?{urlencode(redirect_params)}'
            response = RedirectResponse(url=redirect_url)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _scope_headers(scope: Scope) -> dict[str, str]:
    """Return ASGI scope headers as a lower-cased str→str dict.

    ASGI delivers headers as a list of (bytes, bytes) pairs. For
    convenience, fold duplicate keys with comma-joining (matching
    HTTP/1.1 semantics).
    """
    decoded: dict[str, str] = {}
    for raw_key, raw_value in scope.get('headers', []):
        key = raw_key.decode('latin-1').lower()
        value = raw_value.decode('latin-1')
        if key in decoded:
            decoded[key] = f'{decoded[key]}, {value}'
        else:
            decoded[key] = value
    return decoded
