import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Boolean, Integer, Index

from open_webui.internal.db import Base, get_db


class AttentionCheckQuestion(Base):
    __tablename__ = "attention_check_question"

    id = Column(String, primary_key=True)
    prompt = Column(String, nullable=False)
    options = Column(String, nullable=False)  # pipe-delimited options or JSON-serialized
    correct_option = Column(String, nullable=False)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_acq_created_at", "created_at"),
    )


class AttentionCheckResponse(Base):
    __tablename__ = "attention_check_response"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    session_number = Column(Integer, nullable=True)
    question_id = Column(String, nullable=False)
    response = Column(String, nullable=False)
    is_passed = Column(Boolean, nullable=False, default=False)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_acr_user", "user_id"),
        Index("idx_acr_question", "question_id"),
        Index("idx_acr_created_at", "created_at"),
    )


class AttentionCheckQuestionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prompt: str
    options: str
    correct_option: str
    created_at: int


class AttentionCheckResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    session_number: Optional[int] = None
    question_id: str
    response: str
    is_passed: bool
    created_at: int


class AttentionChecksTable:
    def seed_default_questions(self) -> None:
        """Seed a minimal set of attention check questions if table empty."""
        with get_db() as db:
            count = db.query(AttentionCheckQuestion).count()
            if count > 0:
                return
            now = int(time.time() * 1000)
            defaults = [
                ("Please select ‘Agree’ for this question.", ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"], "Agree"),
                ("Choose the color Blue.", ["Red", "Green", "Blue", "Yellow"], "Blue"),
                ("Select the third option to show you’re paying attention.", ["First option", "Second option", "Third option", "Fourth option"], "Third option"),
                ("Pick ‘I read instructions carefully.’", ["I skim instructions", "I read instructions carefully", "I ignore instructions"], "I read instructions carefully"),
            ]
            for prompt, opts, correct in defaults:
                q = AttentionCheckQuestion(
                    id=str(uuid.uuid4()),
                    prompt=prompt,
                    options="|".join(opts),
                    correct_option=correct,
                    created_at=now,
                )
                db.add(q)
            db.commit()

    def list_questions(self) -> list[AttentionCheckQuestionModel]:
        with get_db() as db:
            rows = db.query(AttentionCheckQuestion).order_by(AttentionCheckQuestion.created_at.asc()).all()
            return [AttentionCheckQuestionModel.model_validate(r) for r in rows]

    def insert_response(self, user_id: str, session_number: Optional[int], question_id: str, response: str) -> AttentionCheckResponseModel:
        with get_db() as db:
            q = db.query(AttentionCheckQuestion).filter(AttentionCheckQuestion.id == question_id).first()
            if not q:
                raise ValueError("Question not found")
            is_passed = (response == q.correct_option)
            row = AttentionCheckResponse(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_number=session_number,
                question_id=question_id,
                response=response,
                is_passed=is_passed,
                created_at=int(time.time() * 1000),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return AttentionCheckResponseModel.model_validate(row)

    def list_responses_by_user(self, user_id: str) -> list[AttentionCheckResponseModel]:
        with get_db() as db:
            rows = db.query(AttentionCheckResponse).filter(AttentionCheckResponse.user_id == user_id).order_by(AttentionCheckResponse.created_at.desc()).all()
            return [AttentionCheckResponseModel.model_validate(r) for r in rows]


AttentionChecks = AttentionChecksTable()


