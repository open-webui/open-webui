import json
from typing import Any

from open_webui.models.users import UserModel
from open_webui.models.groups import Groups
from open_webui.models.access_grants import (
    has_public_read_access_grant,
    has_public_write_access_grant,
    has_user_access_grant,
    strip_user_access_grants,
)
from open_webui.config import DEFAULT_USER_PERMISSIONS

from sqlalchemy.ext.asyncio import AsyncSession


def fill_missing_permissions(permissions: dict[str, Any], default_permissions: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively fills in missing properties in the permissions dictionary
    using the default permissions as a template.
    """
    for key, value in default_permissions.items():
        if key not in permissions:
            permissions[key] = value
        elif isinstance(value, dict) and isinstance(permissions[key], dict):  # Both are nested dictionaries
            permissions[key] = fill_missing_permissions(permissions[key], value)

    return permissions


async def get_permissions(
    user_id: str,
    default_permissions: dict[str, Any],
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Get all permissions for a user by combining the permissions of all groups the user is a member of.
    If a permission is defined in multiple groups, the most permissive value is used (True > False).
    Permissions are nested in a dict with the permission key as the key and a boolean as the value.
    """

    def combine_permissions(permissions: dict[str, Any], group_permissions: dict[str, Any]) -> dict[str, Any]:
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
                    permissions[key] = permissions[key] or value  # Use the most permissive value (True > False)
        return permissions

    user_groups = await Groups.get_groups_by_member_id(user_id, db=db)

    # Deep copy default permissions to avoid modifying the original dict
    permissions = json.loads(json.dumps(default_permissions))

    # Combine permissions from all user groups
    for group in user_groups:
        permissions = combine_permissions(permissions, group.permissions or {})

    # Ensure all fields from default_permissions are present and filled in
    permissions = fill_missing_permissions(permissions, default_permissions)

    return permissions


async def has_permission(
    user_id: str,
    permission_key: str,
    default_permissions: dict[str, Any] = {},
    db: AsyncSession | None = None,
) -> bool:
    """
    Check if a user has a specific permission by checking the group permissions
    and fall back to default permissions if not found in any group.

    Permission keys can be hierarchical and separated by dots ('.').
    """

    def get_permission(permissions: dict[str, Any], keys: list[str]) -> bool:
        """Traverse permissions dict using a list of keys (from dot-split permission_key)."""
        for key in keys:
            if key not in permissions:
                return False  # If any part of the hierarchy is missing, deny access
            permissions = permissions[key]  # Traverse one level deeper

        return bool(permissions)  # Return the boolean at the final level

    permission_hierarchy = permission_key.split('.')

    # Retrieve user group permissions
    user_groups = await Groups.get_groups_by_member_id(user_id, db=db)

    for group in user_groups:
        if get_permission(group.permissions or {}, permission_hierarchy):
            return True

    # Check default permissions afterward if the group permissions don't allow it
    default_permissions = fill_missing_permissions(default_permissions, DEFAULT_USER_PERMISSIONS)
    return get_permission(default_permissions, permission_hierarchy)


async def has_access(
    user_id: str,
    permission: str = 'read',
    access_grants: list | None = None,
    user_group_ids: set[str] | None = None,
    db: AsyncSession | None = None,
) -> bool:
    """
    Check if a user has the specified permission using an in-memory access_grants list.

    Used for config-driven resources (arena models, tool servers) that store
    access control as JSON in PersistentConfig rather than in the access_grant DB table.

    Semantics:
    - None or []  → private (owner-only, deny all)
    - [{"principal_type": "user", "principal_id": "*", "permission": "read"}] → public read
    - Specific grants → check user/group membership
    """
    if not access_grants:
        return False

    if user_group_ids is None:
        user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}

    for grant in access_grants:
        if not isinstance(grant, dict):
            continue
        if grant.get('permission') != permission:
            continue
        principal_type = grant.get('principal_type')
        principal_id = grant.get('principal_id')
        if principal_type == 'user' and (principal_id == '*' or principal_id == user_id):
            return True
        if principal_type == 'group' and user_group_ids and principal_id in user_group_ids:
            return True

    return False


async def has_connection_access(
    user: UserModel,
    connection: dict,
    user_group_ids: set[str] | None = None,
) -> bool:
    """
    Check if a user can access a server connection (tool server, terminal, etc.)
    based on ``config.access_grants`` within the connection dict.

    - Admin with BYPASS_ADMIN_ACCESS_CONTROL → always allowed
    - Missing, None, or empty access_grants → private, admin-only
    - access_grants has entries → delegates to ``has_access``
    """
    from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL

    if user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
        return True

    if user_group_ids is None:
        user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}

    access_grants = (connection.get('config') or {}).get('access_grants', [])
    return await has_access(user.id, 'read', access_grants, user_group_ids)


def migrate_access_control(data: dict, ac_key: str = 'access_control', grants_key: str = 'access_grants') -> None:
    """
    Auto-migrate a config dict in-place from legacy access_control dict to access_grants list.

    If `grants_key` already exists, does nothing.
    If `ac_key` exists (old format), converts it and stores as `grants_key`, then removes `ac_key`.
    """
    if grants_key in data:
        return

    access_control = data.get(ac_key)
    if access_control is None and ac_key not in data:
        return

    grants: list[dict[str, str]] = []
    if access_control and isinstance(access_control, dict):
        for perm in ['read', 'write']:
            perm_data = access_control.get(perm, {})
            if not perm_data:
                continue
            for group_id in perm_data.get('group_ids', []):
                grants.append(
                    {
                        'principal_type': 'group',
                        'principal_id': group_id,
                        'permission': perm,
                    }
                )
            for uid in perm_data.get('user_ids', []):
                grants.append(
                    {
                        'principal_type': 'user',
                        'principal_id': uid,
                        'permission': perm,
                    }
                )

    data[grants_key] = grants
    data.pop(ac_key, None)


async def filter_allowed_access_grants(
    default_permissions: dict[str, Any],
    user_id: str,
    user_role: str,
    access_grants: list,
    public_permission_key: str,
    db: AsyncSession | None = None,
) -> list:
    """
    Checks if the user has the required permissions to grant access to a resource.
    Returns the filtered list of access grants if permissions are missing.
    """
    if user_role == 'admin' or not access_grants:
        return access_grants

    # Check if user can share publicly
    if (
        has_public_read_access_grant(access_grants) or has_public_write_access_grant(access_grants)
    ) and not await has_permission(
        user_id,
        public_permission_key,
        default_permissions,
        db=db,
    ):
        access_grants = [
            grant
            for grant in access_grants
            if not (
                (grant.get('principal_type') if isinstance(grant, dict) else getattr(grant, 'principal_type', None))
                == 'user'
                and (grant.get('principal_id') if isinstance(grant, dict) else getattr(grant, 'principal_id', None))
                == '*'
            )
        ]

    # Strip individual user sharing if user lacks permission
    if has_user_access_grant(access_grants) and not await has_permission(
        user_id,
        'access_grants.allow_users',
        default_permissions,
        db=db,
    ):
        access_grants = strip_user_access_grants(access_grants)

    return access_grants


async def has_base_model_access(
    user_id: str,
    model_info,
    *,
    user_group_ids: set[str] | None = None,
    db=None,
) -> bool:
    """
    Walk the ``base_model_id`` chain and verify the caller has read access
    at every hop.

    Returns ``True`` when access is granted (or the chain ends at a raw
    provider model that has no per-model ACL).  Returns ``False`` the
    moment a registered base model denies access.
    """
    from open_webui.models.models import Models
    from open_webui.models.access_grants import AccessGrants

    base_model_id = getattr(model_info, 'base_model_id', None)
    seen = {model_info.id}
    while base_model_id and base_model_id not in seen:
        seen.add(base_model_id)
        base_model_info = await Models.get_model_by_id(base_model_id, db=db)
        if base_model_info is None:
            break  # Raw provider model — no per-model ACL
        if not (
            user_id == base_model_info.user_id
            or await AccessGrants.has_access(
                user_id=user_id,
                resource_type='model',
                resource_id=base_model_info.id,
                permission='read',
                user_group_ids=user_group_ids,
                db=db,
            )
        ):
            return False
        base_model_id = getattr(base_model_info, 'base_model_id', None)
    return True


async def check_model_access(
    user: UserModel,
    model_info,
    bypass_filter: bool = False,
) -> None:
    """
    Enforce per-model read access for the given user.

    Raises HTTPException(403) if the user is not authorized.
    Does nothing if bypass_filter is True.

    Args:
        user: The authenticated user.
        model_info: The model record from await Models.get_model_by_id(),
                    or None if the model is not registered.
        bypass_filter: If True, skip all access checks (used by
                       internal callers and BYPASS_MODEL_ACCESS_CONTROL).
    """
    from fastapi import HTTPException

    if bypass_filter:
        return

    if model_info:
        if user.role == 'user':
            from open_webui.models.access_grants import AccessGrants

            user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}
            if not (
                user.id == model_info.user_id
                or await AccessGrants.has_access(
                    user_id=user.id,
                    resource_type='model',
                    resource_id=model_info.id,
                    permission='read',
                    user_group_ids=user_group_ids,
                )
            ):
                raise HTTPException(status_code=403, detail='Model not found')

            # Enforce access on chained base models
            if not await has_base_model_access(user.id, model_info, user_group_ids=user_group_ids):
                raise HTTPException(status_code=403, detail='Model not found')
    else:
        if user.role != 'admin':
            raise HTTPException(status_code=403, detail='Model not found')
