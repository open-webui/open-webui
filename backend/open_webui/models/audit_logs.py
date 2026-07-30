import logging
from typing import Any, Optional

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Boolean, Column, Index, Integer, Text

log = logging.getLogger(__name__)


class AuditLog(Base):
    __tablename__ = 'audit_log'

    id = Column(Text, primary_key=True)
    created_at = Column(BigInteger, nullable=False, index=True)
    user_id = Column(Text, nullable=True, index=True)
    user_snapshot = Column(JSON, nullable=True)
    audit_level = Column(Text, nullable=False)
    verb = Column(Text, nullable=False)
    request_path = Column(Text, nullable=False)
    request_uri = Column(Text, nullable=False)
    response_status_code = Column(Integer, nullable=True)
    source_ip = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_object = Column(Text, nullable=True)
    response_object = Column(Text, nullable=True)
    response_id = Column(Text, nullable=True)
    response_model = Column(Text, nullable=True)
    response_finish_reasons = Column(JSON, nullable=True)
    request_truncated = Column(Boolean, nullable=True)
    response_truncated = Column(Boolean, nullable=True)
    request_model = Column(Text, nullable=True)
    request_extra = Column(JSON, nullable=True)
    request_skill_ids = Column(JSON, nullable=True)
    request_tool_ids = Column(JSON, nullable=True)
    request_response_format = Column(JSON, nullable=True)
    request_extra_body = Column(JSON, nullable=True)
    request_system_messages = Column(JSON, nullable=True)
    request_user_messages = Column(JSON, nullable=True)

    __table_args__ = (
        Index('audit_log_path_created_idx', 'request_path', 'created_at'),
        Index('audit_log_user_created_idx', 'user_id', 'created_at'),
        Index('audit_log_status_created_idx', 'response_status_code', 'created_at'),
    )


class AuditLogCreate(BaseModel):
    id: str
    created_at: int
    user_id: Optional[str] = None
    user_snapshot: Optional[dict] = None
    audit_level: str
    verb: str
    request_path: str
    request_uri: str
    response_status_code: Optional[int] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_object: Optional[str] = None
    response_object: Optional[str] = None
    response_id: Optional[str] = None
    response_model: Optional[str] = None
    response_finish_reasons: Optional[list[Any]] = None
    request_truncated: Optional[bool] = None
    response_truncated: Optional[bool] = None
    request_model: Optional[str] = None
    request_extra: Optional[Any] = None
    request_skill_ids: Optional[Any] = None
    request_tool_ids: Optional[Any] = None
    request_response_format: Optional[Any] = None
    request_extra_body: Optional[Any] = None
    request_system_messages: Optional[list[Any]] = None
    request_user_messages: Optional[list[Any]] = None

    model_config = ConfigDict(extra='forbid')


class AuditLogTable:
    async def insert(self, entry: AuditLogCreate) -> bool:
        try:
            async with get_async_db_context() as session:
                session.add(AuditLog(**entry.model_dump()))
                await session.commit()
            return True
        except Exception as e:
            log.error(f'Failed to persist audit log entry: {e}')
            return False


AuditLogs = AuditLogTable()
