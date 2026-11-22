import asyncio
import hmac
import json
import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.automations import (
    AutomationData,
    AutomationForm,
    AutomationListResponse,
    AutomationModel,
    AutomationResponse,
    AutomationRunModel,
    AutomationRuns,
    Automations,
    hide_webhook_token,
)
from open_webui.models.users import UserResponse, Users
from open_webui.models.access_grants import AccessGrantResponse, AccessGrants, has_public_write_access_grant
from open_webui.models.channels import Channels
from open_webui.models.config import Config
from open_webui.models.folders import Folders
from open_webui.models.groups import Groups
from open_webui.utils.access_control.automations import can_manage_automation, has_automation_access
from open_webui.utils.access_control.folders import has_folder_write_access
from open_webui.utils.access_control import has_permission, validate_access_grants
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.agents.discovery import get_models as get_agent_models
from open_webui.utils.automations import (
    execute_automation,
    rrule_interval_seconds,
    schedule_next_run,
    schedule_next_runs,
    validate_rrule,
    validate_automation_machine,
)
from open_webui.utils.prompt_variables import PromptVariableError, fill_variables
from open_webui.utils.rate_limit import RateLimiter
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()

PAGE_ITEM_COUNT = 30
HOOK_MAX_BODY = 64 * 1024
hook_limiter = RateLimiter(30, 60)


# Helpers


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


async def can_use_automation_webhooks(user) -> bool:
    config = await Config.get_many('automations.enable', 'automations.webhooks.enable', 'user.permissions')
    if not config.get('automations.enable') or not config.get('automations.webhooks.enable'):
        return False
    return user.role == 'admin' or await has_permission(user.id, 'features.automations', config.get('user.permissions'))


async def check_automation_triggers(form_data: AutomationForm, user, db, is_create: bool = False):
    data = form_data.data
    if data.webhook and not await can_use_automation_webhooks(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED)
    if not data.rrule and not data.webhook:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Add a schedule or a webhook')
    if data.rrule:
        try:
            await validate_rrule(data.rrule, tz=user.timezone)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await check_automation_limits(None, user, data.rrule or None, db, is_create=is_create)


def check_automation_access(automation, user):
    """The owner only: what a run does, since every run uses the owner's account."""
    if not automation or user.id != automation.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


async def get_accessible_automation(id: str, user, permission: str, db: AsyncSession) -> AutomationModel:
    """Read: view it and its runs. Write: rename, reschedule, pause and run it."""
    automation = await Automations.get_by_id(id, db=db)
    if not await has_automation_access(user, automation, permission, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return automation


async def get_owner_timezone(automation, user) -> Optional[str]:
    """Schedules follow the owner's timezone, like the scheduler does when it reschedules."""
    if automation.user_id == user.id:
        return user.timezone
    owner = await Users.get_user_by_id(automation.user_id)
    return owner.timezone if owner else None


async def check_automation_limits(request, user, rrule_str: Optional[str], db, is_create: bool = False):
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
    min_interval = await Config.get('automations.min_interval') if rrule_str else None
    if min_interval:
        min_interval = int(min_interval)
        if min_interval > 0:
            interval = await rrule_interval_seconds(rrule_str)
            if interval is not None and interval < min_interval:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.AUTOMATION_TOO_FREQUENT(min_interval),
                )


async def check_automation_folder_access(folder_id: Optional[str], user, db: AsyncSession):
    """An automation can live in any folder its creator can write to."""
    if folder_id is None:
        return
    folder = await Folders.get_folder_by_id(folder_id, db=db)
    if not folder or not (user.role == 'admin' or await has_folder_write_access(user.id, folder_id, db=db)):
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


async def enrich_automation(automation: AutomationModel, db: AsyncSession, viewer) -> AutomationResponse:
    """Full enrichment for single-item views (includes next_runs computation)."""
    last_run = await AutomationRuns.get_latest(automation.id, db=db)
    is_owner = viewer.id == automation.user_id
    owner = viewer if is_owner else await Users.get_user_by_id(automation.user_id, db=db)
    grants = (
        await AccessGrants.get_grants_by_resource('automation', automation.id, db=db)
        if can_manage_automation(viewer, automation)
        else None
    )
    return AutomationResponse(
        # The webhook URL starts runs as the owner, so only the owner sees its token.
        **{**automation.model_dump(), 'data': automation.data if is_owner else hide_webhook_token(automation.data)},
        last_run=last_run,
        next_runs=await schedule_next_runs(automation.data, tz=owner.timezone if owner else None),
        user=UserResponse(**owner.model_dump()) if owner else None,
        write_access=await has_automation_access(viewer, automation, 'write', db=db),
        access_grants=[AccessGrantResponse.from_grant(g) for g in grants] if grants is not None else None,
    )


# GetAutomationItems (paginated)


@router.get('/list')
async def get_automation_items(
    request: Request,
    query: Optional[str] = None,
    status: Optional[str] = None,
    folder_id: Optional[str] = None,
    page: Optional[int] = 1,
    view: Literal['all', 'mine', 'shared'] = 'all',
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    limit = PAGE_ITEM_COUNT
    page = max(1, page)
    skip = (page - 1) * limit

    group_ids = [group.id for group in await Groups.get_groups_by_member_id(user.id, db=db, include_inherited=True)]
    result = await Automations.search_automations(
        user_id=user.id,
        query=query,
        status=status,
        folder_id=folder_id,
        skip=skip,
        limit=limit,
        view=view,
        group_ids=group_ids,
        db=db,
    )

    # Batch-fetch latest runs in a single query instead of N+1
    ids = [item.id for item in result.items]
    latest_runs = await AutomationRuns.get_latest_batch(ids, db=db) if ids else {}
    shared = [item for item in result.items if item.user_id != user.id]
    owners = {
        u.id: UserResponse(**u.model_dump())
        for u in await Users.get_users_by_user_ids(list({item.user_id for item in result.items}), db=db)
    }
    writable = (
        {item.id for item in shared}
        if user.role == 'admin'
        else await AccessGrants.get_accessible_resource_ids(
            user_id=user.id,
            resource_type='automation',
            resource_ids=[item.id for item in shared],
            permission='write',
            user_group_ids=set(group_ids),
            db=db,
        )
    )

    items = []
    for item in result.items:
        is_owner = item.user_id == user.id
        items.append(
            AutomationResponse(
                **{**item.model_dump(), 'data': item.data if is_owner else hide_webhook_token(item.data)},
                last_run=latest_runs.get(item.id),
                user=owners.get(item.user_id),
                write_access=is_owner or item.id in writable,
            )
        )
    return {'items': items, 'total': result.total}


@router.get('/models')
async def get_automation_models(
    request: Request,
    machine_id: str | None = None,
    terminal_id: str | None = None,  # former name of machine_id
    cwd: str | None = None,
    automation_id: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    machine_id = machine_id or terminal_id
    if not machine_id:
        raise HTTPException(400, 'Select a machine for the agent.')
    automation = None
    if automation_id:
        automation = await get_accessible_automation(automation_id, user, 'read', db)
        # Only the owner picks the model, so the automation's machine context is the owner's.
        if automation.user_id != user.id:
            automation = None
    metadata = {'machine_id': machine_id}
    if automation:
        metadata.update(model_id=automation.data.get('model_id'), automation_id=automation.id)
    return await get_agent_models(request, user, metadata, cwd=cwd)


# Create New Automation


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
    await validate_automation_machine(request, user, form_data.data.model_dump())
    # The first run creates the ongoing chat or thread; a form can't point at one.
    if form_data.data.target:
        form_data.data.target.chat_id = None
        form_data.data.target.thread_id = None
    await check_automation_triggers(form_data, user, db, is_create=True)

    tz = user.timezone
    next_run_at = await schedule_next_run(form_data.data.model_dump(), tz=tz)
    automation = await Automations.insert(user.id, form_data, next_run_at, db=db)
    response = await enrich_automation(automation, db, viewer=user)
    await publish_event(
        request,
        EVENTS.AUTOMATION_CREATED,
        actor=user,
        subject_id=automation.id,
        data={'name': automation.name, 'is_active': automation.is_active, 'folder_id': automation.folder_id},
    )
    return response


# Get Automation By Id


@router.get('/{id}', response_model=AutomationResponse)
async def get_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await get_accessible_automation(id, user, 'read', db)
    return await enrich_automation(automation, db, viewer=user)


# Update Automation By Id


@router.post('/{id}/update', response_model=AutomationResponse)
async def update_automation_by_id(
    request: Request,
    id: str,
    form_data: AutomationForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await get_accessible_automation(id, user, 'write', db)
    if automation.user_id == user.id:
        await check_automation_folder_access(form_data.folder_id, user, db)
        await check_automation_channel_access(form_data, user, db)
        await validate_automation_machine(request, user, form_data.data.model_dump(), id)
        await check_automation_triggers(form_data, user, db)
    else:
        # Runs use the owner's account, so others only change when it runs: the name,
        # the schedule and whether it's on. Everything else stays as the owner set it.
        form_data = AutomationForm(
            name=form_data.name,
            folder_id=automation.folder_id,
            data=AutomationData(**{**automation.data, 'rrule': form_data.data.rrule}),
            meta=automation.meta,
            is_active=form_data.is_active,
        )
        if not form_data.data.rrule and not form_data.data.webhook:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Add a schedule or a webhook')
        if form_data.data.rrule:
            try:
                await validate_rrule(form_data.data.rrule, tz=await get_owner_timezone(automation, user))
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        await check_automation_limits(None, user, form_data.data.rrule or None, db)

    next_run_at = await schedule_next_run(form_data.data.model_dump(), tz=await get_owner_timezone(automation, user))
    updated = await Automations.update_by_id(id, form_data, next_run_at, db=db)
    response = await enrich_automation(updated, db, viewer=user)
    await publish_event(
        request,
        EVENTS.AUTOMATION_UPDATED,
        actor=user,
        subject_id=updated.id,
        data={'name': updated.name, 'is_active': updated.is_active, 'folder_id': updated.folder_id},
    )
    return response


# Toggle Automation By Id


@router.post('/{id}/toggle', response_model=AutomationResponse)
async def toggle_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await get_accessible_automation(id, user, 'write', db)
    toggled = await Automations.toggle(
        id, await schedule_next_run(automation.data, tz=await get_owner_timezone(automation, user)), db=db
    )
    response = await enrich_automation(toggled, db, viewer=user)
    await publish_event(
        request,
        EVENTS.AUTOMATION_ENABLED if toggled.is_active else EVENTS.AUTOMATION_DISABLED,
        actor=user,
        subject_id=toggled.id,
        subject_type='automation',
        data={'name': toggled.name},
    )
    return response


# Run Automation By Id


class AutomationRunForm(BaseModel):
    variables: Optional[dict[str, Any]] = None


def check_variables(automation: AutomationModel, variables: Optional[dict]):
    try:
        fill_variables(automation.data['prompt'], variables)
    except PromptVariableError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post('/{id}/run')
async def run_automation_by_id(
    request: Request,
    id: str,
    form_data: Optional[AutomationRunForm] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await get_accessible_automation(id, user, 'write', db)
    variables = form_data.variables if form_data else None
    # Variables are written into the owner's prompt, so only the owner fills them in.
    if variables and automation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    check_variables(automation, variables)
    automation = await Automations.update_last_run_at(automation.id, db=db)
    asyncio.create_task(execute_automation(request.app, automation, variables))
    await publish_event(
        request,
        EVENTS.AUTOMATION_RUN_STARTED,
        actor=user,
        subject_id=automation.id,
        data={'name': automation.name},
    )
    return await enrich_automation(automation, db, viewer=user)


# Webhook Trigger


@router.post('/{id}/token/regenerate', response_model=AutomationResponse)
async def regenerate_automation_token(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    if not await can_use_automation_webhooks(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED)
    updated = await Automations.regenerate_webhook_token(id, db=db)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())
    return await enrich_automation(updated, db, viewer=user)


async def read_hook_variables(request: Request) -> dict:
    variables: dict = dict(request.query_params)
    if request.method != 'POST':
        return variables
    if int(request.headers.get('content-length') or 0) > HOOK_MAX_BODY:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    body = await request.body()
    if len(body) > HOOK_MAX_BODY:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    if not body.strip():
        return variables
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Body must be JSON')
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Body must be a JSON object')
    # {"variables": {...}} wins; any other payload (GitHub, Gitea) is read as-is.
    wrapped = payload.get('variables')
    return {**variables, **payload, **(wrapped if isinstance(wrapped, dict) else {})}


@router.api_route('/hooks/{id}/{token}', methods=['GET', 'POST'])
async def trigger_automation_webhook(request: Request, id: str, token: str):
    """Public: the token in the URL is the credential."""
    automation = await Automations.get_by_id(id)
    webhook = (automation.data.get('webhook') or {}) if automation else {}
    config = await Config.get_many('automations.enable', 'automations.webhooks.enable')
    if (
        not automation
        or not webhook.get('token')
        or not hmac.compare_digest(webhook['token'], token)
        or not config.get('automations.enable')
        or not config.get('automations.webhooks.enable')
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if request.method == 'GET' and not webhook.get('allow_get'):
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

    owner = await Users.get_user_by_id(automation.user_id)
    if not owner or not await can_use_automation_webhooks(owner):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not automation.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Automation is paused')
    if await hook_limiter.is_limited(getattr(request.app.state, 'redis', None), f'automation-hook:{id}'):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    variables = await read_hook_variables(request)
    check_variables(automation, variables)
    automation = await Automations.update_last_run_at(automation.id)
    asyncio.create_task(execute_automation(request.app, automation, variables))
    await publish_event(
        request,
        EVENTS.AUTOMATION_RUN_STARTED,
        actor=owner,
        subject_id=automation.id,
        source='automation_webhook',
        data={'name': automation.name},
    )
    return JSONResponse({'status': 'accepted'}, status_code=202, headers={'Cache-Control': 'no-store'})


# Delete Automation By Id


@router.delete('/{id}/delete')
async def delete_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await get_accessible_automation(id, user, 'read', db)
    if not can_manage_automation(user, automation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
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


# Update Automation Access By Id


class AutomationAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/{id}/access/update', response_model=AutomationResponse)
async def update_automation_access_by_id(
    request: Request,
    id: str,
    form_data: AutomationAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = await get_accessible_automation(id, user, 'read', db)
    # Editing an automation does not grant permission to manage its sharing.
    if not can_manage_automation(user, automation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    access_grants = await validate_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        resource_type='automation',
        db=db,
    )
    await AccessGrants.set_access_grants('automation', id, access_grants, db=db)
    await publish_event(
        request,
        EVENTS.AUTOMATION_ACCESS_UPDATED,
        actor=user,
        subject_id=id,
        data={'grant_count': len(access_grants)},
    )
    return await enrich_automation(automation, db, viewer=user)


# Get Automation Runs


@router.get('/{id}/runs', response_model=list[AutomationRunModel])
async def get_automation_runs(
    request: Request,
    id: str,
    skip: int = 0,
    limit: int = 50,
    direction: Literal['asc', 'desc'] = 'desc',
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    await get_accessible_automation(id, user, 'read', db)
    return await AutomationRuns.get_by_automation(id, skip=skip, limit=limit, direction=direction, db=db)


@router.get('/{id}/runs/{run_id}', response_model=AutomationRunModel)
async def get_automation_run(
    request: Request,
    id: str,
    run_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    from open_webui.models.automations import AutomationRun

    await check_automations_permission(request, user)
    await get_accessible_automation(id, user, 'read', db)
    run = await db.get(AutomationRun, run_id)
    if not run or run.automation_id != id:
        raise HTTPException(404, 'Run not found')
    return AutomationRunModel.model_validate(run)
