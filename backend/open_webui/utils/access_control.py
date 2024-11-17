from typing import Optional, Union, List, Dict
from open_webui.apps.webui.models.groups import Groups


def get_permissions(
    user_id: str,
    default_permissions: Dict[str, bool] = {},
) -> dict:
    """
    Get all permissions for a user by combining the permissions of all groups the user is a member of.
    If a permission is defined in multiple groups, the most permissive value is used.
    """

    def merge_permissions(
        permissions: Dict[str, bool], new_permissions: Dict[str, bool]
    ) -> Dict[str, bool]:
        """Merge two permission dictionaries, keeping the most permissive value."""
        for key, value in new_permissions.items():
            if key not in permissions:
                permissions[key] = value
            else:
                permissions[key] = (
                    permissions[key] or value
                )  # Use the most permissive value

        return permissions

    user_groups = Groups.get_groups_by_member_id(user_id)
    user_permissions = default_permissions.copy()

    for group in user_groups:
        user_permissions = merge_permissions(user_permissions, group.permissions)

    return user_permissions


def has_permission(
    user_id: str,
    permission_key: str,
    default_permissions: Dict[str, bool] = {},
) -> bool:
    """
    Check if a user has a specific permission by checking the group permissions
    and falls back to default permissions if not found in any group.

    Permission keys can be hierarchical and separated by dots ('.').
    """

    def get_permission(permissions: Dict[str, bool], keys: List[str]) -> bool:
        """Traverse permissions dict using a list of keys (from dot-split permission_key)."""
        for key in keys:
            if key not in permissions:
                return False  # If any part of the hierarchy is missing, deny access
            permissions = permissions[key]  # Go one level deeper

        return bool(permissions)  # Return the boolean at the final level

    permission_hierarchy = permission_key.split(".")

    # Retrieve user group permissions
    user_groups = Groups.get_groups_by_member_id(user_id)

    for group in user_groups:
        group_permissions = group.permissions
        if get_permission(group_permissions, permission_hierarchy):
            return True

    # Check default permissions afterwards if the group permissions don't allow it
    return get_permission(default_permissions, permission_hierarchy)


def has_access(
    user_id: str,
    type: str = "write",
    access_control: Optional[dict] = None,
) -> bool:
    if access_control is None:
        return type == "read"

    user_groups = Groups.get_groups_by_member_id(user_id)
    user_group_ids = [group.id for group in user_groups]
    permission_access = access_control.get(type, {})
    permitted_group_ids = permission_access.get("group_ids", [])
    permitted_user_ids = permission_access.get("user_ids", [])

    return user_id in permitted_user_ids or any(
        group_id in permitted_group_ids for group_id in user_group_ids
    )
