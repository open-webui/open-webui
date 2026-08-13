import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.automations import (
    AutomationForm,
    AutomationListResponse,
    AutomationModel,
    AutomationResponse,
    AutomationRunModel,
    AutomationRuns,
    Automations,
)
from open_webui.models.access_grants import AccessGrants, has_public_write_access_grant
from open_webui.models.channels import Channels
from open_webui.models.config import Config
from open_webui.models.folders import Folders
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.automations import (
    execute_automation,
    next_n_runs_ns,
    next_run_ns,
    rrule_interval_seconds,
    validate_rrule,
)
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()

PAGE_ITEM_COUNT = 30


############################
# Helpers
############################


async def check_automations_permission(request, user):
    config = await Config.get_many('automations.enable', 'user.permissions')
    if not config.get('automations.enable'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.automations', config.get('user.permissions')
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )


def check_automation_access(automation, user):
    if not automation or user.id != automation.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


async def check_automation_limits(request, user, rrule_str: str, db, is_create: bool = False):
    """Enforce global automation limits. Admins bypass all checks."""
    if user.role == 'admin':
        return

    # Max count (create only)
    if is_create:
        max_count = await Config.get('automations.max_count')
        if max_count:
            max_count = int(max_count)
            if max_count > 0 and await Automations.count_by_user(user.id, db=db) >= max_count:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.AUTOMATION_LIMIT_EXCEEDED(max_count),
                )

    # Min interval (create + update)
    min_interval = await Config.get('automations.min_interval')
    if min_interval:
        min_interval = int(min_interval)
        if min_interval > 0:
            interval = rrule_interval_seconds(rrule_str)
            if interval is not None and interval < min_interval:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.AUTOMATION_TOO_FREQUENT(min_interval),
                )


async def check_automation_folder_access(folder_id: Optional[str], user, db: AsyncSession):
    if folder_id is None:
        return
    folder = await Folders.get_folder_by_id_and_user_id(folder_id, user.id, db=db)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


async def check_automation_channel_access(form_data: AutomationForm, user, db: AsyncSession):
    target = form_data.data.target
    if not target or target.type != 'channel':
        return

    if not target.channel_id or not await Config.get('channels.enable'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    channel = await Channels.get_channel_by_id(target.channel_id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if user.role == 'admin':
        return
    if not await has_permission(user.id, 'features.channels', await Config.get('user.permissions')):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
    if channel.type in ['group', 'dm']:
        allowed = await Channels.is_user_channel_member(channel.id, user.id, db=db)
    else:
        allowed = has_public_write_access_grant(channel.access_grants) or await AccessGrants.has_access(
            user_id=user.id, resource_type='channel', resource_id=channel.id, permission='write', db=db
        )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


async def enrich_automation(automation: AutomationModel, db: AsyncSession, tz: str = None) -> AutomationResponse:
    """Full enrichment for single-item views (includes next_runs computation)."""
    last_run = await AutomationRuns.get_latest(automation.id, db=db)
    return AutomationResponse(
        **automation.model_dump(),
        last_run=last_run,
        next_runs=next_n_runs_ns(automation.data['rrule'], tz=tz),
    )


############################
# GetAutomationItems (paginated)
############################


@router.get('/list')
async def get_automation_items(
    request: Request,
    query: Optional[str] = None,
    status: Optional[str] = None,
    folder_id: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    limit = PAGE_ITEM_COUNT
    page = max(1, page)
    skip = (page - 1) * limit

    result = await Automations.search_automations(
        user_id=user.id,
        query=query,
        status=status,
        folder_id=folder_id,
        skip=skip,
        limit=limit,
        db=db,
    )

    # Batch-fetch latest runs in a single query instead of N+1
    ids = [item.id for item in result.items]
    latest_runs = await AutomationRuns.get_latest_batch(ids, db=db) if ids else {}

    return {
        'items': [
            AutomationResponse(
                **item.model_dump(),
                last_run=latest_runs.get(item.id),
            )
            for item in result.items
        ],
        'total': result.total,
    }


############################
# CreateNewAutomation
############################


@router.post('/create', response_model=AutomationResponse)
async def create_new_automation(
    request: Request,
    form_data: AutomationForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    await check_automation_folder_access(form_data.folder_id, user, db)
    await check_automation_channel_access(form_data, user, db)
    try:
        validate_rrule(form_data.data.rrule, tz=user.timezone)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await check_automation_limits(request, user, form_data.data.rrule, db, is_create=True)

    tz = user.timezone
    automation = await Automations.insert(user.id, form_data, next_run_ns(form_data.data.rrule, tz=tz), db=db)
    response = await enrich_automation(automation, db, tz=tz)
    await publish_event(
        request,
        EVENTS.AUTOMATION_CREATED,
        actor=user,
        subject_id=automation.id,
        data={'name': automation.name, 'is_active': automation.is_active, 'folder_id': automation.folder_id},
    )
    return response


############################
# GetAutomationById
############################


@router.get('/{id}', response_model=AutomationResponse)
async def get_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    return await enrich_automation(automation, db, tz=user.timezone)


############################
# UpdateAutomationById
############################


@router.post('/{id}/update', response_model=AutomationResponse)
async def update_automation_by_id(
    request: Request,
    id: str,
    form_data: AutomationForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    await check_automation_folder_access(form_data.folder_id, user, db)
    await check_automation_channel_access(form_data, user, db)

    try:
        validate_rrule(form_data.data.rrule, tz=user.timezone)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await check_automation_limits(request, user, form_data.data.rrule, db, is_create=False)

    tz = user.timezone
    updated = await Automations.update_by_id(id, form_data, next_run_ns(form_data.data.rrule, tz=tz), db=db)
    response = await enrich_automation(updated, db, tz=tz)
    await publish_event(
        request,
        EVENTS.AUTOMATION_UPDATED,
        actor=user,
        subject_id=updated.id,
        data={'name': updated.name, 'is_active': updated.is_active, 'folder_id': updated.folder_id},
    )
    return response


############################
# ToggleAutomationById
############################


@router.post('/{id}/toggle', response_model=AutomationResponse)
async def toggle_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    toggled = await Automations.toggle(id, next_run_ns(automation.data['rrule'], tz=user.timezone), db=db)
    response = await enrich_automation(toggled, db, tz=user.timezone)
    await publish_event(
        request,
        EVENTS.AUTOMATION_ENABLED if toggled.is_active else EVENTS.AUTOMATION_DISABLED,
        actor=user,
        subject_id=toggled.id,
        subject_type='automation',
        data={'name': toggled.name},
    )
    return response


############################
# RunAutomationById
############################


@router.post('/{id}/run')
async def run_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    asyncio.create_task(execute_automation(request.app, automation))
    await publish_event(
        request,
        EVENTS.AUTOMATION_RUN_STARTED,
        actor=user,
        subject_id=automation.id,
        data={'name': automation.name},
    )
    return await enrich_automation(automation, db, tz=user.timezone)


############################
# DeleteAutomationById
############################


@router.delete('/{id}/delete')
async def delete_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    await AutomationRuns.delete_by_automation(id, db=db)
    result = await Automations.delete(id, db=db)
    if result:
        await publish_event(
            request,
            EVENTS.AUTOMATION_DELETED,
            actor=user,
            subject_id=id,
            data={'name': automation.name},
        )
    return result


############################
# GetAutomationRuns
############################


@router.get('/{id}/runs', response_model=list[AutomationRunModel])
async def get_automation_runs(
    request: Request,
    id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    return await AutomationRuns.get_by_automation(id, skip=skip, limit=limit, db=db)
