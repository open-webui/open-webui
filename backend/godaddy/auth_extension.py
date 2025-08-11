"""
Extensions for the authentication system to refresh groups on every login.

This module provides functionality to ensure user groups are refreshed
upon each login.
"""

import logging

from open_webui.models.users import Users
from open_webui.models.groups import Groups
from open_webui.utils.auth import decode_token
from godaddy.oauth_extension import get_ad_client

# Setup logging
log = logging.getLogger(__name__)

async def refresh_user_groups_on_login(user):
    """
    Refresh user groups from Active Directory whenever a user logs in.
    
    Args:
        user: The user object whose groups should be refreshed
    
    Returns:
        bool: Success status
    """
    from godaddy.config import USE_ACTIVE_DIRECTORY_GROUPS
    
    # Skip if active directory groups are not enabled
    if not USE_ACTIVE_DIRECTORY_GROUPS:
        log.debug(f"Active Directory groups not enabled, skipping refresh for user {user.id}")
        return False
        
    try:
        log.debug(f"Refreshing Active Directory groups for user {user.email}")
        
        # Get the Active Directory client
        ad_client = get_ad_client()
        
        # Fetch user groups from Active Directory
        user_ad_groups = await ad_client.get_user_groups(user.email)
        
        if not user_ad_groups:
            log.warning(f"No AD groups found for user {user.email}")
            return False
            
        log.debug(f"Found {len(user_ad_groups)} Active Directory groups for user {user.email}")
        
        # Sync the groups with the database
        success = Groups.sync_groups_by_group_names(user.id, user_ad_groups)
        
        if success:
            log.info(f"Successfully synced {len(user_ad_groups)} groups for user {user.email}")
        else:
            log.warning(f"Failed to sync groups for user {user.email}")
            
        return success
    except Exception as e:
        log.exception(f"Error refreshing user groups for {user.email}: {e}")
        return False

def patch_signin_handler():
    """
    Patch the authentication system to refresh groups on every login.
    """
    try:
        from open_webui.routers.auths import signin
        
        # Store the original handler
        original_signin = signin
        
        # Define the new handler that wraps the original
        async def patched_signin(request, response, form_data):
            # Call the original handler
            result = await original_signin(request, response, form_data)
            
            # Get the token from the response
            token = None
            if hasattr(result, "get") and callable(result.get):
                token = result.get("token")
            
            # Decode the token to get the user ID
            if token:
                try:
                    data = decode_token(token)
                    if data and "id" in data:
                        user_id = data["id"]
                        user = Users.get_user_by_id(user_id)
                        if user:
                            # Refresh the user's groups
                            # Create a task but don't await it to avoid delaying the login response
                            import asyncio
                            asyncio.create_task(refresh_user_groups_on_login(user))
                except Exception as e:
                    log.exception(f"Error decoding token during group refresh: {e}")
            
            return result
            
        # Replace the original handler
        from open_webui.routers import auths
        auths.signin = patched_signin
        
        log.info("Successfully patched signin handler to refresh groups on login")
        return True
        
    except Exception as e:
        log.exception(f"Failed to patch signin handler: {e}")
        return False