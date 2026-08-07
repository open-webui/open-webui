from typing import Optional

from open_webui.models.access_grants import AccessGrants
from open_webui.models.chats import ChatModel
from open_webui.models.folders import Folders
from open_webui.utils.access_control.folders import has_folder_access
from sqlalchemy.ext.asyncio import AsyncSession


async def has_chat_read_access(
    user_id: str, user_role: str, chat: ChatModel, db: Optional[AsyncSession] = None
) -> bool:
    """Check if a user can read a chat via ownership, admin role, an explicit share grant, or a shared folder."""
    if user_role == 'admin' or chat.user_id == user_id:
        return True

    if await AccessGrants.has_access(
        user_id=user_id,
        resource_type='shared_chat',
        resource_id=chat.id,
        permission='read',
        db=db,
    ):
        return True

    if chat.folder_id:
        folder = await Folders.get_folder_by_id(chat.folder_id, db=db)
        if folder and await has_folder_access(user_id, folder, 'read', db):
            return True

    return False
