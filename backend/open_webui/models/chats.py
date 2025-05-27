import logging
import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.tags import TagModel, Tag, Tags
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

# Import JSONB for PostgreSQL support
try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = None

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
    chat = Column(JSON)  # For JSONB support, change to: Column(JSONB) if JSONB else Column(JSON)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    share_id = Column(Text, unique=True, nullable=True)
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False, nullable=True)

    meta = Column(JSON, server_default="{}")  # For JSONB support, change to: Column(JSONB, server_default="{}") if JSONB else Column(JSON, server_default="{}")
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
    def _is_jsonb_column(self, db, column_name: str) -> bool:
        """
        Helper method to detect if a column is using JSONB type.
        Returns True if the column is JSONB, False otherwise.
        """
        if JSONB is None:
            log.info(f"📦 JSONB not available - PostgreSQL dependencies not installed")
            return False
            
        if db.bind.dialect.name != "postgresql":
            log.info(f"📊 Non-PostgreSQL database - JSONB not applicable")
            return False
        
        try:
            # Get the table metadata
            table = Chat.__table__
            column = table.columns.get(column_name)
            if column is not None:
                is_jsonb = isinstance(column.type, type(JSONB()))
                column_type = type(column.type).__name__
                log.info(f"🔬 Column '{column_name}' type analysis: {column_type} -> JSONB: {is_jsonb}")
                return is_jsonb
            else:
                log.warning(f"⚠️ Column '{column_name}' not found in table metadata")
                return False
        except Exception as e:
            log.error(f"❌ Error checking JSONB column type for '{column_name}': {e}")
            return False

    def _get_json_query_type(self, db, column_name: str = "meta") -> str:
        """
        Determine the appropriate JSON query type based on database dialect and column type.
        Returns: 'sqlite', 'postgresql_json', 'postgresql_jsonb', or 'unsupported'
        """
        try:
            dialect_name = db.bind.dialect.name
            log.info(f"🔍 Database Detection - Dialect: {dialect_name}")
            
            if dialect_name == "sqlite":
                log.info(f"✅ SQLite detected - Using JSON1 extension for column '{column_name}'")
                return "sqlite"
            elif dialect_name == "postgresql":
                is_jsonb = self._is_jsonb_column(db, column_name)
                if is_jsonb:
                    log.info(f"✅ PostgreSQL JSONB detected - Using optimized JSONB queries for column '{column_name}'")
                    return "postgresql_jsonb"
                else:
                    log.info(f"✅ PostgreSQL JSON detected - Using standard JSON queries for column '{column_name}'")
                    return "postgresql_json"
            else:
                # Return 'unsupported' instead of raising exception
                log.warning(f"⚠️ Unsupported database dialect: {dialect_name}. JSON queries will be skipped.")
                return "unsupported"
        except Exception as e:
            log.error(f"❌ Error determining JSON query type: {e}")
            return "unsupported"

    def check_database_compatibility(self) -> dict:
        """
        Check database compatibility and available features.
        Returns a comprehensive report of what features are supported.
        """
        try:
            with get_db() as db:
                dialect_name = db.bind.dialect.name
                
                compatibility = {
                    "database_type": dialect_name,
                    "json_support": False,
                    "jsonb_support": False,
                    "gin_indexes_support": False,
                    "tag_filtering_support": False,
                    "advanced_search_support": False,
                    "features": [],
                    "limitations": [],
                    "recommendations": []
                }
                
                if dialect_name == "sqlite":
                    compatibility.update({
                        "json_support": True,
                        "tag_filtering_support": True,
                        "advanced_search_support": True,
                        "features": [
                            "JSON1 extension support",
                            "Basic tag filtering",
                            "Message content search",
                            "Cross-platform compatibility"
                        ],
                        "limitations": [
                            "No GIN indexes (PostgreSQL only)",
                            "Limited JSON query optimization",
                            "No JSONB support"
                        ],
                        "recommendations": [
                            "Consider PostgreSQL for high-volume applications",
                            "Ensure JSON1 extension is enabled"
                        ]
                    })
                    
                elif dialect_name == "postgresql":
                    has_jsonb_meta = self._is_jsonb_column(db, "meta")
                    has_jsonb_chat = self._is_jsonb_column(db, "chat")
                    
                    compatibility.update({
                        "json_support": True,
                        "jsonb_support": has_jsonb_meta or has_jsonb_chat,
                        "gin_indexes_support": True,
                        "tag_filtering_support": True,
                        "advanced_search_support": True,
                        "features": [
                            "Full JSON/JSONB support",
                            "GIN indexes for performance",
                            "Advanced tag filtering",
                            "Optimized message search",
                            "Concurrent index creation"
                        ],
                        "limitations": [],
                        "recommendations": []
                    })
                    
                    if has_jsonb_meta or has_jsonb_chat:
                        compatibility["features"].extend([
                            "JSONB binary format for speed",
                            "Advanced JSONB operators",
                            "Specialized tag indexes"
                        ])
                        compatibility["recommendations"].append(
                            "Create GIN indexes for optimal performance"
                        )
                    else:
                        compatibility["limitations"].append(
                            "Using JSON instead of JSONB (consider migration)"
                        )
                        compatibility["recommendations"].extend([
                            "Consider migrating to JSONB for better performance",
                            "Create functional indexes on JSON columns"
                        ])
                        
                else:
                    compatibility.update({
                        "limitations": [
                            f"Database type '{dialect_name}' not officially supported",
                            "No JSON query optimization",
                            "No tag filtering support",
                            "Limited search capabilities"
                        ],
                        "recommendations": [
                            "Consider migrating to PostgreSQL or SQLite",
                            "Basic CRUD operations should still work",
                            "Contact support for database-specific optimizations"
                        ]
                    })
                
                return compatibility
                 
        except Exception as e:
            log.error(f"Error checking database compatibility: {e}")
            return {
                "error": str(e),
                "database_type": "unknown",
                "json_support": False,
                "recommendations": ["Check database connection and configuration"]
            }

    def log_database_configuration(self) -> None:
        """
        Log a comprehensive summary of the current database configuration and capabilities.
        This helps with debugging and monitoring which query paths are being used.
        """
        try:
            with get_db() as db:
                dialect_name = db.bind.dialect.name
                log.info("=" * 60)
                log.info("🗄️ DATABASE CONFIGURATION SUMMARY")
                log.info("=" * 60)
                log.info(f"📊 Database Type: {dialect_name.upper()}")
                
                # Check column types
                has_jsonb_meta = self._is_jsonb_column(db, "meta")
                has_jsonb_chat = self._is_jsonb_column(db, "chat")
                
                log.info(f"🔬 Column Types:")
                log.info(f"   • meta column: {'JSONB' if has_jsonb_meta else 'JSON'}")
                log.info(f"   • chat column: {'JSONB' if has_jsonb_chat else 'JSON'}")
                
                # Determine query paths
                meta_query_type = self._get_json_query_type(db, "meta")
                chat_query_type = self._get_json_query_type(db, "chat")
                
                log.info(f"🚀 Query Paths:")
                log.info(f"   • Meta queries: {meta_query_type.upper()}")
                log.info(f"   • Chat queries: {chat_query_type.upper()}")
                
                # Check capabilities
                capabilities = []
                if dialect_name == "sqlite":
                    capabilities = ["JSON1 Extension", "Tag Filtering", "Message Search"]
                elif dialect_name == "postgresql":
                    capabilities = ["JSON/JSONB Support", "Tag Filtering", "Message Search", "GIN Indexes"]
                    if has_jsonb_meta or has_jsonb_chat:
                        capabilities.append("JSONB Optimization")
                else:
                    capabilities = ["Basic CRUD Operations"]
                
                log.info(f"✨ Available Features:")
                for capability in capabilities:
                    log.info(f"   ✅ {capability}")
                
                # Performance recommendations
                if dialect_name == "postgresql" and (has_jsonb_meta or has_jsonb_chat):
                    log.info(f"🚀 Performance: OPTIMIZED (JSONB + GIN indexes available)")
                elif dialect_name == "postgresql":
                    log.info(f"⚡ Performance: GOOD (JSON with functional indexes)")
                elif dialect_name == "sqlite":
                    log.info(f"🔧 Performance: STANDARD (JSON1 extension)")
                else:
                    log.info(f"⚠️ Performance: LIMITED (Basic operations only)")
                
                log.info("=" * 60)
                 
        except Exception as e:
            log.error(f"❌ Error logging database configuration: {e}")

    def create_gin_indexes(self) -> bool:
        """
        Create GIN indexes on JSONB columns for better query performance.
        Only creates indexes if columns are JSONB type and database is PostgreSQL.
        Returns True if indexes were created or already exist, False on error.
        """
        try:
            with get_db() as db:
                dialect_name = db.bind.dialect.name
                log.info(f"🏗️ GIN Index Creation - Database: {dialect_name}")
                
                if dialect_name != "postgresql":
                    log.info("ℹ️ GIN indexes are only supported on PostgreSQL")
                    return False

                # Check if we have JSONB columns
                log.info("🔍 Analyzing column types for GIN index optimization...")
                has_jsonb_meta = self._is_jsonb_column(db, "meta")
                has_jsonb_chat = self._is_jsonb_column(db, "chat")
                log.info(f"📊 Column analysis: meta={has_jsonb_meta}, chat={has_jsonb_chat}")

                if not (has_jsonb_meta or has_jsonb_chat):
                    log.info("ℹ️ No JSONB columns found, skipping GIN index creation")
                    return False

                indexes_created = []

                # Create GIN index on meta column if it's JSONB
                if has_jsonb_meta:
                    try:
                        db.execute(text("""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_meta_gin 
                            ON chat USING GIN (meta)
                        """))
                        indexes_created.append("idx_chat_meta_gin")
                    except Exception as e:
                        log.warning(f"Failed to create GIN index on meta column: {e}")

                # Create GIN index on chat column if it's JSONB
                if has_jsonb_chat:
                    try:
                        db.execute(text("""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_chat_gin 
                            ON chat USING GIN (chat)
                        """))
                        indexes_created.append("idx_chat_chat_gin")
                    except Exception as e:
                        log.warning(f"Failed to create GIN index on chat column: {e}")

                # Create specialized GIN index for tags if meta is JSONB
                if has_jsonb_meta:
                    try:
                        db.execute(text("""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_meta_tags_gin 
                            ON chat USING GIN ((meta->'tags'))
                        """))
                        indexes_created.append("idx_chat_meta_tags_gin")
                    except Exception as e:
                        log.warning(f"Failed to create GIN index on meta->tags: {e}")

                    # Create additional tag-specific indexes for optimal performance
                    try:
                        # Index for checking if tags array exists and is not empty
                        db.execute(text("""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_has_tags 
                            ON chat USING BTREE ((meta ? 'tags' AND jsonb_array_length(meta->'tags') > 0))
                            WHERE meta ? 'tags'
                        """))
                        indexes_created.append("idx_chat_has_tags")
                    except Exception as e:
                        log.warning(f"Failed to create has_tags index: {e}")

                    try:
                        # Index for tag array length (useful for filtering by number of tags)
                        db.execute(text("""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_tag_count 
                            ON chat USING BTREE ((jsonb_array_length(meta->'tags')))
                            WHERE meta ? 'tags'
                        """))
                        indexes_created.append("idx_chat_tag_count")
                    except Exception as e:
                        log.warning(f"Failed to create tag_count index: {e}")

                # Create tag indexes even for JSON columns (less optimal but still helpful)
                elif has_jsonb_meta == False and db.bind.dialect.name == "postgresql":
                    try:
                        # For JSON columns, create a functional index on tags
                        db.execute(text("""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_json_tags 
                            ON chat USING GIN ((meta->'tags'))
                            WHERE meta ? 'tags'
                        """))
                        indexes_created.append("idx_chat_json_tags")
                    except Exception as e:
                        log.warning(f"Failed to create JSON tags index: {e}")

                # Create specialized GIN index for messages if chat is JSONB
                if has_jsonb_chat:
                    try:
                        db.execute(text("""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_gin 
                            ON chat USING GIN ((chat->'history'->'messages'))
                        """))
                        indexes_created.append("idx_chat_messages_gin")
                    except Exception as e:
                        log.warning(f"Failed to create GIN index on chat->messages: {e}")

                db.commit()
                
                if indexes_created:
                    log.info(f"✅ Successfully created GIN indexes: {', '.join(indexes_created)}")
                else:
                    log.info("ℹ️ No GIN indexes were created")
                
                return True

        except Exception as e:
            log.error(f"Error creating GIN indexes: {e}")
            return False

    def check_gin_indexes(self) -> dict:
        """
        Check which GIN indexes exist on the chat table.
        Returns a dictionary with index names and their status.
        """
        try:
            with get_db() as db:
                if db.bind.dialect.name != "postgresql":
                    return {"error": "GIN indexes are only supported on PostgreSQL"}

                result = db.execute(text("""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename = 'chat' 
                    AND indexdef LIKE '%USING gin%'
                """))
                
                indexes = {}
                for row in result:
                    indexes[row[0]] = {
                        "exists": True,
                        "definition": row[1]
                    }
                
                # Check for expected indexes
                expected_indexes = [
                    "idx_chat_meta_gin",
                    "idx_chat_chat_gin", 
                    "idx_chat_meta_tags_gin",
                    "idx_chat_has_tags",
                    "idx_chat_tag_count",
                    "idx_chat_json_tags",
                    "idx_chat_messages_gin"
                ]
                
                for idx_name in expected_indexes:
                    if idx_name not in indexes:
                        indexes[idx_name] = {"exists": False}
                
                return indexes

        except Exception as e:
            log.error(f"Error checking GIN indexes: {e}")
            return {"error": str(e)}

    def drop_gin_indexes(self) -> bool:
        """
        Drop all GIN indexes on the chat table.
        Use with caution - this will impact query performance.
        """
        try:
            with get_db() as db:
                if db.bind.dialect.name != "postgresql":
                    log.info("GIN indexes are only supported on PostgreSQL")
                    return False

                indexes_to_drop = [
                    "idx_chat_meta_gin",
                    "idx_chat_chat_gin",
                    "idx_chat_meta_tags_gin",
                    "idx_chat_has_tags",
                    "idx_chat_tag_count", 
                    "idx_chat_json_tags",
                    "idx_chat_messages_gin"
                ]

                dropped_indexes = []
                for idx_name in indexes_to_drop:
                    try:
                        db.execute(text(f"DROP INDEX CONCURRENTLY IF EXISTS {idx_name}"))
                        dropped_indexes.append(idx_name)
                    except Exception as e:
                        log.warning(f"Failed to drop index {idx_name}: {e}")

                db.commit()
                
                if dropped_indexes:
                    log.info(f"Successfully dropped GIN indexes: {', '.join(dropped_indexes)}")
                else:
                    log.info("No GIN indexes were dropped")
                
                return True

        except Exception as e:
            log.error(f"Error dropping GIN indexes: {e}")
            return False

    def create_tag_indexes(self) -> bool:
        """
        Create specialized indexes optimized specifically for tag operations.
        This includes both GIN and BTREE indexes for different tag query patterns.
        """
        try:
            with get_db() as db:
                if db.bind.dialect.name != "postgresql":
                    log.info("Tag indexes are only supported on PostgreSQL")
                    return False

                has_jsonb_meta = self._is_jsonb_column(db, "meta")
                indexes_created = []

                if has_jsonb_meta:
                    # JSONB-specific tag indexes
                    tag_indexes = [
                        {
                            "name": "idx_chat_meta_tags_gin",
                            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_meta_tags_gin ON chat USING GIN ((meta->'tags'))",
                            "purpose": "Fast tag containment queries (@>, ?, etc.)"
                        },
                        {
                            "name": "idx_chat_has_tags",
                            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_has_tags ON chat USING BTREE ((meta ? 'tags' AND jsonb_array_length(meta->'tags') > 0)) WHERE meta ? 'tags'",
                            "purpose": "Fast filtering for chats with/without tags"
                        },
                        {
                            "name": "idx_chat_tag_count",
                            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_tag_count ON chat USING BTREE ((jsonb_array_length(meta->'tags'))) WHERE meta ? 'tags'",
                            "purpose": "Fast filtering by number of tags"
                        },
                        {
                            "name": "idx_chat_specific_tags",
                            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_specific_tags ON chat USING GIN ((meta->'tags')) WHERE jsonb_array_length(meta->'tags') > 0",
                            "purpose": "Optimized for chats that actually have tags"
                        }
                    ]
                else:
                    # JSON-specific tag indexes (less optimal but still helpful)
                    tag_indexes = [
                        {
                            "name": "idx_chat_json_tags",
                            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_json_tags ON chat USING GIN ((meta->'tags')) WHERE meta ? 'tags'",
                            "purpose": "Tag queries for JSON columns"
                        }
                    ]

                for index_info in tag_indexes:
                    try:
                        db.execute(text(index_info["sql"]))
                        indexes_created.append(f"{index_info['name']} ({index_info['purpose']})")
                        log.info(f"Created tag index: {index_info['name']}")
                    except Exception as e:
                        log.warning(f"Failed to create {index_info['name']}: {e}")

                db.commit()
                
                if indexes_created:
                    log.info(f"Successfully created tag indexes: {len(indexes_created)} indexes")
                    for idx in indexes_created:
                        log.info(f"  • {idx}")
                else:
                    log.info("No tag indexes were created")
                
                return True

        except Exception as e:
            log.error(f"Error creating tag indexes: {e}")
            return False

    def optimize_tag_queries(self) -> dict:
        """
        Analyze and provide recommendations for tag query optimization.
        Returns statistics and suggestions for improving tag query performance.
        """
        try:
            with get_db() as db:
                if db.bind.dialect.name != "postgresql":
                    return {"error": "Tag optimization is only supported on PostgreSQL"}

                stats = {}
                
                # Get basic tag statistics
                result = db.execute(text("""
                    SELECT 
                        COUNT(*) as total_chats,
                        COUNT(*) FILTER (WHERE meta ? 'tags') as chats_with_tags,
                        COUNT(*) FILTER (WHERE meta ? 'tags' AND jsonb_array_length(meta->'tags') > 0) as chats_with_actual_tags,
                        AVG(CASE WHEN meta ? 'tags' THEN jsonb_array_length(meta->'tags') ELSE 0 END) as avg_tags_per_chat
                    FROM chat
                """))
                
                row = result.fetchone()
                if row:
                    stats.update({
                        "total_chats": row[0],
                        "chats_with_tags": row[1], 
                        "chats_with_actual_tags": row[2],
                        "avg_tags_per_chat": float(row[3]) if row[3] else 0
                    })

                # Get most common tags
                result = db.execute(text("""
                    SELECT tag_value, COUNT(*) as usage_count
                    FROM chat, jsonb_array_elements_text(meta->'tags') as tag_value
                    WHERE meta ? 'tags'
                    GROUP BY tag_value
                    ORDER BY usage_count DESC
                    LIMIT 10
                """))
                
                stats["top_tags"] = [{"tag": row[0], "count": row[1]} for row in result]

                # Check index usage
                indexes = self.check_gin_indexes()
                tag_indexes = {k: v for k, v in indexes.items() if "tag" in k.lower()}
                stats["tag_indexes"] = tag_indexes

                # Provide recommendations
                recommendations = []
                
                if stats["chats_with_actual_tags"] > 1000:
                    recommendations.append("Consider creating tag-specific indexes for better performance")
                
                if stats["avg_tags_per_chat"] > 5:
                    recommendations.append("High tag usage detected - GIN indexes will provide significant benefits")
                
                tag_coverage = stats["chats_with_actual_tags"] / stats["total_chats"] if stats["total_chats"] > 0 else 0
                if tag_coverage < 0.1:
                    recommendations.append("Low tag usage - consider partial indexes with WHERE clauses")
                
                stats["recommendations"] = recommendations
                stats["tag_coverage_percentage"] = round(tag_coverage * 100, 2)

                return stats

        except Exception as e:
            log.error(f"Error analyzing tag queries: {e}")
            return {"error": str(e)}

    def insert_new_chat(self, user_id: str, form_data: ChatForm) -> Optional[ChatModel]:
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
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            result = Chat(**chat.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
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
        limit: int = 60,
    ) -> list[ChatModel]:
        """
        Filters chats based on a search query using Python, allowing pagination using skip and limit.
        """
        search_text = search_text.lower().strip()

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

        search_text_words = [
            word for word in search_text_words if not word.startswith("tag:")
        ]

        search_text = " ".join(search_text_words)

        with get_db() as db:
            query = db.query(Chat).filter(Chat.user_id == user_id)

            if not include_archived:
                query = query.filter(Chat.archived == False)

            query = query.order_by(Chat.updated_at.desc())

            # Determine the JSON query type based on database dialect and column types
            json_query_type = self._get_json_query_type(db, "meta")
            log.info(f"🚀 Search Query Path: {json_query_type.upper()}")
            
            # Handle unsupported databases gracefully
            if json_query_type == "unsupported":
                log.warning("⚠️ Skipping JSON-based tag filtering due to unsupported database")
                # Continue with basic query without JSON filtering
            elif json_query_type == "sqlite":
                # SQLite case: using JSON1 extension for JSON searching
                log.info("🔧 Executing SQLite JSON1 queries for search and tag filtering")
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

            elif json_query_type == "postgresql_json":
                # PostgreSQL with JSON type: using standard JSON functions
                log.info("🔧 Executing PostgreSQL JSON queries for search and tag filtering")
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

            elif json_query_type == "postgresql_jsonb":
                # PostgreSQL with JSONB type: using JSONB operators for better performance
                log.info("🚀 Executing PostgreSQL JSONB optimized queries for search and tag filtering")
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
                                WHERE LOWER(message->>'content') ILIKE '%' || :search_text || '%'
                            )
                            """
                        )
                    ).params(search_text=search_text)
                )

                # Check if there are any tags to filter, it should have all the tags
                if "none" in tag_ids:
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
                # For unsupported databases, log warning but don't crash
                if json_query_type == "unsupported":
                    log.warning("⚠️ JSON-based search not available for this database type")
                else:
                    log.error(f"❌ Unexpected JSON query type: {json_query_type}")

            # Perform pagination at the SQL level
            all_chats = query.offset(skip).limit(limit).all()

            log.info(f"The number of chats: {len(all_chats)}")

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

    def get_chat_list_by_user_id_and_tag_name(
        self, user_id: str, tag_name: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            tag_id = tag_name.replace(" ", "_").lower()

            json_query_type = self._get_json_query_type(db, "meta")
            log.info(f"🏷️ Tag Filtering Path: {json_query_type.upper()} for tag '{tag_name}'")
            
            if json_query_type == "sqlite":
                log.info("🔧 Using SQLite JSON1 for tag filtering")
                # SQLite JSON1 querying for tags within the meta JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif json_query_type == "postgresql_json":
                # PostgreSQL JSON query for tags within the meta JSON field
                log.info("🔧 Using PostgreSQL JSON functions for tag filtering")
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif json_query_type == "postgresql_jsonb":
                # PostgreSQL JSONB query for tags within the meta JSONB field
                log.info("🚀 Using PostgreSQL JSONB optimized functions for tag filtering")
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM jsonb_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            else:
                # For unsupported databases, log warning but don't crash
                if json_query_type == "unsupported":
                    log.warning("⚠️ Tag filtering not available for this database type")
                else:
                    log.error(f"❌ Unexpected JSON query type: {json_query_type}")

            all_chats = query.all()
            log.debug(f"all_chats: {all_chats}")
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_multiple_tags(
        self, user_id: str, tag_names: list[str], match_all: bool = True, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        """
        Get chats that match multiple tags. Optimized to use tag indexes when available.
        
        Args:
            user_id: User ID to filter by
            tag_names: List of tag names to search for
            match_all: If True, chat must have ALL tags. If False, chat must have ANY tag.
            skip: Number of results to skip (pagination)
            limit: Maximum number of results to return
        """
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)
            
            if not tag_names:
                return []
            
            # Normalize tag names
            tag_ids = [tag_name.replace(" ", "_").lower() for tag_name in tag_names]
            json_query_type = self._get_json_query_type(db, "meta")
            log.info(f"🏷️ Multi-Tag Query Path: {json_query_type.upper()} for tags {tag_names} (match_all={match_all})")
            
            if json_query_type == "postgresql_jsonb":
                log.info("🚀 Using PostgreSQL JSONB operators for multi-tag filtering")
                # JSONB optimized queries - these will use our GIN indexes
                if match_all:
                    # Chat must contain ALL specified tags
                    for tag_id in tag_ids:
                        query = query.filter(
                            text("meta->'tags' ? :tag_id").params(tag_id=tag_id)
                        )
                else:
                    # Chat must contain ANY of the specified tags
                    tag_conditions = [
                        text("meta->'tags' ? :tag_id").params(tag_id=f"tag_{idx}")
                        for idx, tag_id in enumerate(tag_ids)
                    ]
                    # Build parameters dict
                    params = {f"tag_{idx}": tag_id for idx, tag_id in enumerate(tag_ids)}
                    query = query.filter(or_(*[
                        text(f"meta->'tags' ? :tag_{idx}")
                        for idx in range(len(tag_ids))
                    ])).params(**params)
                    
            elif json_query_type == "postgresql_json":
                # JSON queries (less optimal but still functional)
                log.info("🔧 Using PostgreSQL JSON functions for multi-tag filtering")
                if match_all:
                    for tag_id in tag_ids:
                        query = query.filter(
                            text(
                                "EXISTS (SELECT 1 FROM json_array_elements_text(meta->'tags') elem WHERE elem = :tag_id)"
                            ).params(tag_id=tag_id)
                        )
                else:
                    tag_conditions = [
                        text(
                            f"EXISTS (SELECT 1 FROM json_array_elements_text(meta->'tags') elem WHERE elem = :tag_id_{idx})"
                        ).params(**{f"tag_id_{idx}": tag_id})
                        for idx, tag_id in enumerate(tag_ids)
                    ]
                    query = query.filter(or_(*tag_conditions))
                    
            elif json_query_type == "sqlite":
                # SQLite queries
                log.info("🔧 Using SQLite JSON1 for multi-tag filtering")
                if match_all:
                    for tag_id in tag_ids:
                        query = query.filter(
                            text(
                                "EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                            ).params(tag_id=tag_id)
                        )
                else:
                    tag_conditions = [
                        text(
                            f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id_{idx})"
                        ).params(**{f"tag_id_{idx}": tag_id})
                        for idx, tag_id in enumerate(tag_ids)
                    ]
                    query = query.filter(or_(*tag_conditions))
            else:
                # For unsupported databases, log warning and return empty list
                if json_query_type == "unsupported":
                    log.warning("⚠️ Multi-tag filtering not available for this database type")
                    return []
                else:
                    log.error(f"❌ Unexpected JSON query type: {json_query_type}")
                    return []
            
            # Apply pagination and ordering
            query = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit)
            
            all_chats = query.all()
            log.info(f"Found {len(all_chats)} chats matching tags: {tag_names} (match_all={match_all})")
            
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_without_tags(self, user_id: str, skip: int = 0, limit: int = 50) -> list[ChatModel]:
        """
        Get chats that have no tags. Optimized to use tag indexes when available.
        """
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)
            json_query_type = self._get_json_query_type(db, "meta")
            log.info(f"🏷️ Untagged Chats Query Path: {json_query_type.upper()}")
            
            if json_query_type == "postgresql_jsonb":
                log.info("🚀 Using PostgreSQL JSONB operators for untagged chat filtering")
                # JSONB optimized: use the has_tags index
                query = query.filter(
                    or_(
                        text("NOT (meta ? 'tags')"),  # No tags key at all
                        text("jsonb_array_length(meta->'tags') = 0")  # Empty tags array
                    )
                )
            elif json_query_type == "postgresql_json":
                # JSON version
                log.info("🔧 Using PostgreSQL JSON functions for untagged chat filtering")
                query = query.filter(
                    or_(
                        text("NOT (meta ? 'tags')"),
                        text("json_array_length(meta->'tags') = 0")
                    )
                )
            elif json_query_type == "sqlite":
                # SQLite version
                log.info("🔧 Using SQLite JSON1 for untagged chat filtering")
                query = query.filter(
                    or_(
                        text("NOT EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags'))"),
                        text("json_array_length(Chat.meta, '$.tags') = 0")
                    )
                )
            else:
                # For unsupported databases, log warning and return empty list
                if json_query_type == "unsupported":
                    log.warning("⚠️ Tag filtering not available for this database type")
                    return []
                else:
                    log.error(f"❌ Unexpected JSON query type: {json_query_type}")
                    return []
            
            query = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit)
            all_chats = query.all()
            
            log.info(f"Found {len(all_chats)} chats without tags")
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

    def count_chats_by_tag_name_and_user_id(self, tag_name: str, user_id: str) -> int:
        with get_db() as db:  # Assuming `get_db()` returns a session object
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)

            # Normalize the tag_name for consistency
            tag_id = tag_name.replace(" ", "_").lower()

            json_query_type = self._get_json_query_type(db, "meta")
            log.info(f"🔢 Tag Count Query Path: {json_query_type.upper()} for tag '{tag_name}'")
            
            if json_query_type == "sqlite":
                log.info("🔧 Using SQLite JSON1 for tag counting")
                # SQLite JSON1 support for querying the tags inside the `meta` JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            elif json_query_type == "postgresql_json":
                # PostgreSQL JSON support for querying the tags inside the `meta` JSON field
                log.info("🔧 Using PostgreSQL JSON functions for tag counting")
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            elif json_query_type == "postgresql_jsonb":
                # PostgreSQL JSONB support for querying the tags inside the `meta` JSONB field
                log.info("🚀 Using PostgreSQL JSONB optimized functions for tag counting")
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM jsonb_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            else:
                # For unsupported databases, log warning but don't crash
                if json_query_type == "unsupported":
                    log.warning("⚠️ Tag counting not available for this database type")
                    return 0  # Return 0 for unsupported databases
                else:
                    log.error(f"❌ Unexpected JSON query type: {json_query_type}")
                    return 0

            # Get the count of matching records
            count = query.count()

            # Debugging output for inspection
            log.info(f"Count of chats for tag '{tag_name}': {count}")

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


Chats = ChatTable()
