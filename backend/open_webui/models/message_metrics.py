import time
from typing import Optional
import uuid
from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, func
from open_webui.internal.db import Base, get_db
from open_webui.models.users import User
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
            ts = int(time.time())
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

    def get_domains(self) -> list[str]:
        try:
            with get_db() as db:
                domains = db.query(MessageMetric.user_domain).distinct().all()
                return [domain[0] for domain in domains if domain[0]]
        except Exception as e:
            logger.error(f"Failed to get domains: {e}")
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

                # Build the query to count messages for the current day
                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_time,
                    MessageMetric.created_at < end_time,
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

                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_time,
                    MessageMetric.created_at < end_time,
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

                with get_db() as db:
                    query = db.query(MessageMetric).filter(
                        MessageMetric.created_at >= start_time,
                        MessageMetric.created_at < end_time,
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

                with get_db() as db:
                    query = db.query(MessageMetric).filter(
                        MessageMetric.created_at >= start_time,
                        MessageMetric.created_at < end_time,
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

    def get_range_metrics(
        self,
        start_timestamp: int,
        end_timestamp: int,
        domain: str = None,
        model: str = None,
    ) -> dict:
        """Get message metrics for a specific date range"""
        try:
            with get_db() as db:
                # Build query with range filters
                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_timestamp,
                    MessageMetric.created_at < end_timestamp,
                )

                # Apply domain filter if specified
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)

                # Apply model filter if specified
                if model:
                    query = query.filter(MessageMetric.model == model)

                # Count total prompts
                total_prompts = query.count()

                # Sum total tokens
                tokens_sum = query.with_entities(
                    func.sum(MessageMetric.total_tokens)
                ).first()

                total_tokens = (
                    round(tokens_sum[0], 2) if tokens_sum and tokens_sum[0] else 0
                )

                return {"total_prompts": total_prompts, "total_tokens": total_tokens}
        except Exception as e:
            logger.error(f"Failed to get range metrics: {e}")
            return {"total_prompts": 0, "total_tokens": 0}

    def get_model_token_usage(
        self, start_timestamp: int, end_timestamp: int, domain: str = None
    ) -> list[dict]:
        """Get token usage by model for a specific date range"""
        try:
            with get_db() as db:
                # Base query with filters
                query = (
                    db.query(
                        MessageMetric.model,
                        func.sum(MessageMetric.total_tokens).label("tokens"),
                    )
                    .filter(
                        MessageMetric.created_at >= start_timestamp,
                        MessageMetric.created_at < end_timestamp,
                    )
                    .group_by(MessageMetric.model)
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)

                # Execute query and process results
                results = query.all()

                # Format the results as a list of dictionaries
                model_usage = [
                    {"model": model, "tokens": round(tokens, 2) if tokens else 0}
                    for model, tokens in results
                    if model  # Filter out None models
                ]

                return model_usage
        except Exception as e:
            logger.error(f"Failed to get model token usage: {e}")
            return []

    def get_historical_daily_data(
        self,
        start_timestamp: int,
        end_timestamp: int,
        domain: str = None,
        model: str = None,
    ) -> list[dict]:
        """Get historical daily prompt data for a specific date range"""
        try:
            result = []

            # Get daily data for each day in the range
            current_day = start_timestamp
            while current_day < end_timestamp:
                next_day = current_day + 86400  # add one day in seconds

                with get_db() as db:
                    query = db.query(MessageMetric).filter(
                        MessageMetric.created_at >= current_day,
                        MessageMetric.created_at < next_day,
                    )

                    if domain:
                        query = query.filter(MessageMetric.user_domain == domain)

                    if model:
                        query = query.filter(MessageMetric.model == model)

                    count = query.count()

                    day_str = time.strftime("%Y-%m-%d", time.localtime(current_day))
                    result.append({"date": day_str, "prompts": count})

                current_day = next_day

            return result
        except Exception as e:
            logger.error(f"Failed to get historical daily data: {e}")
            return []

    def get_historical_daily_tokens(
        self,
        start_timestamp: int,
        end_timestamp: int,
        domain: str = None,
        model: str = None,
    ) -> list[dict]:
        """Get historical daily token usage data for a specific date range"""
        try:
            result = []

            # Get daily data for each day in the range
            current_day = start_timestamp
            while current_day < end_timestamp:
                next_day = current_day + 86400  # add one day in seconds

                with get_db() as db:
                    query = db.query(func.sum(MessageMetric.total_tokens)).filter(
                        MessageMetric.created_at >= current_day,
                        MessageMetric.created_at < next_day,
                    )

                    if domain:
                        query = query.filter(MessageMetric.user_domain == domain)

                    if model:
                        query = query.filter(MessageMetric.model == model)

                    tokens_sum = query.first()
                    tokens_count = (
                        round(tokens_sum[0], 2) if tokens_sum and tokens_sum[0] else 0
                    )

                    day_str = time.strftime("%Y-%m-%d", time.localtime(current_day))
                    result.append({"date": day_str, "tokens": tokens_count})

                current_day = next_day

            return result
        except Exception as e:
            logger.error(f"Failed to get historical daily tokens: {e}")
            return []

    # This function is here and not with Users model since the values needed are in the message metrics table.
    # Values are grouped by date and user_id without sql due to limitations with timestamps and being database agnostic.
    def get_historical_daily_users(
        self, days: int = 7, domain: Optional[str] = None, model: Optional[str] = None
    ) -> list[dict]:
        try:
            current_time = int(time.time())
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )
            start_time = today_midnight - (days * 24 * 60 * 60)
            end_time = today_midnight + (24 * 60 * 60)

            with get_db() as db:

                query = db.query(
                    MessageMetric.user_id, MessageMetric.created_at
                ).filter(
                    MessageMetric.created_at >= start_time,
                    MessageMetric.created_at < end_time,
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                if model:
                    query = query.filter(MessageMetric.model == model)

                results = query.all()

                # Group user_ids by date string
                day_to_users = {}
                for user_id, created_at in results:
                    date_str = time.strftime("%Y-%m-%d", time.localtime(created_at))
                    if date_str not in day_to_users:
                        day_to_users[date_str] = set()
                    day_to_users[date_str].add(user_id)

                output = []
                for day in range(days):
                    day_start = today_midnight - (day * 24 * 60 * 60)
                    date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                    count = len(day_to_users.get(date_str, set()))
                    output.append({"date": date_str, "count": count})

                # Return in chronological order (oldest to newest)
                return sorted(output, key=lambda x: x["date"])
        except Exception as e:
            logger.error(f"Failed to get historical daily user counts: {e}")
            # Fallback: return zeros for each day
            fallback = []
            current_time = int(time.time())
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )
            for day in range(days):
                day_start = today_midnight - (day * (24 * 60 * 60))
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                fallback.append({"date": date_str, "count": 0})
            return sorted(fallback, key=lambda x: x["date"])


MessageMetrics = MessageMetricsTable()
