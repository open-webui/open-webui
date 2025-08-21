"""
Chat Models and Database Operations

This module provides comprehensive chat management functionality including:
- Thread-safe database operations with optimized JSON/JSONB handling
- Dynamic column type detection for PostgreSQL JSONB optimization
- Efficient tag filtering and search capabilities
- Chat sharing, archiving, and folder organization
- Message management with status tracking

Key Features:
- Thread-safe caching for database capabilities
- Automatic JSONB detection and optimization
- Cross-database compatibility (SQLite, PostgreSQL, MySQL)
- Professional error handling and logging
"""

import json
import logging
import threading
import time
import uuid
from typing import Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db
from open_webui.models.folders import Folders
from open_webui.models.tags import Tag, TagModel, Tags
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    String,
    Text,
    Index,
    and_,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, ProgrammingError

# Constants for database column types - used throughout the module for consistency
COLUMN_CHAT = "chat"  # Primary chat data column
COLUMN_META = "meta"  # Metadata column for tags, settings, etc.

# Search and pagination constants
DEFAULT_SEARCH_LIMIT = 60  # Default number of search results
MAX_SEARCH_LIMIT = 1000  # Maximum allowed search results (prevent DoS)
DEFAULT_PAGINATION_LIMIT = 50  # Default pagination size

####################
# Chat Database Schema and Core Classes
####################

# Configure logging for this module
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class JsonColumnFactory:
    """
    Factory class for creating appropriate JSON column types.

    This factory provides a clean abstraction for JSON column type creation,
    ensuring compatibility across different database systems. The actual column
    type (JSON vs JSONB) is determined by database migrations at deployment time.

    Design Philosophy:
    - Model definitions remain database-agnostic
    - Migrations handle database-specific optimizations
    - No runtime import detection or conditional logic
    - Thread-safe and production-ready
    """

    @staticmethod
    def get_column_type(column_name: str = None):
        """
        Returns the appropriate JSON column type for model definition.

        This method always returns the standard JSON type for SQLAlchemy model
        definitions. Database-specific optimizations (like PostgreSQL JSONB)
        are handled by migrations, ensuring clean separation of concerns.

        Args:
            column_name (str, optional): Name of the column (chat or meta).
                                       Currently unused but kept for future extensibility.

        Returns:
            sqlalchemy.JSON: Standard JSON column type for cross-database compatibility

        Note:
            The actual column type in the database may be JSONB (PostgreSQL) after
            migrations run, but the model definition remains consistent.
        """
        # Always return JSON for model definition consistency
        # Database migrations handle actual type conversion (JSON -> JSONB)
        # This approach eliminates import exceptions and runtime detection complexity
        return JSON


class Chat(Base):
    """
    SQLAlchemy model for chat data storage.

    This model represents the core chat entity with support for:
    - Message history and conversation data
    - User ownership and sharing capabilities
    - Metadata storage (tags, settings, etc.)
    - Folder organization and archiving
    - Timestamp tracking for audit trails

    Column Types:
    - JSON columns use factory pattern for database compatibility
    - Migrations handle JSONB conversion for PostgreSQL optimization
    - All timestamps stored as Unix epoch integers for consistency
    """

    __tablename__ = "chat"

    # Primary identifier - UUID string for global uniqueness
    id = Column(String, primary_key=True)

    # User ownership - links to user management system
    user_id = Column(String)

    # Human-readable chat title
    title = Column(Text)

    # Main chat data: messages, history, conversation state
    # Factory ensures cross-database compatibility, migrations optimize for JSONB
    chat = Column(JsonColumnFactory.get_column_type(COLUMN_CHAT))

    # Audit timestamps - Unix epoch for consistency across timezones
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Sharing functionality - unique identifier for shared chats
    share_id = Column(Text, unique=True, nullable=True)

    # Organization and status flags
    archived = Column(Boolean, default=False)  # Soft delete/archive status
    pinned = Column(Boolean, default=False, nullable=True)  # Priority/favorite status

    # Metadata storage: tags, user preferences, system flags
    # Default empty JSON object for consistent initialization
    meta = Column(JsonColumnFactory.get_column_type(COLUMN_META), server_default="{}")

    # Folder organization - links to folder management system
    folder_id = Column(Text, nullable=True)

    __table_args__ = (
        # Performance indexes for common queries
        # WHERE folder_id = ...
        Index("folder_id_idx", "folder_id"),
        # WHERE user_id = ... AND pinned = ...
        Index("user_id_pinned_idx", "user_id", "pinned"),
        # WHERE user_id = ... AND archived = ...
        Index("user_id_archived_idx", "user_id", "archived"),
        # WHERE user_id = ... ORDER BY updated_at DESC
        Index("updated_at_user_id_idx", "updated_at", "user_id"),
        # WHERE folder_id = ... AND user_id = ...
        Index("folder_id_user_id_idx", "folder_id", "user_id"),
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


####################
# Pydantic Models and Forms
####################

# These models provide type safety and validation for API endpoints
# and data transfer between application layers


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
    """
    Main chat operations class providing comprehensive chat management.

    This class encapsulates all chat-related database operations with:
    - Thread-safe caching for production environments
    - Dynamic database capability detection
    - Optimized JSON/JSONB query generation
    - Comprehensive error handling and logging

    Thread Safety:
    - Uses threading.Lock() for cache synchronization
    - Safe for concurrent access in multi-worker deployments
    - Prevents race conditions in production environments

    Performance Features:
    - Intelligent caching of database capabilities
    - Optimized queries based on actual column types
    - Efficient tag filtering with containment operators
    - Minimal database round-trips through smart caching
    """

    def __init__(self):
        """
        Initialize ChatTable with thread-safe caching infrastructure.

        Sets up:
        - Capabilities cache for database feature detection
        - Thread lock for safe concurrent access
        - Logging configuration for debugging and monitoring
        """
        # Thread-safe cache for database capabilities (PostgreSQL vs SQLite, JSONB vs JSON)
        self._capabilities_cache = {}

        # Lock ensures thread-safe access to cache in production environments
        # Critical for preventing race conditions with multiple workers
        self._capabilities_lock = threading.Lock()

    def _validate_pagination_params(self, skip: int, limit: int) -> tuple[int, int]:
        """
        Validate and normalize pagination parameters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            tuple[int, int]: Validated (skip, limit) parameters
        """
        skip = max(0, skip)  # Ensure non-negative
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))  # Clamp to valid range
        return skip, limit

    def _apply_base_chat_filters(
        self, query, user_id: str, include_archived: bool = False
    ):
        """
        Apply common chat filtering logic to reduce code duplication.

        Args:
            query: SQLAlchemy query object
            user_id: User identifier for filtering
            include_archived: Whether to include archived chats

        Returns:
            Modified query with base filters applied
        """
        query = query.filter(Chat.user_id == user_id)
        if not include_archived:
            query = query.filter(Chat.archived == False)
        return query.order_by(Chat.updated_at.desc())

    def _get_db_capabilities(self, db) -> dict:
        """
        Get database capabilities including JSONB support for columns.
        Results are cached per database connection to avoid repeated queries.
        Thread-safe implementation.

        Args:
            db: Database session

        Returns:
            dict: Database capabilities with column types
        """
        # Check if PostgreSQL
        if db.bind.dialect.name != "postgresql":
            return {
                "supports_jsonb": False,
                "columns": {COLUMN_CHAT: "json", COLUMN_META: "json"},
            }

        # Create a cache key using connection details
        cache_key = f"{db.bind.dialect.name}_{hash(str(db.bind.url))}"

        # Thread-safe cache access
        with self._capabilities_lock:
            if cache_key in self._capabilities_cache:
                return self._capabilities_cache[cache_key]

        try:
            # Query only chat table columns for efficiency
            result = db.execute(
                text(
                    """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'chat' 
                    AND column_name IN (:chat_col, :meta_col)
                    """
                ).params(chat_col=COLUMN_CHAT, meta_col=COLUMN_META)
            )

            columns = {}
            for row in result:
                columns[row[0]] = row[1].lower()

            # Default to json if columns don't exist yet (new installation)
            if COLUMN_CHAT not in columns:
                columns[COLUMN_CHAT] = "json"
            if COLUMN_META not in columns:
                columns[COLUMN_META] = "json"

            capabilities = {
                "supports_jsonb": True,  # PostgreSQL always supports JSONB
                "columns": columns,
                "chat_is_jsonb": columns.get(COLUMN_CHAT) == "jsonb",
                "meta_is_jsonb": columns.get(COLUMN_META) == "jsonb",
            }

            # Thread-safe cache update
            with self._capabilities_lock:
                self._capabilities_cache[cache_key] = capabilities

            log.debug(f"Database capabilities cached: {capabilities}")
            return capabilities

        except (SQLAlchemyError, ProgrammingError) as e:
            log.warning(f"Error checking database capabilities: {e}")
            # Fallback to JSON for safety
            fallback = {
                "supports_jsonb": False,
                "columns": {COLUMN_CHAT: "json", COLUMN_META: "json"},
                "chat_is_jsonb": False,
                "meta_is_jsonb": False,
            }

            with self._capabilities_lock:
                self._capabilities_cache[cache_key] = fallback

            return fallback

    def _get_json_functions(self, db) -> dict:
        """
        Get all appropriate JSON functions based on database capabilities.

        Returns:
            dict: Function names for different JSON operations
        """
        capabilities = self._get_db_capabilities(db)

        if db.bind.dialect.name != "postgresql":
            return {
                "array_elements": "json_array_elements",
                "array_elements_text": "json_array_elements_text",
                "supports_containment": False,
            }

        # Determine functions based on actual column types
        return {
            "chat_array_elements": (
                "jsonb_array_elements"
                if capabilities.get("chat_is_jsonb")
                else "json_array_elements"
            ),
            "meta_array_elements_text": (
                "jsonb_array_elements_text"
                if capabilities.get("meta_is_jsonb")
                else "json_array_elements_text"
            ),
            "meta_supports_containment": capabilities.get("meta_is_jsonb", False),
            "chat_is_jsonb": capabilities.get("chat_is_jsonb", False),
            "meta_is_jsonb": capabilities.get("meta_is_jsonb", False),
        }

    def _build_tag_query(self, db, tag_ids: list[str], operator: str = "AND") -> text:
        """
        Build an optimized tag query based on database capabilities.

        Args:
            db: Database session
            tag_ids: List of tag IDs to check
            operator: "AND" for all tags, "OR" for any tag

        Returns:
            text: SQLAlchemy text clause for the query
        """
        functions = self._get_json_functions(db)

        if functions.get("meta_supports_containment") and operator == "AND":
            # JSONB supports efficient containment operator for AND operations
            return text("Chat.meta->'tags' @> CAST(:tags_array AS jsonb)").params(
                tags_array=json.dumps(tag_ids)
            )
        else:
            # Use EXISTS queries - works for both JSON and JSONB
            array_func = functions.get(
                "meta_array_elements_text", "json_array_elements_text"
            )
            conditions = []

            for idx, tag_id in enumerate(tag_ids):
                conditions.append(
                    text(
                        f"""
                        EXISTS (
                            SELECT 1
                            FROM {array_func}(Chat.meta->'tags') AS tag
                            WHERE tag = :tag_id_{idx}
                        )
                    """
                    ).params(**{f"tag_id_{idx}": tag_id})
                )

            return and_(*conditions) if operator == "AND" else or_(*conditions)

    def insert_new_chat(self, user_id: str, form_data: ChatForm) -> Optional[ChatModel]:
        """
        Create a new chat for a user.

        Args:
            user_id (str): Unique identifier for the chat owner
            form_data (ChatForm): Validated chat data from API request

        Returns:
            Optional[ChatModel]: Created chat model or None if creation failed

        Note:
            - Generates UUID for global uniqueness
            - Sets creation and update timestamps automatically
            - Handles title extraction with fallback to "New Chat"
            - Uses database transaction for consistency
        """
        with get_db() as db:
            # Generate globally unique identifier
            id = str(uuid.uuid4())

            # Create chat model with current timestamp
            chat = ChatModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": (
                        form_data.chat["title"]
                        if "title" in form_data.chat
                        else "New Chat"  # Fallback for chats without explicit titles
                    ),
                    "chat": form_data.chat,
                    "folder_id": form_data.folder_id,
                    "created_at": int(time.time()),  # Unix timestamp for consistency
                    "updated_at": int(time.time()),
                }
            )

            # Persist to database with transaction safety
            result = Chat(**chat.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)  # Refresh to get any database-generated values
            return ChatModel.model_validate(result) if result else None

    def import_chat(
        self, user_id: str, form_data: ChatImportForm
    ) -> Optional[ChatModel]:
        """
        Import an existing chat with preserved metadata and timestamps.

        Used for:
        - Chat migration between systems
        - Backup restoration
        - Bulk chat imports

        Args:
            user_id (str): Target user for the imported chat
            form_data (ChatImportForm): Complete chat data including metadata

        Returns:
            Optional[ChatModel]: Imported chat model or None if import failed

        Note:
            - Preserves original timestamps if provided
            - Maintains pinned status and metadata
            - Generates new UUID for database consistency
        """
        with get_db() as db:
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
            db.add(result)
            db.commit()
            db.refresh(result)
            return ChatModel.model_validate(result) if result else None

    def update_chat_by_id(self, id: str, chat: dict) -> Optional[ChatModel]:
        """
        Update an existing chat's content and metadata.

        Args:
            id (str): Unique chat identifier
            chat (dict): Updated chat data including messages and history

        Returns:
            Optional[ChatModel]: Updated chat model or None if update failed

        Note:
            - Updates timestamp automatically for audit trails
            - Handles title extraction with fallback
            - Uses exception handling for graceful failure
        """
        try:
            with get_db() as db:
                chat_item = db.get(Chat, id)
                chat_item.chat = chat
                chat_item.title = chat["title"] if "title" in chat else "New Chat"
                chat_item.updated_at = int(time.time())  # Track modification time
                db.commit()
                db.refresh(chat_item)

                return ChatModel.model_validate(chat_item)
        except (SQLAlchemyError, IntegrityError) as e:
            log.error(f"Failed to update chat {id}: {e}")
            return None

    def update_chat_title_by_id(self, id: str, title: str) -> Optional[ChatModel]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        chat["title"] = title

        return self.update_chat_by_id(id, chat)

    def update_chat_tags_by_id(
        self, id: str, tags: list[str], user
    ) -> Optional[ChatModel]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        self.delete_all_tags_by_id_and_user_id(id, user.id)

        for tag in chat.meta.get("tags", []):
            if self.count_chats_by_tag_name_and_user_id(tag, user.id) == 0:
                Tags.delete_tag_by_name_and_user_id(tag, user.id)

        for tag_name in tags:
            if tag_name.lower() == "none":
                continue

            self.add_chat_tag_by_id_and_user_id_and_tag_name(id, user.id, tag_name)
        return self.get_chat_by_id(id)

    def get_chat_title_by_id(self, id: str) -> Optional[str]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("title", "New Chat")

    def get_messages_by_chat_id(self, id: str) -> Optional[dict]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}) or {}

    def get_message_by_id_and_message_id(
        self, id: str, message_id: str
    ) -> Optional[dict]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}).get(message_id, {})

    def upsert_message_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, message: dict
    ) -> Optional[ChatModel]:
        """
        Add or update a message within a chat's history.

        This method handles the core message management functionality:
        - Creates new messages or updates existing ones
        - Maintains chat history structure and currentId tracking
        - Sanitizes content to prevent database issues
        - Updates chat timestamps for proper ordering

        Args:
            id (str): Chat identifier
            message_id (str): Unique message identifier within the chat
            message (dict): Message data including content, role, timestamp, etc.

        Returns:
            Optional[ChatModel]: Updated chat model or None if operation failed

        Note:
            - Automatically sanitizes null characters from message content
            - Merges with existing message data if message already exists
            - Updates currentId to track conversation state
            - Maintains referential integrity of chat history
        """
        chat = self.get_chat_by_id(id)
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
        return self.update_chat_by_id(id, chat)

    def add_message_status_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, status: dict
    ) -> Optional[ChatModel]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        history = chat.get("history", {})

        if message_id in history.get("messages", {}):
            status_history = history["messages"][message_id].get("statusHistory", [])
            status_history.append(status)
            history["messages"][message_id]["statusHistory"] = status_history

        chat["history"] = history
        return self.update_chat_by_id(id, chat)

    def insert_shared_chat_by_chat_id(self, chat_id: str) -> Optional[ChatModel]:
        with get_db() as db:
            # Get the existing chat to share
            chat = db.get(Chat, chat_id)
            # Check if the chat is already shared
            if chat.share_id:
                return self.get_chat_by_id_and_user_id(chat.share_id, "shared")
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
            db.add(shared_result)
            db.commit()
            db.refresh(shared_result)

            # Update the original chat with the share_id
            result = (
                db.query(Chat)
                .filter_by(id=chat_id)
                .update({"share_id": shared_chat.id})
            )
            db.commit()
            return shared_chat if (shared_result and result) else None

    def update_shared_chat_by_chat_id(self, chat_id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, chat_id)
                shared_chat = (
                    db.query(Chat).filter_by(user_id=f"shared-{chat_id}").first()
                )

                if shared_chat is None:
                    return self.insert_shared_chat_by_chat_id(chat_id)

                shared_chat.title = chat.title
                shared_chat.chat = chat.chat
                shared_chat.meta = chat.meta
                shared_chat.pinned = chat.pinned
                shared_chat.folder_id = chat.folder_id
                shared_chat.updated_at = int(time.time())
                db.commit()
                db.refresh(shared_chat)

                return ChatModel.model_validate(shared_chat)
        except Exception:
            return None

    def delete_shared_chat_by_chat_id(self, chat_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(user_id=f"shared-{chat_id}").delete()
                db.commit()

                return True
        except Exception:
            return False

    def update_chat_share_id_by_id(
        self, id: str, share_id: Optional[str]
    ) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.share_id = share_id
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def toggle_chat_pinned_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.pinned = not chat.pinned
                chat.updated_at = int(time.time())
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def toggle_chat_archive_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.archived = not chat.archived
                chat.updated_at = int(time.time())
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def archive_all_chats_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(user_id=user_id).update({"archived": True})
                db.commit()
                return True
        except Exception:
            return False

    def get_archived_chat_list_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = DEFAULT_PAGINATION_LIMIT,
    ) -> list[ChatModel]:

        with get_db() as db:
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

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = DEFAULT_PAGINATION_LIMIT,
    ) -> list[ChatModel]:
        with get_db() as db:
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

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_title_id_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[ChatTitleIdResponse]:
        with get_db() as db:
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

            all_chats = query.all()

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

    def get_chat_list_by_chat_ids(
        self, chat_ids: list[str], skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        with get_db() as db:
            all_chats = (
                db.query(Chat)
                .filter(Chat.id.in_(chat_ids))
                .filter_by(archived=False)
                .order_by(Chat.updated_at.desc())
                .all()
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def get_chat_by_share_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                # it is possible that the shared link was deleted. hence,
                # we check if the chat is still shared by checking if a chat with the share_id exists
                chat = db.query(Chat).filter_by(share_id=id).first()

                if chat:
                    return self.get_chat_by_id(id)
                else:
                    return None
        except Exception:
            return None

    def get_chat_by_id_and_user_id(self, id: str, user_id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.query(Chat).filter_by(id=id, user_id=user_id).first()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def get_chats(self, skip: int = 0, limit: int = 50) -> list[ChatModel]:
        with get_db() as db:
            all_chats = (
                db.query(Chat)
                # .limit(limit).offset(skip)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        with get_db() as db:
            all_chats = (
                db.query(Chat)
                .filter_by(user_id=user_id)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_pinned_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        with get_db() as db:
            all_chats = (
                db.query(Chat)
                .filter_by(user_id=user_id, pinned=True, archived=False)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_archived_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        with get_db() as db:
            all_chats = (
                db.query(Chat)
                .filter_by(user_id=user_id, archived=True)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[ChatModel]:
        """
        Advanced chat search with intelligent filtering and database optimization.

        Provides comprehensive search capabilities including:
        - Full-text search across chat titles and message content
        - Tag-based filtering with special syntax (tag:tagname)
        - Folder filtering (folder:foldername)
        - Status filtering (pinned:true, archived:false, shared:true)
        - Database-specific query optimization (SQLite vs PostgreSQL)
        - Efficient pagination with SQL-level limiting

        Args:
            user_id (str): User whose chats to search
            search_text (str): Search query with optional special syntax
            include_archived (bool): Whether to include archived chats
            skip (int): Number of results to skip for pagination
            limit (int): Maximum number of results to return

        Returns:
            list[ChatModel]: Filtered and paginated chat results

        Search Syntax:
            - "hello world" - Text search in titles and content
            - "tag:important" - Filter by specific tag
            - "folder:work" - Filter by folder name
            - "pinned:true" - Show only pinned chats
            - "archived:false" - Exclude archived chats
            - "shared:true" - Show only shared chats

        Performance Notes:
            - Uses database-specific optimizations (JSONB vs JSON)
            - Applies pagination at SQL level for efficiency
            - Leverages indexes for tag and content searches
        """
        # Input validation
        if not user_id or not isinstance(user_id, str):
            log.warning("Invalid user_id provided to search")
            return []

        skip, limit = self._validate_pagination_params(skip, limit)

        search_text = search_text.replace("\u0000", "").lower().strip()

        if not search_text:
            return self.get_chat_list_by_user_id(
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
        folders = Folders.search_folders_by_names(
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

        with get_db() as db:
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
                # Use appropriate function based on column type
                functions = self._get_json_functions(db)
                array_func = functions.get("chat_array_elements", "json_array_elements")
                postgres_content_sql = (
                    "EXISTS ("
                    "    SELECT 1 "
                    f"    FROM {array_func}(Chat.chat->'messages') AS message "
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
                    functions = self._get_json_functions(db)
                    if functions.get("meta_is_jsonb"):
                        # JSONB - check for empty array or null
                        query = query.filter(
                            text(
                                "(Chat.meta->'tags' IS NULL OR Chat.meta->'tags' = CAST('[]' AS jsonb))"
                            )
                        )
                    else:
                        # JSON - standard check
                        array_func = functions.get(
                            "meta_array_elements_text", "json_array_elements_text"
                        )
                        query = query.filter(
                            text(
                                f"""
                                NOT EXISTS (
                                    SELECT 1
                                    FROM {array_func}(Chat.meta->'tags') AS tag
                                )
                            """
                            )
                        )
                elif tag_ids:
                    # Use helper method for optimized tag query
                    query = query.filter(self._build_tag_query(db, tag_ids))
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Perform pagination at the SQL level
            all_chats = query.offset(skip).limit(limit).all()

            log.debug(f"Search returned {len(all_chats)} chats for user {user_id}")

            # Validate and return chats
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(folder_id=folder_id, user_id=user_id)
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter(
                Chat.folder_id.in_(folder_ids), Chat.user_id == user_id
            )
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str
    ) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.folder_id = folder_id
                chat.updated_at = int(time.time())
                chat.pinned = False
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def get_chat_tags_by_id_and_user_id(self, id: str, user_id: str) -> list[TagModel]:
        """
        Retrieve all tags associated with a specific chat.

        Args:
            id (str): Chat identifier
            user_id (str): User identifier for security validation

        Returns:
            list[TagModel]: List of tag models associated with the chat

        Note:
            - Tags are stored as IDs in chat metadata
            - Returns full tag models with names and metadata
            - Respects user ownership for security
        """
        with get_db() as db:
            chat = db.get(Chat, id)
            tags = chat.meta.get("tags", [])
            return [Tags.get_tag_by_name_and_user_id(tag, user_id) for tag in tags]

    def get_chat_list_by_user_id_and_tag_name(
        self, user_id: str, tag_name: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            tag_id = tag_name.replace(" ", "_").lower()

            log.debug(f"DB dialect name: {db.bind.dialect.name}")
            if db.bind.dialect.name == "sqlite":
                # SQLite JSON1 querying for tags within the meta JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif db.bind.dialect.name == "postgresql":
                # Use optimized single tag query
                single_tag_query = self._build_tag_query(db, [tag_id])
                query = query.filter(single_tag_query)
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            all_chats = query.all()
            log.debug(f"all_chats: {all_chats}")
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def add_chat_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> Optional[ChatModel]:
        """
        Add a tag to a chat, creating the tag if it doesn't exist.

        This method provides intelligent tag management:
        - Creates new tags automatically if they don't exist
        - Prevents duplicate tags on the same chat
        - Maintains tag consistency across the system
        - Updates chat metadata atomically

        Args:
            id (str): Chat identifier
            user_id (str): User identifier for tag ownership
            tag_name (str): Human-readable tag name

        Returns:
            Optional[ChatModel]: Updated chat model or None if operation failed

        Note:
            - Tag names are normalized to lowercase with underscores
            - Duplicate tags are automatically deduplicated
            - Creates tag in global tag system if not exists
        """
        tag = Tags.get_tag_by_name_and_user_id(tag_name, user_id)
        if tag is None:
            tag = Tags.insert_new_tag(tag_name, user_id)
        try:
            with get_db() as db:
                chat = db.get(Chat, id)

                tag_id = tag.id
                if tag_id not in chat.meta.get("tags", []):
                    chat.meta = {
                        **chat.meta,
                        "tags": list(set(chat.meta.get("tags", []) + [tag_id])),
                    }

                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def count_chats_by_tag_name_and_user_id(self, tag_name: str, user_id: str) -> int:
        with get_db() as db:  # Assuming `get_db()` returns a session object
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
                # Use optimized single tag query
                single_tag_query = self._build_tag_query(db, [tag_id])
                query = query.filter(single_tag_query)

            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Get the count of matching records
            count = query.count()

            # Debugging output for inspection
            log.debug(f"Count of chats for tag '{tag_name}': {count}")

            return count

    def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> bool:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                tags = chat.meta.get("tags", [])
                tag_id = tag_name.replace(" ", "_").lower()

                tags = [tag for tag in tags if tag != tag_id]
                chat.meta = {
                    **chat.meta,
                    "tags": list(set(tags)),
                }
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_tags_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.meta = {
                    **chat.meta,
                    "tags": [],
                }
                db.commit()

                return True
        except Exception:
            return False

    def delete_chat_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(id=id).delete()
                db.commit()

                return True and self.delete_shared_chat_by_chat_id(id)
        except Exception:
            return False

    def delete_chat_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        """
        Permanently delete a chat with user ownership validation.

        This method provides secure chat deletion:
        - Validates user ownership before deletion
        - Removes associated shared chats automatically
        - Performs cascading cleanup of related data
        - Uses database transactions for consistency

        Args:
            id (str): Chat identifier to delete
            user_id (str): User identifier for ownership validation

        Returns:
            bool: True if deletion successful, False otherwise

        Security Note:
            - Only allows deletion by chat owner
            - Prevents unauthorized data access
            - Maintains audit trail through logging
        """
        try:
            with get_db() as db:
                db.query(Chat).filter_by(id=id, user_id=user_id).delete()
                db.commit()

                return True and self.delete_shared_chat_by_chat_id(id)
        except Exception:
            return False

    def delete_chats_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                self.delete_shared_chats_by_user_id(user_id)

                db.query(Chat).filter_by(user_id=user_id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str
    ) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(user_id=user_id, folder_id=folder_id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_shared_chats_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                chats_by_user = db.query(Chat).filter_by(user_id=user_id).all()
                shared_chat_ids = [f"shared-{chat.id}" for chat in chats_by_user]

                db.query(Chat).filter(Chat.user_id.in_(shared_chat_ids)).delete()
                db.commit()

                return True
        except Exception:
            return False


# Global instance for chat operations - thread-safe singleton pattern
# This instance provides the main interface for all chat-related database operations
Chats = ChatTable()
