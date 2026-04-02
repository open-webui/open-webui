"""Unit tests for the terminals reverse-proxy router.

Covers:
- _sanitize_proxy_path (path traversal prevention)
- _fetch_novnc_port (noVNC port discovery with fallback)
- HTTP proxy endpoints (list, proxy, desktop status/start)
- WebSocket route registration
"""

import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Pre-populate sys.modules with lightweight stubs for the open_webui
# dependency chain so that ``open_webui.routers.terminals`` can be
# imported without pulling in peewee/sqlalchemy/etc.
# ---------------------------------------------------------------------------


def _setup_module_mocks():
    needed = [
        'open_webui.utils',
        'open_webui.utils.auth',
        'open_webui.utils.access_control',
        'open_webui.models',
        'open_webui.models.groups',
        'open_webui.models.users',
        'open_webui.internal',
        'open_webui.internal.db',
    ]
    for mod_name in needed:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    sys.modules['open_webui.utils.auth'].get_verified_user = lambda: None
    sys.modules['open_webui.utils.access_control'].has_connection_access = lambda *a, **kw: True
    sys.modules['open_webui.models.groups'].Groups = MagicMock()
    sys.modules['open_webui.models.users'].Users = MagicMock()


_setup_module_mocks()

from open_webui.routers.terminals import (  # noqa: E402
    router,
    _sanitize_proxy_path,
    _fetch_novnc_port,
)


# ---------------------------------------------------------------------------
# _sanitize_proxy_path
# ---------------------------------------------------------------------------


class TestSanitizeProxyPath:
    def test_simple_path(self):
        assert _sanitize_proxy_path('api/config') == 'api/config'

    def test_trailing_slash_preserved(self):
        assert _sanitize_proxy_path('api/config/') == 'api/config/'

    def test_encoded_slashes(self):
        assert _sanitize_proxy_path('files/read%3Ffoo') == 'files/read?foo'

    def test_dotdot_rejected(self):
        assert _sanitize_proxy_path('../../../etc/passwd') is None

    def test_dot_only_rejected(self):
        assert _sanitize_proxy_path('.') is None

    def test_empty_rejected(self):
        assert _sanitize_proxy_path('') is None

    def test_double_slash_cleaned(self):
        assert _sanitize_proxy_path('foo//bar') == 'foo/bar'

    def test_leading_slash_stripped(self):
        assert _sanitize_proxy_path('/api/config') == 'api/config'


# ---------------------------------------------------------------------------
# _fetch_novnc_port
# ---------------------------------------------------------------------------


class TestFetchNovncPort:
    @pytest.mark.asyncio
    async def test_returns_port_from_server(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={'running': True, 'novnc_port': 6090})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch('open_webui.routers.terminals.aiohttp.ClientSession', return_value=mock_session):
            port = await _fetch_novnc_port('http://terminal:8080', 'key123')
        assert port == 6090

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception('connection refused'))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch('open_webui.routers.terminals.aiohttp.ClientSession', return_value=mock_session):
            port = await _fetch_novnc_port('http://terminal:8080', 'key123')
        assert port == 6080


def _make_app():
    app = FastAPI()
    app.include_router(router, prefix='/api/v1/terminals')
    return app


@pytest.fixture()
def app():
    return _make_app()


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def mock_user():
    user = MagicMock()
    user.id = 'test-user-id'
    user.email = 'test@example.com'
    user.role = 'user'
    return user


@pytest.fixture()
def mock_connection():
    return {
        'id': 'srv1',
        'name': 'Test Server',
        'url': 'http://terminal-server:8080',
        'key': 'secret-key',
        'auth_type': 'bearer',
        'enabled': True,
        'policy_id': None,
    }


@pytest.fixture()
def mock_config(mock_connection):
    return MagicMock(TERMINAL_SERVER_CONNECTIONS=[mock_connection])


def _override_auth(app, user):
    from open_webui.utils.auth import get_verified_user

    app.dependency_overrides[get_verified_user] = lambda: user


def _clear_auth(app):
    from open_webui.utils.auth import get_verified_user

    app.dependency_overrides.pop(get_verified_user, None)


# ---------------------------------------------------------------------------
# list terminal servers
# ---------------------------------------------------------------------------


class TestListTerminals:
    def test_returns_configured_servers(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=True),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.get('/api/v1/terminals/')

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['id'] == 'srv1'
        assert data[0]['name'] == 'Test Server'
        _clear_auth(app)

    def test_filters_by_access(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=False),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.get('/api/v1/terminals/')

        assert resp.status_code == 200
        assert resp.json() == []
        _clear_auth(app)

    def test_skips_disabled_servers(self, client, app, mock_user):
        _override_auth(app, mock_user)
        conn = {
            'id': 'srv2',
            'name': 'Disabled',
            'url': 'http://ts:8080',
            'key': 'k',
            'enabled': False,
        }
        app.state.config = MagicMock(TERMINAL_SERVER_CONNECTIONS=[conn])

        with patch('open_webui.routers.terminals.Groups') as MockGroups:
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.get('/api/v1/terminals/')

        assert resp.status_code == 200
        assert resp.json() == []
        _clear_auth(app)


# ---------------------------------------------------------------------------
# HTTP proxy: proxy_terminal
# ---------------------------------------------------------------------------


class TestProxyTerminal:
    def test_404_for_unknown_server(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        resp = client.get('/api/v1/terminals/nonexistent/api/config')
        assert resp.status_code == 404
        _clear_auth(app)

    def test_403_for_no_access(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=False),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.get('/api/v1/terminals/srv1/api/config')

        assert resp.status_code == 403
        _clear_auth(app)

    def test_400_for_invalid_path(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=True),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.get('/api/v1/terminals/srv1/..%2F..%2Fetc%2Fpasswd')

        assert resp.status_code == 400
        _clear_auth(app)

    def test_proxies_json_response(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        upstream_body = {'features': {'terminal': True, 'desktop': True}}

        mock_upstream = AsyncMock()
        mock_upstream.status = 200
        mock_upstream.headers = {'content-type': 'application/json'}
        mock_upstream.read = AsyncMock(return_value=json.dumps(upstream_body).encode())
        mock_upstream.release = AsyncMock()

        mock_session_instance = AsyncMock()
        mock_session_instance.request = AsyncMock(return_value=mock_upstream)
        mock_session_instance.close = AsyncMock()

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=True),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
            patch('open_webui.routers.terminals.aiohttp.ClientSession', return_value=mock_session_instance),
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.get('/api/v1/terminals/srv1/api/config')

        assert resp.status_code == 200
        assert resp.json() == upstream_body

        call_kwargs = mock_session_instance.request.call_args
        target_url = call_kwargs.kwargs.get('url', call_kwargs.args[1] if len(call_kwargs.args) > 1 else '')
        assert target_url == 'http://terminal-server:8080/api/config'
        _clear_auth(app)

    def test_proxies_with_bearer_auth_header(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        mock_upstream = AsyncMock()
        mock_upstream.status = 200
        mock_upstream.headers = {'content-type': 'application/json'}
        mock_upstream.read = AsyncMock(return_value=b'{}')
        mock_upstream.release = AsyncMock()

        mock_session_instance = AsyncMock()
        mock_session_instance.request = AsyncMock(return_value=mock_upstream)
        mock_session_instance.close = AsyncMock()

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=True),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
            patch('open_webui.routers.terminals.aiohttp.ClientSession', return_value=mock_session_instance),
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            client.get('/api/v1/terminals/srv1/api/config')

        call_kwargs = mock_session_instance.request.call_args
        headers = call_kwargs.kwargs.get('headers', {})
        assert headers.get('Authorization') == 'Bearer secret-key'
        _clear_auth(app)

    def test_proxies_desktop_status_endpoint(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        desktop_status = {
            'running': True,
            'display': ':0',
            'vnc_port': 5900,
            'novnc_port': 6080,
            'screen_width': 1280,
            'screen_height': 720,
        }

        mock_upstream = AsyncMock()
        mock_upstream.status = 200
        mock_upstream.headers = {'content-type': 'application/json'}
        mock_upstream.read = AsyncMock(return_value=json.dumps(desktop_status).encode())
        mock_upstream.release = AsyncMock()

        mock_session_instance = AsyncMock()
        mock_session_instance.request = AsyncMock(return_value=mock_upstream)
        mock_session_instance.close = AsyncMock()

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=True),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
            patch('open_webui.routers.terminals.aiohttp.ClientSession', return_value=mock_session_instance),
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.get('/api/v1/terminals/srv1/desktop')

        assert resp.status_code == 200
        data = resp.json()
        assert data['running'] is True
        assert data['novnc_port'] == 6080
        _clear_auth(app)

    def test_proxies_desktop_start_endpoint(self, client, app, mock_user, mock_config):
        _override_auth(app, mock_user)
        app.state.config = mock_config

        start_response = {'running': True, 'novnc_port': 6080}

        mock_upstream = AsyncMock()
        mock_upstream.status = 200
        mock_upstream.headers = {'content-type': 'application/json'}
        mock_upstream.read = AsyncMock(return_value=json.dumps(start_response).encode())
        mock_upstream.release = AsyncMock()

        mock_session_instance = AsyncMock()
        mock_session_instance.request = AsyncMock(return_value=mock_upstream)
        mock_session_instance.close = AsyncMock()

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=True),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
            patch('open_webui.routers.terminals.aiohttp.ClientSession', return_value=mock_session_instance),
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.post('/api/v1/terminals/srv1/desktop/start')

        assert resp.status_code == 200
        assert resp.json()['running'] is True
        call_kwargs = mock_session_instance.request.call_args
        assert call_kwargs.kwargs.get('method') == 'POST'
        _clear_auth(app)

    def test_503_for_empty_url(self, client, app, mock_user):
        _override_auth(app, mock_user)
        conn = {'id': 'srv3', 'name': 'No URL', 'url': '', 'key': 'k', 'enabled': True}
        app.state.config = MagicMock(TERMINAL_SERVER_CONNECTIONS=[conn])

        with (
            patch('open_webui.routers.terminals.has_connection_access', return_value=True),
            patch('open_webui.routers.terminals.Groups') as MockGroups,
        ):
            MockGroups.get_groups_by_member_id.return_value = []
            resp = client.get('/api/v1/terminals/srv3/api/config')

        assert resp.status_code == 503
        _clear_auth(app)


# ---------------------------------------------------------------------------
# WebSocket route registration
# ---------------------------------------------------------------------------


class TestDesktopWsRoute:
    def test_ws_desktop_endpoint_registered(self, app):
        routes = [r.path for r in app.routes]
        assert '/api/v1/terminals/{server_id}/desktop/ws' in routes

    def test_ws_terminal_endpoint_registered(self, app):
        routes = [r.path for r in app.routes]
        assert '/api/v1/terminals/{server_id}/api/terminals/{session_id}' in routes
