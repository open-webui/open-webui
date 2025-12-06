import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.tags import TagModel, Tag, Tags
from open_webui.models.users import Users, User, UserNameResponse
from open_webui.models.channels import Channels, ChannelMember


from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# Message DB Schema
####################


class MessageReaction(Base):
    __tablename__ = "message_reaction"
    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text)
    message_id = Column(Text)
    name = Column(Text)
    created_at = Column(BigInteger)


class MessageReactionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    message_id: str
    name: str
    created_at: int  # timestamp in epoch


class Message(Base):
    __tablename__ = "message"
    id = Column(Text, primary_key=True, unique=True)

    user_id = Column(Text)
    channel_id = Column(Text, nullable=True)

    reply_to_id = Column(Text, nullable=True)
    parent_id = Column(Text, nullable=True)

    # Pins
    is_pinned = Column(Boolean, nullable=False, default=False)
    pinned_at = Column(BigInteger, nullable=True)
    pinned_by = Column(Text, nullable=True)

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

    reply_to_id: Optional[str] = None
    parent_id: Optional[str] = None

    # Pins
    is_pinned: bool = False
    pinned_by: Optional[str] = None
    pinned_at: Optional[int] = None  # timestamp in epoch (time_ns)

    content: str
    data: Optional[dict] = None
    meta: Optional[dict] = None

    created_at: int  # timestamp in epoch (time_ns)
    updated_at: int  # timestamp in epoch (time_ns)


####################
# Forms
####################


class MessageForm(BaseModel):
    temp_id: Optional[str] = None
    content: str
    reply_to_id: Optional[str] = None
    parent_id: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None


class Reactions(BaseModel):
    name: str
    users: list[dict]
    count: int


class MessageUserResponse(MessageModel):
    user: Optional[UserNameResponse] = None


class MessageUserSlimResponse(MessageUserResponse):
    data: bool | None = None

    @field_validator("data", mode="before")
    def convert_data_to_bool(cls, v):
        # No data or not a dict → False
        if not isinstance(v, dict):
            return False

        # True if ANY value in the dict is non-empty
        return any(bool(val) for val in v.values())


class MessageReplyToResponse(MessageUserResponse):
    reply_to_message: Optional[MessageUserSlimResponse] = None


class MessageWithReactionsResponse(MessageUserSlimResponse):
    reactions: list[Reactions]


class MessageResponse(MessageReplyToResponse):
    latest_reply_at: Optional[int]
    reply_count: int
    reactions: list[Reactions]


class MessageTable:
    def insert_new_message(
        self, form_data: MessageForm, channel_id: str, user_id: str
    ) -> Optional[MessageModel]:
        with get_db() as db:
            channel_member = Channels.join_channel(channel_id, user_id)

            id = str(uuid.uuid4())
            ts = int(time.time_ns())

            message = MessageModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "reply_to_id": form_data.reply_to_id,
                    "parent_id": form_data.parent_id,
                    "is_pinned": False,
                    "pinned_at": None,
                    "pinned_by": None,
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

    def get_message_by_id(self, id: str) -> Optional[MessageResponse]:
        with get_db() as db:
            message = db.get(Message, id)
            if not message:
                return None

            reply_to_message = (
                self.get_message_by_id(message.reply_to_id)
                if message.reply_to_id
                else None
            )

            reactions = self.get_reactions_by_message_id(id)
            thread_replies = self.get_thread_replies_by_message_id(id)

            user = Users.get_user_by_id(message.user_id)
            return MessageResponse.model_validate(
                {
                    **MessageModel.model_validate(message).model_dump(),
                    "user": user.model_dump() if user else None,
                    "reply_to_message": (
                        reply_to_message.model_dump() if reply_to_message else None
                    ),
                    "latest_reply_at": (
                        thread_replies[0].created_at if thread_replies else None
                    ),
                    "reply_count": len(thread_replies),
                    "reactions": reactions,
                }
            )

    def get_thread_replies_by_message_id(self, id: str) -> list[MessageReplyToResponse]:
        with get_db() as db:
            all_messages = (
                db.query(Message)
                .filter_by(parent_id=id)
                .order_by(Message.created_at.desc())
                .all()
            )

            messages = []
            for message in all_messages:
                reply_to_message = (
                    self.get_message_by_id(message.reply_to_id)
                    if message.reply_to_id
                    else None
                )
                messages.append(
                    MessageReplyToResponse.model_validate(
                        {
                            **MessageModel.model_validate(message).model_dump(),
                            "reply_to_message": (
                                reply_to_message.model_dump()
                                if reply_to_message
                                else None
                            ),
                        }
                    )
                )
            return messages

    def get_reply_user_ids_by_message_id(self, id: str) -> list[str]:
        with get_db() as db:
            return [
                message.user_id
                for message in db.query(Message).filter_by(parent_id=id).all()
            ]

    def get_messages_by_channel_id(
        self, channel_id: str, skip: int = 0, limit: int = 50
    ) -> list[MessageReplyToResponse]:
        with get_db() as db:
            all_messages = (
                db.query(Message)
                .filter_by(channel_id=channel_id, parent_id=None)
                .order_by(Message.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

            messages = []
            for message in all_messages:
                reply_to_message = (
                    self.get_message_by_id(message.reply_to_id)
                    if message.reply_to_id
                    else None
                )
                messages.append(
                    MessageReplyToResponse.model_validate(
                        {
                            **MessageModel.model_validate(message).model_dump(),
                            "reply_to_message": (
                                reply_to_message.model_dump()
                                if reply_to_message
                                else None
                            ),
                        }
                    )
                )
            return messages

    def get_messages_by_parent_id(
        self, channel_id: str, parent_id: str, skip: int = 0, limit: int = 50
    ) -> list[MessageReplyToResponse]:
        with get_db() as db:
            message = db.get(Message, parent_id)

            if not message:
                return []

            all_messages = (
                db.query(Message)
                .filter_by(channel_id=channel_id, parent_id=parent_id)
                .order_by(Message.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

            # If length of all_messages is less than limit, then add the parent message
            if len(all_messages) < limit:
                all_messages.append(message)

            messages = []
            for message in all_messages:
                reply_to_message = (
                    self.get_message_by_id(message.reply_to_id)
                    if message.reply_to_id
                    else None
                )
                messages.append(
                    MessageReplyToResponse.model_validate(
                        {
                            **MessageModel.model_validate(message).model_dump(),
                            "reply_to_message": (
                                reply_to_message.model_dump()
                                if reply_to_message
                                else None
                            ),
                        }
                    )
                )
            return messages

    def get_last_message_by_channel_id(self, channel_id: str) -> Optional[MessageModel]:
        with get_db() as db:
            message = (
                db.query(Message)
                .filter_by(channel_id=channel_id)
                .order_by(Message.created_at.desc())
                .first()
            )
            return MessageModel.model_validate(message) if message else None

    def get_pinned_messages_by_channel_id(
        self, channel_id: str, skip: int = 0, limit: int = 50
    ) -> list[MessageModel]:
        with get_db() as db:
            all_messages = (
                db.query(Message)
                .filter_by(channel_id=channel_id, is_pinned=True)
                .order_by(Message.pinned_at.desc())
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
            message.data = {
                **(message.data if message.data else {}),
                **(form_data.data if form_data.data else {}),
            }
            message.meta = {
                **(message.meta if message.meta else {}),
                **(form_data.meta if form_data.meta else {}),
            }
            message.updated_at = int(time.time_ns())
            db.commit()
            db.refresh(message)
            return MessageModel.model_validate(message) if message else None

    def update_is_pinned_by_id(
        self, id: str, is_pinned: bool, pinned_by: Optional[str] = None
    ) -> Optional[MessageModel]:
        with get_db() as db:
            message = db.get(Message, id)
            message.is_pinned = is_pinned
            message.pinned_at = int(time.time_ns()) if is_pinned else None
            message.pinned_by = pinned_by if is_pinned else None
            db.commit()
            db.refresh(message)
            return MessageModel.model_validate(message) if message else None

    def get_unread_message_count(
        self, channel_id: str, user_id: str, last_read_at: Optional[int] = None
    ) -> int:
        with get_db() as db:
            query = db.query(Message).filter(
                Message.channel_id == channel_id,
                Message.parent_id == None,  # only count top-level messages
                Message.created_at > (last_read_at if last_read_at else 0),
            )
            if user_id:
                query = query.filter(Message.user_id != user_id)
            return query.count()

    def add_reaction_to_message(
        self, id: str, user_id: str, name: str
    ) -> Optional[MessageReactionModel]:
        with get_db() as db:
            # check for existing reaction
            existing_reaction = (
                db.query(MessageReaction)
                .filter_by(message_id=id, user_id=user_id, name=name)
                .first()
            )
            if existing_reaction:
                return MessageReactionModel.model_validate(existing_reaction)

            reaction_id = str(uuid.uuid4())
            reaction = MessageReactionModel(
                id=reaction_id,
                user_id=user_id,
                message_id=id,
                name=name,
                created_at=int(time.time_ns()),
            )
            result = MessageReaction(**reaction.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return MessageReactionModel.model_validate(result) if result else None

    def get_reactions_by_message_id(self, id: str) -> list[Reactions]:
        with get_db() as db:
            # JOIN User so all user info is fetched in one query
            results = (
                db.query(MessageReaction, User)
                .join(User, MessageReaction.user_id == User.id)
                .filter(MessageReaction.message_id == id)
                .all()
            )

            reactions = {}

            for reaction, user in results:
                if reaction.name not in reactions:
                    reactions[reaction.name] = {
                        "name": reaction.name,
                        "users": [],
                        "count": 0,
                    }

                reactions[reaction.name]["users"].append(
                    {
                        "id": user.id,
                        "name": user.name,
                    }
                )
                reactions[reaction.name]["count"] += 1

            return [Reactions(**reaction) for reaction in reactions.values()]

    def remove_reaction_by_id_and_user_id_and_name(
        self, id: str, user_id: str, name: str
    ) -> bool:
        with get_db() as db:
            db.query(MessageReaction).filter_by(
                message_id=id, user_id=user_id, name=name
            ).delete()
            db.commit()
            return True

    def delete_reactions_by_id(self, id: str) -> bool:
        with get_db() as db:
            db.query(MessageReaction).filter_by(message_id=id).delete()
            db.commit()
            return True

    def delete_replies_by_id(self, id: str) -> bool:
        with get_db() as db:
            db.query(Message).filter_by(parent_id=id).delete()
            db.commit()
            return True

    def delete_message_by_id(self, id: str) -> bool:
        with get_db() as db:
            db.query(Message).filter_by(id=id).delete()

            # Delete all reactions to this message
            db.query(MessageReaction).filter_by(message_id=id).delete()

            db.commit()
            return True


Messages = MessageTable()
