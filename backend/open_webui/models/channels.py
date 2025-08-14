import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.utils.access_control import has_access

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# Channel DB Schema
####################


class Channel(Base):
    __tablename__ = "channel"

    id = Column(Text, primary_key=True)
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

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class ChannelForm(BaseModel):
    name: str
    description: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class ChannelTable:
    async def insert_new_channel(
        self, type: Optional[str], form_data: ChannelForm, user_id: str
    ) -> Optional[ChannelModel]:
        async with get_db() as db:
            channel = ChannelModel(
                **{
                    **form_data.model_dump(),
                    "type": type,
                    "name": form_data.name.lower(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_channel = Channel(**channel.model_dump())

            await db.add(new_channel)
            await db.commit()
            return channel

    async def get_channels(self) -> list[ChannelModel]:
        async with get_db() as db:
            channels = await db.query(Channel).all()
            return [ChannelModel.model_validate(channel) for channel in channels]

    async def get_channels_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> list[ChannelModel]:
        channels = await self.get_channels()
        return [
            channel
            for channel in channels
            if channel.user_id == user_id
            or await has_access(user_id, permission, channel.access_control)
        ]

    async def get_channel_by_id(self, id: str) -> Optional[ChannelModel]:
        async with get_db() as db:
            channel = await db.query(Channel).filter(Channel.id == id).first()
            return ChannelModel.model_validate(channel) if channel else None

    async def update_channel_by_id(
        self, id: str, form_data: ChannelForm
    ) -> Optional[ChannelModel]:
        async with get_db() as db:
            channel = await db.query(Channel).filter(Channel.id == id).first()
            if not channel:
                return None

            channel.name = form_data.name
            channel.data = form_data.data
            channel.meta = form_data.meta
            channel.access_control = form_data.access_control
            channel.updated_at = int(time.time_ns())

            await db.commit()
            return ChannelModel.model_validate(channel) if channel else None

    async def delete_channel_by_id(self, id: str):
        async with get_db() as db:
            await db.query(Channel).filter(Channel.id == id).delete()
            await db.commit()
            return True


Channels = ChannelTable()
