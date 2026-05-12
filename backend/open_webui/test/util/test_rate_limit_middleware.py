"""Unit tests for ``open_webui.utils.rate_limit_middleware``.

The middleware is pure ASGI, so the tests drive it through the ASGI
protocol directly (no HTTP client dependency). Redis is mocked with
``AsyncMock`` to match the pattern in ``test_redis.py`` — no new
third-party dependencies are introduced.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from open_webui.utils.rate_limit_middleware import (
    RateLimitMiddleware,
    classify,
    resolve_identity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_state(enabled=True, fail_open=True, **limits) -> SimpleNamespace:
    """Build a fake ``app.state`` object matching what main.py sets up."""
    defaults = {
        'RATE_LIMITING_CHAT_LIMIT': 3,
        'RATE_LIMITING_CHAT_WINDOW': 60,
        'RATE_LIMITING_EMBEDDINGS_LIMIT': 2,
        'RATE_LIMITING_EMBEDDINGS_WINDOW': 60,
        'RATE_LIMITING_UPLOADS_LIMIT': 2,
        'RATE_LIMITING_UPLOADS_WINDOW': 60,
        'RATE_LIMITING_ADMIN_LIMIT': 2,
        'RATE_LIMITING_ADMIN_WINDOW': 60,
    }
    defaults.update(limits)
    config = SimpleNamespace(
        ENABLE_RATE_LIMITING=enabled,
        RATE_LIMITING_FAIL_OPEN=fail_open,
        **defaults,
    )
    return SimpleNamespace(config=config, redis=None)


def _make_scope(path: str = '/api/v1/chat/completions', method: str = 'POST', token: str | None = None) -> dict:
    """Build an ASGI HTTP scope, optionally with a parsed auth token on state.

    ``scope['state']`` must be a plain dict — Starlette's
    ``HTTPConnection.state`` property wraps it into a :class:`State` on
    first access. ``AuthTokenMiddleware`` stores the credentials as
    ``state_dict['token']``, which is exactly what we simulate here.
    """
    state_dict: dict = {}
    if token is not None:
        state_dict['token'] = SimpleNamespace(credentials=token)
    return {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.1'},
        'http_version': '1.1',
        'method': method,
        'scheme': 'http',
        'path': path,
        'raw_path': path.encode('latin-1'),
        'query_string': b'',
        'headers': [],
        'client': ('1.2.3.4', 54321),
        'server': ('127.0.0.1', 8080),
        'state': state_dict,
    }


async def _downstream_ok(scope, receive, send):
    """Minimal ASGI inner app that always returns 200 OK."""
    await send({'type': 'http.response.start', 'status': 200, 'headers': [(b'content-type', b'text/plain')]})
    await send({'type': 'http.response.body', 'body': b'ok'})


def _collect_sender():
    """Return an async send callable plus the list it records messages into."""
    messages: list[dict] = []

    async def send(message):
        messages.append(message)

    return send, messages


# ---------------------------------------------------------------------------
# classify() — endpoint classification table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'path,method,expected',
    [
        ('/api/chat/completions', 'POST', 'chat'),
        ('/api/v1/chat/completions', 'POST', 'chat'),
        ('/ollama/api/chat', 'POST', 'chat'),
        ('/ollama/api/generate', 'POST', 'chat'),
        ('/openai/chat/completions', 'POST', 'chat'),
        ('/api/embeddings', 'POST', 'embeddings'),
        ('/api/v1/embeddings', 'POST', 'embeddings'),
        ('/api/v1/files', 'POST', 'uploads'),
        ('/api/v1/retrieval/process/file', 'POST', 'uploads'),
        ('/api/v1/knowledge/abc-123/file/add', 'POST', 'uploads'),
        ('/api/v1/configs/import', 'POST', 'admin'),
        ('/api/v1/models', 'DELETE', 'admin'),
        ('/api/v1/groups', 'PUT', 'admin'),
        ('/api/v1/users', 'PATCH', 'admin'),
    ],
)
def test_classify_matches_expected_class(path, method, expected):
    assert classify(path, method) == expected


@pytest.mark.parametrize(
    'path,method',
    [
        ('/health', 'GET'),
        ('/ready', 'GET'),
        ('/ws/socket.io/', 'GET'),
        ('/static/foo.js', 'GET'),
        ('/assets/favicon.png', 'GET'),
        ('/manifest.json', 'GET'),
        ('/', 'GET'),
        ('/api/v1/chats', 'GET'),  # Not in the route table.
        ('/api/v1/configs', 'GET'),  # Admin class only matches write methods.
        ('/api/v1/models', 'GET'),
        ('/api/v1/users', 'HEAD'),
    ],
)
def test_classify_skips_unmatched_or_read_only(path, method):
    assert classify(path, method) is None


# ---------------------------------------------------------------------------
# resolve_identity() — order: JWT > API key > IP
# ---------------------------------------------------------------------------


def test_resolve_identity_prefers_jwt_user_id(monkeypatch):
    monkeypatch.setattr(
        'open_webui.utils.rate_limit_middleware.decode_token',
        lambda tok: {'id': 'user-42'},
    )
    scope = _make_scope()
    id_type, ident = resolve_identity(scope, 'fake.jwt.token')
    assert id_type == 'u'
    assert ident == 'user-42'


def test_resolve_identity_falls_back_to_api_key_hash():
    scope = _make_scope()
    id_type, ident = resolve_identity(scope, 'sk-deadbeefcafebabe1234567890abcdef')
    assert id_type == 'k'
    # SHA-256 first 16 hex chars → stable, non-reversible.
    assert len(ident) == 16
    assert all(c in '0123456789abcdef' for c in ident)


def test_resolve_identity_falls_back_to_client_ip(monkeypatch):
    monkeypatch.setattr('open_webui.utils.rate_limit_middleware.decode_token', lambda tok: None)
    scope = _make_scope()
    id_type, ident = resolve_identity(scope, None)
    assert id_type == 'i'
    assert ident == '1.2.3.4'


def test_resolve_identity_anonymous_no_client():
    scope = _make_scope()
    scope['client'] = None
    id_type, ident = resolve_identity(scope, None)
    assert id_type == 'i'
    assert ident == 'unknown'


# ---------------------------------------------------------------------------
# Middleware: feature gating
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_middleware_is_noop_when_disabled():
    state = _make_app_state(enabled=False)
    app_state = SimpleNamespace(state=state)
    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)

    send, messages = _collect_sender()
    await mw(_make_scope('/api/v1/chat/completions'), AsyncMock(), send)

    # Downstream called without any Redis involvement.
    assert messages[0]['status'] == 200
    # No ratelimit headers added when disabled.
    header_keys = {h[0] for h in messages[0]['headers']}
    assert b'ratelimit-limit' not in header_keys


@pytest.mark.asyncio
async def test_middleware_skips_unclassified_paths():
    state = _make_app_state(enabled=True)
    state.redis = AsyncMock()
    app_state = SimpleNamespace(state=state)
    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)

    send, messages = _collect_sender()
    await mw(_make_scope('/health', method='GET'), AsyncMock(), send)

    assert messages[0]['status'] == 200
    state.redis.evalsha.assert_not_called()
    state.redis.script_load.assert_not_called()


# ---------------------------------------------------------------------------
# Middleware: Redis interaction
# ---------------------------------------------------------------------------


def _wire_redis(mock_redis: AsyncMock, script_sha: str = 'abc123') -> None:
    """Make the AsyncMock return sensible defaults for script_load."""
    mock_redis.script_load = AsyncMock(return_value=script_sha)


@pytest.mark.asyncio
async def test_middleware_allows_request_under_limit(monkeypatch):
    monkeypatch.setattr(
        'open_webui.utils.rate_limit_middleware.decode_token',
        lambda tok: {'id': 'user-1'},
    )
    redis = AsyncMock()
    _wire_redis(redis)
    # {limited, count, retry_ms} — allowed.
    redis.evalsha = AsyncMock(return_value=[0, 1, 0])

    state = _make_app_state(enabled=True)
    state.redis = redis
    app_state = SimpleNamespace(state=state)

    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)
    send, messages = _collect_sender()
    await mw(_make_scope(token='jwt'), AsyncMock(), send)

    assert messages[0]['status'] == 200
    headers = dict(messages[0]['headers'])
    assert headers[b'ratelimit-limit'] == b'3'
    assert headers[b'ratelimit-remaining'] == b'2'
    redis.evalsha.assert_awaited_once()


@pytest.mark.asyncio
async def test_middleware_returns_429_when_limit_exceeded(monkeypatch):
    monkeypatch.setattr(
        'open_webui.utils.rate_limit_middleware.decode_token',
        lambda tok: {'id': 'user-1'},
    )
    redis = AsyncMock()
    _wire_redis(redis)
    # {limited, count, retry_ms} — denied, 2500 ms until next slot frees.
    redis.evalsha = AsyncMock(return_value=[1, 3, 2500])

    state = _make_app_state(enabled=True)
    state.redis = redis
    app_state = SimpleNamespace(state=state)

    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)
    send, messages = _collect_sender()
    await mw(_make_scope(token='jwt'), AsyncMock(), send)

    start = messages[0]
    assert start['status'] == 429
    headers = dict(start['headers'])
    assert headers[b'content-type'] == b'application/json'
    assert headers[b'retry-after'] == b'2'
    assert headers[b'ratelimit-limit'] == b'3'
    assert headers[b'ratelimit-remaining'] == b'0'

    body = messages[1]
    payload = json.loads(body['body'])
    assert payload['class'] == 'chat'
    assert 'rate limit' in payload['detail'].lower()


@pytest.mark.asyncio
async def test_middleware_fail_open_on_redis_error(monkeypatch):
    monkeypatch.setattr(
        'open_webui.utils.rate_limit_middleware.decode_token',
        lambda tok: {'id': 'user-1'},
    )
    redis = AsyncMock()
    redis.script_load = AsyncMock(side_effect=ConnectionError('redis down'))
    redis.evalsha = AsyncMock(side_effect=ConnectionError('redis down'))

    state = _make_app_state(enabled=True, fail_open=True)
    state.redis = redis
    app_state = SimpleNamespace(state=state)

    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)
    send, messages = _collect_sender()
    await mw(_make_scope(token='jwt'), AsyncMock(), send)

    assert messages[0]['status'] == 200  # Request allowed through.


@pytest.mark.asyncio
async def test_middleware_fail_closed_on_redis_error(monkeypatch):
    monkeypatch.setattr(
        'open_webui.utils.rate_limit_middleware.decode_token',
        lambda tok: {'id': 'user-1'},
    )
    redis = AsyncMock()
    redis.script_load = AsyncMock(side_effect=ConnectionError('redis down'))
    redis.evalsha = AsyncMock(side_effect=ConnectionError('redis down'))

    state = _make_app_state(enabled=True, fail_open=False)
    state.redis = redis
    app_state = SimpleNamespace(state=state)

    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)
    send, messages = _collect_sender()
    await mw(_make_scope(token='jwt'), AsyncMock(), send)

    assert messages[0]['status'] == 429


@pytest.mark.asyncio
async def test_middleware_reloads_script_on_noscript(monkeypatch):
    monkeypatch.setattr(
        'open_webui.utils.rate_limit_middleware.decode_token',
        lambda tok: {'id': 'user-1'},
    )

    redis = AsyncMock()
    # script_load succeeds twice (initial + reload after NOSCRIPT).
    redis.script_load = AsyncMock(side_effect=['sha1', 'sha1'])

    calls = {'n': 0}

    async def evalsha_side_effect(*args, **kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            raise Exception('NOSCRIPT No matching script')
        return [0, 1, 0]

    async def eval_side_effect(*args, **kwargs):
        return [0, 1, 0]

    redis.evalsha = AsyncMock(side_effect=evalsha_side_effect)
    redis.eval = AsyncMock(side_effect=eval_side_effect)

    state = _make_app_state(enabled=True)
    state.redis = redis
    app_state = SimpleNamespace(state=state)

    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)
    send, messages = _collect_sender()
    await mw(_make_scope(token='jwt'), AsyncMock(), send)

    assert messages[0]['status'] == 200
    redis.eval.assert_awaited()  # NOSCRIPT fallback path exercised.


@pytest.mark.asyncio
async def test_middleware_disabled_class_via_zero_limit(monkeypatch):
    """A limit of zero means "class disabled" — short-circuit, no Redis call."""
    monkeypatch.setattr(
        'open_webui.utils.rate_limit_middleware.decode_token',
        lambda tok: {'id': 'user-1'},
    )
    redis = AsyncMock()
    state = _make_app_state(enabled=True, RATE_LIMITING_CHAT_LIMIT=0)
    state.redis = redis
    app_state = SimpleNamespace(state=state)

    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)
    send, messages = _collect_sender()
    await mw(_make_scope(token='jwt'), AsyncMock(), send)

    assert messages[0]['status'] == 200
    redis.evalsha.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_redis_key_format(monkeypatch):
    """Verify the exact Redis key shape — critical for multi-node consistency."""
    monkeypatch.setattr(
        'open_webui.utils.rate_limit_middleware.decode_token',
        lambda tok: {'id': 'alice'},
    )
    monkeypatch.setattr('open_webui.utils.rate_limit_middleware.REDIS_KEY_PREFIX', 'owui')

    redis = AsyncMock()
    _wire_redis(redis)
    redis.evalsha = AsyncMock(return_value=[0, 1, 0])

    state = _make_app_state(enabled=True)
    state.redis = redis
    app_state = SimpleNamespace(state=state)

    mw = RateLimitMiddleware(_downstream_ok, fastapi_app=app_state)
    send, _messages = _collect_sender()
    await mw(_make_scope(token='jwt'), AsyncMock(), send)

    call_args = redis.evalsha.await_args
    # evalsha(sha, numkeys, key, *argv)
    assert call_args.args[2] == 'owui:rl:chat:u:alice'
