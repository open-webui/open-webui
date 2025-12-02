import logging
from open_webui.models.groups import Groups

log = logging.getLogger(__name__)


def apply_default_group_assignment(
    default_group_id: str,
    user_id: str,
) -> None:
    """
    Apply default group assignment to a user if default_group_id is provided.

    Args:
        default_group_id: ID of the default group to add the user to
        user_id: ID of the user to add to the default group
    """
    if default_group_id:
        try:
            Groups.add_users_to_group(default_group_id, [user_id])
        except Exception as e:
            log.error(
                f"Failed to add user {user_id} to default group {default_group_id}: {e}"
            )
