"""Company governance helpers for private chats and Team Workspaces.

OpenWebUI core roles are intentionally limited to: pending, user, admin.
Company tiers such as CEO/Managers are represented by Groups, not by mutating
``User.role`` into non-core values.
"""

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_db_context
from open_webui.models.groups import Group, GroupMember
from open_webui.models.workspaces import Workspaces

CEO_GROUP_NAMES = {'CEO'}
PRIVATE_CHAT_ALLOWED_GROUP_NAMES = {'CEO', 'Manager', 'Managers', 'Private Chat Allowed'}
WORKSPACE_ALL_ACCESS_GROUP_NAMES = {'CEO'}
WORKSPACE_CREATE_ALLOWED_CORE_ROLES = {'admin'}

PRIVATE_CHAT_DISABLED_MESSAGE = 'Private chats are disabled for your role. Please use a Team Workspace.'
NO_WORKSPACE_ASSIGNMENT_MESSAGE = 'Please contact admin to assign you to a Team Workspace.'


async def user_in_any_group(user_id: str, group_names: set[str], db: AsyncSession | None = None) -> bool:
    """Return whether user_id belongs to at least one named Group."""
    if not user_id or not group_names:
        return False

    async with get_async_db_context(db) as db:
        result = await db.execute(
            select(Group.id)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(and_(GroupMember.user_id == user_id, Group.name.in_(list(group_names))))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None


async def can_use_private_chat(user, db: AsyncSession | None = None) -> bool:
    # Company patch: private chats restored for all authenticated users.
    role = getattr(user, 'role', None)
    return role in ('admin', 'user')


async def can_access_all_workspaces(user, db: AsyncSession | None = None) -> bool:
    """CEO group users can read/write all workspace chats.

    Core admins intentionally are not included here so workspace chat privacy is
    not weakened accidentally. Admins receive separate operational management
    bypasses in workspace member-management routes.
    """
    if getattr(user, 'role', None) != 'user':
        return False
    return await user_in_any_group(user.id, WORKSPACE_ALL_ACCESS_GROUP_NAMES, db=db)


async def can_create_workspace(user, db: AsyncSession | None = None) -> bool:
    return getattr(user, 'role', None) in WORKSPACE_CREATE_ALLOWED_CORE_ROLES


async def user_has_workspace_assignment(user, db: AsyncSession | None = None) -> bool:
    if not getattr(user, 'id', None):
        return False
    return bool(await Workspaces.get_for_user(user.id, db=db))


async def assert_private_chat_allowed(user, db: AsyncSession | None = None) -> None:
    # Company patch: private chats restored for all authenticated users; no-op.
    return


async def assert_workspace_create_allowed(user, db: AsyncSession | None = None) -> None:
    if await can_create_workspace(user, db=db):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail='Only admins can create Team Workspaces.',
    )
