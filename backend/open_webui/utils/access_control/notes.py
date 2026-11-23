from open_webui.models.access_grants import AccessGrants
from open_webui.models.folders import Folders
from open_webui.utils.access_control.folders import has_folder_access
from sqlalchemy.ext.asyncio import AsyncSession


async def has_note_access(user_id: str, note, permission: str = 'read', db: AsyncSession | None = None) -> bool:
    """Owner, a direct grant, or the same permission on the note's folder."""
    if note.user_id == user_id:
        return True
    if await AccessGrants.has_access(
        user_id=user_id, resource_type='note', resource_id=note.id, permission=permission, db=db
    ):
        return True
    if note.folder_id:
        folder = await Folders.get_folder_by_id(note.folder_id, db=db)
        return bool(folder) and await has_folder_access(user_id, folder, permission, db)
    return False
