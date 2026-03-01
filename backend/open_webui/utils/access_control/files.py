import logging
from typing import Optional, Any

from open_webui.models.users import UserModel
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.models.channels import Channels
from open_webui.models.chats import Chats
from open_webui.models.groups import Groups
from open_webui.models.access_grants import AccessGrants

log = logging.getLogger(__name__)


def has_access_to_file(
    file_id: Optional[str],
    access_type: str,
    user: UserModel,
    db: Optional[Any] = None,
) -> bool:
    """
    Check if a user has the specified access to a file through any of:
    - Knowledge bases (ownership or access grants)
    - Channels the user is a member of
    - Shared chats

    NOTE: This does NOT check direct file ownership — callers should check
    file.user_id == user.id separately before calling this.
    """
    file = Files.get_file_by_id(file_id, db=db)
    log.debug(f"Checking if user has {access_type} access to file")
    if not file:
        return False

    # Check if the file is associated with any knowledge bases the user has access to
    knowledge_bases = Knowledges.get_knowledges_by_file_id(file_id, db=db)
    user_group_ids = {
        group.id for group in Groups.get_groups_by_member_id(user.id, db=db)
    }
    for knowledge_base in knowledge_bases:
        if knowledge_base.user_id == user.id or AccessGrants.has_access(
            user_id=user.id,
            resource_type="knowledge",
            resource_id=knowledge_base.id,
            permission=access_type,
            user_group_ids=user_group_ids,
            db=db,
        ):
            return True

    knowledge_base_id = file.meta.get("collection_name") if file.meta else None
    if knowledge_base_id:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
            user.id, access_type, db=db
        )
        for knowledge_base in knowledge_bases:
            if knowledge_base.id == knowledge_base_id:
                return True

    # Check if the file is associated with any channels the user has access to
    channels = Channels.get_channels_by_file_id_and_user_id(file_id, user.id, db=db)
    if access_type == "read" and channels:
        return True

    # Check if the file is associated with any chats the user has access to
    # TODO: Granular access control for chats
    chats = Chats.get_shared_chats_by_file_id(file_id, db=db)
    if chats:
        return True

    return False
