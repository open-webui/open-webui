"""
Extensions for the OAuth module to integrate with GoDaddy Active Directory.

This module provides alternative implementations for the OAuth module functions
that integrate with GoDaddy's Active Directory service.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any

from open_webui.models.users import Users
from open_webui.models.groups import Groups, GroupUpdateForm, GroupForm
from open_webui.utils.oauth import auth_manager_config

from godaddy.config import USE_ACTIVE_DIRECTORY_GROUPS
from godaddy.active_directory import ActiveDirectoryClient

# Setup logging
log = logging.getLogger(__name__)

# Initialize the Active Directory client
active_directory_client = None

def get_ad_client():
    """Get or create the Active Directory client."""
    global active_directory_client
    if active_directory_client is None:
        from godaddy.config import ACTIVE_DIRECTORY_BASE_URL, ACTIVE_DIRECTORY_SSO_HOST, ACTIVE_DIRECTORY_TOKEN_REFRESH_MINUTES, ACTIVE_DIRECTORY_DOMAIN
        active_directory_client = ActiveDirectoryClient(
            base_url=ACTIVE_DIRECTORY_BASE_URL,
            sso_host=ACTIVE_DIRECTORY_SSO_HOST,
            refresh_min=ACTIVE_DIRECTORY_TOKEN_REFRESH_MINUTES,
            domain=ACTIVE_DIRECTORY_DOMAIN
        )
    return active_directory_client

def update_user_groups(self, user, user_data, default_permissions):
    """
    Update user groups based on Active Directory group memberships.
    
    This function is meant to replace the OAuthManager.update_user_groups method
    when USE_ACTIVE_DIRECTORY_GROUPS is enabled. It's a synchronous wrapper
    that creates a background task for the actual async work.
    
    Args:
        self: The OAuthManager instance
        user: The user to update groups for
        user_data: The OAuth user data
        default_permissions: Default permissions to use for new groups
    """
    # Only use Active Directory if enabled
    if USE_ACTIVE_DIRECTORY_GROUPS:
        try:
            # Create a background task for the async work
            asyncio.create_task(_async_update_user_groups(self, user, user_data, default_permissions))
            log.debug(f"Created background task to update groups for user {user.id} from Active Directory")
        except Exception as e:
            log.exception(f"Error creating background task for AD group update: {e}")
            # Fall back to the original method on error
            return self._original_update_user_groups(user, user_data, default_permissions)
    else:
        # Use the original method if Active Directory is disabled
        return self._original_update_user_groups(user, user_data, default_permissions)

async def _async_update_user_groups(self, user, user_data, default_permissions):
    """
    Asynchronous implementation of update_user_groups.
    This runs in the background after being called by the synchronous wrapper.
    """
    # Skip if not enabled - since this is running in a background task,
    # we can't call the original method (would cause another coroutine not awaited error)
    if not USE_ACTIVE_DIRECTORY_GROUPS:
        log.debug("Active Directory groups not enabled, skipping async update")
        return
        
    log.debug("Running Active Directory Group management")
    
    try:
        # Get blocked groups from config using the global auth_manager_config
        blocked_groups = json.loads(auth_manager_config.OAUTH_BLOCKED_GROUPS)
    except Exception as e:
        log.exception(f"Error loading OAUTH_BLOCKED_GROUPS: {e}")
        blocked_groups = []
        
    # Retrieve user email from OAuth data using the global auth_manager_config
    email_claim = auth_manager_config.OAUTH_EMAIL_CLAIM
    user_email = user_data.get(email_claim, "")
    
    if not user_email:
        log.warning("No email found in OAuth claims, cannot fetch AD groups")
        return
        
    try:
        # Fetch user groups from Active Directory API
        ad_client = get_ad_client()
        user_ad_groups = await ad_client.get_user_groups(user_email)
        
        log.debug(f"Active Directory groups for user {user_email}: {user_ad_groups}")
        
        # From here on, the logic is similar to the original update_user_groups method
        user_current_groups = Groups.get_groups_by_member_id(user.id)
        all_available_groups = Groups.get_groups()
        
        # Create groups if they don't exist and creation is enabled
        if auth_manager_config.ENABLE_OAUTH_GROUP_CREATION:
            log.debug("Checking for missing groups to create...")
            all_group_names = {g.name for g in all_available_groups}
            groups_created = False
            # Determine creator ID: Prefer admin, fallback to current user if no admin exists
            admin_user = Users.get_super_admin_user()
            creator_id = admin_user.id if admin_user else user.id
            log.debug(f"Using creator ID {creator_id} for potential group creation.")
            
            for group_name in user_ad_groups:
                if group_name not in all_group_names:
                    log.info(f"Group '{group_name}' not found via AD. Creating group...")
                    try:
                        new_group_form = GroupForm(
                            name=group_name,
                            description=f"Group '{group_name}' created automatically via AD.",
                            permissions=default_permissions,  # Use default permissions from function args
                            user_ids=[],  # Start with no users, user will be added later by subsequent logic
                        )
                        # Use determined creator ID (admin or fallback to current user)
                        created_group = Groups.insert_new_group(
                            creator_id, new_group_form
                        )
                        if created_group:
                            log.info(
                                f"Successfully created group '{group_name}' with ID {created_group.id} using creator ID {creator_id}"
                            )
                            groups_created = True
                            # Add to local set to prevent duplicate creation attempts in this run
                            all_group_names.add(group_name)
                        else:
                            log.error(
                                f"Failed to create group '{group_name}' via AD."
                            )
                    except Exception as e:
                        log.error(f"Error creating group '{group_name}' via AD: {e}")
            
            # Refresh the list of all available groups if any were created
            if groups_created:
                all_available_groups = Groups.get_groups()
                log.debug("Refreshed list of all available groups after creation.")
                
        log.debug(f"Active Directory groups: {user_ad_groups}")
        log.debug(f"User's current groups: {[g.name for g in user_current_groups]}")
        log.debug(
            f"All groups available in OpenWebUI: {[g.name for g in all_available_groups]}"
        )
        
        # Remove groups that user is no longer a part of
        for group_model in user_current_groups:
            if (
                user_ad_groups
                and group_model.name not in user_ad_groups
                and group_model.name not in blocked_groups
            ):
                # Remove group from user
                log.debug(
                    f"Removing user from group {group_model.name} as it is no longer in their AD groups"
                )
                
                user_ids = group_model.user_ids
                user_ids = [i for i in user_ids if i != user.id]
                
                # In case a group is created, but perms are never assigned to the group by hitting "save"
                group_permissions = group_model.permissions
                if not group_permissions:
                    group_permissions = default_permissions
                
                update_form = GroupUpdateForm(
                    name=group_model.name,
                    description=group_model.description,
                    permissions=group_permissions,
                    user_ids=user_ids,
                )
                Groups.update_group_by_id(
                    id=group_model.id, form_data=update_form, overwrite=False
                )
                
        # Add user to new groups
        for group_model in all_available_groups:
            if (
                user_ad_groups
                and group_model.name in user_ad_groups
                and not any(gm.name == group_model.name for gm in user_current_groups)
                and group_model.name not in blocked_groups
            ):
                # Add user to group
                log.debug(
                    f"Adding user to group {group_model.name} as it was found in their AD groups"
                )
                
                user_ids = group_model.user_ids
                user_ids.append(user.id)
                
                # In case a group is created, but perms are never assigned to the group by hitting "save"
                group_permissions = group_model.permissions
                if not group_permissions:
                    group_permissions = default_permissions
                
                update_form = GroupUpdateForm(
                    name=group_model.name,
                    description=group_model.description,
                    permissions=group_permissions,
                    user_ids=user_ids,
                )
                Groups.update_group_by_id(
                    id=group_model.id, form_data=update_form, overwrite=False
                )
                
    except Exception as e:
        log.exception(f"Error updating user groups with Active Directory: {e}")
        # We're in a background task, so we can't call the original method
        # Just log the error and return


def patch_oauth_manager():
    """
    Patch the OAuthManager class to use Active Directory for group management.
    
    This function should be called when initializing the application to override
    the update_user_groups method on the OAuthManager class.
    """
    try:
        from open_webui.utils.oauth import OAuthManager
        
        # Only apply the patch if Active Directory groups are enabled
        if USE_ACTIVE_DIRECTORY_GROUPS:
            # Store the original method for fallback in case we need it
            OAuthManager._original_update_user_groups = OAuthManager.update_user_groups
            
            # Override the update_user_groups method with our sync wrapper
            OAuthManager.update_user_groups = update_user_groups
            
            log.info("Successfully patched OAuthManager to use Active Directory for group management")
        else:
            log.info("Active Directory groups disabled, skipping OAuthManager patch")
            
    except ImportError as e:
        log.error(f"Failed to patch OAuthManager: {e}")
        return False
    except Exception as e:
        log.exception(f"Unexpected error while patching OAuthManager: {e}")
        return False
        
    return True