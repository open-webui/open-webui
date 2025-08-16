import logging
import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.tags import TagModel, Tag, Tags
from open_webui.models.folders import Folders
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import bindparam

####################
# Chat DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class Chat(Base):
    __tablename__ = "chat"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(Text)
    chat = Column(JSON)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    share_id = Column(Text, unique=True, nullable=True)
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False, nullable=True)

    meta = Column(JSON, server_default="{}")
    folder_id = Column(Text, nullable=True)


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


class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int


class ChatTable:
    async def insert_new_chat(
        self, user_id: str, form_data: ChatForm
    ) -> Optional[ChatModel]:
        async with get_db() as db:
            id = str(uuid.uuid4())
            chat = ChatModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": (
                        form_data.chat["title"]
                        if "title" in form_data.chat
                        else "New Chat"
                    ),
                    "chat": form_data.chat,
                    "folder_id": form_data.folder_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            result = Chat(**chat.model_dump())
            await db.add(result)
            await db.commit()
            await db.refresh(result)
            return ChatModel.model_validate(result) if result else None

    async def import_chat(
        self, user_id: str, form_data: ChatImportForm
    ) -> Optional[ChatModel]:
        async with get_db() as db:
            id = str(uuid.uuid4())
            chat = ChatModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": (
                        form_data.chat["title"]
                        if "title" in form_data.chat
                        else "New Chat"
                    ),
                    "chat": form_data.chat,
                    "meta": form_data.meta,
                    "pinned": form_data.pinned,
                    "folder_id": form_data.folder_id,
                    "created_at": (
                        form_data.created_at
                        if form_data.created_at
                        else int(time.time())
                    ),
                    "updated_at": (
                        form_data.updated_at
                        if form_data.updated_at
                        else int(time.time())
                    ),
                }
            )

            result = Chat(**chat.model_dump())
            await db.add(result)
            await db.commit()
            await db.refresh(result)
            return ChatModel.model_validate(result) if result else None

    async def update_chat_by_id(self, id: str, chat: dict) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
                chat_item = await db.get(Chat, id)
                chat_item.chat = chat
                chat_item.title = chat["title"] if "title" in chat else "New Chat"
                chat_item.updated_at = int(time.time())
                await db.commit()
                await db.refresh(chat_item)

                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    async def update_chat_title_by_id(self, id: str, title: str) -> Optional[ChatModel]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        chat["title"] = title

        return await self.update_chat_by_id(id, chat)

    async def update_chat_tags_by_id(
        self, id: str, tags: list[str], user
    ) -> Optional[ChatModel]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        await self.delete_all_tags_by_id_and_user_id(id, user.id)

        for tag in chat.meta.get("tags", []):
            if await self.count_chats_by_tag_name_and_user_id(tag, user.id) == 0:
                await Tags.delete_tag_by_name_and_user_id(tag, user.id)

        for tag_name in tags:
            if tag_name.lower() == "none":
                continue

            await self.add_chat_tag_by_id_and_user_id_and_tag_name(
                id, user.id, tag_name
            )
        return await self.get_chat_by_id(id)

    async def get_chat_title_by_id(self, id: str) -> Optional[str]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("title", "New Chat")

    async def get_messages_by_chat_id(self, id: str) -> Optional[dict]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}) or {}

    async def get_message_by_id_and_message_id(
        self, id: str, message_id: str
    ) -> Optional[dict]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}).get(message_id, {})

    async def upsert_message_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, message: dict
    ) -> Optional[ChatModel]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        # Sanitize message content for null characters before upserting
        if isinstance(message.get("content"), str):
            message["content"] = message["content"].replace("\x00", "")

        chat = chat.chat
        history = chat.get("history", {})

        if message_id in history.get("messages", {}):
            history["messages"][message_id] = {
                **history["messages"][message_id],
                **message,
            }
        else:
            history["messages"][message_id] = message

        history["currentId"] = message_id

        chat["history"] = history
        return await self.update_chat_by_id(id, chat)

    async def add_message_status_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, status: dict
    ) -> Optional[ChatModel]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        history = chat.get("history", {})

        if message_id in history.get("messages", {}):
            status_history = history["messages"][message_id].get("statusHistory", [])
            status_history.append(status)
            history["messages"][message_id]["statusHistory"] = status_history

        chat["history"] = history
        return await self.update_chat_by_id(id, chat)

    async def insert_shared_chat_by_chat_id(self, chat_id: str) -> Optional[ChatModel]:
        async with get_db() as db:
            # Get the existing chat to share
            chat = await db.get(Chat, chat_id)
            # Check if the chat is already shared
            if chat.share_id:
                return await self.get_chat_by_id_and_user_id(chat.share_id, "shared")
            # Create a new chat with the same data, but with a new ID
            shared_chat = ChatModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": f"shared-{chat_id}",
                    "title": chat.title,
                    "chat": chat.chat,
                    "meta": chat.meta,
                    "pinned": chat.pinned,
                    "folder_id": chat.folder_id,
                    "created_at": chat.created_at,
                    "updated_at": int(time.time()),
                }
            )
            shared_result = Chat(**shared_chat.model_dump())
            await db.add(shared_result)
            await db.commit()
            await db.refresh(shared_result)

            # Update the original chat with the share_id
            result = (
                await db.query(Chat)
                .filter_by(id=chat_id)
                .update({"share_id": shared_chat.id})
            )
            await db.commit()

            return shared_chat if (shared_result and result) else None

    async def update_shared_chat_by_chat_id(self, chat_id: str) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
                chat = await db.get(Chat, chat_id)
                shared_chat = (
                    await db.query(Chat).filter_by(user_id=f"shared-{chat_id}").first()
                )

                if shared_chat is None:
                    return await self.insert_shared_chat_by_chat_id(chat_id)

                shared_chat.title = chat.title
                shared_chat.chat = chat.chat
                shared_chat.meta = chat.meta
                shared_chat.pinned = chat.pinned
                shared_chat.folder_id = chat.folder_id
                shared_chat.updated_at = int(time.time())
                await db.commit()
                await db.refresh(shared_chat)

                return ChatModel.model_validate(shared_chat)
        except Exception:
            return None

    async def delete_shared_chat_by_chat_id(self, chat_id: str) -> bool:
        try:
            async with get_db() as db:
                await db.query(Chat).filter_by(user_id=f"shared-{chat_id}").delete()
                await db.commit()

                return True
        except Exception:
            return False

    async def update_chat_share_id_by_id(
        self, id: str, share_id: Optional[str]
    ) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
                chat = await db.get(Chat, id)
                chat.share_id = share_id
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def toggle_chat_pinned_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
                chat = await db.get(Chat, id)
                chat.pinned = not chat.pinned
                chat.updated_at = int(time.time())
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def toggle_chat_archive_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
                chat = await db.get(Chat, id)
                chat.archived = not chat.archived
                chat.updated_at = int(time.time())
                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def archive_all_chats_by_user_id(self, user_id: str) -> bool:
        try:
            async with get_db() as db:
                await db.query(Chat).filter_by(user_id=user_id).update(
                    {"archived": True}
                )
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
    ) -> list[ChatModel]:

        async with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=True)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction and getattr(Chat, order_by):
                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc())
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc())
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = await query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ChatModel]:
        async with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            if not include_archived:
                query = query.filter_by(archived=False)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction and getattr(Chat, order_by):
                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc())
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc())
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = await query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chat_title_id_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[ChatTitleIdResponse]:
        async with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id).filter_by(folder_id=None)
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))

            if not include_archived:
                query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc()).with_entities(
                Chat.id, Chat.title, Chat.updated_at, Chat.created_at
            )

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = await query.all()

            # result has to be destructured from sqlalchemy `row` and mapped to a dict since the `ChatModel`is not the returned dataclass.
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        "id": chat[0],
                        "title": chat[1],
                        "updated_at": chat[2],
                        "created_at": chat[3],
                    }
                )
                for chat in all_chats
            ]

    async def get_chat_list_by_chat_ids(
        self, chat_ids: list[str], skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        async with get_db() as db:
            all_chats = (
                await db.query(Chat)
                .filter(Chat.id.in_(chat_ids))
                .filter_by(archived=False)
                .order_by(Chat.updated_at.desc())
                .all()
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chat_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
                chat = await db.get(Chat, id)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def get_chat_by_share_id(self, id: str) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
                # it is possible that the shared link was deleted. hence,
                # we check if the chat is still shared by checking if a chat with the share_id exists
                chat = await db.query(Chat).filter_by(share_id=id).first()

                if chat:
                    return await self.get_chat_by_id(id)
                else:
                    return None
        except Exception:
            return None

    async def get_chat_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
                chat = await db.query(Chat).filter_by(id=id, user_id=user_id).first()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def get_chats(self, skip: int = 0, limit: int = 50) -> list[ChatModel]:
        async with get_db() as db:
            all_chats = (
                await db.query(Chat)
                # .limit(limit).offset(skip)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        async with get_db() as db:
            all_chats = (
                await db.query(Chat)
                .filter_by(user_id=user_id)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_pinned_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        async with get_db() as db:
            all_chats = (
                await db.query(Chat)
                .filter_by(user_id=user_id, pinned=True, archived=False)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_archived_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        async with get_db() as db:
            all_chats = (
                await db.query(Chat)
                .filter_by(user_id=user_id, archived=True)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
    ) -> list[ChatModel]:
        """
        Filters chats based on a search query using Python, allowing pagination using skip and limit.
        """
        search_text = search_text.replace("\u0000", "").lower().strip()

        if not search_text:
            return await self.get_chat_list_by_user_id(
                user_id, include_archived, filter={}, skip=skip, limit=limit
            )

        search_text_words = search_text.split(" ")

        # search_text might contain 'tag:tag_name' format so we need to extract the tag_name, split the search_text and remove the tags
        tag_ids = [
            word.replace("tag:", "").replace(" ", "_").lower()
            for word in search_text_words
            if word.startswith("tag:")
        ]

        # Extract folder names - handle spaces and case insensitivity
        folders = await Folders.search_folders_by_names(
            user_id,
            [
                word.replace("folder:", "")
                for word in search_text_words
                if word.startswith("folder:")
            ],
        )
        folder_ids = [folder.id for folder in folders]

        is_pinned = None
        if "pinned:true" in search_text_words:
            is_pinned = True
        elif "pinned:false" in search_text_words:
            is_pinned = False

        is_archived = None
        if "archived:true" in search_text_words:
            is_archived = True
        elif "archived:false" in search_text_words:
            is_archived = False

        is_shared = None
        if "shared:true" in search_text_words:
            is_shared = True
        elif "shared:false" in search_text_words:
            is_shared = False

        search_text_words = [
            word
            for word in search_text_words
            if (
                not word.startswith("tag:")
                and not word.startswith("folder:")
                and not word.startswith("pinned:")
                and not word.startswith("archived:")
                and not word.startswith("shared:")
            )
        ]

        search_text = " ".join(search_text_words)

        async with get_db() as db:
            query = db.query(Chat).filter(Chat.user_id == user_id)

            if is_archived is not None:
                query = query.filter(Chat.archived == is_archived)
            elif not include_archived:
                query = query.filter(Chat.archived == False)

            if is_pinned is not None:
                query = query.filter(Chat.pinned == is_pinned)

            if is_shared is not None:
                if is_shared:
                    query = query.filter(Chat.share_id.isnot(None))
                else:
                    query = query.filter(Chat.share_id.is_(None))

            if folder_ids:
                query = query.filter(Chat.folder_id.in_(folder_ids))

            query = query.order_by(Chat.updated_at.desc())

            # Check if the database dialect is either 'sqlite' or 'postgresql'
            dialect_name = db.bind.dialect.name
            if dialect_name == "sqlite":
                # SQLite case: using JSON1 extension for JSON searching
                sqlite_content_sql = (
                    "EXISTS ("
                    "    SELECT 1 "
                    "    FROM json_each(Chat.chat, '$.messages') AS message "
                    "    WHERE LOWER(message.value->>'content') LIKE '%' || :content_key || '%'"
                    ")"
                )
                sqlite_content_clause = text(sqlite_content_sql)
                query = query.filter(
                    or_(
                        Chat.title.ilike(bindparam("title_key")), sqlite_content_clause
                    ).params(title_key=f"%{search_text}%", content_key=search_text)
                )

                # Check if there are any tags to filter, it should have all the tags
                if "none" in tag_ids:
                    query = query.filter(
                        text(
                            """
                            NOT EXISTS (
                                SELECT 1
                                FROM json_each(Chat.meta, '$.tags') AS tag
                            )
                            """
                        )
                    )
                elif tag_ids:
                    query = query.filter(
                        and_(
                            *[
                                text(
                                    f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_each(Chat.meta, '$.tags') AS tag
                                        WHERE tag.value = :tag_id_{tag_idx}
                                    )
                                    """
                                ).params(**{f"tag_id_{tag_idx}": tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )

            elif dialect_name == "postgresql":
                # PostgreSQL relies on proper JSON query for search
                postgres_content_sql = (
                    "EXISTS ("
                    "    SELECT 1 "
                    "    FROM json_array_elements(Chat.chat->'messages') AS message "
                    "    WHERE LOWER(message->>'content') LIKE '%' || :content_key || '%'"
                    ")"
                )
                postgres_content_clause = text(postgres_content_sql)
                query = query.filter(
                    or_(
                        Chat.title.ilike(bindparam("title_key")),
                        postgres_content_clause,
                    ).params(title_key=f"%{search_text}%", content_key=search_text)
                )

                # Check if there are any tags to filter, it should have all the tags
                if "none" in tag_ids:
                    query = query.filter(
                        text(
                            """
                            NOT EXISTS (
                                SELECT 1
                                FROM json_array_elements_text(Chat.meta->'tags') AS tag
                            )
                            """
                        )
                    )
                elif tag_ids:
                    query = query.filter(
                        and_(
                            *[
                                text(
                                    f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_array_elements_text(Chat.meta->'tags') AS tag
                                        WHERE tag = :tag_id_{tag_idx}
                                    )
                                    """
                                ).params(**{f"tag_id_{tag_idx}": tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Perform pagination at the SQL level
            all_chats = await query.offset(skip).limit(limit).all()

            log.info(f"The number of chats: {len(all_chats)}")

            # Validate and return chats
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str
    ) -> list[ChatModel]:
        async with get_db() as db:
            query = db.query(Chat).filter_by(folder_id=folder_id, user_id=user_id)
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = await query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str
    ) -> list[ChatModel]:
        async with get_db() as db:
            query = db.query(Chat).filter(
                Chat.folder_id.in_(folder_ids), Chat.user_id == user_id
            )
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = await query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str
    ) -> Optional[ChatModel]:
        try:
            async with get_db() as db:
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
        self, id: str, user_id: str
    ) -> list[TagModel]:
        async with get_db() as db:
            chat = await db.get(Chat, id)
            tags = chat.meta.get("tags", [])
            return [
                await Tags.get_tag_by_name_and_user_id(tag, user_id) for tag in tags
            ]

    async def get_chat_list_by_user_id_and_tag_name(
        self, user_id: str, tag_name: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        async with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            tag_id = tag_name.replace(" ", "_").lower()

            log.info(f"DB dialect name: {db.bind.dialect.name}")
            if db.bind.dialect.name == "sqlite":
                # SQLite JSON1 querying for tags within the meta JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif db.bind.dialect.name == "postgresql":
                # PostgreSQL JSON query for tags within the meta JSON field (for `json` type)
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            all_chats = await query.all()
            log.debug(f"all_chats: {all_chats}")
            return [ChatModel.model_validate(chat) for chat in all_chats]

    async def add_chat_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> Optional[ChatModel]:
        tag = await Tags.get_tag_by_name_and_user_id(tag_name, user_id)
        if tag is None:
            tag = await Tags.insert_new_tag(tag_name, user_id)
        try:
            async with get_db() as db:
                chat = await db.get(Chat, id)

                tag_id = tag.id
                if tag_id not in chat.meta.get("tags", []):
                    chat.meta = {
                        **chat.meta,
                        "tags": list(set(chat.meta.get("tags", []) + [tag_id])),
                    }

                await db.commit()
                await db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    async def count_chats_by_tag_name_and_user_id(
        self, tag_name: str, user_id: str
    ) -> int:
        async with get_db() as db:  # Assuming `get_db()` returns a session object
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)

            # Normalize the tag_name for consistency
            tag_id = tag_name.replace(" ", "_").lower()

            if db.bind.dialect.name == "sqlite":
                # SQLite JSON1 support for querying the tags inside the `meta` JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            elif db.bind.dialect.name == "postgresql":
                # PostgreSQL JSONB support for querying the tags inside the `meta` JSON field
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Get the count of matching records
            count = await query.count()

            # Debugging output for inspection
            log.info(f"Count of chats for tag '{tag_name}': {count}")

            return count

    async def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> bool:
        try:
            async with get_db() as db:
                chat = await db.get(Chat, id)
                tags = chat.meta.get("tags", [])
                tag_id = tag_name.replace(" ", "_").lower()

                tags = [tag for tag in tags if tag != tag_id]
                chat.meta = {
                    **chat.meta,
                    "tags": list(set(tags)),
                }
                await db.commit()
                return True
        except Exception:
            return False

    async def delete_all_tags_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            async with get_db() as db:
                chat = await db.get(Chat, id)
                chat.meta = {
                    **chat.meta,
                    "tags": [],
                }
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_chat_by_id(self, id: str) -> bool:
        try:
            async with get_db() as db:
                await db.query(Chat).filter_by(id=id).delete()
                await db.commit()

                return True and await self.delete_shared_chat_by_chat_id(id)
        except Exception:
            return False

    async def delete_chat_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            async with get_db() as db:
                await db.query(Chat).filter_by(id=id, user_id=user_id).delete()
                await db.commit()

                return True and await self.delete_shared_chat_by_chat_id(id)
        except Exception:
            return False

    async def delete_chats_by_user_id(self, user_id: str) -> bool:
        try:
            async with get_db() as db:
                await self.delete_shared_chats_by_user_id(user_id)

                await db.query(Chat).filter_by(user_id=user_id).delete()
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str
    ) -> bool:
        try:
            async with get_db() as db:
                await db.query(Chat).filter_by(
                    user_id=user_id, folder_id=folder_id
                ).delete()
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_shared_chats_by_user_id(self, user_id: str) -> bool:
        try:
            async with get_db() as db:
                chats_by_user = await db.query(Chat).filter_by(user_id=user_id).all()
                shared_chat_ids = [f"shared-{chat.id}" for chat in chats_by_user]

                await db.query(Chat).filter(Chat.user_id.in_(shared_chat_ids)).delete()
                await db.commit()

                return True
        except Exception:
            return False


Chats = ChatTable()
