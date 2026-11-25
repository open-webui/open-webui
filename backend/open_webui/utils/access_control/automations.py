from open_webui.models.access_grants import AccessGrants
from open_webui.models.folders import Folders
from open_webui.utils.access_control.folders import has_folder_access
from sqlalchemy.ext.asyncio import AsyncSession


async def has_automation_access(user, automation, permission: str = 'read', db: AsyncSession | None = None) -> bool:
    """Owner, admin, a direct grant, or the same permission on the automation's folder.

    Every run uses the owner's account, so write access only covers changes that can't
    misuse it: the name, the schedule, pausing and running now (see the update route).
    """
    if not automation or not user:
        return False
    if user.role == 'admin' or automation.user_id == user.id:
        return True
    if await AccessGrants.has_access(
        user_id=user.id, resource_type='automation', resource_id=automation.id, permission=permission, db=db
    ):
        return True
    if automation.folder_id:
        folder = await Folders.get_folder_by_id(automation.folder_id, db=db)
        return bool(folder) and await has_folder_access(user.id, folder, permission, db)
    return False


def can_manage_automation(user, automation) -> bool:
    """Sharing and deleting."""
    return bool(automation) and (user.role == 'admin' or automation.user_id == user.id)
