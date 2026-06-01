import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.config import CACHE_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.groups import (
    GroupForm,
    GroupInfoResponse,
    GroupResponse,
    Groups,
    GroupUpdateForm,
    UserIdsForm,
)
from open_webui.models.knowledge import Knowledges
from open_webui.models.models import Models
from open_webui.models.tools import Tools
from open_webui.models.users import UserInfoResponse, Users
from open_webui.utils.auth import get_admin_user, get_verified_user
from sqlalchemy.ext.asyncio import AsyncSession

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
    form_data: GroupForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        group = await Groups.insert_new_group(user.id, form_data, db=db)
        if group:
            return GroupResponse(
                **group.model_dump(),
                member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error creating group'),
            )
    except Exception as e:
        log.exception(f'Error creating a new group: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
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
            status_code=status.HTTP_401_UNAUTHORIZED,
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
            status_code=status.HTTP_401_UNAUTHORIZED,
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
            status_code=status.HTTP_401_UNAUTHORIZED,
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
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# UpdateGroupById
############################


@router.post('/id/{id}/update', response_model=Optional[GroupResponse])
async def update_group_by_id(
    id: str,
    form_data: GroupUpdateForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        group = await Groups.update_group_by_id(id, form_data, db=db)
        if group:
            return GroupResponse(
                **group.model_dump(),
                member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating group'),
            )
    except Exception as e:
        log.exception(f'Error updating group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# AddUserToGroupByUserIdAndGroupId
############################


@router.post('/id/{id}/users/add', response_model=Optional[GroupResponse])
async def add_user_to_group(
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
            return GroupResponse(
                **group.model_dump(),
                member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error adding users to group'),
            )
    except Exception as e:
        log.exception(f'Error adding users to group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post('/id/{id}/users/remove', response_model=Optional[GroupResponse])
async def remove_users_from_group(
    id: str,
    form_data: UserIdsForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        group = await Groups.remove_users_from_group(id, form_data.user_ids, db=db)
        if group:
            return GroupResponse(
                **group.model_dump(),
                member_count=await Groups.get_group_member_count_by_id(group.id, db=db),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error removing users from group'),
            )
    except Exception as e:
        log.exception(f'Error removing users from group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# DeleteGroupById
############################


@router.delete('/id/{id}/delete', response_model=bool)
async def delete_group_by_id(id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    try:
        result = await Groups.delete_group_by_id(id, db=db)
        if result:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error deleting group'),
            )
    except Exception as e:
        log.exception(f'Error deleting group {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
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

    group_ids = {group.id}

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

    return {
        'group': {'id': group.id, 'name': group.name},
        'models': {
            'items': [
                {'id': m.id, 'name': m.name}
                for m in active_models
                if m.id in accessible_model_ids
            ],
            'total': len(active_models),
        },
        'knowledge': {
            'items': [
                {'id': k.id, 'name': k.name}
                for k in all_knowledge
                if k.id in accessible_knowledge_ids
            ],
            'total': len(all_knowledge),
        },
        'tools': {
            'items': [
                {'id': t.id, 'name': t.name}
                for t in all_tools
                if t.id in accessible_tool_ids
            ],
            'total': len(all_tools),
        },
        'permissions': group.permissions or {},
    }

