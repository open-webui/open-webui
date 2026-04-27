import json
import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Float, String, Text

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Attempts DB Schema
####################


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    problem_id = Column(String, nullable=True)
    chapter_id = Column(String, nullable=True)
    answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)
    trace_id = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class AttemptModel(BaseModel):
    id: str
    user_id: str
    problem_id: Optional[str] = None
    chapter_id: Optional[str] = None
    answer: Optional[str] = None
    is_correct: Optional[bool] = None
    score: Optional[float] = None
    trace_id: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms / Responses
####################


class AttemptForm(BaseModel):
    user_id: str
    problem_id: Optional[str] = None
    chapter_id: Optional[str] = None
    answer: Optional[str] = None
    is_correct: Optional[bool] = None
    score: Optional[float] = None
    trace_id: Optional[str] = None
    metadata: Optional[dict] = None


class AttemptResponse(BaseModel):
    id: str
    user_id: str
    problem_id: Optional[str] = None
    chapter_id: Optional[str] = None
    is_correct: Optional[bool] = None
    score: Optional[float] = None
    trace_id: Optional[str] = None
    created_at: int


####################
# Table Accessor
####################


class AttemptsTable:
    def insert_new_attempt(self, form: AttemptForm) -> Optional[AttemptModel]:
        with get_db() as db:
            attempt_id = str(uuid.uuid4())
            metadata_json = (
                json.dumps(form.metadata, ensure_ascii=False) if form.metadata else None
            )
            row = Attempt(
                id=attempt_id,
                user_id=form.user_id,
                problem_id=form.problem_id,
                chapter_id=form.chapter_id,
                answer=form.answer,
                is_correct=form.is_correct,
                score=form.score,
                trace_id=form.trace_id,
                metadata_json=metadata_json,
                created_at=int(time.time()),
            )
            try:
                db.add(row)
                db.commit()
                db.refresh(row)
                return AttemptModel.model_validate(row)
            except Exception as e:
                log.exception(f"insert_new_attempt failed: {e}")
                db.rollback()
                return None

    def get_attempt_by_id(self, attempt_id: str) -> Optional[AttemptModel]:
        try:
            with get_db() as db:
                row = db.query(Attempt).filter_by(id=attempt_id).first()
                if not row:
                    return None
                return AttemptModel.model_validate(row)
        except Exception:
            return None

    def get_attempts_by_user(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[AttemptModel]:
        with get_db() as db:
            q = (
                db.query(Attempt)
                .filter(Attempt.user_id == user_id)
                .order_by(Attempt.created_at.desc())
            )
            if skip:
                q = q.offset(skip)
            if limit:
                q = q.limit(limit)
            return [AttemptModel.model_validate(r) for r in q.all()]

    def get_attempts_by_trace(self, trace_id: str) -> list[AttemptModel]:
        with get_db() as db:
            rows = (
                db.query(Attempt)
                .filter(Attempt.trace_id == trace_id)
                .order_by(Attempt.created_at.desc())
                .all()
            )
            return [AttemptModel.model_validate(r) for r in rows]


Attempts = AttemptsTable()
