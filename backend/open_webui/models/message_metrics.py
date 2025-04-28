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

    def get_used_models(self) -> list[str]:
        try:
            with get_db() as db:
                models = db.query(MessageMetric.model).distinct().all()
                return [model[0] for model in models if model[0]]
        except Exception as e:
            logger.error(f"Failed to get used models: {e}")
            return []

    def get_messages_number(
        self, domain: Optional[str] = None, model: Optional[str] = None
    ) -> Optional[int]:
        try:
            with get_db() as db:
                query = db.query(MessageMetric)
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                if model:
                    query = query.filter(MessageMetric.model == model)
                return query.count()
        except Exception as e:
            logger.error(f"Failed to get messages number: {e}")
            return 0

    def get_daily_messages_number(
        self, days: int = 1, domain: Optional[str] = None, model: Optional[str] = None
    ) -> Optional[int]:
        try:
            with get_db() as db:
                # Use the same time calculation as historical data for consistency
                current_time = int(time.time())
                end_time = current_time
                start_time = end_time - (24 * 60 * 60)

                # Convert to nanoseconds for consistency with historical queries
                start_time_ns = start_time * 1_000_000_000
                end_time_ns = end_time * 1_000_000_000

                # Build the query to count messages for the current day
                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_time_ns,
                    MessageMetric.created_at < end_time_ns,
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                if model:
                    query = query.filter(MessageMetric.model == model)

                return query.count()
        except Exception as e:
            logger.error(f"Failed to get daily messages number: {e}")
            return 0

    def get_message_tokens_sum(self, domain: Optional[str] = None) -> Optional[int]:
        try:
            with get_db() as db:
                query = db.query(MessageMetric)
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                result = query.with_entities(
                    func.sum(MessageMetric.total_tokens),
                ).first()
                return round(result[0], 2) if result and result[0] else 0
        except Exception as e:
            logger.error(f"Failed to get message tokens number: {e}")
            return 0  # Return 0 instead of None

    def get_daily_message_tokens_sum(
        self, days: int = 1, domain: Optional[str] = None
    ) -> Optional[int]:
        try:
            with get_db() as db:
                # Use the same time calculation as historical data for consistency
                current_time = int(time.time())
                end_time = current_time
                start_time = end_time - (24 * 60 * 60)

                # Convert to nanoseconds for consistency with historical queries
                start_time_ns = start_time * 1_000_000_000
                end_time_ns = end_time * 1_000_000_000

                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_time_ns,
                    MessageMetric.created_at < end_time_ns,
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)

                result = query.with_entities(
                    func.sum(MessageMetric.total_tokens),
                ).first()

                return round(result[0], 2) if result and result[0] else 0
        except Exception as e:
            logger.error(f"Failed to get daily message tokens number: {e}")
            return 0  # Return 0 instead of None

    def get_historical_messages_data(
        self, days: int = 7, domain: Optional[str] = None, model: Optional[str] = None
    ) -> list[dict]:
        try:
            result = []
            current_time = int(time.time())

            # Calculate today's date at midnight for proper day boundary
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )

            # Generate all date strings first to ensure no gaps
            date_strings = []
            dates_timestamps = []
            for day in range(days):
                # Calculate day start (midnight) for each day in the past
                day_start = today_midnight - (day * 24 * 60 * 60)
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                date_strings.append(date_str)
                dates_timestamps.append(day_start)

            # Sort date strings to ensure chronological order
            date_pairs = sorted(zip(date_strings, dates_timestamps))
            date_strings = [pair[0] for pair in date_pairs]
            dates_timestamps = [pair[1] for pair in date_pairs]

            # Process each day individually
            for i, (date_str, day_start) in enumerate(
                zip(date_strings, dates_timestamps)
            ):
                # Calculate day boundaries (midnight to midnight)
                start_time = day_start
                end_time = start_time + (24 * 60 * 60)

                # Convert seconds to nanoseconds for comparison with created_at
                start_time_ns = start_time * 1_000_000_000
                end_time_ns = end_time * 1_000_000_000

                with get_db() as db:
                    query = db.query(MessageMetric).filter(
                        MessageMetric.created_at >= start_time_ns,
                        MessageMetric.created_at < end_time_ns,
                    )

                    if domain:
                        query = query.filter(MessageMetric.user_domain == domain)
                    if model:
                        query = query.filter(MessageMetric.model == model)

                    count = query.count()

                    result.append({"date": date_str, "count": count})

            # Return in chronological order
            return result
        except Exception as e:
            logger.error(f"Failed to get historical messages data: {e}")
            # Generate continuous date range as fallback
            fallback = []
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )

            for day in range(days):
                day_start = today_midnight - (day * 24 * 60 * 60)
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                fallback.append({"date": date_str, "count": 0})

            return sorted(fallback, key=lambda x: x["date"])

    def get_historical_tokens_data(
        self, days: int = 7, domain: Optional[str] = None
    ) -> list[dict]:
        try:
            result = []
            current_time = int(time.time())

            # Calculate today's date at midnight for proper day boundary
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )

            # Generate all date strings first to ensure no gaps
            date_strings = []
            dates_timestamps = []
            for day in range(days):
                # Calculate day start (midnight) for each day in the past
                day_start = today_midnight - (day * 24 * 60 * 60)
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                date_strings.append(date_str)
                dates_timestamps.append(day_start)

            # Sort date strings to ensure chronological order
            date_pairs = sorted(zip(date_strings, dates_timestamps))
            date_strings = [pair[0] for pair in date_pairs]
            dates_timestamps = [pair[1] for pair in date_pairs]

            # Process each day individually
            for i, (date_str, day_start) in enumerate(
                zip(date_strings, dates_timestamps)
            ):
                # Calculate day boundaries (midnight to midnight)
                start_time = day_start
                end_time = start_time + (24 * 60 * 60)

                # Convert seconds to nanoseconds for comparison with created_at
                start_time_ns = start_time * 1_000_000_000
                end_time_ns = end_time * 1_000_000_000

                with get_db() as db:
                    query = db.query(MessageMetric).filter(
                        MessageMetric.created_at >= start_time_ns,
                        MessageMetric.created_at < end_time_ns,
                    )

                    if domain:
                        query = query.filter(MessageMetric.user_domain == domain)

                    # Sum tokens for this day
                    tokens_sum = query.with_entities(
                        func.sum(MessageMetric.total_tokens),
                    ).first()

                    count = (
                        round(tokens_sum[0], 2) if tokens_sum and tokens_sum[0] else 0
                    )

                    result.append({"date": date_str, "count": count})

            # Return in chronological order
            return result
        except Exception as e:
            logger.error(f"Failed to get historical tokens data: {e}")
            # Generate continuous date range as fallback
            fallback = []
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )

            for day in range(days):
                day_start = today_midnight - (day * 24 * 60 * 60)
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                fallback.append({"date": date_str, "count": 0})

            return sorted(fallback, key=lambda x: x["date"])


MessageMetrics = MessageMetricsTable()
