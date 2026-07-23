"""Chat models, forms, and database operations."""

from __future__ import annotations

import json
import logging
import time
import uuid
from copy import deepcopy

# local imports
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.automations import AutomationRun
from open_webui.models.chat_messages import ChatMessage, ChatMessages
from open_webui.models.folders import Folders
from open_webui.models.tags import Tag, TagModel, Tags
from open_webui.utils.chat_history import (
    build_window_chat,
    create_message_window,
    has_embedded_messages,
    hydrate_chat,
    merge_compact_chat,
    split_chat_messages,
    uses_normalized_message_storage,
)
from open_webui.utils.misc import sanitize_data_for_db, sanitize_text_for_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    and_,
    cast,
    delete,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import bindparam

log = logging.getLogger(__name__)
ACTIVE_CHAT_GAP_SECONDS = 30 * 60


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
    folder_id = Column(Text, nullable=True)

    tasks = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    current_message_id = Column(Text, nullable=True)

    last_read_at = Column(BigInteger, nullable=True)

    __table_args__ = (
        # Performance indexes for common queries
        Index('folder_id_idx', 'folder_id'),
        Index('user_id_pinned_idx', 'user_id', 'pinned'),
        Index('user_id_archived_idx', 'user_id', 'archived'),
        Index('updated_at_user_id_idx', 'updated_at', 'user_id'),
        Index('folder_id_user_id_idx', 'folder_id', 'user_id'),
    )


def is_internal_chat(meta: dict | None) -> bool:
    return bool(meta and meta.get('internal') is True)


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
    folder_id: str | None = None

    tasks: list | None = None
    summary: str | None = None
    current_message_id: str | None = None

    last_read_at: int | None = None


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


####################
# Forms
####################


class ChatForm(BaseModel):
    chat: dict
    folder_id: str | None = None


class ChatImportForm(ChatForm):
    meta: dict | None = {}
    pinned: bool | None = False
    current_message_id: str | None = None
    created_at: int | None = None
    updated_at: int | None = None


class ChatsImportForm(BaseModel):
    chats: list[ChatImportForm]


class ChatTitleMessagesForm(BaseModel):
    title: str
    messages: list[dict]


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
    folder_id: str | None = None

    tasks: list | None = None
    summary: str | None = None
    current_message_id: str | None = None
    context_usage: dict | None = None


class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int
    last_read_at: int | None = None
    snippet: str | None = None
    active: bool = False


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
    tags: list[str | None] = None  # Derived from message.annotation.tags


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
    def _clean_null_bytes(self, obj):
        """Recursively remove null bytes from strings in dict/list structures."""
        return sanitize_data_for_db(obj)

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

    def _repair_chat_current_id(self, chat: dict) -> bool:
        history = chat.get('history')
        if not isinstance(history, dict):
            return False

        messages = history.get('messages')
        if not isinstance(messages, dict):
            return False

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
            return False

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
            return False

        history['currentId'] = latest_leaf_id
        return True

    async def insert_new_chat(
        self,
        id: str,
        user_id: str,
        form_data: ChatForm,
        db: AsyncSession | None = None,
        *,
        internal_meta: dict | None = None,
    ) -> ChatModel | None:
        async with get_async_db_context(db) as session:
            clean_chat = self._clean_null_bytes(form_data.chat)
            compact_chat, messages = split_chat_messages(clean_chat)
            chat = ChatModel(
                **{
                    'id': id,
                    'user_id': user_id,
                    'title': self._clean_null_bytes(
                        form_data.chat['title'] if 'title' in form_data.chat else 'New Chat'
                    ),
                    'chat': compact_chat,
                    'folder_id': form_data.folder_id,
                    'meta': internal_meta or {},
                    'current_message_id': self.get_current_message_id(form_data.chat),
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                    'last_read_at': int(time.time()),
                }
            )

            chat_item = Chat(**chat.model_dump())
            try:
                session.add(chat_item)
                await session.flush()
                if messages:
                    await ChatMessages.bulk_upsert_messages_in_session(
                        session,
                        id,
                        user_id,
                        messages,
                    )
                await session.commit()
                await session.refresh(chat_item)
            except Exception as e:
                await session.rollback()
                log.exception('Failed to insert normalized chat %s: %s', id, e)
                return None

            if not chat_item:
                return None

            result = ChatModel.model_validate(chat_item)
            if messages:
                result = result.model_copy(update={'chat': hydrate_chat(result.chat, messages)})
            return result

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

    def _chat_import_form_to_chat_model(self, user_id: str, form_data: ChatImportForm) -> ChatModel:
        id = str(uuid.uuid4())
        chat = ChatModel(
            **{
                'id': id,
                'user_id': user_id,
                'title': self._clean_null_bytes(form_data.chat['title'] if 'title' in form_data.chat else 'New Chat'),
                'chat': self._clean_null_bytes(form_data.chat),
                'meta': form_data.meta,
                'pinned': form_data.pinned,
                'folder_id': form_data.folder_id,
                'current_message_id': form_data.current_message_id or self.get_current_message_id(form_data.chat),
                'created_at': (form_data.created_at if form_data.created_at else int(time.time())),
                'updated_at': (form_data.updated_at if form_data.updated_at else int(time.time())),
            }
        )
        return chat

    async def import_chats(
        self,
        user_id: str,
        chat_import_forms: list[ChatImportForm],
        db: AsyncSession | None = None,
    ) -> list[ChatModel]:
        async with get_async_db_context(db) as session:
            # Validate folder_id references — clear any that don't exist
            folder_ids = {f.folder_id for f in chat_import_forms if f.folder_id}
            existing = set()
            for fid in folder_ids:
                if await Folders.get_folder_by_id_and_user_id(fid, user_id, db=session):
                    existing.add(fid)

            cleared = 0
            for form in chat_import_forms:
                if form.folder_id and form.folder_id not in existing:
                    form.folder_id = None
                    cleared += 1
            if cleared:
                log.info('Import: cleared %d dangling folder_id(s) for user %s', cleared, user_id)

            chats = []

            for form_data in chat_import_forms:
                chat = self._chat_import_form_to_chat_model(user_id, form_data)
                chats.append(Chat(**chat.model_dump()))

            session.add_all(chats)
            await session.commit()

            for form_data, chat_obj in zip(chat_import_forms, chats):
                compact_chat, messages = split_chat_messages(form_data.chat)
                try:
                    if messages:
                        await ChatMessages.bulk_upsert_messages_in_session(
                            session,
                            chat_obj.id,
                            user_id,
                            messages,
                        )
                    chat_obj.chat = compact_chat
                    flag_modified(chat_obj, 'chat')
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    await session.refresh(chat_obj)
                    log.warning('Failed to normalize imported chat %s: %s', chat_obj.id, e)

            return [
                ChatModel.model_validate(chat).model_copy(
                    update={'chat': hydrate_chat(chat.chat, split_chat_messages(form.chat)[1])}
                )
                for form, chat in zip(chat_import_forms, chats)
            ]

    async def update_chat_by_id(
        self,
        id: str,
        chat: dict,
        db: AsyncSession | None = None,
        *,
        touch: bool = True,
        include_messages: bool = True,
        deleted_message_ids: set[str] | None = None,
    ) -> ChatModel | None:
        """Persist compact chat metadata and lossless normalized messages."""
        try:  # load the chat record for in-place mutation
            async with get_async_db_context(db) as session:
                chat_item = await session.get(Chat, id, with_for_update=True)
                if chat_item is None:
                    return None

                clean_chat = self._clean_null_bytes(chat)
                legacy_storage_present = has_embedded_messages(chat_item.chat)
                _, legacy_messages = split_chat_messages(chat_item.chat)
                compact_chat, incoming_messages = merge_compact_chat(chat_item.chat, clean_chat)
                messages_to_sync = {**legacy_messages, **incoming_messages}

                if messages_to_sync or legacy_storage_present:
                    if legacy_storage_present:
                        await ChatMessages.replace_messages_in_session(
                            session,
                            id,
                            chat_item.user_id,
                            messages_to_sync,
                        )
                    else:
                        await ChatMessages.bulk_upsert_messages_in_session(
                            session,
                            id,
                            chat_item.user_id,
                            messages_to_sync,
                        )

                if deleted_message_ids:
                    await session.execute(
                        delete(ChatMessage).where(
                            ChatMessage.chat_id == id,
                            ChatMessage.id.in_({f'{id}-{message_id}' for message_id in deleted_message_ids}),
                        )
                    )

                chat_item.chat = compact_chat
                flag_modified(chat_item, 'chat')
                chat_item.title = self._clean_null_bytes(chat['title']) if 'title' in chat else chat_item.title
                if any(key in clean_chat for key in ('history', 'messages', 'currentId', 'branchPointMessageId')):
                    chat_item.current_message_id = self.get_current_message_id(clean_chat)

                if touch:
                    chat_item.updated_at = int(time.time())

                await session.commit()
                await session.refresh(chat_item)

                result = ChatModel.model_validate(chat_item)
                if include_messages:
                    messages = await ChatMessages.get_message_data_map_by_chat_id(id, db=session)
                    result = result.model_copy(update={'chat': hydrate_chat(result.chat, messages or {})})
                return result
        except Exception as exc:
            log.exception('Failed to update chat %s: %s', id, exc)
            return

    async def update_chat_window_by_id(
        self,
        id: str,
        chat: dict,
        db: AsyncSession | None = None,
        *,
        touch: bool = True,
    ) -> ChatModel | None:
        """Merge a window save without replacing already-persisted message bodies."""
        try:
            async with get_async_db_context(db) as session:
                chat_item = await session.get(Chat, id, with_for_update=True)
                if chat_item is None:
                    return None

                clean_chat = self._clean_null_bytes(chat)
                legacy_storage_present = has_embedded_messages(chat_item.chat)
                _, legacy_messages = split_chat_messages(chat_item.chat)
                compact_chat, incoming_messages = merge_compact_chat(chat_item.chat, clean_chat)

                if legacy_storage_present:
                    await ChatMessages.replace_messages_in_session(
                        session,
                        id,
                        chat_item.user_id,
                        legacy_messages,
                    )
                    existing_message_ids = set(legacy_messages)
                else:
                    composite_ids = [f'{id}-{message_id}' for message_id in incoming_messages]
                    if composite_ids:
                        result = await session.execute(
                            select(ChatMessage.id).where(
                                ChatMessage.chat_id == id,
                                ChatMessage.id.in_(composite_ids),
                            )
                        )
                        existing_message_ids = {row_id.removeprefix(f'{id}-') for row_id in result.scalars().all()}
                    else:
                        existing_message_ids = set()

                new_messages = {
                    message_id: message
                    for message_id, message in incoming_messages.items()
                    if message_id not in existing_message_ids
                }
                if new_messages:
                    await ChatMessages.bulk_upsert_messages_in_session(
                        session,
                        id,
                        chat_item.user_id,
                        new_messages,
                    )

                topology = await ChatMessages.get_message_topology_in_session(session, id)
                history = compact_chat.setdefault('history', {})
                current_id = history.get('currentId')
                if current_id not in topology:
                    current_id = chat_item.current_message_id
                if current_id not in topology:
                    current_id = None
                history['currentId'] = current_id

                chat_item.chat = compact_chat
                flag_modified(chat_item, 'chat')
                if 'title' in clean_chat:
                    chat_item.title = self._clean_null_bytes(clean_chat['title'])
                chat_item.current_message_id = current_id
                if touch:
                    chat_item.updated_at = int(time.time())

                await session.commit()
                await session.refresh(chat_item)
                return ChatModel.model_validate(chat_item)
        except Exception as exc:
            log.exception('Failed to update chat window %s: %s', id, exc)
            return None

    async def update_chat_last_read_at_by_id(self, id: str, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                if chat and chat.user_id == user_id:
                    chat.last_read_at = int(time.time())
                    await session.commit()
                    return True
                return False
        except Exception:
            return False

    async def update_chat_title_by_id(self, id: str, title: str) -> ChatModel | None:
        try:
            async with get_async_db_context() as session:
                chat_item = await session.get(Chat, id)
                if chat_item is None:
                    return None
                clean_title = self._clean_null_bytes(title)
                chat_item.title = clean_title
                chat_item.chat = {**(chat_item.chat or {}), 'title': clean_title}
                await session.commit()
                await session.refresh(chat_item)
                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    async def update_chat_tags_by_id(self, id: str, tags: list[str], user) -> ChatModel | None:
        async with get_async_db_context() as session:
            chat = await session.get(Chat, id)
            if chat is None:
                return None

            old_tags = chat.meta.get('tags', [])
            new_tags = [t for t in tags if t.replace(' ', '_').lower() != 'none']
            new_tag_ids = [t.replace(' ', '_').lower() for t in new_tags]

            # Single meta update
            chat.meta = {**chat.meta, 'tags': new_tag_ids}
            await session.commit()
            await session.refresh(chat)

            # Batch-create any missing tag rows
            await Tags.ensure_tags_exist(new_tags, user.id, db=session)

            # Clean up orphaned old tags in one query
            removed = set(old_tags) - set(new_tag_ids)
            if removed:
                await self.delete_orphan_tags_for_user(list(removed), user.id, db=session)

            return ChatModel.model_validate(chat)

    async def get_chat_title_by_id(self, id: str) -> str | None:
        async with get_async_db_context() as session:
            result = await session.execute(select(Chat.title).filter_by(id=id))
            row = result.first()
            if row is None:
                return None
            return row[0] or 'New Chat'

    @staticmethod
    def get_unresolved_parent_ids(messages_map: dict) -> set[str]:
        """Return parent IDs referenced by messages but absent from the map.

        An empty set means the message graph is fully connected.
        """
        return {
            msg['parentId']
            for msg in messages_map.values()
            if msg.get('parentId') and msg['parentId'] not in messages_map
        }

    @staticmethod
    def merge_history(existing_history: dict | None, incoming_history: dict | None) -> dict:
        existing = (existing_history or {}).get('messages') or {}
        incoming = (incoming_history or {}).get('messages') or {}
        merged = {**existing, **incoming}
        merged = {message_id: message for message_id, message in merged.items() if isinstance(message, dict)}

        for message in merged.values():
            message['childrenIds'] = []
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
            else messages.get(current_id, {}).get('childrenIds') or []
        )
        while child_ids:
            current_id = child_ids[-1]
            child_ids = messages.get(current_id, {}).get('childrenIds') or []
        history['currentId'] = current_id if current_id in messages else None
        return deleted_ids

    async def backfill_messages_by_chat_id(self, chat_id: str, user_id: str, messages: dict[str, dict]) -> None:
        """Write messages to the ``chat_message`` table so future lookups
        use the fast path.  Errors are logged but never raised.
        """
        valid_messages = {message_id: message for message_id, message in messages.items() if isinstance(message, dict)}
        if not valid_messages:
            return

        try:
            await ChatMessages.bulk_upsert_messages(
                chat_id=chat_id,
                user_id=user_id,
                messages=valid_messages,
            )
        except Exception as e:
            log.warning('Backfill failed for %d messages in chat %s: %s', len(valid_messages), chat_id, e)

    async def reconcile_messages_by_chat_id(self, chat_id: str, user_id: str, messages: dict[str, dict]) -> None:
        """Sync ``chat_message`` rows with the committed JSON blob.

        Upserts current messages via ``backfill_messages_by_chat_id``.
        Best-effort: errors are logged but never raised.
        """
        try:
            await self.backfill_messages_by_chat_id(chat_id, user_id, messages)
        except Exception as e:
            log.warning('Failed to reconcile chat_message rows for chat %s: %s', chat_id, e)

    async def get_messages_map_by_chat_id(self, id: str) -> dict | None:
        """Message map for walking history (see ``get_message_list``).

        Prefer ``chat_message`` rows to avoid loading the large embedded
        history; fall back to the legacy JSON when no rows exist.
        When rows exist but the parent-link graph has gaps (e.g. migration
        failures), missing messages are merged from the legacy history
        and backfilled so future requests self-heal.
        """
        # Fast path: build from normalized chat_message rows.
        messages_map = await ChatMessages.get_messages_map_by_chat_id(id)

        if messages_map is not None:
            unresolved_ids = self.get_unresolved_parent_ids(messages_map)
            if not unresolved_ids:
                return messages_map

            # Graph has gaps — enrich from the legacy embedded history.
            log.info(
                'Chat %s: %d unresolved parent reference(s) in chat_message — enriching from legacy history',
                id,
                len(unresolved_ids),
            )
            chat = await self.get_chat_by_id(id)
            if chat:
                history_messages = chat.chat.get('history', {}).get('messages', {}) or {}
                missing_messages = {
                    message_id: history_messages[message_id]
                    for message_id in unresolved_ids
                    if message_id in history_messages
                }

                if missing_messages:
                    messages_map.update(missing_messages)

                    # Backfill so future requests use the fast path.
                    await self.backfill_messages_by_chat_id(id, chat.user_id, missing_messages)

            return messages_map

        # No rows — fall back to the legacy embedded history.
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        history_messages = chat.chat.get('history', {}).get('messages', {}) or {}

        # Backfill so future requests use the fast path.
        if history_messages:
            await self.backfill_messages_by_chat_id(id, chat.user_id, history_messages)

        return history_messages

    async def get_message_by_id_and_message_id(self, id: str, message_id: str) -> dict | None:
        async with get_async_db_context() as session:
            chat_item = await session.get(Chat, id)
            if chat_item is None:
                return None

            _, legacy_messages, normalized = await self._normalize_chat_item(chat_item, session)
            if not normalized:
                return legacy_messages.get(message_id)

            row = await session.get(ChatMessage, f'{id}-{message_id}')
            return ChatMessages.row_to_message_data(row)[1] if row is not None else None

    async def patch_message_by_chat_id_and_message_id(
        self,
        id: str,
        message_id: str,
        patch: dict,
        *,
        touch: bool = True,
        db: AsyncSession | None = None,
    ) -> dict | None:
        """Update one existing normalized message without hydrating the chat."""
        protected_fields = {
            '__loaded',
            'childrenIds',
            'id',
            'parentId',
            'role',
            'timestamp',
        }
        clean_patch = {
            key: value for key, value in self._clean_null_bytes(patch).items() if key not in protected_fields
        }

        try:
            async with get_async_db_context(db) as session:
                chat_item = await session.get(Chat, id, with_for_update=True)
                if chat_item is None:
                    return None

                compact_chat, legacy_messages = split_chat_messages(chat_item.chat)
                if has_embedded_messages(chat_item.chat):
                    await ChatMessages.replace_messages_in_session(
                        session,
                        id,
                        chat_item.user_id,
                        legacy_messages,
                    )
                    chat_item.chat = compact_chat
                    flag_modified(chat_item, 'chat')

                row = await session.get(ChatMessage, f'{id}-{message_id}')
                if row is None:
                    return None

                if clean_patch:
                    await ChatMessages.upsert_message_in_session(
                        session,
                        message_id,
                        id,
                        chat_item.user_id,
                        clean_patch,
                        existing=row,
                    )
                    if touch:
                        chat_item.updated_at = int(time.time())

                await session.commit()
                return ChatMessages.row_to_message_data(row)[1]
        except Exception as exc:
            log.exception('Failed to patch message %s for chat %s: %s', message_id, id, exc)
            return None

    async def upsert_message_to_chat_by_id_and_message_id(
        self,
        id: str,
        message_id: str,
        message: dict,
        *,
        touch: bool = True,
        include_messages: bool = False,
    ) -> ChatModel | None:
        clean_message = self._clean_null_bytes(message)

        try:
            async with get_async_db_context() as session:
                chat_item = await session.get(Chat, id, with_for_update=True)
                if chat_item is None:
                    return None

                compact_chat, legacy_messages = split_chat_messages(chat_item.chat)
                if has_embedded_messages(chat_item.chat):
                    await ChatMessages.replace_messages_in_session(
                        session,
                        id,
                        chat_item.user_id,
                        legacy_messages,
                    )

                composite_id = f'{id}-{message_id}'
                existing_row = await session.get(ChatMessage, composite_id)
                existing_message = (
                    ChatMessages.row_to_message_data(existing_row)[1] if existing_row is not None else None
                )
                old_parent_id = existing_message.get('parentId') if existing_message else None

                payload = dict(clean_message)
                if existing_row is None:
                    parent_id = payload.get('parentId')
                    if parent_id is None:
                        topology = await ChatMessages.get_message_topology_in_session(session, id)
                        parent_id = next(
                            (
                                candidate_id
                                for candidate_id, candidate in topology.items()
                                if message_id in (candidate.get('childrenIds') or [])
                            ),
                            None,
                        )

                    parent_row = await session.get(ChatMessage, f'{id}-{parent_id}') if parent_id else None
                    parent = ChatMessages.row_to_message_data(parent_row)[1] if parent_row is not None else None
                    output = payload.get('output') or []
                    output_role = next(
                        (item.get('role') for item in output if isinstance(item, dict) and item.get('role')),
                        None,
                    )
                    role = payload.get('role') or output_role
                    if not role:
                        parent_role = parent.get('role') if parent else None
                        role = (
                            'assistant'
                            if parent_role == 'user'
                            else 'user'
                            if parent_role == 'assistant'
                            else 'assistant'
                        )

                    payload = {
                        **payload,
                        'id': message_id,
                        'parentId': parent_id,
                        'childrenIds': (
                            payload.get('childrenIds') if isinstance(payload.get('childrenIds'), list) else []
                        ),
                        'role': role,
                        'timestamp': payload.get('timestamp') or int(time.time()),
                    }

                await ChatMessages.upsert_message_in_session(
                    session,
                    message_id,
                    id,
                    chat_item.user_id,
                    payload,
                    existing=existing_row,
                )

                new_parent_id = payload.get('parentId', old_parent_id)
                parent_changes = []
                if old_parent_id and old_parent_id != new_parent_id:
                    parent_changes.append((old_parent_id, False))
                if new_parent_id and (existing_row is None or old_parent_id != new_parent_id):
                    parent_changes.append((new_parent_id, True))

                for parent_id, add_child in parent_changes:
                    parent_row = await session.get(ChatMessage, f'{id}-{parent_id}')
                    if parent_row is None:
                        continue
                    parent = ChatMessages.row_to_message_data(parent_row)[1]
                    children_ids = [
                        child_id for child_id in (parent.get('childrenIds') or []) if child_id != message_id
                    ]
                    if add_child:
                        children_ids.append(message_id)
                    await ChatMessages.upsert_message_in_session(
                        session,
                        parent_id,
                        id,
                        chat_item.user_id,
                        {'childrenIds': children_ids},
                        existing=parent_row,
                    )

                history = compact_chat.setdefault('history', {})
                if existing_row is None:
                    history['currentId'] = message_id
                    chat_item.current_message_id = message_id
                chat_item.chat = compact_chat
                flag_modified(chat_item, 'chat')
                if touch:
                    chat_item.updated_at = int(time.time())

                await session.commit()
                await session.refresh(chat_item)
                result = ChatModel.model_validate(chat_item)

                if include_messages:
                    messages = await ChatMessages.get_message_data_map_by_chat_id(id, db=session)
                    result = result.model_copy(update={'chat': hydrate_chat(result.chat, messages)})
                return result
        except Exception as exc:
            log.exception('Failed to upsert message %s for chat %s: %s', message_id, id, exc)
            return None

    async def delete_message_from_chat_by_id_and_message_id(
        self,
        id: str,
        message_id: str,
        *,
        include_messages: bool = True,
        db: AsyncSession | None = None,
    ) -> ChatModel | None:
        """Delete one message branch using normalized topology only."""
        try:
            async with get_async_db_context(db) as session:
                chat_item = await session.get(Chat, id, with_for_update=True)
                if chat_item is None:
                    return None

                compact_chat, legacy_messages = split_chat_messages(chat_item.chat)
                if has_embedded_messages(chat_item.chat):
                    await ChatMessages.replace_messages_in_session(
                        session,
                        id,
                        chat_item.user_id,
                        legacy_messages,
                    )

                topology = await ChatMessages.get_message_topology_in_session(session, id)
                history = {
                    'currentId': (compact_chat.get('history') or {}).get('currentId'),
                    'messages': deepcopy(topology),
                }
                deleted_ids = self.delete_message_from_history(history, message_id)

                if deleted_ids:
                    remaining = history['messages']
                    for remaining_id, message in remaining.items():
                        previous = topology[remaining_id]
                        if message.get('parentId') == previous.get('parentId') and message.get(
                            'childrenIds'
                        ) == previous.get('childrenIds'):
                            continue

                        row = await session.get(ChatMessage, f'{id}-{remaining_id}')
                        if row is not None:
                            await ChatMessages.upsert_message_in_session(
                                session,
                                remaining_id,
                                id,
                                chat_item.user_id,
                                {
                                    'parentId': message.get('parentId'),
                                    'childrenIds': message.get('childrenIds') or [],
                                },
                                existing=row,
                            )

                    await session.execute(
                        delete(ChatMessage).where(
                            ChatMessage.chat_id == id,
                            ChatMessage.id.in_({f'{id}-{deleted_id}' for deleted_id in deleted_ids}),
                        )
                    )

                compact_history = compact_chat.setdefault('history', {})
                compact_history['currentId'] = history['currentId']
                chat_item.chat = compact_chat
                chat_item.current_message_id = history['currentId']
                flag_modified(chat_item, 'chat')
                chat_item.updated_at = int(time.time())

                await session.commit()
                await session.refresh(chat_item)
                result = ChatModel.model_validate(chat_item)

                if include_messages:
                    messages = await ChatMessages.get_message_data_map_by_chat_id(id, db=session)
                    result = result.model_copy(update={'chat': hydrate_chat(result.chat, messages)})
                return result
        except Exception as exc:
            log.exception('Failed to delete message %s from chat %s: %s', message_id, id, exc)
            return None

    async def append_message_items_by_chat_id_and_message_id(
        self,
        id: str,
        message_id: str,
        field: str,
        items: list,
        *,
        deduplicate: bool = False,
        touch: bool = False,
    ) -> list | None:
        """Append a list field while holding the chat transaction lock."""
        try:
            async with get_async_db_context() as session:
                chat_item = await session.get(Chat, id, with_for_update=True)
                if chat_item is None:
                    return None

                compact_chat, legacy_messages = split_chat_messages(chat_item.chat)
                if has_embedded_messages(chat_item.chat):
                    await ChatMessages.replace_messages_in_session(
                        session,
                        id,
                        chat_item.user_id,
                        legacy_messages,
                    )
                    chat_item.chat = compact_chat
                    flag_modified(chat_item, 'chat')

                row = await session.get(ChatMessage, f'{id}-{message_id}')
                if row is None:
                    return None

                message = ChatMessages.row_to_message_data(row)[1]
                values = [*(message.get(field) or []), *(items or [])]
                if deduplicate:
                    unique_values = []
                    for value in values:
                        if value not in unique_values:
                            unique_values.append(value)
                    values = unique_values

                await ChatMessages.upsert_message_in_session(
                    session,
                    message_id,
                    id,
                    chat_item.user_id,
                    {field: values},
                    existing=row,
                )
                if touch:
                    chat_item.updated_at = int(time.time())

                await session.commit()
                return values
        except Exception as exc:
            log.exception(
                'Failed to append %s for message %s in chat %s: %s',
                field,
                message_id,
                id,
                exc,
            )
            return None

    async def add_message_status_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, status: dict
    ) -> ChatModel | None:
        status_history = await self.append_message_items_by_chat_id_and_message_id(
            id,
            message_id,
            'statusHistory',
            [status],
            touch=False,
        )
        return await self.get_chat_by_id(id, include_messages=False) if status_history is not None else None

    async def add_message_files_by_id_and_message_id(self, id: str, message_id: str, files: list[dict]) -> list[dict]:
        message_files = await self.append_message_items_by_chat_id_and_message_id(
            id,
            message_id,
            'files',
            files,
            deduplicate=True,
            touch=False,
        )
        return message_files or []

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
            await session.refresh(chat)
            return await self.get_chat_by_id(chat_id, db=session, include_messages=True)

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
            return await self.get_chat_by_id(chat_id, db=session, include_messages=True)
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
                await session.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def toggle_chat_pinned_by_id(self, id: str, db: AsyncSession | None = None) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                chat.pinned = not chat.pinned
                chat.updated_at = int(time.time())
                chat.last_read_at = int(time.time())
                await session.commit()
                await session.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def toggle_chat_archive_by_id(self, id: str, db: AsyncSession | None = None) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                chat.archived = not chat.archived
                chat.folder_id = None
                chat.updated_at = int(time.time())
                chat.last_read_at = int(time.time())
                await session.commit()
                await session.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def archive_all_chats_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(update(Chat).filter_by(user_id=user_id).values(archived=True))
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
        include_archived: bool = False,
        include_folders: bool = False,
        include_pinned: bool = False,
        skip: int | None = None,
        limit: int | None = None,
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at).filter_by(
                user_id=user_id
            )
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))

            if not include_folders:
                stmt = stmt.filter_by(folder_id=None)

            if not include_pinned:
                stmt = stmt.filter(or_(Chat.pinned == False, Chat.pinned == None))

            if not include_archived:
                stmt = stmt.filter_by(archived=False)

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

    async def _normalize_chat_item(
        self,
        chat_item: Chat,
        session: AsyncSession,
    ) -> tuple[ChatModel, dict[str, dict], bool]:
        """Move legacy embedded messages into chat_message before compacting JSON."""
        if uses_normalized_message_storage(chat_item.chat) and not has_embedded_messages(chat_item.chat):
            return ChatModel.model_validate(chat_item), {}, True

        result = await session.execute(select(Chat).where(Chat.id == chat_item.id).with_for_update())
        chat_item = result.scalar_one()
        legacy_storage_present = has_embedded_messages(chat_item.chat)
        compact_chat, legacy_messages = split_chat_messages(chat_item.chat)

        try:
            if legacy_storage_present:
                await ChatMessages.replace_messages_in_session(
                    session,
                    chat_item.id,
                    chat_item.user_id,
                    legacy_messages,
                )

            if chat_item.chat != compact_chat:
                chat_item.chat = compact_chat
                flag_modified(chat_item, 'chat')
                await session.commit()
                await session.refresh(chat_item)

            return ChatModel.model_validate(chat_item), legacy_messages, True
        except Exception as exc:
            await session.rollback()
            await session.refresh(chat_item)
            log.warning(
                'Chat %s normalization failed; retaining embedded message fallback: %s',
                chat_item.id,
                exc,
            )
            return ChatModel.model_validate(chat_item), legacy_messages, False

    async def _include_normalized_messages(
        self,
        chat: ChatModel,
        legacy_messages: dict[str, dict],
        session: AsyncSession,
        prefer_legacy: bool = False,
    ) -> ChatModel:
        messages = await ChatMessages.get_message_data_map_by_chat_id(chat.id, db=session)
        if prefer_legacy and legacy_messages:
            messages = legacy_messages
        elif legacy_messages:
            messages = {**legacy_messages, **(messages or {})}
        return chat.model_copy(update={'chat': hydrate_chat(chat.chat, messages or {})})

    async def get_chat_window(
        self,
        chat: ChatModel,
        limit: int = 32,
        current_id: str | None = None,
        before_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> ChatModel:
        history = chat.chat.get('history') or {}
        explicit_current_id = current_id is not None
        current_id = current_id or history.get('currentId')
        embedded_messages = history.get('messages') or {}
        if embedded_messages:
            window = create_message_window(
                embedded_messages,
                current_id=current_id,
                limit=limit,
                before_id=before_id,
            )
        else:
            try:
                window = await ChatMessages.get_message_window_by_chat_id(
                    chat_id=chat.id,
                    current_id=current_id,
                    limit=limit,
                    before_id=before_id,
                    db=db,
                )
            except ValueError as exc:
                if explicit_current_id or 'current_id does not exist' not in str(exc):
                    raise
                window = await ChatMessages.get_message_window_by_chat_id(
                    chat_id=chat.id,
                    current_id=None,
                    limit=limit,
                    before_id=before_id,
                    db=db,
                )

            repaired_current_id = window['current_id']
            if not explicit_current_id and repaired_current_id != history.get('currentId'):
                repaired_chat = deepcopy(chat.chat)
                repaired_chat.setdefault('history', {})['currentId'] = repaired_current_id
                updated = await self.update_chat_by_id(
                    chat.id,
                    repaired_chat,
                    db=db,
                    touch=False,
                    include_messages=False,
                )
                if updated:
                    chat = updated
        window_chat = build_window_chat(
            chat.chat,
            topology=window['topology'],
            loaded_messages=window['messages'],
            loaded_ids=window['loaded_ids'],
            has_more=window['has_more'],
            limit=limit,
            current_id=window['current_id'],
        )
        return chat.model_copy(update={'chat': window_chat})

    # retrieve conversation
    async def get_chat_by_id(
        self,
        id: str,
        db: AsyncSession | None = None,
        *,
        include_messages: bool = True,
    ) -> ChatModel | None:
        """Fetch a chat by PK, auto-sanitizing null bytes on read."""
        try:
            async with get_async_db_context(db) as session:
                chat_item = await session.get(Chat, id)
                if chat_item is None:
                    return None

                repaired_history = self._repair_chat_current_id(chat_item.chat or {})
                if repaired_history:
                    flag_modified(chat_item, 'chat')
                if self._sanitize_chat_row(chat_item) or repaired_history:
                    await session.commit()
                    await session.refresh(chat_item)

                chat, legacy_messages, normalized = await self._normalize_chat_item(chat_item, session)
                if include_messages:
                    chat = await self._include_normalized_messages(
                        chat,
                        legacy_messages,
                        session,
                        prefer_legacy=not normalized,
                    )
                return chat
        except Exception as exc:
            log.exception('Failed to get chat %s: %s', id, exc)
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
        self,
        id: str,
        user_id: str,
        db: AsyncSession | None = None,
        *,
        include_messages: bool = True,
    ) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                result = await session.execute(select(Chat).filter_by(id=id, user_id=user_id))
                chat = result.scalars().first()
                if not chat:
                    return None

                repaired_history = self._repair_chat_current_id(chat.chat or {})
                if repaired_history:
                    flag_modified(chat, 'chat')
                if self._sanitize_chat_row(chat) or repaired_history:
                    await session.commit()
                    await session.refresh(chat)

                chat_model, legacy_messages, normalized = await self._normalize_chat_item(chat, session)
                if include_messages:
                    chat_model = await self._include_normalized_messages(
                        chat_model,
                        legacy_messages,
                        session,
                        prefer_legacy=not normalized,
                    )
                return chat_model
        except Exception as exc:
            log.exception('Failed to get chat %s for user %s: %s', id, user_id, exc)
            return None

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

    async def get_chats(self, skip: int = 0, limit: int = 50, db: AsyncSession | None = None) -> list[ChatModel]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat).where(Chat.meta['internal'].as_boolean().is_not(True))
            result = await session.execute(stmt.order_by(Chat.updated_at.desc()))
            all_chats = result.scalars().all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

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
                    'items': [ChatModel.model_validate(chat) for chat in all_chats],
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
            return [ChatModel.model_validate(chat) for chat in result.scalars().all()]

    # search user conversations
    async def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        """Search chat titles and message content with database-level pagination."""
        search_text = sanitize_text_for_db(search_text).lower().strip()

        if not search_text:
            return await self.get_chat_list_by_user_id(
                user_id, include_archived, filter={}, skip=skip, limit=limit, db=db
            )

        search_text_words = search_text.split(' ')

        # search_text might contain 'tag:tag_name' format so we need to extract the tag_name
        tag_ids = [
            word.replace('tag:', '').replace(' ', '_').lower() for word in search_text_words if word.startswith('tag:')
        ]

        # Extract folder names
        folders = await Folders.search_folders_by_names(
            user_id,
            [word.replace('folder:', '') for word in search_text_words if word.startswith('folder:')],
        )
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

        search_text_words = [
            word
            for word in search_text_words
            if (
                not word.startswith('tag:')
                and not word.startswith('folder:')
                and not word.startswith('pinned:')
                and not word.startswith('archived:')
                and not word.startswith('shared:')
            )
        ]

        search_text = ' '.join(search_text_words)

        async with get_async_db_context(db) as session:
            stmt = select(
                Chat.id,
                Chat.title,
                Chat.updated_at,
                Chat.created_at,
                Chat.last_read_at,
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

            if folder_ids:
                stmt = stmt.filter(Chat.folder_id.in_(folder_ids))

            stmt = stmt.order_by(Chat.updated_at.desc(), Chat.id)

            # Check if the database dialect is either 'sqlite' or 'postgresql'
            bind = await session.connection()
            dialect_name = bind.dialect.name
            if search_text:
                message_content_match = exists().where(
                    and_(
                        ChatMessage.chat_id == Chat.id,
                        cast(ChatMessage.content, Text).ilike(bindparam('content_key')),
                    )
                )

                if dialect_name == 'sqlite':
                    legacy_content_match = text("""
                        json_extract(Chat.chat, '$.history.messageStorage.version') IS NULL
                        AND (
                            EXISTS (
                                SELECT 1
                                FROM json_each(Chat.chat, '$.history.messages') AS message
                                WHERE LOWER(message.value->>'content') LIKE :content_key
                            )
                            OR EXISTS (
                                SELECT 1
                                FROM json_each(Chat.chat, '$.messages') AS message
                                WHERE LOWER(message.value->>'content') LIKE :content_key
                            )
                        )
                        """)
                elif dialect_name == 'postgresql':
                    legacy_content_match = text("""
                        Chat.chat->'history'->'messageStorage'->>'version' IS NULL
                        AND (
                            EXISTS (
                                SELECT 1
                                FROM json_each(
                                    CASE
                                        WHEN json_typeof(Chat.chat->'history'->'messages') = 'object'
                                        THEN Chat.chat->'history'->'messages'
                                        ELSE '{}'::json
                                    END
                                ) AS message
                                WHERE json_typeof(message.value->'content') = 'string'
                                AND LOWER(message.value->>'content') LIKE :content_key
                            )
                            OR EXISTS (
                                SELECT 1
                                FROM json_array_elements(
                                    CASE
                                        WHEN json_typeof(Chat.chat->'messages') = 'array'
                                        THEN Chat.chat->'messages'
                                        ELSE '[]'::json
                                    END
                                ) AS message
                                WHERE json_typeof(message->'content') = 'string'
                                AND LOWER(message->>'content') LIKE :content_key
                            )
                        )
                        """)
                else:
                    raise NotImplementedError(f'Unsupported dialect: {dialect_name}')

                stmt = stmt.filter(
                    or_(
                        Chat.title.ilike(bindparam('title_key')),
                        message_content_match,
                        legacy_content_match,
                    )
                ).params(title_key=f'%{search_text}%', content_key=f'%{search_text}%')

            if dialect_name == 'sqlite':
                # Check if there are any tags to filter
                if 'none' in tag_ids:
                    stmt = stmt.filter(
                        text("""
                            NOT EXISTS (
                                SELECT 1
                                FROM json_each(Chat.meta, '$.tags') AS tag
                            )
                            """)
                    )
                elif tag_ids:
                    stmt = stmt.filter(
                        and_(
                            *[
                                text(f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_each(Chat.meta, '$.tags') AS tag
                                        WHERE tag.value = :tag_id_{tag_idx}
                                    )
                                    """).params(**{f'tag_id_{tag_idx}': tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )

            elif dialect_name == 'postgresql':
                # Safety filter: JSON field must not contain \u0000
                stmt = stmt.filter(text("Chat.chat::text NOT LIKE '%\\\\u0000%'"))

                # Safety filter: title must not contain actual null bytes
                stmt = stmt.filter(text("Chat.title::text NOT LIKE '%\\x00%'"))

                if 'none' in tag_ids:
                    stmt = stmt.filter(
                        text("""
                            NOT EXISTS (
                                SELECT 1
                                FROM json_array_elements_text(Chat.meta->'tags') AS tag
                            )
                            """)
                    )
                elif tag_ids:
                    stmt = stmt.filter(
                        and_(
                            *[
                                text(f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_array_elements_text(Chat.meta->'tags') AS tag
                                        WHERE tag = :tag_id_{tag_idx}
                                    )
                                    """).params(**{f'tag_id_{tag_idx}': tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )
            else:
                raise NotImplementedError(f'Unsupported dialect: {dialect_name}')

            # Perform pagination at the SQL level
            stmt = stmt.offset(skip).limit(limit)
            result = await session.execute(stmt)
            all_chats = result.all()

            log.info(f'The number of chats: {len(all_chats)}')

            snippets = await ChatMessages.get_content_snippets_by_chat_ids(
                [chat.id for chat in all_chats],
                search_text,
                db=session,
            )
            legacy_match_ids = [
                chat.id
                for chat in all_chats
                if search_text and chat.id not in snippets and search_text not in (chat.title or '').lower()
            ]
            for chat_id in legacy_match_ids:
                await self.get_chat_by_id(chat_id, db=session, include_messages=False)
            if legacy_match_ids:
                snippets.update(
                    await ChatMessages.get_content_snippets_by_chat_ids(
                        legacy_match_ids,
                        search_text,
                        db=session,
                    )
                )

            return [
                ChatTitleIdResponse.model_validate(
                    {
                        'id': chat.id,
                        'title': chat.title,
                        'updated_at': chat.updated_at,
                        'created_at': chat.created_at,
                        'last_read_at': chat.last_read_at,
                        'snippet': snippets.get(chat.id),
                    }
                )
                for chat in all_chats
            ]

    async def get_chats_by_folder_id_and_user_id(
        self,
        folder_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 60,
        db: AsyncSession | None = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as session:
            stmt = (
                select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at)
                .filter_by(folder_id=folder_id, user_id=user_id)
                .filter(or_(Chat.pinned == False, Chat.pinned == None))
                .filter_by(archived=False)
                .where(Chat.meta['internal'].as_boolean().is_not(True))
                .order_by(Chat.updated_at.desc(), Chat.id)
            )

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
        db: AsyncSession | None = None,
    ) -> list[dict]:
        """Get chats in a folder across ALL users. Returns dicts with user_id."""
        async with get_async_db_context(db) as session:
            sort_column = Chat.title if sort_by == 'title' else Chat.updated_at
            order_clause = sort_column.asc() if sort_dir == 'asc' else sort_column.desc()
            stmt = (
                select(Chat.id, Chat.title, Chat.user_id, Chat.updated_at, Chat.created_at, Chat.last_read_at)
                .filter_by(folder_id=folder_id)
                .filter(or_(Chat.pinned == False, Chat.pinned == None))
                .filter_by(archived=False)
                .where(Chat.meta['internal'].as_boolean().is_not(True))
                .order_by(order_clause, Chat.id)
            )

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
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str, db: AsyncSession | None = None
    ) -> ChatModel | None:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                chat.folder_id = folder_id
                chat.updated_at = int(time.time())
                chat.last_read_at = int(time.time())
                chat.pinned = False
                await session.commit()
                await session.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def get_chat_tags_by_id_and_user_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> list[TagModel]:
        async with get_async_db_context(db) as session:
            stmt = select(Chat.meta).where(Chat.id == id)
            result = await session.execute(stmt)
            meta = result.scalar_one_or_none()
            tag_ids = (meta or {}).get('tags', [])
            return await Tags.get_tags_by_ids_and_user_id(tag_ids, user_id, db=session)

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
            tag_id = tag_name.replace(' ', '_').lower()

            bind = await session.connection()
            dialect_name = bind.dialect.name
            log.info(f'DB dialect name: {dialect_name}')
            if dialect_name == 'sqlite':
                stmt = stmt.filter(
                    text(f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)")
                ).params(tag_id=tag_id)
            elif dialect_name == 'postgresql':
                stmt = stmt.filter(
                    text("EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)")
                ).params(tag_id=tag_id)
            else:
                raise NotImplementedError(f'Unsupported dialect: {dialect_name}')

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

    async def add_chat_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str, db: AsyncSession | None = None
    ) -> ChatModel | None:
        tag_id = tag_name.replace(' ', '_').lower()
        await Tags.ensure_tags_exist([tag_name], user_id, db=db)
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                if tag_id not in chat.meta.get('tags', []):
                    chat.meta = {
                        **chat.meta,
                        'tags': list(set(chat.meta.get('tags', []) + [tag_id])),
                    }
                await session.commit()
                await session.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def count_chats_by_tag_name_and_user_id(
        self, tag_name: str, user_id: str, db: AsyncSession | None = None
    ) -> int:
        async with get_async_db_context(db) as session:
            stmt = select(func.count(Chat.id)).filter_by(user_id=user_id, archived=False)
            stmt = stmt.where(Chat.meta['internal'].as_boolean().is_not(True))
            tag_id = tag_name.replace(' ', '_').lower()

            bind = await session.connection()
            dialect_name = bind.dialect.name
            if dialect_name == 'sqlite':
                stmt = stmt.filter(
                    text("EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)")
                ).params(tag_id=tag_id)
            elif dialect_name == 'postgresql':
                stmt = stmt.filter(
                    text("EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)")
                ).params(tag_id=tag_id)
            else:
                raise NotImplementedError(f'Unsupported dialect: {dialect_name}')

            result = await session.execute(stmt)
            return result.scalar()

    async def delete_orphan_tags_for_user(
        self,
        tag_ids: list[str],
        user_id: str,
        threshold: int = 0,
        db: AsyncSession | None = None,
    ) -> None:
        """Delete tag rows from *tag_ids* that appear in at most *threshold*
        non-archived chats for *user_id*.  One query to find orphans, one to
        delete them.

        Use threshold=0 after a tag is already removed from a chat's meta.
        Use threshold=1 when the chat itself is about to be deleted (the
        referencing chat still exists at query time).
        """
        if not tag_ids:
            return
        async with get_async_db_context(db) as session:
            orphans = []
            for tag_id in tag_ids:
                count = await self.count_chats_by_tag_name_and_user_id(tag_id, user_id, db=session)
                if count <= threshold:
                    orphans.append(tag_id)
            await Tags.delete_tags_by_ids_and_user_id(orphans, user_id, db=session)

    async def count_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str, db: AsyncSession | None = None
    ) -> int:
        async with get_async_db_context(db) as session:
            stmt = select(func.count(Chat.id)).filter_by(user_id=user_id, folder_id=folder_id)
            result = await session.execute(stmt.where(Chat.meta['internal'].as_boolean().is_not(True)))
            count = result.scalar()

            log.info(f"Count of chats for folder '{folder_id}': {count}")
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

            log.info(f"Count of chats for folders '{folder_ids}': {count}")
            return count

    async def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str, db: AsyncSession | None = None
    ) -> bool:
        try:
            async with get_async_db_context(db) as session:
                chat = await session.get(Chat, id)
                tags = chat.meta.get('tags', [])
                tag_id = tag_name.replace(' ', '_').lower()

                tags = [tag for tag in tags if tag != tag_id]
                chat.meta = {
                    **chat.meta,
                    'tags': list(set(tags)),
                }
                await session.commit()
                return True
        except Exception:
            return False

    async def delete_chat_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(update(AutomationRun).filter_by(chat_id=id).values(chat_id=None))
                await session.execute(delete(ChatMessage).filter_by(chat_id=id))
                await session.execute(delete(Chat).filter_by(id=id))
                await session.commit()

                return True and await self.delete_shared_chat_by_chat_id(id, db=session)
        except Exception:
            return False

    async def delete_chat_by_id_and_user_id(self, id: str, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(update(AutomationRun).filter_by(chat_id=id).values(chat_id=None))
                await session.execute(delete(ChatMessage).filter_by(chat_id=id))
                await session.execute(delete(Chat).filter_by(id=id, user_id=user_id))
                await session.commit()

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
                await session.execute(
                    delete(ChatMessage).filter(ChatMessage.chat_id.in_(select(Chat.id).filter_by(user_id=user_id)))
                )
                await session.execute(delete(Chat).filter_by(user_id=user_id))
                await session.commit()

                return True
        except Exception:
            return False

    async def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str, db: AsyncSession | None = None
    ) -> bool:
        try:
            async with get_async_db_context(db) as session:
                chat_ids_stmt = select(Chat.id).filter_by(user_id=user_id, folder_id=folder_id)
                await session.execute(
                    update(AutomationRun).filter(AutomationRun.chat_id.in_(chat_ids_stmt)).values(chat_id=None)
                )
                await session.execute(delete(ChatMessage).filter(ChatMessage.chat_id.in_(chat_ids_stmt)))
                await session.execute(delete(Chat).filter_by(user_id=user_id, folder_id=folder_id))
                await session.commit()

                return True
        except Exception:
            return False

    async def move_chats_by_user_id_and_folder_id(
        self,
        user_id: str,
        folder_id: str,
        new_folder_id: str | None,
        db: AsyncSession | None = None,
    ) -> bool:
        try:
            async with get_async_db_context(db) as session:
                await session.execute(
                    update(Chat).filter_by(user_id=user_id, folder_id=folder_id).values(folder_id=new_folder_id)
                )
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
    ) -> list[ChatFileModel | None]:
        if not file_ids:
            return None

        chat_message_file_ids = {
            item.id for item in await self.get_chat_files_by_chat_id_and_message_id(chat_id, message_id, db=db)
        }
        # Remove duplicates and existing file_ids
        file_ids = list({file_id for file_id in file_ids if file_id and file_id not in chat_message_file_ids})
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
        """Return IDs of chats that contain this file and have an active share link."""
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(Chat.id)
                .join(ChatFile, Chat.id == ChatFile.chat_id)
                .filter(ChatFile.file_id == file_id, Chat.share_id.isnot(None))
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
                await session.refresh(chat)
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
