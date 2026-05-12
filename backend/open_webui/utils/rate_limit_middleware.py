"""Per-user, per-endpoint-class rate limiting middleware.

This module implements a pure-ASGI middleware that enforces rate limits
against four broad endpoint classes (``chat``, ``embeddings``,
``uploads``, ``admin``) using the async Redis client already configured
on ``app.state.redis``. It follows the same hand-written ASGI
conventions as ``open_webui.utils.asgi_middleware`` — deliberately not
``BaseHTTPMiddleware`` — so that client disconnects and streaming
responses are not affected.

The feature is **disabled by default** (``ENABLE_RATE_LIMITING=False``).
When enabled, the middleware is a no-op for requests whose path is not
classified, for health/readiness probes, for WebSocket upgrades, and
for static assets. Classified requests consume a token from a
sliding-window log stored in Redis; exceeded limits respond ``429`` with
standard ``RateLimit-*`` / ``Retry-After`` headers.

Design
------
* **Identity** is resolved from ``request.state.token`` (populated by
  :class:`AuthTokenMiddleware`): JWT ``id`` claim first, then a SHA-256
  prefix of the API key, then the client IP as a last-resort bucket.
* **Endpoint classification** is a compiled regex table at module
  import time. Admin-class paths require a write HTTP method. Unmatched
  paths skip the middleware entirely.
* **Algorithm** is a sliding-window log implemented as a single Redis
  Lua script on a sorted set — one ``EVALSHA`` per limited request.
  Sorted-set size is bounded by ``limit + 1`` entries per active
  ``(identity, class)`` tuple and aggressively trimmed with
  ``ZREMRANGEBYSCORE``.
* **Fail-open** on Redis errors / timeouts (configurable) so a Redis
  incident cannot take the app offline.

The middleware intentionally performs **no database lookups** in the
hot path. Revocation and user-existence checks happen later in
``get_current_user``; this keeps the rate limiter cheap even under
sustained traffic.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid

from open_webui.env import REDIS_KEY_PREFIX
from open_webui.utils.auth import decode_token
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Endpoint classification
# ---------------------------------------------------------------------------

# Paths that bypass the middleware regardless of classification.
# Health probes, readiness checks, WebSocket upgrades, and static assets
# must never be delayed or blocked by rate limiting.
_SKIP_PATH_PREFIXES: tuple[str, ...] = (
    '/health',
    '/ready',
    '/ws/',
    '/static/',
    '/assets/',
    '/cache/',
    '/_app/',
)

# Exact path matches in addition to the prefix list above.
_SKIP_PATHS: frozenset[str] = frozenset({'/', '/manifest.json', '/favicon.ico', '/robots.txt', '/opensearch.xml'})

# HTTP methods considered "writes" for the admin class. GET/HEAD/OPTIONS
# are deliberately excluded so the admin UI can refresh dashboards
# without burning the admin bucket.
_ADMIN_WRITE_METHODS: frozenset[str] = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})


# Ordered list of (compiled regex, class name, optional method filter).
# First match wins; order the specific before the general.
_ROUTE_TABLE: tuple[tuple[re.Pattern[str], str, frozenset[str] | None], ...] = (
    (re.compile(r'^/api(?:/v1)?/chat/completions(?:/|$)'), 'chat', None),
    (re.compile(r'^/ollama/api/chat(?:/|$)'), 'chat', None),
    (re.compile(r'^/ollama/api/generate(?:/|$)'), 'chat', None),
    (re.compile(r'^/openai/chat/completions(?:/|$)'), 'chat', None),
    (re.compile(r'^/api(?:/v1)?/embeddings(?:/|$)'), 'embeddings', None),
    (re.compile(r'^/api/v1/retrieval/process(?:/|$)'), 'uploads', None),
    (re.compile(r'^/api/v1/files(?:/|$)'), 'uploads', None),
    (re.compile(r'^/api/v1/knowledge/[^/]+/file/add(?:/|$)'), 'uploads', None),
    (re.compile(r'^/api/v1/configs(?:/|$)'), 'admin', _ADMIN_WRITE_METHODS),
    (re.compile(r'^/api/v1/models(?:/|$)'), 'admin', _ADMIN_WRITE_METHODS),
    (re.compile(r'^/api/v1/groups(?:/|$)'), 'admin', _ADMIN_WRITE_METHODS),
    (re.compile(r'^/api/v1/users(?:/|$)'), 'admin', _ADMIN_WRITE_METHODS),
)


def classify(path: str, method: str) -> str | None:
    """Return the endpoint class name for a request, or None to skip.

    Path prefixes in ``_SKIP_PATH_PREFIXES`` and exact paths in
    ``_SKIP_PATHS`` always return ``None``. Unmatched paths also return
    ``None`` — the middleware only rate-limits classified traffic.
    """
    if path in _SKIP_PATHS:
        return None
    for prefix in _SKIP_PATH_PREFIXES:
        if path.startswith(prefix):
            return None
    for pattern, class_name, methods in _ROUTE_TABLE:
        if pattern.match(path):
            if methods is None or method.upper() in methods:
                return class_name
            return None
    return None


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------

_API_KEY_HASH_BYTES = 8  # 16 hex chars; collision space is ample for bucketing.


def _hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[: _API_KEY_HASH_BYTES * 2]


def resolve_identity(scope: Scope, token_credentials: str | None) -> tuple[str, str]:
    """Resolve a stable ``(id_type, id)`` tuple for the requester.

    The order is:

    1. JWT — ``id`` claim from :func:`decode_token`. No DB lookup.
    2. API key (``sk-…``) — SHA-256 prefix of the key.
    3. Anonymous — client IP from the ASGI scope.

    The caller passes the *credentials string* (not the
    :class:`HTTPAuthorizationCredentials` wrapper) so this function
    stays free of FastAPI/Starlette imports and is trivially testable.
    """
    if token_credentials:
        if token_credentials.startswith('sk-'):
            return 'k', _hash_api_key(token_credentials)
        decoded = decode_token(token_credentials)
        if decoded and decoded.get('id'):
            return 'u', str(decoded['id'])

    client = scope.get('client')
    if client and isinstance(client, (list, tuple)) and client:
        return 'i', str(client[0])
    return 'i', 'unknown'


# ---------------------------------------------------------------------------
# Lua script — sliding window log
# ---------------------------------------------------------------------------

# Single-trip atomic check-and-increment.
#
#   KEYS[1] : sorted-set key for (identity, class)
#   ARGV[1] : window in seconds
#   ARGV[2] : limit
#   ARGV[3] : now (milliseconds, server time)
#   ARGV[4] : request id (unique per call)
#
# Returns {limited (0/1), count_after, retry_after_ms}.
_LUA_SLIDING_WINDOW: str = """
local key    = KEYS[1]
local window = tonumber(ARGV[1])
local limit  = tonumber(ARGV[2])
local now    = tonumber(ARGV[3])
local req_id = ARGV[4]
local min    = now - (window * 1000)

redis.call('ZREMRANGEBYSCORE', key, 0, min)
local count = redis.call('ZCARD', key)

if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry_ms = 0
  if oldest[2] then
    retry_ms = (window * 1000) - (now - tonumber(oldest[2]))
    if retry_ms < 0 then retry_ms = 0 end
  end
  return {1, count, retry_ms}
end

redis.call('ZADD', key, now, req_id)
redis.call('EXPIRE', key, window + 1)
return {0, count + 1, 0}
"""


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


# Applied to every Redis round-trip from the hot path. Deliberately short:
# at worst, a single slow Redis call should not stall a request.
REDIS_CALL_TIMEOUT_SECONDS: float = 0.05


class RateLimitMiddleware:
    """Pure-ASGI per-user per-endpoint-class rate limiter.

    Constructor arguments
    ---------------------
    app : ASGIApp
        The downstream ASGI application (provided by Starlette).
    fastapi_app : FastAPI
        Reference to the outer FastAPI app. Used at request time to
        read ``state.redis`` and ``state.config.*`` so runtime config
        changes are observed without a restart.
    """

    def __init__(self, app: ASGIApp, *, fastapi_app) -> None:
        self.app = app
        self._fastapi_app = fastapi_app
        self._script_sha: str | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        config = getattr(self._fastapi_app.state, 'config', None)
        if config is None or not getattr(config, 'ENABLE_RATE_LIMITING', False):
            await self.app(scope, receive, send)
            return

        path = scope.get('path', '') or ''
        method = (scope.get('method') or 'GET').upper()
        class_name = classify(path, method)
        if class_name is None:
            await self.app(scope, receive, send)
            return

        limit, window = _class_config(config, class_name)
        if limit <= 0 or window <= 0:
            # Per-class disable — treat any non-positive value as "off".
            await self.app(scope, receive, send)
            return

        # Resolve identity without touching the DB. Reading via
        # Request(scope) mirrors AuthTokenMiddleware and guarantees the
        # same State object that earlier middleware wrote to.
        request = Request(scope)
        token_state = getattr(request.state, 'token', None)
        credentials = getattr(token_state, 'credentials', None) if token_state is not None else None
        id_type, identity = resolve_identity(scope, credentials)
        redis_key = f'{REDIS_KEY_PREFIX}:rl:{class_name}:{id_type}:{identity}'

        redis_client = getattr(self._fastapi_app.state, 'redis', None)
        allowed, count, retry_after_ms = await self._check(redis_client, redis_key, window, limit)

        remaining = max(0, limit - count)
        reset_seconds = max(1, int(retry_after_ms / 1000)) if retry_after_ms > 0 else window

        if not allowed:
            await _send_429(send, class_name, limit, remaining, reset_seconds)
            return

        # Inject the standard RateLimit-* headers into the downstream response.
        async def send_with_headers(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                headers.append((b'ratelimit-limit', str(limit).encode('latin-1')))
                headers.append((b'ratelimit-remaining', str(remaining).encode('latin-1')))
                headers.append((b'ratelimit-reset', str(reset_seconds).encode('latin-1')))
                message['headers'] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)

    async def _check(
        self,
        redis_client,
        redis_key: str,
        window: int,
        limit: int,
    ) -> tuple[bool, int, int]:
        """Run the sliding-window Lua script against Redis.

        Returns ``(allowed, count_after, retry_after_ms)``. On any
        failure — Redis unavailable, timeout, protocol error — the
        result depends on ``RATE_LIMITING_FAIL_OPEN``:

        * fail-open (default): return ``(True, 0, 0)`` so the request
          is allowed through.
        * fail-closed: return ``(False, limit, window * 1000)`` so the
          request is rejected.
        """
        if redis_client is None:
            return self._on_redis_error('redis client not configured')

        now_ms = int(time.time() * 1000)
        request_id = uuid.uuid4().hex
        args = (window, limit, now_ms, request_id)

        try:
            if self._script_sha is None:
                self._script_sha = await asyncio.wait_for(
                    redis_client.script_load(_LUA_SLIDING_WINDOW),
                    timeout=REDIS_CALL_TIMEOUT_SECONDS,
                )
            try:
                result = await asyncio.wait_for(
                    redis_client.evalsha(self._script_sha, 1, redis_key, *args),
                    timeout=REDIS_CALL_TIMEOUT_SECONDS,
                )
            except Exception as e:
                # NOSCRIPT — reload and retry once with EVAL.
                if 'NOSCRIPT' in str(e).upper():
                    result = await asyncio.wait_for(
                        redis_client.eval(_LUA_SLIDING_WINDOW, 1, redis_key, *args),
                        timeout=REDIS_CALL_TIMEOUT_SECONDS,
                    )
                    # Re-cache the SHA for subsequent calls.
                    try:
                        self._script_sha = await asyncio.wait_for(
                            redis_client.script_load(_LUA_SLIDING_WINDOW),
                            timeout=REDIS_CALL_TIMEOUT_SECONDS,
                        )
                    except Exception:
                        self._script_sha = None
                else:
                    raise
        except Exception as e:
            return self._on_redis_error(e)

        try:
            limited, count, retry_ms = int(result[0]), int(result[1]), int(result[2])
        except (TypeError, ValueError, IndexError) as e:
            return self._on_redis_error(f'unexpected script result: {e}')

        return (limited == 0, count, retry_ms)

    def _on_redis_error(self, reason) -> tuple[bool, int, int]:
        config = getattr(self._fastapi_app.state, 'config', None)
        fail_open = getattr(config, 'RATE_LIMITING_FAIL_OPEN', True) if config else True
        # DEBUG-level by design: a Redis incident must not produce a log flood.
        log.debug('Rate limiter Redis call failed (%s); fail_open=%s', reason, fail_open)
        if fail_open:
            return True, 0, 0
        return False, 0, 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _class_config(config, class_name: str) -> tuple[int, int]:
    """Return ``(limit, window_seconds)`` for *class_name*.

    Returns ``(0, 0)`` for unknown classes so the middleware short-circuits.
    Any non-integer or negative value is coerced to ``0``, which has the
    same effect as disabling the class.
    """
    mapping = {
        'chat': ('RATE_LIMITING_CHAT_LIMIT', 'RATE_LIMITING_CHAT_WINDOW'),
        'embeddings': ('RATE_LIMITING_EMBEDDINGS_LIMIT', 'RATE_LIMITING_EMBEDDINGS_WINDOW'),
        'uploads': ('RATE_LIMITING_UPLOADS_LIMIT', 'RATE_LIMITING_UPLOADS_WINDOW'),
        'admin': ('RATE_LIMITING_ADMIN_LIMIT', 'RATE_LIMITING_ADMIN_WINDOW'),
    }
    names = mapping.get(class_name)
    if names is None:
        return 0, 0
    limit = _coerce_positive_int(getattr(config, names[0], 0))
    window = _coerce_positive_int(getattr(config, names[1], 0))
    return limit, window


def _coerce_positive_int(value) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return 0
    return coerced if coerced > 0 else 0


async def _send_429(send: Send, class_name: str, limit: int, remaining: int, reset_seconds: int) -> None:
    body = json.dumps({'detail': f'Rate limit exceeded for {class_name}', 'class': class_name}).encode('utf-8')
    headers: list[tuple[bytes, bytes]] = [
        (b'content-type', b'application/json'),
        (b'content-length', str(len(body)).encode('latin-1')),
        (b'retry-after', str(reset_seconds).encode('latin-1')),
        (b'ratelimit-limit', str(limit).encode('latin-1')),
        (b'ratelimit-remaining', str(remaining).encode('latin-1')),
        (b'ratelimit-reset', str(reset_seconds).encode('latin-1')),
    ]
    await send({'type': 'http.response.start', 'status': 429, 'headers': headers})
    await send({'type': 'http.response.body', 'body': body})
