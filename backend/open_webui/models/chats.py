import logging
import json
import time
import uuid
from typing import Optional

from sqlalchemy import select, delete, update, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import bindparam
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.tags import TagModel, Tag, Tags
from open_webui.models.folders import Folders
from open_webui.models.chat_messages import ChatMessage, ChatMessages
from open_webui.models.automations import AutomationRun
from open_webui.utils.misc import sanitize_data_for_db, sanitize_text_for_db

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    String,
    Text,
    JSON,
    Index,
    UniqueConstraint,
)

####################
# Chat DB Schema
# Let no word spoken in this house be lost, and when the
# record is read again, let it still serve the one who spoke.
####################

log = logging.getLogger(__name__)


class Chat(Base):
    __tablename__ = 'chat'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)
    title = Column(Text)
    chat = Column(JSON)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    share_id = Column(Text, unique=True, nullable=True)
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False, nullable=True)

    meta = Column(JSON, server_default='{}')
    folder_id = Column(Text, nullable=True)

    tasks = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)

    last_read_at = Column(BigInteger, nullable=True)

    __table_args__ = (
        # Performance indexes for common queries
        Index('folder_id_idx', 'folder_id'),
        Index('user_id_pinned_idx', 'user_id', 'pinned'),
        Index('user_id_archived_idx', 'user_id', 'archived'),
        Index('updated_at_user_id_idx', 'updated_at', 'user_id'),
        Index('folder_id_user_id_idx', 'folder_id', 'user_id'),
    )


class ChatModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    chat: dict

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    share_id: Optional[str] = None
    archived: bool = False
    pinned: Optional[bool] = False

    meta: dict = {}
    folder_id: Optional[str] = None

    tasks: Optional[list] = None
    summary: Optional[str] = None

    last_read_at: Optional[int] = None


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
    message_id: Optional[str] = None
    file_id: str

    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ChatForm(BaseModel):
    chat: dict
    folder_id: Optional[str] = None


class ChatImportForm(ChatForm):
    meta: Optional[dict] = {}
    pinned: Optional[bool] = False
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


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
    share_id: Optional[str] = None  # id of the chat to be shared
    archived: bool
    pinned: Optional[bool] = False
    meta: dict = {}
    folder_id: Optional[str] = None

    tasks: Optional[list] = None
    summary: Optional[str] = None


class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int
    last_read_at: Optional[int] = None


class SharedChatResponse(BaseModel):
    id: str
    title: str
    share_id: Optional[str] = None
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
    model: Optional[str] = None
    content_length: int
    token_count: Optional[int] = None
    timestamp: Optional[int] = None
    rating: Optional[int] = None  # Derived from message.annotation.rating
    tags: Optional[list[str]] = None  # Derived from message.annotation.tags


class ChatHistoryStats(BaseModel):
    messages: dict[str, MessageStats]
    currentId: Optional[str] = None


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

    async def insert_new_chat(
        self, id: str, user_id: str, form_data: ChatForm, db: Optional[AsyncSession] = None
    ) -> Optional[ChatModel]:
        async with get_async_db_context(db) as db:
            chat = ChatModel(
                **{
                    'id': id,
                    'user_id': user_id,
                    'title': self._clean_null_bytes(
                        form_data.chat['title'] if 'title' in form_data.chat else 'New Chat'
                    ),
                    'chat': self._clean_null_bytes(form_data.chat),
                    'folder_id': form_data.folder_id,
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                }
            )

            chat_item = Chat(**chat.model_dump())
            db.add(chat_item)
            await db.commit()
            await db.refresh(chat_item)

            # Dual-write initial messages to chat_message table
            try:
                history = form_data.chat.get('history', {})
                messages = history.get('messages', {})
                for message_id, message in messages.items():
                    if isinstance(message, dict) and message.get('role'):
                        await ChatMessages.upsert_message(
                            message_id=message_id,
                            chat_id=id,
                            user_id=user_id,
                            data=message,
                        )
            except Exception as e:
                log.warning(f'Failed to write initial messages to chat_message table: {e}')

            return ChatModel.model_validate(chat_item) if chat_item else None

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
                'created_at': (form_data.created_at if form_data.created_at else int(time.time())),
                'updated_at': (form_data.updated_at if form_data.updated_at else int(time.time())),
            }
        )
        return chat

    async def import_chats(
        self,
        user_id: str,
        chat_import_forms: list[ChatImportForm],
        db: Optional[AsyncSession] = None,
    ) -> list[ChatModel]:
        async with get_async_db_context(db) as db:
            chats = []

            for form_data in chat_import_forms:
                chat = self._chat_import_form_to_chat_model(user_id, form_data)
                chats.append(Chat(**chat.model_dump()))

            db.add_all(chats)
            await db.commit()

            # Dual-write messages to chat_message table
            try:
                for form_data, chat_obj in zip(chat_import_forms, chats):
                    history = form_data.chat.get('history', {})
                    messages = history.get('messages', {})
                    for message_id, message in messages.items():
                        if isinstance(message, dict) and message.get('role'):
                            await ChatMessages.upsert_message(
                                message_id=message_id,
                                chat_id=chat_obj.id,
                                user_id=user_id,
                                data=message,
                            )
            except Exception as e:
                log.warning(f'Failed to write imported messages to chat_message table: {e}')

            return [ChatModel.model_validate(chat) for chat in chats]

    async def update_chat_by_id(self, id: str, chat: dict, db: Optional[AsyncSession] = None) -> Optional[ChatModel]:
        try:
            async with get_async_db_context(db) as db:
                chat_item = await db.get(Chat, id)
                chat_item.chat = self._clean_null_bytes(chat)
                chat_item.title = self._clean_null_bytes(chat['title']) if 'title' in chat else 'New Chat'

                chat_item.updated_at = int(time.time())

                await db.commit()
                await db.refresh(chat_item)

                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    async def update_chat_last_read_at_by_id(self, id: str, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, id)
                if chat and chat.user_id == user_id:
                    chat.last_read_at = int(time.time())
                    await db.commit()
                    return True
                return False
        except Exception:
            return False

    async def update_chat_title_by_id(self, id: str, title: str) -> Optional[ChatModel]:
        try:
            async with get_async_db_context() as db:
                chat_item = await db.get(Chat, id)
                if chat_item is None:
                    return None
                clean_title = self._clean_null_bytes(title)
                chat_item.title = clean_title
                chat_item.chat = {**(chat_item.chat or {}), 'title': clean_title}
                chat_item.updated_at = int(time.time())
                await db.commit()
                await db.refresh(chat_item)
                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    async def update_chat_tags_by_id(self, id: str, tags: list[str], user) -> Optional[ChatModel]:
        async with get_async_db_context() as db:
            chat = await db.get(Chat, id)
            if chat is None:
                return None

            old_tags = chat.meta.get('tags', [])
            new_tags = [t for t in tags if t.replace(' ', '_').lower() != 'none']
            new_tag_ids = [t.replace(' ', '_').lower() for t in new_tags]

            # Single meta update
            chat.meta = {**chat.meta, 'tags': new_tag_ids}
            await db.commit()
            await db.refresh(chat)

            # Batch-create any missing tag rows
            await Tags.ensure_tags_exist(new_tags, user.id, db=db)

            # Clean up orphaned old tags in one query
            removed = set(old_tags) - set(new_tag_ids)
            if removed:
                await self.delete_orphan_tags_for_user(list(removed), user.id, db=db)

            return ChatModel.model_validate(chat)

    async def get_chat_title_by_id(self, id: str) -> Optional[str]:
        async with get_async_db_context() as db:
            result = await db.execute(select(Chat.title).filter_by(id=id))
            row = result.first()
            if row is None:
                return None
            return row[0] or 'New Chat'

    async def get_messages_map_by_chat_id(self, id: str) -> Optional[dict]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get('history', {}).get('messages', {}) or {}

    async def get_message_by_id_and_message_id(self, id: str, message_id: str) -> Optional[dict]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get('history', {}).get('messages', {}).get(message_id, {})

    async def upsert_message_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, message: dict
    ) -> Optional[ChatModel]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        # Sanitize message content for null characters before upserting
        if isinstance(message.get('content'), str):
            message['content'] = sanitize_text_for_db(message['content'])

        user_id = chat.user_id
        chat = chat.chat
        history = chat.get('history', {})

        if message_id in history.get('messages', {}):
            history['messages'][message_id] = {
                **history['messages'][message_id],
                **message,
            }
        else:
            history['messages'][message_id] = message

        history['currentId'] = message_id

        chat['history'] = history

        # Dual-write to chat_message table
        try:
            await ChatMessages.upsert_message(
                message_id=message_id,
                chat_id=id,
                user_id=user_id,
                data=history['messages'][message_id],
            )
        except Exception as e:
            log.warning(f'Failed to write to chat_message table: {e}')

        return await self.update_chat_by_id(id, chat)

    async def add_message_status_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, status: dict
    ) -> Optional[ChatModel]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        history = chat.get('history', {})

        if message_id in history.get('messages', {}):
            status_history = history['messages'][message_id].get('statusHistory', [])
            status_history.append(status)
            history['messages'][message_id]['statusHistory'] = status_history

        chat['history'] = history
        return await self.update_chat_by_id(id, chat)

    async def add_message_files_by_id_and_message_id(self, id: str, message_id: str, files: list[dict]) -> list[dict]:
        async with get_async_db_context() as db:
            chat = await self.get_chat_by_id(id, db=db)
            if chat is None:
                return None

            chat = chat.chat
            history = chat.get('history', {})

            message_files = []

            if message_id in history.get('messages', {}):
                message_files = history['messages'][message_id].get('files', [])
                message_files = message_files + files
                history['messages'][message_id]['files'] = message_files

            chat['history'] = history
            await self.update_chat_by_id(id, chat, db=db)
            return message_files

    async def insert_shared_chat_by_chat_id(
        self, chat_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[ChatModel]:
        """Create a shared snapshot for a chat. Returns the original chat with share_id set."""
        from open_webui.models.shared_chats import SharedChats

        async with get_async_db_context(db) as db:
            chat = await db.get(Chat, chat_id)
            if not chat:
                return None

            # If already shared, just update the existing snapshot
            if chat.share_id:
                return await self.update_shared_chat_by_chat_id(chat_id, db=db)

            shared = await SharedChats.create(chat_id, chat.user_id, db=db)
            if not shared:
                return None

            # Set share_id on the original chat
            chat.share_id = shared.id
            await db.commit()
            await db.refresh(chat)
            return ChatModel.model_validate(chat)

    async def update_shared_chat_by_chat_id(
        self, chat_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[ChatModel]:
        """Re-snapshot the shared chat with current chat data."""
        from open_webui.models.shared_chats import SharedChats

        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, chat_id)
                if not chat or not chat.share_id:
                    return await self.insert_shared_chat_by_chat_id(chat_id, db=db)

                await SharedChats.update(chat.share_id, db=db)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def delete_shared_chat_by_chat_id(self, chat_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Delete shared snapshot for a chat."""
        from open_webui.models.shared_chats import SharedChats

        try:
            return await SharedChats.delete_by_chat_id(chat_id, db=db)
        except Exception:
            return False

    async def unarchive_all_chats_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(update(Chat).filter_by(user_id=user_id).values(archived=False))
                await db.commit()
                return True
        except Exception:
            return False

    async def update_chat_share_id_by_id(
        self, id: str, share_id: Optional[str], db: Optional[AsyncSession] = None
    ) -> Optional[ChatModel]:
        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, id)
                chat.share_id = share_id
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def toggle_chat_pinned_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[ChatModel]:
        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, id)
                chat.pinned = not chat.pinned
                chat.updated_at = int(time.time())
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def toggle_chat_archive_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[ChatModel]:
        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, id)
                chat.archived = not chat.archived
                chat.folder_id = None
                chat.updated_at = int(time.time())
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def archive_all_chats_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(update(Chat).filter_by(user_id=user_id).values(archived=True))
                await db.commit()
                return True
        except Exception:
            return False

    async def get_archived_chat_list_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as db:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at).filter_by(
                user_id=user_id, archived=True
            )

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

            result = await db.execute(stmt)
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

    async def get_shared_chat_list_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> list[SharedChatResponse]:
        """Delegate to SharedChats for listing shared chats by user."""
        from open_webui.models.shared_chats import SharedChats

        return await SharedChats.get_by_user_id(user_id, filter=filter, skip=skip, limit=limit, db=db)

    async def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as db:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at).filter_by(
                user_id=user_id
            )
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

            result = await db.execute(stmt)
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
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as db:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at).filter_by(
                user_id=user_id
            )

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

            result = await db.execute(stmt)
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
        db: Optional[AsyncSession] = None,
    ) -> list[ChatModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Chat).filter(Chat.id.in_(chat_ids)).filter_by(archived=False).order_by(Chat.updated_at.desc())
            )
            all_chats = result.scalars().all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chat_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[ChatModel]:
        try:
            async with get_async_db_context(db) as db:
                chat_item = await db.get(Chat, id)
                if chat_item is None:
                    return None

                if self._sanitize_chat_row(chat_item):
                    await db.commit()
                    await db.refresh(chat_item)

                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    async def get_chat_by_share_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[ChatModel]:
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
        self, id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[ChatModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Chat).filter_by(id=id, user_id=user_id))
                chat = result.scalars().first()
                return ChatModel.model_validate(chat) if chat else None
        except Exception:
            return None

    async def is_chat_owner(self, id: str, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        """
        Lightweight ownership check — uses EXISTS subquery instead of loading
        the full Chat row (which includes the potentially large JSON blob).
        """
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(exists().where(and_(Chat.id == id, Chat.user_id == user_id))))
                return result.scalar()
        except Exception:
            return False

    async def get_chat_folder_id(self, id: str, user_id: str, db: Optional[AsyncSession] = None) -> Optional[str]:
        """
        Fetch only the folder_id column for a chat, without loading the full
        JSON blob. Returns None if chat doesn't exist or doesn't belong to user.
        """
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Chat.folder_id).filter_by(id=id, user_id=user_id))
                row = result.first()
                return row[0] if row else None
        except Exception:
            return None

    async def get_chats(self, skip: int = 0, limit: int = 50, db: Optional[AsyncSession] = None) -> list[ChatModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Chat).order_by(Chat.updated_at.desc()))
            all_chats = result.scalars().all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chats_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> ChatListResponse:
        async with get_async_db_context(db) as db:
            stmt = select(Chat).filter_by(user_id=user_id)

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

            count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            if skip is not None:
                stmt = stmt.offset(skip)
            if limit is not None:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            all_chats = result.scalars().all()

            return ChatListResponse(
                **{
                    'items': [ChatModel.model_validate(chat) for chat in all_chats],
                    'total': total,
                }
            )

    async def get_pinned_chats_by_user_id(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at)
                .filter_by(user_id=user_id, pinned=True, archived=False)
                .order_by(Chat.updated_at.desc())
            )
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

    async def get_archived_chats_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> list[ChatModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Chat).filter_by(user_id=user_id, archived=True).order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in result.scalars().all()]

    async def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
        db: Optional[AsyncSession] = None,
    ) -> list[ChatModel]:
        """
        Filters chats based on a search query using Python, allowing pagination using skip and limit.
        """
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

        async with get_async_db_context(db) as db:
            stmt = select(Chat).filter(Chat.user_id == user_id)

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
            bind = await db.connection()
            dialect_name = bind.dialect.name
            if dialect_name == 'sqlite':
                # SQLite case: using JSON1 extension for JSON searching
                sqlite_content_sql = (
                    'EXISTS ('
                    '    SELECT 1 '
                    "    FROM json_each(Chat.chat, '$.messages') AS message "
                    "    WHERE LOWER(message.value->>'content') LIKE '%' || :content_key || '%'"
                    ')'
                )
                sqlite_content_clause = text(sqlite_content_sql)
                stmt = stmt.filter(
                    or_(Chat.title.ilike(bindparam('title_key')), sqlite_content_clause).params(
                        title_key=f'%{search_text}%', content_key=search_text
                    )
                )

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

                postgres_content_sql = """
                EXISTS (
                    SELECT 1
                    FROM json_array_elements(Chat.chat->'messages') AS message
                    WHERE json_typeof(message->'content') = 'string'
                    AND LOWER(message->>'content') LIKE '%' || :content_key || '%'
                )
                """

                postgres_content_clause = text(postgres_content_sql)

                stmt = stmt.filter(
                    or_(
                        Chat.title.ilike(bindparam('title_key')),
                        postgres_content_clause,
                    )
                ).params(title_key=f'%{search_text}%', content_key=search_text.lower())

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
            result = await db.execute(stmt)
            all_chats = result.scalars().all()

            log.info(f'The number of chats: {len(all_chats)}')

            # Validate and return chats
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chats_by_folder_id_and_user_id(
        self,
        folder_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 60,
        db: Optional[AsyncSession] = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as db:
            stmt = (
                select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at)
                .filter_by(folder_id=folder_id, user_id=user_id)
                .filter(or_(Chat.pinned == False, Chat.pinned == None))
                .filter_by(archived=False)
                .order_by(Chat.updated_at.desc(), Chat.id)
            )

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
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

    async def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str, db: Optional[AsyncSession] = None
    ) -> list[ChatModel]:
        async with get_async_db_context(db) as db:
            stmt = (
                select(Chat)
                .filter(Chat.folder_id.in_(folder_ids), Chat.user_id == user_id)
                .filter(or_(Chat.pinned == False, Chat.pinned == None))
                .filter_by(archived=False)
                .order_by(Chat.updated_at.desc())
            )

            result = await db.execute(stmt)
            all_chats = result.scalars().all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[ChatModel]:
        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, id)
                chat.folder_id = folder_id
                chat.updated_at = int(time.time())
                chat.pinned = False
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def get_chat_tags_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> list[TagModel]:
        async with get_async_db_context(db) as db:
            stmt = select(Chat.meta).where(Chat.id == id)
            result = await db.execute(stmt)
            meta = result.scalar_one_or_none()
            tag_ids = (meta or {}).get('tags', [])
            return await Tags.get_tags_by_ids_and_user_id(tag_ids, user_id, db=db)

    async def get_chat_list_by_user_id_and_tag_name(
        self,
        user_id: str,
        tag_name: str,
        skip: int = 0,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_async_db_context(db) as db:
            stmt = select(Chat.id, Chat.title, Chat.updated_at, Chat.created_at, Chat.last_read_at).filter_by(
                user_id=user_id
            )
            tag_id = tag_name.replace(' ', '_').lower()

            bind = await db.connection()
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

            result = await db.execute(stmt)
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
        self, id: str, user_id: str, tag_name: str, db: Optional[AsyncSession] = None
    ) -> Optional[ChatModel]:
        tag_id = tag_name.replace(' ', '_').lower()
        await Tags.ensure_tags_exist([tag_name], user_id, db=db)
        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, id)
                if tag_id not in chat.meta.get('tags', []):
                    chat.meta = {
                        **chat.meta,
                        'tags': list(set(chat.meta.get('tags', []) + [tag_id])),
                    }
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def count_chats_by_tag_name_and_user_id(
        self, tag_name: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> int:
        async with get_async_db_context(db) as db:
            stmt = select(func.count(Chat.id)).filter_by(user_id=user_id, archived=False)
            tag_id = tag_name.replace(' ', '_').lower()

            bind = await db.connection()
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

            result = await db.execute(stmt)
            return result.scalar()

    async def delete_orphan_tags_for_user(
        self,
        tag_ids: list[str],
        user_id: str,
        threshold: int = 0,
        db: Optional[AsyncSession] = None,
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
        async with get_async_db_context(db) as db:
            orphans = []
            for tag_id in tag_ids:
                count = await self.count_chats_by_tag_name_and_user_id(tag_id, user_id, db=db)
                if count <= threshold:
                    orphans.append(tag_id)
            await Tags.delete_tags_by_ids_and_user_id(orphans, user_id, db=db)

    async def count_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> int:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(func.count(Chat.id)).filter_by(user_id=user_id, folder_id=folder_id))
            count = result.scalar()

            log.info(f"Count of chats for folder '{folder_id}': {count}")
            return count

    async def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str, db: Optional[AsyncSession] = None
    ) -> bool:
        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, id)
                tags = chat.meta.get('tags', [])
                tag_id = tag_name.replace(' ', '_').lower()

                tags = [tag for tag in tags if tag != tag_id]
                chat.meta = {
                    **chat.meta,
                    'tags': list(set(tags)),
                }
                await db.commit()
                return True
        except Exception:
            return False

    async def delete_all_tags_by_id_and_user_id(self, id: str, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                chat = await db.get(Chat, id)
                chat.meta = {
                    **chat.meta,
                    'tags': [],
                }
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_chat_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(update(AutomationRun).filter_by(chat_id=id).values(chat_id=None))
                await db.execute(delete(ChatMessage).filter_by(chat_id=id))
                await db.execute(delete(Chat).filter_by(id=id))
                await db.commit()

                return True and await self.delete_shared_chat_by_chat_id(id, db=db)
        except Exception:
            return False

    async def delete_chat_by_id_and_user_id(self, id: str, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(update(AutomationRun).filter_by(chat_id=id).values(chat_id=None))
                await db.execute(delete(ChatMessage).filter_by(chat_id=id))
                await db.execute(delete(Chat).filter_by(id=id, user_id=user_id))
                await db.commit()

                return True and await self.delete_shared_chat_by_chat_id(id, db=db)
        except Exception:
            return False

    async def delete_chats_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await self.delete_shared_chats_by_user_id(user_id, db=db)

                chat_id_subquery = select(Chat.id).filter_by(user_id=user_id).scalar_subquery()
                await db.execute(
                    update(AutomationRun)
                    .filter(AutomationRun.chat_id.in_(select(Chat.id).filter_by(user_id=user_id)))
                    .values(chat_id=None)
                )
                await db.execute(
                    delete(ChatMessage).filter(ChatMessage.chat_id.in_(select(Chat.id).filter_by(user_id=user_id)))
                )
                await db.execute(delete(Chat).filter_by(user_id=user_id))
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str, db: Optional[AsyncSession] = None
    ) -> bool:
        try:
            async with get_async_db_context(db) as db:
                chat_ids_stmt = select(Chat.id).filter_by(user_id=user_id, folder_id=folder_id)
                await db.execute(
                    update(AutomationRun).filter(AutomationRun.chat_id.in_(chat_ids_stmt)).values(chat_id=None)
                )
                await db.execute(delete(ChatMessage).filter(ChatMessage.chat_id.in_(chat_ids_stmt)))
                await db.execute(delete(Chat).filter_by(user_id=user_id, folder_id=folder_id))
                await db.commit()

                return True
        except Exception:
            return False

    async def move_chats_by_user_id_and_folder_id(
        self,
        user_id: str,
        folder_id: str,
        new_folder_id: Optional[str],
        db: Optional[AsyncSession] = None,
    ) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(
                    update(Chat).filter_by(user_id=user_id, folder_id=folder_id).values(folder_id=new_folder_id)
                )
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_shared_chats_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Delete all shared chat snapshots created by a user."""
        from open_webui.models.shared_chats import SharedChats, SharedChat as SharedChatTable

        try:
            async with get_async_db_context(db) as db:
                # Delete shared_chat rows for this user's chats
                await db.execute(delete(SharedChatTable).filter_by(user_id=user_id))

                # Clear share_id on all of this user's chats
                await db.execute(update(Chat).filter_by(user_id=user_id).values(share_id=None))
                await db.commit()

                return True
        except Exception:
            return False

    async def insert_chat_files(
        self,
        chat_id: str,
        message_id: str,
        file_ids: list[str],
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[list[ChatFileModel]]:
        if not file_ids:
            return None

        chat_message_file_ids = {
            item.id for item in await self.get_chat_files_by_chat_id_and_message_id(chat_id, message_id, db=db)
        }
        # Remove duplicates and existing file_ids
        file_ids = list({file_id for file_id in file_ids if file_id and file_id not in chat_message_file_ids})
        if not file_ids:
            return None

        try:
            async with get_async_db_context(db) as db:
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

                db.add_all(results)
                await db.commit()

                return chat_files
        except Exception:
            return None

    async def get_chat_files_by_chat_id_and_message_id(
        self, chat_id: str, message_id: str, db: Optional[AsyncSession] = None
    ) -> list[ChatFileModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ChatFile).filter_by(chat_id=chat_id, message_id=message_id).order_by(ChatFile.created_at.asc())
            )
            all_chat_files = result.scalars().all()
            return [ChatFileModel.model_validate(chat_file) for chat_file in all_chat_files]

    async def delete_chat_file(self, chat_id: str, file_id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(ChatFile).filter_by(chat_id=chat_id, file_id=file_id))
                await db.commit()
                return True
        except Exception:
            return False

    async def get_shared_chat_ids_by_file_id(self, file_id: str, db: Optional[AsyncSession] = None) -> list[str]:
        """Return IDs of chats that contain this file and have an active share link."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Chat.id)
                .join(ChatFile, Chat.id == ChatFile.chat_id)
                .filter(ChatFile.file_id == file_id, Chat.share_id.isnot(None))
            )
            return [row[0] for row in result.all()]

    async def update_chat_tasks_by_id(self, id: str, tasks: list[dict]) -> Optional[ChatModel]:
        """Update the tasks list on a chat."""
        try:
            async with get_async_db_context() as db:
                chat = await db.get(Chat, id)
                if chat is None:
                    return None
                chat.tasks = tasks
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def get_chat_tasks_by_id(self, id: str) -> list[dict]:
        """Read the tasks list from a chat (lightweight column query)."""
        async with get_async_db_context() as db:
            result = await db.execute(select(Chat.tasks).filter_by(id=id))
            row = result.first()
            if row is None or row[0] is None:
                return []
            return row[0]


Chats = ChatTable()
