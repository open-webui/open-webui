import logging
import time
import uuid
from typing import Optional

from open_webui.apps.webui.internal.db import Base, get_db
from open_webui.apps.webui.models.chats import Chats

from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON, Boolean

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Feedback DB Schema
####################


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    type = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class FeedbackModel(BaseModel):
    id: str
    user_id: str
    type: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class RatingData(BaseModel):
    rating: str
    comment: str
    model_config = ConfigDict(extra="allow")


class VoteData(BaseModel):
    rating: str
    model_id: str
    model_ids: list[str]
    model_config = ConfigDict(extra="allow")


class MetaData(BaseModel):
    chat: Optional[dict] = None
    message_id: Optional[str] = None
    tags: Optional[list[str]] = None
    model_config = ConfigDict(extra="allow")


class FeedbackForm(BaseModel):
    type: str
    data: Optional[RatingData | VoteData] = None
    meta: Optional[dict] = None
    model_config = ConfigDict(extra="allow")


class FeedbackTable:
    def insert_new_feedback(
        self, user_id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            feedback = FeedbackModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "type": form_data.type,
                    "data": form_data.data,
                    "meta": form_data.meta,
                    "created_at": int(time.time()),
                }
            )
            try:
                result = Feedback(**feedback.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return FeedbackModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(e)
                return None

    def get_feedback_by_id(self, id: str) -> Optional[FeedbackModel]:
        try:
            with get_db() as db:
                feedback = db.query(Feedback).filter_by(id=id).first()
                if not feedback:
                    return None
                return FeedbackModel.model_validate(feedback)
        except Exception:
            return None

    def get_feedbacks_by_type(self, type: str) -> list[FeedbackModel]:
        with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in db.query(Feedback).filter_by(type=type).all()
            ]

    def get_feedbacks_by_user_id(self, user_id: str) -> list[FeedbackModel]:
        with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in db.query(Feedback).filter_by(user_id=user_id).all()
            ]

    def update_feedback_by_id(
        self, id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id).first()
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data
            if form_data.meta:
                feedback.meta = form_data.meta

            feedback.updated_at = int(time.time())

            db.commit()
            return FeedbackModel.model_validate(feedback)

    def delete_feedback_by_id(self, id: str) -> bool:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id).first()
            if not feedback:
                return False
            db.delete(feedback)
            db.commit()
            return True


Feedbacks = FeedbackTable()
