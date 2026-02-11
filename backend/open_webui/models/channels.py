import json
import secrets
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context
from open_webui.models.groups import Groups
from open_webui.models.access_grants import (
    AccessGrantModel,
    AccessGrants,
)

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import JSONB


from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    String,
    Text,
    JSON,
    UniqueConstraint,
    case,
    cast,
)
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
    access_grants: list[AccessGrantModel] = Field(default_factory=list)

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


class ChannelFile(Base):
    __tablename__ = "channel_file"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text, nullable=False)

    channel_id = Column(
        Text, ForeignKey("channel.id", ondelete="CASCADE"), nullable=False
    )
    message_id = Column(
        Text, ForeignKey("message.id", ondelete="CASCADE"), nullable=True
    )
    file_id = Column(Text, ForeignKey("file.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("channel_id", "file_id", name="uq_channel_file_channel_file"),
    )


class ChannelFileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str

    channel_id: str
    file_id: str
    user_id: str

    created_at: int  # timestamp in epoch (time_ns)
    updated_at: int  # timestamp in epoch (time_ns)


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
    is_manager: bool = False
    write_access: bool = False

    user_count: Optional[int] = None


class ChannelForm(BaseModel):
    name: str = ""
    description: Optional[str] = None
    is_private: Optional[bool] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_grants: Optional[list[dict]] = None
    group_ids: Optional[list[str]] = None
    user_ids: Optional[list[str]] = None


class CreateChannelForm(ChannelForm):
    type: Optional[str] = None


class ChannelWebhookForm(BaseModel):
    name: str
    profile_image_url: Optional[str] = None


class ChannelTable:
    def _get_access_grants(
        self, channel_id: str, db: Optional[Session] = None
    ) -> list[AccessGrantModel]:
        return AccessGrants.get_grants_by_resource("channel", channel_id, db=db)

    def _to_channel_model(
        self, channel: Channel, db: Optional[Session] = None
    ) -> ChannelModel:
        channel_data = ChannelModel.model_validate(channel).model_dump(
            exclude={"access_grants"}
        )
        access_grants = self._get_access_grants(channel_data["id"], db=db)
        channel_data["access_grants"] = access_grants
        return ChannelModel.model_validate(channel_data)

    def _collect_unique_user_ids(
        self,
        invited_by: str,
        user_ids: Optional[list[str]] = None,
        group_ids: Optional[list[str]] = None,
    ) -> set[str]:
        """
        Collect unique user ids from:
        - invited_by
        - user_ids
        - each group in group_ids
        Returns a set for efficient SQL diffing.
        """
        users = set(user_ids or [])
        users.add(invited_by)

        for group_id in group_ids or []:
            users.update(Groups.get_group_user_ids_by_id(group_id))

        return users

    def _create_membership_models(
        self,
        channel_id: str,
        invited_by: str,
        user_ids: set[str],
    ) -> list[ChannelMember]:
        """
        Takes a set of NEW user IDs (already filtered to exclude existing members).
        Returns ORM ChannelMember objects to be added.
        """
        now = int(time.time_ns())
        memberships = []

        for uid in user_ids:
            model = ChannelMemberModel(
                **{
                    "id": str(uuid.uuid4()),
                    "channel_id": channel_id,
                    "user_id": uid,
                    "status": "joined",
                    "is_active": True,
                    "is_channel_muted": False,
                    "is_channel_pinned": False,
                    "invited_at": now,
                    "invited_by": invited_by,
                    "joined_at": now,
                    "left_at": None,
                    "last_read_at": now,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            memberships.append(ChannelMember(**model.model_dump()))

        return memberships

    def insert_new_channel(
        self, form_data: CreateChannelForm, user_id: str, db: Optional[Session] = None
    ) -> Optional[ChannelModel]:
        with get_db_context(db) as db:
            channel = ChannelModel(
                **{
                    **form_data.model_dump(exclude={"access_grants"}),
                    "type": form_data.type if form_data.type else None,
                    "name": form_data.name.lower(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                    "access_grants": [],
                }
            )
            new_channel = Channel(**channel.model_dump(exclude={"access_grants"}))

            if form_data.type in ["group", "dm"]:
                users = self._collect_unique_user_ids(
                    invited_by=user_id,
                    user_ids=form_data.user_ids,
                    group_ids=form_data.group_ids,
                )
                memberships = self._create_membership_models(
                    channel_id=new_channel.id,
                    invited_by=user_id,
                    user_ids=users,
                )

                db.add_all(memberships)
            db.add(new_channel)
            db.commit()
            AccessGrants.set_access_grants(
                "channel", new_channel.id, form_data.access_grants, db=db
            )
            return self._to_channel_model(new_channel, db=db)

    def get_channels(self, db: Optional[Session] = None) -> list[ChannelModel]:
        with get_db_context(db) as db:
            channels = db.query(Channel).all()
            return [self._to_channel_model(channel, db=db) for channel in channels]

    def _has_permission(self, db, query, filter: dict, permission: str = "read"):
        return AccessGrants.has_permission_filter(
            db=db,
            query=query,
            DocumentModel=Channel,
            filter=filter,
            resource_type="channel",
            permission=permission,
        )

    def get_channels_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> list[ChannelModel]:
        with get_db_context(db) as db:
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
            ]

            membership_channels = (
                db.query(Channel)
                .join(ChannelMember, Channel.id == ChannelMember.channel_id)
                .filter(
                    Channel.deleted_at.is_(None),
                    Channel.archived_at.is_(None),
                    Channel.type.in_(["group", "dm"]),
                    ChannelMember.user_id == user_id,
                    ChannelMember.is_active.is_(True),
                )
                .all()
            )

            query = db.query(Channel).filter(
                Channel.deleted_at.is_(None),
                Channel.archived_at.is_(None),
                or_(
                    Channel.type.is_(None),  # True NULL/None
                    Channel.type == "",  # Empty string
                    and_(Channel.type != "group", Channel.type != "dm"),
                ),
            )
            query = self._has_permission(
                db, query, {"user_id": user_id, "group_ids": user_group_ids}
            )

            standard_channels = query.all()

            all_channels = membership_channels + standard_channels
            return [self._to_channel_model(c, db=db) for c in all_channels]

    def get_dm_channel_by_user_ids(
        self, user_ids: list[str], db: Optional[Session] = None
    ) -> Optional[ChannelModel]:
        with get_db_context(db) as db:
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

            return self._to_channel_model(channel, db=db) if channel else None

    def add_members_to_channel(
        self,
        channel_id: str,
        invited_by: str,
        user_ids: Optional[list[str]] = None,
        group_ids: Optional[list[str]] = None,
        db: Optional[Session] = None,
    ) -> list[ChannelMemberModel]:
        with get_db_context(db) as db:
            # 1. Collect all user_ids including groups + inviter
            requested_users = self._collect_unique_user_ids(
                invited_by, user_ids, group_ids
            )

            existing_users = {
                row.user_id
                for row in db.query(ChannelMember.user_id)
                .filter(ChannelMember.channel_id == channel_id)
                .all()
            }

            new_user_ids = requested_users - existing_users
            if not new_user_ids:
                return []  # Nothing to add

            new_memberships = self._create_membership_models(
                channel_id, invited_by, new_user_ids
            )

            db.add_all(new_memberships)
            db.commit()

            return [
                ChannelMemberModel.model_validate(membership)
                for membership in new_memberships
            ]

    def remove_members_from_channel(
        self,
        channel_id: str,
        user_ids: list[str],
        db: Optional[Session] = None,
    ) -> int:
        with get_db_context(db) as db:
            result = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id.in_(user_ids),
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            return result  # number of rows deleted

    def is_user_channel_manager(
        self, channel_id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            # Check if the user is the creator of the channel
            # or has a 'manager' role in ChannelMember
            channel = db.query(Channel).filter(Channel.id == channel_id).first()
            if channel and channel.user_id == user_id:
                return True

            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                    ChannelMember.role == "manager",
                )
                .first()
            )
            return membership is not None

    def join_channel(
        self, channel_id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[ChannelMemberModel]:
        with get_db_context(db) as db:
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

    def leave_channel(
        self, channel_id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
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
        self, channel_id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[ChannelMemberModel]:
        with get_db_context(db) as db:
            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            return ChannelMemberModel.model_validate(membership) if membership else None

    def get_members_by_channel_id(
        self, channel_id: str, db: Optional[Session] = None
    ) -> list[ChannelMemberModel]:
        with get_db_context(db) as db:
            memberships = (
                db.query(ChannelMember)
                .filter(ChannelMember.channel_id == channel_id)
                .all()
            )
            return [
                ChannelMemberModel.model_validate(membership)
                for membership in memberships
            ]

    def pin_channel(
        self,
        channel_id: str,
        user_id: str,
        is_pinned: bool,
        db: Optional[Session] = None,
    ) -> bool:
        with get_db_context(db) as db:
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

    def update_member_last_read_at(
        self, channel_id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
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
        self,
        channel_id: str,
        user_id: str,
        is_active: bool,
        db: Optional[Session] = None,
    ) -> bool:
        with get_db_context(db) as db:
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

    def is_user_channel_member(
        self, channel_id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            membership = (
                db.query(ChannelMember)
                .filter(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
                .first()
            )
            return membership is not None

    def get_channel_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChannelModel]:
        try:
            with get_db_context(db) as db:
                channel = db.query(Channel).filter(Channel.id == id).first()
                return self._to_channel_model(channel, db=db) if channel else None
        except Exception:
            return None

    def get_channels_by_file_id(
        self, file_id: str, db: Optional[Session] = None
    ) -> list[ChannelModel]:
        with get_db_context(db) as db:
            channel_files = (
                db.query(ChannelFile).filter(ChannelFile.file_id == file_id).all()
            )
            channel_ids = [cf.channel_id for cf in channel_files]
            channels = db.query(Channel).filter(Channel.id.in_(channel_ids)).all()
            return [self._to_channel_model(channel, db=db) for channel in channels]

    def get_channels_by_file_id_and_user_id(
        self, file_id: str, user_id: str, db: Optional[Session] = None
    ) -> list[ChannelModel]:
        with get_db_context(db) as db:
            # 1. Determine which channels have this file
            channel_file_rows = (
                db.query(ChannelFile).filter(ChannelFile.file_id == file_id).all()
            )
            channel_ids = [row.channel_id for row in channel_file_rows]

            if not channel_ids:
                return []

            # 2. Load all channel rows that still exist
            channels = (
                db.query(Channel)
                .filter(
                    Channel.id.in_(channel_ids),
                    Channel.deleted_at.is_(None),
                    Channel.archived_at.is_(None),
                )
                .all()
            )
            if not channels:
                return []

            # Preload user's group membership
            user_group_ids = [
                g.id for g in Groups.get_groups_by_member_id(user_id, db=db)
            ]

            allowed_channels = []

            for channel in channels:
                # --- Case A: group or dm => user must be an active member ---
                if channel.type in ["group", "dm"]:
                    membership = (
                        db.query(ChannelMember)
                        .filter(
                            ChannelMember.channel_id == channel.id,
                            ChannelMember.user_id == user_id,
                            ChannelMember.is_active.is_(True),
                        )
                        .first()
                    )
                    if membership:
                        allowed_channels.append(self._to_channel_model(channel, db=db))
                    continue

                # --- Case B: standard channel => rely on ACL permissions ---
                query = db.query(Channel).filter(Channel.id == channel.id)

                query = self._has_permission(
                    db,
                    query,
                    {"user_id": user_id, "group_ids": user_group_ids},
                    permission="read",
                )

                allowed = query.first()
                if allowed:
                    allowed_channels.append(self._to_channel_model(allowed, db=db))

            return allowed_channels

    def get_channel_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[ChannelModel]:
        with get_db_context(db) as db:
            # Fetch the channel
            channel: Channel = (
                db.query(Channel)
                .filter(
                    Channel.id == id,
                    Channel.deleted_at.is_(None),
                    Channel.archived_at.is_(None),
                )
                .first()
            )

            if not channel:
                return None

            # If the channel is a group or dm, read access requires membership (active)
            if channel.type in ["group", "dm"]:
                membership = (
                    db.query(ChannelMember)
                    .filter(
                        ChannelMember.channel_id == id,
                        ChannelMember.user_id == user_id,
                        ChannelMember.is_active.is_(True),
                    )
                    .first()
                )
                if membership:
                    return self._to_channel_model(channel, db=db)
                else:
                    return None

            # For channels that are NOT group/dm, fall back to ACL-based read access
            query = db.query(Channel).filter(Channel.id == id)

            # Determine user groups
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
            ]

            # Apply ACL rules
            query = self._has_permission(
                db,
                query,
                {"user_id": user_id, "group_ids": user_group_ids},
                permission="read",
            )

            channel_allowed = query.first()
            return (
                self._to_channel_model(channel_allowed, db=db)
                if channel_allowed
                else None
            )

    def update_channel_by_id(
        self, id: str, form_data: ChannelForm, db: Optional[Session] = None
    ) -> Optional[ChannelModel]:
        with get_db_context(db) as db:
            channel = db.query(Channel).filter(Channel.id == id).first()
            if not channel:
                return None

            channel.name = form_data.name
            channel.description = form_data.description
            channel.is_private = form_data.is_private

            channel.data = form_data.data
            channel.meta = form_data.meta

            if form_data.access_grants is not None:
                AccessGrants.set_access_grants(
                    "channel", id, form_data.access_grants, db=db
                )
            channel.updated_at = int(time.time_ns())

            db.commit()
            return self._to_channel_model(channel, db=db) if channel else None

    def add_file_to_channel_by_id(
        self, channel_id: str, file_id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[ChannelFileModel]:
        with get_db_context(db) as db:
            channel_file = ChannelFileModel(
                **{
                    "id": str(uuid.uuid4()),
                    "channel_id": channel_id,
                    "file_id": file_id,
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = ChannelFile(**channel_file.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return ChannelFileModel.model_validate(result)
                else:
                    return None
            except Exception:
                return None

    def set_file_message_id_in_channel_by_id(
        self,
        channel_id: str,
        file_id: str,
        message_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                channel_file = (
                    db.query(ChannelFile)
                    .filter_by(channel_id=channel_id, file_id=file_id)
                    .first()
                )
                if not channel_file:
                    return False

                channel_file.message_id = message_id
                channel_file.updated_at = int(time.time())

                db.commit()
                return True
        except Exception:
            return False

    def remove_file_from_channel_by_id(
        self, channel_id: str, file_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(ChannelFile).filter_by(
                    channel_id=channel_id, file_id=file_id
                ).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_channel_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            AccessGrants.revoke_all_access("channel", id, db=db)
            db.query(Channel).filter(Channel.id == id).delete()
            db.commit()
            return True

    ####################
    # Webhook Methods
    ####################

    def insert_webhook(
        self,
        channel_id: str,
        user_id: str,
        form_data: ChannelWebhookForm,
        db: Optional[Session] = None,
    ) -> Optional[ChannelWebhookModel]:
        with get_db_context(db) as db:
            webhook = ChannelWebhookModel(
                id=str(uuid.uuid4()),
                channel_id=channel_id,
                user_id=user_id,
                name=form_data.name,
                profile_image_url=form_data.profile_image_url,
                token=secrets.token_urlsafe(32),
                last_used_at=None,
                created_at=int(time.time_ns()),
                updated_at=int(time.time_ns()),
            )
            db.add(ChannelWebhook(**webhook.model_dump()))
            db.commit()
            return webhook

    def get_webhooks_by_channel_id(
        self, channel_id: str, db: Optional[Session] = None
    ) -> list[ChannelWebhookModel]:
        with get_db_context(db) as db:
            webhooks = (
                db.query(ChannelWebhook)
                .filter(ChannelWebhook.channel_id == channel_id)
                .all()
            )
            return [ChannelWebhookModel.model_validate(w) for w in webhooks]

    def get_webhook_by_id(
        self, webhook_id: str, db: Optional[Session] = None
    ) -> Optional[ChannelWebhookModel]:
        with get_db_context(db) as db:
            webhook = (
                db.query(ChannelWebhook).filter(ChannelWebhook.id == webhook_id).first()
            )
            return ChannelWebhookModel.model_validate(webhook) if webhook else None

    def get_webhook_by_id_and_token(
        self, webhook_id: str, token: str, db: Optional[Session] = None
    ) -> Optional[ChannelWebhookModel]:
        with get_db_context(db) as db:
            webhook = (
                db.query(ChannelWebhook)
                .filter(
                    ChannelWebhook.id == webhook_id,
                    ChannelWebhook.token == token,
                )
                .first()
            )
            return ChannelWebhookModel.model_validate(webhook) if webhook else None

    def update_webhook_by_id(
        self,
        webhook_id: str,
        form_data: ChannelWebhookForm,
        db: Optional[Session] = None,
    ) -> Optional[ChannelWebhookModel]:
        with get_db_context(db) as db:
            webhook = (
                db.query(ChannelWebhook).filter(ChannelWebhook.id == webhook_id).first()
            )
            if not webhook:
                return None
            webhook.name = form_data.name
            webhook.profile_image_url = form_data.profile_image_url
            webhook.updated_at = int(time.time_ns())
            db.commit()
            return ChannelWebhookModel.model_validate(webhook)

    def update_webhook_last_used_at(
        self, webhook_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            webhook = (
                db.query(ChannelWebhook).filter(ChannelWebhook.id == webhook_id).first()
            )
            if not webhook:
                return False
            webhook.last_used_at = int(time.time_ns())
            db.commit()
            return True

    def delete_webhook_by_id(
        self, webhook_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            result = (
                db.query(ChannelWebhook)
                .filter(ChannelWebhook.id == webhook_id)
                .delete()
            )
            db.commit()
            return result > 0


Channels = ChannelTable()
