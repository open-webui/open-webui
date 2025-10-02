import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from open_webui.utils.group import (
    BlockedGroupMatcher,
    GroupManager,
    is_in_blocked_groups,
)
from open_webui.models.groups import GroupModel, GroupForm, GroupUpdateForm


class TestBlockedGroupMatcher:
    def test_exact_match(self):
        matcher = BlockedGroupMatcher(["admin", "root", "superuser"])
        
        assert matcher.is_blocked("admin") is True
        assert matcher.is_blocked("root") is True
        assert matcher.is_blocked("superuser") is True
        assert matcher.is_blocked("user") is False
        assert matcher.is_blocked("Admin") is False

    def test_wildcard_match(self):
        matcher = BlockedGroupMatcher(["test-*", "dev_*", "?temp"])
        
        assert matcher.is_blocked("test-group") is True
        assert matcher.is_blocked("test-123") is True
        assert matcher.is_blocked("dev_team") is True
        assert matcher.is_blocked("atemp") is True
        assert matcher.is_blocked("1temp") is True
        assert matcher.is_blocked("temp") is False
        assert matcher.is_blocked("test") is False

    def test_regex_match(self):
        matcher = BlockedGroupMatcher([r"^admin-\d+$", r"test\[.*\]"])
        
        assert matcher.is_blocked("admin-123") is True
        assert matcher.is_blocked("admin-001") is True
        assert matcher.is_blocked("test[beta]") is True
        assert matcher.is_blocked("admin-") is False
        assert matcher.is_blocked("admin-abc") is False

    def test_invalid_regex_fallback(self):
        matcher = BlockedGroupMatcher(["test[invalid", "valid-*"])
        
        assert matcher.is_blocked("test[invalid") is False
        assert matcher.is_blocked("valid-group") is True

    def test_empty_patterns(self):
        matcher = BlockedGroupMatcher([])
        
        assert matcher.is_blocked("any-group") is False

    def test_none_and_empty_string_patterns(self):
        matcher = BlockedGroupMatcher(["", None, "valid"])
        
        assert matcher.is_blocked("valid") is True
        assert matcher.is_blocked("") is False

    def test_mixed_patterns(self):
        matcher = BlockedGroupMatcher([
            "exact-match",
            "wildcard-*",
            r"^regex-\d+$",
        ])
        
        assert matcher.is_blocked("exact-match") is True
        assert matcher.is_blocked("wildcard-test") is True
        assert matcher.is_blocked("regex-123") is True
        assert matcher.is_blocked("other") is False

    def test_is_regex_pattern(self):
        assert BlockedGroupMatcher._is_regex_pattern("^test$") is True
        assert BlockedGroupMatcher._is_regex_pattern("test[abc]") is True
        assert BlockedGroupMatcher._is_regex_pattern("test(a|b)") is True
        assert BlockedGroupMatcher._is_regex_pattern("test{2,3}") is True
        assert BlockedGroupMatcher._is_regex_pattern("test+") is True
        assert BlockedGroupMatcher._is_regex_pattern("test\\d") is True
        
        assert BlockedGroupMatcher._is_regex_pattern("test-*") is False
        assert BlockedGroupMatcher._is_regex_pattern("simple") is False


class TestGroupManager:
    @pytest.fixture
    def manager(self):
        return GroupManager()

    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = "user-123"
        user.name = "Test User"
        return user

    @pytest.fixture
    def mock_group(self):
        group = Mock(spec=GroupModel)
        group.id = "group-1"
        group.name = "test-group"
        group.description = "Test Group"
        group.user_ids = []
        group.permissions = {"read": True}
        return group

    @patch("open_webui.utils.group.auth_manager_config")
    def test_parse_blocked_groups_config_empty(self, mock_config, manager):
        mock_config.BLOCKED_GROUPS = "[]"
        mock_config.OAUTH_BLOCKED_GROUPS = "[]"
        
        result = manager._parse_blocked_groups_config()
        
        assert isinstance(result, BlockedGroupMatcher)
        assert result.is_blocked("any-group") is False

    @patch("open_webui.utils.group.auth_manager_config")
    def test_parse_blocked_groups_config_valid(self, mock_config, manager):
        mock_config.BLOCKED_GROUPS = '["admin", "root"]'
        mock_config.OAUTH_BLOCKED_GROUPS = '["oauth-blocked"]'
        
        result = manager._parse_blocked_groups_config()
        
        assert isinstance(result, BlockedGroupMatcher)
        assert result.is_blocked("admin") is True
        assert result.is_blocked("root") is True
        assert result.is_blocked("oauth-blocked") is True

    @patch("open_webui.utils.group.auth_manager_config")
    def test_parse_blocked_groups_config_invalid_json(self, mock_config, manager):
        mock_config.BLOCKED_GROUPS = "invalid json"
        mock_config.OAUTH_BLOCKED_GROUPS = "[]"
        
        result = manager._parse_blocked_groups_config()
        
        assert isinstance(result, BlockedGroupMatcher)
        assert result.is_blocked("any-group") is False

    @patch("open_webui.utils.group.auth_manager_config")
    def test_parse_blocked_groups_config_wrong_type(self, mock_config, manager):
        mock_config.BLOCKED_GROUPS = '{"not": "a list"}'
        mock_config.OAUTH_BLOCKED_GROUPS = "[]"
        
        result = manager._parse_blocked_groups_config()
        
        assert isinstance(result, BlockedGroupMatcher)

    @patch("open_webui.utils.group.Users.get_super_admin_user")
    def test_determine_creator_id_admin_exists(self, mock_get_admin, manager, mock_user):
        admin = Mock()
        admin.id = "admin-456"
        mock_get_admin.return_value = admin
        
        result = manager._determine_creator_id(mock_user)
        
        assert result == "admin-456"
        mock_get_admin.assert_called_once()

    @patch("open_webui.utils.group.Users.get_super_admin_user")
    def test_determine_creator_id_no_admin(self, mock_get_admin, manager, mock_user):
        mock_get_admin.return_value = None
        
        result = manager._determine_creator_id(mock_user)
        
        assert result == "user-123"

    @patch("open_webui.utils.group.Groups.insert_new_group")
    def test_create_group_success(self, mock_insert, manager):
        created_group = Mock()
        created_group.id = "new-group-id"
        mock_insert.return_value = created_group
        
        result = manager._create_group("new-group", "creator-id", {"read": True})
        
        assert result is True
        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][0] == "creator-id"
        assert isinstance(call_args[0][1], GroupForm)

    @patch("open_webui.utils.group.Groups.insert_new_group")
    def test_create_group_failure(self, mock_insert, manager):
        mock_insert.return_value = None
        
        result = manager._create_group("new-group", "creator-id", {"read": True})
        
        assert result is False

    @patch("open_webui.utils.group.Groups.insert_new_group")
    def test_create_group_exception(self, mock_insert, manager):
        mock_insert.side_effect = Exception("Database error")
        
        result = manager._create_group("new-group", "creator-id", {"read": True})
        
        assert result is False

    @patch("open_webui.utils.group.Groups.get_groups")
    def test_ensure_groups_exist_creation_disabled(
        self, mock_get_groups, manager, mock_user
    ):
        existing_groups = [Mock(name="existing")]
        mock_get_groups.return_value = existing_groups
        
        result = manager._ensure_groups_exist(False, ["new-group"], {}, mock_user)
        
        assert result == existing_groups
        assert mock_get_groups.call_count == 1

    @patch("open_webui.utils.group.Groups.get_groups")
    @patch("open_webui.utils.group.Users.get_super_admin_user")
    @patch("open_webui.utils.group.Groups.insert_new_group")
    def test_ensure_groups_exist_creates_missing(
        self, mock_insert, mock_get_admin, mock_get_groups, manager, mock_user
    ):
        existing = Mock()
        existing.name = "existing-group"
        mock_get_groups.side_effect = [[existing], [existing, Mock(name="new-group")]]
        
        admin = Mock()
        admin.id = "admin-id"
        mock_get_admin.return_value = admin
        
        created_group = Mock()
        created_group.id = "new-id"
        mock_insert.return_value = created_group
        
        result = manager._ensure_groups_exist(
            True, ["existing-group", "new-group"], {"read": True}, mock_user
        )
        
        assert mock_insert.call_count == 1
        assert mock_get_groups.call_count == 2

    @patch("open_webui.utils.group.Groups.update_group_by_id")
    def test_update_group_membership(self, mock_update, manager, mock_group):
        manager._update_group_membership(mock_group, ["user-1", "user-2"], {"read": True})
        
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[1]["id"] == "group-1"
        assert isinstance(call_args[1]["form_data"], GroupUpdateForm)

    @patch("open_webui.utils.group.Groups.update_group_by_id")
    def test_update_group_membership_no_permissions(
        self, mock_update, manager, mock_group
    ):
        mock_group.permissions = None
        
        manager._update_group_membership(mock_group, ["user-1"], {"default": True})
        
        mock_update.assert_called_once()

    def test_sync_group_memberships_no_given_groups(self, manager, mock_user, mock_group):
        manager._sync_group_memberships(
            mock_user,
            [mock_group],
            [mock_group],
            [],
            BlockedGroupMatcher([]),
            {},
        )

    @patch("open_webui.utils.group.Groups.update_group_by_id")
    def test_sync_group_memberships_remove_user(
        self, mock_update, manager, mock_user, mock_group
    ):
        mock_group.user_ids = ["user-123", "other-user"]
        current_groups = [mock_group]
        available_groups = [mock_group]
        given_groups = []
        
        manager._sync_group_memberships(
            mock_user,
            current_groups,
            available_groups,
            ["other-group"],
            BlockedGroupMatcher([]),
            {"read": True},
        )
        
        mock_update.assert_called_once()

    @patch("open_webui.utils.group.Groups.update_group_by_id")
    def test_sync_group_memberships_add_user(
        self, mock_update, manager, mock_user, mock_group
    ):
        mock_group.user_ids = ["other-user"]
        current_groups = []
        available_groups = [mock_group]
        given_groups = ["test-group"]
        
        manager._sync_group_memberships(
            mock_user,
            current_groups,
            available_groups,
            given_groups,
            BlockedGroupMatcher([]),
            {"read": True},
        )
        
        mock_update.assert_called_once()

    @patch("open_webui.utils.group.Groups.update_group_by_id")
    def test_sync_group_memberships_blocked_group(
        self, mock_update, manager, mock_user, mock_group
    ):
        mock_group.user_ids = ["other-user"]
        current_groups = []
        available_groups = [mock_group]
        given_groups = ["test-group"]
        blocked_matcher = BlockedGroupMatcher(["test-group"])
        
        manager._sync_group_memberships(
            mock_user,
            current_groups,
            available_groups,
            given_groups,
            blocked_matcher,
            {"read": True},
        )
        
        mock_update.assert_not_called()

    @patch("open_webui.utils.group.auth_manager_config")
    @patch("open_webui.utils.group.Groups.get_groups_by_member_id")
    @patch("open_webui.utils.group.Groups.get_groups")
    def test_sync_user_groups_integration(
        self, mock_get_groups, mock_get_member_groups, mock_config, manager, mock_user, mock_group
    ):
        mock_config.ENABLE_GROUP_MANAGEMENT = True
        mock_config.BLOCKED_GROUPS = "[]"
        mock_config.OAUTH_BLOCKED_GROUPS = "[]"
        mock_config.ENABLE_GROUP_CREATION = False
        
        mock_get_member_groups.return_value = []
        mock_get_groups.return_value = [mock_group]

        manager.sync_user_groups(["test-group"], mock_user, {"read": True}, False)
        
        mock_get_member_groups.assert_called_once_with(mock_user.id)
        mock_get_groups.assert_called()

    @patch("open_webui.utils.group.auth_manager_config")
    @patch("open_webui.utils.group.Groups.get_groups_by_member_id")
    def test_sync_user_groups_disabled(
        self, mock_get_member_groups, mock_config, manager, mock_user
    ):
        mock_config.ENABLE_GROUP_MANAGEMENT = False
        
        manager.sync_user_groups(["test-group"], mock_user, {"read": True})
        
        mock_get_member_groups.assert_not_called()

    def test_log_group_sync_status(self, manager, mock_user, mock_group):
        group1 = Mock(spec=GroupModel)
        group1.name = "group1"
        group2 = Mock(spec=GroupModel)
        group2.name = "group2"
        
        manager._log_group_sync_status(
            ["external-group1", "external-group2"],
            [group1],
            [group1, group2],
        )

    @patch("open_webui.utils.group.Groups.update_group_by_id")
    def test_sync_group_memberships_user_already_in_group(
        self, mock_update, manager, mock_user, mock_group
    ):
        mock_group.user_ids = ["user-123"]
        current_groups = [mock_group]
        available_groups = [mock_group]
        given_groups = ["test-group"]
        
        manager._sync_group_memberships(
            mock_user,
            current_groups,
            available_groups,
            given_groups,
            BlockedGroupMatcher([]),
            {"read": True},
        )
        
        mock_update.assert_not_called()

    @patch("open_webui.utils.group.Groups.update_group_by_id")
    def test_sync_group_memberships_group_not_available(
        self, mock_update, manager, mock_user, mock_group
    ):
        current_groups = []
        available_groups = []
        given_groups = ["non-existent-group"]
        
        manager._sync_group_memberships(
            mock_user,
            current_groups,
            available_groups,
            given_groups,
            BlockedGroupMatcher([]),
            {"read": True},
        )
        
        mock_update.assert_not_called()

    @patch("open_webui.utils.group.Groups.update_group_by_id")
    def test_sync_group_memberships_remove_blocked_group(
        self, mock_update, manager, mock_user, mock_group
    ):
        mock_group.user_ids = ["user-123"]
        mock_group.name = "blocked-group"
        current_groups = [mock_group]
        available_groups = [mock_group]
        given_groups = ["other-group"]
        blocked_matcher = BlockedGroupMatcher(["blocked-group"])
        
        manager._sync_group_memberships(
            mock_user,
            current_groups,
            available_groups,
            given_groups,
            blocked_matcher,
            {"read": True},
        )
        
        mock_update.assert_not_called()


class TestIsInBlockedGroups:
    def test_backward_compatibility(self):
        groups = ["admin", "test-*", r"^dev-\d+$"]
        
        assert is_in_blocked_groups("admin", groups) is True
        assert is_in_blocked_groups("test-123", groups) is True
        assert is_in_blocked_groups("dev-456", groups) is True
        assert is_in_blocked_groups("user", groups) is False

    def test_empty_list(self):
        assert is_in_blocked_groups("any-group", []) is False

    def test_none_list(self):
        assert is_in_blocked_groups("any-group", None) is False