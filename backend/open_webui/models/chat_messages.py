import time
from collections import Counter
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from open_webui.internal.db import Base, get_async_db_context
from open_webui.utils.chat_history import (
    has_embedded_messages,
    split_chat_messages,
    uses_normalized_message_storage,
)
from open_webui.utils.response import merge_usage, normalize_usage
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    Text,
    cast,
    delete,
    distinct,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

####################
# Helpers
####################

_UNSET = object()


def _normalize_timestamp(timestamp: int) -> float:
    """Normalize and validate timestamp. Returns current time if invalid."""
    now = time.time()

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
    children_ids = Column(JSON, nullable=True)

    # Content
    data = Column(JSON, nullable=True)
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
    children_ids: Optional[list[str]] = None
    data: Optional[dict] = None
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
    DB_TO_JSON_KEY_MAP = {
        'parent_id': 'parentId',
        'children_ids': 'childrenIds',
        'model_id': 'model',
        'status_history': 'statusHistory',
        'context_summary': 'contextSummary',
        'created_at': 'timestamp',
    }
    PROJECTION_FIELDS = (
        'role',
        'parent_id',
        'children_ids',
        'content',
        'output',
        'model_id',
        'files',
        'sources',
        'embeds',
        'meta',
        'done',
        'status_history',
        'error',
        'usage',
        'context_summary',
        'created_at',
    )
    PROJECTION_INPUT_KEYS = (
        ('role', ('role',)),
        ('parent_id', ('parent_id', 'parentId')),
        ('children_ids', ('children_ids', 'childrenIds')),
        ('content', ('content',)),
        ('output', ('output',)),
        ('model_id', ('model_id', 'model')),
        ('files', ('files',)),
        ('sources', ('sources',)),
        ('embeds', ('embeds',)),
        ('meta', ('meta',)),
        ('done', ('done',)),
        ('status_history', ('status_history', 'statusHistory')),
        ('error', ('error',)),
        ('context_summary', ('context_summary', 'contextSummary')),
        ('created_at', ('timestamp',)),
    )
    PROJECTION_SOURCE_KEYS = dict(PROJECTION_INPUT_KEYS)

    @staticmethod
    def _composite_id(chat_id: str, message_id: str) -> str:
        return f'{chat_id}-{message_id}'

    @staticmethod
    def _original_message_id(row_id: str, chat_id: str) -> str:
        prefix = f'{chat_id}-'
        return row_id[len(prefix) :] if row_id.startswith(prefix) else row_id

    @staticmethod
    def _aliased_value(data: dict, *keys: str) -> tuple[bool, Any]:
        for key in keys:
            if key in data:
                return True, data[key]
        return False, None

    @staticmethod
    def _valid_projected_children(
        parent_id: str,
        children_ids: Sequence[str],
        parent_by_message_id: dict[str, str | None],
        fallback_children: Sequence[str] = (),
    ) -> list[str]:
        children = []
        seen = set()
        for child_id in children_ids:
            if child_id in seen or parent_by_message_id.get(child_id) != parent_id:
                continue
            seen.add(child_id)
            children.append(child_id)
        for child_id in fallback_children:
            if child_id not in seen and parent_by_message_id.get(child_id) == parent_id:
                seen.add(child_id)
                children.append(child_id)
        return children

    @staticmethod
    def _usage_is_explicitly_null(data: dict) -> bool:
        return data.get('usage', ...) is None or (
            isinstance(data.get('info'), dict) and data['info'].get('usage', ...) is None
        )

    def _merge_stored_message_data(
        self,
        message: ChatMessage,
        message_id: str,
        data: dict,
        *,
        usage_is_explicitly_null: bool,
    ) -> dict:
        stored_data = deepcopy(message.data) if isinstance(message.data, dict) else {}
        stored_data.update(deepcopy(data))
        stored_data['id'] = message_id

        # Keep canonical JSON keys synchronized when callers use snake_case aliases.
        for attribute in self.PROJECTION_FIELDS:
            value = getattr(message, attribute)
            json_key = self.DB_TO_JSON_KEY_MAP.get(attribute, attribute)
            source_keys = self.PROJECTION_SOURCE_KEYS.get(attribute, (json_key,))
            if json_key not in stored_data or any(key in data for key in source_keys):
                stored_data[json_key] = deepcopy(value)

        if usage_is_explicitly_null:
            stored_data['usage'] = None
        elif message.usage is not None:
            stored_data['usage'] = deepcopy(message.usage)
            if isinstance(stored_data.get('info'), dict):
                stored_data['info'] = {**stored_data['info'], 'usage': deepcopy(message.usage)}

        return stored_data

    def _apply_message_data(
        self,
        message: ChatMessage,
        message_id: str,
        user_id: str,
        data: dict,
        now: int,
        *,
        is_new: bool,
    ) -> None:
        """Apply raw message data to lossless storage and indexed projections."""
        message.user_id = user_id

        for attribute, keys in self.PROJECTION_INPUT_KEYS:
            present, value = self._aliased_value(data, *keys)
            if present:
                setattr(message, attribute, value)

        if is_new:
            message.role = message.role or 'user'
            message.done = data.get('done', True)
            message.created_at = message.created_at or now

        usage_is_explicitly_null = self._usage_is_explicitly_null(data)
        incoming_usage = get_usage(data)
        storage_data = data
        if usage_is_explicitly_null:
            message.usage = None
            storage_data = {**data, 'lastRequestUsage': None}
        elif incoming_usage:
            existing_usage = normalize_usage(message.usage or {}) if message.usage else {}
            message.usage = (
                existing_usage if incoming_usage == existing_usage else merge_usage(existing_usage, incoming_usage)
            )
            storage_data = {**data, 'lastRequestUsage': incoming_usage}

        message.data = self._merge_stored_message_data(
            message,
            message_id,
            storage_data,
            usage_is_explicitly_null=usage_is_explicitly_null,
        )
        message.updated_at = now

    async def upsert_message_in_session(
        self,
        db: AsyncSession,
        message_id: str,
        chat_id: str,
        user_id: str,
        data: dict,
        *,
        existing: Any = _UNSET,
    ) -> ChatMessage:
        now = int(time.time())
        composite_id = self._composite_id(chat_id, message_id)
        message = await db.get(ChatMessage, composite_id) if existing is _UNSET else existing
        is_new = message is None

        if message is None:
            message = ChatMessage(
                id=composite_id,
                chat_id=chat_id,
                user_id=user_id,
                role=data.get('role') or 'user',
                done=data.get('done', True),
                created_at=data.get('timestamp') or now,
                updated_at=now,
            )
            db.add(message)

        self._apply_message_data(message, message_id, user_id, data, now, is_new=is_new)
        return message

    async def upsert_message(
        self,
        message_id: str,
        chat_id: str,
        user_id: str,
        data: dict,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ChatMessageModel]:
        """Insert or update a chat message."""
        if not isinstance(data, dict):
            raise TypeError('data must be a dict')

        async with get_async_db_context(db) as session:
            try:
                message = await self.upsert_message_in_session(session, message_id, chat_id, user_id, data)
                await session.flush()
                result = ChatMessageModel.model_validate(message)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    async def bulk_upsert_messages(
        self,
        chat_id: str,
        user_id: str,
        messages: dict[str, dict],
        db: Optional[AsyncSession] = None,
    ) -> list[ChatMessageModel]:
        """Upsert a message map atomically using one session and one commit."""
        if not isinstance(messages, dict):
            raise TypeError('messages must be a dict')
        if any(not isinstance(message, dict) for message in messages.values()):
            raise TypeError('every message must be a dict')
        if not messages:
            return []

        async with get_async_db_context(db) as session:
            try:
                rows = await self.bulk_upsert_messages_in_session(session, chat_id, user_id, messages)
                results = [ChatMessageModel.model_validate(row) for row in rows]
                await session.commit()
                return results
            except Exception:
                await session.rollback()
                raise

    async def bulk_upsert_messages_in_session(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str,
        messages: dict[str, dict],
    ) -> list[ChatMessage]:
        if not messages:
            return []

        composite_ids = [self._composite_id(chat_id, message_id) for message_id in messages]
        result = await db.execute(
            select(ChatMessage).where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.id.in_(composite_ids),
            )
        )
        existing_by_id = {message.id: message for message in result.scalars().all()}

        rows = []
        for message_id, data in messages.items():
            composite_id = self._composite_id(chat_id, message_id)
            row = await self.upsert_message_in_session(
                db,
                message_id,
                chat_id,
                user_id,
                data,
                existing=existing_by_id.get(composite_id),
            )
            rows.append(row)

        await db.flush()
        return rows

    async def replace_messages_in_session(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str,
        messages: dict[str, dict],
    ) -> list[ChatMessage]:
        """Replace a chat's normalized snapshot without committing the caller's session."""
        rows = await self.bulk_upsert_messages_in_session(db, chat_id, user_id, messages)

        delete_stmt = delete(ChatMessage).where(ChatMessage.chat_id == chat_id)
        if messages:
            retained_ids = [self._composite_id(chat_id, message_id) for message_id in messages]
            delete_stmt = delete_stmt.where(ChatMessage.id.not_in(retained_ids))
        await db.execute(delete_stmt)
        await db.flush()
        return rows

    async def compact_legacy_chat_in_session(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str,
        chat: dict | None,
    ) -> dict:
        """Normalize an embedded legacy history without committing the caller's session."""
        embedded_messages = has_embedded_messages(chat)
        if uses_normalized_message_storage(chat) and not embedded_messages:
            return deepcopy(chat or {})

        compact_chat, legacy_messages = split_chat_messages(chat)
        if embedded_messages:
            await self.replace_messages_in_session(db, chat_id, user_id, legacy_messages)
        return compact_chat

    async def replace_messages_by_chat_id(
        self,
        chat_id: str,
        user_id: str,
        messages: dict[str, dict],
        db: Optional[AsyncSession] = None,
    ) -> list[ChatMessageModel]:
        """Atomically replace one chat's normalized message snapshot."""
        if not isinstance(messages, dict):
            raise TypeError('messages must be a dict')
        if any(not isinstance(message, dict) for message in messages.values()):
            raise TypeError('every message must be a dict')

        async with get_async_db_context(db) as session:
            try:
                rows = await self.replace_messages_in_session(session, chat_id, user_id, messages)

                results = [ChatMessageModel.model_validate(row) for row in rows]
                await session.commit()
                return results
            except Exception:
                await session.rollback()
                raise

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
                select(ChatMessage)
                .filter_by(chat_id=chat_id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            )
            messages = result.scalars().all()
            return [ChatMessageModel.model_validate(message) for message in messages]

    def row_to_message_data(self, row: ChatMessage) -> tuple[str, dict]:
        message_id = self._original_message_id(row.id, row.chat_id)
        message = deepcopy(row.data) if isinstance(row.data, dict) else {}
        message['id'] = message_id

        for attribute in self.PROJECTION_FIELDS:
            value = getattr(row, attribute)
            if value is None:
                continue
            json_key = self.DB_TO_JSON_KEY_MAP.get(attribute, attribute)
            message.setdefault(json_key, deepcopy(value))

        message.setdefault('content', '')
        message.setdefault('childrenIds', [])

        if row.usage is not None:
            message.setdefault('usage', deepcopy(row.usage))
            if 'info' not in message:
                message['info'] = {'usage': deepcopy(message['usage'])}
            elif isinstance(message['info'], dict) and 'usage' not in message['info']:
                message['info'] = {**message['info'], 'usage': deepcopy(message['usage'])}

        return message_id, message

    def _rows_to_message_map(self, rows: Sequence[ChatMessage]) -> dict[str, dict]:
        row_by_message_id = {self._original_message_id(row.id, row.chat_id): row for row in rows}
        messages_map = dict(self.row_to_message_data(row) for row in rows)
        parent_by_message_id = {message_id: message.get('parentId') for message_id, message in messages_map.items()}
        fallback_children = {message_id: [] for message_id in messages_map}

        for message_id, message in messages_map.items():
            parent_id = message.get('parentId')
            if parent_id in fallback_children:
                fallback_children[parent_id].append(message_id)

        for message_id, message in messages_map.items():
            projected_children = row_by_message_id[message_id].children_ids
            if isinstance(projected_children, list):
                message['childrenIds'] = self._valid_projected_children(
                    message_id,
                    projected_children,
                    parent_by_message_id,
                    fallback_children[message_id],
                )
            else:
                message['childrenIds'] = fallback_children[message_id]

        return messages_map

    async def _get_message_rows(
        self,
        db: AsyncSession,
        chat_id: str,
        message_ids: Optional[Sequence[str]] = None,
    ) -> list[ChatMessage]:
        if message_ids is not None and not message_ids:
            return []

        stmt = select(ChatMessage).where(ChatMessage.chat_id == chat_id)
        if message_ids is not None:
            composite_ids = [self._composite_id(chat_id, message_id) for message_id in dict.fromkeys(message_ids)]
            stmt = stmt.where(ChatMessage.id.in_(composite_ids))
        stmt = stmt.order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_message_data_map_by_chat_id(
        self,
        chat_id: str,
        message_ids: Optional[Sequence[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        """Return lossless message data keyed by original message ID."""
        async with get_async_db_context(db) as session:
            rows = await self._get_message_rows(session, chat_id, message_ids)
            messages_map = self._rows_to_message_map(rows)

        if message_ids is None:
            return messages_map
        return {
            message_id: messages_map[message_id]
            for message_id in dict.fromkeys(message_ids)
            if message_id in messages_map
        }

    async def get_pending_internal_leaf_messages_in_session(
        self,
        db: AsyncSession,
        chat_id: str,
    ) -> list[dict]:
        """Return pending internal user leaves using normalized message rows only."""
        result = await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.role == 'user',
                ChatMessage.meta.isnot(None),
                ChatMessage.meta['internal'].as_boolean().is_(True),
                ChatMessage.meta['type'].as_string().in_(('subagent', 'timer')),
            )
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        candidates = []
        for row in result.scalars().all():
            meta = row.meta if isinstance(row.meta, dict) else {}
            kind = meta.get('type')
            if kind == 'subagent' and meta.get('status') not in (None, 'pending'):
                continue
            if kind not in ('subagent', 'timer'):
                continue
            candidates.append(row)

        if not candidates:
            return []

        candidate_ids = [self._original_message_id(row.id, chat_id) for row in candidates]
        result = await db.execute(
            select(ChatMessage.parent_id).where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.parent_id.in_(candidate_ids),
            )
        )
        parent_ids = {parent_id for parent_id in result.scalars().all() if parent_id is not None}

        pending = []
        for row, message_id in zip(candidates, candidate_ids, strict=True):
            if message_id in parent_ids:
                continue
            message = self.row_to_message_data(row)[1]
            message['childrenIds'] = []
            pending.append(message)
        return pending

    async def get_latest_eligible_assistant_id_in_session(
        self,
        db: AsyncSession,
        chat_id: str,
    ) -> Optional[str]:
        """Return the newest completed-or-legacy assistant message ID."""
        result = await db.execute(
            select(ChatMessage.id)
            .where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.role == 'assistant',
                or_(ChatMessage.done.is_(True), ChatMessage.done.is_(None)),
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(1)
        )
        row_id = result.scalar_one_or_none()
        return self._original_message_id(row_id, chat_id) if row_id is not None else None

    async def get_message_topology_in_session(
        self,
        db: AsyncSession,
        chat_id: str,
    ) -> dict[str, dict]:
        result = await db.execute(
            select(
                ChatMessage.id,
                ChatMessage.parent_id,
                ChatMessage.children_ids,
                ChatMessage.role,
                ChatMessage.created_at,
            )
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        rows = result.all()
        topology: dict[str, dict] = {}

        projected_children: dict[str, Optional[list[str]]] = {}
        fallback_children: dict[str, list[str]] = {}

        for row_id, parent_id, children_ids, role, timestamp in rows:
            message_id = self._original_message_id(row_id, chat_id)
            topology[message_id] = {
                'id': message_id,
                'parentId': parent_id,
                'childrenIds': [],
                'role': role,
                'timestamp': timestamp,
            }
            projected_children[message_id] = children_ids if isinstance(children_ids, list) else None
            fallback_children[message_id] = []

        for message_id, message in topology.items():
            parent_id = message['parentId']
            if parent_id in fallback_children:
                fallback_children[parent_id].append(message_id)

        parent_by_message_id = {message_id: message['parentId'] for message_id, message in topology.items()}
        for message_id, message in topology.items():
            children_ids = projected_children[message_id]
            if children_ids is None:
                message['childrenIds'] = fallback_children[message_id]
                continue

            message['childrenIds'] = self._valid_projected_children(
                message_id,
                children_ids,
                parent_by_message_id,
                fallback_children[message_id],
            )

        return topology

    async def get_message_topology_by_chat_id(
        self,
        chat_id: str,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        async with get_async_db_context(db) as session:
            return await self.get_message_topology_in_session(session, chat_id)

    async def get_message_window_by_chat_id(
        self,
        chat_id: str,
        current_id: Optional[str],
        limit: int = 32,
        before_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """Return topology and one ancestor page ending at ``current_id``."""
        if limit < 1:
            raise ValueError('limit must be at least 1')

        async with get_async_db_context(db) as session:
            topology = await self.get_message_topology_in_session(session, chat_id)
            if not topology:
                return {
                    'topology': {},
                    'messages': {},
                    'loaded_ids': [],
                    'has_more': False,
                    'current_id': None,
                }

            if current_id is None:
                leaf_ids = [message_id for message_id, message in topology.items() if not message['childrenIds']]
                current_id = leaf_ids[-1] if leaf_ids else next(reversed(topology))

            if current_id not in topology:
                raise ValueError('current_id does not exist in this chat')

            ancestor_ids = []
            seen = set()
            cursor: Optional[str] = current_id
            while cursor is not None and cursor in topology:
                if cursor in seen:
                    raise ValueError('message ancestry contains a cycle')
                seen.add(cursor)
                ancestor_ids.append(cursor)
                cursor = topology[cursor]['parentId']

            if cursor is not None:
                raise ValueError(f'message ancestry references missing parent: {cursor}')

            start = 0
            if before_id is not None:
                if before_id not in ancestor_ids:
                    raise ValueError('before_id must be on the current message ancestry')
                start = ancestor_ids.index(before_id) + 1

            page_ids = ancestor_ids[start : start + limit]
            loaded_ids = list(reversed(page_ids))
            rows = await self._get_message_rows(session, chat_id, loaded_ids)
            row_map = self._rows_to_message_map(rows)
            missing_ids = [message_id for message_id in loaded_ids if message_id not in row_map]
            if missing_ids:
                raise ValueError(f'message ancestry is missing rows: {", ".join(missing_ids)}')

            messages = {}
            for message_id in loaded_ids:
                if message_id not in row_map:
                    continue
                messages[message_id] = {**row_map[message_id], **topology[message_id]}

            return {
                'topology': topology,
                'messages': messages,
                'loaded_ids': loaded_ids,
                'has_more': start + len(page_ids) < len(ancestor_ids),
                'current_id': current_id,
            }

    async def get_message_branch_in_session(
        self,
        db: AsyncSession,
        chat_id: str,
        current_id: str,
    ) -> list[dict]:
        """Return one complete branch without committing or opening another session."""
        topology = await self.get_message_topology_in_session(db, chat_id)
        if current_id not in topology:
            return []

        branch_ids = []
        seen = set()
        cursor: Optional[str] = current_id
        while cursor is not None and cursor in topology:
            if cursor in seen:
                raise ValueError('message ancestry contains a cycle')
            seen.add(cursor)
            branch_ids.append(cursor)
            cursor = topology[cursor]['parentId']

        if cursor is not None:
            raise ValueError(f'message ancestry references missing parent: {cursor}')

        branch_ids.reverse()
        rows = await self._get_message_rows(db, chat_id, branch_ids)
        row_map = self._rows_to_message_map(rows)
        missing_ids = [message_id for message_id in branch_ids if message_id not in row_map]
        if missing_ids:
            raise ValueError(f'message ancestry is missing rows: {", ".join(missing_ids)}')
        return [{**row_map[message_id], **topology[message_id]} for message_id in branch_ids]

    async def get_message_branch_by_chat_id(
        self,
        chat_id: str,
        current_id: str,
        db: Optional[AsyncSession] = None,
    ) -> list[dict]:
        """Return full message bodies for one root-to-leaf branch only."""
        async with get_async_db_context(db) as session:
            return await self.get_message_branch_in_session(session, chat_id, current_id)

    @staticmethod
    def _build_content_snippet(content: Any, search_text: str, max_length: int) -> Optional[str]:
        if not isinstance(content, str):
            return None

        index = content.lower().find(search_text.lower())
        if index == -1:
            return None

        start = max(index - max_length // 2, 0)
        end = min(start + max_length, len(content))
        if index + len(search_text) > end:
            end = min(index + len(search_text), len(content))
            start = max(end - max_length, 0)

        snippet = ' '.join(content[start:end].split())
        return f'{"..." if start else ""}{snippet}{"..." if end < len(content) else ""}'

    async def get_content_snippets_by_chat_ids(
        self,
        chat_ids: Sequence[str],
        search_text: str,
        max_length: int = 200,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, str]:
        """Fetch at most one bounded content snippet for each requested chat."""
        if max_length < 1:
            raise ValueError('max_length must be at least 1')

        unique_chat_ids = list(dict.fromkeys(chat_ids))
        normalized_search_text = search_text.strip()
        if not unique_chat_ids or not normalized_search_text:
            return {}

        escaped_search_text = normalized_search_text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        ranked_matches = (
            select(
                ChatMessage.chat_id.label('chat_id'),
                ChatMessage.content.label('content'),
                func.row_number()
                .over(
                    partition_by=ChatMessage.chat_id,
                    order_by=(ChatMessage.created_at.asc(), ChatMessage.id.asc()),
                )
                .label('match_rank'),
            )
            .where(
                ChatMessage.chat_id.in_(unique_chat_ids),
                ChatMessage.content.isnot(None),
                cast(ChatMessage.content, Text).ilike(f'%{escaped_search_text}%', escape='\\'),
            )
            .subquery()
        )
        stmt = (
            select(ranked_matches.c.chat_id, ranked_matches.c.content)
            .where(ranked_matches.c.match_rank == 1)
            .order_by(ranked_matches.c.chat_id.asc())
            .limit(len(unique_chat_ids))
        )

        async with get_async_db_context(db) as session:
            result = await session.execute(stmt)
            rows = result.all()

        snippets = {}
        for chat_id, content in rows:
            snippet = self._build_content_snippet(content, normalized_search_text, max_length)
            if snippet is not None:
                snippets[chat_id] = snippet
        return snippets

    async def get_messages_map_by_chat_id(self, chat_id: str, db: Optional[AsyncSession] = None) -> Optional[dict]:
        """Build a {message_id: message_dict} map from chat_message rows.

        Returns the same shape as chat.history.messages so callers
        (get_message_list, middleware) work unchanged.  Returns None if
        no rows exist for the chat (caller should fall back to the
        embedded JSON blob for legacy chats).
        """
        messages_map = await self.get_message_data_map_by_chat_id(chat_id, db=db)
        return messages_map or None

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
        async with get_async_db_context(db) as db:
            await self.delete_message_ids_in_session(db, chat_id, message_ids)
            await db.commit()
            return True

    async def delete_message_ids_in_session(
        self,
        db: AsyncSession,
        chat_id: str,
        message_ids: set[str],
    ) -> None:
        """Delete selected normalized rows without committing the caller's session."""
        if not message_ids:
            return
        await db.execute(
            delete(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .where(ChatMessage.id.in_({self._composite_id(chat_id, message_id) for message_id in message_ids}))
        )
        await db.flush()

    # Analytics methods
    async def get_message_count_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, int]:
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import GroupMember

            stmt = select(ChatMessage.model_id, func.count(ChatMessage.id).label('count')).filter(
                ChatMessage.role == 'assistant',
                ChatMessage.model_id.isnot(None),
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(GroupMember.user_id).filter(GroupMember.group_id == group_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.model_id)
            result = await db.execute(stmt)
            return {row.model_id: row.count for row in result.all()}

    async def get_unique_counts_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        """Count distinct users and chats per model."""
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import GroupMember

            stmt = select(
                ChatMessage.model_id,
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
                group_users = select(GroupMember.user_id).filter(GroupMember.group_id == group_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.model_id)
            result = await db.execute(stmt)
            return {
                row.model_id: {
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
            from open_webui.models.groups import GroupMember

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
                group_users = select(GroupMember.user_id).filter(GroupMember.group_id == group_id).scalar_subquery()
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

    async def get_token_usage_by_user(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        """Aggregate token usage by user using database-level aggregation."""
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import GroupMember

            bind = await db.connection()
            dialect = bind.dialect.name

            input_tokens, output_tokens = _token_columns(dialect)

            stmt = select(
                ChatMessage.user_id,
                func.coalesce(func.sum(input_tokens), 0).label('input_tokens'),
                func.coalesce(func.sum(output_tokens), 0).label('output_tokens'),
                func.count(ChatMessage.id).label('message_count'),
            ).filter(
                ChatMessage.role == 'assistant',
                ChatMessage.user_id.isnot(None),
                ChatMessage.usage.isnot(None),
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(GroupMember.user_id).filter(GroupMember.group_id == group_id).scalar_subquery()
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
                day_result = await db.execute(day_stmt)
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
                    ChatMessage.created_at.isnot(None),
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

            result = await db.execute(stmt)
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
            from open_webui.models.groups import GroupMember

            stmt = select(ChatMessage.user_id, func.count(ChatMessage.id).label('count')).filter(
                ChatMessage.role == 'assistant',
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(GroupMember.user_id).filter(GroupMember.group_id == group_id).scalar_subquery()
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
            from open_webui.models.groups import GroupMember

            stmt = select(ChatMessage.chat_id, func.count(ChatMessage.id).label('count')).filter(
                ChatMessage.role == 'assistant',
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(GroupMember.user_id).filter(GroupMember.group_id == group_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            stmt = stmt.group_by(ChatMessage.chat_id)
            result = await db.execute(stmt)
            return {row.chat_id: row.count for row in result.all()}

    async def get_daily_message_counts_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict[str, int]]:
        """Get message counts grouped by day and model."""
        async with get_async_db_context(db) as db:
            from datetime import datetime, timedelta

            from open_webui.models.groups import GroupMember

            stmt = select(ChatMessage.created_at, ChatMessage.model_id).filter(
                ChatMessage.role == 'assistant',
                ChatMessage.model_id.isnot(None),
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = select(GroupMember.user_id).filter(GroupMember.group_id == group_id).scalar_subquery()
                stmt = stmt.filter(ChatMessage.user_id.in_(group_users))

            result = await db.execute(stmt)
            results = result.all()

            # Group by date -> model -> count
            daily_counts: dict[str, dict[str, int]] = {}
            for timestamp, model_id in results:
                date_str = datetime.fromtimestamp(_normalize_timestamp(timestamp)).strftime('%Y-%m-%d')
                if date_str not in daily_counts:
                    daily_counts[date_str] = {}
                daily_counts[date_str][model_id] = daily_counts[date_str].get(model_id, 0) + 1

            # Fill in missing days
            if start_date and end_date:
                current = datetime.fromtimestamp(_normalize_timestamp(start_date))
                end_dt = datetime.fromtimestamp(_normalize_timestamp(end_date))
                while current <= end_dt:
                    date_str = current.strftime('%Y-%m-%d')
                    if date_str not in daily_counts:
                        daily_counts[date_str] = {}
                    current += timedelta(days=1)

            return daily_counts

    async def get_hourly_message_counts_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict[str, int]]:
        """Get message counts grouped by hour and model."""
        async with get_async_db_context(db) as db:
            from datetime import datetime, timedelta

            stmt = select(ChatMessage.created_at, ChatMessage.model_id).filter(
                ChatMessage.role == 'assistant',
                ChatMessage.model_id.isnot(None),
            )

            if start_date:
                stmt = stmt.filter(ChatMessage.created_at >= start_date)
            if end_date:
                stmt = stmt.filter(ChatMessage.created_at <= end_date)

            result = await db.execute(stmt)
            results = result.all()

            # Group by hour -> model -> count
            hourly_counts: dict[str, dict[str, int]] = {}
            for timestamp, model_id in results:
                hour_str = datetime.fromtimestamp(_normalize_timestamp(timestamp)).strftime('%Y-%m-%d %H:00')
                if hour_str not in hourly_counts:
                    hourly_counts[hour_str] = {}
                hourly_counts[hour_str][model_id] = hourly_counts[hour_str].get(model_id, 0) + 1

            # Fill in missing hours
            if start_date and end_date:
                current = datetime.fromtimestamp(_normalize_timestamp(start_date)).replace(
                    minute=0, second=0, microsecond=0
                )
                end_dt = datetime.fromtimestamp(_normalize_timestamp(end_date))
                while current <= end_dt:
                    hour_str = current.strftime('%Y-%m-%d %H:00')
                    if hour_str not in hourly_counts:
                        hourly_counts[hour_str] = {}
                    current += timedelta(hours=1)

            return hourly_counts


ChatMessages = ChatMessageTable()
