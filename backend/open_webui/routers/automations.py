import asyncio
import logging

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from open_webui.models.automations import (
    Automations,
    AutomationRuns,
    AutomationForm,
    AutomationModel,
    AutomationResponse,
    AutomationRunModel,
    AutomationListResponse,
)
from open_webui.utils.automations import (
    validate_rrule,
    next_run_ns,
    next_n_runs_ns,
    execute_automation,
)
from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.utils.access_control import has_permission
from open_webui.internal.db import get_session
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

router = APIRouter()

PAGE_ITEM_COUNT = 30


############################
# Helpers
############################


def check_automations_permission(request, user):
    if user.role != 'admin' and not has_permission(
        user.id, 'features.automations', request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )


def check_automation_access(automation, user):
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if user.role != 'admin' and user.id != automation.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )


def enrich_automation(
    automation: AutomationModel, db: Session, tz: str = None
) -> AutomationResponse:
    last_run = AutomationRuns.get_latest(automation.id, db=db)
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
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_automations_permission(request, user)
    limit = PAGE_ITEM_COUNT
    page = max(1, page)
    skip = (page - 1) * limit

    result = Automations.search_automations(
        user_id=user.id,
        query=query,
        status=status,
        skip=skip,
        limit=limit,
        db=db,
    )

    return {
        'items': [
            enrich_automation(item, db, tz=user.timezone)
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
    db: Session = Depends(get_session),
):
    check_automations_permission(request, user)
    try:
        validate_rrule(form_data.data.rrule)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Validate terminal server exists if linked
    if form_data.data.terminal and form_data.data.terminal.server_id:
        connections = request.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
        if not any(c.get('id') == form_data.data.terminal.server_id for c in connections):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Terminal server not found',
            )

    tz = user.timezone
    automation = Automations.insert(
        user.id, form_data, next_run_ns(form_data.data.rrule, tz=tz), db=db
    )
    return enrich_automation(automation, db, tz=tz)


############################
# GetAutomationById
############################


@router.get('/{id}', response_model=AutomationResponse)
async def get_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_automations_permission(request, user)
    automation = Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    return enrich_automation(automation, db, tz=user.timezone)


############################
# UpdateAutomationById
############################


@router.post('/{id}/update', response_model=AutomationResponse)
async def update_automation_by_id(
    request: Request,
    id: str,
    form_data: AutomationForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_automations_permission(request, user)
    automation = Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)

    try:
        validate_rrule(form_data.data.rrule)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Validate terminal server exists if linked
    if form_data.data.terminal and form_data.data.terminal.server_id:
        connections = request.app.state.config.TERMINAL_SERVER_CONNECTIONS or []
        if not any(c.get('id') == form_data.data.terminal.server_id for c in connections):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Terminal server not found',
            )

    tz = user.timezone
    updated = Automations.update_by_id(
        id, form_data, next_run_ns(form_data.data.rrule, tz=tz), db=db
    )
    return enrich_automation(updated, db, tz=tz)


############################
# ToggleAutomationById
############################


@router.post('/{id}/toggle', response_model=AutomationResponse)
async def toggle_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_automations_permission(request, user)
    automation = Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    toggled = Automations.toggle(
        id, next_run_ns(automation.data['rrule'], tz=user.timezone), db=db
    )
    return enrich_automation(toggled, db, tz=user.timezone)


############################
# RunAutomationById
############################


@router.post('/{id}/run')
async def run_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_automations_permission(request, user)
    automation = Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    asyncio.create_task(execute_automation(request.app, automation))
    return enrich_automation(automation, db, tz=user.timezone)


############################
# DeleteAutomationById
############################


@router.delete('/{id}/delete')
async def delete_automation_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_automations_permission(request, user)
    automation = Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    AutomationRuns.delete_by_automation(id, db=db)
    return Automations.delete(id, db=db)


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
    db: Session = Depends(get_session),
):
    check_automations_permission(request, user)
    automation = Automations.get_by_id(id, db=db)
    check_automation_access(automation, user)
    return AutomationRuns.get_by_automation(id, skip=skip, limit=limit, db=db)



