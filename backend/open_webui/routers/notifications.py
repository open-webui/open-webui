from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.models.config import Config
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_verified_user
from open_webui.utils.notifications import (
    create_target,
    delete_target,
    get_notification_event_catalog,
    list_targets,
    set_default_target,
    test_target,
    update_target,
)

router = APIRouter()


class NotificationTargetForm(BaseModel):
    id: str | None = None
    type: str | None = None
    enabled: bool | None = None
    events: list[str] | None = None
    delivery: str | None = None
    config: dict[str, Any] | None = None


async def _check_notifications_access(user) -> None:
    if not await Config.get('ui.enable_user_webhooks'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and not await has_permission(
        user.id, 'features.webhooks', await Config.get('user.permissions')
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)


@router.get('/events')
async def get_notification_events(user=Depends(get_verified_user)):
    await _check_notifications_access(user)
    return {'events': get_notification_event_catalog()}


@router.get('/targets')
async def get_notification_targets(user=Depends(get_verified_user)):
    await _check_notifications_access(user)
    return await list_targets(user.id)


@router.post('/targets')
async def create_notification_target(form_data: NotificationTargetForm, user=Depends(get_verified_user)):
    await _check_notifications_access(user)
    try:
        return await create_target(user.id, form_data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put('/targets/{target_id}')
async def update_notification_target(
    target_id: str, form_data: NotificationTargetForm, user=Depends(get_verified_user)
):
    await _check_notifications_access(user)
    try:
        return await update_target(user.id, target_id, form_data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete('/targets/{target_id}')
async def delete_notification_target(target_id: str, user=Depends(get_verified_user)):
    await _check_notifications_access(user)
    if not await delete_target(user.id, target_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return {'ok': True}


@router.put('/targets/{target_id}/default')
async def set_default_notification_target(target_id: str, user=Depends(get_verified_user)):
    await _check_notifications_access(user)
    try:
        return await set_default_target(user.id, target_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post('/targets/{target_id}/test')
async def test_notification_target(request: Request, target_id: str, user=Depends(get_verified_user)):
    await _check_notifications_access(user)
    try:
        app_name = getattr(request.app.state, 'WEBUI_NAME', 'Open WebUI')
        return await test_target(user.id, target_id, app_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
