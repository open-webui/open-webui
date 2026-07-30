import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from open_webui.internal.db import get_async_session
from open_webui.models.audit_logs import AuditLog
from open_webui.utils.auth import get_admin_user
from pydantic import BaseModel
from sqlalchemy import and_, exists, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

DEFAULT_RANGE_MS = 24 * 60 * 60 * 1000
STATUS_CLASSES = {'2xx', '4xx', '5xx', 'no_response'}
BODY_STATES = {'request', 'response', 'truncated'}
SORT_COLUMNS = {
    'created_at': AuditLog.created_at,
    'request_path': AuditLog.request_path,
    'response_status_code': AuditLog.response_status_code,
    'user_id': AuditLog.user_id,
}


class AuditUserResponse(BaseModel):
    id: str | None = None
    name: str | None = None
    email: str | None = None
    role: str | None = None


class AuditLogSummaryResponse(BaseModel):
    id: str
    created_at: int
    user: AuditUserResponse | None = None
    verb: str
    request_path: str
    response_status_code: int | None = None
    source_ip: str | None = None
    audit_level: str
    request_captured: bool
    response_captured: bool
    request_truncated: bool
    response_truncated: bool


class AuditLogListResponse(BaseModel):
    items: list[AuditLogSummaryResponse]
    total: int
    page: int
    limit: int


class AuditLogDetailResponse(AuditLogSummaryResponse):
    user_snapshot: dict[str, Any] | None = None
    request_uri: str
    user_agent: str | None = None
    request_object: str | None = None
    request_model: str | None = None
    request_extra: Any | None = None
    request_skill_ids: list[Any] | None = None
    request_tool_ids: list[Any] | None = None
    request_response_format: Any | None = None
    request_extra_body: Any | None = None
    request_system_messages: list[Any] | None = None
    request_user_messages: list[Any] | None = None
    response_object: str | None = None
    response_id: str | None = None
    response_model: str | None = None
    response_finish_reasons: list[Any] | None = None


class AuditLogFacetsResponse(BaseModel):
    endpoints: list[str]
    request_models: list[str]
    response_models: list[str]
    request_skill_ids: list[str]
    status_classes: list[str]


def _validation_error(parameter: str, message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=[{'loc': ['query', parameter], 'msg': message, 'type': 'value_error'}],
    )


def _resolve_time_range(start_at: int | None, end_at: int | None) -> tuple[int, int]:
    now = int(time.time() * 1000)
    resolved_start = start_at if start_at is not None else now - DEFAULT_RANGE_MS
    resolved_end = end_at if end_at is not None else now
    if resolved_start > resolved_end:
        _validation_error('start_at', 'start_at must be less than or equal to end_at')
    return resolved_start, resolved_end


def _parse_csv(value: str | None, parameter: str, allowed: set[str] | None = None) -> list[str]:
    if value is None:
        return []

    values = [item.strip() for item in value.split(',')]
    if not values or any(not item for item in values):
        _validation_error(parameter, f'Invalid {parameter} value')
    if allowed is not None:
        invalid_values = set(values) - allowed
        if invalid_values:
            _validation_error(parameter, f'Invalid {parameter} value')
    return list(dict.fromkeys(values))


def _user_from_snapshot(snapshot: Any) -> AuditUserResponse | None:
    if not isinstance(snapshot, dict):
        return None

    user = AuditUserResponse(
        id=snapshot.get('id'),
        name=snapshot.get('name'),
        email=snapshot.get('email'),
        role=snapshot.get('role'),
    )
    return user if any((user.id, user.name, user.email, user.role)) else None


def _summary(record: AuditLog) -> AuditLogSummaryResponse:
    return AuditLogSummaryResponse(
        id=record.id,
        created_at=record.created_at,
        user=_user_from_snapshot(record.user_snapshot),
        verb=record.verb,
        request_path=record.request_path,
        response_status_code=record.response_status_code,
        source_ip=record.source_ip,
        audit_level=record.audit_level,
        request_captured=record.request_object is not None,
        response_captured=record.response_object is not None,
        request_truncated=bool(record.request_truncated),
        response_truncated=bool(record.response_truncated),
    )


def _json_array_values(dialect_name: str):
    if dialect_name == 'sqlite':
        return func.json_each(AuditLog.request_skill_ids).table_valued('value').alias('skill')
    if dialect_name == 'postgresql':
        return func.json_array_elements_text(AuditLog.request_skill_ids).table_valued('value').alias('skill')
    raise HTTPException(status_code=500, detail='Unsupported database dialect for audit log queries')


async def _filter_conditions(
    db: AsyncSession,
    *,
    start_at: int,
    end_at: int,
    q: str | None = None,
    user_id: str | None = None,
    endpoint: str | None = None,
    request_model: str | None = None,
    response_model: str | None = None,
    request_skill_ids: list[str] | None = None,
    status_classes: list[str] | None = None,
    source_ip: str | None = None,
    body_state: list[str] | None = None,
) -> list[Any]:
    conditions: list[Any] = [AuditLog.created_at.between(start_at, end_at)]

    if q:
        search = f'%{q}%'
        conditions.append(
            or_(
                AuditLog.request_path.ilike(search),
                AuditLog.source_ip.ilike(search),
                AuditLog.id.ilike(search),
                AuditLog.user_snapshot['id'].as_string().ilike(search),
                AuditLog.user_snapshot['name'].as_string().ilike(search),
                AuditLog.user_snapshot['email'].as_string().ilike(search),
            )
        )
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if endpoint:
        conditions.append(AuditLog.request_path == endpoint)
    if request_model:
        conditions.append(AuditLog.request_model == request_model)
    if response_model:
        conditions.append(AuditLog.response_model == response_model)
    if source_ip:
        conditions.append(AuditLog.source_ip.startswith(source_ip, autoescape=True))
    if status_classes:
        status_conditions = []
        for status_class in status_classes:
            if status_class == 'no_response':
                status_conditions.append(AuditLog.response_status_code.is_(None))
            else:
                lower = int(status_class[0]) * 100
                status_conditions.append(AuditLog.response_status_code.between(lower, lower + 99))
        conditions.append(or_(*status_conditions))
    if body_state:
        body_conditions = []
        if 'request' in body_state:
            body_conditions.append(AuditLog.request_object.isnot(None))
        if 'response' in body_state:
            body_conditions.append(AuditLog.response_object.isnot(None))
        if 'truncated' in body_state:
            body_conditions.append(
                or_(AuditLog.request_truncated.is_(True), AuditLog.response_truncated.is_(True))
            )
        conditions.append(or_(*body_conditions))
    if request_skill_ids:
        connection = await db.connection()
        skill_values = _json_array_values(connection.dialect.name)
        conditions.append(
            exists(select(1).select_from(skill_values).where(skill_values.c.value.in_(request_skill_ids)))
        )

    return conditions


@router.get('/facets', response_model=AuditLogFacetsResponse)
async def get_audit_log_facets(
    start_at: int | None = None,
    end_at: int | None = None,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    resolved_start, resolved_end = _resolve_time_range(start_at, end_at)
    conditions = [AuditLog.created_at.between(resolved_start, resolved_end)]

    endpoints = list(
        (await db.scalars(
            select(AuditLog.request_path)
            .where(and_(*conditions), AuditLog.request_path.isnot(None))
            .distinct()
            .order_by(AuditLog.request_path)
        )).all()
    )
    request_models = list(
        (await db.scalars(
            select(AuditLog.request_model)
            .where(and_(*conditions), AuditLog.request_model.isnot(None))
            .distinct()
            .order_by(AuditLog.request_model)
        )).all()
    )
    response_models = list(
        (await db.scalars(
            select(AuditLog.response_model)
            .where(and_(*conditions), AuditLog.response_model.isnot(None))
            .distinct()
            .order_by(AuditLog.response_model)
        )).all()
    )

    connection = await db.connection()
    skill_values = _json_array_values(connection.dialect.name)
    request_skill_ids = list(
        (await db.scalars(
            select(skill_values.c.value)
            .select_from(AuditLog)
            .join(skill_values, true())
            .where(and_(*conditions))
            .distinct()
            .order_by(skill_values.c.value)
        )).all()
    )

    return AuditLogFacetsResponse(
        endpoints=endpoints,
        request_models=request_models,
        response_models=response_models,
        request_skill_ids=request_skill_ids,
        status_classes=['2xx', '4xx', '5xx', 'no_response'],
    )


@router.get('', response_model=AuditLogListResponse)
async def get_audit_logs(
    start_at: int | None = None,
    end_at: int | None = None,
    q: str | None = None,
    user_id: str | None = None,
    endpoint: str | None = None,
    request_model: str | None = None,
    response_model: str | None = None,
    request_skill_ids: str | None = None,
    status_classes: str | None = None,
    source_ip: str | None = None,
    body_state: str | None = None,
    order_by: Literal['created_at', 'request_path', 'response_status_code', 'user_id'] = 'created_at',
    direction: Literal['asc', 'desc'] = 'desc',
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    resolved_start, resolved_end = _resolve_time_range(start_at, end_at)
    skill_ids = _parse_csv(request_skill_ids, 'request_skill_ids')
    selected_status_classes = _parse_csv(status_classes, 'status_classes', STATUS_CLASSES)
    selected_body_states = _parse_csv(body_state, 'body_state', BODY_STATES)
    conditions = await _filter_conditions(
        db,
        start_at=resolved_start,
        end_at=resolved_end,
        q=q,
        user_id=user_id,
        endpoint=endpoint,
        request_model=request_model,
        response_model=response_model,
        request_skill_ids=skill_ids,
        status_classes=selected_status_classes,
        source_ip=source_ip,
        body_state=selected_body_states,
    )

    total = await db.scalar(select(func.count()).select_from(AuditLog).where(and_(*conditions)))
    sort_column = SORT_COLUMNS[order_by]
    order = sort_column.asc() if direction == 'asc' else sort_column.desc()
    id_order = AuditLog.id.asc() if direction == 'asc' else AuditLog.id.desc()
    records = (
        await db.scalars(
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(order, id_order)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()

    return AuditLogListResponse(
        items=[_summary(record) for record in records],
        total=total or 0,
        page=page,
        limit=limit,
    )


@router.get('/{id}', response_model=AuditLogDetailResponse)
async def get_audit_log_by_id(
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    record = await db.get(AuditLog, id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Audit log entry not found')

    return AuditLogDetailResponse(
        **_summary(record).model_dump(),
        user_snapshot=record.user_snapshot if isinstance(record.user_snapshot, dict) else None,
        request_uri=record.request_uri,
        user_agent=record.user_agent,
        request_object=record.request_object,
        request_model=record.request_model,
        request_extra=record.request_extra,
        request_skill_ids=record.request_skill_ids if isinstance(record.request_skill_ids, list) else None,
        request_tool_ids=record.request_tool_ids if isinstance(record.request_tool_ids, list) else None,
        request_response_format=record.request_response_format,
        request_extra_body=record.request_extra_body,
        request_system_messages=(
            record.request_system_messages if isinstance(record.request_system_messages, list) else None
        ),
        request_user_messages=(record.request_user_messages if isinstance(record.request_user_messages, list) else None),
        response_object=record.response_object,
        response_id=record.response_id,
        response_model=record.response_model,
        response_finish_reasons=(
            record.response_finish_reasons if isinstance(record.response_finish_reasons, list) else None
        ),
    )
