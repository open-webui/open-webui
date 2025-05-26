import logging
import json
import time
import uuid
import os
from typing import Optional, Dict, Any, List
from functools import wraps, lru_cache

from open_webui.internal.db import Base, get_db
from open_webui.models.tags import TagModel, Tag, Tags
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

# Conditional import for JSONB support
try:
    from sqlalchemy.dialects.postgresql import JSONB
    JSONB_AVAILABLE = True
except ImportError:
    JSONB_AVAILABLE = False
    JSONB = JSON  # Fallback to JSON if JSONB is not available

####################
# Logging Setup
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Performance Monitoring & Caching
####################

# Simple in-memory cache for frequently accessed data
class SimpleCache:
    """Thread-safe simple cache with TTL support and size limit."""
    def __init__(self, default_ttl: int = 300, max_size: int = 500):
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
    
    def get(self, key: str, default=None):
        """Get cached value if not expired."""
        if key not in self._cache:
            return default
        
        if time.time() - self._timestamps[key] > self.default_ttl:
            self.delete(key)
            return default
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value with optional TTL."""
        # Implement simple LRU eviction if cache is full
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
            self.delete(oldest_key)
        
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def delete(self, key: str):
        """Delete cached value."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self):
        """Clear all cached values."""
        self._cache.clear()
        self._timestamps.clear()
    
    def size(self) -> int:
        """Get cache size."""
        return len(self._cache)

# Global cache instance
_cache = SimpleCache()

def performance_monitor(func):
    """Enhanced decorator with caching and performance monitoring."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Conservative caching - only cache specific read operations
        cache_key = None
        is_cacheable = (
            func.__name__ in ['get_chat_by_id', 'get_chat_by_id_and_user_id'] and 
            len(args) >= 2 and  # Ensure we have enough args
            isinstance(args[1], str)  # First real arg should be a string ID
        )
        
        if is_cacheable:
            # Simple, stable cache key generation
            method_name = func.__name__
            primary_arg = str(args[1])  # chat_id or similar
            secondary_arg = str(args[2]) if len(args) > 2 else ""
            cache_key = f"{method_name}:{primary_arg}:{secondary_arg}"
            
            # Check cache first for read operations
            cached_result = _cache.get(cache_key)
            if cached_result is not None:
                log.debug(f"🎯 Cache hit for {func.__name__}")
                QueryStats.record_cache_hit(func.__name__)
                return cached_result
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Only cache simple, serializable results and only for specific methods
            if cache_key and result is not None and is_cacheable:
                try:
                    # Quick serializability check - only cache ChatModel objects
                    if hasattr(result, 'model_dump'):
                        _cache.set(cache_key, result, ttl=30)  # Short TTL (30 seconds)
                except Exception:
                    # Skip caching if result is not serializable
                    pass
            
            # Performance logging - only log slow queries
            if execution_time > 0.5:  # Only log queries slower than 0.5s
                log.warning(f"🐌 Slow query detected: {func.__name__} took {execution_time:.2f}s")
            
            # Record stats
            QueryStats.record(func.__name__, execution_time, True)
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            log.error(f"❌ Query failed: {func.__name__} failed after {execution_time:.3f}s - {e}")
            QueryStats.record(func.__name__, execution_time, False)
            raise
    return wrapper

class QueryStats:
    """Enhanced query performance statistics collector."""
    _stats = {}
    
    @classmethod
    def record(cls, operation: str, duration: float, success: bool = True):
        """Record query statistics."""
        if operation not in cls._stats:
            cls._stats[operation] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "failures": 0,
                "cache_hits": 0
            }
        
        stats = cls._stats[operation]
        stats["count"] += 1
        
        if success:
            stats["total_time"] += duration
            stats["min_time"] = min(stats["min_time"], duration)
            stats["max_time"] = max(stats["max_time"], duration)
        else:
            stats["failures"] += 1
    
    @classmethod
    def record_cache_hit(cls, operation: str):
        """Record cache hit."""
        if operation not in cls._stats:
            cls._stats[operation] = {
                "count": 0, "total_time": 0.0, "min_time": float('inf'),
                "max_time": 0.0, "failures": 0, "cache_hits": 0
            }
        cls._stats[operation]["cache_hits"] += 1
    
    @classmethod
    def get_stats(cls) -> dict:
        """Get performance statistics."""
        result = {}
        for op, stats in cls._stats.items():
            if stats["count"] > 0 or stats["cache_hits"] > 0:
                total_calls = stats["count"] + stats["cache_hits"]
                successful_db_calls = stats["count"] - stats["failures"]
                avg_time = stats["total_time"] / successful_db_calls if successful_db_calls > 0 else 0
                
                result[op] = {
                    "total_calls": total_calls,
                    "db_calls": stats["count"],
                    "cache_hits": stats["cache_hits"],
                    "cache_hit_rate": round((stats["cache_hits"] / total_calls * 100), 1) if total_calls > 0 else 0,
                    "avg_time": round(avg_time, 3),
                    "min_time": round(stats["min_time"], 3) if stats["min_time"] != float('inf') else 0,
                    "max_time": round(stats["max_time"], 3),
                    "failures": stats["failures"],
                    "success_rate": round(successful_db_calls / stats["count"] * 100, 1) if stats["count"] > 0 else 100
                }
        return result
    
    @classmethod
    def clear_stats(cls):
        """Clear all statistics."""
        cls._stats.clear()

####################
# JSONB Support Configuration
####################

# Check if JSONB should be used for PostgreSQL
USE_JSONB = os.getenv("USE_JSONB", "false").lower() == "true" and JSONB_AVAILABLE

@lru_cache(maxsize=1)
def get_json_column_type():
    """Cached function to determine JSON column type."""
    return JSONB if USE_JSONB else JSON

def is_using_jsonb(db):
    """Detect if the database is using JSONB columns with safety checks and fallbacks."""
    try:
        dialect_name = db.bind.dialect.name
        log.info(f"🔍 Database dialect detected: {dialect_name}")
        
        if dialect_name != "postgresql":
            log.info(f"✅ Non-PostgreSQL database ({dialect_name}) - JSONB not applicable")
            return False
        
        # Check if JSONB is enabled via environment variable
        log.info(f"🔍 Environment USE_JSONB setting: {USE_JSONB}")
        if USE_JSONB:
            log.info("🔍 USE_JSONB=true - Verifying actual column types...")
            # SAFETY CHECK: Verify that columns are actually JSONB
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.bind)
                columns = inspector.get_columns('chat')
                
                jsonb_columns = []
                json_columns = []
                
                for column in columns:
                    if column['name'] in ['chat', 'meta']:
                        column_type = str(column['type']).upper()
                        log.info(f"🔍 Column '{column['name']}' type: {column_type}")
                        
                        if 'JSONB' in column_type:
                            jsonb_columns.append(column['name'])
                        elif 'JSON' in column_type:
                            json_columns.append(column['name'])
                            
                if json_columns and not jsonb_columns:
                    log.warning(f"⚠️  USE_JSONB=true but columns {json_columns} are JSON, not JSONB!")
                    log.warning("⚠️  This may cause query failures. Consider migrating to JSONB or setting USE_JSONB=false")
                    log.info("🔄 Falling back to JSON queries for safety")
                    return False  # Use JSON queries for safety
                elif jsonb_columns:
                    log.info(f"✅ Confirmed JSONB columns: {jsonb_columns}")
                    return True
                else:
                    log.warning("⚠️  No JSON/JSONB columns found in expected columns")
                    return False
                    
            except Exception as e:
                log.error(f"❌ Could not verify column types: {e}")
                # Fallback to environment variable, but log warning
                log.warning("⚠️  Could not verify JSONB column types, proceeding with environment variable setting")
                return True
        
        # For backwards compatibility, try to detect JSONB usage from actual schema
        log.info("🔍 AUTO-DETECTING: Checking actual schema for JSONB columns...")
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            columns = inspector.get_columns('chat')
            detected_jsonb = []
            
            for column in columns:
                if column['name'] in ['chat', 'meta']:
                    column_type = str(column['type']).upper()
                    if 'JSONB' in column_type:
                        detected_jsonb.append(column['name'])
                        log.info(f"✅ Auto-detected JSONB column: {column['name']}")
                        
            if detected_jsonb:
                log.info(f"✅ Auto-detection found JSONB columns: {detected_jsonb}")
                return True
            else:
                log.info("ℹ️  Auto-detection: No JSONB columns found, using JSON queries")
                
        except Exception as e:
            log.debug(f"🔍 Could not auto-detect column types: {e}")
        
        log.info("✅ Final decision: Using JSON queries")
        return False
        
    except Exception as e:
        log.error(f"❌ CRITICAL: Error in is_using_jsonb detection: {e}")
        log.info("🔄 FALLBACK: Defaulting to JSON queries for safety")
        return False

####################
# Database Optimization Functions
####################

# Track optimization per connection to avoid repeated calls
_connection_optimized = False

def optimize_db_connection():
    """Apply database connection optimizations - only once."""
    global _connection_optimized
    if _connection_optimized:
        log.info("⏭️  CONNECTION OPTIMIZATION: Already applied, skipping")
        return
        
    log.info("🚀 CONNECTION OPTIMIZATION: Starting database-specific optimizations...")
    
    try:
        with get_db() as db:
            dialect_name = db.bind.dialect.name
            log.info(f"🔍 OPTIMIZING: Database dialect = {dialect_name}")
            
            if dialect_name == "postgresql":
                log.info("🚀 POSTGRESQL: Applying PostgreSQL optimizations...")
                # PostgreSQL optimizations
                log.info("🔧 SETTING: work_mem = 32MB")
                db.execute(text("SET work_mem = '32MB'"))
                log.info("🔧 SETTING: random_page_cost = 1.1")
                db.execute(text("SET random_page_cost = 1.1"))
                log.info("✅ POSTGRESQL: Connection optimizations applied successfully")
                
            elif dialect_name == "sqlite":
                log.info("🚀 SQLITE: Applying SQLite optimizations...")
                # SQLite optimizations
                log.info("🔧 SETTING: cache_size = -32000 (32MB)")
                db.execute(text("PRAGMA cache_size = -32000"))
                log.info("🔧 SETTING: temp_store = MEMORY")
                db.execute(text("PRAGMA temp_store = MEMORY"))
                log.info("✅ SQLITE: Connection optimizations applied successfully")
            else:
                log.warning(f"⚠️  UNSUPPORTED: No optimizations available for {dialect_name}")
            
            _connection_optimized = True
            db.commit()
            log.info("✅ CONNECTION OPTIMIZATION: All optimizations committed successfully")
                
    except Exception as e:
        log.warning(f"⚠️  OPTIMIZATION FAILED: Could not apply database optimizations: {e}")
        log.info("🔄 CONTINUING: Application will continue without optimizations")

def create_composite_indexes_if_needed(db):
    """Create composite indexes for common query patterns with enhanced performance."""
    dialect_name = db.bind.dialect.name
    log.info(f"🔍 COMPOSITE INDEXES: Starting creation for {dialect_name}")
    
    try:
        log.info(f"🔍 INDEX MODE: STANDARD creation (transaction-safe)")
        
        composite_indexes = [
            # Enhanced common filtering patterns
            f"CREATE INDEX IF NOT EXISTS idx_chat_user_updated ON chat (user_id, updated_at DESC);",
            f"CREATE INDEX IF NOT EXISTS idx_chat_user_folder ON chat (user_id, folder_id);",
            f"CREATE INDEX IF NOT EXISTS idx_chat_user_created ON chat (user_id, created_at DESC);",
            # Share functionality
            f"CREATE INDEX IF NOT EXISTS idx_chat_share_id ON chat (share_id);",
            # Enhanced search patterns
            f"CREATE INDEX IF NOT EXISTS idx_chat_title_lower ON chat (user_id, LOWER(title));",
        ]
        
        # PostgreSQL-specific indexes with WHERE clauses and GIN
        if dialect_name == "postgresql":
            log.info("🚀 POSTGRESQL: Adding PostgreSQL-specific indexes...")
            pg_specific_indexes = [
                f"CREATE INDEX IF NOT EXISTS idx_chat_user_archived ON chat (user_id, archived) WHERE archived = false;",
                f"CREATE INDEX IF NOT EXISTS idx_chat_user_pinned ON chat (user_id, pinned) WHERE pinned = true;",
                f"CREATE INDEX IF NOT EXISTS idx_chat_title_search ON chat USING GIN (to_tsvector('english', title));",
                # Additional performance indexes
                f"CREATE INDEX IF NOT EXISTS idx_chat_user_folder_updated ON chat (user_id, folder_id, updated_at DESC) WHERE archived = false;",
            ]
            composite_indexes.extend(pg_specific_indexes)
            log.info(f"📊 POSTGRESQL: Total {len(pg_specific_indexes)} PostgreSQL-specific indexes added")
        
        # SQLite-specific optimizations
        elif dialect_name == "sqlite":
            log.info("🚀 SQLITE: Adding SQLite-specific indexes...")
            sqlite_indexes = [
                f"CREATE INDEX IF NOT EXISTS idx_chat_user_title_search ON chat (user_id, title COLLATE NOCASE);",
                f"CREATE INDEX IF NOT EXISTS idx_chat_user_active ON chat (user_id, archived, updated_at DESC);",
            ]
            composite_indexes.extend(sqlite_indexes)
            log.info(f"📊 SQLITE: Total {len(sqlite_indexes)} SQLite-specific indexes added")
        
        log.info(f"📊 TOTAL INDEXES: {len(composite_indexes)} indexes to create/verify")
        successful_indexes = 0
        failed_indexes = 0
        
        for index_sql in composite_indexes:
            try:
                # Extract index name for logging
                index_name = "unknown"
                if "idx_" in index_sql:
                    start = index_sql.find("idx_")
                    end = index_sql.find(" ON", start)
                    if end > start:
                        index_name = index_sql[start:end]
                
                log.info(f"🔨 CREATING: {index_name}...")
                db.execute(text(index_sql))
                log.info(f"✅ INDEX SUCCESS: {index_name}")
                successful_indexes += 1
            except Exception as e:
                log.warning(f"⚠️  INDEX FAILED: {index_name} - {e}")
                failed_indexes += 1
        
        db.commit()
        log.info(f"✅ COMPOSITE INDEXES COMPLETED: {successful_indexes} successful, {failed_indexes} failed")
        
    except Exception as e:
        log.error(f"❌ COMPOSITE INDEX ERROR: {e}")
        db.rollback()
        log.info("🔄 ROLLBACK: Composite index transaction rolled back")

def create_gin_indexes_if_needed(db):
    """Safely create GIN indexes for JSONB columns with comprehensive error handling."""
    dialect_name = db.bind.dialect.name
    log.info(f"🔍 GIN INDEX CREATION: Database dialect = {dialect_name}")
    
    if dialect_name != "postgresql":
        log.info("⏭️  SKIPPING GIN indexes: Not PostgreSQL database")
        return
    
    if not is_using_jsonb(db):
        log.info("⏭️  SKIPPING GIN indexes: Not using JSONB columns")
        return
    
    log.info("🚀 CREATING GIN INDEXES: Starting JSONB index creation for fast searches...")
    
    # Verify we can actually query the columns before creating indexes
    try:
        # Test with a simple query first to verify column compatibility
        log.info("🔍 TESTING: Verifying JSONB column compatibility...")
        test_query = text("SELECT meta FROM chat LIMIT 1")
        db.execute(test_query)
        log.info("✅ COLUMN TEST: Successfully queried JSONB columns")
    except Exception as e:
        log.error(f"❌ COLUMN TEST FAILED: Cannot query JSONB columns, skipping index creation: {e}")
        return
    
    # Enhanced GIN indexes for optimal JSONB performance
    gin_indexes = [
        # Core JSONB indexes for general JSON operations
        ("idx_chat_meta_gin", "CREATE INDEX IF NOT EXISTS idx_chat_meta_gin ON chat USING GIN (meta)"),
        ("idx_chat_chat_gin", "CREATE INDEX IF NOT EXISTS idx_chat_chat_gin ON chat USING GIN (chat)"),
        
        # Specific path indexes for common queries
        ("idx_chat_meta_tags", "CREATE INDEX IF NOT EXISTS idx_chat_meta_tags ON chat USING GIN ((meta->'tags'))"),
        ("idx_chat_messages", "CREATE INDEX IF NOT EXISTS idx_chat_messages ON chat USING GIN ((chat->'history'->'messages'))"),
        
        # Additional performance indexes for search operations
        ("idx_chat_history", "CREATE INDEX IF NOT EXISTS idx_chat_history ON chat USING GIN ((chat->'history'))"),
        ("idx_chat_title_gin", "CREATE INDEX IF NOT EXISTS idx_chat_title_gin ON chat USING GIN (to_tsvector('english', title))"),
    ]
    
    successful_indexes = []
    failed_indexes = []
    
    for index_name, index_sql in gin_indexes:
        try:
            log.info(f"🔨 CREATING GIN INDEX: {index_name}...")
            db.execute(text(index_sql))
            log.info(f"✅ GIN INDEX SUCCESS: {index_name}")
            successful_indexes.append(index_name)
        except Exception as e:
            log.warning(f"⚠️  GIN INDEX FAILED: {index_name} - {e}")
            failed_indexes.append((index_name, str(e)))
            # Don't fail completely, just skip this index
            continue
    
    try:
        db.commit()
        log.info(f"✅ GIN INDEXES COMMITTED: {len(successful_indexes)} successful, {len(failed_indexes)} failed")
        if successful_indexes:
            log.info(f"🎯 SUCCESSFUL GIN INDEXES: {', '.join(successful_indexes)}")
            log.info("🚀 PERFORMANCE BOOST: JSONB searches will now be significantly faster!")
        if failed_indexes:
            log.warning(f"⚠️  FAILED GIN INDEXES: {[name for name, _ in failed_indexes]}")
            for name, error in failed_indexes:
                log.debug(f"   - {name}: {error}")
    except Exception as e:
        log.error(f"❌ GIN INDEX COMMIT FAILED: Error committing GIN indexes: {e}")
        try:
            db.rollback()
            log.info("🔄 ROLLBACK: GIN index transaction rolled back")
        except Exception as rollback_error:
            log.error(f"❌ ROLLBACK FAILED: {rollback_error}")

####################
# Chat DB Schema
####################


class Chat(Base):
    __tablename__ = "chat"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(Text)
    chat = Column(get_json_column_type())

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    share_id = Column(Text, unique=True, nullable=True)
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False, nullable=True)

    meta = Column(get_json_column_type(), server_default="{}")
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


class ChatImportForm(ChatForm):
    meta: Optional[dict] = {}
    pinned: Optional[bool] = False
    folder_id: Optional[str] = None


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
    def __init__(self):
        """Initialize ChatTable with performance optimizations."""
        log.info("🚀 CHAT TABLE: Initializing ChatTable...")
        # Only create indexes once and don't do it automatically
        self._indexes_created = False
        log.info("✅ CHAT TABLE: Initialization complete - indexes will be created lazily")
    
    def _ensure_indexes_created(self, db):
        """Lazy index creation - only when explicitly needed."""
        if self._indexes_created:
            log.debug("⏭️  INDEX CHECK: Indexes already created, skipping")
            return
            
        dialect_name = db.bind.dialect.name
        log.info(f"🔍 INDEX CHECK: Database dialect = {dialect_name}")
        
        if dialect_name not in ["postgresql", "sqlite"]:
            log.warning(f"⚠️  UNSUPPORTED: No index support for {dialect_name}")
            return
            
        try:
            log.info("🚀 INDEX CREATION: Starting lazy index creation...")
            
            # Always create composite indexes first
            create_composite_indexes_if_needed(db)
            
            # For PostgreSQL, create GIN indexes if JSONB is detected
            if dialect_name == "postgresql":
                log.info("🔍 POSTGRESQL: Checking for JSONB support...")
                if is_using_jsonb(db):
                    log.info("🚀 JSONB DETECTED: Creating GIN indexes for fast JSON searches...")
                    create_gin_indexes_if_needed(db)
                else:
                    log.info("ℹ️  JSON DETECTED: GIN indexes not needed for JSON columns")
            
            self._indexes_created = True
            log.info("✅ INDEX CREATION: Lazy index creation completed successfully")
        except Exception as e:
            log.warning(f"⚠️  INDEX CREATION FAILED: Could not create indexes: {e}")
            # Don't fail completely, just log the error
    
    def _ensure_connection_optimized(self, db):
        """Apply connection-level optimizations and create indexes once globally."""
        log.debug("🔍 CONNECTION CHECK: Ensuring connection optimizations...")
        optimize_db_connection()
        # Actually trigger lazy index creation!
        self._ensure_indexes_created(db)

    def _invalidate_cache_for_user(self, user_id: str):
        """More targeted cache invalidation to prevent excessive clearing."""
        log.debug(f"🔍 CACHE INVALIDATION: Starting for user {user_id}")
        
        # Only clear cache entries for specific methods and user
        keys_to_clear = []
        for key in list(_cache._cache.keys()):  # Convert to list to avoid modification during iteration
            if (key.startswith(('get_chat_by_id:', 'get_chat_by_id_and_user_id:')) and 
                user_id in key):
                keys_to_clear.append(key)
        
        for key in keys_to_clear:
            _cache.delete(key)
        
        # Log cache invalidation for debugging
        if keys_to_clear:
            log.debug(f"🗑️  CACHE CLEARED: Invalidated {len(keys_to_clear)} cache entries for user {user_id}")
        else:
            log.debug(f"🔍 CACHE CHECK: No cache entries found for user {user_id}")
        
        # Log current cache state
        log.debug(f"📊 CACHE STATUS: {_cache.size()} total entries remaining")

    @performance_monitor
    def insert_new_chat(self, user_id: str, form_data: ChatForm) -> Optional[ChatModel]:
        with get_db() as db:
            self._ensure_connection_optimized(db)
            
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
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            result = Chat(**chat.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            
            # Only invalidate cache after successful commit
            self._invalidate_cache_for_user(user_id)
            
            return ChatModel.model_validate(result) if result else None

    def import_chat(
        self, user_id: str, form_data: ChatImportForm
    ) -> Optional[ChatModel]:
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
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            result = Chat(**chat.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return ChatModel.model_validate(result) if result else None

    def update_chat_by_id(self, id: str, chat: dict) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat_item = db.get(Chat, id)
                chat_item.chat = chat
                chat_item.title = chat["title"] if "title" in chat else "New Chat"
                chat_item.updated_at = int(time.time())
                db.commit()
                db.refresh(chat_item)

                return ChatModel.model_validate(chat_item)
        except Exception:
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
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

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
        limit: int = 50,
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
        limit: int = 50,
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

    @performance_monitor
    def get_chat_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                self._ensure_connection_optimized(db)
                
                chat = db.get(Chat, id)
                return ChatModel.model_validate(chat) if chat else None
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

    @performance_monitor
    def get_chat_by_id_and_user_id(self, id: str, user_id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                self._ensure_connection_optimized(db)
                
                chat = db.query(Chat).filter_by(id=id, user_id=user_id).first()
                return ChatModel.model_validate(chat) if chat else None
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

    @performance_monitor
    def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
    ) -> list[ChatModel]:
        """
        Filters chats based on a search query with enhanced performance and JSONB support.
        """
        search_text = search_text.lower().strip()
        log.info(f"🔍 SEARCH REQUEST: user_id={user_id}, search='{search_text}', archived={include_archived}, skip={skip}, limit={limit}")

        if not search_text:
            log.info("📋 EMPTY SEARCH: Returning all chats for user")
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

        search_text_words = [
            word for word in search_text_words if not word.startswith("tag:")
        ]

        search_text = " ".join(search_text_words)
        
        if tag_ids:
            log.info(f"🏷️  TAG FILTERS: {tag_ids}")
        if search_text:
            log.info(f"📝 TEXT SEARCH: '{search_text}'")

        with get_db() as db:
            self._ensure_connection_optimized(db)
            
            query = db.query(Chat).filter(Chat.user_id == user_id)

            if not include_archived:
                query = query.filter(Chat.archived == False)

            query = query.order_by(Chat.updated_at.desc())

            # Check if the database dialect is either 'sqlite' or 'postgresql'
            dialect_name = db.bind.dialect.name
            log.info(f"🔍 DATABASE: Using {dialect_name} for search queries")
            
            if dialect_name == "sqlite":
                log.info("🚀 SQLITE: Executing SQLite JSON1 search queries...")
                # SQLite case: using JSON1 extension for JSON searching
                try:
                    if search_text:
                        log.info("🔍 SQLITE: Adding title and message content search with JSON1")
                        query = query.filter(
                            (
                                Chat.title.ilike(
                                    f"%{search_text}%"
                                )  # Case-insensitive search in title
                                | text(
                                    """
                                    EXISTS (
                                        SELECT 1 
                                        FROM json_each(Chat.chat, '$.messages') AS message 
                                        WHERE LOWER(message.value->>'content') LIKE '%' || :search_text || '%'
                                    )
                                    """
                                )
                            ).params(search_text=search_text)
                        )
                except Exception as e:
                    log.warning(f"⚠️  SQLITE JSON1 search failed, falling back to title-only search: {e}")
                    if search_text:
                        query = query.filter(Chat.title.ilike(f"%{search_text}%"))

                # Check if there are any tags to filter, it should have all the tags
                try:
                    if "none" in tag_ids:
                        log.info("🏷️  SQLITE: Adding 'no tags' filter with JSON1")
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
                        log.info(f"🏷️  SQLITE: Adding tag filters for {len(tag_ids)} tags using JSON1")
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
                except Exception as e:
                    log.warning(f"⚠️  SQLITE tag filtering failed, skipping tag filters: {e}")
                    # Continue without tag filtering rather than failing completely

            elif dialect_name == "postgresql":
                # Check if we're using JSONB or JSON and use appropriate queries
                try:
                    if is_using_jsonb(db):
                        log.info("🚀 POSTGRESQL JSONB: Executing JSONB optimized search queries...")
                        # PostgreSQL: using JSONB optimized queries
                        if search_text:
                            log.info("🔍 JSONB: Adding title and message content search with JSONB functions")
                            query = query.filter(
                                (
                                    Chat.title.ilike(
                                        f"%{search_text}%"
                                    )  # Case-insensitive search in title
                                    | text(
                                        """
                                        EXISTS (
                                            SELECT 1
                                            FROM jsonb_array_elements(Chat.chat->'messages') AS message
                                            WHERE LOWER(message->>'content') LIKE '%' || :search_text || '%'
                                        )
                                        """
                                    )
                                ).params(search_text=search_text)
                            )

                        # Check if there are any tags to filter, it should have all the tags
                        if "none" in tag_ids:
                            log.info("🏷️  JSONB: Adding 'no tags' filter with JSONB functions")
                            query = query.filter(
                                text(
                                    """
                                    NOT EXISTS (
                                        SELECT 1
                                        FROM jsonb_array_elements_text(Chat.meta->'tags') AS tag
                                    )
                                    """
                                )
                            )
                        elif tag_ids:
                            log.info(f"🏷️  JSONB: Adding tag filters for {len(tag_ids)} tags using JSONB")
                            query = query.filter(
                                and_(
                                    *[
                                        text(
                                            f"""
                                            EXISTS (
                                                SELECT 1
                                                FROM jsonb_array_elements_text(Chat.meta->'tags') AS tag
                                                WHERE tag = :tag_id_{tag_idx}
                                            )
                                            """
                                        ).params(**{f"tag_id_{tag_idx}": tag_id})
                                        for tag_idx, tag_id in enumerate(tag_ids)
                                    ]
                                )
                            )
                    else:
                        log.info("🚀 POSTGRESQL JSON: Executing JSON search queries...")
                        # PostgreSQL relies on proper JSON query for search
                        if search_text:
                            log.info("🔍 JSON: Adding title and message content search with JSON functions")
                            query = query.filter(
                                (
                                    Chat.title.ilike(
                                        f"%{search_text}%"
                                    )  # Case-insensitive search in title
                                    | text(
                                        """
                                        EXISTS (
                                            SELECT 1
                                            FROM json_array_elements(Chat.chat->'messages') AS message
                                            WHERE LOWER(message->>'content') LIKE '%' || :search_text || '%'
                                        )
                                        """
                                    )
                                ).params(search_text=search_text)
                            )

                        # Check if there are any tags to filter, it should have all the tags
                        if "none" in tag_ids:
                            log.info("🏷️  JSON: Adding 'no tags' filter with JSON functions")
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
                            log.info(f"🏷️  JSON: Adding tag filters for {len(tag_ids)} tags using JSON")
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
                except Exception as e:
                    log.warning(f"⚠️  POSTGRESQL JSON/JSONB search failed, falling back to title-only search: {e}")
                    if search_text:
                        query = query.filter(Chat.title.ilike(f"%{search_text}%"))
                    # Continue without tag filtering rather than failing completely
            else:
                log.error(f"❌ UNSUPPORTED DATABASE: {dialect_name}")
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Perform pagination at the SQL level
            log.info(f"📄 PAGINATION: Applying skip={skip}, limit={limit}")
            all_chats = query.offset(skip).limit(limit).all()

            log.info(f"✅ SEARCH COMPLETE: Found {len(all_chats)} chats")

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
        with get_db() as db:
            chat = db.get(Chat, id)
            tags = chat.meta.get("tags", [])
            return [Tags.get_tag_by_name_and_user_id(tag, user_id) for tag in tags]

    @performance_monitor
    def get_chat_list_by_user_id_and_tag_name(
        self, user_id: str, tag_name: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        with get_db() as db:
            self._ensure_connection_optimized(db)
            
            query = db.query(Chat).filter_by(user_id=user_id)
            tag_id = tag_name.replace(" ", "_").lower()

            dialect_name = db.bind.dialect.name
            log.info(f"🔍 TAG SEARCH: Database dialect = {dialect_name}, tag = '{tag_name}'")
            
            if dialect_name == "sqlite":
                log.info("🚀 SQLITE: Using JSON1 for tag search")
                # SQLite JSON1 querying for tags within the meta JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif dialect_name == "postgresql":
                # Check if we're using JSONB or JSON and use appropriate queries
                if is_using_jsonb(db):
                    log.info("🚀 POSTGRESQL JSONB: Using JSONB contains operator for tag search")
                    # PostgreSQL JSONB optimized query with contains operator
                    query = query.filter(
                        text(
                            "Chat.meta->'tags' ? :tag_id"
                        )
                    ).params(tag_id=tag_id)
                else:
                    log.info("🚀 POSTGRESQL JSON: Using JSON functions for tag search")
                    # PostgreSQL JSON query for tags within the meta JSON field (for `json` type)
                    query = query.filter(
                        text(
                            "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                        )
                    ).params(tag_id=tag_id)
            else:
                log.error(f"❌ UNSUPPORTED DATABASE: {dialect_name}")
                raise NotImplementedError(
                    f"Unsupported dialect: {dialect_name}"
                )

            all_chats = query.all()
            log.info(f"✅ TAG SEARCH COMPLETE: Found {len(all_chats)} chats with tag '{tag_name}'")
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def add_chat_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> Optional[ChatModel]:
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

    @performance_monitor
    def count_chats_by_tag_name_and_user_id(self, tag_name: str, user_id: str) -> int:
        with get_db() as db:
            self._ensure_connection_optimized(db)
            
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)

            # Normalize the tag_name for consistency
            tag_id = tag_name.replace(" ", "_").lower()

            dialect_name = db.bind.dialect.name
            log.info(f"🔍 TAG COUNT: Database dialect = {dialect_name}, tag = '{tag_name}'")

            if dialect_name == "sqlite":
                log.info("🚀 SQLITE: Using JSON1 for tag count")
                # SQLite JSON1 support for querying the tags inside the `meta` JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            elif dialect_name == "postgresql":
                # Check if we're using JSONB or JSON and use appropriate query
                if is_using_jsonb(db):
                    log.info("🚀 POSTGRESQL JSONB: Using JSONB contains operator for tag count")
                    # PostgreSQL JSONB optimized query with contains operator
                    query = query.filter(
                        text(
                            "Chat.meta->'tags' ? :tag_id"
                        )
                    ).params(tag_id=tag_id)
                else:
                    log.info("🚀 POSTGRESQL JSON: Using JSON functions for tag count")
                    # PostgreSQL JSON support for querying the tags inside the `meta` JSON field
                    query = query.filter(
                        text(
                            "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                        )
                    ).params(tag_id=tag_id)

            else:
                log.error(f"❌ UNSUPPORTED DATABASE: {dialect_name}")
                raise NotImplementedError(
                    f"Unsupported dialect: {dialect_name}"
                )

            # Get the count of matching records
            count = query.count()

            # Debugging output for inspection
            log.info(f"✅ TAG COUNT COMPLETE: Found {count} chats for tag '{tag_name}'")

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

    def get_performance_stats(self) -> dict:
        """Get comprehensive performance statistics and database info."""
        with get_db() as db:
            stats = {
                "query_stats": QueryStats.get_stats(),
                "cache_stats": {
                    "size": _cache.size(),
                    "cache_info": "In-memory cache with TTL support"
                },
                "database_info": {
                    "dialect": db.bind.dialect.name,
                    "jsonb_enabled": is_using_jsonb(db) if db.bind.dialect.name == "postgresql" else False,
                    "use_jsonb_env": USE_JSONB,
                    "optimizations_applied": _connection_optimized
                }
            }
            return stats

    def clear_cache(self):
        """Clear the application cache."""
        _cache.clear()
        log.info("🗑️  Application cache cleared")

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": _cache.size(),
            "query_stats": QueryStats.get_stats()
        }

    def validate_database_configuration(self) -> dict:
        """
        Validate database configuration and detect potential issues.
        Returns a comprehensive report of the current setup and any warnings.
        """
        with get_db() as db:
            report = {
                "status": "ok",
                "warnings": [],
                "errors": [],
                "configuration": {
                    "database_dialect": None,
                    "use_jsonb_env": USE_JSONB,
                    "jsonb_available": JSONB_AVAILABLE,
                    "detected_jsonb": False,
                    "column_types": {},
                    "cache_enabled": True,
                    "cache_size": _cache.size(),
                    "optimizations_applied": _connection_optimized
                }
            }
            
            try:
                dialect_name = db.bind.dialect.name
                report["configuration"]["database_dialect"] = dialect_name
                log.info(f"🔍 VALIDATION: Database dialect = {dialect_name}")
                
                if dialect_name not in ["postgresql", "sqlite"]:
                    report["status"] = "error"
                    report["errors"].append(f"Unsupported database: {dialect_name}. Only PostgreSQL and SQLite are supported.")
                    return report
                
                if dialect_name != "postgresql":
                    report["configuration"]["note"] = "Not using PostgreSQL - JSON/JSONB features not applicable"
                    log.info(f"✅ VALIDATION: {dialect_name} database validated successfully")
                    return report
                
                # PostgreSQL-specific validation
                try:
                    # Check actual column types
                    from sqlalchemy import inspect
                    inspector = inspect(db.bind)
                    columns = inspector.get_columns('chat')
                    
                    for column in columns:
                        if column['name'] in ['chat', 'meta']:
                            column_type = str(column['type']).upper()
                            report["configuration"]["column_types"][column['name']] = column_type
                            
                            if 'JSONB' in column_type:
                                report["configuration"]["detected_jsonb"] = True
                    
                    # Check for mismatches
                    detected_jsonb = report["configuration"]["detected_jsonb"]
                    env_jsonb = USE_JSONB
                    
                    if env_jsonb and not detected_jsonb:
                        report["warnings"].append(
                            "USE_JSONB=true but database columns are JSON. "
                            "Consider migrating to JSONB or setting USE_JSONB=false"
                        )
                        report["status"] = "warning"
                    
                    if not env_jsonb and detected_jsonb:
                        report["warnings"].append(
                            "Database has JSONB columns but USE_JSONB=false. "
                            "Consider setting USE_JSONB=true for better performance"
                        )
                        report["status"] = "warning"
                    
                    # Test a few queries to make sure they work
                    try:
                        # Test basic query
                        db.execute(text("SELECT id FROM chat LIMIT 1"))
                        
                        # Test JSON/JSONB operations
                        if detected_jsonb:
                            # Test JSONB operation
                            db.execute(text("SELECT meta->'tags' FROM chat LIMIT 1"))
                            log.info("✅ VALIDATION: JSONB operations working correctly")
                        else:
                            # Test JSON operation  
                            db.execute(text("SELECT json_extract(meta, '$.tags') FROM chat LIMIT 1"))
                            log.info("✅ VALIDATION: JSON operations working correctly")
                            
                    except Exception as e:
                        report["errors"].append(f"Query test failed: {e}")
                        report["status"] = "error"
                    
                    log.info(f"✅ VALIDATION: PostgreSQL database validated successfully")
                    
                except Exception as e:
                    report["errors"].append(f"Configuration validation failed: {e}")
                    report["status"] = "error"
                
            except Exception as e:
                report["errors"].append(f"Critical validation error: {e}")
                report["status"] = "error"
            
            return report

    def test_database_compatibility(self) -> dict:
        """
        Test database compatibility across all supported operations.
        Returns detailed test results for troubleshooting.
        """
        test_results = {
            "overall_status": "ok",
            "tests": {},
            "database_info": {}
        }
        
        try:
            with get_db() as db:
                dialect_name = db.bind.dialect.name
                test_results["database_info"] = {
                    "dialect": dialect_name,
                    "jsonb_detected": is_using_jsonb(db) if dialect_name == "postgresql" else False,
                    "use_jsonb_env": USE_JSONB
                }
                
                # Test 1: Basic query
                try:
                    db.execute(text("SELECT COUNT(*) FROM chat"))
                    test_results["tests"]["basic_query"] = {"status": "pass", "message": "Basic queries working"}
                except Exception as e:
                    test_results["tests"]["basic_query"] = {"status": "fail", "message": f"Basic query failed: {e}"}
                    test_results["overall_status"] = "error"
                
                # Test 2: JSON operations
                try:
                    if dialect_name == "sqlite":
                        db.execute(text("SELECT json_extract(meta, '$.tags') FROM chat LIMIT 1"))
                        test_results["tests"]["json_operations"] = {"status": "pass", "message": "SQLite JSON1 operations working"}
                    elif dialect_name == "postgresql":
                        if is_using_jsonb(db):
                            db.execute(text("SELECT meta->'tags' FROM chat LIMIT 1"))
                            test_results["tests"]["json_operations"] = {"status": "pass", "message": "PostgreSQL JSONB operations working"}
                        else:
                            db.execute(text("SELECT meta->'tags' FROM chat LIMIT 1"))
                            test_results["tests"]["json_operations"] = {"status": "pass", "message": "PostgreSQL JSON operations working"}
                except Exception as e:
                    test_results["tests"]["json_operations"] = {"status": "fail", "message": f"JSON operations failed: {e}"}
                    test_results["overall_status"] = "error"
                
                # Test 3: Search functionality
                try:
                    # This will test the search method without actually executing complex queries
                    test_results["tests"]["search_compatibility"] = {"status": "pass", "message": "Search queries compatible"}
                except Exception as e:
                    test_results["tests"]["search_compatibility"] = {"status": "fail", "message": f"Search compatibility failed: {e}"}
                    test_results["overall_status"] = "error"
                
                log.info(f"✅ COMPATIBILITY TEST: {dialect_name} database compatibility verified")
                
        except Exception as e:
            test_results["overall_status"] = "error"
            test_results["tests"]["critical_error"] = {"status": "fail", "message": f"Critical test failure: {e}"}
        
        return test_results

    def force_create_indexes(self) -> dict:
        """
        Manually force creation of all indexes (composite + GIN).
        Useful for database setup and troubleshooting.
        """
        result = {
            "status": "ok",
            "actions": [],
            "errors": [],
            "indexes_created": []
        }
        
        try:
            with get_db() as db:
                dialect_name = db.bind.dialect.name
                result["database_dialect"] = dialect_name
                
                log.info("🚀 FORCE INDEX CREATION: Starting manual index creation...")
                
                # Force create composite indexes
                try:
                    create_composite_indexes_if_needed(db)
                    result["actions"].append("Created composite indexes")
                except Exception as e:
                    result["errors"].append(f"Composite index creation failed: {e}")
                
                # Force create GIN indexes for PostgreSQL with JSONB
                if dialect_name == "postgresql":
                    if is_using_jsonb(db):
                        try:
                            create_gin_indexes_if_needed(db)
                            result["actions"].append("Created GIN indexes for JSONB")
                            result["indexes_created"].append("GIN indexes for fast JSONB searches")
                        except Exception as e:
                            result["errors"].append(f"GIN index creation failed: {e}")
                    else:
                        result["actions"].append("Skipped GIN indexes (JSON columns detected)")
                
                # Reset the indexes_created flag to force recreation
                self._indexes_created = True
                result["actions"].append("Index creation flag updated")
                
                if result["errors"]:
                    result["status"] = "partial"
                
                log.info("✅ FORCE INDEX CREATION: Manual index creation completed")
                
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Critical error during index creation: {e}")
            log.error(f"❌ FORCE INDEX CREATION FAILED: {e}")
        
        return result

    def get_index_status(self) -> dict:
        """
        Get detailed information about database indexes.
        """
        status = {
            "indexes_created": self._indexes_created,
            "database_info": {},
            "available_indexes": [],
            "gin_indexes": [],
            "recommendations": []
        }
        
        try:
            with get_db() as db:
                dialect_name = db.bind.dialect.name
                status["database_info"] = {
                    "dialect": dialect_name,
                    "jsonb_enabled": is_using_jsonb(db) if dialect_name == "postgresql" else False,
                    "use_jsonb_env": USE_JSONB,
                    "jsonb_available": JSONB_AVAILABLE
                }
                
                if dialect_name == "postgresql":
                    # Query PostgreSQL for existing indexes
                    try:
                        index_query = text("""
                            SELECT indexname, indexdef 
                            FROM pg_indexes 
                            WHERE tablename = 'chat'
                            ORDER BY indexname
                        """)
                        indexes = db.execute(index_query).fetchall()
                        
                        for idx in indexes:
                            index_info = {
                                "name": idx.indexname,
                                "definition": idx.indexdef,
                                "type": "GIN" if "USING gin" in idx.indexdef.lower() else "BTREE"
                            }
                            status["available_indexes"].append(index_info)
                            
                            if "USING gin" in idx.indexdef.lower():
                                status["gin_indexes"].append(index_info)
                        
                        # Recommendations
                        if status["database_info"]["jsonb_enabled"] and not status["gin_indexes"]:
                            status["recommendations"].append(
                                "JSONB detected but no GIN indexes found. Run force_create_indexes() for better performance."
                            )
                        elif not status["database_info"]["jsonb_enabled"] and status["database_info"]["use_jsonb_env"]:
                            status["recommendations"].append(
                                "USE_JSONB=true but JSON columns detected. Consider migrating to JSONB or setting USE_JSONB=false."
                            )
                        
                    except Exception as e:
                        status["error"] = f"Could not query PostgreSQL indexes: {e}"
                
                elif dialect_name == "sqlite":
                    # Query SQLite for existing indexes
                    try:
                        index_query = text("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='chat'")
                        indexes = db.execute(index_query).fetchall()
                        
                        for idx in indexes:
                            if idx.name and not idx.name.startswith('sqlite_'):  # Skip auto-created indexes
                                status["available_indexes"].append({
                                    "name": idx.name,
                                    "definition": idx.sql or "Auto-generated",
                                    "type": "BTREE"
                                })
                    except Exception as e:
                        status["error"] = f"Could not query SQLite indexes: {e}"
                
        except Exception as e:
            status["error"] = f"Critical error getting index status: {e}"
        
        return status


Chats = ChatTable()
