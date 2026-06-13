import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _Router:
    def get(self, *args, **kwargs):
        return lambda func: func

    def post(self, *args, **kwargs):
        return lambda func: func


class _BaseModel:
    pass


class _HTTPException(Exception):
    def __init__(self, status_code=None, detail=None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class _OAuthClientManager:
    def __init__(self):
        self.removed_clients = []
        self.added_clients = []

    def remove_client(self, client_key):
        self.removed_clients.append(client_key)

    def add_client(self, client_key, client_info):
        self.added_clients.append((client_key, client_info))


class _Connection:
    def __init__(self, data):
        self.data = data

    def model_dump(self):
        return self.data


def _install_stub(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_configs_module():
    for name in list(sys.modules):
        if name == 'open_webui' or name.startswith('open_webui.') or name == 'mcp' or name.startswith('mcp.'):
            del sys.modules[name]

    _install_stub('aiohttp')
    _install_stub(
        'fastapi',
        APIRouter=lambda: _Router(),
        Depends=lambda dependency=None: dependency,
        HTTPException=_HTTPException,
        Request=object,
    )
    _install_stub('mcp')
    _install_stub('mcp.shared')
    _install_stub('mcp.shared.auth', OAuthMetadata=object)
    _install_stub('open_webui')
    _install_stub(
        'open_webui.config',
        BannerModel=object,
        async_save_config=lambda config: None,
        get_config=lambda: {},
        save_config=lambda config: None,
    )
    _install_stub(
        'open_webui.env',
        AIOHTTP_CLIENT_SESSION_SSL=True,
        AIOHTTP_CLIENT_TIMEOUT=10,
    )
    _install_stub('open_webui.models')
    _install_stub('open_webui.models.oauth_sessions', OAuthSessions=object)
    _install_stub('open_webui.utils')
    _install_stub('open_webui.utils.auth', get_admin_user=object(), get_verified_user=object())
    _install_stub('open_webui.utils.headers', get_custom_headers=lambda *args, **kwargs: {})
    _install_stub('open_webui.utils.mcp')
    _install_stub('open_webui.utils.mcp.client', MCPClient=object)
    _install_stub(
        'open_webui.utils.oauth',
        OAuthClientInformationFull=lambda **kwargs: kwargs,
        decrypt_data=lambda data: data,
        encrypt_data=lambda data: data,
        get_discovery_urls=lambda url: [],
        get_oauth_client_info_with_dynamic_client_registration=lambda *args, **kwargs: None,
        get_oauth_client_info_with_static_credentials=lambda *args, **kwargs: None,
        resolve_oauth_client_info=lambda connection: {},
    )
    _install_stub(
        'open_webui.utils.tools',
        get_tool_server_data=lambda *args, **kwargs: {},
        get_tool_server_url=lambda url, path: f'{url}/{path}',
        set_terminal_servers=lambda request: [],
        set_tool_servers=lambda request: [],
    )
    _install_stub('pydantic', BaseModel=_BaseModel, ConfigDict=dict)

    module_path = Path(__file__).parents[1] / 'backend' / 'open_webui' / 'routers' / 'configs.py'
    spec = importlib.util.spec_from_file_location('configs_under_test', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToolServersConfigTests(unittest.TestCase):
    def setUp(self):
        self.configs = _load_configs_module()

        async def set_tool_servers(_request):
            return []

        self.configs.set_tool_servers = set_tool_servers

    def _request_with_connections(self, connections):
        oauth_client_manager = _OAuthClientManager()
        request = types.SimpleNamespace(
            app=types.SimpleNamespace(
                state=types.SimpleNamespace(
                    config=types.SimpleNamespace(TOOL_SERVER_CONNECTIONS=connections),
                    oauth_client_manager=oauth_client_manager,
                )
            )
        )
        return request, oauth_client_manager

    def test_existing_oauth_mcp_connection_allows_null_info(self):
        request, oauth_client_manager = self._request_with_connections(
            [
                {
                    'url': 'http://mcp.example',
                    'path': '/mcp',
                    'type': 'mcp',
                    'auth_type': 'oauth_2.1',
                    'info': None,
                }
            ]
        )
        form_data = types.SimpleNamespace(TOOL_SERVER_CONNECTIONS=[])

        result = asyncio.run(self.configs.set_tool_servers_config(request, form_data))

        self.assertEqual(result, {'TOOL_SERVER_CONNECTIONS': []})
        self.assertEqual(oauth_client_manager.removed_clients, ['mcp:None'])

    def test_new_mcp_connection_allows_null_info(self):
        request, oauth_client_manager = self._request_with_connections([])
        connection = _Connection(
            {
                'url': 'http://mcp.example',
                'path': '/mcp',
                'type': 'mcp',
                'auth_type': 'none',
                'info': None,
            }
        )
        form_data = types.SimpleNamespace(TOOL_SERVER_CONNECTIONS=[connection])

        result = asyncio.run(self.configs.set_tool_servers_config(request, form_data))

        self.assertEqual(result, {'TOOL_SERVER_CONNECTIONS': [connection.data]})
        self.assertEqual(oauth_client_manager.added_clients, [])
