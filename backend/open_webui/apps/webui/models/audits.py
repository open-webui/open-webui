import logging
from datetime import UTC, datetime, timedelta
from typing import Optional
import uuid

from open_webui.constants import AUDIT_EVENT
from open_webui.apps.webui.internal.db import Base, JSONField, get_db
from open_webui.env import AUDIT_LOG_RETENTION_PERIOD, SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict, TypeAdapter
from sqlalchemy import BigInteger, Column, String

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(BigInteger, nullable=False)
    log_level = Column(String, nullable=False)
    event = Column(String, nullable=False)
    extra = Column(JSONField, nullable=True)
    source_ip = Column(String, nullable=True)
    object_id = Column(String, nullable=True)
    object_type = Column(String, nullable=True)
    admin_id = Column(String, nullable=True)
    admin_api_key = Column(String, nullable=True)
    request_uri = Column(String, nullable=True)
    entry_expiration_timestamp = Column(BigInteger, nullable=True)
    user_agent = Column(String, nullable=True)
    request_info = Column(JSONField, nullable=True)
    response_info = Column(JSONField, nullable=True)


class RequestInfo(BaseModel):
    header: Optional[dict] = None
    body: Optional[dict] = None


class ResponseInfo(BaseModel):
    header: Optional[dict] = None
    body: Optional[dict] = None


class AuditLogModel(BaseModel):
    id: str
    timestamp: int
    log_level: str
    event: AUDIT_EVENT
    extra: Optional[dict] = None
    admin_id: Optional[str] = None
    source_ip: Optional[str] = None
    object_id: Optional[str] = None
    object_type: Optional[str] = None
    admin_api_key: Optional[str] = None
    request_uri: Optional[str] = None
    entry_expiration_timestamp: Optional[int] = None
    user_agent: Optional[str] = None
    request_info: Optional[RequestInfo] = None
    response_info: Optional[ResponseInfo] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogsTable:
    def __init__(self):
        # Example: 'AUDIT_LOG_RETENTION_PERIOD' = 'P30D' (ISO 8601 duration string)
        retention_period_str = AUDIT_LOG_RETENTION_PERIOD
        timedelta_adapter = TypeAdapter(timedelta)
        try:
            self.retention_period = timedelta_adapter.validate_python(
                retention_period_str
            )
        except Exception as e:
            log.exception(
                f"Invalid retention period format: {retention_period_str}, error: {e}"
            )
            self.retention_period = timedelta(days=30)

    def insert_new_log(self, audit_log_data: AuditLogModel) -> Optional[AuditLogModel]:
        with get_db() as db:
            try:
                audit_log = AuditLog(**audit_log_data.model_dump())
                db.add(audit_log)
                db.commit()
                db.refresh(audit_log)
                return AuditLogModel.model_validate(audit_log)
            except Exception as e:
                log.exception(e)
                return None

    def create_log(
        self,
        log_level: str,
        event: AUDIT_EVENT,
        admin_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        object_id: Optional[str] = None,
        object_type: Optional[str] = None,
        admin_api_key: Optional[str] = None,
        request_uri: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_info: Optional[RequestInfo] = None,
        response_info: Optional[ResponseInfo] = None,
        extra: Optional[dict] = None,
    ) -> Optional[AuditLogModel]:
        expiration_datetime = datetime.now(UTC) + self.retention_period
        entry_expiration_timestamp = int(expiration_datetime.timestamp())
        current_time = int(datetime.now(UTC).timestamp())

        audit_log_data = AuditLogModel(
            id=str(uuid.uuid4()),
            timestamp=current_time,
            log_level=log_level,
            event=event,
            extra=extra,
            admin_id=admin_id,
            source_ip=source_ip,
            object_id=object_id,
            object_type=object_type,
            admin_api_key=admin_api_key,
            request_uri=request_uri,
            entry_expiration_timestamp=entry_expiration_timestamp,
            user_agent=user_agent,
            request_info=request_info,
            response_info=response_info,
        )
        return self.insert_new_log(audit_log_data)

    def get_log_by_id(self, id: str) -> Optional[AuditLogModel]:
        with get_db() as db:
            try:
                audit_log = db.query(AuditLog).filter_by(id=id).first()
                return AuditLogModel.model_validate(audit_log) if audit_log else None
            except Exception as e:
                log.exception(e)
                return None

    def get_logs(self, skip: int = 0, limit: int = 100) -> list[AuditLogModel]:
        with get_db() as db:
            try:
                logs = db.query(AuditLog).offset(skip).limit(limit).all()
                return [AuditLogModel.model_validate(log) for log in logs]
            except Exception as e:
                log.exception(e)
                return []

    def get_logs_by_admin_id(
        self, admin_id: str, skip: int = 0, limit: int = 100
    ) -> list[AuditLogModel]:
        with get_db() as db:
            try:
                logs = (
                    db.query(AuditLog)
                    .filter_by(admin_id=admin_id)
                    .offset(skip)
                    .limit(limit)
                    .all()
                )
                return [AuditLogModel.model_validate(log) for log in logs]
            except Exception as e:
                log.exception(e)
                return []


AuditLogs = AuditLogsTable()
