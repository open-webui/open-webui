"""Tests for the Workbench sidebar entitlement fetcher.

The behaviors that are easy to regress (TTL caching, 404 negative
caching, soft-fail to last-known on error, pruning) are non-obvious
from the code alone, so they get explicit coverage here. httpx is
mocked via a fake AsyncClient class so we don't need a network.
"""

from unittest.mock import MagicMock

import httpx
import pytest
from open_webui.utils import workbench_sidebar
from open_webui.utils.workbench_sidebar import (
    _CACHE,
    _TTL_SECONDS,
    _prune_expired,
    fetch_sidebar,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Each test starts from an empty cache."""
    _CACHE.clear()
    yield
    _CACHE.clear()


@pytest.fixture
def configured_env(monkeypatch):
    """Sets the three env-derived module-level constants so
    _is_configured() returns True. Module reads happen at import
    time, so we patch the module attrs directly rather than os.environ."""
    monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_URL', 'https://wb.example')
    monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_API_TOKEN', 'stw_test.secret')
    monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_COMPANY_ID', 'c-uuid')


def _mock_response(status_code: int, body: dict | None = None):
    response = MagicMock()
    response.status_code = status_code
    response.json = MagicMock(return_value=body or {})
    response.raise_for_status = MagicMock()
    if status_code >= 400 and status_code != 404:
        response.raise_for_status.side_effect = httpx.HTTPStatusError('err', request=MagicMock(), response=response)
    return response


class _FakeAsyncClient:
    """Stand-in for httpx.AsyncClient used as an async context manager
    in fetch_sidebar. Each instance returns whatever `_next` produces
    on the next `get` call — set by the test via the class attribute."""

    _next = None  # callable(url, params, headers) -> Response  OR Exception

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, params=None, headers=None):
        if isinstance(self._next, BaseException):
            raise self._next
        if callable(self._next):
            return self._next(url, params, headers)
        raise AssertionError('FakeAsyncClient._next not set')


def _patch_client(monkeypatch, *, response=None, exception=None, handler=None):
    """Install _FakeAsyncClient as the httpx.AsyncClient seen by the
    module under test. Either a static response, a raised exception,
    or a handler closure (for asserting call args) can be configured.

    Functions stored as class attributes become bound methods when
    accessed via the instance, so callables are wrapped in
    staticmethod to keep them unbound. Exceptions are stored as-is."""
    if exception is not None:
        _FakeAsyncClient._next = exception
    elif handler is not None:
        _FakeAsyncClient._next = staticmethod(handler)
    else:
        _FakeAsyncClient._next = staticmethod(lambda *_a, **_kw: response)
    monkeypatch.setattr(workbench_sidebar.httpx, 'AsyncClient', _FakeAsyncClient)


class TestNotConfigured:
    @pytest.mark.asyncio
    async def test_returns_none_when_url_missing(self, monkeypatch):
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_URL', '')
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_API_TOKEN', 't')
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_COMPANY_ID', 'c')
        assert await fetch_sidebar('user@example.com') is None

    @pytest.mark.asyncio
    async def test_returns_none_when_token_missing(self, monkeypatch):
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_URL', 'https://wb')
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_API_TOKEN', '')
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_COMPANY_ID', 'c')
        assert await fetch_sidebar('user@example.com') is None

    @pytest.mark.asyncio
    async def test_returns_none_when_company_id_missing(self, monkeypatch):
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_URL', 'https://wb')
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_API_TOKEN', 't')
        monkeypatch.setattr(workbench_sidebar, 'WORKBENCH_COMPANY_ID', '')
        assert await fetch_sidebar('user@example.com') is None

    @pytest.mark.asyncio
    async def test_returns_none_when_email_blank(self, configured_env):
        assert await fetch_sidebar('') is None
        assert await fetch_sidebar(None) is None


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_returns_sidebar_subtree(self, monkeypatch, configured_env):
        # fetch_sidebar extracts and returns just the `sidebar` subtree
        # — siblings (user, company, features) are intentionally dropped
        # so the OWUI shell only gets what it needs.
        sidebar = {'main': [{'label': 'Chat'}], 'bottom': [{'label': 'Settings'}]}
        body = {'data': {'user': {'email': 'a@b'}, 'features': ['chat'], 'sidebar': sidebar}}
        _patch_client(monkeypatch, response=_mock_response(200, body))

        result = await fetch_sidebar('a@b')

        assert result == sidebar

    @pytest.mark.asyncio
    async def test_request_uses_token_and_url(self, monkeypatch, configured_env):
        captured = {}

        def handler(url, params, headers):
            captured['url'] = url
            captured['params'] = params
            captured['headers'] = headers
            return _mock_response(200, {'data': {'sidebar': {'main': [], 'bottom': []}}})

        _patch_client(monkeypatch, handler=handler)
        await fetch_sidebar('a@b')

        assert captured['url'] == 'https://wb.example/v1/companies/c-uuid/sidebar'
        assert captured['params'] == {'user_email': 'a@b'}
        assert captured['headers'] == {'Authorization': 'Bearer stw_test.secret'}

    @pytest.mark.asyncio
    async def test_request_normalizes_email_to_lowercase(self, monkeypatch, configured_env):
        # Request params should carry the normalized lowercase email so
        # request and cache key are symmetric (and so two callers using
        # different cases hit the same upstream cache).
        captured = {}

        def handler(url, params, headers):
            captured['params'] = params
            return _mock_response(200, {'data': {'sidebar': {'main': [], 'bottom': []}}})

        _patch_client(monkeypatch, handler=handler)
        await fetch_sidebar('Alice@Example.COM')

        assert captured['params'] == {'user_email': 'alice@example.com'}


class TestCaching:
    @pytest.mark.asyncio
    async def test_second_call_within_ttl_skips_http(self, monkeypatch, configured_env):
        call_count = {'n': 0}

        def handler(*_a, **_kw):
            call_count['n'] += 1
            return _mock_response(200, {'data': {'features': []}})

        _patch_client(monkeypatch, handler=handler)
        await fetch_sidebar('a@b')
        await fetch_sidebar('a@b')

        assert call_count['n'] == 1

    @pytest.mark.asyncio
    async def test_cache_is_keyed_by_lowercase_email(self, monkeypatch, configured_env):
        call_count = {'n': 0}

        def handler(*_a, **_kw):
            call_count['n'] += 1
            return _mock_response(200, {'data': {}})

        _patch_client(monkeypatch, handler=handler)
        await fetch_sidebar('Alice@Example.com')
        await fetch_sidebar('alice@example.com')

        assert call_count['n'] == 1

    @pytest.mark.asyncio
    async def test_expired_entries_re_fetch(self, monkeypatch, configured_env):
        call_count = {'n': 0}

        def handler(*_a, **_kw):
            call_count['n'] += 1
            return _mock_response(
                200, {'data': {'sidebar': {'main': [{'label': f'v{call_count["n"]}'}], 'bottom': []}}}
            )

        _patch_client(monkeypatch, handler=handler)

        # First call populates cache
        await fetch_sidebar('a@b')
        assert call_count['n'] == 1

        # Walk the cache entry's timestamp backwards past the TTL
        ts, data = _CACHE['a@b']
        _CACHE['a@b'] = (ts - _TTL_SECONDS - 1, data)

        result = await fetch_sidebar('a@b')
        assert call_count['n'] == 2
        assert result == {'main': [{'label': 'v2'}], 'bottom': []}


class TestNegativeCache:
    @pytest.mark.asyncio
    async def test_404_caches_none_and_returns_none(self, monkeypatch, configured_env):
        call_count = {'n': 0}

        def handler(*_a, **_kw):
            call_count['n'] += 1
            return _mock_response(404)

        _patch_client(monkeypatch, handler=handler)

        assert await fetch_sidebar('ghost@example.com') is None
        # Second call within TTL should be served from the negative cache
        assert await fetch_sidebar('ghost@example.com') is None
        assert call_count['n'] == 1


class TestSoftFail:
    @pytest.mark.asyncio
    async def test_exception_returns_last_known_value(self, monkeypatch, configured_env):
        # First populate the cache with a real value
        good_sidebar = {'main': [{'label': 'Chat'}], 'bottom': []}
        _patch_client(monkeypatch, response=_mock_response(200, {'data': {'sidebar': good_sidebar}}))
        first = await fetch_sidebar('a@b')
        assert first == good_sidebar

        # Expire the entry so the next call goes back to the network,
        # but the network call raises. Last-known value should come back.
        ts, data = _CACHE['a@b']
        _CACHE['a@b'] = (ts - _TTL_SECONDS - 1, data)
        _patch_client(monkeypatch, exception=httpx.ConnectError('boom'))

        result = await fetch_sidebar('a@b')
        assert result == good_sidebar

    @pytest.mark.asyncio
    async def test_exception_with_no_prior_cache_returns_none(self, monkeypatch, configured_env):
        _patch_client(monkeypatch, exception=httpx.ConnectError('boom'))
        assert await fetch_sidebar('fresh@example.com') is None

    @pytest.mark.asyncio
    async def test_exception_throttles_subsequent_calls_within_ttl(self, monkeypatch, configured_env):
        # During a Workbench outage, the cache timestamp should be
        # refreshed on every exception so subsequent calls within the
        # TTL window short-circuit instead of repeatedly blocking on
        # a _TIMEOUT_SECONDS-bounded network attempt.
        call_count = {'n': 0}

        def handler(*_a, **_kw):
            call_count['n'] += 1
            raise httpx.ConnectError('boom')

        _patch_client(monkeypatch, handler=handler)

        # Three rapid-fire calls during an outage with no prior cache:
        # only the first should attempt the network — the rest hit the
        # negative cache.
        await fetch_sidebar('outage@example.com')
        await fetch_sidebar('outage@example.com')
        await fetch_sidebar('outage@example.com')

        assert call_count['n'] == 1

    @pytest.mark.asyncio
    async def test_exception_preserves_last_known_value_in_cache(self, monkeypatch, configured_env):
        # First populate with a real value
        good_sidebar = {'main': [{'label': 'Chat'}], 'bottom': []}
        _patch_client(monkeypatch, response=_mock_response(200, {'data': {'sidebar': good_sidebar}}))
        await fetch_sidebar('a@b')

        # Expire the entry, then a network call raises
        ts, data = _CACHE['a@b']
        _CACHE['a@b'] = (ts - _TTL_SECONDS - 1, data)
        _patch_client(monkeypatch, exception=httpx.ConnectError('boom'))

        # The exception path should refresh the timestamp on the
        # last-known value so the next call returns it from cache
        # without another network attempt.
        await fetch_sidebar('a@b')

        cached_ts, cached_data = _CACHE['a@b']
        assert cached_data == good_sidebar
        # Fresh timestamp — well inside the TTL window
        assert cached_ts > ts


class TestPrune:
    def test_prune_removes_only_expired(self):
        now = 1000.0
        _CACHE.update(
            {
                'fresh@example.com': (now - 10, {'features': []}),
                'stale@example.com': (now - _TTL_SECONDS - 5, {'features': []}),
            }
        )

        _prune_expired(now)

        assert 'fresh@example.com' in _CACHE
        assert 'stale@example.com' not in _CACHE

    def test_prune_treats_entry_exactly_at_ttl_boundary_as_expired(self):
        # The implementation treats `>=` as expired, so an entry exactly
        # at the TTL boundary gets dropped. Locks in current behavior.
        now = 1000.0
        _CACHE['x@y'] = (now - _TTL_SECONDS, {})

        _prune_expired(now)

        assert 'x@y' not in _CACHE
