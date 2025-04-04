import time
from typing import Optional
import uuid
from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, func
from open_webui.internal.db import Base, get_db
from logging import getLogger

logger = getLogger(__name__)


class MessageMetric(Base):
    __tablename__ = "message_metrics"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    user_domain = Column(Text)
    model = Column(Text)
    completion_tokens = Column(BigInteger)
    prompt_tokens = Column(BigInteger)
    total_tokens = Column(BigInteger)
    created_at = Column(BigInteger)


class MessageMetricsModel(BaseModel):
    id: str
    user_id: str
    user_domain: str
    model: str
    completion_tokens: float
    prompt_tokens: float
    total_tokens: float
    created_at: int


class UsageModel(BaseModel):
    completion_tokens: float
    prompt_tokens: float
    total_tokens: float


class MessageMetricsTable:
    def insert_new_metrics(self, user: dict, model: str, usage: dict):
        with get_db() as db:
            id = str(uuid.uuid4())
            ts = int(time.time_ns())
            tokens = UsageModel(**usage)

            metrics = MessageMetricsModel(
                **{
                    "id": id,
                    "user_id": user.id,
                    "user_domain": user.domain,
                    "model": model,
                    "completion_tokens": tokens.completion_tokens,
                    "prompt_tokens": tokens.prompt_tokens,
                    "total_tokens": tokens.total_tokens,
                    "created_at": ts,
                }
            )

            result = MessageMetric(**metrics.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)

    def get_messages_number(self, domain: Optional[str] = None) -> Optional[int]:
        try:
            with get_db() as db:
                query = db.query(MessageMetric)
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                return query.count()
        except Exception as e:
            logger.error(f"Failed to get messages number: {e}")
            return None

    def get_daily_messages_number(
        self, days: int = 1, domain: Optional[str] = None
    ) -> Optional[int]:
        try:
            with get_db() as db:
                # Get the timestamp for the start of the day 'days' days ago
                start_time = int(time.time()) - (days * 24 * 60 * 60)

                # Build the query to count users active after the start time
                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_time
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)

                return query.count()
        except Exception as e:
            logger.error(f"Failed to get daily messages number: {e}")
            return None

    def get_message_tokens_sum(self, domain: Optional[str] = None) -> Optional[int]:
        try:
            with get_db() as db:
                query = db.query(MessageMetric)
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                result = query.with_entities(
                    func.sum(MessageMetric.total_tokens),
                ).first()
                return round(result[0], 2) if result else 0
        except Exception as e:
            logger.error(f"Failed to get message tokens number: {e}")
            return None

    def get_daily_message_tokens_sum(
        self, days: int = 1, domain: Optional[str] = None
    ) -> Optional[int]:
        try:
            with get_db() as db:
                start_time = int(time.time()) - (days * 24 * 60 * 60)

                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_time
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)

                result = query.with_entities(
                    func.sum(MessageMetric.total_tokens),
                ).first()
                return round(result[0], 2) if result else 0
        except Exception as e:
            logger.error(f"Failed to get message tokens number: {e}")
            return None


MessageMetrics = MessageMetricsTable()
