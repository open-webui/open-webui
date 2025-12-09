"""
Workspace access control utilities for group-based collaboration
"""

def item_assigned_to_user_groups(user_id: str, item, permission: str = "write") -> bool:
    """Check if item is assigned to any group the user is member of OR owns OR user is super admin"""
    from open_webui.models.groups import Groups
    from open_webui.models.users import Users
    from open_webui.utils.super_admin import is_super_admin
    
    # Check if user is super admin - they see everything
    user = Users.get_user_by_id(user_id)
    user_is_super_admin = is_super_admin(user)
    
    if user_is_super_admin:
        return True  # Super admin sees ALL items
    
    # Get groups where user is member
    user_groups = Groups.get_groups_by_member_id(user_id)
    user_group_ids = [g.id for g in user_groups]
    
    # Handle None access_control (legacy records without group assignments)
    if item.access_control is None:
        return False
    
    # Get BOTH read and write groups for the item
    read_groups = item.access_control.get("read", {}).get("group_ids", [])
    write_groups = item.access_control.get("write", {}).get("group_ids", [])
    item_groups = list(set(read_groups + write_groups))  # Combine and dedupe
    
    # Check if user is member of any group that has access
    member_match = any(group_id in user_group_ids for group_id in item_groups)
    if member_match:
        return True
    
    # Also check if user owns any of the groups that have access to this item
    all_groups = Groups.get_groups()
    owned_group_ids = [g.id for g in all_groups if g.user_id == user_id]
    owner_match = any(group_id in owned_group_ids for group_id in item_groups)
    
    return owner_match