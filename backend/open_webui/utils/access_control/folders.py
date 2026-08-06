from open_webui.models.access_grants import AccessGrants
from open_webui.models.folders import FolderModel, Folders
from sqlalchemy.ext.asyncio import AsyncSession


async def has_folder_access(user_id: str, folder: FolderModel, permission: str, db: AsyncSession) -> bool:
    """Check if user has access to folder directly or via ancestor inheritance."""
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
    # Check ancestor chain for inherited access
    if folder.parent_id:
        parent = await Folders.get_folder_by_id(folder.parent_id, db=db)
        if parent:
            return await has_folder_access(user_id, parent, permission, db)
    return False
