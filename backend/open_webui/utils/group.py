import logging
import sys
import json
import re
import fnmatch

from open_webui.models.users import Users
from open_webui.models.groups import Groups, GroupModel, GroupUpdateForm, GroupForm
from open_webui.config import (
    ENABLE_GROUP_MANAGEMENT,
    ENABLE_GROUP_CREATION,
    BLOCKED_GROUPS,
    OAUTH_BLOCKED_GROUPS,
    AppConfig,
)
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

auth_manager_config = AppConfig()
auth_manager_config.ENABLE_GROUP_MANAGEMENT = ENABLE_GROUP_MANAGEMENT
auth_manager_config.ENABLE_GROUP_CREATION = ENABLE_GROUP_CREATION
auth_manager_config.BLOCKED_GROUPS = BLOCKED_GROUPS
auth_manager_config.OAUTH_BLOCKED_GROUPS = OAUTH_BLOCKED_GROUPS


class BlockedGroupMatcher:
    """Compiled matcher for blocked group patterns with optimized matching."""

    def __init__(self, patterns: list[str]):
        self.exact_matches = set()
        self.wildcards = []
        self.regexes = []

        for pattern in patterns:
            if not pattern:
                continue

            if self._is_regex_pattern(pattern):
                try:
                    self.regexes.append(re.compile(pattern))
                except re.error as e:
                    log.warning(f"Invalid regex pattern '{pattern}': {e}")
            elif "*" in pattern or "?" in pattern:
                self.wildcards.append(pattern)
            else:
                self.exact_matches.add(pattern)

    @staticmethod
    def _is_regex_pattern(pattern: str) -> bool:
        """Check if pattern contains regex-specific characters."""
        return any(
            c in pattern
            for c in ["^", "$", "[", "]", "(", ")", "{", "}", "+", "\\", "|"]
        )

    def is_blocked(self, group_name: str) -> bool:
        """Check if group name matches any blocked pattern."""
        if group_name in self.exact_matches:
            return True

        for pattern in self.wildcards:
            if fnmatch.fnmatch(group_name, pattern):
                return True

        for regex in self.regexes:
            if regex.search(group_name):
                return True

        return False


class GroupManager:
    """Manages group synchronization for users with OAuth/SCIM integration."""

    def sync_user_groups(
            self,
            given_groups: list[str],
            user,
            default_permissions: dict,
            enable_group_creation = auth_manager_config.ENABLE_GROUP_CREATION,
    ) -> None:
        """
        Synchronize user's group memberships based on external groups.

        Args:
            given_groups: List of group names from external auth provider
            user: User object to synchronize groups for
            default_permissions: Default permissions for newly created groups
            enable_group_creation: if false given_groups that do not already exist will not be created
        """
        if auth_manager_config.ENABLE_GROUP_MANAGEMENT:
            log.debug("Running Group management")

            blocked_matcher = self._parse_blocked_groups_config()

            user_current_groups = Groups.get_groups_by_member_id(user.id)
            all_available_groups = self._ensure_groups_exist(
                enable_group_creation, given_groups, default_permissions, user
            )

            self._log_group_sync_status(given_groups, user_current_groups, all_available_groups)

            self._sync_group_memberships(
                user,
                user_current_groups,
                all_available_groups,
                given_groups,
                blocked_matcher,
                default_permissions,
            )
        else:
            log.debug("Group management disabled")

    def _parse_blocked_groups_config(self) -> BlockedGroupMatcher:
        """Parse and combine blocked groups from configuration."""
        blocked_groups = []

        try:
            parsed = json.loads(auth_manager_config.BLOCKED_GROUPS) if auth_manager_config.BLOCKED_GROUPS else []
            if isinstance(parsed, list):
                blocked_groups = parsed
            else:
                log.warning(f"BLOCKED_GROUPS is not a list: {type(parsed)}")
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON in BLOCKED_GROUPS: {e}")

        # Support the legacy OAUTH_BLOCKED_GROUPS value.  This should be phased out for the generic BLOCKED_GROUPS value
        try:
            oauth_blocked = json.loads(auth_manager_config.OAUTH_BLOCKED_GROUPS) if auth_manager_config.OAUTH_BLOCKED_GROUPS else []
            if isinstance(oauth_blocked, list):
                blocked_groups.extend(oauth_blocked)
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON in OAUTH_BLOCKED_GROUPS: {e}")

        return BlockedGroupMatcher(blocked_groups)

    def _ensure_groups_exist(
            self,
            enable_group_creation: bool,
            given_groups: list[str],
            default_permissions: dict,
            user
    ) -> list[GroupModel]:
        """Create missing groups if creation is enabled."""
        if not enable_group_creation:
            log.debug("Group creation disabled")
            return Groups.get_groups()

        all_available_groups = Groups.get_groups()
        existing_names = {g.name for g in all_available_groups}

        log.debug("Checking for missing groups to create...")
        creator_id = self._determine_creator_id(user)
        groups_created = False

        for group_name in given_groups:
            if group_name not in existing_names:
                if self._create_group(group_name, creator_id, default_permissions):
                    groups_created = True
                    existing_names.add(group_name)

        if groups_created:
            all_available_groups = Groups.get_groups()
            log.debug("Refreshed list of all available groups after creation.")

        return all_available_groups

    def _determine_creator_id(self, fallback_user) -> str:
        """Get admin user ID or fallback to provided user."""
        admin_user = Users.get_super_admin_user()
        creator_id = admin_user.id if admin_user else fallback_user.id
        log.debug(f"Using creator ID {creator_id} for potential group creation")
        return creator_id

    def _create_group(
            self, group_name: str, creator_id: str, default_permissions: dict
    ) -> bool:
        """Create a single group."""
        log.info(f"Group '{group_name}' not found. Creating group...")
        try:
            new_group_form = GroupForm(
                name=group_name,
                description=f"Group '{group_name}' created automatically.",
                permissions=default_permissions,
                user_ids=[],
            )
            created_group = Groups.insert_new_group(creator_id, new_group_form)
            if created_group:
                log.info(
                    f"Successfully created group '{group_name}' with ID {created_group.id}"
                )
                return True
            else:
                log.error(f"Failed to create group '{group_name}'")
                return False
        except Exception as e:
            log.error(f"Error creating group '{group_name}': {e}")
            return False

    def _log_group_sync_status(
            self,
            given_groups: list[str],
            user_current_groups: list[GroupModel],
            all_available_groups: list[GroupModel],
    ) -> None:
        """Log current state of group synchronization."""
        log.debug(f"Given user groups: {given_groups}")
        log.debug(f"User's current groups: {[g.name for g in user_current_groups]}")
        log.debug(
            f"All groups available in OpenWebUI: {[g.name for g in all_available_groups]}"
        )

    def _sync_group_memberships(
            self,
            user,
            user_current_groups: list[GroupModel],
            all_available_groups: list[GroupModel],
            given_groups: list[str],
            blocked_matcher: BlockedGroupMatcher,
            default_permissions: dict,
    ) -> None:
        """Efficiently sync group memberships in a single pass."""
        if not given_groups:
            return

        given_groups_set = set(given_groups)
        current_groups_map = {g.name: g for g in user_current_groups}
        available_groups_map = {g.name: g for g in all_available_groups}

        for group_name, group_model in current_groups_map.items():
            if (
                    group_name not in given_groups_set
                    and not blocked_matcher.is_blocked(group_name)
            ):
                log.debug(
                    f"Removing user from group {group_name} as it is no longer in their groups"
                )
                user_ids = [uid for uid in group_model.user_ids if uid != user.id]
                self._update_group_membership(
                    group_model, user_ids, default_permissions
                )

        for group_name in given_groups_set:
            if (
                    group_name not in current_groups_map
                    and group_name in available_groups_map
                    and not blocked_matcher.is_blocked(group_name)
            ):
                log.debug(
                    f"Adding user to group {group_name} as it was found in their given groups"
                )
                group_model = available_groups_map[group_name]
                user_ids = group_model.user_ids + [user.id]
                self._update_group_membership(
                    group_model, user_ids, default_permissions
                )

    def _update_group_membership(
            self, group_model: GroupModel, user_ids: list[str], default_permissions: dict
    ) -> None:
        """Update group membership with given user IDs."""
        permissions = group_model.permissions or default_permissions

        update_form = GroupUpdateForm(
            name=group_model.name,
            description=group_model.description,
            permissions=permissions,
            user_ids=user_ids,
        )
        Groups.update_group_by_id(
            id=group_model.id, form_data=update_form, overwrite=False
        )


def is_in_blocked_groups(group_name: str, groups: list) -> bool:
    """
    Check if a group name matches any blocked pattern.
    Supports exact matches, shell-style wildcards (*, ?), and regex patterns.

    Deprecated: Use BlockedGroupMatcher.is_blocked() instead for better performance.

    Args:
        group_name: The group name to check
        groups: List of patterns to match against

    Returns:
        True if the group is blocked, False otherwise
    """
    if not groups:
        return False

    matcher = BlockedGroupMatcher(groups)
    return matcher.is_blocked(group_name)
