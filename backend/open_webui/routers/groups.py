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
from open_webui.models.models import ModelForm, ModelMeta, ModelParams, Models
from open_webui.models.tools import Tools
from open_webui.models.users import UserInfoResponse, Users
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.models import get_all_models
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


class GroupModelIdsForm(BaseModel):
    model_ids: list[str] = Field(default_factory=list, max_length=100)


class GroupModelResponse(BaseModel):
    id: str
    name: str
    base_model_id: str | None = None
    description: str | None = None
    selected: bool = False


def _model_label(model: dict) -> str:
    return str(model.get('name') or model.get('id') or '')


def _model_info(model: dict) -> dict:
    info = model.get('info') or {}
    return info if isinstance(info, dict) else {}


def _grant_data(grant) -> dict:
    return grant.model_dump() if hasattr(grant, 'model_dump') else dict(grant)


def _model_meta(model) -> dict:
    data = model.model_dump() if hasattr(model, 'model_dump') else dict(model)
    meta = data.get('meta') or {}
    return meta if isinstance(meta, dict) else {}


def _model_hidden(model) -> bool:
    return bool(_model_meta(model).get('hidden'))


def _is_assignable_model(model: dict) -> bool:
    if model.get('arena'):
        return False
    if 'pipeline' in model and model['pipeline'].get('type', None) == 'filter':
        return False
    if _model_meta(model).get('hidden'):
        return False
    return True


def _model_summary(model, selected: bool = False) -> dict:
    data = model.model_dump() if hasattr(model, 'model_dump') else dict(model)
    meta = _model_meta(model)
    return {
        'id': data.get('id'),
        'name': data.get('name') or data.get('id'),
        'base_model_id': data.get('base_model_id'),
        'description': meta.get('description') if isinstance(meta, dict) else None,
        'selected': selected,
    }


def _with_group_read_grant(access_grants: list, group_id: str) -> list[dict]:
    grants = [_grant_data(grant) for grant in (access_grants or [])]
    if not any(
        grant.get('principal_type') == 'group'
        and grant.get('principal_id') == group_id
        and grant.get('permission') == 'read'
        for grant in grants
    ):
        grants.append(
            {
                'principal_type': 'group',
                'principal_id': group_id,
                'permission': 'read',
            }
        )
    return grants


def _without_group_grants(access_grants: list, group_id: str) -> list[dict]:
    grants = []
    for grant in access_grants or []:
        grant_data = _grant_data(grant)
        if (
            grant_data.get('principal_type') == 'group'
            and grant_data.get('principal_id') == group_id
            and grant_data.get('permission') == 'read'
        ):
            continue
        grants.append(grant_data)
    return grants


async def _ensure_model_access_record(model_id: str, visible_model: dict, user, db: AsyncSession):
    model = await Models.get_model_by_id(model_id, db=db)
    if model:
        if not model.is_active or _model_hidden(model):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
        return model

    model_info = _model_info(visible_model)
    model_meta = model_info.get('meta') or {}

    return await Models.insert_new_model(
        ModelForm(
            id=model_id,
            base_model_id=None,
            name=_model_label(visible_model),
            meta=ModelMeta(
                description=visible_model.get('description')
                or (model_meta.get('description') if isinstance(model_meta, dict) else None),
                capabilities=visible_model.get('capabilities'),
            ),
            params=ModelParams(),
            access_grants=[],
            is_active=True,
        ),
        user.id,
        db=db,
    )

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
# ManageGroupModels
############################


@router.get('/id/{id}/models', response_model=list[GroupModelResponse])
async def get_group_models(id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    group = await Groups.get_group_by_id(id, db=db)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    models = await Models.get_all_models(db=db)
    return [
        _model_summary(model, selected=True)
        for model in models
        if model.is_active
        and not _model_hidden(model)
        and any(
            grant.principal_type == 'group'
            and grant.principal_id == id
            and grant.permission == 'read'
            for grant in (model.access_grants or [])
        )
    ]


@router.get('/id/{id}/models/available', response_model=list[GroupModelResponse])
async def get_available_group_models(
    id: str,
    request: Request,
    query: Optional[str] = None,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    group = await Groups.get_group_by_id(id, db=db)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    configured = {model.id: model for model in await Models.get_all_models(db=db)}
    q = (query or '').strip().lower()
    items = []

    for model in await get_all_models(request, user=user):
        if not _is_assignable_model(model):
            continue

        model_id = str(model.get('id') or '')
        if not model_id:
            continue

        model_info = _model_info(model)
        model_meta = model_info.get('meta') or {}
        configured_model = configured.get(model_id)
        if configured_model and (not configured_model.is_active or _model_hidden(configured_model)):
            continue

        access_grants = configured_model.access_grants if configured_model else model_info.get('access_grants', [])
        grants = [_grant_data(grant) for grant in (access_grants or [])]
        selected = any(
            grant.get('principal_type') == 'group'
            and grant.get('principal_id') == id
            and grant.get('permission') == 'read'
            for grant in grants
        )
        item = {
            'id': model_id,
            'name': _model_label(model),
            'base_model_id': model_info.get('base_model_id'),
            'description': model.get('description')
            or (model_meta.get('description') if isinstance(model_meta, dict) else None),
            'selected': selected,
        }
        if q and q not in item['id'].lower() and q not in item['name'].lower():
            continue
        items.append(item)

    return sorted(items, key=lambda item: item['name'].lower())


@router.post('/id/{id}/models/add', response_model=list[GroupModelResponse])
async def add_models_to_group(
    id: str,
    form_data: GroupModelIdsForm,
    request: Request,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    group = await Groups.get_group_by_id(id, db=db)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    visible_models = {
        model.get('id'): model
        for model in await get_all_models(request, user=user)
        if model.get('id') and _is_assignable_model(model)
    }

    for model_id in form_data.model_ids:
        visible_model = visible_models.get(model_id)
        if not visible_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

        model = await _ensure_model_access_record(model_id, visible_model, user, db)
        if not model:
            continue
        await AccessGrants.set_access_grants(
            'model',
            model.id,
            _with_group_read_grant(model.access_grants or [], id),
            db=db,
        )

    return await get_group_models(id, user=user, db=db)


@router.post('/id/{id}/models/remove', response_model=list[GroupModelResponse])
async def remove_models_from_group(
    id: str,
    form_data: GroupModelIdsForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    group = await Groups.get_group_by_id(id, db=db)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    for model_id in form_data.model_ids:
        model = await Models.get_model_by_id(model_id, db=db)
        if not model:
            continue
        await AccessGrants.set_access_grants(
            'model',
            model.id,
            _without_group_grants(model.access_grants or [], id),
            db=db,
        )

    return await get_group_models(id, user=user, db=db)


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
    }
