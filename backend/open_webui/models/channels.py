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
# Channel DB Schema
####################


class Channel(Base):
    __tablename__ = "channel"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ChannelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
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
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class ChannelTable:
    def insert_new_channel(
        self, form_data: ChannelForm, user_id: str
    ) -> Optional[ChannelModel]:
        with get_db() as db:
            new_channel = Channel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            db.add(new_channel)
            db.commit()
            return new_channel

    def get_channels(self) -> list[ChannelModel]:
        with get_db() as db:
            channels = db.query(Channel).all()
            return [ChannelModel.model_validate(channel) for channel in channels]

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
            channel.updated_at = int(time.time())

            db.commit()
            return ChannelModel.model_validate(channel) if channel else None

    def delete_channel_by_id(self, id: str):
        with get_db() as db:
            db.query(Channel).filter(Channel.id == id).delete()
            db.commit()
            return True


Channels = ChannelTable()
