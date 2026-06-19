import json
import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Integer, String, Text, select, update
from sqlalchemy.ext.asyncio import AsyncSession

####################
# Webhook Delivery Log DB Schema
####################


class WebhookDeliveryLog(Base):
    __tablename__ = 'webhook_delivery_log'
    id = Column(Text, primary_key=True, unique=True)
    url = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    event_action = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='pending')  # pending, success, failed
    retry_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class WebhookDeliveryLogModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    payload: dict
    event_action: Optional[str] = None
    status: str
    retry_count: int
    last_attempt_at: Optional[int] = None
    created_at: int


####################
# Webhook Delivery Logs Table
####################


class WebhookDeliveryLogsTable:
    async def insert_new_log(
        self, id: str, url: str, payload: dict, event_action: Optional[str], db: Optional[AsyncSession] = None
    ) -> Optional[WebhookDeliveryLogModel]:
        async with get_async_db_context(db) as db:
            log_entry = WebhookDeliveryLogModel(
                id=id,
                url=url,
                payload=payload,
                event_action=event_action,
                status='pending',
                retry_count=0,
                last_attempt_at=None,
                created_at=int(time.time_ns()),
            )
            db.add(WebhookDeliveryLog(**log_entry.model_dump()))
            await db.commit()
            return log_entry

    async def update_log_status(
        self, id: str, status: str, retry_count: int, db: Optional[AsyncSession] = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(WebhookDeliveryLog).filter(WebhookDeliveryLog.id == id))
            log_entry = result.scalars().first()
            if log_entry:
                log_entry.status = status
                log_entry.retry_count = retry_count
                log_entry.last_attempt_at = int(time.time_ns())
                await db.commit()
                return True
            return False

    async def get_logs(
        self, skip: int = 0, limit: int = 50, db: Optional[AsyncSession] = None
    ) -> list[WebhookDeliveryLogModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(WebhookDeliveryLog).order_by(WebhookDeliveryLog.created_at.desc()).offset(skip).limit(limit)
            )
            logs = result.scalars().all()
            return [WebhookDeliveryLogModel.model_validate(log) for log in logs]

    async def get_failed_logs_for_retry(
        self, max_retries: int = 3, limit: int = 50, db: Optional[AsyncSession] = None
    ) -> list[WebhookDeliveryLogModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(WebhookDeliveryLog)
                .filter(WebhookDeliveryLog.status == 'failed')
                .filter(WebhookDeliveryLog.retry_count < max_retries)
                .order_by(WebhookDeliveryLog.created_at.asc())
                .limit(limit)
            )
            logs = result.scalars().all()
            return [WebhookDeliveryLogModel.model_validate(log) for log in logs]

    async def get_log_by_id(
        self, id: str, db: Optional[AsyncSession] = None
    ) -> Optional[WebhookDeliveryLogModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(WebhookDeliveryLog).filter(WebhookDeliveryLog.id == id))
            log_entry = result.scalars().first()
            if log_entry:
                return WebhookDeliveryLogModel.model_validate(log_entry)
            return None


WebhookDeliveryLogs = WebhookDeliveryLogsTable()
