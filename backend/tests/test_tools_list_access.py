"""Regression tests for GET /api/v1/tools/ server visibility.

Private external tool servers and MCP Streamable HTTP servers with no access
grants must remain visible to admins when BYPASS_ADMIN_ACCESS_CONTROL=false.
``has_access`` denies that state; ``has_connection_access`` applies the same
admin-private rule terminals already use.

These tests avoid importing the Open WebUI app (which pulls the full backend
stack). They lock the listing filter to ``has_connection_access`` and check
that helper's empty-grant contract against the same cases as ``get_tools``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
TOOLS_PY = BACKEND / 'open_webui' / 'routers' / 'tools.py'
ACCESS_CONTROL_PY = BACKEND / 'open_webui' / 'utils' / 'access_control' / '__init__.py'

PRIVATE_OPENAPI = {'config': {}}
PRIVATE_MCP = {
    'type': 'mcp',
    'config': {'enable': True, 'access_grants': []},
}
GRANTED_OPENAPI = {
    'config': {'access_grants': [{'principal_type': 'group', 'principal_id': 'g1', 'permission': 'read'}]}
}


def _fn(tree: ast.Module, name: str) -> ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f'{name} not found')


def _call_names(fn: ast.AsyncFunctionDef) -> set[str]:
    return {node.func.id for node in ast.walk(fn) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}


def test_get_tools_filters_servers_with_has_connection_access():
    """The chat Integrations picker list must use the connection helper."""
    source = TOOLS_PY.read_text()
    tree = ast.parse(source)
    fn = _fn(tree, 'get_tools')
    calls = _call_names(fn)

    assert 'has_connection_access' in calls
    assert 'has_access' not in calls
    assert 'server_connections' in source
    assert 'server_access_grants' not in source


def test_has_connection_access_empty_grants_are_admin_only():
    """#27581's helper is the contract get_tools now relies on for servers."""
    source = ACCESS_CONTROL_PY.read_text()
    fn = _fn(ast.parse(source), 'has_connection_access')
    body = ast.get_source_segment(source, fn)
    assert body is not None
    assert 'if not access_grants:' in body
    assert "return user.role == 'admin'" in body


def _load_has_access():
    """Exec the real has_access so grant matching is not reimplemented here."""
    source = ACCESS_CONTROL_PY.read_text()
    fn = _fn(ast.parse(source), 'has_access')
    segment = ast.get_source_segment(source, fn)
    namespace: dict = {}
    exec('from __future__ import annotations\n' + segment, namespace)
    return namespace['has_access']


_HAS_ACCESS = _load_has_access()


async def _has_connection_access(user, connection, user_group_ids, *, bypass: bool) -> bool:
    """Same branches as has_connection_access, with bypass injected (no config import)."""
    if user.role == 'admin' and bypass:
        return True

    access_grants = (connection.get('config') or {}).get('access_grants', [])
    if not access_grants:
        return user.role == 'admin'

    return await _HAS_ACCESS(user.id, 'read', access_grants, user_group_ids)


async def _filter_picker_servers(user, server_connections, *, bypass: bool, user_group_ids: set[str]):
    """Mirror get_tools' server visibility list comprehension."""
    tools = [SimpleNamespace(id=server_id) for server_id in server_connections]
    if bypass and user.role == 'admin':
        return tools
    return [
        tool
        for tool in tools
        if not str(tool.id).startswith('server:')
        or await _has_connection_access(
            user,
            server_connections.get(str(tool.id), {}),
            user_group_ids,
            bypass=bypass,
        )
    ]


def _admin():
    return SimpleNamespace(id='admin-1', role='admin')


def _user():
    return SimpleNamespace(id='user-1', role='user')


def _ids(tools) -> set[str]:
    return {tool.id for tool in tools}


@pytest.mark.asyncio
async def test_admin_sees_private_openapi_and_mcp_servers_when_bypass_disabled():
    tools = await _filter_picker_servers(
        _admin(),
        {
            'server:openapi-private': PRIVATE_OPENAPI,
            'server:mcp:mcp-private': PRIVATE_MCP,
        },
        bypass=False,
        user_group_ids=set(),
    )
    assert _ids(tools) == {'server:openapi-private', 'server:mcp:mcp-private'}


@pytest.mark.asyncio
async def test_non_admin_does_not_see_private_servers():
    tools = await _filter_picker_servers(
        _user(),
        {
            'server:openapi-private': PRIVATE_OPENAPI,
            'server:mcp:mcp-private': PRIVATE_MCP,
        },
        bypass=False,
        user_group_ids=set(),
    )
    assert _ids(tools) == set()


@pytest.mark.asyncio
async def test_granted_group_still_sees_server():
    tools = await _filter_picker_servers(
        _user(),
        {'server:openapi-granted': GRANTED_OPENAPI},
        bypass=False,
        user_group_ids={'g1'},
    )
    assert _ids(tools) == {'server:openapi-granted'}


@pytest.mark.asyncio
async def test_ungranted_group_does_not_see_server():
    tools = await _filter_picker_servers(
        _user(),
        {'server:openapi-granted': GRANTED_OPENAPI},
        bypass=False,
        user_group_ids={'other'},
    )
    assert _ids(tools) == set()
