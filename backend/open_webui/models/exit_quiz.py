import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db, JSONField
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, JSON, Text, Index, Boolean, Integer


class ExitQuizResponse(Base):
    __tablename__ = "exit_quiz_response"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    child_id = Column(String, nullable=False)

    answers = Column(JSON)  # structured answers keyed by question ids/keys
    score = Column(JSON, nullable=True)  # allow number or structured breakdown
    meta = Column(JSON, nullable=True)  # duration_ms, version, etc.

    # Reset/attempt tracking
    attempt_number = Column(Integer, nullable=False, default=1)
    is_current = Column(Boolean, nullable=False, default=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        Index("idx_exit_quiz_user_id", "user_id"),
        Index("idx_exit_quiz_child_id", "child_id"),
        Index("idx_exit_quiz_created_at", "created_at"),
        Index("idx_exit_quiz_attempt", "user_id", "child_id", "attempt_number"),
        Index("idx_exit_quiz_user_current", "user_id", "is_current"),
    )


class ExitQuizModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    child_id: str
    answers: dict
    score: Optional[dict] = None
    meta: Optional[dict] = None
    attempt_number: int
    is_current: bool
    created_at: int
    updated_at: int


class ExitQuizForm(BaseModel):
    child_id: str
    answers: dict
    score: Optional[dict] = None
    meta: Optional[dict] = None


class ExitQuizTable:
    def insert_new_response(self, form_data: ExitQuizForm, user_id: str) -> Optional[ExitQuizModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            ts = int(time.time_ns())

            model = ExitQuizModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "child_id": form_data.child_id,
                    "answers": form_data.answers,
                    "score": form_data.score,
                    "meta": form_data.meta,
                    "attempt_number": 1,
                    "is_current": True,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )

            row = ExitQuizResponse(**model.model_dump())
            db.add(row)
            db.commit()
            db.refresh(row)
            return ExitQuizModel.model_validate(row) if row else None

    def get_responses_by_user(self, user_id: str, child_id: Optional[str] = None) -> list[ExitQuizModel]:
        with get_db() as db:
            query = db.query(ExitQuizResponse).filter(ExitQuizResponse.user_id == user_id)
            if child_id:
                query = query.filter(ExitQuizResponse.child_id == child_id)
            rows = query.order_by(ExitQuizResponse.created_at.desc()).all()
            return [ExitQuizModel.model_validate(r) for r in rows]

    def get_response_by_id(self, id: str, user_id: str) -> Optional[ExitQuizModel]:
        with get_db() as db:
            row = (
                db.query(ExitQuizResponse)
                .filter(ExitQuizResponse.id == id, ExitQuizResponse.user_id == user_id)
                .first()
            )
            return ExitQuizModel.model_validate(row) if row else None

    def update_response_by_id(self, id: str, user_id: str, updated: ExitQuizForm) -> Optional[ExitQuizModel]:
        with get_db() as db:
            row = (
                db.query(ExitQuizResponse)
                .filter(ExitQuizResponse.id == id, ExitQuizResponse.user_id == user_id)
                .first()
            )
            if not row:
                return None
            ts = int(time.time_ns())
            row.child_id = updated.child_id
            row.answers = updated.answers
            row.score = updated.score
            row.meta = updated.meta
            row.updated_at = ts
            db.commit()
            db.refresh(row)
            return ExitQuizModel.model_validate(row)

    def delete_response(self, id: str, user_id: str) -> bool:
        with get_db() as db:
            row = (
                db.query(ExitQuizResponse)
                .filter(ExitQuizResponse.id == id, ExitQuizResponse.user_id == user_id)
                .first()
            )
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True


ExitQuizzes = ExitQuizTable()



