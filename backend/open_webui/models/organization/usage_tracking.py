import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import secrets
import pytz

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Float, Date, Index, func
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


class ClientDailyUsage(Base):
    """
    Daily usage summaries - 99% storage reduction vs per-request tracking
    One record per client per day instead of thousands of request records
    """
    __tablename__ = "client_daily_usage"

    id = Column(String, primary_key=True)
    client_org_id = Column(String, nullable=False)  # References client_organizations.id
    usage_date = Column(Date, nullable=False)  # SQL Date type for daily grouping

    # Daily totals
    total_tokens = Column(BigInteger, default=0)
    total_requests = Column(Integer, default=0)
    raw_cost = Column(Float, default=0.0)  # OpenRouter cost
    markup_cost = Column(Float, default=0.0)  # Client cost (with markup)

    # Optional: Most used model (if needed for reporting)
    primary_model = Column(String, nullable=True)
    unique_users = Column(Integer, default=1)  # Count of unique users that day

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Indexes for performance
    __table_args__ = (
        Index('idx_client_date', 'client_org_id', 'usage_date'),
        Index('idx_usage_date', 'usage_date'),
    )


class ClientUserDailyUsage(Base):
    """
    Per-user daily usage summaries within each client organization
    Tracks which users are using how much
    """
    __tablename__ = "client_user_daily_usage"

    id = Column(String, primary_key=True)
    client_org_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)  # Open WebUI user ID
    openrouter_user_id = Column(String, nullable=False)  # OpenRouter tracking ID
    usage_date = Column(Date, nullable=False)
    
    # User's daily totals
    total_tokens = Column(BigInteger, default=0)
    total_requests = Column(Integer, default=0)
    raw_cost = Column(Float, default=0.0)
    markup_cost = Column(Float, default=0.0)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    
    __table_args__ = (
        Index('idx_client_user_date', 'client_org_id', 'user_id', 'usage_date'),
        Index('idx_user_date', 'user_id', 'usage_date'),
    )


class ClientModelDailyUsage(Base):
    """
    Per-model daily usage summaries within each client organization
    Tracks which AI models are being used and their costs
    """
    __tablename__ = "client_model_daily_usage"

    id = Column(String, primary_key=True)
    client_org_id = Column(String, nullable=False)
    model_name = Column(String, nullable=False)  # e.g., "anthropic/claude-3.5-sonnet"
    usage_date = Column(Date, nullable=False)
    
    # Model's daily totals
    total_tokens = Column(BigInteger, default=0)
    total_requests = Column(Integer, default=0)
    raw_cost = Column(Float, default=0.0)
    markup_cost = Column(Float, default=0.0)
    
    # Optional model metadata
    provider = Column(String, nullable=True)  # e.g., "anthropic", "openai"
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    
    __table_args__ = (
        Index('idx_client_model_date', 'client_org_id', 'model_name', 'usage_date'),
        Index('idx_model_date', 'model_name', 'usage_date'),
    )


class ClientLiveCounters(Base):
    """
    Live counters for today's usage - reset daily at midnight
    Provides real-time data without storing individual requests
    """
    __tablename__ = "client_live_counters"

    client_org_id = Column(String, primary_key=True)  # References client_organizations.id
    current_date = Column(Date, nullable=False, default=date.today)

    # Today's running totals
    today_tokens = Column(BigInteger, default=0)
    today_requests = Column(Integer, default=0)
    today_raw_cost = Column(Float, default=0.0)
    today_markup_cost = Column(Float, default=0.0)

    last_updated = Column(BigInteger, default=lambda: int(time.time()))

    # Index for fast lookups
    __table_args__ = (
        Index('idx_live_date', 'current_date'),
    )


# Pydantic Models
class ClientDailyUsageModel(BaseModel):
    id: str
    client_org_id: str
    usage_date: date
    total_tokens: int = 0
    total_requests: int = 0
    raw_cost: float = 0.0
    markup_cost: float = 0.0
    primary_model: Optional[str] = None
    unique_users: int = 1
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class ClientUserDailyUsageModel(BaseModel):
    id: str
    client_org_id: str
    user_id: str
    openrouter_user_id: str
    usage_date: date
    total_tokens: int = 0
    total_requests: int = 0
    raw_cost: float = 0.0
    markup_cost: float = 0.0
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class ClientModelDailyUsageModel(BaseModel):
    id: str
    client_org_id: str
    model_name: str
    usage_date: date
    total_tokens: int = 0
    total_requests: int = 0
    raw_cost: float = 0.0
    markup_cost: float = 0.0
    provider: Optional[str] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class ClientLiveCountersModel(BaseModel):
    client_org_id: str
    current_date: date
    today_tokens: int = 0
    today_requests: int = 0
    today_raw_cost: float = 0.0
    today_markup_cost: float = 0.0
    last_updated: int

    model_config = ConfigDict(from_attributes=True)


# Response Models
class ClientUsageStatsResponse(BaseModel):
    """Simplified usage stats for Option 1"""
    today: dict  # Real-time today's usage
    this_month: dict  # Current month totals
    daily_history: List[dict]  # Last 30 days
    client_org_name: str


class ClientBillingResponse(BaseModel):
    client_org_id: str
    client_name: str
    total_tokens: int
    raw_cost: float
    markup_cost: float
    profit_margin: float
    total_requests: int
    days_active: int


# Service Class
class ClientUsageTable:
    """Service class for all usage tracking operations"""
    
    def increment_live_counter(
        self, client_org_id: str, tokens: int, raw_cost: float, markup_cost: float,
        db: Session = None
    ) -> bool:
        """Increment live counter for today's usage"""
        try:
            if db is None:
                with get_db() as db:
                    return self._do_increment_live_counter(
                        db, client_org_id, tokens, raw_cost, markup_cost
                    )
            else:
                return self._do_increment_live_counter(
                    db, client_org_id, tokens, raw_cost, markup_cost
                )
        except Exception as e:
            log.error(f"Failed to increment live counter: {e}")
            return False

    def _do_increment_live_counter(
        self, db: Session, client_org_id: str, tokens: int, raw_cost: float, markup_cost: float
    ) -> bool:
        """Internal method to increment live counter"""
        today = date.today()
        counter = db.query(ClientLiveCounters).filter_by(
            client_org_id=client_org_id
        ).first()
        
        if not counter:
            # Create new counter
            counter = ClientLiveCounters(
                client_org_id=client_org_id,
                current_date=today,
                today_tokens=tokens,
                today_requests=1,
                today_raw_cost=raw_cost,
                today_markup_cost=markup_cost,
                last_updated=int(time.time())
            )
            db.add(counter)
        elif counter.current_date != today:
            # Reset for new day
            counter.current_date = today
            counter.today_tokens = tokens
            counter.today_requests = 1
            counter.today_raw_cost = raw_cost
            counter.today_markup_cost = markup_cost
            counter.last_updated = int(time.time())
        else:
            # Increment existing
            counter.today_tokens += tokens
            counter.today_requests += 1
            counter.today_raw_cost += raw_cost
            counter.today_markup_cost += markup_cost
            counter.last_updated = int(time.time())
        
        db.commit()
        return True

    def get_live_counter(self, client_org_id: str) -> Optional[ClientLiveCountersModel]:
        """Get today's live counter"""
        try:
            with get_db() as db:
                counter = db.query(ClientLiveCounters).filter_by(
                    client_org_id=client_org_id
                ).first()
                
                if counter and counter.current_date == date.today():
                    return ClientLiveCountersModel.from_orm(counter)
                
                # Return empty counter if none exists or it's outdated
                return ClientLiveCountersModel(
                    client_org_id=client_org_id,
                    current_date=date.today(),
                    today_tokens=0,
                    today_requests=0,
                    today_raw_cost=0.0,
                    today_markup_cost=0.0,
                    last_updated=int(time.time())
                )
        except Exception as e:
            log.error(f"Failed to get live counter: {e}")
            return None

    def add_daily_usage(
        self, client_org_id: str, usage_date: date, tokens: int, 
        requests: int, raw_cost: float, markup_cost: float,
        primary_model: Optional[str] = None, unique_users: int = 1
    ) -> bool:
        """Add or update daily usage summary"""
        try:
            with get_db() as db:
                usage_id = f"{client_org_id}_{usage_date.isoformat()}"
                usage = db.query(ClientDailyUsage).filter_by(
                    id=usage_id
                ).first()
                
                current_time = int(time.time())
                
                if usage:
                    # Update existing
                    usage.total_tokens += tokens
                    usage.total_requests += requests
                    usage.raw_cost += raw_cost
                    usage.markup_cost += markup_cost
                    usage.unique_users = max(usage.unique_users, unique_users)
                    usage.updated_at = current_time
                else:
                    # Create new
                    usage = ClientDailyUsage(
                        id=usage_id,
                        client_org_id=client_org_id,
                        usage_date=usage_date,
                        total_tokens=tokens,
                        total_requests=requests,
                        raw_cost=raw_cost,
                        markup_cost=markup_cost,
                        primary_model=primary_model,
                        unique_users=unique_users,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    db.add(usage)
                
                db.commit()
                return True
        except Exception as e:
            log.error(f"Failed to add daily usage: {e}")
            return False

    def get_usage_stats(
        self, client_org_id: str, days: int = 30, timezone: str = "Europe/Warsaw"
    ) -> Optional[ClientUsageStatsResponse]:
        """Get comprehensive usage statistics"""
        try:
            with get_db() as db:
                # Get client name
                from .client_organization import ClientOrganization
                client = db.query(ClientOrganization).filter_by(id=client_org_id).first()
                if not client:
                    return None
                
                # Get today's live counter
                live_counter = self.get_live_counter(client_org_id)
                
                # Get current month totals
                tz = pytz.timezone(timezone)
                local_now = datetime.now(tz)
                month_start = local_now.replace(day=1).date()
                
                month_totals = db.query(
                    func.sum(ClientDailyUsage.total_tokens),
                    func.sum(ClientDailyUsage.total_requests),
                    func.sum(ClientDailyUsage.raw_cost),
                    func.sum(ClientDailyUsage.markup_cost)
                ).filter(
                    ClientDailyUsage.client_org_id == client_org_id,
                    ClientDailyUsage.usage_date >= month_start
                ).first()
                
                # Get daily history
                cutoff_date = local_now.date() - timedelta(days=days)
                daily_usage = db.query(ClientDailyUsage).filter(
                    ClientDailyUsage.client_org_id == client_org_id,
                    ClientDailyUsage.usage_date >= cutoff_date
                ).order_by(ClientDailyUsage.usage_date.desc()).all()
                
                # Format response
                return ClientUsageStatsResponse(
                    today={
                        "tokens": live_counter.today_tokens if live_counter else 0,
                        "requests": live_counter.today_requests if live_counter else 0,
                        "raw_cost": live_counter.today_raw_cost if live_counter else 0.0,
                        "markup_cost": live_counter.today_markup_cost if live_counter else 0.0
                    },
                    this_month={
                        "tokens": (month_totals[0] or 0) + (live_counter.today_tokens if live_counter else 0),
                        "requests": (month_totals[1] or 0) + (live_counter.today_requests if live_counter else 0),
                        "raw_cost": (month_totals[2] or 0.0) + (live_counter.today_raw_cost if live_counter else 0.0),
                        "markup_cost": (month_totals[3] or 0.0) + (live_counter.today_markup_cost if live_counter else 0.0)
                    },
                    daily_history=[{
                        "date": usage.usage_date.isoformat(),
                        "tokens": usage.total_tokens,
                        "requests": usage.total_requests,
                        "raw_cost": usage.raw_cost,
                        "markup_cost": usage.markup_cost,
                        "primary_model": usage.primary_model
                    } for usage in daily_usage],
                    client_org_name=client.name
                )
        except Exception as e:
            log.error(f"Failed to get usage stats: {e}")
            return None

    def rollover_daily_counters(self, client_org_id: str) -> bool:
        """Roll over live counters to daily summary at midnight"""
        try:
            with get_db() as db:
                counter = db.query(ClientLiveCounters).filter_by(
                    client_org_id=client_org_id
                ).first()
                
                if not counter or counter.current_date >= date.today():
                    return True  # Nothing to roll over
                
                # Add to daily summary
                success = self.add_daily_usage(
                    client_org_id=client_org_id,
                    usage_date=counter.current_date,
                    tokens=counter.today_tokens,
                    requests=counter.today_requests,
                    raw_cost=counter.today_raw_cost,
                    markup_cost=counter.today_markup_cost
                )
                
                if success:
                    # Reset counter for new day
                    counter.current_date = date.today()
                    counter.today_tokens = 0
                    counter.today_requests = 0
                    counter.today_raw_cost = 0.0
                    counter.today_markup_cost = 0.0
                    counter.last_updated = int(time.time())
                    db.commit()
                
                return success
        except Exception as e:
            log.error(f"Failed to rollover daily counters: {e}")
            return False