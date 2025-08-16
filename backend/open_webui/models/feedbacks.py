import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.chats import Chats

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
    version = Column(BigInteger, default=0)
    type = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    snapshot = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class FeedbackModel(BaseModel):
    id: str
    user_id: str
    version: int
    type: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    snapshot: Optional[dict] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    version: int
    type: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int


class RatingData(BaseModel):
    rating: Optional[str | int] = None
    model_id: Optional[str] = None
    sibling_model_ids: Optional[list[str]] = None
    reason: Optional[str] = None
    comment: Optional[str] = None
    model_config = ConfigDict(extra="allow", protected_namespaces=())


class MetaData(BaseModel):
    arena: Optional[bool] = None
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    tags: Optional[list[str]] = None
    model_config = ConfigDict(extra="allow")


class SnapshotData(BaseModel):
    chat: Optional[dict] = None
    model_config = ConfigDict(extra="allow")


class FeedbackForm(BaseModel):
    type: str
    data: Optional[RatingData] = None
    meta: Optional[dict] = None
    snapshot: Optional[SnapshotData] = None
    model_config = ConfigDict(extra="allow")


class FeedbackTable:
    async def insert_new_feedback(
        self, user_id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        async with get_db() as db:
            id = str(uuid.uuid4())
            feedback = FeedbackModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "version": 0,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = Feedback(**feedback.model_dump())
                await db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return FeedbackModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error creating a new feedback: {e}")
                return None

    async def get_feedback_by_id(self, id: str) -> Optional[FeedbackModel]:
        try:
            async with get_db() as db:
                feedback = await db.query(Feedback).filter_by(id=id).first()
                if not feedback:
                    return None
                return FeedbackModel.model_validate(feedback)
        except Exception:
            return None

    async def get_feedback_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[FeedbackModel]:
        try:
            async with get_db() as db:
                feedback = (
                    await db.query(Feedback).filter_by(id=id, user_id=user_id).first()
                )
                if not feedback:
                    return None
                return FeedbackModel.model_validate(feedback)
        except Exception:
            return None

    async def get_all_feedbacks(self) -> list[FeedbackModel]:
        async with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in await db.query(Feedback)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    async def get_feedbacks_by_type(self, type: str) -> list[FeedbackModel]:
        async with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in await db.query(Feedback)
                .filter_by(type=type)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    async def get_feedbacks_by_user_id(self, user_id: str) -> list[FeedbackModel]:
        async with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in await db.query(Feedback)
                .filter_by(user_id=user_id)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    async def update_feedback_by_id(
        self, id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        async with get_db() as db:
            feedback = await db.query(Feedback).filter_by(id=id).first()
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data.model_dump()
            if form_data.meta:
                feedback.meta = form_data.meta
            if form_data.snapshot:
                feedback.snapshot = form_data.snapshot.model_dump()

            feedback.updated_at = int(time.time())

            await db.commit()
            return FeedbackModel.model_validate(feedback)

    async def update_feedback_by_id_and_user_id(
        self, id: str, user_id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        async with get_db() as db:
            feedback = (
                await db.query(Feedback).filter_by(id=id, user_id=user_id).first()
            )
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data.model_dump()
            if form_data.meta:
                feedback.meta = form_data.meta
            if form_data.snapshot:
                feedback.snapshot = form_data.snapshot.model_dump()

            feedback.updated_at = int(time.time())

            await db.commit()
            return FeedbackModel.model_validate(feedback)

    async def delete_feedback_by_id(self, id: str) -> bool:
        async with get_db() as db:
            feedback = await db.query(Feedback).filter_by(id=id).first()
            if not feedback:
                return False
            await db.delete(feedback)
            await db.commit()
            return True

    async def delete_feedback_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        async with get_db() as db:
            feedback = (
                await db.query(Feedback).filter_by(id=id, user_id=user_id).first()
            )
            if not feedback:
                return False
            await db.delete(feedback)
            await db.commit()
            return True

    async def delete_feedbacks_by_user_id(self, user_id: str) -> bool:
        async with get_db() as db:
            feedbacks = await db.query(Feedback).filter_by(user_id=user_id).all()
            if not feedbacks:
                return False
            for feedback in feedbacks:
                await db.delete(feedback)
            await db.commit()
            return True

    async def delete_all_feedbacks(self) -> bool:
        async with get_db() as db:
            feedbacks = await db.query(Feedback).all()
            if not feedbacks:
                return False
            for feedback in feedbacks:
                await db.delete(feedback)
            await db.commit()
            return True


Feedbacks = FeedbackTable()
