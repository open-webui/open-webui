import logging
import os
from pathlib import Path
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from open_webui.config import CACHE_DIR
from open_webui.models.config import Config
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.groups import (
    GroupForm,
    group_default_models,
    resolve_group_default_models,
    GroupHierarchyError,
    Group,
    GroupMember,
    group_user_memberships,
    descendant_groups,
    GroupInfoResponse,
    GroupResponse,
    Groups,
    GroupUpdateForm,
    UserIdsForm,
)
from open_webui.models.knowledge import Knowledges
from open_webui.models.models import Models
from open_webui.models.tools import Tools
from open_webui.models.users import UserInfoResponse, Users, User
from open_webui.utils.auth import get_admin_user, get_verified_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from open_webui.utils.access_control import combine_permissions
from open_webui.utils.json_codec import JSONCodec

log = logging.getLogger(__name__)

router = APIRouter()

############################
# GetFunctions
############################


@router.get('/', response_model=list[GroupResponse])
async def get_groups(
    share: Optional[bool] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    filter = {}

    # Admins can share to all groups regardless of share setting
    if user.role != 'admin':
        filter['member_id'] = user.id
        if share is not None:
            filter['share'] = share

    groups = await Groups.get_groups(filter=filter, db=db)

    return groups


############################
# CreateNewGroup
############################


@router.post('/create', response_model=Optional[GroupResponse])
async def create_new_group(
    request: Request,
    form_data: GroupForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        group = await Groups.insert_new_group(user.id, form_data, db=db)
        if group:
            await publish_event(
                request,
                EVENTS.GROUP_CREATED,
                actor=user,
                subject_id=group.id,
                data={'name': group.name},
            )
            return GroupResponse(
                **group.model_dump(),
                member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error creating group'),
            )
    except GroupHierarchyError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Error creating a new group: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error creating group'),
        )


############################
# GetGroupById
############################


@router.get('/id/{id}', response_model=Optional[GroupResponse])
async def get_group_by_id(id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    group = await Groups.get_group_by_id(id, db=db)
    if group:
        return GroupResponse(
            **group.model_dump(),
            member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get('/id/{id}/info', response_model=Optional[GroupInfoResponse])
async def get_group_info_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    group = await Groups.get_group_by_id(id, db=db)
    if group:
        return GroupInfoResponse(
            **group.model_dump(),
            member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# ExportGroupById
############################


class GroupExportResponse(GroupResponse):
    user_ids: list[str] = []
    pass


@router.get('/id/{id}/export', response_model=Optional[GroupExportResponse])
async def export_group_by_id(id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    group = await Groups.get_group_by_id(id, db=db)
    if group:
        return GroupExportResponse(
            **group.model_dump(),
            member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            user_ids=await Groups.get_group_user_ids_by_id(group.id, db=db),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# GetUsersInGroupById
############################


@router.post('/id/{id}/users', response_model=list[UserInfoResponse])
async def get_users_in_group(id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    try:
        users = await Users.get_users_by_group_id(id, db=db)
        return users
    except Exception as e:
        log.exception(f'Error adding users to group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error getting group members'),
        )


############################
# UpdateGroupById
############################


@router.post('/id/{id}/update', response_model=Optional[GroupResponse])
async def update_group_by_id(
    request: Request,
    id: str,
    form_data: GroupUpdateForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        changes = {}
        group = await Groups.update_group_by_id(id, form_data, db=db, changes=changes)
        if group:
            await publish_event(
                request,
                EVENTS.GROUP_UPDATED,
                actor=user,
                subject_id=id,
                data={'name': group.name, **changes},
            )
            return GroupResponse(
                **group.model_dump(),
                member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating group'),
            )
    except GroupHierarchyError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Error updating group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating group'),
        )


############################
# AddUserToGroupByUserIdAndGroupId
############################


@router.post('/id/{id}/users/add', response_model=Optional[GroupResponse])
async def add_user_to_group(
    request: Request,
    id: str,
    form_data: UserIdsForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        if form_data.user_ids:
            form_data.user_ids = await Users.get_valid_user_ids(form_data.user_ids, db=db)

        group = await Groups.add_users_to_group(id, form_data.user_ids, db=db)
        if group:
            await publish_event(
                request,
                EVENTS.GROUP_MEMBER_ADDED,
                actor=user,
                subject_id=id,
                data={'user_ids': form_data.user_ids},
            )
            return GroupResponse(
                **group.model_dump(),
                member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error adding users to group'),
            )
    except GroupHierarchyError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Error adding users to group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error adding users to group'),
        )


@router.post('/id/{id}/users/remove', response_model=Optional[GroupResponse])
async def remove_users_from_group(
    request: Request,
    id: str,
    form_data: UserIdsForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        group = await Groups.remove_users_from_group(id, form_data.user_ids, db=db)
        if group:
            await publish_event(
                request,
                EVENTS.GROUP_MEMBER_REMOVED,
                actor=user,
                subject_id=id,
                data={'user_ids': form_data.user_ids},
            )
            return GroupResponse(
                **group.model_dump(),
                member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error removing users from group'),
            )
    except GroupHierarchyError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Error removing users from group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error removing users from group'),
        )


############################
# DeleteGroupById
############################


@router.delete('/id/{id}/delete', response_model=bool)
async def delete_group_by_id(
    request: Request, id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    try:
        changes = {}
        result = await Groups.delete_group_by_id(id, db=db, changes=changes)
        if result:
            await publish_event(
                request,
                EVENTS.GROUP_DELETED,
                actor=user,
                subject_id=id,
                data=changes,
            )
            for child_id in changes['promoted_child_ids']:
                await publish_event(
                    request,
                    EVENTS.GROUP_UPDATED,
                    actor=user,
                    subject_id=child_id,
                    data={'old_parent_group_id': id, 'parent_group_id': changes['parent_group_id']},
                )
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error deleting group'),
            )
    except GroupHierarchyError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Error deleting group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error deleting group'),
        )


############################
# PreviewGroupAccess
############################


@router.get('/id/{id}/preview')
async def preview_group_access(
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Show what resources a group can access (preview audit)."""
    group = await Groups.get_group_by_id(id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    group_ids = await Groups.get_ancestor_ids(group.id, db=db)

    # Batch-check accessible resources using existing AccessGrants
    all_models = await Models.get_all_models(db=db)
    accessible_model_ids = await AccessGrants.get_accessible_resource_ids(
        user_id='',
        resource_type='model',
        resource_ids=[m.id for m in all_models],
        permission='read',
        user_group_ids=group_ids,
        db=db,
    )

    all_knowledge = await Knowledges.get_knowledge_bases(db=db)
    accessible_knowledge_ids = await AccessGrants.get_accessible_resource_ids(
        user_id='',
        resource_type='knowledge',
        resource_ids=[k.id for k in all_knowledge],
        permission='read',
        user_group_ids=group_ids,
        db=db,
    )

    all_tools = await Tools.get_tools(defer_content=True, db=db)
    accessible_tool_ids = await AccessGrants.get_accessible_resource_ids(
        user_id='',
        resource_type='tool',
        resource_ids=[t.id for t in all_tools],
        permission='read',
        user_group_ids=group_ids,
        db=db,
    )

    active_models = [m for m in all_models if m.is_active]

    ancestors = (await db.execute(select(Group).where(Group.id.in_(group_ids - {id})))).scalars().all()
    inherited_permissions = JSONCodec.loads(JSONCodec.dumps(await Config.get('user.permissions') or {}))
    for ancestor in ancestors:
        inherited_permissions = combine_permissions(inherited_permissions, ancestor.permissions or {})
    effective_permissions = combine_permissions(
        JSONCodec.loads(JSONCodec.dumps(inherited_permissions)), group.permissions or {}
    )

    default_models, source_group_id = resolve_group_default_models([group, *ancestors])
    if default_models is None:
        default_models = [
            model.strip() for model in (await Config.get('ui.default_models') or '').split(',') if model.strip()
        ]

    return {
        'group': {'id': group.id, 'name': group.name},
        'default_models': {
            'local': group_default_models(group),
            'effective': default_models,
            'source_group_id': source_group_id,
        },
        'models': {
            'items': [{'id': m.id, 'name': m.name} for m in active_models if m.id in accessible_model_ids],
            'total': len(active_models),
        },
        'knowledge': {
            'items': [{'id': k.id, 'name': k.name} for k in all_knowledge if k.id in accessible_knowledge_ids],
            'total': len(all_knowledge),
        },
        'tools': {
            'items': [{'id': t.id, 'name': t.name} for t in all_tools if t.id in accessible_tool_ids],
            'total': len(all_tools),
        },
        'permissions': group.permissions or {},
        'inherited_permissions': inherited_permissions,
        'effective_permissions': effective_permissions,
    }


class GroupMemberInfo(UserInfoResponse):
    membership_type: Literal['direct', 'inherited']
    via_group_ids: list[str] = []


class GroupMembersResponse(BaseModel):
    items: list[GroupMemberInfo]
    total: int
    counts: dict[str, int]


@router.get('/id/{id}/members', response_model=GroupMembersResponse)
async def inspect_group_members(
    id: str,
    membership: Literal['direct', 'inherited', 'effective'] = 'effective',
    query: str = '',
    page: int = Query(default=1, ge=1),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not await db.get(Group, id):
        raise HTTPException(status_code=404, detail='Group not found.')
    direct = select(GroupMember.user_id).where(GroupMember.group_id == id)
    effective = group_user_memberships([id], True)
    direct_count = (await db.execute(select(func.count()).select_from(direct.subquery()))).scalar_one()
    effective_count = (await db.execute(select(func.count()).select_from(effective))).scalar_one()
    stmt = select(User).where(User.id.in_(select(effective.c.user_id)))
    if membership == 'direct':
        stmt = stmt.where(User.id.in_(direct))
    elif membership == 'inherited':
        stmt = stmt.where(User.id.not_in(direct))
    if query:
        stmt = stmt.where(or_(User.name.ilike(f'%{query}%'), User.email.ilike(f'%{query}%')))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    users = (await db.execute(stmt.order_by(User.name, User.id).offset((page - 1) * 30).limit(30))).scalars().all()
    descendant = descendant_groups([id])
    sources = {u.id: [] for u in users}
    if sources:
        rows = await db.execute(
            select(GroupMember.user_id, GroupMember.group_id).where(
                GroupMember.user_id.in_(sources), GroupMember.group_id.in_(select(descendant.c.group_id))
            )
        )
        for uid, gid in rows:
            sources[uid].append(gid)
    return GroupMembersResponse(
        items=[
            GroupMemberInfo(
                id=u.id,
                name=u.name,
                email=u.email,
                role=u.role,
                membership_type='direct' if id in sources[u.id] else 'inherited',
                via_group_ids=sorted(gid for gid in sources[u.id] if gid != id),
            )
            for u in users
        ],
        total=total,
        counts={
            'direct': direct_count,
            'effective': effective_count,
            'inherited': effective_count - direct_count,
        },
    )
