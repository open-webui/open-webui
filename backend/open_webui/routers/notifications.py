from __future__ import annotations

from typing import Any
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import get_async_session
from open_webui.models.notifications import Notification, emit_changes
from open_webui.utils.inbox import hydrate, visible_clause
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

log = logging.getLogger(__name__)


async def _check_notifications_enabled():
    if not await Config.get('notifications.enable'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)


async def inbox_page(user, cursor=None, limit=20, clause=None, *, db):
    started = time.monotonic()
    if clause is None:
        clause = await visible_clause(user, db=db)
    query = select(Notification).where(clause)
    if cursor:
        try:
            timestamp, id = cursor.split(':', 1)
            timestamp = int(timestamp)
            UUID(id)
            if not 0 <= timestamp <= 2**63 - 1:
                raise ValueError()
        except (ValueError, TypeError):
            raise HTTPException(422, 'Invalid inbox cursor')
        query = query.where(
            or_(Notification.created_at < timestamp, and_(Notification.created_at == timestamp, Notification.id < id))
        )
    rows = (
        await db.scalars(query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit + 1))
    ).all()
    more = len(rows) > limit
    rows = rows[:limit]
    result = {
        'items': await hydrate(rows, db=db),
        'next_cursor': f'{rows[-1].created_at}:{rows[-1].id}' if more else None,
    }
    log.debug('Inbox page loaded in %.3fs', time.monotonic() - started)
    return result


@router.get('/inbox')
async def get_inbox(
    cursor: str | None = Query(None, max_length=100),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _check_notifications_enabled()
    return await inbox_page(user, cursor, limit, db=db)


@router.get('/inbox/count')
async def get_inbox_count(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    await _check_notifications_enabled()
    started = time.monotonic()
    clause = await visible_clause(user, db=db)
    count = await db.scalar(
        select(func.count()).select_from(Notification).where(clause, Notification.seen_at.is_(None))
    )
    log.debug('Inbox count loaded in %.3fs', time.monotonic() - started)
    return {'count': count}


@router.post('/inbox/open')
async def open_inbox(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    await _check_notifications_enabled()
    clause = await visible_clause(user, db=db)
    now = time.time_ns()
    # A single UPDATE acknowledges only rows visible to this statement. A late
    # commit with an older created_at must remain unseen (no timestamp watermark).
    result = await db.execute(
        update(Notification)
        .where(clause, Notification.seen_at.is_(None))
        .values(seen_at=now, updated_at=now)
        .returning(Notification.id)
        .execution_options(synchronize_session=False)
    )
    # SQLite reports rowcount=-1 for UPDATEs containing the recursive folder CTE.
    acknowledged = len(result.scalars().all())
    await db.commit()
    await emit_changes({user.id})
    page = await inbox_page(user, clause=clause, db=db)
    for item in page['items']:
        item['is_new'] = item['seen_at'] == str(now) or item['seen_at'] is None
    page.update(
        acknowledged_count=acknowledged,
        acknowledged_at=str(now),
        count=await db.scalar(
            select(func.count()).select_from(Notification).where(clause, Notification.seen_at.is_(None))
        ),
    )
    return page


@router.patch('/inbox/{id}')
async def read_inbox_item(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    await _check_notifications_enabled()
    clause = await visible_clause(user, db=db)
    now = time.time_ns()
    row = await db.scalar(
        update(Notification)
        .where(clause, Notification.id == id)
        .values(
            seen_at=func.coalesce(Notification.seen_at, now),
            read_at=func.coalesce(Notification.read_at, now),
            updated_at=now,
        )
        .returning(Notification)
        .execution_options(populate_existing=True)
    )
    if not row:
        raise HTTPException(404, 'Notification not found')
    response = (await hydrate([row], db=db))[0]
    await db.commit()
    await emit_changes({user.id})
    return response


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
        # LICENSE covers this Open WebUI notification identifier.
        # Do not alter, remove, obscure, or replace it except as LICENSE permits:
        # https://docs.openwebui.com/license.
        app_name = getattr(request.app.state, 'WEBUI_NAME', 'Open WebUI')
        return await test_target(user.id, target_id, app_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
