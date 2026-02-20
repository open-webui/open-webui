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
    CheckConstraint,
    Index,
)

from open_webui.internal.db import Base, get_db_context
from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)


####################
# DB Schema
####################


class OversightAssignment(Base):
    __tablename__ = "oversight_assignment"

    id = Column(Text, primary_key=True)
    overseer_id = Column(
        Text,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id = Column(
        Text,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = Column(
        Text,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(BigInteger, nullable=False)
    source = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "overseer_id", "target_id", name="uq_oversight_overseer_target"
        ),
        CheckConstraint("overseer_id != target_id", name="ck_oversight_no_self"),
        Index("idx_oversight_overseer", "overseer_id"),
        Index("idx_oversight_target", "target_id"),
    )


####################
# Pydantic Models
####################


class OversightAssignmentModel(BaseModel):
    id: str
    overseer_id: str
    target_id: str
    created_by: str
    created_at: int
    source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OversightAssignmentForm(BaseModel):
    overseer_id: Optional[str] = None
    target_id: str
    source: Optional[str] = None


class BulkAssignForm(BaseModel):
    group_id: str
    overseer_id: str


####################
# Table Operations
####################


class OversightAssignmentTable:
    def add_assignment(
        self,
        overseer_id: str,
        target_id: str,
        created_by: str,
        source: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[OversightAssignmentModel]:
        with get_db_context(db) as db:
            try:
                existing = (
                    db.query(OversightAssignment)
                    .filter_by(overseer_id=overseer_id, target_id=target_id)
                    .first()
                )
                if existing:
                    return OversightAssignmentModel.model_validate(existing)

                assignment = OversightAssignment(
                    id=str(uuid.uuid4()),
                    overseer_id=overseer_id,
                    target_id=target_id,
                    created_by=created_by,
                    created_at=int(time.time()),
                    source=source,
                )
                db.add(assignment)
                db.commit()
                db.refresh(assignment)
                return OversightAssignmentModel.model_validate(assignment)
            except Exception as e:
                log.exception(f"Failed to add oversight assignment: {e}")
                db.rollback()
                return None

    def remove_assignment(
        self,
        overseer_id: str,
        target_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        with get_db_context(db) as db:
            try:
                deleted = (
                    db.query(OversightAssignment)
                    .filter_by(overseer_id=overseer_id, target_id=target_id)
                    .delete()
                )
                db.commit()
                return deleted > 0
            except Exception as e:
                log.exception(f"Failed to remove oversight assignment: {e}")
                db.rollback()
                return False

    def get_targets_for_overseer(
        self,
        overseer_id: str,
        db: Optional[Session] = None,
    ) -> list[OversightAssignmentModel]:
        with get_db_context(db) as db:
            rows = (
                db.query(OversightAssignment).filter_by(overseer_id=overseer_id).all()
            )
            return [OversightAssignmentModel.model_validate(r) for r in rows]

    def get_target_ids_for_overseer(
        self,
        overseer_id: str,
        db: Optional[Session] = None,
    ) -> set[str]:
        with get_db_context(db) as db:
            rows = (
                db.query(OversightAssignment.target_id)
                .filter_by(overseer_id=overseer_id)
                .all()
            )
            return {r[0] for r in rows}

    def get_overseers_for_target(
        self,
        target_id: str,
        db: Optional[Session] = None,
    ) -> list[OversightAssignmentModel]:
        with get_db_context(db) as db:
            rows = db.query(OversightAssignment).filter_by(target_id=target_id).all()
            return [OversightAssignmentModel.model_validate(r) for r in rows]

    def get_all_assignments(
        self,
        db: Optional[Session] = None,
    ) -> list[OversightAssignmentModel]:
        with get_db_context(db) as db:
            rows = db.query(OversightAssignment).all()
            return [OversightAssignmentModel.model_validate(r) for r in rows]

    def has_assignment(
        self,
        overseer_id: str,
        target_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        with get_db_context(db) as db:
            return (
                db.query(OversightAssignment)
                .filter_by(overseer_id=overseer_id, target_id=target_id)
                .first()
                is not None
            )

    def remove_all_for_overseer(
        self,
        overseer_id: str,
        db: Optional[Session] = None,
    ) -> int:
        with get_db_context(db) as db:
            try:
                deleted = (
                    db.query(OversightAssignment)
                    .filter_by(overseer_id=overseer_id)
                    .delete()
                )
                db.commit()
                return deleted
            except Exception as e:
                log.exception(f"Failed to remove assignments for overseer: {e}")
                db.rollback()
                return 0


OversightAssignments = OversightAssignmentTable()
