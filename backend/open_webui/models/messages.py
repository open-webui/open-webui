import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.tags import TagModel, Tag, Tags


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# Message DB Schema
####################


class Message(Base):
    __tablename__ = "message"
    id = Column(Text, primary_key=True)

    user_id = Column(Text)
    channel_id = Column(Text, nullable=True)

    content = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)  # time_ns
    updated_at = Column(BigInteger)  # time_ns


class MessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    channel_id: Optional[str] = None

    content: str
    data: Optional[dict] = None
    meta: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class MessageForm(BaseModel):
    content: str
    data: Optional[dict] = None
    meta: Optional[dict] = None


class MessageTable:
    def insert_new_message(
        self, form_data: MessageForm, channel_id: str, user_id: str
    ) -> Optional[MessageModel]:
        with get_db() as db:
            id = str(uuid.uuid4())

            ts = int(time.time_ns())
            message = MessageModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "content": form_data.content,
                    "data": form_data.data,
                    "meta": form_data.meta,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )

            result = Message(**message.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return MessageModel.model_validate(result) if result else None

    def get_message_by_id(self, id: str) -> Optional[MessageModel]:
        with get_db() as db:
            message = db.get(Message, id)
            return MessageModel.model_validate(message) if message else None

    def get_messages_by_channel_id(
        self, channel_id: str, skip: int = 0, limit: int = 50
    ) -> list[MessageModel]:
        with get_db() as db:
            all_messages = (
                db.query(Message)
                .filter_by(channel_id=channel_id)
                .order_by(Message.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [MessageModel.model_validate(message) for message in all_messages]

    def get_messages_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[MessageModel]:
        with get_db() as db:
            all_messages = (
                db.query(Message)
                .filter_by(user_id=user_id)
                .order_by(Message.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [MessageModel.model_validate(message) for message in all_messages]

    def update_message_by_id(
        self, id: str, form_data: MessageForm
    ) -> Optional[MessageModel]:
        with get_db() as db:
            message = db.get(Message, id)
            message.content = form_data.content
            message.data = form_data.data
            message.meta = form_data.meta
            message.updated_at = int(time.time_ns())
            db.commit()
            db.refresh(message)
            return MessageModel.model_validate(message) if message else None

    def delete_message_by_id(self, id: str) -> bool:
        with get_db() as db:
            db.query(Message).filter_by(id=id).delete()
            db.commit()
            return True


Messages = MessageTable()
