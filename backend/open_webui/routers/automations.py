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
    AutomationForm,
    AutomationListResponse,
    AutomationModel,
    AutomationResponse,
    AutomationRunModel,
    AutomationRuns,
    Automations,
    hide_webhook_token,
)
from open_webui.models.users import Users
from open_webui.models.access_grants import AccessGrants, has_public_write_access_grant
from open_webui.models.channels import Channels
from open_webui.models.config import Config
from open_webui.models.folders import Folders
from open_webui.utils.access_control.folders import has_folder_write_access
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.agents.discovery import get_models as get_agent_models
from open_webui.utils.automations import (
    execute_automation,
    rrule_interval_seconds,
    schedule_next_run,
    schedule_next_runs,
    validate_rrule,
    validate_automation_terminal,
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
    if not automation or user.id != automation.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


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


async def check_automation_manage_access(automation, user, db: AsyncSession):
    """Pausing, running and run history: the creator, or anyone who can write to its folder."""
    if automation and automation.user_id == user.id:
        return
    if (
        automation
        and automation.folder_id
        and (user.role == 'admin' or await has_folder_write_access(user.id, automation.folder_id, db=db))
    ):
        return
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


async def enrich_automation(
    automation: AutomationModel, db: AsyncSession, tz: str = None, viewer=None
) -> AutomationResponse:
    """Full enrichment for single-item views (includes next_runs computation)."""
    last_run = await AutomationRuns.get_latest(automation.id, db=db)
    data = automation.data if viewer is None or viewer.id == automation.user_id else hide_webhook_token(automation.data)
    return AutomationResponse(
        **{**automation.model_dump(), 'data': data},
        last_run=last_run,
        next_runs=await schedule_next_runs(automation.data, tz=tz),
    )


# GetAutomationItems (paginated)


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


@router.get('/models')
async def get_automation_models(
    request: Request,
    terminal_id: str,
    cwd: str | None = None,
    automation_id: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_automations_permission(request, user)
    automation = None
    if automation_id:
        automation = await Automations.get_by_id(automation_id, db=db)
        check_automation_access(automation, user)
    metadata = {'terminal_id': terminal_id}
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
    await validate_automation_terminal(request, user, form_data.data.model_dump())
    # The first run creates the ongoing chat or thread; a form can't point at one.
    if form_data.data.target:
        form_data.data.target.chat_id = None
        form_data.data.target.thread_id = None
    await check_automation_triggers(form_data, user, db, is_create=True)

    tz = user.timezone
    next_run_at = await schedule_next_run(form_data.data.model_dump(), tz=tz)
    automation = await Automations.insert(user.id, form_data, next_run_at, db=db)
    response = await enrich_automation(automation, db, tz=tz)
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
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    return await enrich_automation(automation, db, tz=user.timezone)


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
    automation = await Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    await check_automation_folder_access(form_data.folder_id, user, db)
    await check_automation_channel_access(form_data, user, db)
    await validate_automation_terminal(request, user, form_data.data.model_dump(), id)
    await check_automation_triggers(form_data, user, db)

    tz = user.timezone
    next_run_at = await schedule_next_run(form_data.data.model_dump(), tz=tz)
    updated = await Automations.update_by_id(id, form_data, next_run_at, db=db)
    response = await enrich_automation(updated, db, tz=tz)
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
    automation = await Automations.get_by_id(id, db=db)
    await check_automation_manage_access(automation, user, db)
    toggled = await Automations.toggle(id, await schedule_next_run(automation.data, tz=user.timezone), db=db)
    response = await enrich_automation(toggled, db, tz=user.timezone, viewer=user)
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
    automation = await Automations.get_by_id(id, db=db)
    await check_automation_manage_access(automation, user, db)
    variables = form_data.variables if form_data else None
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
    return await enrich_automation(automation, db, tz=user.timezone, viewer=user)


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
    return await enrich_automation(updated, db, tz=user.timezone)


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
    automation = await Automations.get_by_id(id, db=db)
    await check_automation_manage_access(automation, user, db)
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
    automation = await Automations.get_by_id(id, db=db)
    await check_automation_manage_access(automation, user, db)
    run = await db.get(AutomationRun, run_id)
    if not run or run.automation_id != id:
        raise HTTPException(404, 'Run not found')
    return AutomationRunModel.model_validate(run)
