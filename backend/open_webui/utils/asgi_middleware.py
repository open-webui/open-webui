"""
Pure-ASGI replacement for the project's previous
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

All of the app's own per-request concerns live in a single layer: each
extra layer costs a coroutine hop per request, and each `send` wrapper
runs per ASGI message, which on a streamed response means per chunk.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import parse_qs, urlencode

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from open_webui.env import CUSTOM_API_KEY_HEADER
from open_webui.internal.db import ScopedSession
from open_webui.utils.auth import get_http_authorization_cred
from open_webui.utils.security_headers import set_security_headers
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger(__name__)


class WebUIMiddleware:
    """Open WebUI's own per-request handling, in one ASGI layer:

    * reject malformed `/ws/socket.io` upgrade requests
    * stash the bearer/cookie/API-key credential on `request.state.token`
    * stamp `X-Process-Time` and the configured security headers
    * serve the legacy `/watch` and `?shared=` redirects
    * commit and release the thread-local sync `ScopedSession`

    Routes that depend on `get_verified_user` etc. read that credential.
    The header used for API-key transport is controlled by the
    ``CUSTOM_API_KEY_HEADER`` environment variable (default ``x-api-key``).
    This is useful when Open WebUI sits behind a reverse proxy that
    consumes the ``Authorization`` header for its own authentication —
    set the env var to a unique header (e.g. ``X-OpenWebUI-Key``) so the
    middleware checks that instead and avoids the 401 short-circuit.

    Most requests now use the async session; the sync ScopedSession is
    only touched by startup, healthchecks, and a handful of legacy
    helpers (notably the pgvector / opengauss vector-DB clients). It is
    handled here so that PostgreSQL connections do not accumulate as
    "idle in transaction" and so that any pending sync work made inside
    the request is durably persisted.

    Sync session failure semantics
    ------------------------------
    * Downstream raised → roll back any pending sync work, release the
      connection, and re-raise so the outer exception middleware can
      turn it into an error response. We never commit work on a
      request that did not complete successfully.
    * Downstream returned → commit pending sync work; on commit
      failure, log loudly, roll back, and re-raise. Note that in pure
      ASGI the response messages have already been emitted by the
      time `await self.app(...)` returns, so a commit failure cannot
      retroactively change what the client sees on the wire — but
      re-raising still surfaces the error in logs and to ASGI servers
      that expose it. We deliberately do not buffer the response to
      gate it on commit success, because that would defeat streaming
      responses (chat completions, SSE) which are core to the app.

    For request paths where commit-before-send is required, manage the
    sync session explicitly inside the handler instead of relying on
    this middleware.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        # Headers derive only from env vars, which are static for the process
        # lifetime — compute them once instead of per response.
        self._security_headers = list(set_security_headers().items())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Guarded first, so as before this 400 carries no X-Process-Time or security headers.
        if _is_invalid_websocket_upgrade(scope):
            response = JSONResponse(status_code=400, content={'detail': 'Invalid WebSocket upgrade request'})
            await response(scope, receive, send)
            return

        start_time = time.monotonic()
        request = Request(scope)

        token = get_http_authorization_cred(request.headers.get('Authorization'))
        if token is None:
            cookie_token = request.cookies.get('token')
            if cookie_token:
                token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=cookie_token)
        if token is None:
            api_key = request.headers.get(CUSTOM_API_KEY_HEADER)
            if api_key:
                token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=api_key)

        request.state.token = token

        async def send_with_headers(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = MutableHeaders(scope=message)
                headers['X-Process-Time'] = f'{time.monotonic() - start_time:.6f}'
                for key, value in self._security_headers:
                    headers[key] = value
            await send(message)

        redirect_url = _legacy_redirect_url(scope)
        if redirect_url:
            response = RedirectResponse(url=redirect_url)
            await response(scope, receive, send_with_headers)
            return

        # Keep health probes independent from sync session commit/remove so DB
        # pressure cannot delay or fail probe responses.
        if scope.get('path', '') in {'/health', '/ready', '/health/db'}:
            await self.app(scope, receive, send_with_headers)
            return

        try:
            await self.app(scope, receive, send_with_headers)
        except BaseException:
            # Downstream did not complete successfully. Roll back any
            # pending sync writes, release the connection, and let the
            # exception propagate.
            if ScopedSession.registry.has():
                try:
                    ScopedSession.rollback()
                except Exception:
                    log.exception('WebUIMiddleware: rollback failed after downstream error')
                finally:
                    ScopedSession.remove()
            raise

        # Nothing in this request touched the sync session: committing would
        # only instantiate one to run an empty transaction.
        if not ScopedSession.registry.has():
            return

        # Downstream completed. Commit pending sync work.
        try:
            ScopedSession.commit()
        except Exception:
            log.exception('WebUIMiddleware: post-request commit failed; response was already sent to client')
            try:
                ScopedSession.rollback()
            except Exception:
                log.exception('WebUIMiddleware: rollback failed after commit failure')
            raise
        finally:
            # CRITICAL: remove() returns the connection to the pool.
            # Without this, connections remain "checked out" and
            # accumulate as "idle in transaction" in PostgreSQL.
            ScopedSession.remove()


def _is_invalid_websocket_upgrade(scope: Scope) -> bool:
    """Whether this is an HTTP request to `/ws/socket.io` claiming
    `transport=websocket` but lacking the proper `Upgrade`/`Connection`
    headers, which engineio mishandles.

    https://github.com/miguelgrinberg/python-engineio/issues/367
    """
    if '/ws/socket.io' not in scope.get('path', ''):
        return False

    query_string = scope.get('query_string', b'').decode('latin-1', errors='replace')
    if parse_qs(query_string).get('transport', [''])[0] != 'websocket':
        return False

    headers = _scope_headers(scope)
    upgrade = headers.get('upgrade', '').lower()
    connection_tokens = [token.strip() for token in headers.get('connection', '').lower().split(',')]
    return upgrade != 'websocket' or 'upgrade' not in connection_tokens


def _legacy_redirect_url(scope: Scope) -> str | None:
    """Target for the two legacy entry-points that map onto the SPA's own
    routes:

    * ``GET /watch?v=ID`` (YouTube) → ``/?youtube=ID``
    * ``GET /?shared=…`` (PWA share-target) → ``/?youtube=…`` /
      ``/?load-url=…`` / ``/?q=…``

    Returns None for anything else.
    """
    if scope.get('method', '').upper() != 'GET':
        return None

    path = scope.get('path', '')
    raw_query = scope.get('query_string', b'')
    # Skip the decode + parse_qs work for every other GET. (A false positive on
    # the substring check just falls through to the full parse below.)
    if not (path.endswith('/watch') or b'shared' in raw_query):
        return None

    query_params = parse_qs(raw_query.decode('latin-1', errors='replace'))
    redirect_params: dict[str, str] = {}

    if path.endswith('/watch') and query_params.get('v'):
        redirect_params['youtube'] = query_params['v'][0]

    shared_text = (query_params.get('shared') or [''])[0]
    if shared_text:
        url_match = re.match(r'https://\S+', shared_text)
        if url_match:
            # Local import: youtube loader pulls heavy deps and is only needed
            # when a share-target actually contains a YouTube URL.
            from open_webui.retrieval.loaders.youtube import _parse_video_id

            youtube_video_id = _parse_video_id(url_match[0])
            if youtube_video_id:
                redirect_params['youtube'] = youtube_video_id
            else:
                redirect_params['load-url'] = url_match[0]
        else:
            redirect_params['q'] = shared_text

    return f'/?{urlencode(redirect_params)}' if redirect_params else None


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
