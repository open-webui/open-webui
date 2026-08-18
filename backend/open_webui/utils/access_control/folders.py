from open_webui.models.access_grants import AccessGrants
from open_webui.models.folders import FolderModel, Folders
from sqlalchemy.ext.asyncio import AsyncSession


async def has_folder_access(user_id: str, folder: FolderModel, permission: str, db: AsyncSession | None) -> bool:
    """Check if user has access to folder directly or via ancestor inheritance."""
    # A corrupt parent loop must not spin forever
    seen_ids = set()
    while folder and folder.id not in seen_ids:
        seen_ids.add(folder.id)

        if folder.user_id == user_id:
            return True

        if await AccessGrants.has_access(
            user_id=user_id,
            resource_type='folder',
            resource_id=folder.id,
            permission=permission,
            db=db,
        ):
            return True

        folder = await Folders.get_folder_by_id(folder.parent_id, db=db) if folder.parent_id else None
    return False


async def has_folder_write_access(user_id: str, folder_id: str, db: AsyncSession | None = None) -> bool:
    """Check write access on the folder with this id; False if no such folder exists."""
    folder = await Folders.get_folder_by_id(folder_id, db=db)
    if not folder:
        return False
    return await has_folder_access(user_id, folder, 'write', db)
