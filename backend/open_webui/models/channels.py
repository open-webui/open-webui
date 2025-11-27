import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.utils.access_control import has_access

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, case
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# Channel DB Schema
####################


class Channel(Base):
    __tablename__ = "channel"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text)
    type = Column(Text, nullable=True)

    name = Column(Text)
    description = Column(Text, nullable=True)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ChannelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    type: Optional[str] = None

    name: str
    description: Optional[str] = None

    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch (time_ns)
    updated_at: int  # timestamp in epoch (time_ns)


class ChannelMember(Base):
    __tablename__ = "channel_member"

    id = Column(Text, primary_key=True, unique=True)
    channel_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)

    status = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    is_channel_muted = Column(Boolean, nullable=False, default=False)
    is_channel_pinned = Column(Boolean, nullable=False, default=False)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    joined_at = Column(BigInteger)
    left_at = Column(BigInteger, nullable=True)

    last_read_at = Column(BigInteger, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ChannelMemberModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    user_id: str

    status: Optional[str] = None
    is_active: bool = True

    is_channel_muted: bool = False
    is_channel_pinned: bool = False

    data: Optional[dict] = None
    meta: Optional[dict] = None

    joined_at: Optional[int] = None  # timestamp in epoch (time_ns)
    left_at: Optional[int] = None  # timestamp in epoch (time_ns)

    last_read_at: Optional[int] = None  # timestamp in epoch (time_ns)

    created_at: Optional[int] = None  # timestamp in epoch (time_ns)
    updated_at: Optional[int] = None  # timestamp in epoch (time_ns)


####################
# Forms
####################


class ChannelResponse(ChannelModel):
    write_access: bool = False
    user_count: Optional[int] = None


class ChannelForm(BaseModel):
    type: Optional[str] = None
    name: str
    description: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None
    user_ids: Optional[list[str]] = None


class ChannelTable:
    def insert_new_channel(
        self, form_data: ChannelForm, user_id: str
    ) -> Optional[ChannelModel]:
        with get_db() as db:
            channel = ChannelModel(
                **{
                    **form_data.model_dump(),
                    "type": form_data.type if form_data.type else None,
                    "name": form_data.name.lower(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )
            new_channel = Channel(**channel.model_dump())

            if form_data.type == "dm":
                # For direct message channels, automatically add the specified users as members
                user_ids = form_data.user_ids or []
                if user_id not in user_ids:
                    user_ids.append(user_id)  # Ensure the creator is also a member

                for uid in user_ids:
                    channel_member = ChannelMemberModel(
                        **{
                            "id": str(uuid.uuid4()),
                            "channel_id": channel.id,
                            "user_id": uid,
                            "status": "joined",
                            "is_active": True,
                            "is_channel_muted": False,
                            "is_channel_pinned": False,
                            "joined_at": int(time.time_ns()),
                            "left_at": None,
                            "last_read_at": int(time.time_ns()),
                            "created_at": int(time.time_ns()),
                            "updated_at": int(time.time_ns()),
                        }
                    )
                    new_membership = ChannelMember(**channel_member.model_dump())
                    db.add(new_membership)

            db.add(new_channel)
            db.commit()
            return channel

    def get_channels(self) -> list[ChannelModel]:
        with get_db() as db:
            channels = db.query(Channel).all()
            return [ChannelModel.model_validate(channel) for channel in channels]

    def get_channels_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> list[ChannelModel]:
        channels = self.get_channels()

        channel_list = []
        for channel in channels:
            if channel.type == "dm":
                membership = self.get_member_by_channel_and_user_id(channel.id, user_id)
                if membership and membership.is_active:
                    channel_list.append(channel)
            else:
                if channel.user_id == user_id or has_access(
                    user_id, permission, channel.access_control
                ):
                    channel_list.append(channel)

        return channel_list

    def get_dm_channel_by_user_ids(self, user_ids: list[str]) -> Optional[ChannelModel]:
        with get_db() as db:
            # Ensure uniqueness in case a list with duplicates is passed
            unique_user_ids = list(set(user_ids))

            match_count = func.sum(
                case(
                    (ChannelMember.user_id.in_(unique_user_ids), 1),
                    else_=0,
                )
            )

            subquery = (
                db.query(ChannelMember.channel_id)
                .group_by(ChannelMember.channel_id)
                # 1. Channel must have exactly len(user_ids) members
                .having(func.count(ChannelMember.user_id) == len(unique_user_ids))
                # 2. All those members must be in unique_user_ids
                .having(match_count == len(unique_user_ids))
                .subquery()
            )

            channel = (
                db.query(Channel)
                .filter(
                    Channel.id.in_(subquery),
                    Channel.type == "dm",
                )
                .first()
            )

            return ChannelModel.model_validate(channel) if channel else None

    def join_channel(
        self, channel_id: str, user_id: str
    ) -> Optional[ChannelMemberModel]:
        with get_db() as db:
            # Check if the membership already exists
            existing_membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            if existing_membership:
                return ChannelMemberModel.model_validate(existing_membership)

            # Create new membership
            channel_member = ChannelMemberModel(
                **{
                    "id": str(uuid.uuid4()),
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "status": "joined",
                    "is_active": True,
                    "is_channel_muted": False,
                    "is_channel_pinned": False,
                    "joined_at": int(time.time_ns()),
                    "left_at": None,
                    "last_read_at": int(time.time_ns()),
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )
            new_membership = ChannelMember(**channel_member.model_dump())

            db.add(new_membership)
            db.commit()
            return channel_member

    def leave_channel(self, channel_id: str, user_id: str) -> bool:
        with get_db() as db:
            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            if not membership:
                return False

            membership.status = "left"
            membership.is_active = False
            membership.left_at = int(time.time_ns())
            membership.updated_at = int(time.time_ns())

            db.commit()
            return True

    def get_member_by_channel_and_user_id(
        self, channel_id: str, user_id: str
    ) -> Optional[ChannelMemberModel]:
        with get_db() as db:
            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            return ChannelMemberModel.model_validate(membership) if membership else None

    def get_members_by_channel_id(self, channel_id: str) -> list[ChannelMemberModel]:
        with get_db() as db:
            memberships = (
                db.query(ChannelMember)
                .filter(ChannelMember.channel_id == channel_id)
                .all()
            )
            return [
                ChannelMemberModel.model_validate(membership)
                for membership in memberships
            ]

    def pin_channel(self, channel_id: str, user_id: str, is_pinned: bool) -> bool:
        with get_db() as db:
            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            if not membership:
                return False

            membership.is_channel_pinned = is_pinned
            membership.updated_at = int(time.time_ns())

            db.commit()
            return True

    def update_member_last_read_at(self, channel_id: str, user_id: str) -> bool:
        with get_db() as db:
            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            if not membership:
                return False

            membership.last_read_at = int(time.time_ns())
            membership.updated_at = int(time.time_ns())

            db.commit()
            return True

    def update_member_active_status(
        self, channel_id: str, user_id: str, is_active: bool
    ) -> bool:
        with get_db() as db:
            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            if not membership:
                return False

            membership.is_active = is_active
            membership.updated_at = int(time.time_ns())

            db.commit()
            return True

    def is_user_channel_member(self, channel_id: str, user_id: str) -> bool:
        with get_db() as db:
            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            return membership is not None

    def get_channel_by_id(self, id: str) -> Optional[ChannelModel]:
        with get_db() as db:
            channel = db.query(Channel).filter(Channel.id == id).first()
            return ChannelModel.model_validate(channel) if channel else None

    def update_channel_by_id(
        self, id: str, form_data: ChannelForm
    ) -> Optional[ChannelModel]:
        with get_db() as db:
            channel = db.query(Channel).filter(Channel.id == id).first()
            if not channel:
                return None

            channel.name = form_data.name
            channel.data = form_data.data
            channel.meta = form_data.meta
            channel.access_control = form_data.access_control
            channel.updated_at = int(time.time_ns())

            db.commit()
            return ChannelModel.model_validate(channel) if channel else None

    def delete_channel_by_id(self, id: str):
        with get_db() as db:
            db.query(Channel).filter(Channel.id == id).delete()
            db.commit()
            return True


Channels = ChannelTable()
