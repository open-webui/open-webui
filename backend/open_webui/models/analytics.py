"""
Token Analytics Models for "Wrapped" Feature

This module provides database models and helper classes for tracking token usage
analytics per conversation, per day, and per model. This data is used to generate
"Spotify Wrapped" style analytics for users and site-wide statistics.

Tables:
- ConversationTokenUsage: Tracks tokens per chat conversation
- DailyTokenUsage: Aggregates daily token stats per user for heatmaps
- ModelTokenUsage: Tracks usage per model per user for breakdowns
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Index, func, desc
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# SQLAlchemy Models
####################


class ConversationTokenUsage(Base):
    """
    Tracks token usage for each conversation/chat.
    Updated after each message exchange.
    """
    __tablename__ = "conversation_token_usage"

    id = Column(String, primary_key=True)  # UUID
    chat_id = Column(String, index=True, unique=True)  # References chat.id
    user_id = Column(String, index=True)  # References user.id
    model_id = Column(String)  # Primary model used in conversation

    # Cumulative totals for the conversation
    total_input_tokens = Column(BigInteger, default=0)
    total_output_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)

    # Last message stats (for real-time display)
    last_input_tokens = Column(BigInteger, default=0)
    last_output_tokens = Column(BigInteger, default=0)

    # Metadata
    message_count = Column(Integer, default=0)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        Index("conv_token_user_idx", "user_id"),
        Index("conv_token_chat_idx", "chat_id"),
        Index("conv_token_total_idx", "total_tokens"),  # For "longest chats" queries
    )


class DailyTokenUsage(Base):
    """
    Aggregated daily token usage per user.
    Used for activity heatmaps and daily trends.
    """
    __tablename__ = "daily_token_usage"

    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, index=True)  # References user.id
    date = Column(String, index=True)  # YYYY-MM-DD format

    # Token counts
    total_input_tokens = Column(BigInteger, default=0)
    total_output_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)

    # Activity metrics
    conversation_count = Column(Integer, default=0)  # Unique chats active that day
    message_count = Column(Integer, default=0)  # Total messages sent

    # Timestamps
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        Index("daily_user_date_idx", "user_id", "date", unique=True),
        Index("daily_date_idx", "date"),
        Index("daily_total_idx", "total_tokens"),
    )


class ModelTokenUsage(Base):
    """
    Tracks per-model token usage.
    Supports both per-user and global (user_id=NULL) aggregations.
    """
    __tablename__ = "model_token_usage"

    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, index=True, nullable=True)  # NULL = global aggregate
    model_id = Column(String, index=True)

    # Token counts
    total_input_tokens = Column(BigInteger, default=0)
    total_output_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)

    # Usage counts
    conversation_count = Column(Integer, default=0)
    message_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        Index("model_user_model_idx", "user_id", "model_id", unique=True),
        Index("model_total_idx", "total_tokens"),
    )


####################
# Pydantic Response Models
####################


class ConversationTokenUsageResponse(BaseModel):
    """Response model for conversation token stats"""
    model_config = ConfigDict(from_attributes=True)

    chat_id: str
    user_id: str
    model_id: Optional[str] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    last_input_tokens: int = 0
    last_output_tokens: int = 0
    message_count: int = 0
    created_at: int
    updated_at: int


class DailyTokenUsageResponse(BaseModel):
    """Response model for daily token stats"""
    model_config = ConfigDict(from_attributes=True)

    date: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    conversation_count: int = 0
    message_count: int = 0


class HeatmapDataPoint(BaseModel):
    """Single data point for activity heatmap"""
    date: str
    tokens: int
    level: int  # 0-4 scale for color intensity


class HeatmapResponse(BaseModel):
    """Response model for heatmap data"""
    year: int
    data: List[HeatmapDataPoint]
    max_tokens: int
    total_days_active: int


class ModelUsageResponse(BaseModel):
    """Response model for model usage breakdown"""
    model_id: str
    model_name: Optional[str] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    conversation_count: int = 0
    message_count: int = 0
    percentage: float = 0.0


class TopChatResponse(BaseModel):
    """Response model for top chats by tokens"""
    chat_id: str
    title: Optional[str] = None
    model_id: Optional[str] = None
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    message_count: int


class WrappedSummaryResponse(BaseModel):
    """Response model for wrapped summary stats"""
    year: int
    total_conversations: int = 0
    total_messages: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    days_active: int = 0
    most_active_day: Optional[Dict] = None
    favorite_model: Optional[Dict] = None
    top_chats: List[TopChatResponse] = []


class GlobalWrappedResponse(BaseModel):
    """Response model for site-wide wrapped stats"""
    year: int
    total_users_active: int = 0
    total_conversations: int = 0
    total_messages: int = 0
    total_tokens: int = 0
    top_models: List[ModelUsageResponse] = []
    busiest_day: Optional[Dict] = None


####################
# Analytics Table Class
####################


class AnalyticsTable:
    """
    Database operations for token analytics.
    Handles conversation, daily, and model-level token tracking.
    """

    # ==================
    # Conversation Token Usage
    # ==================

    def get_conversation_token_usage(self, chat_id: str) -> Optional[ConversationTokenUsageResponse]:
        """Get token usage stats for a specific conversation"""
        log.info(f"📊 [Analytics.get_conversation_token_usage] Looking up chat_id={chat_id}")
        try:
            with get_db() as db:
                record = db.query(ConversationTokenUsage).filter_by(chat_id=chat_id).first()
                log.info(f"📊 [Analytics.get_conversation_token_usage] Query result: {record}")
                if record:
                    log.info(f"📊 [Analytics.get_conversation_token_usage] Found record with total_tokens={record.total_tokens}")
                    return ConversationTokenUsageResponse.model_validate(record)
                log.info(f"📊 [Analytics.get_conversation_token_usage] No record found for chat_id={chat_id}")
                return None
        except Exception as e:
            log.error(f"📊 [Analytics.get_conversation_token_usage] Error getting conversation token usage for chat {chat_id}: {e}", exc_info=True)
            return None

    def update_conversation_token_usage(
        self,
        chat_id: str,
        user_id: str,
        model_id: str,
        token_in: int,
        token_out: int,
        token_total: int
    ) -> Optional[ConversationTokenUsageResponse]:
        """
        Update or create conversation token usage record.
        Called after each message in a chat.
        """
        log.info(f"📊 [Analytics.update_conversation] Starting: chat_id={chat_id}, user_id={user_id}, model_id={model_id}")
        log.info(f"📊 [Analytics.update_conversation] Tokens: in={token_in}, out={token_out}, total={token_total}")
        try:
            with get_db() as db:
                log.info(f"📊 [Analytics.update_conversation] Got DB session")
                record = db.query(ConversationTokenUsage).filter_by(chat_id=chat_id).first()
                now = int(time.time())
                log.info(f"📊 [Analytics.update_conversation] Existing record: {record}")

                if record:
                    # Update existing record
                    log.info(f"📊 [Analytics.update_conversation] Updating existing record")
                    record.total_input_tokens += token_in
                    record.total_output_tokens += token_out
                    record.total_tokens += token_total
                    record.last_input_tokens = token_in
                    record.last_output_tokens = token_out
                    record.message_count += 1
                    record.updated_at = now
                    # Update model if changed
                    if model_id:
                        record.model_id = model_id
                else:
                    # Create new record
                    log.info(f"📊 [Analytics.update_conversation] Creating new record")
                    record = ConversationTokenUsage(
                        id=str(uuid.uuid4()),
                        chat_id=chat_id,
                        user_id=user_id,
                        model_id=model_id,
                        total_input_tokens=token_in,
                        total_output_tokens=token_out,
                        total_tokens=token_total,
                        last_input_tokens=token_in,
                        last_output_tokens=token_out,
                        message_count=1,
                        created_at=now,
                        updated_at=now
                    )
                    db.add(record)

                log.info(f"📊 [Analytics.update_conversation] Committing...")
                db.commit()
                db.refresh(record)
                log.info(f"📊 [Analytics.update_conversation] SUCCESS! total_tokens now={record.total_tokens}")
                return ConversationTokenUsageResponse.model_validate(record)
        except Exception as e:
            log.error(f"📊 [Analytics.update_conversation] ERROR: {e}", exc_info=True)
            return None

    def get_top_chats_by_user(
        self,
        user_id: str,
        year: Optional[int] = None,
        limit: int = 10
    ) -> List[ConversationTokenUsageResponse]:
        """Get user's top conversations by total token count"""
        try:
            with get_db() as db:
                query = db.query(ConversationTokenUsage).filter_by(user_id=user_id)

                # Optional year filter
                if year:
                    start_ts = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
                    end_ts = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp())
                    query = query.filter(
                        ConversationTokenUsage.created_at >= start_ts,
                        ConversationTokenUsage.created_at < end_ts
                    )

                records = query.order_by(desc(ConversationTokenUsage.total_tokens)).limit(limit).all()
                return [ConversationTokenUsageResponse.model_validate(r) for r in records]
        except Exception as e:
            log.error(f"Error getting top chats for user {user_id}: {e}")
            return []

    # ==================
    # Daily Token Usage
    # ==================

    def update_daily_token_usage(
        self,
        user_id: str,
        token_in: int,
        token_out: int,
        token_total: int,
        chat_id: Optional[str] = None
    ) -> bool:
        """
        Update daily token aggregation for a user.
        Called after each message.
        """
        try:
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            now = int(time.time())

            with get_db() as db:
                record = db.query(DailyTokenUsage).filter_by(
                    user_id=user_id,
                    date=today
                ).first()

                if record:
                    record.total_input_tokens += token_in
                    record.total_output_tokens += token_out
                    record.total_tokens += token_total
                    record.message_count += 1
                    record.updated_at = now
                    # Increment conversation_count only if it's a new chat for today
                    # This is tracked separately in update_conversation_token_usage
                else:
                    record = DailyTokenUsage(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        date=today,
                        total_input_tokens=token_in,
                        total_output_tokens=token_out,
                        total_tokens=token_total,
                        conversation_count=1,
                        message_count=1,
                        created_at=now,
                        updated_at=now
                    )
                    db.add(record)

                db.commit()
                log.debug(f"Updated daily token usage for user {user_id} on {today}")
                return True
        except Exception as e:
            log.error(f"Error updating daily token usage for user {user_id}: {e}")
            return False

    def get_heatmap_data(
        self,
        user_id: str,
        year: Optional[int] = None
    ) -> HeatmapResponse:
        """
        Get daily token usage data for heatmap visualization.
        Returns all days of the specified year with token counts.
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        try:
            with get_db() as db:
                # Query all daily records for the year
                year_start = f"{year}-01-01"
                year_end = f"{year}-12-31"

                records = db.query(DailyTokenUsage).filter(
                    DailyTokenUsage.user_id == user_id,
                    DailyTokenUsage.date >= year_start,
                    DailyTokenUsage.date <= year_end
                ).all()

                # Build date -> tokens map
                date_tokens = {r.date: r.total_tokens for r in records}
                max_tokens = max(date_tokens.values()) if date_tokens else 0

                # Calculate levels (0-4 scale)
                def calculate_level(tokens: int) -> int:
                    if tokens == 0:
                        return 0
                    if max_tokens == 0:
                        return 0
                    # Quartile-based levels
                    ratio = tokens / max_tokens
                    if ratio < 0.25:
                        return 1
                    elif ratio < 0.5:
                        return 2
                    elif ratio < 0.75:
                        return 3
                    else:
                        return 4

                # Generate data points for all days in the year
                data_points = []
                current_date = datetime(year, 1, 1, tzinfo=timezone.utc)
                end_date = datetime(year, 12, 31, tzinfo=timezone.utc)

                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    tokens = date_tokens.get(date_str, 0)
                    data_points.append(HeatmapDataPoint(
                        date=date_str,
                        tokens=tokens,
                        level=calculate_level(tokens)
                    ))
                    current_date = current_date.replace(day=current_date.day + 1) if current_date.day < 28 else \
                                   (current_date + __import__('datetime').timedelta(days=1))

                # Fix the date iteration using timedelta properly
                from datetime import timedelta
                data_points = []
                current_date = datetime(year, 1, 1, tzinfo=timezone.utc)
                end_date = datetime(year, 12, 31, tzinfo=timezone.utc)

                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    tokens = date_tokens.get(date_str, 0)
                    data_points.append(HeatmapDataPoint(
                        date=date_str,
                        tokens=tokens,
                        level=calculate_level(tokens)
                    ))
                    current_date += timedelta(days=1)

                return HeatmapResponse(
                    year=year,
                    data=data_points,
                    max_tokens=max_tokens,
                    total_days_active=len([d for d in data_points if d.tokens > 0])
                )
        except Exception as e:
            log.error(f"Error getting heatmap data for user {user_id}: {e}")
            return HeatmapResponse(year=year, data=[], max_tokens=0, total_days_active=0)

    def get_most_active_day(
        self,
        user_id: str,
        year: Optional[int] = None
    ) -> Optional[Dict]:
        """Get the user's most active day by token count"""
        if year is None:
            year = datetime.now(timezone.utc).year

        try:
            with get_db() as db:
                year_start = f"{year}-01-01"
                year_end = f"{year}-12-31"

                record = db.query(DailyTokenUsage).filter(
                    DailyTokenUsage.user_id == user_id,
                    DailyTokenUsage.date >= year_start,
                    DailyTokenUsage.date <= year_end
                ).order_by(desc(DailyTokenUsage.total_tokens)).first()

                if record:
                    # Parse date to get day of week
                    date_obj = datetime.strptime(record.date, '%Y-%m-%d')
                    return {
                        "date": record.date,
                        "tokens": record.total_tokens,
                        "messages": record.message_count,
                        "day_of_week": date_obj.strftime('%A')
                    }
                return None
        except Exception as e:
            log.error(f"Error getting most active day for user {user_id}: {e}")
            return None

    # ==================
    # Model Token Usage
    # ==================

    def update_model_token_usage(
        self,
        user_id: Optional[str],
        model_id: str,
        token_in: int,
        token_out: int,
        token_total: int
    ) -> bool:
        """
        Update model token usage.
        Updates both per-user and global (user_id=None) records.
        """
        try:
            now = int(time.time())

            with get_db() as db:
                # Update user-specific record
                if user_id:
                    user_record = db.query(ModelTokenUsage).filter_by(
                        user_id=user_id,
                        model_id=model_id
                    ).first()

                    if user_record:
                        user_record.total_input_tokens += token_in
                        user_record.total_output_tokens += token_out
                        user_record.total_tokens += token_total
                        user_record.message_count += 1
                        user_record.updated_at = now
                    else:
                        user_record = ModelTokenUsage(
                            id=str(uuid.uuid4()),
                            user_id=user_id,
                            model_id=model_id,
                            total_input_tokens=token_in,
                            total_output_tokens=token_out,
                            total_tokens=token_total,
                            conversation_count=1,
                            message_count=1,
                            created_at=now,
                            updated_at=now
                        )
                        db.add(user_record)

                # Update global record (user_id=None)
                global_record = db.query(ModelTokenUsage).filter_by(
                    user_id=None,
                    model_id=model_id
                ).first()

                if global_record:
                    global_record.total_input_tokens += token_in
                    global_record.total_output_tokens += token_out
                    global_record.total_tokens += token_total
                    global_record.message_count += 1
                    global_record.updated_at = now
                else:
                    global_record = ModelTokenUsage(
                        id=str(uuid.uuid4()),
                        user_id=None,
                        model_id=model_id,
                        total_input_tokens=token_in,
                        total_output_tokens=token_out,
                        total_tokens=token_total,
                        conversation_count=1,
                        message_count=1,
                        created_at=now,
                        updated_at=now
                    )
                    db.add(global_record)

                db.commit()
                log.debug(f"Updated model token usage for model {model_id}")
                return True
        except Exception as e:
            log.error(f"Error updating model token usage for model {model_id}: {e}")
            return False

    def get_model_usage_by_user(
        self,
        user_id: str,
        year: Optional[int] = None
    ) -> List[ModelUsageResponse]:
        """Get per-model token usage breakdown for a user"""
        try:
            with get_db() as db:
                records = db.query(ModelTokenUsage).filter_by(user_id=user_id).all()

                if not records:
                    return []

                # Calculate total for percentages
                total_all = sum(r.total_tokens for r in records)

                result = []
                for r in records:
                    percentage = (r.total_tokens / total_all * 100) if total_all > 0 else 0
                    result.append(ModelUsageResponse(
                        model_id=r.model_id,
                        total_input_tokens=r.total_input_tokens,
                        total_output_tokens=r.total_output_tokens,
                        total_tokens=r.total_tokens,
                        conversation_count=r.conversation_count,
                        message_count=r.message_count,
                        percentage=round(percentage, 1)
                    ))

                # Sort by total tokens descending
                result.sort(key=lambda x: x.total_tokens, reverse=True)
                return result
        except Exception as e:
            log.error(f"Error getting model usage for user {user_id}: {e}")
            return []

    def get_favorite_model(
        self,
        user_id: str,
        year: Optional[int] = None
    ) -> Optional[Dict]:
        """Get user's most-used model"""
        try:
            with get_db() as db:
                record = db.query(ModelTokenUsage).filter_by(
                    user_id=user_id
                ).order_by(desc(ModelTokenUsage.total_tokens)).first()

                if record:
                    # Get total for percentage
                    total_all = db.query(func.sum(ModelTokenUsage.total_tokens)).filter_by(
                        user_id=user_id
                    ).scalar() or 0

                    percentage = (record.total_tokens / total_all * 100) if total_all > 0 else 0

                    return {
                        "model_id": record.model_id,
                        "total_tokens": record.total_tokens,
                        "percentage": round(percentage, 1)
                    }
                return None
        except Exception as e:
            log.error(f"Error getting favorite model for user {user_id}: {e}")
            return None

    def get_global_model_usage(self, limit: int = 10) -> List[ModelUsageResponse]:
        """Get site-wide model usage breakdown"""
        try:
            with get_db() as db:
                records = db.query(ModelTokenUsage).filter_by(
                    user_id=None
                ).order_by(desc(ModelTokenUsage.total_tokens)).limit(limit).all()

                if not records:
                    return []

                # Calculate total for percentages
                total_all = sum(r.total_tokens for r in records)

                result = []
                for r in records:
                    percentage = (r.total_tokens / total_all * 100) if total_all > 0 else 0
                    result.append(ModelUsageResponse(
                        model_id=r.model_id,
                        total_input_tokens=r.total_input_tokens,
                        total_output_tokens=r.total_output_tokens,
                        total_tokens=r.total_tokens,
                        conversation_count=r.conversation_count,
                        message_count=r.message_count,
                        percentage=round(percentage, 1)
                    ))

                return result
        except Exception as e:
            log.error(f"Error getting global model usage: {e}")
            return []

    # ==================
    # Wrapped Summary
    # ==================

    def get_user_wrapped(
        self,
        user_id: str,
        year: Optional[int] = None
    ) -> WrappedSummaryResponse:
        """Get comprehensive wrapped summary for a user"""
        if year is None:
            year = datetime.now(timezone.utc).year

        try:
            with get_db() as db:
                year_start = f"{year}-01-01"
                year_end = f"{year}-12-31"
                year_start_ts = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
                year_end_ts = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp())

                # Aggregate daily stats
                daily_stats = db.query(
                    func.sum(DailyTokenUsage.total_input_tokens).label('total_input'),
                    func.sum(DailyTokenUsage.total_output_tokens).label('total_output'),
                    func.sum(DailyTokenUsage.total_tokens).label('total'),
                    func.sum(DailyTokenUsage.message_count).label('messages'),
                    func.count(DailyTokenUsage.id).label('days_active')
                ).filter(
                    DailyTokenUsage.user_id == user_id,
                    DailyTokenUsage.date >= year_start,
                    DailyTokenUsage.date <= year_end
                ).first()

                # Count conversations
                conv_count = db.query(func.count(ConversationTokenUsage.id)).filter(
                    ConversationTokenUsage.user_id == user_id,
                    ConversationTokenUsage.created_at >= year_start_ts,
                    ConversationTokenUsage.created_at < year_end_ts
                ).scalar() or 0

                # Get top chats
                top_chats_records = db.query(ConversationTokenUsage).filter(
                    ConversationTokenUsage.user_id == user_id,
                    ConversationTokenUsage.created_at >= year_start_ts,
                    ConversationTokenUsage.created_at < year_end_ts
                ).order_by(desc(ConversationTokenUsage.total_tokens)).limit(10).all()

                top_chats = [
                    TopChatResponse(
                        chat_id=r.chat_id,
                        model_id=r.model_id,
                        total_tokens=r.total_tokens,
                        total_input_tokens=r.total_input_tokens,
                        total_output_tokens=r.total_output_tokens,
                        message_count=r.message_count
                    ) for r in top_chats_records
                ]

                # Get most active day and favorite model
                most_active = self.get_most_active_day(user_id, year)
                favorite = self.get_favorite_model(user_id, year)

                return WrappedSummaryResponse(
                    year=year,
                    total_conversations=conv_count,
                    total_messages=daily_stats.messages or 0,
                    total_input_tokens=daily_stats.total_input or 0,
                    total_output_tokens=daily_stats.total_output or 0,
                    total_tokens=daily_stats.total or 0,
                    days_active=daily_stats.days_active or 0,
                    most_active_day=most_active,
                    favorite_model=favorite,
                    top_chats=top_chats
                )
        except Exception as e:
            log.error(f"Error getting user wrapped for user {user_id}: {e}")
            return WrappedSummaryResponse(year=year)

    def get_global_wrapped(self, year: Optional[int] = None) -> GlobalWrappedResponse:
        """Get site-wide wrapped statistics (admin only)"""
        if year is None:
            year = datetime.now(timezone.utc).year

        try:
            with get_db() as db:
                year_start = f"{year}-01-01"
                year_end = f"{year}-12-31"
                year_start_ts = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
                year_end_ts = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp())

                # Count unique active users
                users_active = db.query(func.count(func.distinct(DailyTokenUsage.user_id))).filter(
                    DailyTokenUsage.date >= year_start,
                    DailyTokenUsage.date <= year_end
                ).scalar() or 0

                # Total conversations
                total_convs = db.query(func.count(ConversationTokenUsage.id)).filter(
                    ConversationTokenUsage.created_at >= year_start_ts,
                    ConversationTokenUsage.created_at < year_end_ts
                ).scalar() or 0

                # Aggregate totals
                daily_totals = db.query(
                    func.sum(DailyTokenUsage.total_tokens).label('total'),
                    func.sum(DailyTokenUsage.message_count).label('messages')
                ).filter(
                    DailyTokenUsage.date >= year_start,
                    DailyTokenUsage.date <= year_end
                ).first()

                # Busiest day across all users
                busiest_day = db.query(
                    DailyTokenUsage.date,
                    func.sum(DailyTokenUsage.total_tokens).label('total')
                ).filter(
                    DailyTokenUsage.date >= year_start,
                    DailyTokenUsage.date <= year_end
                ).group_by(DailyTokenUsage.date).order_by(desc('total')).first()

                busiest = None
                if busiest_day:
                    date_obj = datetime.strptime(busiest_day.date, '%Y-%m-%d')
                    busiest = {
                        "date": busiest_day.date,
                        "tokens": busiest_day.total,
                        "day_of_week": date_obj.strftime('%A')
                    }

                # Top models
                top_models = self.get_global_model_usage(limit=10)

                return GlobalWrappedResponse(
                    year=year,
                    total_users_active=users_active,
                    total_conversations=total_convs,
                    total_messages=daily_totals.messages or 0,
                    total_tokens=daily_totals.total or 0,
                    top_models=top_models,
                    busiest_day=busiest
                )
        except Exception as e:
            log.error(f"Error getting global wrapped: {e}")
            return GlobalWrappedResponse(year=year)

    # ==================
    # Utility Methods
    # ==================

    def increment_conversation_count_for_day(self, user_id: str, date: str) -> bool:
        """Increment the conversation count for a specific day"""
        try:
            with get_db() as db:
                record = db.query(DailyTokenUsage).filter_by(
                    user_id=user_id,
                    date=date
                ).first()

                if record:
                    record.conversation_count += 1
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error incrementing conversation count: {e}")
            return False

    def increment_model_conversation_count(
        self,
        user_id: Optional[str],
        model_id: str
    ) -> bool:
        """Increment the conversation count for a model"""
        try:
            with get_db() as db:
                # User-specific
                if user_id:
                    user_record = db.query(ModelTokenUsage).filter_by(
                        user_id=user_id,
                        model_id=model_id
                    ).first()
                    if user_record:
                        user_record.conversation_count += 1

                # Global
                global_record = db.query(ModelTokenUsage).filter_by(
                    user_id=None,
                    model_id=model_id
                ).first()
                if global_record:
                    global_record.conversation_count += 1

                db.commit()
                return True
        except Exception as e:
            log.error(f"Error incrementing model conversation count: {e}")
            return False


# Global instance
Analytics = AnalyticsTable()
