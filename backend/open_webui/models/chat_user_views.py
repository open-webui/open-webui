"""
ChatUserView model for tracking when users last viewed a chat.
Used to determine unread status for shared/space chats.
"""

import logging
import time
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, ForeignKey, Text, Index
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context, engine

log = logging.getLogger(__name__)


####################
# ChatUserView DB Schema
####################


class ChatUserView(Base):
    """Tracks when a user last viewed a specific chat."""

    __tablename__ = "chat_user_view"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text, nullable=False)
    chat_id = Column(Text, ForeignKey("chat.id", ondelete="CASCADE"), nullable=False)
    last_viewed_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        # Composite unique constraint for user_id + chat_id
        Index("idx_chat_user_view_user_chat", "user_id", "chat_id", unique=True),
        # Index for looking up all views by user
        Index("idx_chat_user_view_user_id", "user_id"),
        # Index for looking up all views for a chat
        Index("idx_chat_user_view_chat_id", "chat_id"),
    )


####################
# Pydantic Models
####################


class ChatUserViewModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    chat_id: str
    last_viewed_at: int


####################
# ChatUserViewTable
####################


class ChatUserViewTable:
    def upsert_view(
        self,
        user_id: str,
        chat_id: str,
        viewed_at: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Optional[ChatUserViewModel]:
        """
        Record that a user viewed a chat at the specified time.
        If a record already exists, update the timestamp.
        """
        with get_db_context(db) as db:
            try:
                # Check if record exists
                existing = (
                    db.query(ChatUserView)
                    .filter_by(user_id=user_id, chat_id=chat_id)
                    .first()
                )

                timestamp = viewed_at if viewed_at is not None else int(time.time())

                if existing:
                    existing.last_viewed_at = timestamp
                    db.commit()
                    db.refresh(existing)
                    return ChatUserViewModel.model_validate(existing)
                else:
                    view = ChatUserView(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        chat_id=chat_id,
                        last_viewed_at=timestamp,
                    )
                    db.add(view)
                    db.commit()
                    db.refresh(view)
                    return ChatUserViewModel.model_validate(view)
            except Exception as e:
                log.exception(f"Error upserting chat user view: {e}")
                return None

    def get_view(
        self,
        user_id: str,
        chat_id: str,
        db: Optional[Session] = None,
    ) -> Optional[ChatUserViewModel]:
        """Get the view record for a specific user and chat."""
        try:
            with get_db_context(db) as db:
                view = (
                    db.query(ChatUserView)
                    .filter_by(user_id=user_id, chat_id=chat_id)
                    .first()
                )
                return ChatUserViewModel.model_validate(view) if view else None
        except Exception as e:
            log.exception(f"Error getting chat user view: {e}")
            return None

    def get_last_viewed_at(
        self,
        user_id: str,
        chat_id: str,
        db: Optional[Session] = None,
    ) -> Optional[int]:
        """Get the timestamp when a user last viewed a chat."""
        view = self.get_view(user_id, chat_id, db)
        return view.last_viewed_at if view else None

    def get_views_by_user_id(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> List[ChatUserViewModel]:
        """Get all view records for a user."""
        try:
            with get_db_context(db) as db:
                views = db.query(ChatUserView).filter_by(user_id=user_id).all()
                return [ChatUserViewModel.model_validate(v) for v in views]
        except Exception as e:
            log.exception(f"Error getting views by user_id: {e}")
            return []

    def get_views_by_chat_id(
        self,
        chat_id: str,
        db: Optional[Session] = None,
    ) -> List[ChatUserViewModel]:
        """Get all view records for a chat."""
        try:
            with get_db_context(db) as db:
                views = db.query(ChatUserView).filter_by(chat_id=chat_id).all()
                return [ChatUserViewModel.model_validate(v) for v in views]
        except Exception as e:
            log.exception(f"Error getting views by chat_id: {e}")
            return []

    def get_views_map_by_user_id(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> dict[str, int]:
        """
        Get a mapping of chat_id -> last_viewed_at for all chats a user has viewed.
        Useful for bulk unread checks.
        """
        views = self.get_views_by_user_id(user_id, db)
        return {v.chat_id: v.last_viewed_at for v in views}

    def delete_view(
        self,
        user_id: str,
        chat_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Delete a view record."""
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(ChatUserView)
                    .filter_by(user_id=user_id, chat_id=chat_id)
                    .delete()
                )
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error deleting chat user view: {e}")
            return False

    def delete_views_by_chat_id(
        self,
        chat_id: str,
        db: Optional[Session] = None,
    ) -> int:
        """Delete all view records for a chat (used when chat is deleted)."""
        try:
            with get_db_context(db) as db:
                result = db.query(ChatUserView).filter_by(chat_id=chat_id).delete()
                db.commit()
                return result
        except Exception as e:
            log.exception(f"Error deleting views by chat_id: {e}")
            return 0

    def delete_views_by_user_id(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> int:
        """Delete all view records for a user."""
        try:
            with get_db_context(db) as db:
                result = db.query(ChatUserView).filter_by(user_id=user_id).delete()
                db.commit()
                return result
        except Exception as e:
            log.exception(f"Error deleting views by user_id: {e}")
            return 0


ChatUserViews = ChatUserViewTable()

# Ensure table exists (for fork additions not managed by Alembic)
try:
    ChatUserView.__table__.create(bind=engine, checkfirst=True)
except Exception:
    pass
