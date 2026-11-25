import logging
import secrets
import time
from typing import Literal, Optional
from uuid import uuid4

from open_webui.models.notifications import emit_changes
from open_webui.models.access_grants import AccessGrant, AccessGrantResponse, AccessGrants
from open_webui.models.users import UserResponse
from open_webui.internal.db import Base, get_async_db_context
from open_webui.utils.misc import json_text_variants
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import JSON, BigInteger, Boolean, Column, Index, String, Text, cast, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


# Automation DB Schema


class Automation(Base):
    __tablename__ = 'automation'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    folder_id = Column(Text, nullable=True)
    name = Column(Text, nullable=False)
    data = Column(JSON, nullable=False)  # {prompt, model_id, rrule}
    meta = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_run_at = Column(BigInteger, nullable=True)
    next_run_at = Column(BigInteger, nullable=True)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('ix_automation_next_run', 'next_run_at'),
        Index('ix_automation_user_folder', 'user_id', 'folder_id'),
    )


class AutomationRun(Base):
    __tablename__ = 'automation_run'

    id = Column(Text, primary_key=True)
    automation_id = Column(Text, nullable=False)
    chat_id = Column(Text, nullable=True)
    status = Column(Text, nullable=False)  # success | error
    error = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('ix_automation_run_automation_id', 'automation_id'),
        Index('ix_automation_run_aid_created', 'automation_id', 'created_at'),
    )


# Pydantic Models


class AutomationMachineConfig(BaseModel):
    server_id: str
    cwd: Optional[str] = None


class AutomationTarget(BaseModel):
    type: Literal['chat', 'channel'] = 'chat'
    channel_id: Optional[str] = None
    # Off: every run continues one chat (or channel thread). The first run creates it and saves its id here.
    new_chat: bool = True
    chat_id: Optional[str] = None
    new_thread: bool = True
    thread_id: Optional[str] = None
    # False: the reply posts in the channel instead of under the run's message. Unset replies in a thread, as does an ongoing thread.
    reply_in_thread: Optional[bool] = None


def keep_target_refs(target: Optional[dict], previous: Optional[dict]) -> Optional[dict]:
    """The ongoing chat or thread is the runner's, not the form's: keep it while the target still continues there."""
    if not target:
        return target
    previous = previous or {}
    target = {**target, 'chat_id': None, 'thread_id': None}
    if target.get('type', 'chat') == 'chat':
        if not target.get('new_chat', True) and previous.get('type', 'chat') == 'chat':
            target['chat_id'] = previous.get('chat_id')
    elif (
        not target.get('new_thread', True)
        and previous.get('type') == 'channel'
        and previous.get('channel_id') == target.get('channel_id')
    ):
        target['thread_id'] = previous.get('thread_id')
    return target


class AutomationWebhook(BaseModel):
    token: Optional[str] = None  # server-owned
    allow_get: bool = False


def has_webhook(data: Optional[dict]) -> bool:
    return bool((data or {}).get('webhook'))


def hide_webhook_token(data: dict) -> dict:
    if not (data.get('webhook') or {}).get('token'):
        return data
    return {**data, 'webhook': {**data['webhook'], 'token': None}}


def new_webhook_token() -> str:
    return secrets.token_urlsafe(32)


def keep_webhook_token(webhook: Optional[dict], previous: Optional[dict]) -> Optional[dict]:
    if not webhook:
        return None
    return {**webhook, 'token': (previous or {}).get('token') or new_webhook_token()}


class AutomationData(BaseModel):
    prompt: str
    model_id: str
    rrule: str = ''  # empty: no schedule
    machine: Optional[AutomationMachineConfig] = None
    target: Optional[AutomationTarget] = None
    webhook: Optional[AutomationWebhook] = None

    @model_validator(mode='before')
    @classmethod
    def _former_machine_key(cls, data):
        # Automations saved before Terminals became Machines keep their settings under `terminal`.
        if isinstance(data, dict) and 'terminal' in data:
            data = {**data}
            legacy = data.pop('terminal')
            if not data.get('machine'):
                data['machine'] = legacy
        return data


class AutomationModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    folder_id: Optional[str] = None
    name: str
    data: dict
    meta: Optional[dict] = None
    is_active: bool
    last_run_at: Optional[int] = None
    next_run_at: Optional[int] = None

    created_at: int
    updated_at: int


class AutomationRunModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    automation_id: str
    chat_id: Optional[str] = None
    status: str
    error: Optional[str] = None
    created_at: int


class AutomationForm(BaseModel):
    name: str
    folder_id: Optional[str] = None
    data: AutomationData
    meta: Optional[dict] = None
    is_active: Optional[bool] = True


class AutomationResponse(AutomationModel):
    last_run: Optional[AutomationRunModel] = None
    next_runs: Optional[list[int]] = None
    user: Optional[UserResponse] = None  # the owner, shown like on workspace items
    # Rename, reschedule, pause and run. What a run does stays the owner's: it runs as them.
    write_access: Optional[bool] = None
    access_grants: Optional[list[AccessGrantResponse]] = None  # for the owner or an admin


class AutomationListResponse(BaseModel):
    items: list[AutomationModel]
    total: int


# Automation Table


class AutomationTable:
    async def insert(
        self,
        user_id: str,
        form: AutomationForm,
        next_run_at: int,
        db: Optional[AsyncSession] = None,
    ) -> AutomationModel:
        async with get_async_db_context(db) as db:
            now = int(time.time_ns())
            data = form.data.model_dump()
            data['webhook'] = keep_webhook_token(data.get('webhook'), None)
            row = Automation(
                id=str(uuid4()),
                user_id=user_id,
                folder_id=form.folder_id,
                name=form.name,
                data=data,
                meta=form.meta,
                is_active=form.is_active,
                next_run_at=next_run_at,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            return AutomationModel.model_validate(row)

    async def count_by_user(self, user_id: str, db: Optional[AsyncSession] = None) -> int:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(func.count()).select_from(Automation).filter_by(user_id=user_id))
            return result.scalar()

    async def get_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[AutomationModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Automation, id)
            return AutomationModel.model_validate(row) if row else None

    async def get_by_folder(self, folder_id: str, db: Optional[AsyncSession] = None) -> list[AutomationModel]:
        """Every automation that lives in a folder, whoever created it."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Automation).filter_by(folder_id=folder_id).order_by(Automation.created_at.asc())
            )
            return [AutomationModel.model_validate(r) for r in result.scalars().all()]

    async def get_active_by_user(self, user_id: str, db: Optional[AsyncSession] = None) -> list[AutomationModel]:
        """Get active automations for a user (for calendar RRULE expansion)."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Automation).filter_by(user_id=user_id, is_active=True).order_by(Automation.created_at.desc())
            )
            return [AutomationModel.model_validate(r) for r in result.scalars().all()]

    async def search_automations(
        self,
        user_id: str,
        query: Optional[str] = None,
        status: Optional[str] = None,
        folder_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 30,
        view: Literal['all', 'mine', 'shared'] = 'mine',
        group_ids: Optional[list[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> 'AutomationListResponse':
        async with get_async_db_context(db) as db:
            if view == 'mine':
                stmt = select(Automation).filter_by(user_id=user_id)
            else:
                # Owned plus shared directly; folder-shared ones are listed in their folder.
                stmt = AccessGrants.has_permission_filter(
                    select(Automation),
                    Automation,
                    {'user_id': user_id, 'group_ids': group_ids or []},
                    'automation',
                    'read',
                    db=db,
                )
                if view == 'shared':
                    stmt = stmt.filter(Automation.user_id != user_id)

            if folder_id:
                stmt = stmt.filter(Automation.folder_id == folder_id)

            if query:
                # Search the name column and the prompt inside the JSON data.
                data_text = cast(Automation.data, String)
                stmt = stmt.filter(
                    or_(
                        Automation.name.ilike(f'%{query}%'),
                        *(data_text.icontains(variant, autoescape=True) for variant in json_text_variants(query)),
                    )
                )

            if status == 'active':
                stmt = stmt.filter(Automation.is_active == True)
            elif status == 'paused':
                stmt = stmt.filter(Automation.is_active == False)

            stmt = stmt.order_by(Automation.created_at.desc())

            # Get total count
            count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            rows = result.scalars().all()
            return AutomationListResponse(
                items=[AutomationModel.model_validate(r) for r in rows],
                total=total,
            )

    async def update_by_id(
        self,
        id: str,
        form: AutomationForm,
        next_run_at: int,
        db: Optional[AsyncSession] = None,
    ) -> Optional[AutomationModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Automation, id)
            if not row:
                return None
            row.name = form.name
            row.folder_id = form.folder_id
            data = form.data.model_dump()
            data['target'] = keep_target_refs(data.get('target'), (row.data or {}).get('target'))
            data['webhook'] = keep_webhook_token(data.get('webhook'), (row.data or {}).get('webhook'))
            row.data = data
            row.meta = form.meta
            if form.is_active is not None:
                row.is_active = form.is_active
            row.next_run_at = next_run_at
            row.updated_at = int(time.time_ns())
            await db.commit()
            return AutomationModel.model_validate(row)

    async def set_target_ref(self, id: str, key: Literal['chat_id', 'thread_id'], value: Optional[str]) -> None:
        """Save the ongoing chat or thread a run created, without counting as an edit."""
        async with get_async_db_context() as db:
            row = await db.get(Automation, id, with_for_update=True)
            if not row:
                return
            data = dict(row.data or {})
            data['target'] = {**(data.get('target') or {'type': 'chat'}), key: value}
            row.data = data
            await db.commit()

    async def regenerate_webhook_token(self, id: str, db: Optional[AsyncSession] = None) -> Optional[AutomationModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Automation, id, with_for_update=True)
            if not row or not has_webhook(row.data):
                return None
            data = dict(row.data or {})
            data['webhook'] = {**data['webhook'], 'token': new_webhook_token()}
            row.data = data
            row.updated_at = int(time.time_ns())
            await db.commit()
            return AutomationModel.model_validate(row)

    async def update_last_run_at(self, id: str, db: Optional[AsyncSession] = None) -> Optional[AutomationModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Automation, id)
            if not row:
                return None
            row.last_run_at = int(time.time_ns())
            await db.commit()
            return AutomationModel.model_validate(row)

    async def clear_folder_ids(
        self,
        user_id: str,
        folder_ids: list[str],
        db: Optional[AsyncSession] = None,
    ) -> int:
        if not folder_ids:
            return 0
        async with get_async_db_context(db) as db:
            result = await db.execute(
                update(Automation)
                .where(Automation.user_id == user_id, Automation.folder_id.in_(folder_ids))
                .values(folder_id=None, updated_at=int(time.time_ns()))
            )
            await db.commit()
            return result.rowcount or 0

    async def toggle(
        self,
        id: str,
        next_run_at: Optional[int],
        db: Optional[AsyncSession] = None,
    ) -> Optional[AutomationModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Automation, id)
            if not row:
                return None
            row.is_active = not row.is_active
            row.next_run_at = next_run_at if row.is_active else None
            row.updated_at = int(time.time_ns())
            await db.commit()
            return AutomationModel.model_validate(row)

    async def delete(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            row = await db.get(Automation, id)
            if not row:
                return False
            from open_webui.models.notifications import delete_notifications

            recipients = await delete_notifications(resource_type='automation', resource_ids=[id], db=db)
            await db.execute(delete(AccessGrant).filter_by(resource_type='automation', resource_id=id))
            await db.delete(row)
            await db.commit()
            await emit_changes(recipients)
            return True

    async def claim_due(self, now_ns: int, limit: int = 10, db: Optional[AsyncSession] = None) -> list[AutomationModel]:
        """
        Atomically claim due automations for execution.

        Advances next_run_at immediately so the row can never be
        double-claimed. On PostgreSQL, uses FOR UPDATE SKIP LOCKED
        for zero-contention distributed work claiming.
        """
        async with get_async_db_context(db) as db:
            stmt = (
                select(Automation)
                .where(
                    Automation.is_active == True,
                    Automation.next_run_at <= now_ns,
                )
                .order_by(Automation.next_run_at)
                .limit(limit)
            )

            if db.bind.dialect.name == 'postgresql':
                stmt = stmt.with_for_update(skip_locked=True)

            result = await db.execute(stmt)
            rows = result.scalars().all()

            from open_webui.utils.automations import next_run_ns
            from open_webui.utils.recurrence import RecurrenceEvaluationTimeout

            # Batch-fetch user timezones so rescheduling respects each
            # user's local timezone instead of falling back to server time.
            user_ids = list({row.user_id for row in rows})
            timezone_by_user_id: dict[str, Optional[str]] = {}
            if user_ids:
                from open_webui.models.users import User

                tz_result = await db.execute(select(User.id, User.timezone).where(User.id.in_(user_ids)))
                timezone_by_user_id = {uid: tz for uid, tz in tz_result.all()}

            claimed = []
            for row in rows:
                try:
                    next_run_at = await next_run_ns(row.data.get('rrule', ''), tz=timezone_by_user_id.get(row.user_id))
                except RecurrenceEvaluationTimeout:
                    log.warning('Skipping automation %s: recurrence evaluation timed out', row.id)
                    continue
                row.last_run_at = now_ns
                row.next_run_at = next_run_at
                claimed.append(row)

            await db.commit()

            return [AutomationModel.model_validate(r) for r in claimed]


# Automation Run Table


class AutomationRunTable:
    async def insert(
        self,
        automation_id: str,
        status: str,
        chat_id: Optional[str] = None,
        error: Optional[str] = None,
        *,
        request=None,
        event_actor=None,
        db: Optional[AsyncSession] = None,
    ) -> AutomationRunModel:
        async with get_async_db_context(db) as db:
            row = AutomationRun(
                id=str(uuid4()),
                automation_id=automation_id,
                chat_id=chat_id,
                status=status,
                error=error,
                created_at=int(time.time_ns()),
            )
            db.add(row)
            await db.flush()
            event = None
            recipients = set()
            if status == 'error':
                from open_webui.events import EVENTS, build_event, publish_event
                from open_webui.utils.inbox import consume_event
                from open_webui.models.notifications import emit_changes

                automation = await db.get(Automation, automation_id)
                if automation:
                    event = build_event(
                        request,
                        EVENTS.AUTOMATION_RUN_FAILED,
                        actor=event_actor,
                        subject_id=automation_id,
                        event_id=f'automation-run:{row.id}',
                        data={
                            'run_id': row.id,
                            'name': automation.name,
                            'error': error,
                            'user_id': automation.user_id,
                            'message': f'{automation.name}: {error}',
                            **({'chat_id': chat_id} if chat_id else {}),
                        },
                    )
                    recipients = await consume_event(event, db=db)
            await db.commit()
            if event is not None:
                await emit_changes(recipients)
                if request is not None:
                    await publish_event(request, event)
            return AutomationRunModel.model_validate(row)

    async def get_latest(self, automation_id: str, db: Optional[AsyncSession] = None) -> Optional[AutomationRunModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(AutomationRun)
                .filter_by(automation_id=automation_id)
                .order_by(AutomationRun.created_at.desc())
                .limit(1)
            )
            row = result.scalars().first()
            return AutomationRunModel.model_validate(row) if row else None

    async def get_latest_batch(
        self, automation_ids: list[str], db: Optional[AsyncSession] = None
    ) -> dict[str, AutomationRunModel]:
        """Fetch the latest run for each automation in a single query."""
        if not automation_ids:
            return {}
        async with get_async_db_context(db) as db:
            # Subquery: max created_at per automation_id
            subq = (
                select(
                    AutomationRun.automation_id,
                    func.max(AutomationRun.created_at).label('max_created'),
                )
                .filter(AutomationRun.automation_id.in_(automation_ids))
                .group_by(AutomationRun.automation_id)
                .subquery()
            )
            result = await db.execute(
                select(AutomationRun).join(
                    subq,
                    (AutomationRun.automation_id == subq.c.automation_id)
                    & (AutomationRun.created_at == subq.c.max_created),
                )
            )
            rows = result.scalars().all()
            return {row.automation_id: AutomationRunModel.model_validate(row) for row in rows}

    async def get_by_automation(
        self,
        automation_id: str,
        skip: int = 0,
        limit: int = 50,
        direction: str = 'desc',
        db: Optional[AsyncSession] = None,
    ) -> list[AutomationRunModel]:
        order = AutomationRun.created_at.asc() if direction == 'asc' else AutomationRun.created_at.desc()
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(AutomationRun).filter_by(automation_id=automation_id).order_by(order).offset(skip).limit(limit)
            )
            rows = result.scalars().all()
            return [AutomationRunModel.model_validate(r) for r in rows]

    async def delete_by_automation(self, automation_id: str, db: Optional[AsyncSession] = None) -> int:
        async with get_async_db_context(db) as db:
            from open_webui.models.notifications import delete_notifications

            recipients = await delete_notifications(
                object_type='automation_run',
                object_ids=select(AutomationRun.id).where(AutomationRun.automation_id == automation_id),
                db=db,
            )
            result = await db.execute(delete(AutomationRun).filter_by(automation_id=automation_id))
            await db.commit()
            await emit_changes(recipients)
            return result.rowcount

    async def get_runs_by_user_range(
        self,
        user_id: str,
        start_ns: int,
        end_ns: int,
        limit: int = 500,
        db: Optional[AsyncSession] = None,
    ) -> list[tuple['AutomationRunModel', 'AutomationModel']]:
        """Get runs within a date range for a user, joined with parent automation."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(AutomationRun, Automation)
                .join(Automation, Automation.id == AutomationRun.automation_id)
                .filter(
                    Automation.user_id == user_id,
                    AutomationRun.created_at >= start_ns,
                    AutomationRun.created_at < end_ns,
                )
                .order_by(AutomationRun.created_at.desc())
                .limit(limit)
            )
            return [
                (AutomationRunModel.model_validate(run), AutomationModel.model_validate(auto))
                for run, auto in result.all()
            ]


Automations = AutomationTable()
AutomationRuns = AutomationRunTable()
