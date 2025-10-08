from typing import Optional, Set, Union, List, Dict, Any
from open_webui.models.users import Users, UserModel
from open_webui.models.groups import Groups


from open_webui.config import DEFAULT_USER_PERMISSIONS
import json


def fill_missing_permissions(
    permissions: Dict[str, Any], default_permissions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Recursively fills in missing properties in the permissions dictionary
    using the default permissions as a template.
    """
    for key, value in default_permissions.items():
        if key not in permissions:
            permissions[key] = value
        elif isinstance(value, dict) and isinstance(
            permissions[key], dict
        ):  # Both are nested dictionaries
            permissions[key] = fill_missing_permissions(permissions[key], value)

    return permissions


def _get_role_default_permissions(
    role: Optional[str], default_permissions: Dict[str, Any]
) -> Dict[str, Any]:
    role_permissions = json.loads(json.dumps(default_permissions))

    if role == "knowledge":
        workspace_permissions = role_permissions.get("workspace", {})
        workspace_permissions.setdefault("knowledge", False)
        for key in workspace_permissions.keys():
            workspace_permissions[key] = key == "knowledge"
        role_permissions["workspace"] = workspace_permissions

        chat_permissions = role_permissions.get("chat", {})
        for key in chat_permissions.keys():
            chat_permissions[key] = False
        role_permissions["chat"] = chat_permissions

        feature_permissions = role_permissions.get("features", {})
        for key in feature_permissions.keys():
            feature_permissions[key] = False
        role_permissions["features"] = feature_permissions

    return role_permissions


def get_permissions(
    user_id: str,
    default_permissions: Dict[str, Any],
    role: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get all permissions for a user by combining the permissions of all groups the user is a member of.
    If a permission is defined in multiple groups, the most permissive value is used (True > False).
    Permissions are nested in a dict with the permission key as the key and a boolean as the value.
    """

    def combine_permissions(
        permissions: Dict[str, Any], group_permissions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine permissions from multiple groups by taking the most permissive value."""
        for key, value in group_permissions.items():
            if isinstance(value, dict):
                if key not in permissions:
                    permissions[key] = {}
                permissions[key] = combine_permissions(permissions[key], value)
            else:
                if key not in permissions:
                    permissions[key] = value
                else:
                    permissions[key] = (
                        permissions[key] or value
                    )  # Use the most permissive value (True > False)
        return permissions

    user_groups = Groups.get_groups_by_member_id(user_id)

    role_permissions = fill_missing_permissions(
        _get_role_default_permissions(role, default_permissions),
        DEFAULT_USER_PERMISSIONS,
    )

    # Deep copy default permissions to avoid modifying the original dict
    permissions = json.loads(json.dumps(role_permissions))

    # Combine permissions from all user groups
    for group in user_groups:
        permissions = combine_permissions(permissions, group.permissions or {})

    # Ensure all fields from default_permissions are present and filled in
    permissions = fill_missing_permissions(permissions, role_permissions)

    return permissions


def has_permission(
    user_id: str,
    permission_key: str,
    default_permissions: Dict[str, Any] = {},
    user_role: Optional[str] = None,
) -> bool:
    """
    Check if a user has a specific permission by checking the group permissions
    and fall back to default permissions if not found in any group.

    Permission keys can be hierarchical and separated by dots ('.').
    """

    def get_permission(permissions: Dict[str, Any], keys: List[str]) -> bool:
        """Traverse permissions dict using a list of keys (from dot-split permission_key)."""
        for key in keys:
            if key not in permissions:
                return False  # If any part of the hierarchy is missing, deny access
            permissions = permissions[key]  # Traverse one level deeper

        return bool(permissions)  # Return the boolean at the final level

    permission_hierarchy = permission_key.split(".")

    # Retrieve user group permissions
    user_groups = Groups.get_groups_by_member_id(user_id)

    for group in user_groups:
        if get_permission(group.permissions or {}, permission_hierarchy):
            return True

    # Check default permissions afterward if the group permissions don't allow it
    role_permissions = fill_missing_permissions(
        _get_role_default_permissions(user_role, default_permissions),
        DEFAULT_USER_PERMISSIONS,
    )
    return get_permission(role_permissions, permission_hierarchy)


def has_access(
    user_id: str,
    type: str = "write",
    access_control: Optional[dict] = None,
    user_group_ids: Optional[Set[str]] = None,
) -> bool:
    if access_control is None:
        return type == "read"

    if user_group_ids is None:
        user_groups = Groups.get_groups_by_member_id(user_id)
        user_group_ids = {group.id for group in user_groups}

    permission_access = access_control.get(type, {})
    permitted_group_ids = permission_access.get("group_ids", [])
    permitted_user_ids = permission_access.get("user_ids", [])

    return user_id in permitted_user_ids or any(
        group_id in permitted_group_ids for group_id in user_group_ids
    )


# Get all users with access to a resource
def get_users_with_access(
    type: str = "write", access_control: Optional[dict] = None
) -> list[UserModel]:
    if access_control is None:
        result = Users.get_users()
        return result.get("users", [])

    permission_access = access_control.get(type, {})
    permitted_group_ids = permission_access.get("group_ids", [])
    permitted_user_ids = permission_access.get("user_ids", [])

    user_ids_with_access = set(permitted_user_ids)

    for group_id in permitted_group_ids:
        group_user_ids = Groups.get_group_user_ids_by_id(group_id)
        if group_user_ids:
            user_ids_with_access.update(group_user_ids)

    return Users.get_users_by_user_ids(list(user_ids_with_access))
