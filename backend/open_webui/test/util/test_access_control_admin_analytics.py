import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_webui.config import DEFAULT_USER_PERMISSIONS
from open_webui.utils.access_control import fill_missing_permissions, get_permissions, has_permission

LEGACY_PERMISSIONS = {
    'workspace': {'models': False},
    'sharing': {'public_chats': False},
    'access_grants': {'allow_users': True},
    'chat': {'controls': True},
    'features': {'notes': True},
    'settings': {'interface': True},
}


def _user(user_id: str, role: str = 'user', info: dict | None = None):
    return SimpleNamespace(id=user_id, role=role, info=info)


@pytest.mark.parametrize(
    'permissions,expected_analytics',
    [
        ({}, False),
        (LEGACY_PERMISSIONS.copy(), False),
    ],
)
def test_fill_missing_permissions_adds_admin_section(permissions, expected_analytics):
    result = fill_missing_permissions(permissions, DEFAULT_USER_PERMISSIONS)
    assert 'admin' in result
    assert 'analytics' in result['admin']
    assert result['admin']['analytics'] is expected_analytics


@pytest.mark.asyncio
async def test_get_permissions_admin_always_has_analytics():
    with (
        patch(
            'open_webui.utils.access_control.Groups.get_groups_by_member_id',
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            'open_webui.models.users.Users.get_user_by_id',
            new_callable=AsyncMock,
            return_value=_user('admin-1', role='admin'),
        ),
    ):
        permissions = await get_permissions('admin-1', LEGACY_PERMISSIONS.copy())

    assert permissions['admin']['analytics'] is True


@pytest.mark.asyncio
async def test_get_permissions_user_info_override():
    with (
        patch(
            'open_webui.utils.access_control.Groups.get_groups_by_member_id',
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            'open_webui.models.users.Users.get_user_by_id',
            new_callable=AsyncMock,
            return_value=_user(
                'user-1',
                role='user',
                info={'permissions': {'admin': {'analytics': True}}},
            ),
        ),
    ):
        permissions = await get_permissions('user-1', LEGACY_PERMISSIONS.copy())

    assert permissions['admin']['analytics'] is True


@pytest.mark.asyncio
async def test_get_permissions_group_override():
    group = SimpleNamespace(permissions={'admin': {'analytics': True}})

    with (
        patch(
            'open_webui.utils.access_control.Groups.get_groups_by_member_id',
            new_callable=AsyncMock,
            return_value=[group],
        ),
        patch(
            'open_webui.models.users.Users.get_user_by_id',
            new_callable=AsyncMock,
            return_value=_user('user-2', role='user'),
        ),
    ):
        permissions = await get_permissions('user-2', LEGACY_PERMISSIONS.copy())

    assert permissions['admin']['analytics'] is True


@pytest.mark.asyncio
async def test_get_permissions_regular_user_default_denied():
    with (
        patch(
            'open_webui.utils.access_control.Groups.get_groups_by_member_id',
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            'open_webui.models.users.Users.get_user_by_id',
            new_callable=AsyncMock,
            return_value=_user('user-3', role='user'),
        ),
    ):
        permissions = await get_permissions('user-3', LEGACY_PERMISSIONS.copy())

    assert permissions['admin']['analytics'] is False


@pytest.mark.asyncio
async def test_has_permission_admin_role_grants_admin_scope():
    with (
        patch(
            'open_webui.models.users.Users.get_user_by_id',
            new_callable=AsyncMock,
            return_value=_user('admin-1', role='admin'),
        ),
        patch(
            'open_webui.utils.access_control.Groups.get_groups_by_member_id',
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        allowed = await has_permission('admin-1', 'admin.analytics', LEGACY_PERMISSIONS.copy())

    assert allowed is True


@pytest.mark.asyncio
async def test_has_permission_user_info_grants_analytics():
    with (
        patch(
            'open_webui.models.users.Users.get_user_by_id',
            new_callable=AsyncMock,
            return_value=_user(
                'user-1',
                role='user',
                info={'permissions': {'admin': {'analytics': True}}},
            ),
        ),
        patch(
            'open_webui.utils.access_control.Groups.get_groups_by_member_id',
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        allowed = await has_permission('user-1', 'admin.analytics', LEGACY_PERMISSIONS.copy())

    assert allowed is True


@pytest.mark.asyncio
async def test_has_permission_denied_without_grant():
    with (
        patch(
            'open_webui.models.users.Users.get_user_by_id',
            new_callable=AsyncMock,
            return_value=_user('user-2', role='user'),
        ),
        patch(
            'open_webui.utils.access_control.Groups.get_groups_by_member_id',
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        allowed = await has_permission('user-2', 'admin.analytics', LEGACY_PERMISSIONS.copy())

    assert allowed is False


def test_get_permissions_template_merges_code_defaults():
    """Persisted defaults without `admin` must inherit from DEFAULT_USER_PERMISSIONS."""
    persisted = json.loads(json.dumps(LEGACY_PERMISSIONS))
    assert 'admin' not in persisted

    template = fill_missing_permissions(persisted, DEFAULT_USER_PERMISSIONS)
    assert template['admin']['analytics'] is False
