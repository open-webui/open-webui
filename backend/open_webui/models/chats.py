import logging
import json
import time
import uuid
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from open_webui.internal.db import Base, get_db
from open_webui.models.tags import TagModel, Tag, Tags
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists
from sqlalchemy.sql.elements import TextClause

# Import JSONB for PostgreSQL support
try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = None

####################
# Database Adapter
####################

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL_JSON = "postgresql_json"
    POSTGRESQL_JSONB = "postgresql_jsonb"
    UNSUPPORTED = "unsupported"

class DatabaseAdapter:
    """Centralized database-specific query generation with caching"""
    
    def __init__(self, db):
        self.db = db
        self.dialect = db.bind.dialect.name
        self._cache: Dict[str, DatabaseType] = {}
    
    def get_database_type(self, column_name: str = "meta") -> DatabaseType:
        """Determine database type with caching"""
        cache_key = f"{self.dialect}_{column_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if self.dialect == "sqlite":
            result = DatabaseType.SQLITE
        elif self.dialect == "postgresql":
            result = DatabaseType.POSTGRESQL_JSONB if self._is_jsonb_column(column_name) else DatabaseType.POSTGRESQL_JSON
        else:
            result = DatabaseType.UNSUPPORTED
        
        self._cache[cache_key] = result
        return result
    
    def _is_jsonb_column(self, column_name: str) -> bool:
        """Check if column is JSONB type"""
        if JSONB is None or self.dialect != "postgresql":
            return False
        
        try:
            result = self.db.execute(text("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'chat' AND column_name = :column_name
            """), {"column_name": column_name})
            
            row = result.fetchone()
            return row[0].lower() == 'jsonb' if row else False
        except Exception:
            return False
    
    def _get_function_template(self, db_type: DatabaseType, function_type: str) -> Optional[str]:
        """Get function template for specific database type and function"""
        templates = {
            DatabaseType.SQLITE: {
                "tag_exists": "EXISTS (SELECT 1 FROM json_each({column}, '$.tags') WHERE json_each.value = :tag_id)",
                "has_key": "json_extract({column}, '$.{path}') IS NOT NULL",
                "array_length": "json_array_length({column}, '$.{path}')",
                "array_elements": "json_each({column}, '$.{path}')",
                "content_search": """EXISTS (
                    SELECT 1 FROM json_each({column}, '$.messages') AS message 
                    WHERE LOWER(message.value->>'content') LIKE '%' || :search_text || '%'
                )"""
            },
            DatabaseType.POSTGRESQL_JSON: {
                "tag_exists": "EXISTS (SELECT 1 FROM json_array_elements_text({column}->'tags') elem WHERE elem = :tag_id)",
                "has_key": "{column} ? '{path}'",
                "array_length": "json_array_length({column}->'{path}')",
                "array_elements": "json_array_elements({column}->'{path}')",
                "content_search": """EXISTS (
                    SELECT 1 FROM json_array_elements({column}->'messages') AS message
                    WHERE LOWER(message->>'content') LIKE '%' || :search_text || '%'
                )"""
            },
            DatabaseType.POSTGRESQL_JSONB: {
                "tag_exists": "EXISTS (SELECT 1 FROM jsonb_array_elements_text({column}->'tags') elem WHERE elem = :tag_id)",
                "has_key": "{column} ? '{path}'",
                "array_length": "jsonb_array_length({column}->'{path}')",
                "array_elements": "jsonb_array_elements({column}->'{path}')",
                "content_search": """EXISTS (
                    SELECT 1 FROM jsonb_array_elements({column}->'messages') AS message
                    WHERE LOWER(message->>'content') LIKE '%' || :search_text || '%'
                )"""
            }
        }
        
        return templates.get(db_type, {}).get(function_type)
    
    def build_tag_filter(self, column_name: str, tag_ids: List[str], match_all: bool = True) -> Optional[Union[TextClause, and_, or_]]:
        """Build optimized tag filtering query"""
        if not tag_ids:
            return None
            
        db_type = self.get_database_type(column_name)
        template = self._get_function_template(db_type, "tag_exists")
        
        if not template:
            return None
        
        query_template = template.replace("{column}", f"Chat.{column_name}")
        
        if match_all:
            return and_(*[
                text(query_template).params(tag_id=tag_id)
                for tag_id in tag_ids
            ])
        else:
            conditions = []
            params = {}
            for idx, tag_id in enumerate(tag_ids):
                param_name = f"tag_id_{idx}"
                params[param_name] = tag_id
                condition_template = query_template.replace(":tag_id", f":{param_name}")
                conditions.append(text(condition_template))
            
            return or_(*conditions).params(**params)
    
    def build_search_filter(self, search_text: str) -> Optional[TextClause]:
        """Build content search query"""
        db_type = self.get_database_type("chat")
        template = self._get_function_template(db_type, "content_search")
        
        if not template:
            return None
        
        query = template.replace("{column}", "Chat.chat")
        return text(query).params(search_text=search_text)
    
    def build_untagged_filter(self, column_name: str = "meta") -> Optional[or_]:
        """Build filter for chats without tags"""
        db_type = self.get_database_type(column_name)
        
        has_key_template = self._get_function_template(db_type, "has_key")
        array_length_template = self._get_function_template(db_type, "array_length")
        
        if not has_key_template or not array_length_template:
            return None
        
        has_key = has_key_template.replace("{column}", f"Chat.{column_name}").replace("{path}", "tags")
        array_length = array_length_template.replace("{column}", f"Chat.{column_name}").replace("{path}", "tags")
        
        return or_(
            text(f"NOT ({has_key})"),
            text(f"{array_length} = 0")
        )

####################
# Utility Functions
####################

def normalize_tag_name(tag_name: str) -> str:
    """Normalize tag name for consistent storage and querying"""
    return tag_name.replace(" ", "_").lower()

def normalize_tag_names(tag_names: List[str]) -> List[str]:
    """Normalize multiple tag names"""
    return [normalize_tag_name(tag) for tag in tag_names]

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
    def __init__(self):
        pass
    
    def _get_adapter(self, db) -> DatabaseAdapter:
        """Get database adapter for the current session"""
        return DatabaseAdapter(db)
    
    # Legacy methods for backward compatibility
    def _is_jsonb_column(self, db, column_name: str) -> bool:
        """Legacy method - use adapter instead"""
        adapter = self._get_adapter(db)
        return adapter.get_database_type(column_name) == DatabaseType.POSTGRESQL_JSONB
    
    def _get_json_query_type(self, db, column_name: str = "meta") -> str:
        """Legacy method - use adapter instead"""
        adapter = self._get_adapter(db)
        db_type = adapter.get_database_type(column_name)
        return db_type.value

    def check_database_compatibility(self) -> dict:
        """Check database compatibility and available features"""
        try:
            with get_db() as db:
                adapter = self._get_adapter(db)
                dialect_name = db.bind.dialect.name
                
                meta_type = adapter.get_database_type("meta")
                chat_type = adapter.get_database_type("chat")
                
                compatibility = {
                    "database_type": dialect_name,
                    "json_support": meta_type != DatabaseType.UNSUPPORTED,
                    "jsonb_support": meta_type == DatabaseType.POSTGRESQL_JSONB or chat_type == DatabaseType.POSTGRESQL_JSONB,
                    "gin_indexes_support": dialect_name == "postgresql",
                    "tag_filtering_support": meta_type != DatabaseType.UNSUPPORTED,
                    "advanced_search_support": chat_type != DatabaseType.UNSUPPORTED,
                    "meta_column_type": meta_type.value,
                    "chat_column_type": chat_type.value,
                    "features": [],
                    "limitations": [],
                    "recommendations": []
                }
                
                # Add features based on database type
                if dialect_name == "sqlite":
                    compatibility["features"] = ["JSON1 extension", "Basic tag filtering", "Message search"]
                    compatibility["limitations"] = ["No GIN indexes", "Limited JSON optimization"]
                elif dialect_name == "postgresql":
                    compatibility["features"] = ["Full JSON/JSONB support", "GIN indexes", "Advanced filtering"]
                    if compatibility["jsonb_support"]:
                        compatibility["features"].append("JSONB binary format optimization")
                
                return compatibility
                
        except Exception as e:
            log.error(f"Error checking database compatibility: {e}")
            return {"error": str(e), "database_type": "unknown"}



    def create_gin_indexes(self) -> bool:
        """Create GIN indexes on JSONB columns for better query performance"""
        try:
            with get_db() as db:
                adapter = self._get_adapter(db)
                
                if db.bind.dialect.name != "postgresql":
                    return False

                meta_type = adapter.get_database_type("meta")
                chat_type = adapter.get_database_type("chat")
                
                has_jsonb_meta = meta_type == DatabaseType.POSTGRESQL_JSONB
                has_jsonb_chat = chat_type == DatabaseType.POSTGRESQL_JSONB

                if not (has_jsonb_meta or has_jsonb_chat):
                    return False

                # Create GIN indexes
                if has_jsonb_meta:
                    try:
                        db.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_chat_meta_gin 
                            ON chat USING GIN (meta)
                        """))
                        db.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_chat_meta_tags_gin 
                            ON chat USING GIN ((meta->'tags'))
                        """))
                        db.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_chat_has_tags 
                            ON chat USING BTREE ((meta ? 'tags' AND jsonb_array_length(meta->'tags') > 0))
                            WHERE meta ? 'tags'
                        """))
                    except Exception:
                        pass

                if has_jsonb_chat:
                    try:
                        db.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_chat_chat_gin 
                            ON chat USING GIN (chat)
                        """))
                        db.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_chat_messages_gin 
                            ON chat USING GIN ((chat->'messages'))
                        """))
                    except Exception:
                        pass

                db.commit()
                return True

        except Exception:
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
        """Drop all GIN indexes on the chat table"""
        try:
            with get_db() as db:
                if db.bind.dialect.name != "postgresql":
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

                for idx_name in indexes_to_drop:
                    try:
                        db.execute(text(f"DROP INDEX CONCURRENTLY IF EXISTS {idx_name}"))
                    except Exception:
                        pass

                db.commit()
                return True

        except Exception:
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
                .order_by(Chat.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
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
            normalize_tag_name(word.replace("tag:", ""))
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

            # Use adapter for cleaner query building
            adapter = self._get_adapter(db)
            
            # Add search filter if search text provided
            if search_text:
                search_filter = adapter.build_search_filter(search_text)
                if search_filter is not None:
                    query = query.filter(
                        Chat.title.ilike(f"%{search_text}%") | search_filter
                    )
                else:
                    # Fallback to title-only search for unsupported databases
                    query = query.filter(Chat.title.ilike(f"%{search_text}%"))
            
            # Add tag filters
            if "none" in tag_ids:
                untagged_filter = adapter.build_untagged_filter("meta")
                if untagged_filter is not None:
                    query = query.filter(untagged_filter)
            elif tag_ids:
                tag_filter = adapter.build_tag_filter("meta", tag_ids, match_all=True)
                if tag_filter is not None:
                    query = query.filter(tag_filter)

            # Perform pagination at the SQL level
            all_chats = query.offset(skip).limit(limit).all()

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
            adapter = self._get_adapter(db)
            query = db.query(Chat).filter_by(user_id=user_id)
            tag_id = normalize_tag_name(tag_name)

            # Use adapter to build tag filter
            tag_filter = adapter.build_tag_filter("meta", [tag_id], match_all=True)
            if tag_filter is not None:
                query = query.filter(tag_filter)
                all_chats = query.all()
                return [ChatModel.model_validate(chat) for chat in all_chats]
            else:
                return []

    def get_chats_by_multiple_tags(
        self, user_id: str, tag_names: List[str], match_all: bool = True, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        """Get chats that match multiple tags"""
        with get_db() as db:
            adapter = self._get_adapter(db)
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)
            
            if not tag_names:
                return []
            
            # Normalize tag names
            tag_ids = normalize_tag_names(tag_names)
            
            # Use adapter to build tag filter
            tag_filter = adapter.build_tag_filter("meta", tag_ids, match_all=match_all)
            if tag_filter is not None:
                query = query.filter(tag_filter)
                # Apply pagination and ordering
                query = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit)
                all_chats = query.all()
                return [ChatModel.model_validate(chat) for chat in all_chats]
            else:
                return []

    def get_chats_without_tags(self, user_id: str, skip: int = 0, limit: int = 50) -> list[ChatModel]:
        """Get chats that have no tags"""
        with get_db() as db:
            adapter = self._get_adapter(db)
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)
            
            # Use adapter to build untagged filter
            untagged_filter = adapter.build_untagged_filter("meta")
            if untagged_filter is not None:
                query = query.filter(untagged_filter)
                query = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit)
                all_chats = query.all()
                return [ChatModel.model_validate(chat) for chat in all_chats]
            else:
                return []

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
        with get_db() as db:
            adapter = self._get_adapter(db)
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)

            # Normalize the tag_name for consistency
            tag_id = normalize_tag_name(tag_name)

            # Use adapter to build tag filter
            tag_filter = adapter.build_tag_filter("meta", [tag_id], match_all=True)
            if tag_filter is not None:
                query = query.filter(tag_filter)
                return query.count()
            else:
                return 0

    def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> bool:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                tags = chat.meta.get("tags", [])
                tag_id = normalize_tag_name(tag_name)

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
