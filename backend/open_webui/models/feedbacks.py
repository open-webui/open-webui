import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import get_db
from open_webui.models.base import Base
from open_webui.models.users import User

from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON

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
    snapshot: Optional[dict] = None
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
    def insert_new_feedback(
        self, user_id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        with get_db() as db:
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

    def get_feedback_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[FeedbackModel]:
        try:
            with get_db() as db:
                feedback = db.query(Feedback).filter_by(id=id, user_id=user_id).first()
                if not feedback:
                    return None
                return FeedbackModel.model_validate(feedback)
        except Exception:
            return None

    def get_all_feedbacks(self) -> list[FeedbackModel]:
        with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in db.query(Feedback)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    def get_all_feedbacks_paginated(
        self, page: int = 1, limit: int = 10, search: str = None
    ) -> list[FeedbackModel]:
        """Get paginated feedbacks with optional search"""
        with get_db() as db:
            # Join with users table to enable username search
            query = db.query(Feedback).outerjoin(User, Feedback.user_id == User.id)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                # Search in multiple fields:
                # 1. JSON data fields: model_id, reason, comment
                # 2. JSON data tags array (using JSON path)
                # 3. User name and email
                # 4. Feedback type
                query = query.filter(
                    # Search in data JSON fields
                    Feedback.data.op("->>")("model_id").ilike(search_term)
                    | Feedback.data.op("->>")("reason").ilike(search_term)
                    | Feedback.data.op("->>")("comment").ilike(search_term)
                    # Search in tags array (convert to string and search)
                    | Feedback.data.op("->>")("tags").cast(Text).ilike(search_term)
                    # Search in user info
                    | User.name.ilike(search_term)
                    | User.email.ilike(search_term)
                    # Search in feedback type
                    | Feedback.type.ilike(search_term)
                    # Search in meta JSON fields (chat_id, message_id)
                    | Feedback.meta.op("->>")("chat_id").ilike(search_term)
                    | Feedback.meta.op("->>")("message_id").ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            feedbacks = (
                query.order_by(Feedback.updated_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return [FeedbackModel.model_validate(feedback) for feedback in feedbacks]

    def get_feedbacks_count(self, search: str = None) -> int:
        """Get total count of feedbacks with optional search filter"""
        with get_db() as db:
            # Join with users table to enable username search
            query = db.query(Feedback).outerjoin(User, Feedback.user_id == User.id)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                # Use same comprehensive search as paginated query
                query = query.filter(
                    # Search in data JSON fields
                    Feedback.data.op("->>")("model_id").ilike(search_term)
                    | Feedback.data.op("->>")("reason").ilike(search_term)
                    | Feedback.data.op("->>")("comment").ilike(search_term)
                    # Search in tags array
                    | Feedback.data.op("->>")("tags").cast(Text).ilike(search_term)
                    # Search in user info
                    | User.name.ilike(search_term)
                    | User.email.ilike(search_term)
                    # Search in feedback type
                    | Feedback.type.ilike(search_term)
                    # Search in meta JSON fields
                    | Feedback.meta.op("->>")("chat_id").ilike(search_term)
                    | Feedback.meta.op("->>")("message_id").ilike(search_term)
                )

            return query.count()

    def get_feedbacks_by_type(self, type: str) -> list[FeedbackModel]:
        with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in db.query(Feedback)
                .filter_by(type=type)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    def get_feedbacks_by_user_id(self, user_id: str) -> list[FeedbackModel]:
        with get_db() as db:
            return [
                FeedbackModel.model_validate(feedback)
                for feedback in db.query(Feedback)
                .filter_by(user_id=user_id)
                .order_by(Feedback.updated_at.desc())
                .all()
            ]

    def update_feedback_by_id(
        self, id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id).first()
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data.model_dump()
            if form_data.meta:
                feedback.meta = form_data.meta
            if form_data.snapshot:
                feedback.snapshot = form_data.snapshot.model_dump()

            feedback.updated_at = int(time.time())

            db.commit()
            return FeedbackModel.model_validate(feedback)

    def update_feedback_by_id_and_user_id(
        self, id: str, user_id: str, form_data: FeedbackForm
    ) -> Optional[FeedbackModel]:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id, user_id=user_id).first()
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data.model_dump()
            if form_data.meta:
                feedback.meta = form_data.meta
            if form_data.snapshot:
                feedback.snapshot = form_data.snapshot.model_dump()

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

    def delete_feedback_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        with get_db() as db:
            feedback = db.query(Feedback).filter_by(id=id, user_id=user_id).first()
            if not feedback:
                return False
            db.delete(feedback)
            db.commit()
            return True

    def delete_feedbacks_by_user_id(self, user_id: str) -> bool:
        with get_db() as db:
            feedbacks = db.query(Feedback).filter_by(user_id=user_id).all()
            if not feedbacks:
                return False
            for feedback in feedbacks:
                db.delete(feedback)
            db.commit()
            return True

    def delete_all_feedbacks(self) -> bool:
        with get_db() as db:
            feedbacks = db.query(Feedback).all()
            if not feedbacks:
                return False
            for feedback in feedbacks:
                db.delete(feedback)
            db.commit()
            return True


Feedbacks = FeedbackTable()
