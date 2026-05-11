"""
User Usage Tracking Model

This module provides tracking for user token usage and costs across models.
Used for implementing spend limits and usage reporting.

Key Features:
- Daily/monthly usage aggregation per user
- Per-model cost tracking
- Efficient queries for limit checking
"""

import time
import logging
from datetime import date
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import (
    BigInteger,
    Column,
    String,
    Integer,
    Float,
    Date,
    Index,
    func,
    and_,
)
from pydantic import BaseModel, ConfigDict

from open_webui.internal.db import Base, get_db, get_db_context
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", logging.INFO))


####################
# UserUsage DB Schema
####################


class UserUsage(Base):
    """
    Tracks token usage and costs per user per day per model.

    This allows for:
    - Daily spend limit enforcement
    - Monthly spend limit enforcement
    - Usage reporting and analytics
    - Per-model cost tracking
    """

    __tablename__ = "user_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    model_id = Column(String, nullable=False)

    # Token counts
    input_tokens = Column(BigInteger, default=0)
    output_tokens = Column(BigInteger, default=0)
    reasoning_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)

    # Cost tracking (in USD)
    cost = Column(Float, default=0.0)

    # Request count for this user/date/model
    request_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        # Composite index for efficient daily/monthly queries
        Index('idx_user_usage_user_date', 'user_id', 'date'),
        # Unique constraint to ensure one record per user/date/model
        Index('idx_user_usage_unique', 'user_id', 'date', 'model_id', unique=True),
    )


class UserUsageModel(BaseModel):
    """Pydantic model for UserUsage."""

    id: int
    user_id: str
    date: date
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    request_count: int = 0
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class UsageRecordForm(BaseModel):
    """Form for recording usage after a chat completion."""

    user_id: str
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost: float = 0.0


class UserSpendSummary(BaseModel):
    """Summary of user spending for a period."""

    user_id: str
    daily_spend: float = 0.0
    monthly_spend: float = 0.0
    daily_tokens: int = 0
    monthly_tokens: int = 0
    daily_requests: int = 0
    monthly_requests: int = 0


class UserUsageResponse(BaseModel):
    """Response model for usage queries."""

    date: date
    model_id: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    cost: float
    request_count: int


class UserUsageListResponse(BaseModel):
    """Response model for listing usage records."""

    items: List[UserUsageResponse]
    total: int
    total_cost: float
    total_tokens: int


####################
# UserUsage Operations
####################


class UserUsageTable:
    """Operations for tracking and querying user usage."""

    def record_usage(
        self,
        form_data: UsageRecordForm,
        db: Optional[Session] = None,
    ) -> Optional[UserUsageModel]:
        """
        Record usage for a user after a chat completion.

        Upserts the usage record, incrementing counts if a record
        already exists for this user/date/model combination.
        """
        try:
            with get_db_context(db) as db:
                today = date.today()
                now = int(time.time())

                total_tokens = form_data.input_tokens + form_data.output_tokens + form_data.reasoning_tokens

                # Try to find existing record for today
                existing = (
                    db.query(UserUsage)
                    .filter(
                        and_(
                            UserUsage.user_id == form_data.user_id,
                            UserUsage.date == today,
                            UserUsage.model_id == form_data.model_id,
                        )
                    )
                    .first()
                )

                if existing:
                    # Update existing record
                    existing.input_tokens += form_data.input_tokens
                    existing.output_tokens += form_data.output_tokens
                    existing.reasoning_tokens += form_data.reasoning_tokens
                    existing.total_tokens += total_tokens
                    existing.cost += form_data.cost
                    existing.request_count += 1
                    existing.updated_at = now
                    db.commit()
                    db.refresh(existing)
                    return UserUsageModel.model_validate(existing)
                else:
                    # Create new record
                    usage = UserUsage(
                        user_id=form_data.user_id,
                        date=today,
                        model_id=form_data.model_id,
                        input_tokens=form_data.input_tokens,
                        output_tokens=form_data.output_tokens,
                        reasoning_tokens=form_data.reasoning_tokens,
                        total_tokens=total_tokens,
                        cost=form_data.cost,
                        request_count=1,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(usage)
                    db.commit()
                    db.refresh(usage)
                    return UserUsageModel.model_validate(usage)

        except Exception as e:
            log.error(f"Error recording usage for user {form_data.user_id}: {e}")
            return None

    def get_user_daily_spend(
        self,
        user_id: str,
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> float:
        """Get total spend for a user on a specific date (defaults to today)."""
        try:
            with get_db_context(db) as db:
                if target_date is None:
                    target_date = date.today()

                result = (
                    db.query(func.sum(UserUsage.cost))
                    .filter(
                        and_(
                            UserUsage.user_id == user_id,
                            UserUsage.date == target_date,
                        )
                    )
                    .scalar()
                )

                return float(result) if result else 0.0
        except Exception as e:
            log.error(f"Error getting daily spend for user {user_id}: {e}")
            return 0.0

    def get_user_monthly_spend(
        self,
        user_id: str,
        year: Optional[int] = None,
        month: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> float:
        """Get total spend for a user in a specific month (defaults to current month)."""
        try:
            with get_db_context(db) as db:
                if year is None or month is None:
                    today = date.today()
                    year = today.year
                    month = today.month

                # First day of month
                month_start = date(year, month, 1)
                # First day of next month
                if month == 12:
                    month_end = date(year + 1, 1, 1)
                else:
                    month_end = date(year, month + 1, 1)

                result = (
                    db.query(func.sum(UserUsage.cost))
                    .filter(
                        and_(
                            UserUsage.user_id == user_id,
                            UserUsage.date >= month_start,
                            UserUsage.date < month_end,
                        )
                    )
                    .scalar()
                )

                return float(result) if result else 0.0
        except Exception as e:
            log.error(f"Error getting monthly spend for user {user_id}: {e}")
            return 0.0

    def get_user_spend_summary(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> UserSpendSummary:
        """Get a complete spend summary for a user (daily and monthly)."""
        try:
            with get_db_context(db) as db:
                today = date.today()
                month_start = date(today.year, today.month, 1)
                if today.month == 12:
                    month_end = date(today.year + 1, 1, 1)
                else:
                    month_end = date(today.year, today.month + 1, 1)

                # Daily aggregation
                daily_result = (
                    db.query(
                        func.sum(UserUsage.cost).label('cost'),
                        func.sum(UserUsage.total_tokens).label('tokens'),
                        func.sum(UserUsage.request_count).label('requests'),
                    )
                    .filter(
                        and_(
                            UserUsage.user_id == user_id,
                            UserUsage.date == today,
                        )
                    )
                    .first()
                )

                # Monthly aggregation
                monthly_result = (
                    db.query(
                        func.sum(UserUsage.cost).label('cost'),
                        func.sum(UserUsage.total_tokens).label('tokens'),
                        func.sum(UserUsage.request_count).label('requests'),
                    )
                    .filter(
                        and_(
                            UserUsage.user_id == user_id,
                            UserUsage.date >= month_start,
                            UserUsage.date < month_end,
                        )
                    )
                    .first()
                )

                return UserSpendSummary(
                    user_id=user_id,
                    daily_spend=float(daily_result.cost) if daily_result.cost else 0.0,
                    monthly_spend=float(monthly_result.cost) if monthly_result.cost else 0.0,
                    daily_tokens=int(daily_result.tokens) if daily_result.tokens else 0,
                    monthly_tokens=int(monthly_result.tokens) if monthly_result.tokens else 0,
                    daily_requests=int(daily_result.requests) if daily_result.requests else 0,
                    monthly_requests=int(monthly_result.requests) if monthly_result.requests else 0,
                )
        except Exception as e:
            log.error(f"Error getting spend summary for user {user_id}: {e}")
            return UserSpendSummary(user_id=user_id)

    def get_user_usage_history(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> UserUsageListResponse:
        """Get usage history for a user within a date range."""
        try:
            with get_db_context(db) as db:
                query = db.query(UserUsage).filter(UserUsage.user_id == user_id)

                if start_date:
                    query = query.filter(UserUsage.date >= start_date)
                if end_date:
                    query = query.filter(UserUsage.date <= end_date)

                # Get totals before pagination
                totals = db.query(
                    func.count(UserUsage.id).label('total'),
                    func.sum(UserUsage.cost).label('total_cost'),
                    func.sum(UserUsage.total_tokens).label('total_tokens'),
                ).filter(UserUsage.user_id == user_id)

                if start_date:
                    totals = totals.filter(UserUsage.date >= start_date)
                if end_date:
                    totals = totals.filter(UserUsage.date <= end_date)

                totals_result = totals.first()

                # Get paginated results
                query = query.order_by(UserUsage.date.desc(), UserUsage.model_id)
                query = query.offset(skip).limit(limit)
                records = query.all()

                items = [
                    UserUsageResponse(
                        date=r.date,
                        model_id=r.model_id,
                        input_tokens=r.input_tokens,
                        output_tokens=r.output_tokens,
                        reasoning_tokens=r.reasoning_tokens,
                        total_tokens=r.total_tokens,
                        cost=r.cost,
                        request_count=r.request_count,
                    )
                    for r in records
                ]

                return UserUsageListResponse(
                    items=items,
                    total=totals_result.total if totals_result.total else 0,
                    total_cost=float(totals_result.total_cost) if totals_result.total_cost else 0.0,
                    total_tokens=int(totals_result.total_tokens) if totals_result.total_tokens else 0,
                )
        except Exception as e:
            log.error(f"Error getting usage history for user {user_id}: {e}")
            return UserUsageListResponse(items=[], total=0, total_cost=0.0, total_tokens=0)

    def delete_user_usage(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Delete all usage records for a user (used when deleting user)."""
        try:
            with get_db_context(db) as db:
                db.query(UserUsage).filter(UserUsage.user_id == user_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting usage for user {user_id}: {e}")
            return False


# Singleton instance
UserUsages = UserUsageTable()
