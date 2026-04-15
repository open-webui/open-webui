import logging

from open_webui.models.users import UserModel
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.models.channels import Channels
from open_webui.models.chats import Chats
from open_webui.models.groups import Groups
from open_webui.models.models import Models
from open_webui.models.access_grants import AccessGrants

from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


async def has_access_to_file(
    file_id: str | None,
    access_type: str,
    user: UserModel,
    db: AsyncSession | None = None,
) -> bool:
    """
    Check if a user has the specified access to a file through any of:
    - Knowledge bases (ownership or access grants)
    - Shared workspace models that attach the file directly
    - Channels the user is a member of
    - Shared chats

    NOTE: This does NOT check direct file ownership — callers should check
    file.user_id == user.id separately before calling this.
    """
    file = await Files.get_file_by_id(file_id, db=db)
    log.debug(f'Checking if user has {access_type} access to file')
    if not file:
        return False

    # Direct ownership
    if file.user_id == user.id:
        return True

    # Check if the file is associated with any knowledge bases the user has access to
    knowledge_bases = await Knowledges.get_knowledges_by_file_id(file_id, db=db)
    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id, db=db)}
    for knowledge_base in knowledge_bases:
        if knowledge_base.user_id == user.id or await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge_base.id,
            permission=access_type,
            user_group_ids=user_group_ids,
            db=db,
        ):
            return True

    knowledge_base_id = file.meta.get('collection_name') if file.meta else None
    if knowledge_base_id:
        knowledge_bases = await Knowledges.get_knowledge_bases_by_user_id(user.id, access_type, db=db)
        for knowledge_base in knowledge_bases:
            if knowledge_base.id == knowledge_base_id:
                return True

    # Check if the file is associated with any channels the user has access to
    channels = await Channels.get_channels_by_file_id_and_user_id(file_id, user.id, db=db)
    if access_type == 'read' and channels:
        return True

    # Check if the file is associated with any chats the user has access to
    # TODO: Granular access control for chats
    chats = await Chats.get_shared_chats_by_file_id(file_id, db=db)
    if chats:
        return True

    # Check if the file is directly attached to a shared workspace model
    for model in await Models.get_models_by_user_id(user.id, permission=access_type, db=db):
        knowledge_items = getattr(model.meta, 'knowledge', None) or []
        for item in knowledge_items:
            if isinstance(item, dict) and item.get('type') == 'file' and item.get('id') == file.id:
                return True

    return False
