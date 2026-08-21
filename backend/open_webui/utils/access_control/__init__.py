from typing import Any

from open_webui.config import DEFAULT_USER_PERMISSIONS
from open_webui.models.access_grants import (
    has_anyone_read_access_grant,
    has_public_read_access_grant,
    has_public_write_access_grant,
    has_user_access_grant,
    strip_anyone_access_grants,
    strip_user_access_grants,
)
from open_webui.models.groups import Groups
from open_webui.models.users import UserModel
from open_webui.utils.json_codec import JSONCodec
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Custom-role permission resolution
# ---------------------------------------------------------------------------

# Roles that use legacy permission evaluation (default_permissions + group OR-merging).
# ``admin`` is always bypass-admin and never flows through the ordinary permissions path.
LEGACY_PERMISSION_ROLES = {'user', 'pending'}


async def _get_custom_role_permissions(role: str, db: AsyncSession | None = None) -> dict[str, Any] | None:
    """Look up the explicit permission set for a custom role reference.

    Returns the permissions dict if the role is a valid active custom role,
    or ``None`` if it cannot be resolved (unknown, malformed, or disabled).
    """
    from open_webui.models.custom_roles import CustomRoles, extract_custom_role_id

    role_id = extract_custom_role_id(role)
    if role_id is None:
        return None

    active_role = await CustomRoles.get_active_role_by_id(role_id, db=db)
    if active_role is None:
        return None

    return active_role.permissions


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
    user_role: str | None = None,
) -> dict[str, Any]:
    """
    Get all permissions for a user.

    Resolution order:
    1. If the user has a valid active custom role, return ONLY that role's
       explicit permissions normalised against the server-owned catalog
       (no group merging, no config defaults).
    2. Otherwise (legacy ``user``/``pending``), combine the configured
       default permissions with the most-permissive merge of all group
       permissions — the existing behaviour.
    """

    # Fast path: if the caller already knows the role, use it.
    if user_role is None:
        from open_webui.models.users import Users as _Users

        user_obj = await _Users.get_user_by_id(user_id, db=db)
        if user_obj is None:
            return JSONCodec.loads(JSONCodec.dumps(default_permissions))
        user_role = user_obj.role

    # ── Custom role path ──────────────────────────────────────────────
    if user_role not in LEGACY_PERMISSION_ROLES and user_role != 'admin':
        return await _resolve_custom_role_permissions(user_role, db=db)

    # ── Legacy path (user / pending) ──────────────────────────────────
    return await _resolve_legacy_permissions(user_id, default_permissions, db=db)


async def _resolve_custom_role_permissions(role: str, db: AsyncSession | None = None) -> dict[str, Any]:
    """Resolve permissions for a custom role reference.

    Returns the normalised permission tree if the role is valid and active.
    For unknown/disabled/malformed roles returns a full-deny tree derived
    from the fixed server-owned catalog (fail-closed).
    """
    from open_webui.models.custom_roles import normalize_permissions

    custom_perms = await _get_custom_role_permissions(role, db=db)
    if custom_perms is not None:
        return normalize_permissions(custom_perms)
    # Unknown/disabled custom role — fail closed: return a full-deny
    # tree derived from the fixed server-owned catalog, NOT from the
    # caller's ``default_permissions`` shape.  This ensures caller
    # config cannot alter the denial shape or grant anything.
    return normalize_permissions(None)


def _combine_permissions(permissions: dict[str, Any], group_permissions: dict[str, Any]) -> dict[str, Any]:
    """Combine permissions from multiple groups by taking the most permissive value."""
    for key, value in group_permissions.items():
        if isinstance(value, dict):
            if key not in permissions:
                permissions[key] = {}
            permissions[key] = _combine_permissions(permissions[key], value)
        else:
            if key not in permissions:
                permissions[key] = value
            else:
                permissions[key] = permissions[key] or value  # Use the most permissive value (True > False)
    return permissions


async def _resolve_legacy_permissions(
    user_id: str,
    default_permissions: dict[str, Any],
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Resolve permissions for legacy ``user``/``pending`` roles.

    Combines the configured default permissions with the most-permissive
    merge of all group permissions.
    """
    user_groups = await Groups.get_groups_by_member_id(user_id, db=db)

    # Deep copy default permissions to avoid modifying the original dict
    permissions = JSONCodec.loads(JSONCodec.dumps(default_permissions))

    # Combine permissions from all user groups
    for group in user_groups:
        permissions = _combine_permissions(permissions, group.permissions or {})

    # Ensure all fields from default_permissions are present and filled in
    permissions = fill_missing_permissions(permissions, default_permissions)

    return permissions


def _empty_permissions(default_permissions: dict[str, Any]) -> dict[str, Any]:
    """Return a permissions dict with all boolean leaves set to False.

    Used for fail-closed resolution of unknown/disabled custom roles.
    """
    def _deny_tree(template: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in template.items():
            if isinstance(value, dict):
                result[key] = _deny_tree(value)
            else:
                result[key] = False
        return result

    return _deny_tree(default_permissions)


async def has_permission(
    user_id: str,
    permission_key: str,
    default_permissions: dict[str, Any] = {},
    db: AsyncSession | None = None,
) -> bool:
    """
    Check if a user has a specific permission.

    Resolution:
    1. Custom roles: check only the role's explicit permission tree
       normalised against the server-owned catalog.
       Unknown/disabled custom roles return False (fail-closed).
    2. Legacy roles (user/pending): check group permissions, then default.
    3. Admin: always returns True (admin bypass handled by callers).
    """

    def get_permission(permissions: dict[str, Any], keys: list[str]) -> bool:
        """Traverse permissions dict using a list of keys (from dot-split permission_key)."""
        for key in keys:
            if key not in permissions:
                return False  # If any part of the hierarchy is missing, deny access
            permissions = permissions[key]  # Traverse one level deeper

        return bool(permissions)  # Return the boolean at the final level

    permission_hierarchy = permission_key.split('.')

    # Resolve user role if not provided via caller context
    from open_webui.models.users import Users as _Users

    user_obj = await _Users.get_user_by_id(user_id, db=db)
    if user_obj is None:
        return False

    user_role = user_obj.role

    # ── Custom role path ──────────────────────────────────────────────
    if user_role not in LEGACY_PERMISSION_ROLES and user_role != 'admin':
        custom_perms = await _get_custom_role_permissions(user_role, db=db)
        if custom_perms is not None:
            # Normalize against the server-owned catalog
            from open_webui.models.custom_roles import normalize_permissions
            normalized = normalize_permissions(custom_perms)
            return get_permission(normalized, permission_hierarchy)
        # Unknown/disabled custom role — fail closed
        return False

    # ── Admin bypass ──────────────────────────────────────────────────
    if user_role == 'admin':
        return True

    # ── Legacy path (user / pending) ──────────────────────────────────
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
    access control as JSON config rather than in the access_grant DB table.

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

    access_grants = (connection.get('config') or {}).get('access_grants', [])
    if not access_grants:
        # No grants configured → private, admin-only: admins must keep access
        # to connections only they can configure, even when they do not bypass
        # access control globally.
        return user.role == 'admin'

    if user_group_ids is None:
        user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id)}

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
    anyone_permission_key: str | None = None,
    db: AsyncSession | None = None,
) -> list:
    """
    Checks if the user has the required permissions to grant access to a resource.
    Returns the filtered list of access grants if permissions are missing.
    """
    if not access_grants:
        return access_grants

    if has_anyone_read_access_grant(access_grants) and (
        not anyone_permission_key
        or (
            user_role != 'admin'
            and not await has_permission(
                user_id,
                anyone_permission_key,
                default_permissions,
                db=db,
            )
        )
    ):
        access_grants = strip_anyone_access_grants(access_grants)

    if user_role == 'admin':
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

    if any(
        (grant.get('principal_type') if isinstance(grant, dict) else getattr(grant, 'principal_type', None)) == 'group'
        for grant in access_grants
    ) and not await has_permission(
        user_id,
        'access_grants.allow_groups',
        default_permissions,
        db=db,
    ):
        access_grants = [
            grant
            for grant in access_grants
            if (grant.get('principal_type') if isinstance(grant, dict) else getattr(grant, 'principal_type', None))
            != 'group'
        ]

    return access_grants


async def has_base_model_access(
    user_id: str,
    model_info,
    *,
    user_role: str | None = None,
    user_group_ids: set[str] | None = None,
    db=None,
) -> bool:
    """
    Walk the ``base_model_id`` chain and verify the caller has read access
    at every hop.

    A base model without a ``model`` table row is admin-only, matching how
    unregistered models are treated for direct use (``get_filtered_models``
    hides them from non-admins and ``check_model_access`` rejects them), so
    a shared preset cannot be used to reach a base model the caller could
    not use directly.  Returns ``False`` the moment any hop denies access.
    """
    from open_webui.models.access_grants import AccessGrants
    from open_webui.models.models import Models

    base_model_id = getattr(model_info, 'base_model_id', None)
    seen = {model_info.id}
    while base_model_id and base_model_id not in seen:
        seen.add(base_model_id)
        base_model_info = await Models.get_model_by_id(base_model_id, db=db)
        if base_model_info is None:
            return user_role == 'admin'
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
        # Enforce for every non-admin role (including pending); never fail open.
        if user.role != 'admin':
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
            if not await has_base_model_access(user.id, model_info, user_role=user.role, user_group_ids=user_group_ids):
                raise HTTPException(status_code=403, detail='Model not found')
    else:
        if user.role != 'admin':
            raise HTTPException(status_code=403, detail='Model not found')
