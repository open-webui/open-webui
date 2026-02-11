import json
import time
import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db_context

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Text,
    JSON,
    Index,
)

####################
# Helpers
####################


def _normalize_timestamp(timestamp: int) -> float:
    """Normalize and validate timestamp. Returns current time if invalid."""
    now = time.time()

    # Convert milliseconds to seconds if needed
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000

    # Validate: must be after 2020 and not in the future (with 1 day tolerance)
    min_valid = 1577836800  # 2020-01-01 00:00:00 UTC
    max_valid = now + 86400  # 1 day in the future (clock skew tolerance)

    if timestamp < min_valid or timestamp > max_valid:
        return now

    return timestamp


####################
# ChatMessage DB Schema
####################


class ChatMessage(Base):
    __tablename__ = "chat_message"

    # Identity
    id = Column(Text, primary_key=True)
    chat_id = Column(
        Text, ForeignKey("chat.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Text, index=True)

    # Structure
    role = Column(Text, nullable=False)  # user, assistant, system
    parent_id = Column(Text, nullable=True)

    # Content
    content = Column(JSON, nullable=True)  # Can be str or list of blocks
    output = Column(JSON, nullable=True)

    # Model (for assistant messages)
    model_id = Column(Text, nullable=True, index=True)

    # Attachments
    files = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    embeds = Column(JSON, nullable=True)

    # Status
    done = Column(Boolean, default=True)
    status_history = Column(JSON, nullable=True)
    error = Column(JSON, nullable=True)

    # Usage (tokens, timing, etc.)
    usage = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)

    __table_args__ = (
        Index("chat_message_chat_parent_idx", "chat_id", "parent_id"),
        Index("chat_message_model_created_idx", "model_id", "created_at"),
        Index("chat_message_user_created_idx", "user_id", "created_at"),
    )


####################
# Pydantic Models
####################


class ChatMessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    user_id: str
    role: str
    parent_id: Optional[str] = None
    content: Optional[Any] = None  # str or list of blocks
    output: Optional[list] = None
    model_id: Optional[str] = None
    files: Optional[list] = None
    sources: Optional[list] = None
    embeds: Optional[list] = None
    done: bool = True
    status_history: Optional[list] = None
    error: Optional[dict | str] = None
    usage: Optional[dict] = None
    created_at: int
    updated_at: int


####################
# Table Operations
####################


class ChatMessageTable:
    def upsert_message(
        self,
        message_id: str,
        chat_id: str,
        user_id: str,
        data: dict,
        db: Optional[Session] = None,
    ) -> Optional[ChatMessageModel]:
        """Insert or update a chat message."""
        with get_db_context(db) as db:
            now = int(time.time())
            timestamp = data.get("timestamp", now)

            # Use composite ID: {chat_id}-{message_id}
            composite_id = f"{chat_id}-{message_id}"

            existing = db.get(ChatMessage, composite_id)
            if existing:
                # Update existing
                if "role" in data:
                    existing.role = data["role"]
                if "parent_id" in data:
                    existing.parent_id = data.get("parent_id") or data.get("parentId")
                if "content" in data:
                    existing.content = data.get("content")
                if "output" in data:
                    existing.output = data.get("output")
                if "model_id" in data or "model" in data:
                    existing.model_id = data.get("model_id") or data.get("model")
                if "files" in data:
                    existing.files = data.get("files")
                if "sources" in data:
                    existing.sources = data.get("sources")
                if "embeds" in data:
                    existing.embeds = data.get("embeds")
                if "done" in data:
                    existing.done = data.get("done", True)
                if "status_history" in data or "statusHistory" in data:
                    existing.status_history = data.get("status_history") or data.get(
                        "statusHistory"
                    )
                if "error" in data:
                    existing.error = data.get("error")
                # Extract usage - check direct field first, then info.usage
                usage = data.get("usage")
                if not usage:
                    info = data.get("info", {})
                    usage = info.get("usage") if info else None
                if usage:
                    existing.usage = usage
                existing.updated_at = now
                db.commit()
                db.refresh(existing)
                return ChatMessageModel.model_validate(existing)
            else:
                # Insert new
                # Extract usage - check direct field first, then info.usage
                usage = data.get("usage")
                if not usage:
                    info = data.get("info", {})
                    usage = info.get("usage") if info else None
                message = ChatMessage(
                    id=composite_id,
                    chat_id=chat_id,
                    user_id=user_id,
                    role=data.get("role", "user"),
                    parent_id=data.get("parent_id") or data.get("parentId"),
                    content=data.get("content"),
                    output=data.get("output"),
                    model_id=data.get("model_id") or data.get("model"),
                    files=data.get("files"),
                    sources=data.get("sources"),
                    embeds=data.get("embeds"),
                    done=data.get("done", True),
                    status_history=data.get("status_history")
                    or data.get("statusHistory"),
                    error=data.get("error"),
                    usage=usage,
                    created_at=timestamp,
                    updated_at=now,
                )
                db.add(message)
                db.commit()
                db.refresh(message)
                return ChatMessageModel.model_validate(message)

    def get_message_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatMessageModel]:
        with get_db_context(db) as db:
            message = db.get(ChatMessage, id)
            return ChatMessageModel.model_validate(message) if message else None

    def get_messages_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> list[ChatMessageModel]:
        with get_db_context(db) as db:
            messages = (
                db.query(ChatMessage)
                .filter_by(chat_id=chat_id)
                .order_by(ChatMessage.created_at.asc())
                .all()
            )
            return [ChatMessageModel.model_validate(message) for message in messages]

    def get_messages_by_user_id(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ChatMessageModel]:
        with get_db_context(db) as db:
            messages = (
                db.query(ChatMessage)
                .filter_by(user_id=user_id)
                .order_by(ChatMessage.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [ChatMessageModel.model_validate(message) for message in messages]

    def get_messages_by_model_id(
        self,
        model_id: str,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> list[ChatMessageModel]:
        with get_db_context(db) as db:
            query = db.query(ChatMessage).filter_by(model_id=model_id)
            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)
            messages = (
                query.order_by(ChatMessage.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [ChatMessageModel.model_validate(message) for message in messages]

    def get_chat_ids_by_model_id(
        self,
        model_id: str,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[str]:
        """Get distinct chat_ids that used a specific model."""
        from sqlalchemy import distinct

        with get_db_context(db) as db:
            query = db.query(distinct(ChatMessage.chat_id)).filter(
                ChatMessage.model_id == model_id
            )
            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)

            # Order by most recent message in each chat
            chat_ids = (
                query.order_by(ChatMessage.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [chat_id for (chat_id,) in chat_ids]

    def delete_messages_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            db.query(ChatMessage).filter_by(chat_id=chat_id).delete()
            db.commit()
            return True

    # Analytics methods
    def get_message_count_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict[str, int]:
        with get_db_context(db) as db:
            from sqlalchemy import func
            from open_webui.models.groups import GroupMember

            query = db.query(
                ChatMessage.model_id, func.count(ChatMessage.id).label("count")
            ).filter(
                ChatMessage.role == "assistant",
                ChatMessage.model_id.isnot(None),
                ~ChatMessage.user_id.like("shared-%"),
            )

            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = (
                    db.query(GroupMember.user_id)
                    .filter(GroupMember.group_id == group_id)
                    .subquery()
                )
                query = query.filter(ChatMessage.user_id.in_(group_users))

            results = query.group_by(ChatMessage.model_id).all()
            return {row.model_id: row.count for row in results}

    def get_token_usage_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict[str, dict]:
        """Aggregate token usage by model using database-level aggregation."""
        with get_db_context(db) as db:
            from sqlalchemy import func, cast, Integer
            from open_webui.models.groups import GroupMember

            dialect = db.bind.dialect.name

            if dialect == "sqlite":
                input_tokens = cast(
                    func.json_extract(ChatMessage.usage, "$.input_tokens"), Integer
                )
                output_tokens = cast(
                    func.json_extract(ChatMessage.usage, "$.output_tokens"), Integer
                )
            elif dialect == "postgresql":
                # Use json_extract_path_text for PostgreSQL JSON columns
                input_tokens = cast(
                    func.json_extract_path_text(ChatMessage.usage, "input_tokens"),
                    Integer,
                )
                output_tokens = cast(
                    func.json_extract_path_text(ChatMessage.usage, "output_tokens"),
                    Integer,
                )
            else:
                raise NotImplementedError(f"Unsupported dialect: {dialect}")

            query = db.query(
                ChatMessage.model_id,
                func.coalesce(func.sum(input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(output_tokens), 0).label("output_tokens"),
                func.count(ChatMessage.id).label("message_count"),
            ).filter(
                ChatMessage.role == "assistant",
                ChatMessage.model_id.isnot(None),
                ChatMessage.usage.isnot(None),
                ~ChatMessage.user_id.like("shared-%"),
            )

            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = (
                    db.query(GroupMember.user_id)
                    .filter(GroupMember.group_id == group_id)
                    .subquery()
                )
                query = query.filter(ChatMessage.user_id.in_(group_users))

            results = query.group_by(ChatMessage.model_id).all()

            return {
                row.model_id: {
                    "input_tokens": row.input_tokens,
                    "output_tokens": row.output_tokens,
                    "total_tokens": row.input_tokens + row.output_tokens,
                    "message_count": row.message_count,
                }
                for row in results
            }

    def get_token_usage_by_user(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> dict[str, dict]:
        """Aggregate token usage by user using database-level aggregation."""
        with get_db_context(db) as db:
            from sqlalchemy import func, cast, Integer

            dialect = db.bind.dialect.name

            if dialect == "sqlite":
                input_tokens = cast(
                    func.json_extract(ChatMessage.usage, "$.input_tokens"), Integer
                )
                output_tokens = cast(
                    func.json_extract(ChatMessage.usage, "$.output_tokens"), Integer
                )
            elif dialect == "postgresql":
                # Use json_extract_path_text for PostgreSQL JSON columns
                input_tokens = cast(
                    func.json_extract_path_text(ChatMessage.usage, "input_tokens"),
                    Integer,
                )
                output_tokens = cast(
                    func.json_extract_path_text(ChatMessage.usage, "output_tokens"),
                    Integer,
                )
            else:
                raise NotImplementedError(f"Unsupported dialect: {dialect}")

            query = db.query(
                ChatMessage.user_id,
                func.coalesce(func.sum(input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(output_tokens), 0).label("output_tokens"),
                func.count(ChatMessage.id).label("message_count"),
            ).filter(
                ChatMessage.role == "assistant",
                ChatMessage.user_id.isnot(None),
                ChatMessage.usage.isnot(None),
                ~ChatMessage.user_id.like("shared-%"),
            )

            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)

            results = query.group_by(ChatMessage.user_id).all()

            return {
                row.user_id: {
                    "input_tokens": row.input_tokens,
                    "output_tokens": row.output_tokens,
                    "total_tokens": row.input_tokens + row.output_tokens,
                    "message_count": row.message_count,
                }
                for row in results
            }

    def get_message_count_by_user(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict[str, int]:
        with get_db_context(db) as db:
            from sqlalchemy import func
            from open_webui.models.groups import GroupMember

            query = db.query(
                ChatMessage.user_id, func.count(ChatMessage.id).label("count")
            ).filter(~ChatMessage.user_id.like("shared-%"))

            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = (
                    db.query(GroupMember.user_id)
                    .filter(GroupMember.group_id == group_id)
                    .subquery()
                )
                query = query.filter(ChatMessage.user_id.in_(group_users))

            results = query.group_by(ChatMessage.user_id).all()
            return {row.user_id: row.count for row in results}

    def get_message_count_by_chat(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict[str, int]:
        with get_db_context(db) as db:
            from sqlalchemy import func
            from open_webui.models.groups import GroupMember

            query = db.query(
                ChatMessage.chat_id, func.count(ChatMessage.id).label("count")
            ).filter(~ChatMessage.user_id.like("shared-%"))

            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = (
                    db.query(GroupMember.user_id)
                    .filter(GroupMember.group_id == group_id)
                    .subquery()
                )
                query = query.filter(ChatMessage.user_id.in_(group_users))

            results = query.group_by(ChatMessage.chat_id).all()
            return {row.chat_id: row.count for row in results}

    def get_daily_message_counts_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict[str, dict[str, int]]:
        """Get message counts grouped by day and model."""
        with get_db_context(db) as db:
            from datetime import datetime, timedelta
            from open_webui.models.groups import GroupMember

            query = db.query(ChatMessage.created_at, ChatMessage.model_id).filter(
                ChatMessage.role == "assistant",
                ChatMessage.model_id.isnot(None),
                ~ChatMessage.user_id.like("shared-%"),
            )

            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)
            if group_id:
                group_users = (
                    db.query(GroupMember.user_id)
                    .filter(GroupMember.group_id == group_id)
                    .subquery()
                )
                query = query.filter(ChatMessage.user_id.in_(group_users))

            results = query.all()

            # Group by date -> model -> count
            daily_counts: dict[str, dict[str, int]] = {}
            for timestamp, model_id in results:
                date_str = datetime.fromtimestamp(
                    _normalize_timestamp(timestamp)
                ).strftime("%Y-%m-%d")
                if date_str not in daily_counts:
                    daily_counts[date_str] = {}
                daily_counts[date_str][model_id] = (
                    daily_counts[date_str].get(model_id, 0) + 1
                )

            # Fill in missing days
            if start_date and end_date:
                current = datetime.fromtimestamp(_normalize_timestamp(start_date))
                end_dt = datetime.fromtimestamp(_normalize_timestamp(end_date))
                while current <= end_dt:
                    date_str = current.strftime("%Y-%m-%d")
                    if date_str not in daily_counts:
                        daily_counts[date_str] = {}
                    current += timedelta(days=1)

            return daily_counts

    def get_hourly_message_counts_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> dict[str, dict[str, int]]:
        """Get message counts grouped by hour and model."""
        with get_db_context(db) as db:
            from datetime import datetime, timedelta

            query = db.query(ChatMessage.created_at, ChatMessage.model_id).filter(
                ChatMessage.role == "assistant",
                ChatMessage.model_id.isnot(None),
                ~ChatMessage.user_id.like("shared-%"),
            )

            if start_date:
                query = query.filter(ChatMessage.created_at >= start_date)
            if end_date:
                query = query.filter(ChatMessage.created_at <= end_date)

            results = query.all()

            # Group by hour -> model -> count
            hourly_counts: dict[str, dict[str, int]] = {}
            for timestamp, model_id in results:
                hour_str = datetime.fromtimestamp(
                    _normalize_timestamp(timestamp)
                ).strftime("%Y-%m-%d %H:00")
                if hour_str not in hourly_counts:
                    hourly_counts[hour_str] = {}
                hourly_counts[hour_str][model_id] = (
                    hourly_counts[hour_str].get(model_id, 0) + 1
                )

            # Fill in missing hours
            if start_date and end_date:
                current = datetime.fromtimestamp(
                    _normalize_timestamp(start_date)
                ).replace(minute=0, second=0, microsecond=0)
                end_dt = datetime.fromtimestamp(_normalize_timestamp(end_date))
                while current <= end_dt:
                    hour_str = current.strftime("%Y-%m-%d %H:00")
                    if hour_str not in hourly_counts:
                        hourly_counts[hour_str] = {}
                    current += timedelta(hours=1)

            return hourly_counts


ChatMessages = ChatMessageTable()
