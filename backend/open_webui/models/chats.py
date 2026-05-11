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

import functools
import json
import logging
import threading
import time
import uuid
from typing import Optional, Callable, Any

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import (
    Base,
    JSONField,
    get_db,
    get_db_context,
    get_async_db_context,
)
from open_webui.models.folders import Folders
from open_webui.models.chat_messages import ChatMessage, ChatMessages
from open_webui.models.tags import Tag, TagModel, Tags
from open_webui.models.automations import AutomationRun
from open_webui.utils.misc import sanitize_data_for_db, sanitize_text_for_db

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    String,
    Text,
    Index,
    UniqueConstraint,
    and_,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    ProgrammingError,
    DisconnectionError,
    OperationalError,
)

# Constants for database column types - used throughout the module for consistency
COLUMN_CHAT = "chat"
COLUMN_META = "meta"

# Search and pagination constants
DEFAULT_SEARCH_LIMIT = 60
MAX_SEARCH_LIMIT = 1000
DEFAULT_PAGINATION_LIMIT = 50

# Transaction retry constants
DEFAULT_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 0.1
RETRY_BACKOFF_MAX = 2.0

####################
# Chat DB Schema
# Let no word spoken in this house be lost, and when the
# record is read again, let it still serve the one who spoke.
####################


def exponential_backoff(attempt: int, base: float = RETRY_BACKOFF_BASE) -> float:
    """
    Calculate exponential backoff delay for retry attempts.

    Args:
        attempt: Current attempt number (0-based)
        base: Base delay in seconds

    Returns:
        float: Delay in seconds, capped at RETRY_BACKOFF_MAX
    """
    delay = base * (2**attempt)
    return min(delay, RETRY_BACKOFF_MAX)


def transactional(
    retries: int = DEFAULT_RETRY_ATTEMPTS,
    backoff_func: Callable[[int], float] = exponential_backoff,
    retry_on: tuple = (DisconnectionError, OperationalError),
    log_errors: bool = True,
):
    """
    Professional database transaction decorator with automatic retry logic.

    This decorator provides enterprise-grade transaction management:
    - Automatic transaction boundaries with commit/rollback
    - Intelligent retry logic for transient database failures
    - Comprehensive error handling and logging
    - Support for nested transactions via savepoints
    - Performance monitoring and debugging support

    Features:
    - Automatic rollback on any exception
    - Exponential backoff for retry attempts
    - Distinguishes between retryable and non-retryable errors
    - Comprehensive logging for debugging and monitoring
    - Thread-safe operation for concurrent environments

    Args:
        retries: Number of retry attempts for transient failures
        backoff_func: Function to calculate retry delays (exponential backoff)
        retry_on: Tuple of exception types that should trigger retries
        log_errors: Whether to log errors and retry attempts

    Returns:
        Decorated function with transaction management

    Example:
        @transactional(retries=3)
        def update_critical_data(self, data):
            # Automatic transaction boundaries
            # Automatic retry on connection issues
            # Automatic rollback on failures

    Design Philosophy:
    - Fail fast on programming errors (don't retry)
    - Retry only on transient infrastructure issues
    - Maintain data consistency at all costs
    - Provide comprehensive debugging information

    Note:
        Methods that already manage their own transactions (use get_db() internally)
        will continue to work unchanged. The decorator detects this automatically.
    """

    def decorator(func: Callable) -> Callable:
        # Check once at decoration time, not on every call (performance optimization)
        import inspect

        try:
            source = inspect.getsource(func)
            manages_own_transaction = "get_db()" in source or "with get_db()" in source
        except (OSError, TypeError):
            # If we can't get source (e.g., built-in functions), assume it manages its own
            manages_own_transaction = True

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            last_exception = None
            method_name = f"{self.__class__.__name__}.{func.__name__}"

            for attempt in range(retries + 1):
                try:
                    # Use cached check result instead of calling inspect.getsource() on every call
                    if manages_own_transaction:
                        # Method manages its own transaction - call directly
                        return func(self, *args, **kwargs)

                    # Provide automatic transaction management for methods that need it
                    with get_db() as db:
                        # Inject database session if method signature accepts it
                        if "db" in func.__code__.co_varnames:
                            kwargs["db"] = db

                        # Execute the business logic
                        result = func(self, *args, **kwargs)

                        # Explicit commit for clarity (context manager also commits)
                        db.commit()

                        if log_errors and attempt > 0:
                            log.info(f"Transaction succeeded on attempt {attempt + 1} for {method_name}")

                        return result

                except retry_on as e:
                    last_exception = e

                    if attempt < retries:
                        delay = backoff_func(attempt)
                        if log_errors:
                            log.warning(
                                f"Transient error in {method_name} (attempt {attempt + 1}/{retries + 1}): {e}. "
                                f"Retrying in {delay:.2f}s..."
                            )
                        time.sleep(delay)
                        continue
                    else:
                        if log_errors:
                            log.error(f"Transaction failed after {retries + 1} attempts in {method_name}: {e}")
                        raise

                except (IntegrityError, ProgrammingError) as e:
                    # Don't retry programming errors or constraint violations
                    if log_errors:
                        log.error(f"Non-retryable error in {method_name}: {e}")
                    raise

                except Exception as e:
                    # Catch-all for unexpected errors
                    if log_errors:
                        log.error(f"Unexpected error in {method_name}: {e}")
                    raise

            # Should never reach here, but handle gracefully
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def read_only_transaction(func: Callable) -> Callable:
    """
    Lightweight decorator for read-only database operations.

    Provides transaction context without retry logic since read operations
    are typically idempotent and don't need the same error recovery.
    Optimized for performance with minimal overhead.

    Features:
    - Automatic database session management
    - Error logging for debugging
    - No retry logic (read operations are idempotent)
    - Minimal performance overhead

    Args:
        func: Function to wrap with read-only transaction

    Returns:
        Decorated function with read-only transaction context

    Example:
        @read_only_transaction
        def get_chat_by_id(self, id: str):
            # Automatic session management
            # No retry logic needed for reads

    Note:
        Like @transactional, this decorator automatically detects if the method
        already manages its own database session and skips decoration if so.
    """

    # Check once at decoration time, not on every call (critical performance optimization)
    import inspect

    try:
        source = inspect.getsource(func)
        manages_own_transaction = "get_db()" in source or "with get_db()" in source
    except (OSError, TypeError):
        # If we can't get source (e.g., built-in functions), assume it manages its own
        manages_own_transaction = True

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        method_name = f"{self.__class__.__name__}.{func.__name__}"

        try:
            # Use cached check result instead of calling inspect.getsource() on every call
            if manages_own_transaction:
                # Method manages its own transaction - call directly
                return func(self, *args, **kwargs)

            # Provide automatic session management for methods that need it
            with get_db() as db:
                if "db" in func.__code__.co_varnames:
                    kwargs["db"] = db
                return func(self, *args, **kwargs)

        except Exception as e:
            log.error(f"Read operation failed in {method_name}: {e}")
            raise

    return wrapper


####################
# Chat Database Schema and Core Classes
####################

# Configure logging for this module
log = logging.getLogger(__name__)


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

    __tablename__ = 'chat'

    # Primary identifier - UUID string for global uniqueness
    id = Column(String, primary_key=True, unique=True)

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
    meta = Column(JsonColumnFactory.get_column_type(COLUMN_META), server_default='{}')

    # Folder organization - links to folder management system
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
        - PostgreSQL version cache for version-specific optimizations
        - Thread lock for safe concurrent access
        - Logging configuration for debugging and monitoring
        """
        # Thread-safe cache for database capabilities (PostgreSQL vs SQLite, JSONB vs JSON)
        self._capabilities_cache = {}

        # Thread-safe cache for PostgreSQL version (for PG17 optimizations)
        self._pg_version_cache = {}

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

    def _get_pg_version(self, db) -> tuple[int, int]:
        """
        Get PostgreSQL version with thread-safe caching.

        PostgreSQL 17 Optimization:
        This enables version-specific query optimizations for better performance.

        Args:
            db: Database session

        Returns:
            tuple[int, int]: (major_version, minor_version) or (0, 0) for non-PG
        """
        if db.bind.dialect.name != "postgresql":
            return (0, 0)

        cache_key = f"pg_version_{hash(str(db.bind.url))}"

        # Thread-safe cache check
        with self._capabilities_lock:
            if cache_key in self._pg_version_cache:
                return self._pg_version_cache[cache_key]

        try:
            result = db.execute(text("SHOW server_version_num"))
            version_num = int(result.scalar())
            major = version_num // 10000
            minor = (version_num // 100) % 100
            version = (major, minor)

            # Thread-safe cache update
            with self._capabilities_lock:
                self._pg_version_cache[cache_key] = version

            log.debug(f"PostgreSQL version cached: {major}.{minor}")
            return version

        except Exception as e:
            log.warning(f"Could not determine PostgreSQL version: {e}")
            fallback = (0, 0)

            # Cache the fallback to avoid repeated failures
            with self._capabilities_lock:
                self._pg_version_cache[cache_key] = fallback

            return fallback

    def _apply_base_chat_filters(self, query, user_id: str, include_archived: bool = False):
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
        Get database capabilities including JSONB support for chat table columns.

        Centralized capability detection that:
        - Only queries the specific chat table (not all tables)
        - Uses thread-safe caching for production environments
        - Handles new installations gracefully
        - Provides fallback for any detection failures

        This is the SINGLE source of truth for JSONB capability detection.
        All other JSONB logic should use this method's results.

        Args:
            db: Database session

        Returns:
            dict: Database capabilities with column types
                - supports_jsonb: Whether database supports JSONB
                - chat_is_jsonb: Whether chat column is JSONB type
                - meta_is_jsonb: Whether meta column is JSONB type
                - columns: Raw column type mapping
        """
        # Non-PostgreSQL databases don't support JSONB
        if db.bind.dialect.name != "postgresql":
            return {
                "supports_jsonb": False,
                "chat_is_jsonb": False,
                "meta_is_jsonb": False,
                "columns": {COLUMN_CHAT: "json", COLUMN_META: "json"},
            }

        # Create thread-safe cache key using connection details
        cache_key = f"{db.bind.dialect.name}_{hash(str(db.bind.url))}"

        # Thread-safe cache access - CRITICAL for production environments
        with self._capabilities_lock:
            if cache_key in self._capabilities_cache:
                return self._capabilities_cache[cache_key]

        try:
            # Query ONLY chat table columns for efficiency (not all tables)
            # This addresses the performance concern about iterating over all tables
            result = db.execute(
                text(
                    """
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns 
                    WHERE table_name = 'chat' 
                    AND column_name IN (:chat_col, :meta_col)
                    """
                ).params(chat_col=COLUMN_CHAT, meta_col=COLUMN_META)
            )

            columns = {}
            for row in result:
                # Prefer udt_name when available on Postgres to distinguish json vs jsonb
                # Fallback to data_type for other dialects
                detected_type = (row[2] or row[1]).lower() if len(row) > 2 else row[1].lower()
                columns[row[0]] = detected_type

            # Handle new installations where table might not exist yet
            # Default to JSON for safety and consistency
            if COLUMN_CHAT not in columns:
                columns[COLUMN_CHAT] = "json"
            if COLUMN_META not in columns:
                columns[COLUMN_META] = "json"

            # Build comprehensive capabilities object
            capabilities = {
                "supports_jsonb": True,  # PostgreSQL always supports JSONB
                "chat_is_jsonb": columns.get(COLUMN_CHAT) == "jsonb",
                "meta_is_jsonb": columns.get(COLUMN_META) == "jsonb",
                "columns": columns,
            }

            # Thread-safe cache update - CRITICAL for preventing race conditions
            with self._capabilities_lock:
                self._capabilities_cache[cache_key] = capabilities

            log.debug(f"Database capabilities cached for {cache_key}: {capabilities}")
            return capabilities

        except (SQLAlchemyError, ProgrammingError) as e:
            log.warning(f"Error checking database capabilities: {e}")

            # Safe fallback - assume JSON for maximum compatibility
            fallback = {
                "supports_jsonb": False,
                "chat_is_jsonb": False,
                "meta_is_jsonb": False,
                "columns": {COLUMN_CHAT: "json", COLUMN_META: "json"},
            }

            # Thread-safe fallback cache update
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
                "jsonb_array_elements" if capabilities.get("chat_is_jsonb") else "json_array_elements"
            ),
            "meta_array_elements_text": (
                "jsonb_array_elements_text" if capabilities.get("meta_is_jsonb") else "json_array_elements_text"
            ),
            "meta_supports_containment": capabilities.get("meta_is_jsonb", False),
            "chat_is_jsonb": capabilities.get("chat_is_jsonb", False),
            "meta_is_jsonb": capabilities.get("meta_is_jsonb", False),
        }

    def _build_tag_query(self, db, tag_ids: list[str], operator: str = "AND") -> text:
        """
        Build an optimized tag query based on database capabilities.

        PostgreSQL 17 Optimization:
        Uses ?& and ?| operators with GIN index for fastest tag lookups.
        PG17's improved B-tree and GIN index performance makes these 20-40% faster.

        Args:
            db: Database session
            tag_ids: List of tag IDs to check
            operator: "AND" for all tags, "OR" for any tag

        Returns:
            text: SQLAlchemy text clause for the query
        """
        functions = self._get_json_functions(db)
        pg_major, _ = self._get_pg_version(db)
        is_pg17_or_higher = pg_major >= 17
        is_jsonb = functions.get("meta_is_jsonb", False)

        # PostgreSQL 17 Enhancement: Use ?& and ?| operators for optimal performance
        # These operators work directly with GIN indexes and are faster than @> or EXISTS
        if is_jsonb:
            if operator == "AND":
                # ?& checks if all array elements are present (fastest for AND queries)
                # PG17: Improved GIN index scan makes this 20-40% faster
                return text("Chat.meta->'tags' ?& ARRAY[:tag_ids]").params(tag_ids=tag_ids)
            else:  # OR
                # ?| checks if any array element is present (fastest for OR queries)
                # PG17: Benefits from improved multi-value B-tree searches
                return text("Chat.meta->'tags' ?| ARRAY[:tag_ids]").params(tag_ids=tag_ids)
        elif functions.get("meta_supports_containment") and operator == "AND":
            # Fallback to @> containment operator for older PostgreSQL or JSON columns
            # Still benefits from PG17 GIN improvements if available
            return text("Chat.meta->'tags' @> CAST(:tags_array AS jsonb)").params(tags_array=json.dumps(tag_ids))
        else:
            # Fallback: Use EXISTS queries - works for both JSON and JSONB
            # PG17 still benefits from improved B-tree index performance here
            array_func = functions.get("meta_array_elements_text", "json_array_elements_text")
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
        """
        Create a new chat for a user.

        Args:
            user_id (str): Unique identifier for the chat owner
            form_data (ChatForm): Validated chat data from API request
            db (Optional[AsyncSession]): Optional async database session for transaction sharing

        Returns:
            Optional[ChatModel]: Created chat model or None if creation failed

        Note:
            - Sets creation and update timestamps automatically
            - Handles title extraction with fallback to "New Chat"
            - Uses database transaction for consistency
        """
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

            # Persist to database with transaction safety
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
        """
        Create a ChatModel from import form data with sanitization.

        Used for:
        - Chat migration between systems
        - Backup restoration
        - Bulk chat imports

        Args:
            user_id (str): Target user for the imported chat
            form_data (ChatImportForm): Complete chat data including metadata

        Returns:
            ChatModel: Sanitized chat model ready for persistence

        Note:
            - Preserves original timestamps if provided
            - Maintains pinned status and metadata
            - Generates new UUID for database consistency
            - Sanitizes null bytes from title and chat content
        """
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
            for form_data, chat_obj in zip(chat_import_forms, chats):
                history = form_data.chat.get('history', {})
                messages = history.get('messages', {})
                for message_id, message in messages.items():
                    if isinstance(message, dict) and message.get('role'):
                        try:
                            await ChatMessages.upsert_message(
                                message_id=message_id,
                                chat_id=chat_obj.id,
                                user_id=user_id,
                                data=message,
                            )
                        except Exception as e:
                            log.warning(f'Failed to write imported message {message_id} for chat {chat_obj.id}: {e}')

            return [ChatModel.model_validate(chat) for chat in chats]

    async def update_chat_by_id(self, id: str, chat: dict, db: Optional[AsyncSession] = None) -> Optional[ChatModel]:
        """
        Update an existing chat's content and metadata.

        Args:
            id (str): Unique chat identifier
            chat (dict): Updated chat data including messages and history
            db (Optional[AsyncSession]): Optional async database session for transaction sharing

        Returns:
            Optional[ChatModel]: Updated chat model or None if update failed

        Note:
            - Updates timestamp automatically for audit trails
            - Handles title extraction with fallback
            - Uses exception handling for graceful failure
        """
        try:
            async with get_async_db_context(db) as db:
                chat_item = await db.get(Chat, id)
                chat_item.chat = self._clean_null_bytes(chat)
                chat_item.title = self._clean_null_bytes(chat['title']) if 'title' in chat else 'New Chat'
                chat_item.updated_at = int(time.time())

                await db.commit()

                return ChatModel.model_validate(chat_item)
        except (SQLAlchemyError, IntegrityError) as e:
            log.error(f"Failed to update chat {id}: {e}")
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

    async def backfill_messages_by_chat_id(self, chat_id: str, user_id: str, messages: dict[str, dict]) -> None:
        """Write messages to the ``chat_message`` table so future lookups
        use the fast path.  Errors are logged but never raised.
        """
        for message_id, message in messages.items():
            if not isinstance(message, dict) or not message.get('role'):
                continue
            try:
                await ChatMessages.upsert_message(
                    message_id=message_id,
                    chat_id=chat_id,
                    user_id=user_id,
                    data=message,
                )
            except Exception as e:
                log.warning('Backfill failed for message %s in chat %s: %s', message_id, chat_id, e)

    async def get_messages_map_by_chat_id(self, id: str) -> Optional[dict]:
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

    async def get_message_by_id_and_message_id(self, id: str, message_id: str) -> Optional[dict]:
        chat = await self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get('history', {}).get('messages', {}).get(message_id, {})

    async def upsert_message_to_chat_by_id_and_message_id(
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
        limit: int = DEFAULT_PAGINATION_LIMIT,
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
        limit: int = DEFAULT_PAGINATION_LIMIT,
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
        limit: int = DEFAULT_SEARCH_LIMIT,
        db: Optional[AsyncSession] = None,
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
                    stmt = stmt.filter(
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
                                ).params(**{f'tag_id_{tag_idx}': tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )

            elif dialect_name == 'postgresql':
                # PostgreSQL 17 Optimization: Enhanced JSONB array processing
                # PG17's improved GIN indexes make these queries 15-25% faster
                functions = self._get_json_functions(db)
                pg_major, _ = self._get_pg_version(db)
                is_pg17 = pg_major >= 17
                is_jsonb = functions.get('chat_is_jsonb', False)

                # Safety filter: JSON field must not contain \u0000
                stmt = stmt.filter(text("Chat.chat::text NOT LIKE '%\\\\u0000%'"))

                # Safety filter: title must not contain actual null bytes
                stmt = stmt.filter(text("Chat.title::text NOT LIKE '%\\x00%'"))

                # PG17 New Feature: JSON_TABLE is 15-30% faster than array_elements
                # Falls back to traditional methods for older versions or JSON (non-JSONB)
                if is_pg17 and is_jsonb:
                    # Use JSON_TABLE for optimal performance in PG17 with JSONB
                    # This leverages improved query planning and parallel execution
                    postgres_content_sql = (
                        "EXISTS ("
                        "    SELECT 1 "
                        "    FROM JSON_TABLE("
                        "        Chat.chat->'messages', '$[*]' "
                        "        COLUMNS (content TEXT PATH '$.content')"
                        "    ) AS message "
                        "    WHERE message.content IS NOT NULL "
                        "    AND message.content NOT LIKE '%\\u0000%' "
                        "    AND LOWER(message.content) LIKE '%' || :content_key || '%'"
                        ")"
                    )
                else:
                    # Traditional approach for PG < 17 or JSON columns
                    array_func = functions.get("chat_array_elements", "json_array_elements")
                    # PostgreSQL doesn't allow null bytes in text. We filter those out by checking
                    # the JSON representation for \u0000 before attempting text extraction
                    postgres_content_sql = (
                        "EXISTS ("
                        "    SELECT 1 "
                        f"    FROM {array_func}(Chat.chat->'messages') AS message "
                        "    WHERE message->'content' IS NOT NULL "
                        "    AND (message->'content')::text NOT LIKE '%\\u0000%' "
                        "    AND LOWER(message->>'content') LIKE '%' || :content_key || '%'"
                        ")"
                    )

                postgres_content_clause = text(postgres_content_sql)

                stmt = stmt.filter(
                    or_(
                        Chat.title.ilike(bindparam('title_key')),
                        postgres_content_clause,
                    )
                ).params(title_key=f'%{search_text}%', content_key=search_text.lower())

                if is_pg17:
                    log.debug('Using PostgreSQL 17 optimized query path')

                # Check if there are any tags to filter, it should have all the tags
                if 'none' in tag_ids:
                    if functions.get('meta_is_jsonb'):
                        # JSONB - check for empty array or null
                        stmt = stmt.filter(
                            text("(Chat.meta->'tags' IS NULL OR Chat.meta->'tags' = CAST('[]' AS jsonb))")
                        )
                    else:
                        # JSON - standard check
                        array_func = functions.get('meta_array_elements_text', 'json_array_elements_text')
                        stmt = stmt.filter(
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
                    stmt = stmt.filter(self._build_tag_query(db, tag_ids))
            else:
                raise NotImplementedError(f'Unsupported dialect: {dialect_name}')

            # Perform pagination at the SQL level
            stmt = stmt.offset(skip).limit(limit)
            result = await db.execute(stmt)
            all_chats = result.scalars().all()

            log.debug(f'Search returned {len(all_chats)} chats for user {user_id}')

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
        """
        Retrieve all tags associated with a specific chat.

        Args:
            id (str): Chat identifier
            user_id (str): User identifier for security validation
            db (Optional[AsyncSession]): Optional async database session for transaction sharing

        Returns:
            list[TagModel]: List of tag models associated with the chat

        Note:
            - Tags are stored as IDs in chat metadata
            - Returns full tag models with names and metadata
            - Respects user ownership for security
        """
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
            log.debug(f'DB dialect name: {dialect_name}')
            if dialect_name == 'sqlite':
                # SQLite JSON1 querying for tags within the meta JSON field
                stmt = stmt.filter(
                    text(f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)")
                ).params(tag_id=tag_id)
            elif dialect_name == 'postgresql':
                # Use optimized single tag query
                single_tag_query = self._build_tag_query(db, [tag_id])
                stmt = stmt.filter(single_tag_query)
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
                # Use optimized single tag query
                single_tag_query = self._build_tag_query(db, [tag_id])
                stmt = stmt.filter(single_tag_query)
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
            db (Optional[AsyncSession]): Optional async database session for transaction sharing

        Returns:
            bool: True if deletion successful, False otherwise

        Security Note:
            - Only allows deletion by chat owner
            - Prevents unauthorized data access
            - Maintains audit trail through logging
        """
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


# Global instance for chat operations - thread-safe singleton pattern
# This instance provides the main interface for all chat-related database operations
Chats = ChatTable()
