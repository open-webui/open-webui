"""
Authentication dependencies for Usage Tracking
Shared authentication and authorization logic
"""

from fastapi import Depends
from open_webui.utils.auth import get_current_user, get_admin_user
from open_webui.models.users import Users


async def get_usage_tracking_user(user=Depends(get_current_user)) -> Users:
    """Get current user with usage tracking permissions"""
    # For now, all authenticated users can view usage data
    # This can be enhanced with role-based permissions later
    return user


async def get_usage_admin_user(user=Depends(get_admin_user)) -> Users:
    """Get admin user for usage tracking operations"""
    return user