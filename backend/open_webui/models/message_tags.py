"""
Message Tags Model

Handles message-level tagging with AI-generated tags and summaries.
"""

import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Integer, JSON, Index, UniqueConstraint

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Message Tag Definition DB Schema
####################
class MessageTagDefinition(Base):
    __tablename__ = "message_tag_definition"

    id = Column(String, primary_key=True)  # Normalized tag ID (e.g., "calculus_basics")
    name = Column(String, nullable=False)  # Display name (e.g., "Calculus Basics")
    usage_count = Column(Integer, default=0)  # For consolidation priority
    is_protected = Column(Boolean, default=False)  # Admin-created tags that can't be auto-deleted
    chapter_id = Column(String, nullable=True)  # Link to textbook_chapter
    meta = Column(JSON, nullable=True)  # For AI similarity hints
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_message_tag_def_usage", "usage_count"),
        Index("idx_message_tag_def_chapter", "chapter_id"),
    )


class MessageTagDefinitionModel(BaseModel):
    id: str
    name: str
    usage_count: int = 0
    is_protected: bool = False
    chapter_id: Optional[str] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Message Tag DB Schema
####################
class MessageTag(Base):
    __tablename__ = "message_tag"

    id = Column(String, primary_key=True)
    chat_id = Column(String, nullable=False)  # Reference to chat.id
    message_id = Column(String, nullable=False)  # Key from chat.chat["history"]["messages"]
    tag_id = Column(String, nullable=False)  # Reference to message_tag_definition.id
    summary = Column(String(100), nullable=True)  # Summary of the message
    user_id = Column(String, nullable=False)  # For access control
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_message_tag_chat_message", "chat_id", "message_id"),
        Index("idx_message_tag_tag", "tag_id"),
        Index("idx_message_tag_user", "user_id"),
        UniqueConstraint("chat_id", "message_id", "tag_id", name="uq_chat_message_tag"),
    )


class MessageTagModel(BaseModel):
    id: str
    chat_id: str
    message_id: str
    tag_id: str
    summary: Optional[str] = None
    user_id: str
    created_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Tagging Daemon Config DB Schema
####################
class TaggingDaemonConfig(Base):
    __tablename__ = "tagging_daemon_config"

    id = Column(String, primary_key=True, default="default")
    enabled = Column(Boolean, default=True)
    schedule = Column(String, default="daily")  # "daily" | "weekly"
    run_time = Column(String, default="03:00")  # Time to run (UTC)
    lookback_days = Column(Integer, default=7)  # Process messages from last N days
    batch_size = Column(Integer, default=10)  # Messages per Gemini API call
    max_tags = Column(Integer, default=100)  # Maximum unique tags
    consolidation_threshold = Column(Integer, default=90)  # Start consolidation at N tags
    custom_tagging_prompt = Column(String, nullable=True)  # Custom prompt for AI tagging
    custom_system_instruction = Column(String, nullable=True)  # Custom system instruction
    blacklisted_tags = Column(JSON, nullable=True)  # List of tag IDs that should never be created
    last_run_at = Column(BigInteger, nullable=True)
    last_run_status = Column(String, nullable=True)
    lock_acquired_at = Column(BigInteger, nullable=True)  # For distributed locking
    lock_instance_id = Column(String, nullable=True)
    updated_at = Column(BigInteger, nullable=False)


class TaggingDaemonConfigModel(BaseModel):
    id: str = "default"
    enabled: bool = True
    schedule: str = "daily"
    run_time: str = "03:00"
    lookback_days: int = 7
    batch_size: int = 10
    max_tags: int = 100
    consolidation_threshold: int = 90
    custom_tagging_prompt: Optional[str] = None
    custom_system_instruction: Optional[str] = None
    blacklisted_tags: Optional[List[str]] = None
    last_run_at: Optional[int] = None
    last_run_status: Optional[str] = None
    lock_acquired_at: Optional[int] = None
    lock_instance_id: Optional[str] = None
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Table Operations
####################

class MessageTagTable:
    """Table operations for message_tag."""

    def create(
        self,
        chat_id: str,
        message_id: str,
        tag_id: str,
        summary: Optional[str],
        user_id: str
    ) -> Optional[MessageTagModel]:
        try:
            with get_db() as db:
                tag = MessageTag(
                    id=str(uuid.uuid4()),
                    chat_id=chat_id,
                    message_id=message_id,
                    tag_id=tag_id,
                    summary=summary[:100] if summary else None,
                    user_id=user_id,
                    created_at=int(time.time())
                )
                db.add(tag)
                db.commit()
                db.refresh(tag)
                return MessageTagModel.model_validate(tag)
        except Exception as e:
            log.error(f"Error creating message tag: {e}")
            return None

    def has_tags(self, chat_id: str, message_id: str) -> bool:
        with get_db() as db:
            count = db.query(MessageTag).filter_by(
                chat_id=chat_id, message_id=message_id
            ).count()
            return count > 0

    def get_by_message(self, chat_id: str, message_id: str) -> List[MessageTagModel]:
        with get_db() as db:
            tags = db.query(MessageTag).filter_by(
                chat_id=chat_id, message_id=message_id
            ).all()
            return [MessageTagModel.model_validate(t) for t in tags]

    def get_by_tag(self, tag_id: str, limit: int = 100) -> List[MessageTagModel]:
        with get_db() as db:
            tags = db.query(MessageTag).filter_by(tag_id=tag_id).limit(limit).all()
            return [MessageTagModel.model_validate(t) for t in tags]

    def get_by_tag_and_user(
        self, tag_id: str, user_id: str, limit: int = 100
    ) -> List[MessageTagModel]:
        with get_db() as db:
            tags = db.query(MessageTag).filter_by(
                tag_id=tag_id, user_id=user_id
            ).limit(limit).all()
            return [MessageTagModel.model_validate(t) for t in tags]

    def update_tag_id(self, old_tag_id: str, new_tag_id: str) -> int:
        """Update all messages with old_tag_id to new_tag_id (for consolidation)."""
        with get_db() as db:
            count = db.query(MessageTag).filter_by(tag_id=old_tag_id).update(
                {"tag_id": new_tag_id}
            )
            db.commit()
            return count

    def delete_by_chat(self, chat_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(MessageTag).filter_by(chat_id=chat_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting message tags by chat: {e}")
            return False

    def delete_by_tag(self, tag_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(MessageTag).filter_by(tag_id=tag_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting message tags by tag: {e}")
            return False

    def delete_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(MessageTag).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting message tag: {e}")
            return False


class MessageTagDefinitionTable:
    """Table operations for message_tag_definition."""

    def create(self, name: str, is_protected: bool = False, tag_id: Optional[str] = None, chapter_id: Optional[str] = None) -> Optional[MessageTagDefinitionModel]:
        """Create a new tag definition.

        Args:
            name: Display name (e.g., "라플라스 변환 (Laplace Transform)")
            is_protected: Whether this tag is protected from auto-deletion
            tag_id: Optional explicit tag ID. If not provided, generated from name.
            chapter_id: Optional link to textbook_chapter.
        """
        try:
            with get_db() as db:
                now = int(time.time())
                # Use provided tag_id or generate from name
                final_tag_id = tag_id if tag_id else name.lower().replace(" ", "_")
                tag_def = MessageTagDefinition(
                    id=final_tag_id,
                    name=name,
                    usage_count=0,
                    is_protected=is_protected,
                    chapter_id=chapter_id,
                    created_at=now,
                    updated_at=now
                )
                db.add(tag_def)
                db.commit()
                db.refresh(tag_def)
                return MessageTagDefinitionModel.model_validate(tag_def)
        except Exception as e:
            log.error(f"Error creating message tag definition: {e}")
            return None

    def update_chapter_id(self, tag_id: str, chapter_id: str) -> Optional[MessageTagDefinitionModel]:
        """Update the chapter_id for a tag (only if currently null)."""
        try:
            with get_db() as db:
                tag = db.query(MessageTagDefinition).filter_by(id=tag_id).first()
                if tag and tag.chapter_id is None:
                    tag.chapter_id = chapter_id
                    tag.updated_at = int(time.time())
                    db.commit()
                    db.refresh(tag)
                    return MessageTagDefinitionModel.model_validate(tag)
                return MessageTagDefinitionModel.model_validate(tag) if tag else None
        except Exception as e:
            log.error(f"Error updating tag chapter_id: {e}")
            return None

    def set_protected(self, id: str, is_protected: bool) -> Optional[MessageTagDefinitionModel]:
        """Set or unset protection status for a tag."""
        try:
            with get_db() as db:
                tag = db.query(MessageTagDefinition).filter_by(id=id).first()
                if tag:
                    tag.is_protected = is_protected
                    tag.updated_at = int(time.time())
                    db.commit()
                    db.refresh(tag)
                    return MessageTagDefinitionModel.model_validate(tag)
                return None
        except Exception as e:
            log.error(f"Error setting tag protection: {e}")
            return None

    def get_unprotected_tags(self) -> List[MessageTagDefinitionModel]:
        """Get all tags that are not protected (can be auto-deleted/merged)."""
        with get_db() as db:
            tags = db.query(MessageTagDefinition).filter_by(is_protected=False).all()
            return [MessageTagDefinitionModel.model_validate(t) for t in tags]

    def get_by_id(self, id: str) -> Optional[MessageTagDefinitionModel]:
        with get_db() as db:
            tag = db.query(MessageTagDefinition).filter_by(id=id).first()
            return MessageTagDefinitionModel.model_validate(tag) if tag else None

    def get_count(self) -> int:
        with get_db() as db:
            return db.query(MessageTagDefinition).count()

    def get_all(self) -> List[MessageTagDefinitionModel]:
        with get_db() as db:
            tags = db.query(MessageTagDefinition).all()
            return [MessageTagDefinitionModel.model_validate(t) for t in tags]

    def get_all_tag_names(self) -> List[str]:
        with get_db() as db:
            return [t.name for t in db.query(MessageTagDefinition).all()]

    def get_all_with_usage(self) -> List[MessageTagDefinitionModel]:
        with get_db() as db:
            tags = db.query(MessageTagDefinition).order_by(
                MessageTagDefinition.usage_count.desc()
            ).all()
            return [MessageTagDefinitionModel.model_validate(t) for t in tags]

    def increment_usage(self, id: str) -> bool:
        try:
            with get_db() as db:
                tag = db.query(MessageTagDefinition).filter_by(id=id).first()
                if tag:
                    tag.usage_count += 1
                    tag.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error incrementing tag usage: {e}")
            return False

    def delete(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(MessageTagDefinition).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting message tag definition: {e}")
            return False

    def merge_tags(self, keep_id: str, merge_ids: List[str]) -> bool:
        """Merge multiple tags into one."""
        try:
            with get_db() as db:
                # Get usage counts to sum
                merge_tags = db.query(MessageTagDefinition).filter(
                    MessageTagDefinition.id.in_(merge_ids)
                ).all()
                total_usage = sum(t.usage_count for t in merge_tags)

                # Update kept tag
                kept = db.query(MessageTagDefinition).filter_by(id=keep_id).first()
                if kept:
                    kept.usage_count += total_usage
                    kept.updated_at = int(time.time())

                # Delete merged tags
                db.query(MessageTagDefinition).filter(
                    MessageTagDefinition.id.in_(merge_ids)
                ).delete(synchronize_session=False)

                db.commit()
                return True
        except Exception as e:
            log.error(f"Error merging tags: {e}")
            return False

    def rename(self, id: str, new_name: str) -> Optional[MessageTagDefinitionModel]:
        try:
            with get_db() as db:
                tag = db.query(MessageTagDefinition).filter_by(id=id).first()
                if tag:
                    tag.name = new_name
                    tag.updated_at = int(time.time())
                    db.commit()
                    db.refresh(tag)
                    return MessageTagDefinitionModel.model_validate(tag)
                return None
        except Exception as e:
            log.error(f"Error renaming tag: {e}")
            return None


class TaggingDaemonConfigTable:
    """Table operations for tagging_daemon_config."""

    def get_config(self) -> Optional[TaggingDaemonConfigModel]:
        with get_db() as db:
            config = db.query(TaggingDaemonConfig).filter_by(id="default").first()
            if not config:
                # Create default config
                now = int(time.time())
                config = TaggingDaemonConfig(
                    id="default",
                    enabled=True,
                    schedule="daily",
                    run_time="03:00",
                    lookback_days=7,
                    batch_size=10,
                    max_tags=100,
                    consolidation_threshold=90,
                    updated_at=now
                )
                db.add(config)
                db.commit()
                db.refresh(config)
            return TaggingDaemonConfigModel.model_validate(config)

    def update_config(self, **kwargs) -> Optional[TaggingDaemonConfigModel]:
        try:
            with get_db() as db:
                config = db.query(TaggingDaemonConfig).filter_by(id="default").first()
                if config:
                    for key, value in kwargs.items():
                        if hasattr(config, key) and key != "id":
                            setattr(config, key, value)
                    config.updated_at = int(time.time())
                    db.commit()
                    db.refresh(config)
                    return TaggingDaemonConfigModel.model_validate(config)
                return None
        except Exception as e:
            log.error(f"Error updating daemon config: {e}")
            return None

    def update_lock(self, instance_id: Optional[str], timestamp: Optional[int]) -> bool:
        try:
            with get_db() as db:
                config = db.query(TaggingDaemonConfig).filter_by(id="default").first()
                if config:
                    config.lock_instance_id = instance_id
                    config.lock_acquired_at = timestamp
                    config.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error updating lock: {e}")
            return False

    def update_last_run(self, timestamp: int, status: str) -> bool:
        try:
            with get_db() as db:
                config = db.query(TaggingDaemonConfig).filter_by(id="default").first()
                if config:
                    config.last_run_at = timestamp
                    config.last_run_status = status
                    config.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error updating last run: {e}")
            return False


# Singleton instances
MessageTags = MessageTagTable()
MessageTagDefinitions = MessageTagDefinitionTable()
TaggingDaemonConfigs = TaggingDaemonConfigTable()
