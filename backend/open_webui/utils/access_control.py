from typing import Optional, Set, Union, List, Dict, Any
from functools import lru_cache
from open_webui.models.users import Users, UserModel
from open_webui.models.groups import Groups


from open_webui.config import DEFAULT_USER_PERMISSIONS
import json


# Request-scoped cache for user capabilities
# This avoids repeated DB queries within a single request
_capability_cache: Dict[str, Set[str]] = {}


def clear_capability_cache() -> None:
    """Clear the capability cache. Call at the start of each request."""
    global _capability_cache
    _capability_cache = {}


def has_capability(
    user_id: str,
    capability: str,
    db: Optional[Any] = None,
) -> bool:
    """
    Check if a user has a specific admin-tier capability based on their role.

    Capabilities are distinct from permissions:
    - Permissions: User-facing feature toggles (can use TTS? can share chats?)
    - Capabilities: Admin-tier actions (can manage users? can read all chats?)

    This function:
    1. Looks up the user's role_id
    2. Checks if that role has the specified capability via role_capability table
    3. Falls back to checking if user.role == "admin" (backward compatibility)

    Args:
        user_id: The user's ID
        capability: The capability to check (e.g., "admin.manage_users", "audit.read_user_chats")
        db: Optional database session

    Returns:
        True if the user has the capability, False otherwise
    """
    from open_webui.internal.db import get_db_context
    from open_webui.models.roles import RoleCapability, Role
    from open_webui.models.users import User

    # Check cache first
    global _capability_cache
    if user_id in _capability_cache:
        return capability in _capability_cache[user_id]

    with get_db_context(db) as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return False

        # Backward compatibility: if user has role_id, use new system
        # Otherwise fall back to checking user.role == "admin"
        if hasattr(user, "role_id") and user.role_id:
            # New system: check role_capability table
            exists = (
                db.query(RoleCapability)
                .filter_by(
                    role_id=user.role_id,
                    capability=capability,
                )
                .first()
            )
            return exists is not None
        else:
            # Backward compatibility: admin role has all capabilities
            # This ensures existing code works during migration
            if user.role == "admin":
                return True
            return False


def get_user_capabilities(
    user_id: str,
    db: Optional[Any] = None,
) -> Set[str]:
    """
    Get all capabilities for a user based on their role.

    Returns a set of capability strings that the user has.
    Results are cached per-request for performance.

    Args:
        user_id: The user's ID
        db: Optional database session

    Returns:
        Set of capability strings (e.g., {"admin.manage_users", "audit.read_user_chats"})
    """
    from open_webui.internal.db import get_db_context
    from open_webui.models.roles import RoleCapability, Role, SYSTEM_CAPABILITIES
    from open_webui.models.users import User

    global _capability_cache
    if user_id in _capability_cache:
        return _capability_cache[user_id]

    with get_db_context(db) as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            _capability_cache[user_id] = set()
            return set()

        capabilities = set()

        # New system: get capabilities from role
        if hasattr(user, "role_id") and user.role_id:
            caps = db.query(RoleCapability).filter_by(role_id=user.role_id).all()
            capabilities = {cap.capability for cap in caps}
        else:
            # Backward compatibility: admin role has all capabilities
            if user.role == "admin":
                capabilities = set(SYSTEM_CAPABILITIES.keys())

        _capability_cache[user_id] = capabilities
        return capabilities


def has_any_capability(
    user_id: str,
    capabilities: List[str],
    db: Optional[Any] = None,
) -> bool:
    """
    Check if a user has ANY of the specified capabilities.

    Args:
        user_id: The user's ID
        capabilities: List of capability strings to check
        db: Optional database session

    Returns:
        True if the user has at least one of the capabilities
    """
    user_caps = get_user_capabilities(user_id, db=db)
    return bool(user_caps.intersection(capabilities))


def has_all_capabilities(
    user_id: str,
    capabilities: List[str],
    db: Optional[Any] = None,
) -> bool:
    """
    Check if a user has ALL of the specified capabilities.

    Args:
        user_id: The user's ID
        capabilities: List of capability strings to check
        db: Optional database session

    Returns:
        True if the user has all of the capabilities
    """
    user_caps = get_user_capabilities(user_id, db=db)
    return all(cap in user_caps for cap in capabilities)


def can_bypass_access_control(user_id: str, db: Optional[Any] = None) -> bool:
    """
    Check if user can bypass access control for workspace resources.

    This maps to the "admin.bypass_access_control" capability.
    For backward compatibility, also respects the legacy BYPASS_ADMIN_ACCESS_CONTROL config.

    Use this instead of: user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL
    """
    return has_capability(user_id, "admin.bypass_access_control", db=db)


def can_manage_all(user_id: str, resource_type: str, db: Optional[Any] = None) -> bool:
    """
    Check if user can manage all resources of a given type regardless of ownership.

    Maps resource types to workspace.manage_all_* capabilities.
    Use this instead of: user.role == "admin" (for ownership-or-admin checks)

    Args:
        user_id: The user's ID
        resource_type: One of: models, knowledge, tools, prompts, skills,
                       spaces, files, channels
        db: Optional database session

    Returns:
        True if the user has the workspace.manage_all_{resource_type} capability
    """
    capability = f"workspace.manage_all_{resource_type}"
    return has_capability(user_id, capability, db=db)


def can_access_user_chats(user_id: str, db: Optional[Any] = None) -> bool:
    """
    Check if user can access other users' chats (audit/compliance use case).

    Maps to the "audit.read_user_chats" capability.
    Use this instead of: user.role == "admin" and ENABLE_ADMIN_CHAT_ACCESS
    """
    return has_capability(user_id, "audit.read_user_chats", db=db)


def can_export_data(user_id: str, db: Optional[Any] = None) -> bool:
    """
    Check if user can export system data (chats, analytics, DB).

    Maps to the "audit.export_data" capability.
    Use this instead of: user.role == "admin" and ENABLE_ADMIN_EXPORT
    """
    return has_capability(user_id, "audit.export_data", db=db)


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


def get_permissions(
    user_id: str,
    default_permissions: Dict[str, Any],
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Get all permissions for a user by combining:
    1. Default permissions (base)
    2. Role permissions (from user's assigned role)
    3. Group permissions (additive overrides)

    Permission resolution order:
    - Start with default_permissions
    - Apply role permissions (if user has a role with permissions defined)
    - Apply group permissions (most permissive value wins: True > False)

    Permissions are nested in a dict with the permission key as the key and a boolean as the value.
    """
    from open_webui.internal.db import get_db_context
    from open_webui.models.roles import Role
    from open_webui.models.users import User

    def combine_permissions(
        permissions: Dict[str, Any], overlay_permissions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine permissions by taking the most permissive value (True > False)."""
        for key, value in overlay_permissions.items():
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

    # Deep copy default permissions to avoid modifying the original dict
    permissions = json.loads(json.dumps(default_permissions))

    # Step 1: Get role permissions (if user has a role assigned)
    with get_db_context(db) as db:
        user = db.query(User).filter_by(id=user_id).first()
        if user and hasattr(user, "role_id") and user.role_id:
            role = db.query(Role).filter_by(id=user.role_id).first()
            if role and role.permissions:
                permissions = combine_permissions(permissions, role.permissions)

    # Step 2: Get group permissions (additive overrides)
    user_groups = Groups.get_groups_by_member_id(user_id, db=db)
    for group in user_groups:
        permissions = combine_permissions(permissions, group.permissions or {})

    # Ensure all fields from default_permissions are present and filled in
    permissions = fill_missing_permissions(permissions, default_permissions)

    return permissions


def has_permission(
    user_id: str,
    permission_key: str,
    default_permissions: Dict[str, Any] = {},
    db: Optional[Any] = None,
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
    user_groups = Groups.get_groups_by_member_id(user_id, db=db)

    for group in user_groups:
        if get_permission(group.permissions or {}, permission_hierarchy):
            return True

    # Check default permissions afterward if the group permissions don't allow it
    default_permissions = fill_missing_permissions(
        default_permissions, DEFAULT_USER_PERMISSIONS
    )
    return get_permission(default_permissions, permission_hierarchy)


def has_access(
    user_id: str,
    permission: str = "read",
    access_grants: Optional[list] = None,
    user_group_ids: Optional[Set[str]] = None,
    db: Optional[Any] = None,
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
        user_groups = Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}

    for grant in access_grants:
        if not isinstance(grant, dict):
            continue
        if grant.get("permission") != permission:
            continue
        principal_type = grant.get("principal_type")
        principal_id = grant.get("principal_id")
        if principal_type == "user" and (
            principal_id == "*" or principal_id == user_id
        ):
            return True
        if (
            principal_type == "group"
            and user_group_ids
            and principal_id in user_group_ids
        ):
            return True

    return False


def migrate_access_control(
    data: dict, ac_key: str = "access_control", grants_key: str = "access_grants"
) -> None:
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

    grants: List[Dict[str, str]] = []
    if access_control and isinstance(access_control, dict):
        for perm in ["read", "write"]:
            perm_data = access_control.get(perm, {})
            if not perm_data:
                continue
            for group_id in perm_data.get("group_ids", []):
                grants.append(
                    {
                        "principal_type": "group",
                        "principal_id": group_id,
                        "permission": perm,
                    }
                )
            for uid in perm_data.get("user_ids", []):
                grants.append(
                    {
                        "principal_type": "user",
                        "principal_id": uid,
                        "permission": perm,
                    }
                )

    data[grants_key] = grants
    data.pop(ac_key, None)
