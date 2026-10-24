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


async def has_chat_move_access(
    user_id: str, source_folder_id: str | None, target_folder_id: str | None, db: AsyncSession | None = None
) -> bool:
    """Only the owner may reorganize another user's chat within the same folder tree."""

    async def get_owned_folder_root_id(folder_id):
        seen_ids = set()
        shared_root_id = None
        while folder_id and folder_id not in seen_ids:
            seen_ids.add(folder_id)
            folder = await Folders.get_folder_by_id(folder_id, db=db)
            if not folder or folder.user_id != user_id:
                return None
            if await AccessGrants.get_grants_by_resource('folder', folder.id, db=db):
                shared_root_id = folder.id
            if not folder.parent_id:
                # A private parent must not let moves escape a shared subtree.
                return shared_root_id or folder.id
            folder_id = folder.parent_id
        return None

    source_root_id = await get_owned_folder_root_id(source_folder_id)
    return source_root_id is not None and source_root_id == await get_owned_folder_root_id(target_folder_id)
