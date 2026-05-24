"""
SupervisionCallback — stores inbound callbacks from the Swept Workbench
supervision pipeline. Workbench POSTs here when a SupervisionEvent it
previously received from Open WebUI transitions to a terminal evaluation
status (completed / failed).

Inserts are idempotent on `event_id` so Workbench's retry_on policy doesn't
duplicate rows. V1 just persists; nothing is surfaced in the chat UI yet.
"""

import time
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Index, JSON, Text

from open_webui.internal.db import Base


####################
# SupervisionCallback DB Schema
####################


class SupervisionCallback(Base):
    __tablename__ = 'supervision_callback'

    id = Column(Text, primary_key=True, unique=True)
    # Uniqueness on event_id is enforced by the
    # ix_supervision_callback_event_id index declared in __table_args__
    # below (matches the migration); don't add `unique=True` here too,
    # which would generate a duplicate constraint on create_all.
    event_id = Column(Text, nullable=False)
    supervision_session_id = Column(Text, nullable=False)
    agent_name = Column(Text, nullable=False)
    evaluation_status = Column(Text, nullable=False)
    external_message_id = Column(Text, nullable=True)
    external_chat_id = Column(Text, nullable=True)
    evaluated_at = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)
    received_at = Column(BigInteger, nullable=False)

    # Indexes are materialized by migration 8a2b4c6e1d3f; declare them on
    # the ORM model too so SQLAlchemy's metadata matches the live schema
    # (matters for tools that introspect Base.metadata, e.g. autogenerate
    # diffs and `create_all` in test fixtures).
    __table_args__ = (
        Index('ix_supervision_callback_event_id', 'event_id', unique=True),
        Index('ix_supervision_callback_external_chat_id', 'external_chat_id'),
    )


class SupervisionCallbackModel(BaseModel):
    id: str
    event_id: str
    supervision_session_id: str
    agent_name: str
    evaluation_status: str
    external_message_id: Optional[str] = None
    external_chat_id: Optional[str] = None
    evaluated_at: Optional[str] = None
    raw: Optional[dict] = None
    received_at: int

    model_config = ConfigDict(from_attributes=True)


def now_seconds() -> int:
    return int(time.time())
