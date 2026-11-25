"""Chat models, forms, and database operations."""

from __future__ import annotations

from contextlib import asynccontextmanager
from copy import deepcopy
import logging
import re
import time
import uuid
from typing import Any, Literal

# local imports
from open_webui.models.chat_views import ChatViewState
from open_webui.models.notifications import emit_changes
from open_webui.env import ENABLE_ADMIN_CHAT_ACCESS
from open_webui.models.comments import delete_resource_comments
from open_webui.internal.db import Base, JSONField, get_async_db, get_async_db_context
from open_webui.models.access_grants import AccessGrants
from open_webui.models.automations import AutomationRun
from open_webui.models.chat_messages import ChatMessage, ChatMessages
from open_webui.models.folders import Folders
from open_webui.models.tags import Tags, delete_resource_tags, get_tag_id, resource_tag_filter
from open_webui.tasks import has_active_tasks
from open_webui.utils.misc import get_output_text, sanitize_data_for_db, sanitize_text_for_db
from open_webui.utils.session_records import has_pending_tool_approval
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    ColumnElement,
    ForeignKey,
    Index,
    Row,
    String,
    Text,
    UniqueConstraint,
    and_,
    delete,
    exists,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import case, exists
from sqlalchemy.sql.expression import bindparam

log = logging.getLogger(__name__)
ACTIVE_CHAT_GAP_SECONDS = 30 * 60
# Filter token for chats without a folder status. The status itself is stored and returned as null;
# only query strings, which can't carry null, need a name for it.
NO_FOLDER_STATUS = 'none'
# Priorities are fixed, most urgent first. A chat without one stores nothing; 'none' is only
# the filter token for that, like NO_FOLDER_STATUS.
FOLDER_PRIORITIES = ('urgent', 'high', 'medium', 'low')
NO_FOLDER_PRIORITY = 'none'


def _as_seconds(value):
    # Older rows may hold numbers as strings; chats set before tracking have none.
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def folder_status_since(meta: dict, status: str | None):
    """When the chat would have entered `status` had all its time there been one stretch.

    Earlier stretches in the same status count, so moving away and back doesn't reset it.
    """
    started = _as_seconds(meta.get('folder_status_at'))
    if status is None or started is None:
        return None
    return started - (_as_seconds((meta.get('folder_status_durations') or {}).get(status)) or 0)


CHAT_SEARCH_FILTER_PREFIXES = ('tag:', 'folder:', 'pinned:', 'archived:', 'shared:')


def chat_search_content_query(text: str) -> str:
    words = sanitize_text_for_db(text).lower().strip().split()
    return ' '.join(word for word in words if not word.startswith(CHAT_SEARCH_FILTER_PREFIXES)).strip()


def chat_search_terms(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r'[a-z0-9]+', text.lower())))[:12]


def chat_message_list(chat: dict) -> list:
    if not isinstance(chat, dict):
        return []
    history = chat.get('history')
    messages = history.get('messages') if isinstance(history, dict) else None
    if not isinstance(messages, (dict, list)) or not messages:
        messages = chat.get('messages')
    if isinstance(messages, dict):
        return list(messages.values())
    return messages if isinstance(messages, list) else []


def chat_search_snippet(chat: dict, search_text: str, max_length: int = 200) -> str | None:
    search_text = chat_search_content_query(search_text)
    if not search_text:
        return None

    messages = chat_message_list(chat)

    needles = list(dict.fromkeys([search_text, *chat_search_terms(search_text)]))
    for needle in needles:
        for message in messages:
            if not isinstance(message, dict):
                continue

            content = message.get('content')
            if not isinstance(content, str):
                continue

            index = content.lower().find(needle)
            if index == -1:
                continue

            start = max(index - max_length // 2, 0)
            end = min(start + max_length, len(content))
            if index + len(needle) > end:
                end = min(index + len(needle), len(content))
                start = max(end - max_length, 0)

            snippet = ' '.join(content[start:end].split())
            return f'{"..." if start else ""}{snippet}{"..." if end < len(content) else ""}'

    return None


def chat_search_message_content_match_sql(dialect_name: str, key: str) -> str:
    if dialect_name == 'sqlite':
        content = "json_extract(message.content, '$')"
    elif dialect_name == 'postgresql':
        content = "CASE WHEN json_typeof(message.content) = 'string' THEN message.content #>> '{}' END"
    else:
        raise NotImplementedError(f'Unsupported dialect: {dialect_name}')

    return f"""
    EXISTS (
        SELECT 1
        FROM chat_message AS message
        WHERE message.chat_id = Chat.id
        AND LOWER({content}) LIKE '%' || :{key} || '%'
    )
    """


def folder_priority_rank():
    """Higher is more urgent, so descending puts Urgent first; no priority ranks lowest."""
    return case(
        {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1},
        value=Chat.meta['folder_priority'].as_string(),
        else_=0,
    )


def chat_list_order(sort_by: str = 'updated_at', sort_dir: str = 'desc', user_id: str | None = None):
    if sort_by == 'priority':
        rank = folder_priority_rank()
        return (rank.asc() if sort_dir == 'asc' else rank.desc()), Chat.updated_at.desc(), Chat.id
    if sort_by != 'unread_updated_at':
        sort_column = {'title': Chat.title, 'created_at': Chat.created_at}.get(sort_by, Chat.updated_at)
        order_clause = sort_column.asc() if sort_dir == 'asc' else sort_column.desc()
        return order_clause, Chat.id

    unfinished_assistant = (
        select(ChatMessage.id)
        .where(ChatMessage.chat_id == Chat.id)
        .where(ChatMessage.role == 'assistant')
        .where(ChatMessage.done.is_(False))
        .exists()
    )
    conditions = [Chat.updated_at > func.coalesce(Chat.last_read_at, 0), ~unfinished_assistant]
    if user_id is not None:
        conditions.append(Chat.user_id == user_id)

    unread = case(
        (and_(*conditions), 1),
        else_=0,
    )
    return unread.desc(), Chat.updated_at.desc(), Chat.id


class Chat(Base):  # database table mapping for chat entity
    __tablename__ = 'chat'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)  # owner user id
    title = Column(Text)  # user-visible conversation title
    chat = Column(JSON)

    created_at = Column(BigInteger, index=True)  # conversation creation timestamp
    updated_at = Column(BigInteger, index=True)  # conversation modification timestamp

    share_id = Column(Text, unique=True, nullable=True)  # public share link token
    archived = Column(Boolean, default=False)  # hidden from main chat list
    pinned = Column(Boolean, default=False, nullable=True)

    meta = Column(JSON, server_default='{}')
    variables = Column(JSON, nullable=True)
    folder_id = Column(Text, nullable=True)

    tasks = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    current_message_id = Column(Text, nullable=True)

    last_read_at = Column(BigInteger, nullable=True)
    timer_at = Column(BigInteger, nullable=True)  # ns due time, set only while a timer chat waits to be claimed

    __table_args__ = (
        # Performance indexes for common queries
        Index('folder_id_idx', 'folder_id'),
        Index('user_id_pinned_idx', 'user_id', 'pinned'),
        Index('user_id_archived_idx', 'user_id', 'archived'),
        Index('updated_at_user_id_idx', 'updated_at', 'user_id'),
        Index('folder_id_user_id_idx', 'folder_id', 'user_id'),
        Index('user_id_updated_at_id_idx', 'user_id', updated_at.desc(), 'id'),
        Index(
            'timer_at_idx',
            'timer_at',
            sqlite_where=text('timer_at IS NOT NULL'),
            postgresql_where=text('timer_at IS NOT NULL'),
        ),
        # timer_at key column turns the IS NOT NULL into a seek, so this beats the plain user_id indexes
        Index(
            'user_id_timer_at_idx',
            'user_id',
            'timer_at',
            sqlite_where=text('timer_at IS NOT NULL'),
            postgresql_where=text('timer_at IS NOT NULL'),
        ),
        # covering index: lets SQLite serve count_unread_by_folder_ids without reading chat rows
        Index('user_id_folder_unread_idx', 'user_id', 'folder_id', 'archived', 'updated_at', 'last_read_at', 'id'),
    )


class ChatModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # allows ORM model binding
    id: str
    user_id: str
    title: str
    chat: dict

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    share_id: str | None = None
    archived: bool = False
    pinned: bool | None = False

    meta: dict = {}
    variables: dict = {}
    folder_id: str | None = None

    tasks: list | None = None
    summary: str | None = None
    current_message_id: str | None = None

    last_read_at: int | None = None
    timer_at: int | None = None

    @field_validator('variables', mode='before')
    @classmethod
    def normalize_variables(cls, value):
        return value if isinstance(value, dict) else {}


class ChatFile(Base):
    __tablename__ = 'chat_file'

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text, nullable=False)

    chat_id = Column(Text, ForeignKey('chat.id', ondelete='CASCADE'), nullable=False)
    message_id = Column(Text, nullable=True)
    file_id = Column(Text, ForeignKey('file.id', ondelete='CASCADE'), nullable=False)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (UniqueConstraint('chat_id', 'file_id', name='uq_chat_file_chat_file'),)


class ChatFileModel(BaseModel):
    id: str
    user_id: str

    chat_id: str
    message_id: str | None = None
    file_id: str

    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


# Forms


class ChatForm(BaseModel):
    chat: dict
    variables: dict | None = None
    folder_id: str | None = None


class ChatImportForm(ChatForm):
    meta: dict | None = {}
    pinned: bool | None = False
    archived: bool | None = False
    current_message_id: str | None = None
    created_at: int | None = None
    updated_at: int | None = None


class ChatsImportForm(BaseModel):
    chats: list[ChatImportForm]


class ChatTitleForm(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: str
    chat: dict
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch
    share_id: str | None = None  # id of the chat to be shared
    archived: bool
    pinned: bool | None = False
    meta: dict = {}
    variables: dict = {}
    folder_id: str | None = None

    tasks: list | None = None
    summary: str | None = None
    current_message_id: str | None = None
    context_usage: dict | None = None

    @field_validator('variables', mode='before')
    @classmethod
    def normalize_variables(cls, value):
        return value if isinstance(value, dict) else {}


class ChatAccessResponse(ChatResponse):
    write_access: bool
    task_ids: list[str] | None = None


class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int
    last_read_at: int | None = None
    snippet: str | None = None
    active: bool = False
    pending_approval: bool = False
    archived: bool = False


class SharedChatResponse(BaseModel):
    id: str
    title: str
    share_id: str | None = None
    updated_at: int
    created_at: int


class ChatListResponse(BaseModel):
    items: list[ChatModel]
    total: int


class ChatUsageStatsResponse(BaseModel):
    id: str  # chat id

    models: dict = {}  # models used in the chat with their usage counts
    message_count: int  # number of messages in the chat

    history_models: dict = {}  # models used in the chat history with their usage counts
    history_message_count: int  # number of messages in the chat history
    history_user_message_count: int  # number of user messages in the chat history
    history_assistant_message_count: int  # number of assistant messages in the chat history

    average_response_time: float  # average response time of assistant messages in seconds
    average_user_message_content_length: float  # average length of user message contents
    average_assistant_message_content_length: float  # average length of assistant message contents

    tags: list[str] = []  # tags associated with the chat

    last_message_at: int  # timestamp of the last message
    updated_at: int
    created_at: int

    model_config = ConfigDict(extra='allow')


class ChatUsageStatsListResponse(BaseModel):
    items: list[ChatUsageStatsResponse]
    total: int
    model_config = ConfigDict(extra='allow')


class MessageStats(BaseModel):
    id: str
    role: str
    model: str | None = None
    content_length: int
    token_count: int | None = None
    timestamp: int | None = None
    rating: int | None = None  # Derived from message.annotation.rating
    tags: list[str] | None = None  # Derived from message.annotation.tags


class ChatHistoryStats(BaseModel):
    messages: dict[str, MessageStats]
    currentId: str | None = None


class ChatBody(BaseModel):
    history: ChatHistoryStats


class AggregateChatStats(BaseModel):
    average_response_time: float
    average_user_message_content_length: float
    average_assistant_message_content_length: float
    models: dict[str, int]
    message_count: int
    history_models: dict[str, int]
    history_message_count: int
    history_user_message_count: int
    history_assistant_message_count: int


class ChatStatsExport(BaseModel):
    id: str
    user_id: str
    created_at: int
    updated_at: int
    tags: list[str] = []
    stats: AggregateChatStats
    chat: ChatBody


class ChatTable:
    @asynccontextmanager
    async def _chat_transaction(self, id: str):
        # Own the transaction; callers may already have a read session.
        async with get_async_db() as session:
            if session.bind.dialect.name == 'sqlite':
                await session.execute(text('BEGIN IMMEDIATE'))
            chat = await session.get(Chat, id, with_for_update=True)
            yield session, chat
            await session.commit()

    @asynccontextmanager
    async def edit_message_output(self, chat_id: str, message_id: str):
        """Read and modify tool state under the chat lock."""
        async with self._chat_transaction(chat_id) as (session, chat):
            if chat is None:
                yield None
                return
            row = await session.get(ChatMessage, f'{chat_id}-{message_id}')
            if row is None:
                yield None
                return
            message = deepcopy(ChatMessages.to_message(row))
            yield message
            message = self._clean_null_bytes(message)
            await ChatMessages.upsert_message(message_id, chat_id, row.user_id, message, db=session)

    def _clean_null_bytes(self, obj):
        """Recursively remove null bytes from strings in dict/list structures."""
        return sanitize_data_for_db(obj)

    async def _with_history(self, chat: Chat, db: AsyncSession) -> ChatModel:
        """The chat model with chat.history built from its message rows."""
        return (await self._with_histories([chat], db=db))[0]

    async def _with_histories(self, chats: list[Chat], db: AsyncSession) -> list[ChatModel]:
        """The chat models with chat.history built from their message rows, in one query."""
        messages = await ChatMessages.get_messages_maps_by_chat_ids([chat.id for chat in chats], db=db)
        return [
            ChatModel.model_validate(chat).model_copy(
                update={
                    'chat': {
                        **(chat.chat or {}),
                        'history': {'messages': messages.get(chat.id, {}), 'currentId': chat.current_message_id},
                    }
                }
            )
            for chat in chats
        ]

    @staticmethod
    def _without_history(chat: dict) -> dict:
        """The chat blob as stored: its messages live in chat_message rows."""
        return {key: value for key, value in chat.items() if key not in ('history', 'messages')}

    @staticmethod
    def _history_messages(chat: dict, user_id: str) -> dict:
        """The messages a client sent with a chat, each with its author; a legacy list becomes a chain."""
        history = chat.get('history') if isinstance(chat.get('history'), dict) else {}
        messages = history.get('messages') if isinstance(history.get('messages'), dict) else None
        if messages is None and isinstance(chat.get('messages'), list):
            messages = {}
            parent_id = None
            for index, message in enumerate(chat['messages']):
                if isinstance(message, dict):
                    # Ids by position, so saving the same list again updates these messages.
                    message_id = str(message.get('id') or index)
                    messages[message_id] = {
                        **message,
                        'id': message_id,
                        'parentId': message.get('parentId') or parent_id,
                    }
                    parent_id = message_id
        authored = {}
        for message_id, message in (messages or {}).items():
            if isinstance(message, dict):
                author_id = message.get('user_id') or (
                    message['user'].get('id') if isinstance(message.get('user'), dict) else None
                )
                authored[message_id] = {**message, 'user_id': author_id if isinstance(author_id, str) else user_id}
        return authored

    def get_current_message_id(self, chat: dict | None) -> str | None:
        chat = chat or {}
        history = chat.get('history') if isinstance(chat.get('history'), dict) else {}
        current_id = history.get('currentId') or chat.get('currentId') or chat.get('branchPointMessageId')
        if current_id:
            return current_id

        messages = chat.get('messages')
        if isinstance(messages, list):
            for message in reversed(messages):
                if isinstance(message, dict) and message.get('id'):
                    return message['id']

        return None

    def _sanitize_chat_row(self, chat_item):
        """
        Clean a Chat SQLAlchemy model's title + chat JSON,
        and return True if anything changed.
        """
        changed = False

        # Clean title
        if chat_item.title:
            cleaned = self._clean_null_bytes(chat_item.title)
            if cleaned != chat_item.title:
                chat_item.title = cleaned
                changed = True

        # Clean JSON
        if chat_item.chat:
            cleaned = self._clean_null_bytes(chat_item.chat)
            if cleaned != chat_item.chat:
                chat_item.chat = cleaned
                changed = True

        return changed

    @staticmethod
    def _last_descendant_id(messages: dict, message_id: str) -> str:
        seen_ids = set()
        while message_id in messages and message_id not in seen_ids:
            seen_ids.add(message_id)
            message = messages[message_id]
            child_ids = message.get('childrenIds') if isinstance(message, dict) else []
            child_ids = child_ids if isinstance(child_ids, list) else []
            # Skip malformed messages and stale links when recovering the branch.
            next_id = next(
                (
                    child_id
                    for child_id in reversed(child_ids)
                    if isinstance(child_id, str)
                    and child_id not in seen_ids
                    and isinstance(child := messages.get(child_id), dict)
                    and child.get('id') == child_id
                    and child.get('role')
                    and child.get('parentId') == message_id
                    # A queued message waits in the queue, not on the branch shown.
                    and not (
                        (child.get('meta') or {}).get('status') == 'pending'
                        and (child.get('meta') or {}).get('internal') is not True
                    )
                ),
                None,
            )
            if not next_id:
                break
            message_id = next_id
        return message_id

    @staticmethod
    def _add_child_id_to_parent(messages: dict, parent_id: str | None, child_id: str) -> bool:
        parent = messages.get(parent_id) if parent_id else None
        if not isinstance(parent, dict):
            return False

        child_ids = parent.get('childrenIds')
        if not isinstance(child_ids, list):
            child_ids = []
            parent['childrenIds'] = child_ids

        if child_id in child_ids:
            return False

        child_ids.append(child_id)
        return True

    def _repair_chat_current_id(self, chat: dict) -> bool:
        history = chat.get('history')
        if not isinstance(history, dict):
            return False

        messages = history.get('messages')
        if not isinstance(messages, dict):
            return False

        changed = False
        for message_id, message in messages.items():
            if not isinstance(message, dict):
                continue
            changed = self._add_child_id_to_parent(messages, message.get('parentId'), message_id) or changed

        current_id = history.get('currentId')
        current_message = messages.get(current_id)
        output = []
        if isinstance(current_message, dict):
            output = current_message.get('output') or []

        output_role = next(
            (item.get('role') for item in output if isinstance(item, dict) and item.get('role')),
            None,
        )
        current_is_bad_leaf = (
            isinstance(current_message, dict)
            and output_role == 'assistant'
            and current_message.get('parentId') is None
            and not current_message.get('timestamp')
            and len(messages) > 1
        )
        if (
            isinstance(current_message, dict)
            and current_message.get('id')
            and current_message.get('role')
            and not current_is_bad_leaf
        ):
            last_descendant_id = self._last_descendant_id(messages, current_id)
            if last_descendant_id != current_id:
                history['currentId'] = last_descendant_id
                return True

            return changed

        latest_leaf_id = None
        latest_timestamp = -1
        for message_id, message in messages.items():
            if not isinstance(message, dict) or not message.get('role'):
                continue

            children_ids = message.get('childrenIds') if isinstance(message.get('childrenIds'), list) else []
            timestamp = message.get('timestamp') or 0
            if len(children_ids) == 0 and timestamp > latest_timestamp:
                latest_leaf_id = message_id
                latest_timestamp = timestamp

        if not latest_leaf_id or latest_leaf_id == current_id:
            return changed

        history['currentId'] = latest_leaf_id
        return True

    async def require_chat_creation_permission(self, user_id: str, db: AsyncSession | None = None) -> None:
        from fastapi import HTTPException
        from open_webui.constants import ERROR_MESSAGES
        from open_webui.models.config import Config
        from open_webui.models.users import Users
        from open_webui.utils.access_control import get_permissions

        user = await Users.get_user_by_id(user_id, db=db)
        if user and user.role == 'admin':
            return
        if not user:
            raise HTTPException(status_code=403, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

        permissions = await get_permissions(user_id, await Config.get('user.permissions'), db=db)
        chat_permissions = permissions.get('chat', {})
        if chat_permissions.get('temporary') and chat_permissions.get('temporary_enforced'):
            raise HTTPException(status_code=403, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    async def insert_new_chat(
        self,
        id: str,
        user_id: str,
        form_data: ChatForm,
        db: AsyncSession | None = None,
        *,
        internal_meta: dict | None = None,
        timer_at: int | None = None,
    ) -> ChatModel | None:
        await self.require_chat_creation_permission(user_id, db=db)
        async with get_async_db_context(db) as session:
            chat = ChatModel(
                **{
                    'id': id,
                    'user_id': user_id,
                    'title': self._clean_null_bytes(
                        form_data.chat['title'] if 'title' in form_data.chat else 'New Chat'
                    ),
                    'chat': self._clean_null_bytes(form_data.chat),
                    'folder_id': form_data.folder_id,
                    'meta': internal_meta or {},
                    'timer_at': timer_at,
                    'variables': form_data.variables or {},
                    'current_message_id': self.get_current_message_id(form_data.chat),
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                    'last_read_at': int(time.time()),
                }
            )

            chat_item = Chat(**{**chat.model_dump(), 'chat': self._without_history(chat.chat)})
            session.add(chat_item)
            await session.flush()
            ChatMessages.insert_messages(id, self._history_messages(chat.chat, user_id), db=session)
            await session.commit()
            return chat

    async def get_internal_chat_ids_by_parent_id(self, parent_chat_id: str, user_id: str) -> list[str]:
        async with get_async_db_context() as session:
            result = await session.execute(
                select(Chat.id).where(
                    Chat.user_id == user_id,
                    Chat.meta['internal'].as_boolean().is_(True),
                    Chat.meta['parent_chat_id'].as_string() == parent_chat_id,
                )
            )
            return list(result.scalars().all())

    async def get_chat_ids_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> list[str]:
        async with get_async_db_context(db) as session:
            result = await session.execute(select(Chat.id).filter_by(user_id=user_id))
            return list(result.scalars().all())

    async def get_chat_ids_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str, db: AsyncSession | None = None
    ) -> list[str]:
        async with get_async_db_context(db) as session:
            result = await session.execute(select(Chat.id).filter_by(user_id=user_id, folder_id=folder_id))
            return list(result.scalars().all())

    async def get_children_by_parent_id(self, parent_chat_id: str, user_id: str) -> list:
        async with get_async_db_context() as session:
            result = await session.execute(
                select(Chat.id, Chat.title, Chat.meta, Chat.timer_at, Chat.created_at)
                .where(
                    Chat.user_id == user_id,
                    Chat.meta['internal'].as_boolean().is_(True),
                    Chat.meta['parent_chat_id'].as_string() == parent_chat_id,
                )
                .order_by(Chat.created_at.desc())
            )
            return list(result.all())

    async def get_internal_chat_by_note_id(
        self, note_id: str, user_id: str, db: AsyncSession | None = None
    ) -> ChatModel | None:
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(Chat)
                .where(
                    Chat.user_id == user_id,
                    Chat.meta['internal'].as_boolean().is_(True),
                    Chat.meta['type'].as_string() == 'note',
                    Chat.meta['note_id'].as_string() == note_id,
                )
                .order_by(Chat.updated_at.desc(), Chat.created_at.desc())
            )
            chat = result.scalars().first()
            return ChatModel.model_validate(chat) if chat else None

    async def get_internal_chats_by_note_id(
        self, note_id: str, user_id: str, db: AsyncSession | None = None
    ) -> list[ChatModel]:
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(Chat)
                .where(
                    Chat.user_id == user_id,
                    Chat.meta['internal'].as_boolean().is_(True),
                    Chat.meta['type'].as_string() == 'note',
                    Chat.meta['note_id'].as_string() == note_id,
                )
                .order_by(Chat.updated_at.desc(), Chat.created_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in result.scalars().all()]

    async def get_internal_chat_ids_by_note_id(self, note_id: str, db: AsyncSession | None = None) -> list[str]:
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(Chat.id).where(
                    Chat.meta['internal'].as_boolean().is_(True),
                    Chat.meta['type'].as_string() == 'note',
                    Chat.meta['note_id'].as_string() == note_id,
                )
            )
            return list(result.scalars().all())

    def _chat_import_form_to_chat_model(self, user_id: str, form_data: ChatImportForm) -> ChatModel:
        id = str(uuid.uuid4())
        chat = ChatModel(
            **{
                'id': id,
                'user_id': user_id,
                'title': self._clean_null_bytes(form_data.chat['title'] if 'title' in form_data.chat else 'New Chat'),
                'chat': self._clean_null_bytes(form_data.chat),
                # Tags are stored as links, see import_chats.
                'meta': {key: value for key, value in (form_data.meta or {}).items() if key != 'tags'},
                'variables': form_data.variables or {},
                'pinned': form_data.pinned,
                'archived': form_data.archived,
                'folder_id': form_data.folder_id,
                'current_message_id': form_data.current_message_id or self.get_current_message_id(form_data.chat),
                'created_at': (form_data.created_at if form_data.created_at else int(time.time())),
                'updated_at': (form_data.updated_at if form_data.updated_at else int(time.time())),
                'last_read_at': int(time.time()),
            }
        )
        messages = list((chat.chat.get('history', {}).get('messages') or {}).values())
        messages.extend(chat.chat.get('messages') or [])
        for message in messages:
            message['user_id'] = (
                message.get('user_id')
                or (message['user'].get('id') if isinstance(message.get('user'), dict) else None)
                or user_id
            )
        return chat

    async def import_chats(
        self,
        user_id: str,
        chat_import_forms: list[ChatImportForm],
        db: AsyncSession | None = None,
    ) -> list[ChatModel]:
        await self.require_chat_creation_permission(user_id, db=db)
        async with get_async_db_context(db) as session:
            from open_webui.utils.access_control.folders import has_folder_write_access

            # Validate folder_id references — clear any that don't exist
            folder_ids = {f.folder_id for f in chat_import_forms if f.folder_id}
            existing = set()
            for fid in folder_ids:
                if await has_folder_write_access(user_id, fid, db=session):
                    existing.add(fid)

            cleared = 0
            for form in chat_import_forms:
                if form.folder_id and form.folder_id not in existing:
                    form.folder_id = None
                    cleared += 1
            if cleared:
                log.info('Import: cleared %d dangling folder_id(s) for user %s', cleared, user_id)

            chats = [self._chat_import_form_to_chat_model(user_id, form_data) for form_data in chat_import_forms]
            session.add_all(Chat(**{**chat.model_dump(), 'chat': self._without_history(chat.chat)}) for chat in chats)
            await session.flush()
            for chat in chats:
                ChatMessages.insert_messages(chat.id, self._history_messages(chat.chat, user_id), db=session)
            await session.commit()

            tags = {}
            for form_data, imported_chat in zip(chat_import_forms, chats):
                names = (form_data.meta or {}).get('tags')
                if isinstance(names, list):
                    tags[imported_chat.id] = [get_tag_id(name) for name in names if isinstance(name, str)]
            await Tags.add_tags_to_resources('chat', tags, user_id)

            return chats

    async def update_chat_by_id(
        self,
        id: str,
        chat: dict,
        db: AsyncSession | None = None,
        *,
        touch: bool = True,
    ) -> ChatModel | None:
        """Patch top-level chat keys; history is merged so stale writers don't drop messages."""
        try:
            async with self._chat_transaction(id) as (session, chat_item):
                if chat_item is None:
                    return None

                if 'history' not in chat and isinstance(chat.get('messages'), list):
                    listed = self._history_messages(chat, chat_item.user_id)
                    stored_ids = set(
                        (await session.execute(select(ChatMessage.id).where(ChatMessage.chat_id == id))).scalars()
                    )
                    # Only a chat kept by its list takes it; a chat kept by its history ignores the copy.
                    if not stored_ids or any(f'{id}-{message_id}' in stored_ids for message_id in listed):
                        chat = {**chat, 'history': {'messages': listed}}

                stored = self._without_history(chat_item.chat or {})
                updated = {**stored, **chat}
                if 'machine_id' in chat:
                    updated.pop('terminal_id', None)  # former name; would otherwise linger in the merge
                if 'history' in chat:
                    stored = {
                        **stored,
                        'history': {
                            'messages': await ChatMessages.get_messages_map_by_chat_id(id, db=session) or {},
                            'currentId': chat_item.current_message_id,
                        },
                    }
                    # The caller built its history from an earlier read; merge so messages saved since then survive.
                    updated['history'] = self.merge_history(stored.get('history'), chat['history'])
                    for mid, message in (stored.get('history', {}).get('messages') or {}).items():
                        if (message.get('user_id') or chat_item.user_id) != chat_item.user_id or (
                            message.get('role') == 'assistant'
                            and (
                                message.get('done') is False or updated['history']['messages'][mid].get('done') is False
                            )
                        ):
                            updated['history']['messages'][mid] = message
                    updated['history'] = self.merge_history(updated['history'], {})
                    self._repair_chat_current_id(updated)

                updated = self._clean_null_bytes(updated)
                chat_item.chat = self._without_history(updated)
                chat_item.title = updated.get('title', 'New Chat')
                if 'history' in chat:
                    chat_item.current_message_id = self.get_current_message_id(updated)

                if touch:
                    chat_item.updated_at = int(time.time())

                for mid in chat.get('history', {}).get('messages') or {}:
                    message = updated['history']['messages'].get(mid)
                    if message and message != (stored.get('history', {}).get('messages') or {}).get(mid):
                        await ChatMessages.upsert_message(
                            mid, id, message.get('user_id') or chat_item.user_id, message, db=session
                        )
                return ChatModel.model_validate(chat_item).model_copy(update={'chat': updated})
        except Exception:
            return

    async def update_chat_params_by_id(self, id: str, params: dict) -> ChatModel | None:
        async with self._chat_transaction(id) as (_, chat):
            if chat is None:
                return None

            stored = chat.chat or {}
            chat.chat = {
                **stored,
                'params': self._clean_null_bytes({**(stored.get('params') or {}), **params}),
            }
            return ChatModel.model_validate(chat)

    async def update_chat_variables_by_id(
        self,
        id: str,
        variables: dict | None,
        db: AsyncSession | None = None,
        *,
        touch: bool = True,
    ) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                chat_item = await session.get(Chat, id)
                if chat_item is None:
                    return None

                chat_item.variables = variables if isinstance(variables, dict) else {}
                if touch:
                    chat_item.updated_at = int(time.time())

                await session.commit()
                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    async def update_chat_last_read_at_by_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> tuple[int, bool] | None:
        try:
            async with get_async_db_context(db) as session:
                row = (
                    await session.execute(select(Chat.updated_at, Chat.last_read_at).filter_by(id=id, user_id=user_id))
                ).one_or_none()
                if row is None:
                    return None

                last_read_at = int(time.time())
                was_unread = row.last_read_at is None or row.updated_at > row.last_read_at
                await session.execute(update(Chat).filter_by(id=id).values(last_read_at=last_read_at))
                await session.commit()
                return last_read_at, was_unread
        except Exception:
            return None

    async def mark_chat_unread_by_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> ChatTitleIdResponse | None:
        try:
            async with get_async_db_context(db) as session:
                row = (
                    await session.execute(
                        select(Chat.title, Chat.updated_at, Chat.created_at).filter_by(id=id, user_id=user_id)
                    )
                ).one_or_none()
                if row is None:
                    return None

                await session.execute(update(Chat).filter_by(id=id).values(last_read_at=0))
                await session.commit()
                return ChatTitleIdResponse(
                    id=id,
                    title=row.title,
                    updated_at=row.updated_at,
                    created_at=row.created_at,
                    last_read_at=0,
                )
        except Exception:
            return None

    async def mark_chats_read_by_folder_ids(
        self, user_id: str, folder_ids: list[str], db: AsyncSession | None = None
    ) -> int:
        if not folder_ids:
            return 0

        async with get_async_db_context(db) as session:
            result = await session.execute(
                update(Chat)
                .where(
                    Chat.user_id == user_id,
                    Chat.folder_id.in_(folder_ids),
                    Chat.archived == False,
                    Chat.meta['internal'].as_boolean().is_not(True),
                )
                .values(last_read_at=Chat.updated_at)
            )
            await session.commit()
            return result.rowcount or 0

    async def mark_chats_read_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> int:
        async with get_async_db_context(db) as session:
            result = await session.execute(
                update(Chat)
                .where(
                    Chat.user_id == user_id,
                    Chat.archived == False,
                    Chat.meta['internal'].as_boolean().is_not(True),
                )
                .values(last_read_at=Chat.updated_at)
            )
            await session.commit()
            return result.rowcount or 0

    async def update_chat_title_by_id(
        self, id: str, title: str, *, expected_title: str | None = None
    ) -> ChatModel | None:
        try:
            async with self._chat_transaction(id) as (session, chat_item):
                if chat_item is None:
                    return None
                if expected_title is not None and chat_item.title != expected_title:
                    return None
                clean_title = self._clean_null_bytes(title)
                chat_item.title = clean_title
                chat_item.chat = {**(chat_item.chat or {}), 'title': clean_title}

                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    async def update_chat_tags_by_id(self, id: str, tags: list[str]) -> None:
        """Replace a chat's tags. Runs after every completion with tag generation enabled."""
        async with get_async_db_context() as session:
            owner_id = (await session.execute(select(Chat.user_id).filter_by(id=id))).scalar_one_or_none()
        if owner_id is not None:
            await Tags.set_resource_tags('chat', id, tags, owner_id)

    async def get_chat_title_by_id(self, id: str) -> str | None:
        async with get_async_db_context() as session:
            result = await session.execute(select(Chat.title).filter_by(id=id))
            row = result.first()
            if row is None:
                return None
            return row[0] or 'New Chat'

    @staticmethod
    def merge_history(existing_history: dict | None, incoming_history: dict | None) -> dict:
        existing = (existing_history or {}).get('messages') or {}
        incoming = (incoming_history or {}).get('messages') or {}
        merged = {
            message_id: {**message, 'childrenIds': []}
            for message_id, message in {**existing, **incoming}.items()
            if isinstance(message, dict)
        }

        for message_id, message in merged.items():
            parent_id = message.get('parentId')
            if parent_id in merged:
                merged[parent_id]['childrenIds'].append(message_id)

        current_id = (incoming_history or {}).get('currentId')
        if current_id not in merged:
            current_id = (existing_history or {}).get('currentId')
            if current_id not in merged:
                current_id = None

        return {**(existing_history or {}), **(incoming_history or {}), 'messages': merged, 'currentId': current_id}

    @staticmethod
    def delete_message_from_history(history: dict, message_id: str) -> set[str]:
        messages = history.get('messages') or {}
        message = messages.get(message_id)
        if not isinstance(message, dict):
            return set()

        parent_id = message.get('parentId')
        child_ids = [child_id for child_id in (message.get('childrenIds') or []) if child_id in messages]
        grandchild_ids = [
            grandchild_id
            for child_id in child_ids
            for grandchild_id in (messages.get(child_id, {}).get('childrenIds') or [])
            if grandchild_id in messages
        ]

        if parent_id in messages:
            messages[parent_id]['childrenIds'] = [
                child_id for child_id in (messages[parent_id].get('childrenIds') or []) if child_id != message_id
            ] + grandchild_ids

        for grandchild_id in grandchild_ids:
            messages[grandchild_id]['parentId'] = parent_id

        deleted_ids = {message_id, *child_ids}
        for deleted_id in deleted_ids:
            messages.pop(deleted_id, None)

        current_id = parent_id
        child_ids = (
            [child_id for child_id, child in messages.items() if child.get('parentId') is None]
            if current_id is None
            else messages.get(current_id, {}).get('childrenIds', [])
        )
        visited_ids = set()
        while child_ids and child_ids[-1] not in visited_ids:
            current_id = child_ids[-1]
            visited_ids.add(current_id)
            child_ids = messages.get(current_id, {}).get('childrenIds', [])
        history['currentId'] = current_id if current_id in messages else None
        return deleted_ids

    @staticmethod
    def upsert_message_to_history(history: dict, message_id: str, message: dict) -> dict:
        messages = history.setdefault('messages', {})

        if message_id in messages:
            # Voice updates must not replace approval-resume metadata, and approval
            # pauses must retain speech and response timing already attached to this turn.
            existing_meta = messages[message_id].get('meta')
            existing_meta = existing_meta if isinstance(existing_meta, dict) else {}
            incoming_meta = message.get('meta')
            if isinstance(incoming_meta, dict):
                if set(incoming_meta) <= {'voice', 'task_id', 'response_started_at', 'response_ended_at'}:
                    message = {**message, 'meta': {**existing_meta, **incoming_meta}}
                else:
                    message = {
                        **message,
                        'meta': {
                            **{
                                key: existing_meta[key]
                                for key in ('voice', 'task_id', 'response_started_at', 'response_ended_at')
                                if key in existing_meta
                            },
                            **incoming_meta,
                        },
                    }
            messages[message_id] = {
                **messages[message_id],
                **message,
            }
        else:
            message_parent_id = message.get('parentId')
            parent_id = message_parent_id
            if parent_id is None:
                for existing_id, existing_message in messages.items():
                    if message_id in existing_message.get('childrenIds', []):
                        parent_id = existing_id
                        break

            parent = messages.get(parent_id) if parent_id else None
            output = message.get('output') or []
            output_role = next(
                (item.get('role') for item in output if isinstance(item, dict) and item.get('role')),
                None,
            )
            role = message.get('role') or output_role
            if not role:
                parent_role = parent.get('role') if parent else None
                if parent_role == 'user':
                    role = 'assistant'
                elif parent_role == 'assistant':
                    role = 'user'
                else:
                    role = 'assistant'

            messages[message_id] = {
                **message,
                'id': message.get('id') or message_id,
                'parentId': message_parent_id if message_parent_id is not None else parent_id,
                'childrenIds': (message.get('childrenIds') if isinstance(message.get('childrenIds'), list) else []),
                'role': role,
                'timestamp': message.get('timestamp') or int(time.time()),
            }
            history['currentId'] = message_id

        ChatTable._add_child_id_to_parent(messages, messages[message_id].get('parentId'), message_id)
        return messages[message_id]

    async def get_messages_map_by_chat_id(self, id: str) -> dict | None:
        """Message map for walking history (see ``get_message_list``)."""
        return await ChatMessages.get_messages_map_by_chat_id(id)

    async def get_message_by_id_and_message_id(self, id: str, message_id: str) -> dict | None:
        messages_map = await ChatMessages.get_messages_map_by_message_ids(id, [message_id])
        return messages_map.get(message_id)

    async def get_message_metadata(
        self,
        chat_id: str,
        message_id: str,
        metadata_key: Literal['files', 'sources', 'embeds'],
    ) -> Any | None:
        """Read one message metadata field without rebuilding the whole history."""
        async with get_async_db_context() as db:
            # Read the column directly; some stored rows cannot be validated as full ChatMessageModel objects.
            result = await db.execute(
                select(getattr(ChatMessage, metadata_key)).where(ChatMessage.id == f'{chat_id}-{message_id}')
            )
            metadata_row = result.first()

        if metadata_row is not None:
            return metadata_row[0]

    async def insert_chat_turn(self, chat_id, user, user_message, message_ids):
        from fastapi import HTTPException

        if not await self.has_chat_access(chat_id, user, permission='write'):
            raise HTTPException(403, 'Chat continuation is not allowed.')
        async with self._chat_transaction(chat_id) as (db, chat):
            if not chat:
                raise HTTPException(404, 'Chat not found.')
            user_message_id = user_message.get('id')
            assistant_ids = [assistant_message.get('message_id') for assistant_message in message_ids]
            ids = [user_message_id, *assistant_ids] if user_message else assistant_ids
            if not all(isinstance(mid, str) and mid for mid in ids) or len(set(ids)) != len(ids):
                raise HTTPException(409, 'Message already exists or has an invalid ID.')
            messages = await ChatMessages.get_messages_map_by_message_ids(chat_id, ids, db=db)
            history = {'messages': messages, 'currentId': chat.current_message_id}
            # An empty reply may be prepared before the request.
            for mid in assistant_ids:
                existing_reply = messages.get(mid)
                if existing_reply and (
                    existing_reply.get('role') != 'assistant'
                    or existing_reply.get('done')
                    or existing_reply.get('content')
                    or existing_reply.get('output')
                    or (existing_reply.get('user_id') or chat.user_id) != user.id
                    or (user_message and existing_reply.get('parentId') != user_message_id)
                ):
                    raise HTTPException(409, 'Message already exists or has an invalid ID.')
            turn = {}
            parent_id = None
            if user_message:
                existing = messages.get(user_message_id)
                if existing and existing.get('role') != 'user':
                    raise HTTPException(403, 'You can only regenerate replies to user messages.')
                parent_id = existing.get('parentId') if existing else user_message.get('parentId')
                if parent_id is not None:
                    messages.update(await ChatMessages.get_messages_map_by_message_ids(chat_id, [parent_id], db=db))
                if parent_id is not None and parent_id not in messages:
                    raise HTTPException(409, 'Parent message no longer exists.')
                message = existing or (
                    dict(user_message)
                    if chat.user_id == user.id
                    else {key: user_message[key] for key in ('content', 'files', 'models') if key in user_message}
                )
                if not existing:
                    message.update(
                        id=user_message_id,
                        parentId=parent_id,
                        role='user',
                        childrenIds=[],
                        timestamp=int(time.time()),
                        user_id=user.id,
                        user={'id': user.id, 'name': user.name},
                    )
                elif 'models' in user_message and (existing.get('user_id') or chat.user_id) == user.id:
                    message = {**existing, 'models': user_message['models']}
                turn[user_message_id] = self.upsert_message_to_history(
                    history, user_message_id, self._clean_null_bytes(message)
                )
            for assistant_message in message_ids:
                mid = assistant_message['message_id']
                turn[mid] = self.upsert_message_to_history(
                    history,
                    mid,
                    {
                        'id': mid,
                        'parentId': user_message_id,
                        'childrenIds': [],
                        'role': 'assistant',
                        'content': '',
                        'done': False,
                        'model': assistant_message['model_id'],
                        'modelIdx': assistant_message.get('modelIdx'),
                        'timestamp': int(time.time()),
                        'user_id': user.id,
                        'meta': assistant_message['meta'],
                        **({'modelName': assistant_message['modelName']} if assistant_message['modelName'] else {}),
                    },
                )
            chat.current_message_id = history['currentId']
            chat.updated_at = int(time.time())
            for mid, message in turn.items():
                await ChatMessages.upsert_message(mid, chat_id, message.get('user_id') or chat.user_id, message, db=db)
            if parent_id:
                turn[parent_id] = history['messages'][parent_id]
                if not existing:
                    await ChatMessages.upsert_message(parent_id, chat_id, chat.user_id, turn[parent_id], db=db)
            return {'messages': turn, 'currentId': history['currentId']}

    async def upsert_message_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, message: dict, *, touch: bool = True
    ) -> ChatModel | None:
        if not message.get('content'):
            output_text = get_output_text(message.get('output'))
            if output_text:
                message['content'] = output_text

        message = self._clean_null_bytes(message)
        message_id = self._clean_null_bytes(message_id)

        try:
            async with self._chat_transaction(id) as (session, chat_item):
                if chat_item is None:
                    return None

                messages = await ChatMessages.get_messages_map_by_message_ids(id, [message_id], db=session)
                is_new = message_id not in messages
                if is_new and message.get('parentId'):
                    messages = await ChatMessages.get_messages_map_by_message_ids(id, [message['parentId']], db=session)
                elif is_new:
                    messages = await ChatMessages.get_messages_map_by_chat_id(id, db=session) or {}
                history = {'messages': messages, 'currentId': chat_item.current_message_id}
                saved_message = self.upsert_message_to_history(history, message_id, message)
                saved_ids = [message_id, saved_message.get('parentId')] if is_new else [message_id]
                for mid in saved_ids:
                    if mid in messages:
                        await ChatMessages.upsert_message(
                            mid, id, messages[mid].get('user_id') or chat_item.user_id, messages[mid], db=session
                        )
                chat_item.current_message_id = history['currentId']

                if touch:
                    chat_item.updated_at = int(time.time())

                updated_chat = ChatModel.model_validate(chat_item)

            return updated_chat
        except Exception:
            return None

    async def delete_message_from_chat_by_id_and_message_id(self, id: str, message_id: str) -> ChatModel | None:
        try:
            async with self._chat_transaction(id) as (session, chat_item):
                if chat_item is None:
                    return None

                chat = {
                    **(chat_item.chat or {}),
                    'history': {
                        'messages': await ChatMessages.get_messages_map_by_chat_id(id, db=session) or {},
                        'currentId': chat_item.current_message_id,
                    },
                }
                self._repair_chat_current_id(chat)

                history = chat.get('history', {})
                parent_id = ((history.get('messages') or {}).get(message_id) or {}).get('parentId')
                deleted_ids = self.delete_message_from_history(history, message_id)
                await ChatMessages.delete_message_ids_by_chat_id(id, deleted_ids, db=session)
                if not deleted_ids:
                    chat_item.current_message_id = self.get_current_message_id(chat)

                    return ChatModel.model_validate(chat_item).model_copy(update={'chat': chat})

                for mid, message in (history.get('messages') or {}).items():
                    if message.get('parentId') == parent_id or mid == parent_id:
                        await ChatMessages.upsert_message(
                            mid, id, message.get('user_id') or chat_item.user_id, message, db=session
                        )

                chat_item.current_message_id = self.get_current_message_id(chat)
                chat_item.updated_at = int(time.time())

                updated_chat = ChatModel.model_validate(chat_item).model_copy(update={'chat': chat})

            return updated_chat
        except Exception:
            return None

    async def add_message_status_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, status: dict
    ) -> ChatModel | None:
        try:
            status = self._clean_null_bytes(status)
            async with self._chat_transaction(id) as (session, chat_item):
                if chat_item is None:
                    return None

                history = {'messages': await ChatMessages.get_messages_map_by_message_ids(id, [message_id], db=session)}

                if message_id in history.get('messages', {}):
                    status_history = history['messages'][message_id].get('statusHistory', [])
                    status_history.append(status)
                    history['messages'][message_id]['statusHistory'] = status_history
                    message = history['messages'][message_id]
                    await ChatMessages.upsert_message(
                        message_id, id, message.get('user_id') or chat_item.user_id, message, db=session
                    )

                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    async def add_message_files_by_id_and_message_id(
        self, id: str, message_id: str, files: list[dict]
    ) -> list[dict] | None:
        async with self._chat_transaction(id) as (session, chat_item):
            if chat_item is None:
                return None

            history = {'messages': await ChatMessages.get_messages_map_by_message_ids(id, [message_id], db=session)}

            message_files = []

            if message_id in history.get('messages', {}):
                message_files = history['messages'][message_id].get('files', [])
                message_files = message_files + files
                history['messages'][message_id]['files'] = message_files
                message = history['messages'][message_id]
                await ChatMessages.upsert_message(
                    message_id,
                    id,
                    message.get('user_id') or chat_item.user_id,
                    self._clean_null_bytes(message),
                    db=session,
                )

            chat_item.updated_at = int(time.time())

            return message_files

    async def insert_shared_chat_by_chat_id(self, chat_id: str, db: AsyncSession | None = None) -> ChatModel | None:
        """Create a shared snapshot for a chat. Returns the original chat with share_id set."""
        from open_webui.models.shared_chats import SharedChats

        async with get_async_db_context(db) as session:
            chat = await session.get(Chat, chat_id)
            if not chat:
                return None

            # If already shared, just update the existing snapshot
            if chat.share_id:
                return await self.update_shared_chat_by_chat_id(chat_id, db=session)

            shared = await SharedChats.create(chat_id, chat.user_id, db=session)
            if not shared:
                return None

            # Set share_id on the original chat
            chat.share_id = shared.id
            await session.commit()
            return ChatModel.model_validate(chat)  # return the updated original

    # refresh helper
    async def update_shared_chat_by_chat_id(
        self,
        chat_id: str,
        db: AsyncSession | None = None,
    ) -> ChatModel | None:
        """Refresh the shared snapshot with current chat content."""
        from open_webui.models.shared_chats import SharedChats

        async with get_async_db_context(db) as session:
            record = await session.get(Chat, chat_id)
            if not record or not record.share_id:
                return await self.insert_shared_chat_by_chat_id(chat_id, db=session)
            await SharedChats.update(record.share_id, db=session)
            return ChatModel.model_validate(record)
        # unreachable — context manager above always returns
        return

    async def delete_shared_chat_by_chat_id(self, chat_id: str, db: AsyncSession | None = None) -> bool:
        """Delete shared snapshot for a chat."""
        from open_webui.models.shared_chats import SharedChats

        try:
            return await SharedChats.delete_by_chat_id(chat_id, db=db)
        except Exception:
            return False

    async def unarchive_all_chats_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(update(Chat).filter_by(user_id=user_id).values(archived=False))
                await session.commit()
                return True
        except Exception:
            return False

    async def update_chat_share_id_by_id(
        self, id: str, share_id: str | None, db: AsyncSession | None = None
    ) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                chat.share_id = share_id
                await session.commit()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def toggle_chat_pinned_by_id(self, id: str, db: AsyncSession | None = None) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                chat.pinned = not chat.pinned
                await session.commit()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def toggle_chat_archive_by_id(self, id: str, db: AsyncSession | None = None) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                chat.archived = not chat.archived
                chat.folder_id = None
                await session.commit()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def archive_all_chats_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(update(Chat).filter_by(user_id=user_id).values(archived=True, folder_id=None))
                await session.commit()
                return True
        except Exception:
            return False

    async def get_archived_chat_list_by_user_id(
        self,
        user_id: str,
        filter: dict | None = None,
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at).filter_by(
                user_id=user_id, archived=True
            )
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))

            if filter:
                query_key = filter.get('query')
                if query_key:
                    stmt = stmt.filter(Chat.title.ilike(f'%{query_key}%'))

                order_by = filter.get('order_by')
                direction = filter.get('direction')

                if order_by and direction:
                    if not getattr(Chat, order_by, None):
                        raise ValueError('Invalid order_by field')

                    if direction.lower() == 'asc':
                        stmt = stmt.order_by(getattr(Chat, order_by).asc(), Chat.id)
                    elif direction.lower() == 'desc':
                        stmt = stmt.order_by(getattr(Chat, order_by).desc(), Chat.id)
                    else:
                        raise ValueError('Invalid direction for ordering')
            else:
                stmt = stmt.order_by(Chat.updated_at.desc(), Chat.id)

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            all_chats = result.all()
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        'id': chat[0],
                        'title': chat[1],
                        'updated_at': chat[2],
                        'created_at': chat[3],
                    }
                )
                for chat in all_chats
            ]

    async def count_archived_chats_by_user_id(
        self,
        user_id: str,
        db: AsyncSession | None = None,
    ) -> int:
        async with get_async_db_context(db) as session:
            stmt = select(func.count(Chat.id)).filter_by(user_id=user_id, archived=True)
            result = await session.execute(stmt.where(Chat.meta['internal'].as_boolean().is_not(True)))
            return result.scalar() or 0

    async def get_shared_chat_list_by_user_id(
        self,
        user_id: str,
        filter: dict | None = None,
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[SharedChatResponse]:
        """Delegate to SharedChats for listing shared chats by user."""
        from open_webui.models.shared_chats import SharedChats

        return await SharedChats.get_by_user_id(user_id, filter=filter, skip=skip, limit=limit, db=db)

    async def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        filter: dict | None = None,
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at).filter_by(
                user_id=user_id
            )
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))
            if not include_archived:
                stmt = stmt.filter_by(archived=False)

            if filter:
                query_key = filter.get('query')
                if query_key:
                    stmt = stmt.filter(Chat.title.ilike(f'%{query_key}%'))

                order_by = filter.get('order_by')
                direction = filter.get('direction')

                if order_by and direction and getattr(Chat, order_by):
                    if direction.lower() == 'asc':
                        stmt = stmt.order_by(getattr(Chat, order_by).asc(), Chat.id)
                    elif direction.lower() == 'desc':
                        stmt = stmt.order_by(getattr(Chat, order_by).desc(), Chat.id)
                    else:
                        raise ValueError('Invalid direction for ordering')
            else:
                stmt = stmt.order_by(Chat.updated_at.desc(), Chat.id)

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            all_chats = result.all()
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        'id': chat[0],
                        'title': chat[1],
                        'updated_at': chat[2],
                        'created_at': chat[3],
                        'last_read_at': chat[4],
                    }
                )
                for chat in all_chats
            ]

    async def get_chat_title_id_list_by_user_id(
        self,
        user_id: str,
        status: str = 'active',  # 'active', 'archived' or 'all'
        include_folders: bool = False,
        include_pinned: bool = False,
        sort_by: str = 'updated_at',
        sort_dir: str = 'desc',
        skip: int | None = None,
        limit: int | None = None,
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as session:
            stmt = select(
                Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at, Chat.archived
            ).filter_by(user_id=user_id)
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))

            if not include_folders:
                stmt = stmt.filter_by(folder_id=None)

            if not include_pinned:
                stmt = stmt.filter(or_(Chat.pinned == False, Chat.pinned == None))

            if status == 'archived':
                stmt = stmt.filter_by(archived=True)
            elif status != 'all':
                stmt = stmt.filter_by(archived=False)

            stmt = stmt.order_by(*chat_list_order(sort_by, sort_dir))

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            all_chats = result.all()

            return [
                ChatTitleIdResponse.model_validate(
                    {
                        'id': chat[0],
                        'title': chat[1],
                        'updated_at': chat[2],
                        'created_at': chat[3],
                        'last_read_at': chat[4],
                        'archived': bool(chat[5]),
                    }
                )
                for chat in all_chats
            ]

    async def get_chat_list_by_chat_ids(
        self,
        chat_ids: list[str],
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[ChatModel]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat).filter(Chat.id.in_(chat_ids)).filter_by(archived=False)
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))
            result = await session.execute(stmt.order_by(Chat.updated_at.desc()))
            all_chats = result.scalars().all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chat_metas_by_chat_ids(
        self,
        chat_ids: list[str],
        include_archived: bool = False,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat.meta).filter(Chat.id.in_(chat_ids))
            if not include_archived:
                stmt = stmt.filter_by(archived=False)

            result = await session.execute(stmt)
            return [meta for meta in result.scalars().all() if isinstance(meta, dict)]

    async def get_owner_ids_by_chat_ids(self, chat_ids: list[str], db: AsyncSession | None = None) -> dict[str, str]:
        if not chat_ids:
            return {}
        async with get_async_db_context(db) as session:
            result = await session.execute(select(Chat.id, Chat.user_id).filter(Chat.id.in_(chat_ids)))
            return dict(result.all())

    async def get_chats_by_model_id(
        self,
        model_id: str,
        filter: dict | None = None,
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> dict:
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            chat_ids = (
                select(ChatMessage.chat_id).filter(ChatMessage.model_id == model_id).group_by(ChatMessage.chat_id)
            )

            if filter:
                if filter.get('start_date'):
                    chat_ids = chat_ids.filter(ChatMessage.created_at >= filter.get('start_date'))
                if filter.get('end_date'):
                    chat_ids = chat_ids.filter(ChatMessage.created_at <= filter.get('end_date'))
                if filter.get('group_id'):
                    from open_webui.models.groups import group_user_memberships

                    group_users = select(group_user_memberships([filter['group_id']], True).c.user_id).scalar_subquery()
                    chat_ids = chat_ids.filter(ChatMessage.user_id.in_(group_users))

            chat_ids = chat_ids.subquery()

            stmt = (
                select(Chat.id, Chat.user_id, Chat.title, Chat.updated_at, User.name.label('user_name'))
                .join(chat_ids, chat_ids.c.chat_id == Chat.id)
                .outerjoin(User, User.id == Chat.user_id)
                .where(Chat.meta['internal'].as_boolean().is_not(True))
            )

            order_by = filter.get('order_by') if filter else None
            direction = filter.get('direction') if filter else None
            is_asc = direction == 'asc'

            if order_by == 'title':
                primary_sort = Chat.title.asc() if is_asc else Chat.title.desc()
            elif order_by == 'user_name':
                primary_sort = User.name.asc() if is_asc else User.name.desc()
            else:
                primary_sort = Chat.updated_at.asc() if is_asc else Chat.updated_at.desc()

            stmt = stmt.order_by(primary_sort, Chat.id.asc())

            count_result = await session.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            return {
                'items': [
                    {
                        'chat_id': chat.id,
                        'user_id': chat.user_id,
                        'user_name': chat.user_name,
                        'first_message': chat.title,
                        'updated_at': chat.updated_at,
                    }
                    for chat in result.all()
                ],
                'total': total,
            }

    # retrieve conversation
    async def get_chat_by_id(
        self,
        id: str,
        db: AsyncSession | None = None,
    ) -> ChatModel | None:
        """Fetch a chat by PK, auto-sanitizing null bytes on read."""
        try:
            async with get_async_db_context(db) as session:
                chat_item = await session.get(Chat, id)
                if chat_item is None:
                    return None

                model = await self._with_history(chat_item, db=session)
                model.chat = self._clean_null_bytes(model.chat)
                self._repair_chat_current_id(model.chat)
                return model

        except Exception:
            return None

    async def get_chat_metadata_by_id(self, id: str) -> Row | None:
        """
        Fetch only the id, user_id, meta, folder_id and current_message_id columns
        for a chat, without loading the full JSON blob.
        """
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(Chat.id, Chat.user_id, Chat.meta, Chat.folder_id, Chat.current_message_id).filter_by(id=id)
                )
                return result.first()
        except Exception:
            return None

    async def get_chat_by_share_id(self, id: str, db: AsyncSession | None = None) -> ChatModel | None:
        """Look up a shared chat snapshot by its share token."""
        from open_webui.models.shared_chats import SharedChats

        try:
            shared = await SharedChats.get_by_id(id, db=db)
            if shared:
                # Return a ChatModel-compatible view of the snapshot
                return ChatModel(
                    id=shared.id,
                    user_id=shared.user_id,
                    title=shared.title,
                    chat=shared.chat,
                    created_at=shared.created_at,
                    updated_at=shared.updated_at,
                    share_id=shared.id,
                )
            return None
        except Exception:
            return None

    async def get_chat_by_id_and_user_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                result = await session.execute(select(Chat).filter_by(id=id, user_id=user_id))
                chat = result.scalars().first()
                if not chat:
                    return None

                model = await self._with_history(chat, db=session)
                model.chat = self._clean_null_bytes(model.chat)
                self._repair_chat_current_id(model.chat)
                return model

        except Exception:
            return None

    async def get_accessible_chat_by_id(
        self,
        id: str,
        user,
        db: AsyncSession | None = None,
        *,
        permission: Literal['read', 'write'] = 'read',
        chat: Chat | ChatModel | None = None,
    ) -> ChatModel | None:
        if user.role not in {'user', 'admin'}:
            return None
        chat = chat if chat is not None else await self.get_chat_by_id(id, db=db)
        if chat and await self.has_chat_access(id, user, db=db, permission=permission, chat=chat):
            return ChatModel.model_validate(chat)
        return None

    async def has_chat_access(
        self,
        id: str,
        user,
        db: AsyncSession | None = None,
        *,
        permission: Literal['read', 'write'] = 'read',
        chat: Chat | ChatModel | Row | None = None,
    ) -> bool:
        if user.role not in {'user', 'admin'}:
            return False
        if chat is None:
            async with get_async_db_context(db) as session:
                result = await session.execute(select(Chat.user_id, Chat.meta, Chat.folder_id).filter_by(id=id))
                chat = result.first()
        if not chat:
            return False
        if chat.user_id == user.id or user.role == 'admin' and permission == 'read' and ENABLE_ADMIN_CHAT_ACCESS:
            return True
        from open_webui.models.shared_chats import SharedChats

        shared = await SharedChats.get_by_chat_id(id, db=db)
        if (
            shared
            and shared.chat.get('share_mode') == 'continue'
            and await AccessGrants.has_access(
                user_id=user.id, resource_type='shared_chat', resource_id=id, permission='read', db=db
            )
        ):
            return True
        if chat.folder_id:
            from open_webui.utils.access_control.folders import has_folder_access

            folder = await Folders.get_folder_by_id(chat.folder_id, db=db)
            if (
                folder
                and (permission == 'read' or (folder.data or {}).get('share_mode') == 'continue')
                and await has_folder_access(user.id, folder, permission, db)
            ):
                return True
        # A run chat is readable by anyone the automation is shared with.
        automation_id = (chat.meta or {}).get('automation_id')
        if automation_id and permission == 'read':
            from open_webui.models.automations import Automations
            from open_webui.utils.access_control.automations import has_automation_access

            automation = await Automations.get_by_id(automation_id, db=db)
            if (
                automation
                and automation.user_id == chat.user_id
                and await has_automation_access(user, automation, 'read', db=db)
            ):
                return True
        return False

    async def filter_task_ids_by_user_id(self, chat, user_id: str, task_ids: list[str]) -> list[str]:
        if not task_ids:
            return []
        actors = {
            (m.get('meta') or {}).get('task_id'): m.get('user_id') or chat.user_id
            for m in (chat.chat.get('history', {}).get('messages') or {}).values()
        }
        return [task_id for task_id in task_ids if actors.get(task_id, chat.user_id) == user_id]

    async def is_chat_owner(self, id: str, user_id: str, db: AsyncSession | None = None) -> bool:
        """
        Lightweight ownership check — uses EXISTS subquery instead of loading
        the full Chat row (which includes the potentially large JSON blob).
        """
        try:
            async with get_async_db_context(db) as session:
                result = await session.execute(select(exists().where(and_(Chat.id == id, Chat.user_id == user_id))))
                return result.scalar()
        except Exception:
            return False

    async def get_chat_folder_id(self, id: str, user_id: str, db: AsyncSession | None = None) -> str | None:
        """
        Fetch only the folder_id column for a chat, without loading the full
        JSON blob. Returns None if chat doesn't exist or doesn't belong to user.
        """
        try:
            async with get_async_db_context(db) as session:
                result = await session.execute(select(Chat.folder_id).filter_by(id=id, user_id=user_id))
                row = result.first()
                return row[0] if row else None
        except Exception:
            return None

    async def count_unread_by_folder_ids(
        self,
        user_id: str,
        folder_ids: list[str],
        db: AsyncSession | None = None,
    ) -> dict[str, int]:
        """Count unread or approval-pending chats for folder notification badges."""
        if not folder_ids:
            return {}

        unfinished_assistant = (
            select(ChatMessage.id)
            .where(ChatMessage.chat_id == Chat.id)
            .where(ChatMessage.role == 'assistant')
            .where(ChatMessage.done.is_(False))
            .exists()
        )

        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(Chat.folder_id, func.count(Chat.id))
                .where(
                    Chat.user_id == user_id,
                    Chat.folder_id.in_(folder_ids),
                    Chat.archived == False,
                    Chat.updated_at > func.coalesce(Chat.last_read_at, 0),
                    ~unfinished_assistant,
                )
                .group_by(Chat.folder_id)
            )
            counts = {folder_id: count for folder_id, count in result.all() if folder_id}
            result = await session.execute(
                select(Chat.folder_id, Chat.id, ChatMessage.output)
                .join(ChatMessage, ChatMessage.chat_id == Chat.id)
                .where(
                    Chat.user_id == user_id,
                    Chat.folder_id.in_(folder_ids),
                    Chat.archived == False,
                    ChatMessage.role == 'assistant',
                    ChatMessage.done.is_(False),
                )
            )
            # Unfinished chats are excluded above; count each approval-pending chat once.
            pending_chats = {
                (folder_id, chat_id) for folder_id, chat_id, output in result.all() if has_pending_tool_approval(output)
            }
            for folder_id, _ in pending_chats:
                counts[folder_id] = counts.get(folder_id, 0) + 1
            return counts

    async def get_active_chats(
        self, user_id: str, folder_ids: list[str], db: AsyncSession | None = None
    ) -> dict[str, tuple[str, bool, int]]:
        """Chats with an unfinished reply: their folder, whether it waits for an approval or answer, and when they changed."""
        if not folder_ids:
            return {}
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(Chat.id, Chat.folder_id, Chat.updated_at, ChatMessage.output)
                .join(ChatMessage, ChatMessage.chat_id == Chat.id)
                .where(
                    Chat.user_id == user_id,
                    Chat.folder_id.in_(folder_ids),
                    Chat.archived == False,
                    Chat.meta['internal'].as_boolean().is_not(True),
                    ChatMessage.role == 'assistant',
                    ChatMessage.done.is_(False),
                )
            )
            active_chats: dict[str, tuple[str, bool, int]] = {}
            for chat_id, folder_id, updated_at, output in result.all():
                waiting = active_chats.get(chat_id, (folder_id, False, 0))[1]
                active_chats[chat_id] = (folder_id, waiting or has_pending_tool_approval(output), updated_at)
            return active_chats

    async def get_chats(self, skip: int = 0, limit: int = 50, db: AsyncSession | None = None) -> list[ChatModel]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat).where(Chat.meta['internal'].as_boolean().is_not(True))
            result = await session.execute(stmt.order_by(Chat.updated_at.desc()))
            all_chats = result.scalars().all()
            return await self._with_histories(all_chats, db=session)

    async def get_user_usage_chat_stats(self, user_id: str, db: AsyncSession | None = None) -> dict:
        async with get_async_db_context(db) as session:
            chat_filter = (Chat.user_id == user_id, Chat.meta['internal'].as_boolean().is_not(True))
            result = await session.execute(select(func.count(Chat.id).label('total_chats')).where(*chat_filter))
            total_chats = int(result.scalar() or 0)

            messages_stmt = (
                select(ChatMessage.chat_id, ChatMessage.created_at)
                .join(Chat, Chat.id == ChatMessage.chat_id)
                .where(*chat_filter, ChatMessage.created_at.isnot(None))
                .order_by(ChatMessage.chat_id, ChatMessage.created_at.asc())
            )
            messages_result = await session.execute(messages_stmt)
            last_message_at_by_chat: dict[str, int] = {}
            active_seconds_by_chat: dict[str, int] = {}

            for chat_id, created_at in messages_result.all():
                timestamp = int(created_at / 1000) if created_at > 10_000_000_000 else int(created_at)
                last_message_at = last_message_at_by_chat.get(chat_id)
                if last_message_at is not None:
                    delta = timestamp - last_message_at
                    if 0 < delta <= ACTIVE_CHAT_GAP_SECONDS:
                        active_seconds_by_chat[chat_id] = active_seconds_by_chat.get(chat_id, 0) + delta
                last_message_at_by_chat[chat_id] = timestamp

            return {
                'total_chats': total_chats,
                'longest_chat_seconds': max(active_seconds_by_chat.values(), default=0),
            }

    # list user conversations
    async def get_chats_by_user_id(
        self,
        user_id: str,
        filter: dict | None = None,
        skip: int | None = None,
        limit: int | None = None,
        db: AsyncSession | None = None,
    ) -> ChatListResponse:
        async with get_async_db_context(db) as session:
            stmt = select(Chat).filter_by(user_id=user_id)
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))

            if filter:
                if filter.get('updated_at'):
                    stmt = stmt.filter(Chat.updated_at > filter.get('updated_at'))

                order_by = filter.get('order_by')
                direction = filter.get('direction')

                if order_by and direction:
                    if hasattr(Chat, order_by):
                        if direction.lower() == 'asc':
                            stmt = stmt.order_by(getattr(Chat, order_by).asc(), Chat.id)
                        elif direction.lower() == 'desc':
                            stmt = stmt.order_by(getattr(Chat, order_by).desc(), Chat.id)
                else:
                    stmt = stmt.order_by(Chat.updated_at.desc(), Chat.id)

            else:
                stmt = stmt.order_by(Chat.updated_at.desc(), Chat.id)

            count_result = await session.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            if skip is not None:
                stmt = stmt.offset(skip)
            if limit is not None:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            all_chats = result.scalars().all()

            return ChatListResponse(
                **{
                    'items': await self._with_histories(all_chats, db=session),
                    'total': total,
                }
            )

    # list pinned chats
    async def get_pinned_chats_by_user_id(
        self, user_id: str, db: AsyncSession | None = None
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at).filter_by(
                user_id=user_id, pinned=True, archived=False
            )
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))
            result = await session.execute(stmt.order_by(Chat.updated_at.desc()))
            all_chats = result.all()
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        'id': chat[0],
                        'title': chat[1],
                        'updated_at': chat[2],
                        'created_at': chat[3],
                        'last_read_at': chat[4],
                    }
                )
                for chat in all_chats
            ]

    async def get_archived_chats_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> list[ChatModel]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat).filter_by(user_id=user_id, archived=True)
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))
            result = await session.execute(stmt.order_by(Chat.updated_at.desc()))
            return await self._with_histories(result.scalars().all(), db=session)

    # search user conversations
    async def get_chats_by_user_id_and_search_text(  # noqa: C901
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        """
        Search chats without loading their bodies, with pagination applied in SQL.
        """
        search_text = sanitize_text_for_db(search_text).lower().strip()

        if not search_text:
            return await self.get_chat_list_by_user_id(
                user_id, include_archived, filter={}, skip=skip, limit=limit, db=db
            )

        search_text_words = search_text.split()

        # search_text might contain 'tag:tag_name' format so we need to extract the tag_name
        tag_ids = [
            word.replace('tag:', '').replace(' ', '_').lower() for word in search_text_words if word.startswith('tag:')
        ]

        # Extract folder names
        folder_names = [word.replace('folder:', '') for word in search_text_words if word.startswith('folder:')]
        folders = await Folders.search_folders_by_names(user_id, folder_names)
        folder_ids = [folder.id for folder in folders]

        is_pinned = None
        if 'pinned:true' in search_text_words:
            is_pinned = True
        elif 'pinned:false' in search_text_words:
            is_pinned = False

        is_archived = None
        if 'archived:true' in search_text_words:
            is_archived = True
        elif 'archived:false' in search_text_words:
            is_archived = False

        is_shared = None
        if 'shared:true' in search_text_words:
            is_shared = True
        elif 'shared:false' in search_text_words:
            is_shared = False

        search_text_words = [word for word in search_text_words if not word.startswith(CHAT_SEARCH_FILTER_PREFIXES)]

        phrase_query = ' '.join(search_text_words).strip()
        # A single-word query is already fully covered by the phrase match
        search_terms = [term for term in chat_search_terms(phrase_query) if term != phrase_query]

        async with get_async_db_context(db) as session:
            stmt = select(
                Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at, Chat.archived
            ).filter(Chat.user_id == user_id)
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))

            if is_archived is not None:
                stmt = stmt.filter(Chat.archived == is_archived)
            elif not include_archived:
                stmt = stmt.filter(Chat.archived == False)

            if is_pinned is not None:
                stmt = stmt.filter(Chat.pinned == is_pinned)

            if is_shared is not None:
                if is_shared:
                    stmt = stmt.filter(Chat.share_id.isnot(None))
                else:
                    stmt = stmt.filter(Chat.share_id.is_(None))

            if folder_names:
                stmt = stmt.filter(Chat.folder_id.in_(folder_ids))

            # Check if the database dialect is either 'sqlite' or 'postgresql'
            bind = await session.connection()
            dialect_name = bind.dialect.name

            search_params = {}
            exact_match_clause = None
            if phrase_query:
                exact_match_clause = or_(
                    Chat.title.ilike(bindparam('phrase_title_key')),
                    text(chat_search_message_content_match_sql(dialect_name, 'phrase_content_key')),
                )
                search_params.update(
                    {
                        'phrase_title_key': f'%{phrase_query}%',
                        'phrase_content_key': phrase_query,
                    }
                )

                term_clauses = []
                for term_idx, term in enumerate(search_terms):
                    title_key = f'term_title_key_{term_idx}'
                    content_key = f'term_content_key_{term_idx}'
                    term_clauses.append(
                        or_(
                            Chat.title.ilike(bindparam(title_key)),
                            text(chat_search_message_content_match_sql(dialect_name, content_key)),
                        )
                    )
                    search_params[title_key] = f'%{term}%'
                    search_params[content_key] = term

                if term_clauses:
                    stmt = stmt.filter(or_(exact_match_clause, and_(*term_clauses)))
                else:
                    stmt = stmt.filter(exact_match_clause)

            # Every tag must match, unless 'none' asks for untagged chats.
            for tag_id in ['none'] if 'none' in tag_ids else tag_ids:
                stmt = stmt.filter(resource_tag_filter('chat', Chat.id, [tag_id]))

            if dialect_name == 'postgresql':
                # Safety filter: JSON field must not contain \u0000
                stmt = stmt.filter(text("Chat.chat::text NOT LIKE '%\\\\u0000%'"))

                # Safety filter: title must not contain actual null bytes
                stmt = stmt.filter(text("Chat.title::text NOT LIKE '%\\x00%'"))

            if exact_match_clause is not None:
                stmt = stmt.order_by(case((exact_match_clause, 0), else_=1), Chat.updated_at.desc(), Chat.id)
            else:
                stmt = stmt.order_by(Chat.updated_at.desc(), Chat.id)

            if search_params:
                stmt = stmt.params(**search_params)

            # Perform pagination at the SQL level
            stmt = stmt.offset(skip).limit(limit)
            result = await session.execute(stmt)
            all_chats = result.mappings().all()

            log.info('The number of chats: %s', len(all_chats))

            # Validate and return chats
            return [ChatTitleIdResponse.model_validate(chat) for chat in all_chats]

    @staticmethod
    async def _search_bodies(session: AsyncSession, *conditions: ColumnElement[bool]) -> dict[str, dict]:
        """Message contents of the matching chats, in the shape ``chat_search_snippet`` reads."""
        result = await session.execute(
            select(ChatMessage.chat_id, ChatMessage.created_at, ChatMessage.id, ChatMessage.content)
            .join(Chat, Chat.id == ChatMessage.chat_id)
            .where(*conditions)
        )
        bodies = {}
        for row in sorted(result.all(), key=lambda row: (row.created_at or 0, row.id)):
            bodies.setdefault(row.chat_id, {'messages': []})['messages'].append({'content': row.content})
        return bodies

    async def get_chat_search_snippets(
        self, ids: list[str], user_id: str, search_text: str, db: AsyncSession | None = None
    ) -> dict[str, str | None]:
        if not ids or not chat_search_content_query(search_text):
            return {}
        async with get_async_db_context(db) as session:
            bodies = await self._search_bodies(session, Chat.id.in_(ids), Chat.user_id == user_id)
            return {id: chat_search_snippet(body, search_text) for id, body in bodies.items()}

    async def get_chats_by_folder_id_and_user_id(
        self,
        folder_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 60,
        sort_by: str = 'updated_at',
        sort_dir: str = 'desc',
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as session:
            stmt = (
                select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at)
                .filter_by(folder_id=folder_id, user_id=user_id)
                .filter(or_(Chat.pinned == False, Chat.pinned == None))
                .filter_by(archived=False)
                .where(Chat.meta['internal'].as_boolean().is_not(True))
            )
            stmt = stmt.order_by(*chat_list_order(sort_by, sort_dir))

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            all_chats = result.all()
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        'id': chat[0],
                        'title': chat[1],
                        'updated_at': chat[2],
                        'created_at': chat[3],
                        'last_read_at': chat[4],
                    }
                )
                for chat in all_chats
            ]

    async def get_all_chats_by_folder_id(
        self,
        folder_id: str,
        skip: int = 0,
        limit: int = 60,
        sort_by: str = 'updated_at',
        sort_dir: str = 'desc',
        unread_for_user_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        """Get chats in a folder across ALL users. Returns dicts with user_id."""
        async with get_async_db_context(db) as session:
            stmt = (
                select(Chat.id, Chat.title, Chat.user_id, Chat.updated_at, Chat.created_at, Chat.last_read_at)
                .filter_by(folder_id=folder_id)
                .filter(or_(Chat.pinned == False, Chat.pinned == None))
                .filter_by(archived=False)
                .where(Chat.meta['internal'].as_boolean().is_not(True))
            )
            stmt = stmt.order_by(*chat_list_order(sort_by, sort_dir, unread_for_user_id))

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            all_chats = result.all()
            return [
                {
                    'id': chat[0],
                    'title': chat[1],
                    'user_id': chat[2],
                    'updated_at': chat[3],
                    'created_at': chat[4],
                    'last_read_at': chat[5],
                }
                for chat in all_chats
            ]

    async def get_participant_ids_by_chat_ids(
        self, chat_ids: list[str], db: AsyncSession | None = None
    ) -> dict[str, list[str]]:
        participants: dict[str, list[str]] = {chat_id: [] for chat_id in chat_ids}
        if not chat_ids:
            return participants

        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(ChatMessage.chat_id, ChatMessage.user_id)
                .where(
                    ChatMessage.chat_id.in_(chat_ids), ChatMessage.role == 'user', func.trim(ChatMessage.user_id) != ''
                )
                .distinct()
                .order_by(ChatMessage.chat_id, ChatMessage.user_id)
            )
            for chat_id, author_id in result.all():
                participants[chat_id].append(author_id)
        return participants

    def _folder_chat_conditions(
        self,
        folder_id: str,
        dialect_name: str,
        search: str = '',
        tag_ids: list[str] | None = None,
        status_ids: list[str] | None = None,
        valid_status_ids: tuple[str, ...] = (),
        priority_ids: list[str] | None = None,
    ) -> list:
        conditions = [
            Chat.folder_id == folder_id,
            Chat.archived.is_(False),
            Chat.meta['internal'].as_boolean().is_not(True),
        ]

        # Same matching as the sidebar search: the phrase, or every term.
        phrase = chat_search_content_query(search)
        if phrase:

            def match(key: str, value: str):
                return or_(
                    Chat.title.ilike(f'%{value}%'),
                    text(chat_search_message_content_match_sql(dialect_name, key)).bindparams(**{key: value}),
                )

            terms = [term for term in chat_search_terms(phrase) if term != phrase]
            phrase_match = match('folder_phrase', phrase)
            conditions.append(
                or_(phrase_match, and_(*[match(f'folder_term_{i}', term) for i, term in enumerate(terms)]))
                if terms
                else phrase_match
            )

        # 'none' means untagged, as in the sidebar search's tag:none.
        if tag_ids:
            conditions.append(resource_tag_filter('chat', Chat.id, tag_ids))

        # 'not_started' was the default status's earlier name.
        status_ids = {NO_FOLDER_STATUS if value == 'not_started' else value for value in status_ids or []}
        if status_ids:
            stored = Chat.meta['folder_status'].as_string()
            named = sorted(status_ids - {NO_FOLDER_STATUS})
            matches = [stored.in_(named)] if named else []
            if NO_FOLDER_STATUS in status_ids:
                # Unknown or deleted statuses read as no status.
                matches.append(or_(stored.is_(None), stored.not_in(list(valid_status_ids))))
            conditions.append(or_(*matches))

        priority_ids = set(priority_ids or [])
        if priority_ids:
            stored = Chat.meta['folder_priority'].as_string()
            named = sorted(priority_ids & set(FOLDER_PRIORITIES))
            matches = [stored.in_(named)] if named else []
            if NO_FOLDER_PRIORITY in priority_ids:
                matches.append(or_(stored.is_(None), stored.not_in(list(FOLDER_PRIORITIES))))
            conditions.append(or_(*matches))
        return conditions

    async def get_folder_chat_page(
        self,
        folder_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        search: str = '',
        tag_ids: list[str] | None = None,
        status_ids: list[str] | None = None,
        valid_status_ids: tuple[str, ...] = (),
        priority_ids: list[str] | None = None,
        user_ids: list[str] | None = None,
        activity: str | None = None,
        updated_at_gte: int | None = None,
        sort_by: str = 'updated_at',
        sort_dir: str = 'desc',
        redis=None,
        db: AsyncSession | None = None,
    ) -> tuple[list[dict], int]:
        """A page of a folder's chats for the list and board views, filtered before paging."""
        async with get_async_db_context(db) as session:
            dialect_name = (await session.connection()).dialect.name
            conditions = self._folder_chat_conditions(
                folder_id, dialect_name, search, tag_ids, status_ids, valid_status_ids, priority_ids
            )

            if user_ids:
                # Participants come from message history, so match them over this folder's chats.
                wanted = set(user_ids)
                rows = (await session.execute(select(Chat.id, Chat.user_id).where(*conditions))).all()
                authors = await self.get_participant_ids_by_chat_ids([row[0] for row in rows], db=session)
                conditions.append(
                    Chat.id.in_(
                        [
                            chat_id
                            for chat_id, owner in rows
                            if owner in wanted or wanted.intersection(authors.get(chat_id, ()))
                        ]
                    )
                )

            if updated_at_gte is not None:
                conditions.append(Chat.updated_at >= updated_at_gte)

            if activity:
                # Same precedence as the sidebar markers: approval > generating > unread.
                unfinished = (
                    await session.execute(
                        select(ChatMessage.chat_id, ChatMessage.output)
                        .join(Chat, Chat.id == ChatMessage.chat_id)
                        .where(*conditions, ChatMessage.role == 'assistant', ChatMessage.done.is_(False))
                    )
                ).all()
                pending_ids = {chat_id for chat_id, output in unfinished if has_pending_tool_approval(output)}
                if activity == 'waiting_for_approval':
                    conditions.append(Chat.id.in_(pending_ids))
                else:
                    active_ids = {
                        chat_id for chat_id in {row[0] for row in unfinished} if await has_active_tasks(redis, chat_id)
                    }
                    if activity == 'generating':
                        conditions.append(Chat.id.in_(active_ids - pending_ids))
                    elif activity == 'unread':
                        conditions.extend(
                            [
                                Chat.user_id == user_id,
                                or_(
                                    Chat.last_read_at.is_(None),
                                    Chat.last_read_at == 0,
                                    Chat.updated_at > Chat.last_read_at,
                                ),
                                Chat.id.not_in(active_ids | pending_ids),
                            ]
                        )
                    elif activity == 'idle':
                        # Everything the other three leave out.
                        conditions.extend(
                            [
                                Chat.id.not_in(active_ids | pending_ids),
                                or_(
                                    Chat.user_id != user_id,
                                    and_(
                                        Chat.last_read_at.is_not(None),
                                        Chat.last_read_at != 0,
                                        Chat.updated_at <= Chat.last_read_at,
                                    ),
                                ),
                            ]
                        )

            total = (await session.execute(select(func.count(Chat.id)).where(*conditions))).scalar_one()
            rows = (
                (
                    await session.execute(
                        select(
                            Chat.id,
                            Chat.title,
                            Chat.user_id,
                            Chat.updated_at,
                            Chat.created_at,
                            Chat.last_read_at,
                            Chat.meta,
                        )
                        .where(*conditions)
                        .order_by(*chat_list_order(sort_by, sort_dir, user_id))
                        .offset(skip)
                        .limit(limit)
                    )
                )
                .mappings()
                .all()
            )

            tags = await Tags.get_tags_by_resources('chat', [row['id'] for row in rows], db=session)

            bodies = {}
            if chat_search_content_query(search) and rows:
                bodies = await self._search_bodies(session, Chat.id.in_([row['id'] for row in rows]))

        terms = chat_search_content_query(search).split()
        chats = []
        for row in rows:
            chat = dict(row)
            meta = chat.pop('meta') or {}
            chat['tags'] = tags.get(chat['id'], [])
            status = meta.get('folder_status')
            chat['status'] = status if status in valid_status_ids else None
            chat['status_since'] = folder_status_since(meta, chat['status'])
            # For the time-in-status tooltip: when the current stretch began, and earlier
            # time per status (statuses the folder no longer has are left out).
            chat['status_entered_at'] = _as_seconds(meta.get('folder_status_at')) if chat['status'] else None
            chat['status_durations'] = {
                key: seconds
                for key, value in (meta.get('folder_status_durations') or {}).items()
                if key in valid_status_ids and (seconds := _as_seconds(value))
            }
            priority = meta.get('folder_priority')
            chat['priority'] = priority if priority in FOLDER_PRIORITIES else None
            chat['automation_id'] = meta.get('automation_id')
            # Only explain matches the title doesn't already show.
            chat['search_snippet'] = (
                chat_search_snippet(bodies.get(chat['id']) or {}, search)
                if terms and not all(term in chat['title'].lower() for term in terms)
                else None
            )
            chats.append(chat)
        return chats, total

    async def get_participant_counts_by_folder_id(
        self, folder_id: str, db: AsyncSession | None = None
    ) -> dict[str, int]:
        """How many of a folder's chats each person owns or wrote in."""
        async with get_async_db_context(db) as session:
            dialect_name = (await session.connection()).dialect.name
            rows = (
                await session.execute(
                    select(Chat.id, Chat.user_id).where(*self._folder_chat_conditions(folder_id, dialect_name))
                )
            ).all()
            authors = await self.get_participant_ids_by_chat_ids([row[0] for row in rows], db=session)
        counts: dict[str, int] = {}
        for chat_id, owner in rows:
            for participant_id in {owner, *authors.get(chat_id, ())}:
                counts[participant_id] = counts.get(participant_id, 0) + 1
        return counts

    async def get_tag_counts_by_folder_id(self, folder_id: str, db: AsyncSession | None = None) -> list[dict]:
        """Tags used in a folder with chat counts, aggregated in SQL without loading chats."""
        chat_ids = select(Chat.id).where(
            Chat.folder_id == folder_id,
            Chat.archived.is_(False),
            Chat.meta['internal'].as_boolean().is_not(True),
        )
        return await Tags.get_tag_counts('chat', chat_ids, db=db)

    async def update_chat_folder_status_by_id(
        self, id: str, folder_id: str, user_id: str | None, status: str | None, db: AsyncSession | None = None
    ) -> bool:
        """Set (or with None, clear) a chat's folder status, banking the time spent in its previous one.

        Time adds up per status, so moving away and coming back doesn't reset it.
        A user_id limits this to that user's chats; None allows any chat in the folder.
        """
        async with get_async_db_context(db) as session:
            row = (
                await session.execute(
                    select(Chat.meta).filter_by(id=id, folder_id=folder_id, **({'user_id': user_id} if user_id else {}))
                )
            ).one_or_none()
            if row is None:
                return False
            meta = dict(row[0] or {})
            previous = meta.get('folder_status')
            if previous == status:
                return True  # Same status: keep its clock running.
            now = int(time.time())
            started = _as_seconds(meta.get('folder_status_at'))
            durations = dict(meta.get('folder_status_durations') or {})
            if previous and previous != 'none' and started is not None:  # 'none' was stored by older builds
                durations[previous] = (_as_seconds(durations.get(previous)) or 0) + max(0, now - started)
            await session.execute(
                update(Chat)
                .filter_by(id=id)
                .values(
                    meta={
                        # No status means no stored status, like chats that never had one.
                        **{
                            key: value
                            for key, value in meta.items()
                            if key not in ('folder_status', 'folder_status_at')
                        },
                        **({'folder_status': status, 'folder_status_at': now} if status is not None else {}),
                        'folder_status_durations': durations,
                    }
                )
            )
            await session.commit()
            return True

    async def update_chat_folder_priority_by_id(
        self, id: str, folder_id: str, user_id: str | None, priority: str | None, db: AsyncSession | None = None
    ) -> bool:
        """Set (or with None, clear) a chat's priority in its folder.

        A user_id limits this to that user's chats; None allows any chat in the folder.
        """
        async with get_async_db_context(db) as session:
            row = (
                await session.execute(
                    select(Chat.meta).filter_by(id=id, folder_id=folder_id, **({'user_id': user_id} if user_id else {}))
                )
            ).one_or_none()
            if row is None:
                return False
            meta = {key: value for key, value in (row[0] or {}).items() if key != 'folder_priority'}
            if priority is not None:
                meta['folder_priority'] = priority
            await session.execute(update(Chat).filter_by(id=id).values(meta=meta))
            await session.commit()
            return True

    async def count_all_chats_by_folder_id(
        self,
        folder_id: str,
        db: AsyncSession | None = None,
    ) -> int:
        async with get_async_db_context(db) as session:
            stmt = (
                select(func.count(Chat.id))
                .filter_by(folder_id=folder_id)
                .filter(or_(Chat.pinned == False, Chat.pinned == None))
                .filter_by(archived=False)
                .where(Chat.meta['internal'].as_boolean().is_not(True))
            )
            result = await session.execute(stmt)
            return result.scalar_one()

    async def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str, db: AsyncSession | None = None
    ) -> list[ChatModel]:
        async with get_async_db_context(db) as session:
            stmt = (
                select(Chat)
                .filter(Chat.folder_id.in_(folder_ids), Chat.user_id == user_id)
                .filter(or_(Chat.pinned == False, Chat.pinned == None))
                .filter_by(archived=False)
                .where(Chat.meta['internal'].as_boolean().is_not(True))
                .order_by(Chat.updated_at.desc())
            )

            result = await session.execute(stmt)
            all_chats = result.scalars().all()
            return await self._with_histories(all_chats, db=session)

    async def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str, db: AsyncSession | None = None
    ) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                chat.folder_id = folder_id
                if chat.user_id == user_id:
                    chat.pinned = False
                if folder_id is not None:
                    # Folder listings only show unarchived chats, so moving an archived
                    # chat into a folder would otherwise have no visible effect: the chat
                    # stays in the archived list and never appears in the folder.
                    chat.archived = False
                await session.commit()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def get_chat_list_by_user_id_and_tag_name(
        self,
        user_id: str,
        tag_name: str,
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at).filter_by(
                user_id=user_id
            )
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))
            stmt = stmt.filter(resource_tag_filter('chat', Chat.id, [get_tag_id(tag_name)]))
            stmt = stmt.order_by(Chat.updated_at.desc(), Chat.id)

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            all_chats = result.all()
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        'id': chat[0],
                        'title': chat[1],
                        'updated_at': chat[2],
                        'created_at': chat[3],
                        'last_read_at': chat[4],
                    }
                )
                for chat in all_chats
            ]

    async def count_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str, db: AsyncSession | None = None
    ) -> int:
        async with get_async_db_context(db) as session:
            stmt = select(func.count(Chat.id)).filter_by(user_id=user_id, folder_id=folder_id)
            result = await session.execute(stmt.where(Chat.meta['internal'].as_boolean().is_not(True)))
            count = result.scalar()

            log.info("Count of chats for folder '%s': %s", folder_id, count)
            return count

    async def count_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str, db: AsyncSession | None = None
    ) -> int:
        if not folder_ids:
            return 0

        async with get_async_db_context(db) as session:
            stmt = select(func.count(Chat.id)).filter(Chat.user_id == user_id, Chat.folder_id.in_(folder_ids))
            result = await session.execute(stmt.where(Chat.meta['internal'].as_boolean().is_not(True)))
            count = result.scalar()

            log.info("Count of chats for folders '%s': %s", folder_ids, count)
            return count

    async def delete_chat_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(update(AutomationRun).filter_by(chat_id=id).values(chat_id=None))
                recipients = await delete_resource_comments('chat', select(Chat.id).filter_by(id=id), db=session)
                await session.execute(delete(ChatMessage).filter_by(chat_id=id))
                await delete_resource_tags('chat', select(Chat.id).filter_by(id=id), session)
                await session.execute(
                    delete(ChatViewState).where(ChatViewState.chat_id.in_(select(Chat.id).filter_by(id=id)))
                )
                await session.execute(delete(Chat).filter_by(id=id))
                await session.commit()
                await emit_changes(recipients)

                return True and await self.delete_shared_chat_by_chat_id(id, db=session)
        except Exception:
            return False

    async def delete_chat_by_id_and_user_id(self, id: str, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(update(AutomationRun).filter_by(chat_id=id).values(chat_id=None))
                recipients = await delete_resource_comments(
                    'chat', select(Chat.id).filter_by(id=id, user_id=user_id), db=session
                )
                await session.execute(delete(ChatMessage).filter_by(chat_id=id))
                await delete_resource_tags('chat', select(Chat.id).filter_by(id=id, user_id=user_id), session)
                await session.execute(
                    delete(ChatViewState).where(
                        ChatViewState.chat_id.in_(select(Chat.id).filter_by(id=id, user_id=user_id))
                    )
                )
                await session.execute(delete(Chat).filter_by(id=id, user_id=user_id))
                await session.commit()
                await emit_changes(recipients)

                return True and await self.delete_shared_chat_by_chat_id(id, db=session)
        except Exception:
            return False

    async def delete_chats_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await self.delete_shared_chats_by_user_id(user_id, db=session)

                chat_id_subquery = select(Chat.id).filter_by(user_id=user_id).scalar_subquery()
                await session.execute(
                    update(AutomationRun)
                    .filter(AutomationRun.chat_id.in_(select(Chat.id).filter_by(user_id=user_id)))
                    .values(chat_id=None)
                )
                recipients = await delete_resource_comments(
                    'chat', select(Chat.id).filter_by(user_id=user_id), db=session
                )
                await session.execute(
                    delete(ChatMessage).filter(ChatMessage.chat_id.in_(select(Chat.id).filter_by(user_id=user_id)))
                )
                await delete_resource_tags('chat', select(Chat.id).filter_by(user_id=user_id), session)
                await session.execute(
                    delete(ChatViewState).where(ChatViewState.chat_id.in_(select(Chat.id).filter_by(user_id=user_id)))
                )
                await session.execute(delete(Chat).filter_by(user_id=user_id))
                await session.commit()
                await emit_changes(recipients)

                return True
        except Exception:
            return False

    async def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str, db: AsyncSession | None = None
    ) -> bool:
        from open_webui.models.shared_chats import SharedChat as SharedChatTable

        try:
            async with get_async_db_context(db) as session:
                folder_chat_ids_stmt = select(Chat.id).filter_by(user_id=user_id, folder_id=folder_id)
                # Internal child chats sit outside the folder but go with their parent.
                chat_ids_stmt = select(Chat.id).where(
                    Chat.user_id == user_id,
                    or_(
                        Chat.folder_id == folder_id,
                        and_(
                            Chat.meta['internal'].as_boolean().is_(True),
                            Chat.meta['parent_chat_id'].as_string().in_(folder_chat_ids_stmt),
                        ),
                    ),
                )
                await session.execute(
                    update(AutomationRun).filter(AutomationRun.chat_id.in_(chat_ids_stmt)).values(chat_id=None)
                )
                recipients = await delete_resource_comments('chat', chat_ids_stmt, db=session)
                await session.execute(delete(ChatMessage).filter(ChatMessage.chat_id.in_(chat_ids_stmt)))
                await delete_resource_tags('chat', chat_ids_stmt, session)
                await session.execute(delete(SharedChatTable).filter(SharedChatTable.chat_id.in_(chat_ids_stmt)))
                recipients.update(
                    await delete_resource_comments(
                        'chat', select(Chat.id).filter_by(user_id=user_id, folder_id=folder_id), db=session
                    )
                )
                await session.execute(delete(ChatViewState).where(ChatViewState.chat_id.in_(chat_ids_stmt)))
                await session.execute(delete(Chat).where(Chat.id.in_(chat_ids_stmt)))
                await session.commit()
                await emit_changes(recipients)

                return True
        except Exception:
            return False

    async def move_chats_by_folder_id(
        self,
        folder_id: str,
        new_folder_id: str | None,
        db: AsyncSession | None = None,
    ) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(update(Chat).filter_by(folder_id=folder_id).values(folder_id=new_folder_id))
                await session.commit()

                return True
        except Exception:
            return False

    async def delete_shared_chats_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        """Delete all shared chat snapshots created by a user."""
        from open_webui.models.shared_chats import SharedChat as SharedChatTable
        from open_webui.models.shared_chats import SharedChats

        try:
            async with get_async_db_context(db) as session:
                # Delete shared_chat rows for this user's chats
                await session.execute(delete(SharedChatTable).filter_by(user_id=user_id))

                # Clear share_id on all of this user's chats
                await session.execute(update(Chat).filter_by(user_id=user_id).values(share_id=None))
                await session.commit()

                return True
        except Exception:
            return False

    async def insert_chat_files(
        self,
        chat_id: str,
        message_id: str,
        file_ids: list[str],
        user_id: str,
        db: AsyncSession | None = None,
    ) -> list[ChatFileModel] | None:
        if not file_ids:
            return None

        async with get_async_db_context(db) as session:
            result = await session.execute(select(ChatFile.file_id).filter_by(chat_id=chat_id))
            chat_file_ids = set(result.scalars().all())
        # Remove duplicates and existing file_ids
        file_ids = list({file_id for file_id in file_ids if file_id and file_id not in chat_file_ids})
        if not file_ids:
            return None

        # Only link files the caller can read; blocks forging a chat_file row to another user's file.
        from open_webui.models.files import Files
        from open_webui.models.users import Users
        from open_webui.utils.access_control.files import has_access_to_file

        user = await Users.get_user_by_id(user_id, db=db)
        accessible_file_ids = []
        for file_id in file_ids:
            file = await Files.get_file_by_id(file_id, db=db)
            if not file:
                continue
            if (
                file.user_id == user_id
                or (user and user.role == 'admin')
                or (user and await has_access_to_file(file_id, 'read', user, db=db))
            ):
                accessible_file_ids.append(file_id)
        file_ids = accessible_file_ids
        if not file_ids:
            return None

        try:
            async with get_async_db_context(db) as session:
                now = int(time.time())

                chat_files = [
                    ChatFileModel(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        chat_id=chat_id,
                        message_id=message_id,
                        file_id=file_id,
                        created_at=now,
                        updated_at=now,
                    )
                    for file_id in file_ids
                ]

                results = [ChatFile(**chat_file.model_dump()) for chat_file in chat_files]

                session.add_all(results)
                await session.commit()

                return chat_files
        except Exception:
            return None

    async def get_chat_files_by_chat_id_and_message_id(
        self, chat_id: str, message_id: str, db: AsyncSession | None = None
    ) -> list[ChatFileModel]:
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(ChatFile).filter_by(chat_id=chat_id, message_id=message_id).order_by(ChatFile.created_at.asc())
            )
            all_chat_files = result.scalars().all()
            return [ChatFileModel.model_validate(chat_file) for chat_file in all_chat_files]

    async def delete_chat_file(self, chat_id: str, file_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(delete(ChatFile).filter_by(chat_id=chat_id, file_id=file_id))
                await session.commit()
                return True
        except Exception:
            return False

    async def get_shared_chat_ids_by_file_id(self, file_id: str, db: AsyncSession | None = None) -> list[str]:
        """Return file-associated chats with a share link or folder audience."""
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(Chat.id)
                .join(ChatFile, Chat.id == ChatFile.chat_id)
                .filter(ChatFile.file_id == file_id, or_(Chat.share_id.isnot(None), Chat.folder_id.isnot(None)))
            )
            return [row[0] for row in result.all()]

    async def update_chat_tasks_by_id(self, id: str, tasks: list[dict]) -> ChatModel | None:
        """Update the tasks list on a chat."""
        try:
            async with get_async_db_context() as session:
                chat = await session.get(Chat, id)
                if chat is None:
                    return None
                chat.tasks = tasks
                await session.commit()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def get_chat_tasks_by_id(self, id: str) -> list[dict]:
        """Read the tasks list from a chat (lightweight column query)."""
        async with get_async_db_context() as session:
            result = await session.execute(select(Chat.tasks).filter_by(id=id))
            row = result.first()
            if row is None or row[0] is None:
                return []
            return row[0]


Chats = ChatTable()  # singleton chats repository
