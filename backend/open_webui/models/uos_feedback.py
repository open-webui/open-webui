import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Grants Feedback DB Schema
####################


class GrantsFeedbackBase(Base):
    __tablename__ = "grants_feedback"
    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    chat_id = Column(Text)
    version = Column(BigInteger, default=0)
    type = Column(Text)
    feedback_str = Column(Text, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class GrantsFeedbackModel(BaseModel):
    id: str
    user_id: str
    chat_id: str
    version: int
    type: str
    feedback_str: Optional[str] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class GrantsFeedbackForm(BaseModel):
    feedback: str  # the actual feedback string
    extra_data: Optional[dict] = None  # if you want extensibility later

    model_config = ConfigDict(extra="allow")  # allows arbitrary fields if needed


####################


class GrantsFeedbackTable:
    def insert_new_feedback(
        self, chat_id: str, user_id: str, feedback_str: str
    ) -> GrantsFeedbackModel:
        with get_db() as db:
            id = str(uuid.uuid4())
            feedback = GrantsFeedbackModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "version": 0,
                    "type": "grants_feedback",
                    "feedback_str": feedback_str,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = GrantsFeedbackBase(**feedback.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return GrantsFeedbackModel.model_validate(result)
                else:
                    return None

            except Exception as e:
                log.exception(f"Error creating a new grants feedback: {e}")
                return None

    def get_feedback_by_user_id_and_chat_id(
        self, user_id: str, chat_id: str
    ) -> Optional[GrantsFeedbackModel]:
        try:
            with get_db() as db:
                feedback = (
                    db.query(GrantsFeedbackBase)
                    .filter_by(user_id=user_id, chat_id=chat_id)
                    .first()
                )
                if not feedback:
                    return None
                return GrantsFeedbackModel.model_validate(feedback)
        except Exception:
            return None

    def update_feedback_by_user_id_and_chat_id(
        self, user_id: str, chat_id: str, feedback_str: str
    ) -> Optional[GrantsFeedbackModel]:
        try:
            with get_db() as db:
                feedback = (
                    db.query(GrantsFeedbackBase)
                    .filter_by(user_id=user_id, chat_id=chat_id)
                    .first()
                )
                if not feedback:
                    return None
                feedback.feedback_str = feedback_str
                db.commit()
                db.refresh(feedback)
                return GrantsFeedbackModel.model_validate(feedback)
        except Exception as e:
            log.exception(f"Error updating grants feedback: {e}")
            return None


GrantsFeedback = GrantsFeedbackTable()
