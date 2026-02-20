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
    return capability in get_user_capabilities(user_id, db=db)


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


def can_read_group_member_chats(user_id: str, db: Optional[Any] = None) -> bool:
    """
    Check if user's role allows group-scoped chat oversight.

    Maps to the "audit.read_group_chats" capability.
    This is separate from audit.read_user_chats (global) — this one is scoped
    to groups where the user is an admin.
    """
    return has_capability(user_id, "audit.read_group_chats", db=db)


def get_oversight_target_user_ids(user_id: str, db: Optional[Any] = None) -> set:
    """
    Return user IDs whose chats this user can read via group admin oversight.

    Logic:
    1. Find all groups where requesting user is admin (group_member.role = 'admin')
    2. Get all members of those groups
    3. Subtract self and any users on the exclusion list

    Returns empty set if user doesn't have audit.read_group_chats capability.
    """
    if not can_read_group_member_chats(user_id, db=db):
        return set()

    from open_webui.internal.db import get_db_context
    from open_webui.models.groups import GroupMember
    from open_webui.models.group_oversight import GroupOversightExclusion

    with get_db_context(db) as db:
        # Groups where requesting user is admin
        admin_group_ids = [
            r[0]
            for r in db.query(GroupMember.group_id)
            .filter(
                GroupMember.user_id == user_id,
                GroupMember.role == "admin",
            )
            .all()
        ]

        if not admin_group_ids:
            return set()

        # Excluded users across those groups
        excluded_user_ids = {
            r[0]
            for r in db.query(GroupOversightExclusion.user_id)
            .filter(GroupOversightExclusion.group_id.in_(admin_group_ids))
            .all()
        }

        # All members of those groups, minus self, minus excluded
        target_user_ids = {
            r[0]
            for r in db.query(GroupMember.user_id)
            .filter(
                GroupMember.group_id.in_(admin_group_ids),
                GroupMember.user_id != user_id,
            )
            .distinct()
            .all()
        }

        return target_user_ids - excluded_user_ids


def can_read_user_chats_in_group(
    requesting_user_id: str,
    target_user_id: str,
    db: Optional[Any] = None,
) -> bool:
    """
    Point check: can requesting_user read target_user's chats via group oversight?

    Returns True if:
    1. Requesting user has audit.read_group_chats capability
    2. Requesting user is admin of at least one group that target_user is a member of
    3. Target user is not excluded from oversight in that group
    """
    if not can_read_group_member_chats(requesting_user_id, db=db):
        return False
    targets = get_oversight_target_user_ids(requesting_user_id, db=db)
    return target_user_id in targets


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
