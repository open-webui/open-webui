import logging
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import (
    BigInteger,
    Column,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)

from open_webui.internal.db import Base, get_db_context
from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)


####################
# DB Schema
####################


class MessageLimit(Base):
    __tablename__ = "message_limit"

    id = Column(Text, primary_key=True)

    # Scope: exactly ONE of these should be set
    # scope_type="system" -> system-wide default (role_id=None, user_id=None)
    # scope_type="role"   -> per-role limit (role_id set, user_id=None)
    # scope_type="user"   -> per-user override (user_id set, role_id=None)
    scope_type = Column(Text, nullable=False)  # "system", "role", "user"
    role_id = Column(
        Text,
        ForeignKey("role.id", ondelete="CASCADE"),
        nullable=True,
    )
    user_id = Column(
        Text,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Limits (-1 means unlimited)
    max_messages_per_day = Column(BigInteger, default=-1, nullable=False)

    # Metadata
    created_by = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "scope_type", "role_id", "user_id", name="uq_message_limit_scope"
        ),
        Index("message_limit_scope_type_idx", "scope_type"),
        Index("message_limit_role_id_idx", "role_id"),
        Index("message_limit_user_id_idx", "user_id"),
    )


####################
# Pydantic Models
####################


class MessageLimitModel(BaseModel):
    id: str
    scope_type: str
    role_id: Optional[str] = None
    user_id: Optional[str] = None
    max_messages_per_day: int
    created_by: Optional[str] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class MessageLimitForm(BaseModel):
    scope_type: str  # "system", "role", "user"
    role_id: Optional[str] = None
    user_id: Optional[str] = None
    max_messages_per_day: int = -1


class UserLimitStatus(BaseModel):
    effective_limit: int  # -1 = unlimited
    used_today: int
    remaining: int  # -1 if unlimited
    resets_at: int  # Unix timestamp of midnight tonight UTC
    scope_source: str  # "system", "role", "user", "admin", "default"


####################
# Table Operations
####################


class MessageLimitTable:
    def get_system_default(
        self,
        db: Optional[Session] = None,
    ) -> Optional[MessageLimitModel]:
        with get_db_context(db) as db:
            row = db.query(MessageLimit).filter_by(scope_type="system").first()
            return MessageLimitModel.model_validate(row) if row else None

    def get_limit_for_role(
        self,
        role_id: str,
        db: Optional[Session] = None,
    ) -> Optional[MessageLimitModel]:
        with get_db_context(db) as db:
            row = (
                db.query(MessageLimit)
                .filter_by(scope_type="role", role_id=role_id)
                .first()
            )
            return MessageLimitModel.model_validate(row) if row else None

    def get_limit_for_user(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[MessageLimitModel]:
        with get_db_context(db) as db:
            row = (
                db.query(MessageLimit)
                .filter_by(scope_type="user", user_id=user_id)
                .first()
            )
            return MessageLimitModel.model_validate(row) if row else None

    def get_effective_limit(
        self,
        user_id: str,
        role: str,
        role_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> tuple[int, str]:
        """Returns (limit, source). Resolution order:
        admin role -> user override -> role limit -> system default -> -1 (unlimited).
        """
        # Admins are always unlimited
        if role == "admin":
            return (-1, "admin")

        with get_db_context(db) as db:
            # 1. User-specific override
            user_limit = (
                db.query(MessageLimit)
                .filter_by(scope_type="user", user_id=user_id)
                .first()
            )
            if user_limit:
                return (user_limit.max_messages_per_day, "user")

            # 2. Role-based limit
            if role_id:
                role_limit = (
                    db.query(MessageLimit)
                    .filter_by(scope_type="role", role_id=role_id)
                    .first()
                )
                if role_limit:
                    return (role_limit.max_messages_per_day, "role")

            # 3. System default
            system_limit = db.query(MessageLimit).filter_by(scope_type="system").first()
            if system_limit:
                return (system_limit.max_messages_per_day, "system")

            # 4. No limit configured — unlimited
            return (-1, "default")

    def upsert_limit(
        self,
        form_data: MessageLimitForm,
        created_by: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[MessageLimitModel]:
        with get_db_context(db) as db:
            try:
                now = int(time.time())

                existing = (
                    db.query(MessageLimit)
                    .filter_by(
                        scope_type=form_data.scope_type,
                        role_id=form_data.role_id,
                        user_id=form_data.user_id,
                    )
                    .first()
                )

                if existing:
                    existing.max_messages_per_day = form_data.max_messages_per_day
                    existing.updated_at = now
                    db.commit()
                    db.refresh(existing)
                    return MessageLimitModel.model_validate(existing)
                else:
                    limit = MessageLimit(
                        id=str(uuid.uuid4()),
                        scope_type=form_data.scope_type,
                        role_id=form_data.role_id,
                        user_id=form_data.user_id,
                        max_messages_per_day=form_data.max_messages_per_day,
                        created_by=created_by,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(limit)
                    db.commit()
                    db.refresh(limit)
                    return MessageLimitModel.model_validate(limit)
            except Exception as e:
                log.exception(f"Failed to upsert message limit: {e}")
                db.rollback()
                return None

    def delete_limit(
        self,
        id: str,
        db: Optional[Session] = None,
    ) -> bool:
        with get_db_context(db) as db:
            try:
                deleted = db.query(MessageLimit).filter_by(id=id).delete()
                db.commit()
                return deleted > 0
            except Exception as e:
                log.exception(f"Failed to delete message limit: {e}")
                db.rollback()
                return False

    def get_all_limits(
        self,
        db: Optional[Session] = None,
    ) -> list[MessageLimitModel]:
        with get_db_context(db) as db:
            rows = db.query(MessageLimit).all()
            return [MessageLimitModel.model_validate(r) for r in rows]


MessageLimits = MessageLimitTable()
