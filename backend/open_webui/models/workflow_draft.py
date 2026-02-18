"""Workflow draft storage - replaces localStorage for exit survey and moderation drafts."""

import time
import uuid
from typing import Any, Optional

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, JSON, Text


class WorkflowDraft(Base):
    __tablename__ = "workflow_draft"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    child_id = Column(Text, nullable=False)
    draft_type = Column(Text, nullable=False)  # "exit_survey" | "moderation"
    data = Column(JSON, nullable=True)
    updated_at = Column(BigInteger, nullable=False)


class WorkflowDraftModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    child_id: str
    draft_type: str
    data: Optional[dict] = None
    updated_at: int


def get_draft(
    user_id: str, child_id: str, draft_type: str
) -> Optional[WorkflowDraftModel]:
    with get_db() as db:
        row = (
            db.query(WorkflowDraft)
            .filter(
                WorkflowDraft.user_id == user_id,
                WorkflowDraft.child_id == child_id,
                WorkflowDraft.draft_type == draft_type,
            )
            .first()
        )
        return WorkflowDraftModel.model_validate(row) if row else None


def save_draft(
    user_id: str, child_id: str, draft_type: str, data: dict
) -> WorkflowDraftModel:
    ts = int(time.time() * 1000)
    with get_db() as db:
        row = (
            db.query(WorkflowDraft)
            .filter(
                WorkflowDraft.user_id == user_id,
                WorkflowDraft.child_id == child_id,
                WorkflowDraft.draft_type == draft_type,
            )
            .first()
        )
        if row:
            row.data = data
            row.updated_at = ts
            db.commit()
            db.refresh(row)
        else:
            row = WorkflowDraft(
                id=str(uuid.uuid4()),
                user_id=user_id,
                child_id=child_id,
                draft_type=draft_type,
                data=data,
                updated_at=ts,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return WorkflowDraftModel.model_validate(row)


def delete_draft(user_id: str, child_id: str, draft_type: str) -> bool:
    with get_db() as db:
        row = (
            db.query(WorkflowDraft)
            .filter(
                WorkflowDraft.user_id == user_id,
                WorkflowDraft.child_id == child_id,
                WorkflowDraft.draft_type == draft_type,
            )
            .first()
        )
        if row:
            db.delete(row)
            db.commit()
            return True
        return False
