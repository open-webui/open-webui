"""Prompt history model for version tracking."""

import time
import uuid
from typing import Optional
import json
import difflib

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db_context
from open_webui.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON, Index

####################
# PromptHistory DB Schema
####################


class PromptHistory(Base):
    __tablename__ = "prompt_history"

    id = Column(Text, primary_key=True)
    prompt_id = Column(Text, nullable=False, index=True)
    parent_id = Column(Text, nullable=True)  # Reference to parent commit
    snapshot = Column(JSON, nullable=False)
    user_id = Column(Text, nullable=False)
    commit_message = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class PromptHistoryModel(BaseModel):
    id: str
    prompt_id: str
    parent_id: Optional[str] = None
    snapshot: dict
    user_id: str
    commit_message: Optional[str] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class PromptHistoryResponse(PromptHistoryModel):
    """Response model with user info."""

    user: Optional[UserResponse] = None


class PromptHistoryTable:
    def create_history_entry(
        self,
        prompt_id: str,
        snapshot: dict,
        user_id: str,
        parent_id: Optional[str] = None,
        commit_message: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[PromptHistoryModel]:
        """Create a new history entry (commit) for a prompt."""
        with get_db_context(db) as db:
            history = PromptHistory(
                id=str(uuid.uuid4()),
                prompt_id=prompt_id,
                parent_id=parent_id,
                snapshot=snapshot,
                user_id=user_id,
                commit_message=commit_message,
                created_at=int(time.time()),
            )
            db.add(history)
            db.commit()
            db.refresh(history)
            return PromptHistoryModel.model_validate(history)

    def get_history_by_prompt_id(
        self,
        prompt_id: str,
        limit: int = 50,
        offset: int = 0,
        db: Optional[Session] = None,
    ) -> list[PromptHistoryResponse]:
        """Get all history entries for a prompt, ordered by created_at desc."""
        with get_db_context(db) as db:
            entries = (
                db.query(PromptHistory)
                .filter(PromptHistory.prompt_id == prompt_id)
                .order_by(PromptHistory.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            # Get user info for each entry
            user_ids = list(set(e.user_id for e in entries))
            users = Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            return [
                PromptHistoryResponse(
                    **PromptHistoryModel.model_validate(entry).model_dump(),
                    user=(
                        users_dict.get(entry.user_id).model_dump()
                        if users_dict.get(entry.user_id)
                        else None
                    ),
                )
                for entry in entries
            ]

    def get_history_entry_by_id(
        self,
        history_id: str,
        db: Optional[Session] = None,
    ) -> Optional[PromptHistoryModel]:
        """Get a specific history entry by ID."""
        with get_db_context(db) as db:
            entry = (
                db.query(PromptHistory).filter(PromptHistory.id == history_id).first()
            )
            if entry:
                return PromptHistoryModel.model_validate(entry)
            return None

    def get_latest_history_entry(
        self,
        prompt_id: str,
        db: Optional[Session] = None,
    ) -> Optional[PromptHistoryModel]:
        """Get the most recent history entry for a prompt."""
        with get_db_context(db) as db:
            entry = (
                db.query(PromptHistory)
                .filter(PromptHistory.prompt_id == prompt_id)
                .order_by(PromptHistory.created_at.desc())
                .first()
            )
            if entry:
                return PromptHistoryModel.model_validate(entry)
            return None

    def get_history_count(
        self,
        prompt_id: str,
        db: Optional[Session] = None,
    ) -> int:
        """Get the number of history entries for a prompt."""
        with get_db_context(db) as db:
            return (
                db.query(PromptHistory)
                .filter(PromptHistory.prompt_id == prompt_id)
                .count()
            )

    def compute_diff(
        self,
        from_id: str,
        to_id: str,
        db: Optional[Session] = None,
    ) -> Optional[dict]:
        """Compute diff between two history entries."""
        with get_db_context(db) as db:
            from_entry = (
                db.query(PromptHistory).filter(PromptHistory.id == from_id).first()
            )
            to_entry = db.query(PromptHistory).filter(PromptHistory.id == to_id).first()

            if not from_entry or not to_entry:
                return None

            from_snapshot = from_entry.snapshot
            to_snapshot = to_entry.snapshot

            # Compute diff for content field
            from_content = from_snapshot.get("content", "")
            to_content = to_snapshot.get("content", "")

            diff_lines = list(
                difflib.unified_diff(
                    from_content.splitlines(keepends=True),
                    to_content.splitlines(keepends=True),
                    fromfile=f"v{from_id[:8]}",
                    tofile=f"v{to_id[:8]}",
                    lineterm="",
                )
            )

            return {
                "from_id": from_id,
                "to_id": to_id,
                "from_snapshot": from_snapshot,
                "to_snapshot": to_snapshot,
                "content_diff": diff_lines,
                "name_changed": from_snapshot.get("name") != to_snapshot.get("name"),
            }

    def delete_history_by_prompt_id(
        self,
        prompt_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Delete all history entries for a prompt."""
        with get_db_context(db) as db:
            db.query(PromptHistory).filter(
                PromptHistory.prompt_id == prompt_id
            ).delete()
            db.commit()
            return True

    def delete_history_entry(
        self,
        history_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Delete a history entry and reparent its children to grandparent."""
        with get_db_context(db) as db:
            entry = db.query(PromptHistory).filter_by(id=history_id).first()
            if not entry:
                return False

            # Find children that reference this entry as parent
            children = db.query(PromptHistory).filter_by(parent_id=history_id).all()

            # Reparent children to grandparent
            for child in children:
                child.parent_id = entry.parent_id

            db.delete(entry)
            db.commit()
            return True


PromptHistories = PromptHistoryTable()
