import json
import logging
from typing import Optional, Union, List, Dict, Any
from open_webui.models.users import Users, UserModel
from open_webui.models.groups import Groups
from open_webui.config import DEFAULT_USER_PERMISSIONS

log = logging.getLogger(__name__)

def fill_missing_permissions(
    permissions: Optional[Dict[str, Any]], default_permissions: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Recursively fills in missing properties in the permissions dictionary
    using the default permissions as a template.
    """
    if permissions is None:
        permissions = {}
    if default_permissions is None:
        default_permissions = {}

    for key, value in default_permissions.items():
        if key not in permissions:
            permissions[key] = value
        elif isinstance(value, dict) and isinstance(
            permissions[key], dict
        ):  # Both are nested dictionaries
            permissions[key] = fill_missing_permissions(permissions[key], value)

    return permissions

def get_permissions(
    user_id: str,
    default_permissions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get all permissions for a user by combining the permissions of all groups the user is a member of.
    If a permission is defined in multiple groups, the most permissive value is used (True > False).
    Permissions are nested in a dict with the permission key as the key and a boolean as the value.
    """
    try:
        # 確保 default_permissions 不為 None
        if default_permissions is None:
            default_permissions = {}

        # 取得使用者的群組
        user_groups = Groups.get_groups_by_member_id(user_id)
        
        # 深度複製預設權限避免修改原始資料
        permissions = json.loads(json.dumps(default_permissions))

        # 遍歷所有群組並合併權限
        for group in user_groups:
            if not hasattr(group, 'permissions'):
                continue
            if not group.permissions:
                continue
            permissions = combine_permissions(permissions, group.permissions)

        # 確保所有來自預設權限的欄位都存在並填充
        return fill_missing_permissions(permissions, default_permissions)
    except Exception as e:
        log.error(f"Error getting permissions for user {user_id}: {str(e)}")
        return default_permissions or {}

def combine_permissions(
    permissions: Dict[str, Any],
    group_permissions: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Combine permissions from multiple groups by taking the most permissive value."""
    # 確保基礎情況處理
    if not permissions:
        permissions = {}
    if not group_permissions:
        return permissions

    try:
        for key, value in group_permissions.items():
            if value is None:  # 跳過None值
                continue
            if isinstance(value, dict):
                if key not in permissions:
                    permissions[key] = {}
                permissions[key] = combine_permissions(permissions.get(key, {}), value)
            else:
                current_value = permissions.get(key, False)
                permissions[key] = current_value or value  # 使用最寬鬆的權限（True > False）
    except AttributeError:
        log.warning(f"Received invalid permissions format: {group_permissions}")
    except Exception as e:
        log.error(f"Error combining permissions: {str(e)}")
    
    return permissions

def has_permission(
    user_id: str,
    permission_key: str,
    default_permissions: Optional[Dict[str, Any]] = None,
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

    try:
        permission_hierarchy = permission_key.split(".")
        user_groups = Groups.get_groups_by_member_id(user_id)

        # 檢查群組權限
        for group in user_groups:
            if not hasattr(group, 'permissions') or not group.permissions:
                continue
            if get_permission(group.permissions, permission_hierarchy):
                return True

        # 如果群組權限不允許，檢查預設權限
        if default_permissions is None:
            default_permissions = DEFAULT_USER_PERMISSIONS or {}
        
        default_permissions = fill_missing_permissions(
            default_permissions, DEFAULT_USER_PERMISSIONS
        )
        return get_permission(default_permissions, permission_hierarchy)
    except Exception as e:
        log.error(f"Error checking permission '{permission_key}' for user {user_id}: {str(e)}")
        return False

def has_access(
    user_id: str,
    type: str = "write",
    access_control: Optional[dict] = None,
) -> bool:
    if access_control is None:
        return type == "read"

    try:
        user_groups = Groups.get_groups_by_member_id(user_id)
        user_group_ids = [group.id for group in user_groups]
        permission_access = access_control.get(type, {})
        permitted_group_ids = permission_access.get("group_ids", [])
        permitted_user_ids = permission_access.get("user_ids", [])

        return user_id in permitted_user_ids or any(
            group_id in permitted_group_ids for group_id in user_group_ids
        )
    except Exception as e:
        log.error(f"Error checking access for user {user_id}: {str(e)}")
        return False

def get_users_with_access(
    type: str = "write", access_control: Optional[dict] = None
) -> List[UserModel]:
    """Get all users with access to a resource"""
    try:
        if access_control is None:
            return Users.get_users()

        permission_access = access_control.get(type, {})
        permitted_group_ids = permission_access.get("group_ids", [])
        permitted_user_ids = permission_access.get("user_ids", [])

        user_ids_with_access = set(permitted_user_ids)

        for group_id in permitted_group_ids:
            group_user_ids = Groups.get_group_user_ids_by_id(group_id)
            if group_user_ids:
                user_ids_with_access.update(group_user_ids)

        return Users.get_users_by_user_ids(list(user_ids_with_access))
    except Exception as e:
        log.error(f"Error getting users with access: {str(e)}")
        return []
