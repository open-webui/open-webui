"""
Group Oversight Exclusion Model

Handles per-user opt-out from group chat oversight.
Default behavior: group admins can read all group members' chats.
Exclusions allow specific users to be excluded from oversight.
"""

import logging
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import BigInteger, Column, Text, ForeignKey, UniqueConstraint

from open_webui.internal.db import Base, get_db_context
from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)


####################
# DB Schema
####################


class GroupOversightExclusion(Base):
    """
    Represents a user excluded from group chat oversight.

    When a user is in this table for a given group, group admins
    of that group cannot read that user's chats via oversight.
    """

    __tablename__ = "group_oversight_exclusion"

    id = Column(Text, primary_key=True)
    group_id = Column(
        Text,
        ForeignKey("group.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_oversight_excl_group_user"),
    )


####################
# Pydantic Models
####################


class GroupOversightExclusionModel(BaseModel):
    id: str
    group_id: str
    user_id: str
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class GroupOversightExclusionForm(BaseModel):
    user_id: str


####################
# Table Operations
####################


class GroupOversightExclusionTable:
    """CRUD operations for group oversight exclusions."""

    def add_exclusion(
        self,
        group_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[GroupOversightExclusionModel]:
        """Add a user to the exclusion list for a group. Idempotent."""
        with get_db_context(db) as db:
            try:
                # Check if already excluded
                existing = (
                    db.query(GroupOversightExclusion)
                    .filter_by(group_id=group_id, user_id=user_id)
                    .first()
                )
                if existing:
                    return GroupOversightExclusionModel.model_validate(existing)

                exclusion = GroupOversightExclusion(
                    id=str(uuid.uuid4()),
                    group_id=group_id,
                    user_id=user_id,
                    created_at=int(time.time()),
                )
                db.add(exclusion)
                db.commit()
                db.refresh(exclusion)
                return GroupOversightExclusionModel.model_validate(exclusion)
            except Exception as e:
                log.exception(f"Failed to add oversight exclusion: {e}")
                db.rollback()
                return None

    def remove_exclusion(
        self,
        group_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Remove a user from the exclusion list for a group."""
        with get_db_context(db) as db:
            try:
                deleted = (
                    db.query(GroupOversightExclusion)
                    .filter_by(group_id=group_id, user_id=user_id)
                    .delete()
                )
                db.commit()
                return deleted > 0
            except Exception as e:
                log.exception(f"Failed to remove oversight exclusion: {e}")
                db.rollback()
                return False

    def get_exclusions_by_group(
        self,
        group_id: str,
        db: Optional[Session] = None,
    ) -> list[GroupOversightExclusionModel]:
        """Get all exclusions for a group."""
        with get_db_context(db) as db:
            rows = db.query(GroupOversightExclusion).filter_by(group_id=group_id).all()
            return [GroupOversightExclusionModel.model_validate(r) for r in rows]

    def get_excluded_user_ids_by_group(
        self,
        group_id: str,
        db: Optional[Session] = None,
    ) -> set[str]:
        """Get the set of excluded user IDs for a group."""
        with get_db_context(db) as db:
            rows = (
                db.query(GroupOversightExclusion.user_id)
                .filter_by(group_id=group_id)
                .all()
            )
            return {r[0] for r in rows}

    def get_excluded_user_ids_by_groups(
        self,
        group_ids: list[str],
        db: Optional[Session] = None,
    ) -> set[str]:
        """Get all excluded user IDs across multiple groups."""
        if not group_ids:
            return set()
        with get_db_context(db) as db:
            rows = (
                db.query(GroupOversightExclusion.user_id)
                .filter(GroupOversightExclusion.group_id.in_(group_ids))
                .all()
            )
            return {r[0] for r in rows}

    def is_excluded(
        self,
        group_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Check if a user is excluded from oversight in a group."""
        with get_db_context(db) as db:
            return (
                db.query(GroupOversightExclusion)
                .filter_by(group_id=group_id, user_id=user_id)
                .first()
                is not None
            )


OversightExclusions = GroupOversightExclusionTable()
