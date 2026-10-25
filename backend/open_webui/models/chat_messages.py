import os
import time
import uuid
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from open_webui.internal.db import Base, get_async_db_context
from open_webui.utils.response import normalize_usage
from open_webui.utils.session_records import normalize_tool_output, recorded_timestamp
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    case,
    cast,
    delete,
    distinct,
    func,
    literal,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

####################
# Helpers
####################


def _normalize_timestamp(timestamp: Optional[int]) -> float:
    """Normalize and validate timestamp. Returns current time if invalid."""
    now = time.time()
    if timestamp is None:
        return now

    # Convert milliseconds to seconds if needed
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000

    # Validate: must be after 2020 and not in the future (with 1 day tolerance)
    min_valid = 1577836800  # 2020-01-01 00:00:00 UTC
    max_valid = now + 86400  # 1 day in the future (clock skew tolerance)

    if timestamp < min_valid or timestamp > max_valid:
        return now

    return timestamp


def _timezone(tz: Optional[str]) -> ZoneInfo:
    try:
        return ZoneInfo(tz or 'UTC')
    except ZoneInfoNotFoundError:
        return ZoneInfo('UTC')


def _date_key(timestamp: int, tz: ZoneInfo) -> str:
    return datetime.fromtimestamp(_normalize_timestamp(timestamp), tz=tz).strftime('%Y-%m-%d')


def get_usage(data: dict) -> Optional[dict]:
    """Extract and normalize usage from message data."""
    usage = data.get('usage') or (data.get('info') or {}).get('usage')
    return normalize_usage(usage) if usage else None


def _token_columns(dialect: str):
    """Return (input_tokens, output_tokens) SQL column expressions.

    Falls back to OpenAI-style keys (prompt_tokens / completion_tokens)
    when the normalized keys are absent.
    """
    if dialect == 'sqlite':
        extract = lambda key: cast(func.json_extract(ChatMessage.usage, f'$.{key}'), Integer)
    elif dialect == 'postgresql':
        extract = lambda key: cast(func.json_extract_path_text(ChatMessage.usage, key), Integer)
    else:
        raise NotImplementedError(f'Unsupported dialect: {dialect}')

    return (
        func.coalesce(extract('input_tokens'), extract('prompt_tokens')),
        func.coalesce(extract('output_tokens'), extract('completion_tokens')),
    )


def _daily_usage_bucket(dialect: str, bucket_offset: int):
    """Match Python's server-local day and legacy timestamp normalization in SQL."""
    if dialect not in {'sqlite', 'postgresql'}:
        return None
    if dialect == 'postgresql':
        # The database server/session can use a different timezone from the application.
        zone = os.environ.get('TZ')
        if zone is None:
            localtime = str(Path('/etc/localtime').resolve())
            if '/zoneinfo/' in localtime:
                zone = localtime.split('/zoneinfo/', 1)[1]
            elif time.timezone == 0 and not time.daylight:
                zone = 'UTC'
        try:
            ZoneInfo(zone or '')
        except (ValueError, ZoneInfoNotFoundError):
            # Retain Python bucketing when the OS timezone has no portable IANA name.
            return None

    now = time.time()
    seconds = case(
        (ChatMessage.created_at > 10_000_000_000, cast(ChatMessage.created_at, Float) / 1000),
        else_=ChatMessage.created_at,
    )
    timestamp = case((seconds.between(1577836800, now + 86400), seconds), else_=now) + bucket_offset
    if dialect == 'sqlite':
        return func.strftime('%Y-%m-%d', timestamp, 'unixepoch', 'localtime')
    return func.to_char(func.timezone(zone, func.to_timestamp(timestamp)), 'YYYY-MM-DD')


def _extract_tool_names(value: Any) -> list[str]:
    names: list[str] = []

    def add(name: Any):
        if isinstance(name, str):
            cleaned = name.strip()
            if cleaned and len(cleaned) <= 128:
                names.append(cleaned)

    def walk(item: Any):
        if isinstance(item, list):
            for child in item:
                walk(child)
            return

        if not isinstance(item, dict):
            return

        item_type = str(item.get('type') or '')
        looks_like_tool = 'tool' in item_type or item_type in {'function_call', 'function_call_output'}
        if looks_like_tool:
            add(item.get('name') or item.get('tool_name'))
            function = item.get('function')
            if isinstance(function, dict):
                add(function.get('name'))

        for key in ('tool_calls', 'tools', 'output', 'meta'):
            if key in item:
                walk(item.get(key))

    walk(value)
    return names


####################
# ChatMessage DB Schema
####################


class ChatMessage(Base):
    __tablename__ = 'chat_message'

    # Identity
    id = Column(Text, primary_key=True)
    chat_id = Column(Text, ForeignKey('chat.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Text, index=True)

    # Structure
    role = Column(Text, nullable=False)  # user, assistant, system
    parent_id = Column(Text, nullable=True)

    # Content
    content = Column(JSON, nullable=True)  # Can be str or list of blocks
    output = Column(JSON, nullable=True)

    # Model (for assistant messages)
    model_id = Column(Text, nullable=True, index=True)

    # Attachments
    files = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    embeds = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    # Status
    done = Column(Boolean, default=True)
    status_history = Column(JSON, nullable=True)
    error = Column(JSON, nullable=True)

    # Usage (tokens, timing, etc.)
    usage = Column(JSON, nullable=True)

    # Context compaction checkpoint
    context_summary = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)

    __table_args__ = (
        Index('chat_message_chat_parent_idx', 'chat_id', 'parent_id'),
        Index('chat_message_model_created_idx', 'model_id', 'created_at'),
        Index('chat_message_user_created_idx', 'user_id', 'created_at'),
        Index('chat_message_chat_role_done_idx', 'chat_id', 'role', 'done'),  # unfinished-assistant probe
    )


####################
# Pydantic Models
####################


class ChatMessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    user_id: str
    role: str
    parent_id: Optional[str] = None
    content: Optional[Any] = None  # str or list of blocks
    output: Optional[list] = None
    model_id: Optional[str] = None
    files: Optional[list] = None
    sources: Optional[list] = None
    embeds: Optional[list] = None
    meta: Optional[dict] = None
    done: bool = True
    status_history: Optional[list] = None
    error: Optional[dict | str] = None
    usage: Optional[dict] = None
    context_summary: Optional[str] = None
    created_at: int
    updated_at: int


####################
# Table Operations
####################


class ChatMessageTable:
    @staticmethod
    def _apply_message_data(message: ChatMessage, data: dict, now: int) -> None:
        """Overwrite only the fields the payload carries."""
        if 'role' in data:
            message.role = data['role']
        if 'parent_id' in data or 'parentId' in data:
            message.parent_id = data.get('parent_id') or data.get('parentId')
        if 'content' in data:
            message.content = data.get('content')
        if 'output' in data:
            message.output = normalize_tool_output(data.get('output'))
        if 'model_id' in data or 'model' in data:
            message.model_id = data.get('model_id') or data.get('model')
        if 'files' in data:
            message.files = data.get('files')
        if 'sources' in data:
            message.sources = data.get('sources')
        if 'embeds' in data:
            message.embeds = data.get('embeds')
        if 'meta' in data:
            message.meta = data.get('meta')
        if 'done' in data:
            message.done = data['done']
        if 'status_history' in data or 'statusHistory' in data:
            message.status_history = data.get('status_history') or data.get('statusHistory')
        if 'error' in data:
            message.error = data.get('error')
        if 'context_summary' in data or 'contextSummary' in data:
            message.context_summary = data.get('context_summary') or data.get('contextSummary')

        usage = get_usage(data)
        if usage:
            # The caller saves a cumulative message snapshot; accumulation belongs to the model-call loop.
            message.usage = usage
        message.updated_at = now

    @staticmethod
    def _build_message(composite_id: str, chat_id: str, user_id: str, data: dict, now: int) -> ChatMessage:
        return ChatMessage(
            id=composite_id,
            chat_id=chat_id,
            user_id=user_id,
            role=data.get('role', 'user'),
            parent_id=data.get('parent_id') or data.get('parentId'),
            content=data.get('content'),
            output=normalize_tool_output(data.get('output')),
            model_id=data.get('model_id') or data.get('model'),
            files=data.get('files'),
            sources=data.get('sources'),
            embeds=data.get('embeds'),
            meta=data.get('meta'),
            done=data.get('done', True),
            status_history=data.get('status_history') or data.get('statusHistory'),
            error=data.get('error'),
            usage=get_usage(data),
            context_summary=data.get('context_summary') or data.get('contextSummary'),
            created_at=(recorded_timestamp(data.get('timestamp')) or 0) if 'timestamp' in data else now,
            updated_at=now,
        )

    async def upsert_message(
        self,
        message_id: str,
        chat_id: str,
        user_id: str,
        data: dict,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ChatMessageModel]:
        """Insert or update a chat message."""
        async with nullcontext(db) if db is not None else get_async_db_context() as session:
            now = int(time.time())
            # Use composite ID: {chat_id}-{message_id}
            composite_id = f'{chat_id}-{message_id}'

            message = await session.get(ChatMessage, composite_id)
            if message:
                self._apply_message_data(message, data, now)
            else:
                message = self._build_message(composite_id, chat_id, user_id, data, now)
                session.add(message)

            if db is None:
                await session.commit()
            else:
                await session.flush()
            return ChatMessageModel.model_validate(message)

    async def upsert_messages(
        self, chat_id: str, user_id: str, messages: dict[str, dict], db: AsyncSession | None = None
    ) -> None:
        """Backfill missing rows without overwriting newer message data."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        if not messages:
            return
        async with get_async_db_context(db) as db:
            insert = sqlite_insert if db.bind.dialect.name == 'sqlite' else pg_insert
            rows = [
                self._build_message(
                    f'{chat_id}-{mid}',
                    chat_id,
                    data.get('user_id') or user_id,
                    {**data, 'timestamp': data.get('timestamp')},
                    int(time.time()),
                )
                for mid, data in messages.items()
            ]
            await db.execute(
                insert(ChatMessage).on_conflict_do_nothing(index_elements=['id']),
                [{column.name: getattr(row, column.name) for column in ChatMessage.__table__.columns} for row in rows],
            )
            await db.commit()

    async def get_message_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[ChatMessageModel]:
        async with get_async_db_context(db) as db:
            message = await db.get(ChatMessage, id)
            return ChatMessageModel.model_validate(message) if message else None

    async def has_unfinished_assistant_by_chat_id(
        self,
        chat_id: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ChatMessage.id)
                .where(ChatMessage.chat_id == chat_id)
                .where(ChatMessage.role == 'assistant')
                .where(ChatMessage.done.is_(False))
                .limit(1)
            )
            return result.scalar_one_or_none() is not None

    async def get_messages_by_chat_id(self, chat_id: str, db: Optional[AsyncSession] = None) -> list[ChatMessageModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ChatMessage).filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.asc())
            )
            messages = result.scalars().all()
            return [ChatMessageModel.model_validate(message) for message in messages]

    # DB column names that differ from the JSON message keys.
    DB_TO_JSON_KEY_MAP = {
        'parent_id': 'parentId',
        'model_id': 'model',
        'status_history': 'statusHistory',
        'context_summary': 'contextSummary',
        'created_at': 'timestamp',
    }
    # DB-internal columns excluded from the reconstructed message dict.
    EXCLUDED_COLUMNS = frozenset({'id', 'chat_id', 'updated_at'})

    async def get_messages_map_by_chat_id(self, chat_id: str, db: Optional[AsyncSession] = None) -> Optional[dict]:
        """Build a {message_id: message_dict} map from chat_message rows.

        Returns the same shape as chat.history.messages so callers
        (get_message_list, middleware) work unchanged.  Returns None if
        no rows exist for the chat (caller should fall back to the
        embedded JSON blob for legacy chats).
        """
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ChatMessage).filter_by(chat_id=chat_id))
            rows = result.scalars().all()

        if not rows:
            return None

        # Strip the composite-id prefix ("{chat_id}-") to recover the
        # original message_id used as map key.
        prefix = f'{chat_id}-'
        prefix_len = len(prefix)
        col_keys = [c.key for c in ChatMessage.__table__.columns]

        messages_map: dict[str, dict] = {}
        for row in rows:
            msg_id = row.id[prefix_len:] if row.id.startswith(prefix) else row.id

            msg: dict = {'id': msg_id}
            for key in col_keys:
                if key in self.EXCLUDED_COLUMNS:
                    continue
                val = getattr(row, key)
                if val is None:
                    continue
                json_key = self.DB_TO_JSON_KEY_MAP.get(key, key)
                msg[json_key] = val

            # Ensure content always has a value
            msg.setdefault('content', '')

            # Mirror usage into info.usage for callers that read it there
            if 'usage' in msg:
                msg['info'] = {'usage': msg['usage']}

            messages_map[msg_id] = msg

        # Reconstruct childrenIds from parentId links so that the map
        # is fully navigable (callers like the frontend rely on this).
        for msg_id, msg in messages_map.items():
            parent_id = msg.get('parentId')
            if parent_id and parent_id in messages_map:
                parent = messages_map[parent_id]
                children = parent.get('childrenIds')
                if children is None:
                    parent['childrenIds'] = [msg_id]
                elif msg_id not in children:
                    children.append(msg_id)

        # Ensure every message has a childrenIds list (leaf nodes get [])
        for msg in messages_map.values():
            if 'childrenIds' not in msg:
                msg['childrenIds'] = []

        return messages_map

    async def get_messages_by_user_id(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> list[ChatMessageModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ChatMessage)
                .filter_by(user_id=user_id)
                .order_by(ChatMessage.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            messages = result.scalars().all()
            return [ChatMessageModel.model_validate(message) for message in messages]

    async def get_messages_by_model_id(
        self,
        model_id: str,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        db: Optional[AsyncSession] = None,
    ) -> list[ChatMessageModel]:
        async with get_async_db_context(db) as db:
            stmt = select(ChatMessage).filter_by(model_id=model_id)
            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            stmt = stmt.order_by(ChatMessage.created_at.desc()).offset(skip).limit(limit)
            result = await db.execute(stmt)
            messages = result.scalars().all()
            return [ChatMessageModel.model_validate(message) for message in messages]

    async def get_chat_ids_by_model_id(
        self,
        model_id: str,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> list[str]:
        """Get distinct chat_ids that used a specific model."""

        async with get_async_db_context(db) as db:
            stmt = select(
                ChatMessage.chat_id,
                func.max(ChatMessage.created_at).label('last_message_at'),
            ).filter(ChatMessage.model_id == model_id)
            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)

            # Group by chat_id and order by most recent message in each chat
            # Secondary sort on chat_id ensures deterministic pagination
            stmt = (
                stmt.group_by(ChatMessage.chat_id)
                .order_by(func.max(ChatMessage.created_at).desc(), ChatMessage.chat_id)
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            chat_ids = result.all()
            return [chat_id for chat_id, _ in chat_ids]

    async def delete_messages_by_chat_id(self, chat_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            await db.execute(delete(ChatMessage).filter_by(chat_id=chat_id))
            await db.commit()
            return True

    async def delete_message_ids_by_chat_id(
        self,
        chat_id: str,
        message_ids: set[str],
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """Delete specific ``chat_message`` rows by their original message IDs."""
        if not message_ids:
            return True
        async with nullcontext(db) if db is not None else get_async_db_context() as session:
            await session.execute(
                delete(ChatMessage)
                .where(ChatMessage.chat_id == chat_id)
                .where(ChatMessage.id.in_({f'{chat_id}-{mid}' for mid in message_ids}))
            )
            if db is None:
                await session.commit()
            else:
                await session.flush()
            return True

    # Analytics methods
    async def get_analytics_summary(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, int]:
        """Return dashboard totals without materializing every model, user, and chat group."""
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import group_user_memberships

            stmt = select(
                func.count(ChatMessage.model_id).label('total_messages'),
                func.count(distinct(ChatMessage.chat_id)).label('total_chats'),
                func.count(distinct(ChatMessage.model_id)).label('total_models'),
                # GROUP BY user_id included the anonymous/null group in the old summary.
                (
                    func.count(distinct(ChatMessage.user_id))
                    + case((func.count() > func.count(ChatMessage.user_id), 1), else_=0)
                ).label('total_users'),
            ).where(ChatMessage.role == 'assistant')
            if start_date:
                stmt = stmt.where(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.where(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(group_user_memberships([group_id], True).c.user_id).scalar_subquery()
                stmt = stmt.where(ChatMessage.user_id.in_(group_users))

            return dict((await db.execute(stmt)).mappings().one())

    async def get_message_count_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, int]:
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import group_user_memberships

            stmt = select(ChatMessage.model_id, func.count(ChatMessage.id).label('count')).filter(
                ChatMessage.role == 'assistant',
                ChatMessage.model_id.isnot(None),
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(group_user_memberships([group_id], True).c.user_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.model_id)
            result = await db.execute(stmt)
            return {row.model_id: row.count for row in result.all()}

    async def get_model_analytics(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        """Count messages, distinct users, and chats per model in one pass."""
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import group_user_memberships

            stmt = select(
                ChatMessage.model_id,
                func.count(ChatMessage.id).label('count'),
                func.count(distinct(ChatMessage.user_id)).label('unique_users'),
                func.count(distinct(ChatMessage.chat_id)).label('unique_chats'),
            ).filter(
                ChatMessage.role == 'assistant',
                ChatMessage.model_id.isnot(None),
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(group_user_memberships([group_id], True).c.user_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.model_id)
            result = await db.execute(stmt)
            return {
                row.model_id: {
                    'count': row.count,
                    'unique_users': row.unique_users,
                    'unique_chats': row.unique_chats,
                }
                for row in result.all()
            }

    async def get_token_usage_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        """Aggregate token usage by model using database-level aggregation."""
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import group_user_memberships

            # We need the dialect to determine JSON extraction syntax
            # For async sessions, access via get_bind()
            bind = await db.connection()
            dialect = bind.dialect.name

            input_tokens, output_tokens = _token_columns(dialect)

            stmt = select(
                ChatMessage.model_id,
                func.coalesce(func.sum(input_tokens), 0).label('input_tokens'),
                func.coalesce(func.sum(output_tokens), 0).label('output_tokens'),
                func.count(ChatMessage.id).label('message_count'),
            ).filter(
                ChatMessage.role == 'assistant',
                ChatMessage.model_id.isnot(None),
                ChatMessage.usage.isnot(None),
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(group_user_memberships([group_id], True).c.user_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.model_id)
            result = await db.execute(stmt)

            return {
                row.model_id: {
                    'input_tokens': row.input_tokens,
                    'output_tokens': row.output_tokens,
                    'total_tokens': row.input_tokens + row.output_tokens,
                    'message_count': row.message_count,
                }
                for row in result.all()
            }

    async def get_user_analytics(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        """Aggregate all message counts and token usage per user in one pass."""
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import group_user_memberships

            bind = await db.connection()
            dialect = bind.dialect.name

            input_tokens, output_tokens = _token_columns(dialect)

            # The previous token query excluded anonymous users; keep those totals at zero.
            input_tokens = case((ChatMessage.user_id.isnot(None), input_tokens), else_=0)
            output_tokens = case((ChatMessage.user_id.isnot(None), output_tokens), else_=0)

            stmt = select(
                ChatMessage.user_id,
                func.coalesce(func.sum(input_tokens), 0).label('input_tokens'),
                func.coalesce(func.sum(output_tokens), 0).label('output_tokens'),
                func.count(ChatMessage.id).label('message_count'),
            ).filter(
                ChatMessage.role == 'assistant',
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(group_user_memberships([group_id], True).c.user_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.user_id)
            result = await db.execute(stmt)

            return {
                row.user_id: {
                    'input_tokens': row.input_tokens,
                    'output_tokens': row.output_tokens,
                    'total_tokens': row.input_tokens + row.output_tokens,
                    'message_count': row.message_count,
                }
                for row in result.all()
            }

    async def get_user_usage_summary(
        self,
        user_id: str,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        include_active_days: bool = True,
        timezone: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        async with get_async_db_context(db) as db:
            bind = await db.connection()
            dialect = bind.dialect.name
            input_tokens, output_tokens = _token_columns(dialect)

            messages_stmt = select(ChatMessage.role, func.count(ChatMessage.id).label('count')).filter(
                ChatMessage.user_id == user_id,
            )
            token_stmt = select(
                func.coalesce(func.sum(input_tokens), 0).label('input_tokens'),
                func.coalesce(func.sum(output_tokens), 0).label('output_tokens'),
            ).filter(
                ChatMessage.user_id == user_id,
                ChatMessage.role == 'assistant',
                ChatMessage.usage.isnot(None),
            )
            models_stmt = select(func.count(distinct(ChatMessage.model_id)).label('models_used')).filter(
                ChatMessage.user_id == user_id,
                ChatMessage.role == 'assistant',
                ChatMessage.model_id.isnot(None),
            )
            if start_date:
                messages_stmt = messages_stmt.filter(ChatMessage.created_at >= start_date)
                token_stmt = token_stmt.filter(ChatMessage.created_at >= start_date)
                models_stmt = models_stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                messages_stmt = messages_stmt.filter(ChatMessage.created_at <= end_date)
                token_stmt = token_stmt.filter(ChatMessage.created_at <= end_date)
                models_stmt = models_stmt.filter(ChatMessage.created_at <= end_date)

            messages_result = await db.execute(messages_stmt.group_by(ChatMessage.role))
            message_counts = {row.role: row.count for row in messages_result.all()}

            token_result = (await db.execute(token_stmt)).one()
            models_used = (await db.execute(models_stmt)).scalar() or 0

            active_days = set()
            if include_active_days:
                tz = _timezone(timezone)
                day_stmt = select(ChatMessage.created_at).filter(ChatMessage.user_id == user_id)
                if start_date:
                    day_stmt = day_stmt.filter(ChatMessage.created_at >= start_date)
                if end_date:
                    day_stmt = day_stmt.filter(ChatMessage.created_at <= end_date)
                day_result = await db.execute(day_stmt.where(ChatMessage.created_at > 0))
                active_days = {_date_key(row.created_at, tz) for row in day_result.all()}

            input_total = int(token_result.input_tokens or 0)
            output_total = int(token_result.output_tokens or 0)

            return {
                'messages': sum(message_counts.values()),
                'user_messages': message_counts.get('user', 0),
                'assistant_messages': message_counts.get('assistant', 0),
                'input_tokens': input_total,
                'output_tokens': output_total,
                'total_tokens': input_total + output_total,
                'models_used': int(models_used),
                'active_days': len(active_days),
            }

    async def get_user_first_message_created_at(
        self,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[int]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(func.min(ChatMessage.created_at)).filter(
                    ChatMessage.user_id == user_id,
                    ChatMessage.created_at > 0,
                )
            )
            value = result.scalar()
            return int(value) if value else None

    async def get_user_daily_usage(
        self,
        user_id: str,
        start_date: int,
        end_date: int,
        timezone: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> list[dict]:
        async with get_async_db_context(db) as db:
            tz = _timezone(timezone)
            bind = await db.connection()
            dialect = bind.dialect.name
            input_tokens, output_tokens = _token_columns(dialect)

            stmt = select(
                ChatMessage.created_at,
                ChatMessage.chat_id,
                ChatMessage.role,
                ChatMessage.model_id,
                ChatMessage.usage,
                input_tokens.label('input_tokens'),
                output_tokens.label('output_tokens'),
            ).filter(
                ChatMessage.user_id == user_id,
                ChatMessage.created_at >= start_date,
                ChatMessage.created_at <= end_date,
            )

            result = await db.execute(stmt.where(ChatMessage.created_at > 0))
            daily: dict[str, dict] = {}
            for row in result.all():
                date = _date_key(row.created_at, tz)
                entry = daily.setdefault(
                    date,
                    {
                        'date': date,
                        'messages': 0,
                        'chat_ids': set(),
                        'tokens': 0,
                        'models': Counter(),
                    },
                )
                entry['messages'] += 1
                entry['chat_ids'].add(row.chat_id)
                if row.role == 'assistant' and row.model_id:
                    entry['models'][row.model_id] += 1
                if row.usage:
                    entry['tokens'] += int(row.input_tokens or 0) + int(row.output_tokens or 0)

            current = datetime.fromtimestamp(_normalize_timestamp(start_date), tz=tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_dt = datetime.fromtimestamp(_normalize_timestamp(end_date), tz=tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            while current <= end_dt:
                date = current.strftime('%Y-%m-%d')
                daily.setdefault(
                    date,
                    {'date': date, 'messages': 0, 'chat_ids': set(), 'tokens': 0, 'models': Counter()},
                )
                current += timedelta(days=1)

            return [
                {
                    'date': item['date'],
                    'messages': item['messages'],
                    'chats': len(item['chat_ids']),
                    'tokens': item['tokens'],
                    'models': dict(item['models']),
                }
                for item in sorted(daily.values(), key=lambda x: x['date'])
            ]

    async def get_user_top_models(
        self,
        user_id: str,
        start_date: int,
        end_date: int,
        limit: int = 5,
        db: Optional[AsyncSession] = None,
    ) -> list[dict]:
        async with get_async_db_context(db) as db:
            bind = await db.connection()
            dialect = bind.dialect.name
            input_tokens, output_tokens = _token_columns(dialect)

            stmt = (
                select(
                    ChatMessage.model_id,
                    func.count(ChatMessage.id).label('messages'),
                    func.coalesce(func.sum(input_tokens), 0).label('input_tokens'),
                    func.coalesce(func.sum(output_tokens), 0).label('output_tokens'),
                )
                .filter(
                    ChatMessage.user_id == user_id,
                    ChatMessage.role == 'assistant',
                    ChatMessage.model_id.isnot(None),
                    ChatMessage.created_at >= start_date,
                    ChatMessage.created_at <= end_date,
                )
                .group_by(ChatMessage.model_id)
                .order_by(func.count(ChatMessage.id).desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            return [
                {
                    'model_id': row.model_id,
                    'messages': row.messages,
                    'input_tokens': int(row.input_tokens or 0),
                    'output_tokens': int(row.output_tokens or 0),
                    'total_tokens': int(row.input_tokens or 0) + int(row.output_tokens or 0),
                }
                for row in result.all()
            ]

    async def get_user_top_tools(
        self,
        user_id: str,
        start_date: int,
        end_date: int,
        limit: int = 5,
        db: Optional[AsyncSession] = None,
    ) -> list[dict]:
        async with get_async_db_context(db) as db:
            stmt = select(ChatMessage.output, ChatMessage.meta).filter(
                ChatMessage.user_id == user_id,
                ChatMessage.created_at >= start_date,
                ChatMessage.created_at <= end_date,
            )
            result = await db.execute(stmt)

            counts: Counter[str] = Counter()
            for output, meta in result.all():
                for name in _extract_tool_names(output):
                    counts[name] += 1
                for name in _extract_tool_names(meta):
                    counts[name] += 1

            return [{'name': name, 'count': count} for name, count in counts.most_common(limit)]

    async def get_message_count_by_user(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, int]:
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import group_user_memberships

            stmt = select(ChatMessage.user_id, func.count(ChatMessage.id).label('count')).filter(
                ChatMessage.role == 'assistant',
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(group_user_memberships([group_id], True).c.user_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.user_id)
            result = await db.execute(stmt)
            return {row.user_id: row.count for row in result.all()}

    async def get_message_count_by_chat(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, int]:
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import group_user_memberships

            stmt = select(ChatMessage.chat_id, func.count(ChatMessage.id).label('count')).filter(
                ChatMessage.role == 'assistant',
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(group_user_memberships([group_id], True).c.user_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.chat_id)
            result = await db.execute(stmt)
            return {row.chat_id: row.count for row in result.all()}

    async def get_usage_over_time_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        granularity: str = 'daily',
        metric: str = 'messages',
        bucket_offset: int = 0,
    ) -> dict[str, dict[str, int]]:
        """Get message counts or total tokens grouped by time bucket and model."""
        bucket_minutes = {'10m': 10, 'hourly': 60, '3h': 180, '6h': 360, 'daily': 1440}[granularity]
        date_format = '%Y-%m-%d' if granularity == 'daily' else '%Y-%m-%d %H:%M'
        step = timedelta(minutes=bucket_minutes)

        def bucket_start(timestamp):
            # Shift comparison events before bucketing so partial intervals align exactly.
            date = datetime.fromtimestamp(_normalize_timestamp(timestamp) + bucket_offset)
            minutes = date.hour * 60 + date.minute
            minutes = minutes // bucket_minutes * bucket_minutes
            return date.replace(hour=minutes // 60, minute=minutes % 60, second=0, microsecond=0)

        async with get_async_db_context(db) as db:
            from open_webui.models.groups import group_user_memberships

            bind = await db.connection()
            day = _daily_usage_bucket(bind.dialect.name, bucket_offset) if granularity == 'daily' else None
            value = literal(1)
            if metric == 'tokens':
                input_tokens, output_tokens = _token_columns(bind.dialect.name)
                value = func.coalesce(input_tokens, 0) + func.coalesce(output_tokens, 0)

            stmt = select(
                day if day is not None else ChatMessage.created_at,
                ChatMessage.model_id,
                func.sum(value) if day is not None else value,
            ).filter(
                ChatMessage.role == 'assistant',
                ChatMessage.model_id.isnot(None),
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(group_user_memberships([group_id], True).c.user_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            if day is not None:
                stmt = stmt.group_by(day, ChatMessage.model_id)
            result = await db.execute(stmt.where(ChatMessage.created_at > 0))
            counts: dict[str, dict[str, int]] = {}
            for timestamp, model_id, value in result.all():
                date_str = timestamp if day is not None else bucket_start(timestamp).strftime(date_format)
                bucket = counts.setdefault(date_str, {})
                bucket[model_id] = bucket.get(model_id, 0) + int(value)

            if start_date and end_date:
                current = bucket_start(start_date)
                end_dt = datetime.fromtimestamp(_normalize_timestamp(end_date) + bucket_offset)
                while current <= end_dt:
                    counts.setdefault(current.strftime(date_format), {})
                    current += step

            return counts


ChatMessages = ChatMessageTable()
