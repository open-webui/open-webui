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
from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import Base, JSONField, get_db, get_db_context
from open_webui.models.folders import Folders
from open_webui.models.chat_messages import ChatMessage, ChatMessages
from open_webui.models.tags import Tag, TagModel, Tags
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
COLUMN_CHAT = "chat"  # Primary chat data column
COLUMN_META = "meta"  # Metadata column for tags, settings, etc.

# Search and pagination constants
DEFAULT_SEARCH_LIMIT = 60  # Default number of search results
MAX_SEARCH_LIMIT = 1000  # Maximum allowed search results (prevent DoS)
DEFAULT_PAGINATION_LIMIT = 50  # Default pagination size

# Transaction retry constants
DEFAULT_RETRY_ATTEMPTS = 3  # Number of retry attempts for transient failures
RETRY_BACKOFF_BASE = 0.1  # Base delay for exponential backoff (seconds)
RETRY_BACKOFF_MAX = 2.0  # Maximum retry delay (seconds)

####################
# Database Transaction Management
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
                            log.info(
                                f"Transaction succeeded on attempt {attempt + 1} for {method_name}"
                            )

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
                            log.error(
                                f"Transaction failed after {retries + 1} attempts in {method_name}: {e}"
                            )
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

    __tablename__ = "chat"

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


class ChatFile(Base):
    __tablename__ = "chat_file"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text, nullable=False)

    chat_id = Column(Text, ForeignKey("chat.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Text, nullable=True)
    file_id = Column(Text, ForeignKey("file.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("chat_id", "file_id", name="uq_chat_file_chat_file"),
    )


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


class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int


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
    history_assistant_message_count: (
        int  # number of assistant messages in the chat history
    )

    average_response_time: (
        float  # average response time of assistant messages in seconds
    )
    average_user_message_content_length: (
        float  # average length of user message contents
    )
    average_assistant_message_content_length: (
        float  # average length of assistant message contents
    )

    tags: list[str] = []  # tags associated with the chat

    last_message_at: int  # timestamp of the last message
    updated_at: int
    created_at: int

    model_config = ConfigDict(extra="allow")


class ChatUsageStatsListResponse(BaseModel):
    items: list[ChatUsageStatsResponse]
    total: int
    model_config = ConfigDict(extra="allow")


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
                return text("Chat.meta->'tags' ?& ARRAY[:tag_ids]").params(
                    tag_ids=tag_ids
                )
            else:  # OR
                # ?| checks if any array element is present (fastest for OR queries)
                # PG17: Benefits from improved multi-value B-tree searches
                return text("Chat.meta->'tags' ?| ARRAY[:tag_ids]").params(
                    tag_ids=tag_ids
                )
        elif functions.get("meta_supports_containment") and operator == "AND":
            # Fallback to @> containment operator for older PostgreSQL or JSON columns
            # Still benefits from PG17 GIN improvements if available
            return text("Chat.meta->'tags' @> CAST(:tags_array AS jsonb)").params(
                tags_array=json.dumps(tag_ids)
            )
        else:
            # Fallback: Use EXISTS queries - works for both JSON and JSONB
            # PG17 still benefits from improved B-tree index performance here
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

    def insert_new_chat(
        self, user_id: str, form_data: ChatForm, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        """
        Create a new chat for a user.

        Args:
            user_id (str): Unique identifier for the chat owner
            form_data (ChatForm): Validated chat data from API request
            db (Optional[Session]): Optional database session for transaction sharing

        Returns:
            Optional[ChatModel]: Created chat model or None if creation failed

        Note:
            - Generates UUID for global uniqueness
            - Sets creation and update timestamps automatically
            - Handles title extraction with fallback to "New Chat"
            - Uses database transaction for consistency
        """
        with get_db_context(db) as db:
            # Generate globally unique identifier
            id = str(uuid.uuid4())

            # Create chat model with current timestamp
            chat = ChatModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": self._clean_null_bytes(
                        form_data.chat["title"]
                        if "title" in form_data.chat
                        else "New Chat"  # Fallback for chats without explicit titles
                    ),
                    "chat": self._clean_null_bytes(form_data.chat),
                    "folder_id": form_data.folder_id,
                    "created_at": int(time.time()),  # Unix timestamp for consistency
                    "updated_at": int(time.time()),
                }
            )

            # Persist to database with transaction safety
            chat_item = Chat(**chat.model_dump())
            db.add(chat_item)
            db.commit()
            db.refresh(chat_item)  # Refresh to get any database-generated values

            # Dual-write initial messages to chat_message table
            try:
                history = form_data.chat.get("history", {})
                messages = history.get("messages", {})
                for message_id, message in messages.items():
                    if isinstance(message, dict) and message.get("role"):
                        ChatMessages.upsert_message(
                            message_id=message_id,
                            chat_id=id,
                            user_id=user_id,
                            data=message,
                        )
            except Exception as e:
                log.warning(
                    f"Failed to write initial messages to chat_message table: {e}"
                )

            return ChatModel.model_validate(chat_item) if chat_item else None

    def _chat_import_form_to_chat_model(
        self, user_id: str, form_data: ChatImportForm
    ) -> ChatModel:
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
                "id": id,
                "user_id": user_id,
                "title": self._clean_null_bytes(
                    form_data.chat["title"] if "title" in form_data.chat else "New Chat"
                ),
                "chat": self._clean_null_bytes(form_data.chat),
                "meta": form_data.meta,
                "pinned": form_data.pinned,
                "folder_id": form_data.folder_id,
                "created_at": (
                    form_data.created_at if form_data.created_at else int(time.time())
                ),
                "updated_at": (
                    form_data.updated_at if form_data.updated_at else int(time.time())
                ),
            }
        )
        return chat

    def import_chats(
        self,
        user_id: str,
        chat_import_forms: list[ChatImportForm],
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            chats = []

            for form_data in chat_import_forms:
                chat = self._chat_import_form_to_chat_model(user_id, form_data)
                chats.append(Chat(**chat.model_dump()))

            db.add_all(chats)
            db.commit()

            # Dual-write messages to chat_message table
            try:
                for form_data, chat_obj in zip(chat_import_forms, chats):
                    history = form_data.chat.get("history", {})
                    messages = history.get("messages", {})
                    for message_id, message in messages.items():
                        if isinstance(message, dict) and message.get("role"):
                            ChatMessages.upsert_message(
                                message_id=message_id,
                                chat_id=chat_obj.id,
                                user_id=user_id,
                                data=message,
                            )
            except Exception as e:
                log.warning(
                    f"Failed to write imported messages to chat_message table: {e}"
                )

            return [ChatModel.model_validate(chat) for chat in chats]

    def update_chat_by_id(
        self, id: str, chat: dict, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        """
        Update an existing chat's content and metadata.

        Args:
            id (str): Unique chat identifier
            chat (dict): Updated chat data including messages and history
            db (Optional[Session]): Optional database session for transaction sharing

        Returns:
            Optional[ChatModel]: Updated chat model or None if update failed

        Note:
            - Updates timestamp automatically for audit trails
            - Handles title extraction with fallback
            - Uses exception handling for graceful failure
        """
        try:
            with get_db_context(db) as db:
                chat_item = db.get(Chat, id)
                chat_item.chat = self._clean_null_bytes(chat)
                chat_item.title = (
                    self._clean_null_bytes(chat["title"])
                    if "title" in chat
                    else "New Chat"
                )
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
        with get_db_context() as db:
            chat = db.get(Chat, id)
            if chat is None:
                return None

            old_tags = chat.meta.get("tags", [])
            new_tags = [t for t in tags if t.replace(" ", "_").lower() != "none"]
            new_tag_ids = [t.replace(" ", "_").lower() for t in new_tags]

            # Single meta update
            chat.meta = {**chat.meta, "tags": new_tag_ids}
            db.commit()
            db.refresh(chat)

            # Batch-create any missing tag rows
            Tags.ensure_tags_exist(new_tags, user.id, db=db)

            # Clean up orphaned old tags in one query
            removed = set(old_tags) - set(new_tag_ids)
            if removed:
                self.delete_orphan_tags_for_user(list(removed), user.id, db=db)

            return ChatModel.model_validate(chat)

    def get_chat_title_by_id(self, id: str) -> Optional[str]:
        with get_db_context() as db:
            result = db.query(Chat.title).filter_by(id=id).first()
            if result is None:
                return None
            return result[0] or "New Chat"

    def get_messages_map_by_chat_id(self, id: str) -> Optional[dict]:
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
            message["content"] = sanitize_text_for_db(message["content"])

        user_id = chat.user_id
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

        # Dual-write to chat_message table
        try:
            ChatMessages.upsert_message(
                message_id=message_id,
                chat_id=id,
                user_id=user_id,
                data=history["messages"][message_id],
            )
        except Exception as e:
            log.warning(f"Failed to write to chat_message table: {e}")

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

    def add_message_files_by_id_and_message_id(
        self, id: str, message_id: str, files: list[dict]
    ) -> list[dict]:
        with get_db_context() as db:
            chat = self.get_chat_by_id(id, db=db)
            if chat is None:
                return None

            chat = chat.chat
            history = chat.get("history", {})

            message_files = []

            if message_id in history.get("messages", {}):
                message_files = history["messages"][message_id].get("files", [])
                message_files = message_files + files
                history["messages"][message_id]["files"] = message_files

            chat["history"] = history
            self.update_chat_by_id(id, chat, db=db)
            return message_files

    def insert_shared_chat_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        with get_db_context(db) as db:
            # Get the existing chat to share
            chat = db.get(Chat, chat_id)
            # Check if chat exists
            if not chat:
                return None
            # Check if the chat is already shared
            if chat.share_id:
                return self.get_chat_by_id_and_user_id(chat.share_id, "shared", db=db)
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

    def update_shared_chat_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, chat_id)
                shared_chat = (
                    db.query(Chat).filter_by(user_id=f"shared-{chat_id}").first()
                )

                if shared_chat is None:
                    return self.insert_shared_chat_by_chat_id(chat_id, db=db)

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

    def delete_shared_chat_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                # Use subquery to delete chat_messages for shared chats
                shared_chat_id_subquery = (
                    db.query(Chat.id)
                    .filter_by(user_id=f"shared-{chat_id}")
                    .scalar_subquery()
                )
                db.query(ChatMessage).filter(
                    ChatMessage.chat_id.in_(shared_chat_id_subquery)
                ).delete(synchronize_session=False)
                db.query(Chat).filter_by(user_id=f"shared-{chat_id}").delete()
                db.commit()

                return True
        except Exception:
            return False

    def unarchive_all_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Chat).filter_by(user_id=user_id).update({"archived": False})
                db.commit()
                return True
        except Exception:
            return False

    def update_chat_share_id_by_id(
        self, id: str, share_id: Optional[str], db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.share_id = share_id
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def toggle_chat_pinned_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.pinned = not chat.pinned
                chat.updated_at = int(time.time())
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def toggle_chat_archive_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.archived = not chat.archived
                chat.folder_id = None
                chat.updated_at = int(time.time())
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def archive_all_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
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
        db: Optional[Session] = None,
    ) -> list[ChatTitleIdResponse]:

        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=True)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction:
                    if not getattr(Chat, order_by, None):
                        raise ValueError("Invalid order_by field")

                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc(), Chat.id)
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc(), Chat.id)
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc(), Chat.id)

            query = query.with_entities(
                Chat.id, Chat.title, Chat.updated_at, Chat.created_at
            )

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
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

    def get_shared_chat_list_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[SharedChatResponse]:

        with get_db_context(db) as db:
            query = (
                db.query(Chat)
                .filter_by(user_id=user_id)
                .filter(Chat.share_id.isnot(None))
            )

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction:
                    if not getattr(Chat, order_by, None):
                        raise ValueError("Invalid order_by field")

                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc(), Chat.id)
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc(), Chat.id)
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc(), Chat.id)

            # Select only the columns needed for SharedChatResponse
            # to avoid loading the heavy chat JSON blob
            query = query.with_entities(
                Chat.id,
                Chat.title,
                Chat.share_id,
                Chat.updated_at,
                Chat.created_at,
            )

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [
                SharedChatResponse.model_validate(
                    {
                        "id": chat[0],
                        "title": chat[1],
                        "share_id": chat[2],
                        "updated_at": chat[3],
                        "created_at": chat[4],
                    }
                )
                for chat in all_chats
            ]

    def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = DEFAULT_PAGINATION_LIMIT,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
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
                        query = query.order_by(getattr(Chat, order_by).asc(), Chat.id)
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc(), Chat.id)
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc(), Chat.id)

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
        include_folders: bool = False,
        include_pinned: bool = False,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> list[ChatTitleIdResponse]:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id)

            if not include_folders:
                query = query.filter_by(folder_id=None)

            if not include_pinned:
                query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))

            if not include_archived:
                query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc(), Chat.id).with_entities(
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
        self,
        chat_ids: list[str],
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            all_chats = (
                db.query(Chat)
                .filter(Chat.id.in_(chat_ids))
                .filter_by(archived=False)
                .order_by(Chat.updated_at.desc())
                .all()
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat_item = db.get(Chat, id)
                if chat_item is None:
                    return None

                if self._sanitize_chat_row(chat_item):
                    db.commit()
                    db.refresh(chat_item)

                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    def get_chat_by_share_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                # it is possible that the shared link was deleted. hence,
                # we check if the chat is still shared by checking if a chat with the share_id exists
                chat = db.query(Chat).filter_by(share_id=id).first()

                if chat:
                    return self.get_chat_by_id(id, db=db)
                else:
                    return None
        except Exception:
            return None

    def get_chat_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.query(Chat).filter_by(id=id, user_id=user_id).first()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def is_chat_owner(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        """
        Lightweight ownership check — uses EXISTS subquery instead of loading
        the full Chat row (which includes the potentially large JSON blob).
        """
        try:
            with get_db_context(db) as db:
                return db.query(
                    exists().where(and_(Chat.id == id, Chat.user_id == user_id))
                ).scalar()
        except Exception:
            return False

    def get_chat_folder_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[str]:
        """
        Fetch only the folder_id column for a chat, without loading the full
        JSON blob. Returns None if chat doesn't exist or doesn't belong to user.
        """
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(Chat.folder_id).filter_by(id=id, user_id=user_id).first()
                )
                return result[0] if result else None
        except Exception:
            return None

    def get_chats(
        self, skip: int = 0, limit: int = 50, db: Optional[Session] = None
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            all_chats = (
                db.query(Chat)
                # .limit(limit).offset(skip)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> ChatListResponse:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id)

            if filter:
                if filter.get("updated_at"):
                    query = query.filter(Chat.updated_at > filter.get("updated_at"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction:
                    if hasattr(Chat, order_by):
                        if direction.lower() == "asc":
                            query = query.order_by(
                                getattr(Chat, order_by).asc(), Chat.id
                            )
                        elif direction.lower() == "desc":
                            query = query.order_by(
                                getattr(Chat, order_by).desc(), Chat.id
                            )
                else:
                    query = query.order_by(Chat.updated_at.desc(), Chat.id)

            else:
                query = query.order_by(Chat.updated_at.desc(), Chat.id)

            total = query.count()

            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            all_chats = query.all()

            return ChatListResponse(
                **{
                    "items": [ChatModel.model_validate(chat) for chat in all_chats],
                    "total": total,
                }
            )

    def get_pinned_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> list[ChatTitleIdResponse]:
        with get_db_context(db) as db:
            all_chats = (
                db.query(Chat)
                .filter_by(user_id=user_id, pinned=True, archived=False)
                .order_by(Chat.updated_at.desc())
                .with_entities(Chat.id, Chat.title, Chat.updated_at, Chat.created_at)
            )
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

    def get_archived_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
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
        db: Optional[Session] = None,
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
            return self.get_chat_list_by_user_id(
                user_id, include_archived, filter={}, skip=skip, limit=limit, db=db
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

        with get_db_context(db) as db:
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

            query = query.order_by(Chat.updated_at.desc(), Chat.id)

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
                    query = query.filter(text("""
                            NOT EXISTS (
                                SELECT 1
                                FROM json_each(Chat.meta, '$.tags') AS tag
                            )
                            """))
                elif tag_ids:
                    query = query.filter(
                        and_(
                            *[
                                text(f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_each(Chat.meta, '$.tags') AS tag
                                        WHERE tag.value = :tag_id_{tag_idx}
                                    )
                                    """).params(**{f"tag_id_{tag_idx}": tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )

            elif dialect_name == "postgresql":
                # PostgreSQL 17 Optimization: Enhanced JSONB array processing
                # PG17's improved GIN indexes make these queries 15-25% faster
                functions = self._get_json_functions(db)
                pg_major, _ = self._get_pg_version(db)
                is_pg17 = pg_major >= 17
                is_jsonb = functions.get("chat_is_jsonb", False)

                # Safety filter: JSON field must not contain \u0000
                query = query.filter(text("Chat.chat::text NOT LIKE '%\\\\u0000%'"))

                # Safety filter: title must not contain actual null bytes
                query = query.filter(text("Chat.title::text NOT LIKE '%\\x00%'"))

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
                query = query.filter(
                    or_(
                        Chat.title.ilike(bindparam("title_key")),
                        postgres_content_clause,
                    )
                ).params(title_key=f"%{search_text}%", content_key=search_text.lower())

                if is_pg17:
                    log.debug("Using PostgreSQL 17 optimized query path")

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
        self,
        folder_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 60,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(folder_id=folder_id, user_id=user_id)
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc(), Chat.id)

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str, db: Optional[Session] = None
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            query = db.query(Chat).filter(
                Chat.folder_id.in_(folder_ids), Chat.user_id == user_id
            )
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.folder_id = folder_id
                chat.updated_at = int(time.time())
                chat.pinned = False
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def get_chat_tags_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> list[TagModel]:
        """
        Retrieve all tags associated with a specific chat.

        Args:
            id (str): Chat identifier
            user_id (str): User identifier for security validation
            db (Optional[Session]): Optional database session for transaction sharing

        Returns:
            list[TagModel]: List of tag models associated with the chat

        Note:
            - Tags are stored as IDs in chat metadata
            - Returns full tag models with names and metadata
            - Respects user ownership for security
        """
        with get_db_context(db) as db:
            chat = db.get(Chat, id)
            tag_ids = chat.meta.get("tags", [])
            return Tags.get_tags_by_ids_and_user_id(tag_ids, user_id, db=db)

    def get_chat_list_by_user_id_and_tag_name(
        self,
        user_id: str,
        tag_name: str,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
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
        self, id: str, user_id: str, tag_name: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        tag_id = tag_name.replace(" ", "_").lower()
        Tags.ensure_tags_exist([tag_name], user_id, db=db)
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
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

    def count_chats_by_tag_name_and_user_id(
        self, tag_name: str, user_id: str, db: Optional[Session] = None
    ) -> int:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)
            tag_id = tag_name.replace(" ", "_").lower()

            if db.bind.dialect.name == "sqlite":
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
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

            return query.count()

    def delete_orphan_tags_for_user(
        self,
        tag_ids: list[str],
        user_id: str,
        threshold: int = 0,
        db: Optional[Session] = None,
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
        with get_db_context(db) as db:
            orphans = []
            for tag_id in tag_ids:
                count = self.count_chats_by_tag_name_and_user_id(tag_id, user_id, db=db)
                if count <= threshold:
                    orphans.append(tag_id)
            Tags.delete_tags_by_ids_and_user_id(orphans, user_id, db=db)

    def count_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str, db: Optional[Session] = None
    ) -> int:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id)

            query = query.filter_by(folder_id=folder_id)
            count = query.count()

            log.info(f"Count of chats for folder '{folder_id}': {count}")
            return count

    def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
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

    def delete_all_tags_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.meta = {
                    **chat.meta,
                    "tags": [],
                }
                db.commit()

                return True
        except Exception:
            return False

    def delete_chat_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(ChatMessage).filter_by(chat_id=id).delete()
                db.query(Chat).filter_by(id=id).delete()
                db.commit()

                return True and self.delete_shared_chat_by_chat_id(id, db=db)
        except Exception:
            return False

    def delete_chat_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
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
            db (Optional[Session]): Optional database session for transaction sharing

        Returns:
            bool: True if deletion successful, False otherwise

        Security Note:
            - Only allows deletion by chat owner
            - Prevents unauthorized data access
            - Maintains audit trail through logging
        """
        try:
            with get_db_context(db) as db:
                db.query(ChatMessage).filter_by(chat_id=id).delete()
                db.query(Chat).filter_by(id=id, user_id=user_id).delete()
                db.commit()

                return True and self.delete_shared_chat_by_chat_id(id, db=db)
        except Exception:
            return False

    def delete_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                self.delete_shared_chats_by_user_id(user_id, db=db)

                chat_id_subquery = (
                    db.query(Chat.id).filter_by(user_id=user_id).subquery()
                )
                db.query(ChatMessage).filter(
                    ChatMessage.chat_id.in_(chat_id_subquery)
                ).delete(synchronize_session=False)
                db.query(Chat).filter_by(user_id=user_id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                chat_id_subquery = (
                    db.query(Chat.id)
                    .filter_by(user_id=user_id, folder_id=folder_id)
                    .subquery()
                )
                db.query(ChatMessage).filter(
                    ChatMessage.chat_id.in_(chat_id_subquery)
                ).delete(synchronize_session=False)
                db.query(Chat).filter_by(user_id=user_id, folder_id=folder_id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def move_chats_by_user_id_and_folder_id(
        self,
        user_id: str,
        folder_id: str,
        new_folder_id: Optional[str],
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Chat).filter_by(user_id=user_id, folder_id=folder_id).update(
                    {"folder_id": new_folder_id}
                )
                db.commit()

                return True
        except Exception:
            return False

    def delete_shared_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                chats_by_user = db.query(Chat).filter_by(user_id=user_id).all()
                shared_chat_ids = [f"shared-{chat.id}" for chat in chats_by_user]

                # Use subquery to delete chat_messages for shared chats
                shared_id_subq = (
                    db.query(Chat.id)
                    .filter(Chat.user_id.in_(shared_chat_ids))
                    .subquery()
                )
                db.query(ChatMessage).filter(
                    ChatMessage.chat_id.in_(shared_id_subq)
                ).delete(synchronize_session=False)
                db.query(Chat).filter(Chat.user_id.in_(shared_chat_ids)).delete()
                db.commit()

                return True
        except Exception:
            return False

    def insert_chat_files(
        self,
        chat_id: str,
        message_id: str,
        file_ids: list[str],
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[list[ChatFileModel]]:
        if not file_ids:
            return None

        chat_message_file_ids = [
            item.id
            for item in self.get_chat_files_by_chat_id_and_message_id(
                chat_id, message_id, db=db
            )
        ]
        # Remove duplicates and existing file_ids
        file_ids = list(
            set(
                [
                    file_id
                    for file_id in file_ids
                    if file_id and file_id not in chat_message_file_ids
                ]
            )
        )
        if not file_ids:
            return None

        try:
            with get_db_context(db) as db:
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

                results = [
                    ChatFile(**chat_file.model_dump()) for chat_file in chat_files
                ]

                db.add_all(results)
                db.commit()

                return chat_files
        except Exception:
            return None

    def get_chat_files_by_chat_id_and_message_id(
        self, chat_id: str, message_id: str, db: Optional[Session] = None
    ) -> list[ChatFileModel]:
        with get_db_context(db) as db:
            all_chat_files = (
                db.query(ChatFile)
                .filter_by(chat_id=chat_id, message_id=message_id)
                .order_by(ChatFile.created_at.asc())
                .all()
            )
            return [
                ChatFileModel.model_validate(chat_file) for chat_file in all_chat_files
            ]

    def delete_chat_file(
        self, chat_id: str, file_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(ChatFile).filter_by(chat_id=chat_id, file_id=file_id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def get_shared_chats_by_file_id(
        self, file_id: str, db: Optional[Session] = None
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            # Join Chat and ChatFile tables to get shared chats associated with the file_id
            all_chats = (
                db.query(Chat)
                .join(ChatFile, Chat.id == ChatFile.chat_id)
                .filter(ChatFile.file_id == file_id, Chat.share_id.isnot(None))
                .all()
            )

            return [ChatModel.model_validate(chat) for chat in all_chats]


# Global instance for chat operations - thread-safe singleton pattern
# This instance provides the main interface for all chat-related database operations
Chats = ChatTable()
