import logging
from open_webui.models.groups import Groups
from typing import Optional

log = logging.getLogger(__name__)


def apply_default_group_assignment(
    config,
    user_id: str,
    user_email: str,
    context: str = "user"
) -> None:
    """
    Apply default group assignment to a user if DEFAULT_GROUP_ID is configured.
    
    Args:
        config: Application config object with DEFAULT_GROUP_ID attribute
        user_id: ID of the user to add to the default group
        user_email: Email of the user (for logging)
        context: Description of the context (e.g., "LDAP", "OAuth", "signup")
    """
    default_group_id = getattr(config, "DEFAULT_GROUP_ID", "")
    
    if default_group_id:
        try:
            Groups.add_users_to_group(default_group_id, [user_id])
            log.info(
                f"Added {context} user {user_email} to default group {default_group_id}"
            )
        except Exception as e:
            log.error(
                f"Failed to add {context} user {user_email} to default group {default_group_id}: {e}"
            )
