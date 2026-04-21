from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_webui.utils.access_control import (
    enforce_knowledge_upload_limits,
    get_permission_value,
    get_permissions,
)


def _group(permissions: dict):
    return SimpleNamespace(permissions=permissions)


def _user(role: str = 'user', user_id: str = 'user1'):
    return SimpleNamespace(id=user_id, role=role)


GROUPS_PATH = 'open_webui.utils.access_control.Groups.get_groups_by_member_id'
CONFIG_GET_PATH = 'open_webui.utils.access_control.Config.get'
FILE_COUNT_PATH = 'open_webui.utils.access_control.Knowledges.get_file_count_by_id'


class TestCombinePermissionsIntegers:
    """get_permissions merges integer-valued permissions using most-permissive semantics."""

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_single_group_integer_limit(self, mock_groups):
        mock_groups.return_value = [_group({'workspace': {'knowledge_max_count': 10}})]
        result = await get_permissions('user1', {'workspace': {'knowledge_max_count': None}})
        assert result['workspace']['knowledge_max_count'] == 10

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_most_permissive_takes_higher_limit(self, mock_groups):
        mock_groups.return_value = [
            _group({'workspace': {'knowledge_max_count': 10}}),
            _group({'workspace': {'knowledge_max_count': 25}}),
        ]
        result = await get_permissions('user1', {'workspace': {'knowledge_max_count': None}})
        assert result['workspace']['knowledge_max_count'] == 25

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_zero_means_unlimited_always_wins(self, mock_groups):
        mock_groups.return_value = [
            _group({'workspace': {'knowledge_max_count': 10}}),
            _group({'workspace': {'knowledge_max_count': 0}}),
        ]
        result = await get_permissions('user1', {'workspace': {'knowledge_max_count': None}})
        assert result['workspace']['knowledge_max_count'] == 0

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_none_group_value_is_skipped(self, mock_groups):
        mock_groups.return_value = [
            _group({'workspace': {'knowledge_max_count': None}}),
            _group({'workspace': {'knowledge_max_count': 15}}),
        ]
        result = await get_permissions('user1', {'workspace': {'knowledge_max_count': None}})
        assert result['workspace']['knowledge_max_count'] == 15

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_boolean_permissions_unaffected(self, mock_groups):
        mock_groups.return_value = [
            _group({'workspace': {'knowledge': True, 'knowledge_max_count': 10}}),
            _group({'workspace': {'knowledge': False, 'knowledge_max_count': 5}}),
        ]
        result = await get_permissions('user1', {'workspace': {'knowledge': False, 'knowledge_max_count': None}})
        assert result['workspace']['knowledge'] is True
        assert result['workspace']['knowledge_max_count'] == 10


class TestGetPermissionValue:
    """get_permission_value returns the raw resolved value for a permission key."""

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_returns_none_when_no_groups_and_no_default(self, mock_groups):
        mock_groups.return_value = []
        assert await get_permission_value('user1', 'workspace.knowledge_max_count') is None

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_falls_back_to_default_permissions(self, mock_groups):
        mock_groups.return_value = []
        result = await get_permission_value(
            'user1', 'workspace.knowledge_max_count',
            {'workspace': {'knowledge_max_count': 20}},
        )
        assert result == 20

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_group_value_overrides_default(self, mock_groups):
        mock_groups.return_value = [_group({'workspace': {'knowledge_max_count': 5}})]
        result = await get_permission_value(
            'user1', 'workspace.knowledge_max_count',
            {'workspace': {'knowledge_max_count': 20}},
        )
        assert result == 5

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_most_permissive_across_groups(self, mock_groups):
        mock_groups.return_value = [
            _group({'workspace': {'knowledge_max_count': 5}}),
            _group({'workspace': {'knowledge_max_count': 30}}),
        ]
        assert await get_permission_value('user1', 'workspace.knowledge_max_count') == 30

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_zero_unlimited_wins_over_any_limit(self, mock_groups):
        mock_groups.return_value = [
            _group({'workspace': {'knowledge_max_count': 5}}),
            _group({'workspace': {'knowledge_max_count': 0}}),
        ]
        assert await get_permission_value('user1', 'workspace.knowledge_max_count') == 0

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_missing_key_returns_none(self, mock_groups):
        mock_groups.return_value = [_group({'workspace': {'knowledge': True}})]
        assert await get_permission_value('user1', 'workspace.knowledge_max_count') is None

    @pytest.mark.anyio
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_size_limit_key(self, mock_groups):
        mock_groups.return_value = [_group({'workspace': {'knowledge_max_size': 50}})]
        assert await get_permission_value('user1', 'workspace.knowledge_max_size') == 50


class TestEnforceKnowledgeUploadLimits:
    """enforce_knowledge_upload_limits gates linking a file to a knowledge base."""

    @pytest.mark.anyio
    @patch(CONFIG_GET_PATH, new_callable=AsyncMock)
    async def test_admin_bypasses_without_checking_anything(self, mock_config_get):
        # No Groups/Knowledges patches — if the admin bypass didn't short-circuit,
        # these unmocked calls would blow up, so a clean return proves the bypass.
        await enforce_knowledge_upload_limits(_user(role='admin'), 'kb1', 999_999_999)
        mock_config_get.assert_not_called()

    @pytest.mark.anyio
    @patch(CONFIG_GET_PATH, new_callable=AsyncMock)
    async def test_none_user_bypasses(self, mock_config_get):
        await enforce_knowledge_upload_limits(None, 'kb1', 999_999_999)
        mock_config_get.assert_not_called()

    @pytest.mark.anyio
    @patch(FILE_COUNT_PATH, new_callable=AsyncMock)
    @patch(CONFIG_GET_PATH, new_callable=AsyncMock)
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_passes_under_both_limits(self, mock_groups, mock_config_get, mock_file_count):
        mock_groups.return_value = []
        mock_config_get.return_value = {'workspace': {'knowledge_max_count': 5, 'knowledge_max_size': 50}}
        mock_file_count.return_value = 2

        await enforce_knowledge_upload_limits(_user(), 'kb1', 10 * 1024 * 1024)

    @pytest.mark.anyio
    @patch(FILE_COUNT_PATH, new_callable=AsyncMock)
    @patch(CONFIG_GET_PATH, new_callable=AsyncMock)
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_raises_when_count_limit_reached(self, mock_groups, mock_config_get, mock_file_count):
        mock_groups.return_value = []
        mock_config_get.return_value = {'workspace': {'knowledge_max_count': 5, 'knowledge_max_size': None}}
        mock_file_count.return_value = 5

        with pytest.raises(ValueError, match='5 files maximum'):
            await enforce_knowledge_upload_limits(_user(), 'kb1', 1024)

    @pytest.mark.anyio
    @patch(FILE_COUNT_PATH, new_callable=AsyncMock)
    @patch(CONFIG_GET_PATH, new_callable=AsyncMock)
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_raises_when_file_too_large(self, mock_groups, mock_config_get, mock_file_count):
        mock_groups.return_value = []
        mock_config_get.return_value = {'workspace': {'knowledge_max_count': None, 'knowledge_max_size': 25}}

        with pytest.raises(ValueError, match='25 MB limit'):
            await enforce_knowledge_upload_limits(_user(), 'kb1', 26 * 1024 * 1024)
        mock_file_count.assert_not_called()

    @pytest.mark.anyio
    @patch(FILE_COUNT_PATH, new_callable=AsyncMock)
    @patch(CONFIG_GET_PATH, new_callable=AsyncMock)
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_zero_count_means_unlimited(self, mock_groups, mock_config_get, mock_file_count):
        mock_groups.return_value = []
        mock_config_get.return_value = {'workspace': {'knowledge_max_count': 0, 'knowledge_max_size': None}}

        await enforce_knowledge_upload_limits(_user(), 'kb1', 1024)
        mock_file_count.assert_not_called()

    @pytest.mark.anyio
    @patch(CONFIG_GET_PATH, new_callable=AsyncMock)
    @patch(GROUPS_PATH, new_callable=AsyncMock)
    async def test_zero_size_means_unlimited(self, mock_groups, mock_config_get):
        mock_groups.return_value = []
        mock_config_get.return_value = {'workspace': {'knowledge_max_count': None, 'knowledge_max_size': 0}}

        await enforce_knowledge_upload_limits(_user(), 'kb1', 999_999_999)
