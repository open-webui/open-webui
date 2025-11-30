import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.groups import Groups
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

    # Used to indicate if the channel is private (for 'group' type channels)
    is_private = Column(Boolean, nullable=True)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)

    updated_at = Column(BigInteger)
    updated_by = Column(Text, nullable=True)

    archived_at = Column(BigInteger, nullable=True)
    archived_by = Column(Text, nullable=True)

    deleted_at = Column(BigInteger, nullable=True)
    deleted_by = Column(Text, nullable=True)


class ChannelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    type: Optional[str] = None

    name: str
    description: Optional[str] = None

    is_private: Optional[bool] = None

    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch (time_ns)

    updated_at: int  # timestamp in epoch (time_ns)
    updated_by: Optional[str] = None

    archived_at: Optional[int] = None  # timestamp in epoch (time_ns)
    archived_by: Optional[str] = None

    deleted_at: Optional[int] = None  # timestamp in epoch (time_ns)
    deleted_by: Optional[str] = None


class ChannelMember(Base):
    __tablename__ = "channel_member"

    id = Column(Text, primary_key=True, unique=True)
    channel_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)

    role = Column(Text, nullable=True)
    status = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    is_channel_muted = Column(Boolean, nullable=False, default=False)
    is_channel_pinned = Column(Boolean, nullable=False, default=False)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    invited_at = Column(BigInteger, nullable=True)
    invited_by = Column(Text, nullable=True)

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

    role: Optional[str] = None
    status: Optional[str] = None

    is_active: bool = True

    is_channel_muted: bool = False
    is_channel_pinned: bool = False

    data: Optional[dict] = None
    meta: Optional[dict] = None

    invited_at: Optional[int] = None  # timestamp in epoch (time_ns)
    invited_by: Optional[str] = None

    joined_at: Optional[int] = None  # timestamp in epoch (time_ns)
    left_at: Optional[int] = None  # timestamp in epoch (time_ns)

    last_read_at: Optional[int] = None  # timestamp in epoch (time_ns)

    created_at: Optional[int] = None  # timestamp in epoch (time_ns)
    updated_at: Optional[int] = None  # timestamp in epoch (time_ns)


class ChannelWebhook(Base):
    __tablename__ = "channel_webhook"

    id = Column(Text, primary_key=True, unique=True)
    channel_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)

    name = Column(Text, nullable=False)
    profile_image_url = Column(Text, nullable=True)

    token = Column(Text, nullable=False)
    last_used_at = Column(BigInteger, nullable=True)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class ChannelWebhookModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    user_id: str

    name: str
    profile_image_url: Optional[str] = None

    token: str
    last_used_at: Optional[int] = None  # timestamp in epoch (time_ns)

    created_at: int  # timestamp in epoch (time_ns)
    updated_at: int  # timestamp in epoch (time_ns)


####################
# Forms
####################


class ChannelResponse(ChannelModel):
    write_access: bool = False
    user_count: Optional[int] = None


class ChannelForm(BaseModel):
    name: str = ""
    description: Optional[str] = None
    is_private: Optional[bool] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None
    group_ids: Optional[list[str]] = None
    user_ids: Optional[list[str]] = None


class CreateChannelForm(ChannelForm):
    type: Optional[str] = None


class ChannelTable:

    def _create_memberships_by_user_ids_and_group_ids(
        self,
        channel_id: str,
        invited_by: str,
        user_ids: Optional[list[str]] = None,
        group_ids: Optional[list[str]] = None,
    ) -> list[ChannelMemberModel]:
        # For group and direct message channels, automatically add the specified users as members
        user_ids = user_ids or []
        if invited_by not in user_ids:
            user_ids.append(invited_by)  # Ensure the creator is also a member

        # Add users from specified groups
        group_ids = group_ids or []
        for group_id in group_ids:
            group_user_ids = Groups.get_group_user_ids_by_id(group_id)
            for uid in group_user_ids:
                if uid not in user_ids:
                    user_ids.append(uid)

        # Ensure uniqueness
        user_ids = list(set(user_ids))

        memberships = []
        for uid in user_ids:
            channel_member = ChannelMemberModel(
                **{
                    "id": str(uuid.uuid4()),
                    "channel_id": channel_id,
                    "user_id": uid,
                    "status": "joined",
                    "is_active": True,
                    "is_channel_muted": False,
                    "is_channel_pinned": False,
                    "invited_at": int(time.time_ns()),
                    "invited_by": invited_by,
                    "joined_at": int(time.time_ns()),
                    "left_at": None,
                    "last_read_at": int(time.time_ns()),
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            memberships.append(ChannelMember(**channel_member.model_dump()))

        return memberships

    def insert_new_channel(
        self, form_data: CreateChannelForm, user_id: str
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

            if form_data.type in ["group", "dm"]:
                memberships = self._create_memberships_by_user_ids_and_group_ids(
                    channel.id,
                    user_id,
                    form_data.user_ids,
                    form_data.group_ids,
                )
                db.add_all(memberships)

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
            channel.description = form_data.description
            channel.is_private = form_data.is_private

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
