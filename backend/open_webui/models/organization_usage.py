import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Float, Date, Index, Boolean
from sqlalchemy.orm import relationship

log = logging.getLogger(__name__)


####################
# Option 1: Simplified Database Schema
# Daily summaries + live counters approach for minimal storage
####################


class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id = Column(String, primary_key=True)
    openrouter_provisioning_key = Column(Text, nullable=True)  # For creating client API keys
    default_markup_rate = Column(Float, default=1.3)
    billing_currency = Column(String, default="USD")
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ProcessedGeneration(Base):
    """Track processed OpenRouter generations to prevent duplicates"""
    __tablename__ = "processed_generations"

    id = Column(String, primary_key=True)  # OpenRouter generation ID
    client_org_id = Column(String, nullable=False)
    generation_date = Column(Date, nullable=False)
    processed_at = Column(BigInteger, nullable=False)
    total_cost = Column(Float, nullable=False)
    total_tokens = Column(Integer, nullable=False)

    __table_args__ = (
        Index('idx_client_date', 'client_org_id', 'generation_date'),
        Index('idx_processed_at', 'processed_at'),
    )


class ProcessedGenerationCleanupLog(Base):
    """Track cleanup operations for audit and monitoring"""
    __tablename__ = "processed_generation_cleanup_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cleanup_date = Column(Date, nullable=False)  # Date when cleanup was performed
    cutoff_date = Column(Date, nullable=False)   # Records older than this were deleted
    days_retained = Column(Integer, nullable=False)  # Retention period used
    records_before = Column(Integer, nullable=False)
    records_deleted = Column(Integer, nullable=False)
    records_remaining = Column(Integer, nullable=False)
    old_tokens_removed = Column(BigInteger, nullable=False)
    old_cost_removed = Column(Float, nullable=False)
    storage_saved_kb = Column(Float, nullable=False)
    cleanup_duration_seconds = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('idx_cleanup_date', 'cleanup_date'),
        Index('idx_success', 'success'),
    )


class ClientOrganization(Base):
    __tablename__ = "client_organizations"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    openrouter_api_key = Column(Text, nullable=False, unique=True)  # Dedicated key per client
    openrouter_key_hash = Column(String, nullable=True)  # OpenRouter's key identifier
    markup_rate = Column(Float, default=1.3)
    monthly_limit = Column(Float, nullable=True)  # Optional spending limit
    billing_email = Column(String, nullable=True)
    timezone = Column(String, default="Europe/Warsaw")  # Client's local timezone for accurate date calculations
    is_active = Column(Integer, default=1)  # Boolean as integer
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Add indexes for performance
    __table_args__ = (
        Index('idx_api_key', 'openrouter_api_key'),
        Index('idx_active', 'is_active'),
    )


class UserClientMapping(Base):
    __tablename__ = "user_client_mapping"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)  # Open WebUI user ID
    client_org_id = Column(String, nullable=False)  # References client_organizations.id
    openrouter_user_id = Column(String, nullable=False)  # For OpenRouter user parameter
    is_active = Column(Integer, default=1)  # Boolean as integer
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Add indexes for performance
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_client_org_id', 'client_org_id'),
        Index('idx_openrouter_user_id', 'openrouter_user_id'),
    )


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
        Index('idx_client_live_date', 'client_org_id', 'current_date'),
    )


####################
# Pydantic Models
####################


class GlobalSettingsModel(BaseModel):
    id: str
    openrouter_provisioning_key: Optional[str] = None
    default_markup_rate: float = 1.3
    billing_currency: str = "USD"
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class ClientOrganizationModel(BaseModel):
    id: str
    name: str
    openrouter_api_key: str
    openrouter_key_hash: Optional[str] = None
    markup_rate: float = 1.3
    monthly_limit: Optional[float] = None
    billing_email: Optional[str] = None
    timezone: str = "Europe/Warsaw"
    is_active: bool = True
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class UserClientMappingModel(BaseModel):
    id: str
    user_id: str
    client_org_id: str
    openrouter_user_id: str
    is_active: bool = True
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


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


####################
# Forms and Responses
####################


class GlobalSettingsForm(BaseModel):
    openrouter_provisioning_key: Optional[str] = None
    default_markup_rate: float = 1.3
    billing_currency: str = "USD"


class ClientOrganizationForm(BaseModel):
    name: str
    markup_rate: float = 1.3
    monthly_limit: Optional[float] = None
    billing_email: Optional[str] = None
    timezone: str = "Europe/Warsaw"


class UserClientMappingForm(BaseModel):
    user_id: str
    client_org_id: str
    openrouter_user_id: str


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


####################
# Database Operations - Option 1 Implementation
####################


class GlobalSettingsTable:
    def get_settings(self) -> Optional[GlobalSettingsModel]:
        """Get global settings (singleton)"""
        try:
            with get_db() as db:
                settings = db.query(GlobalSettings).first()
                if settings:
                    return GlobalSettingsModel.model_validate(settings)
                return None
        except Exception:
            return None

    def create_or_update_settings(
        self, settings_form: GlobalSettingsForm
    ) -> Optional[GlobalSettingsModel]:
        """Create or update global settings"""
        try:
            with get_db() as db:
                existing = db.query(GlobalSettings).first()
                current_time = int(time.time())
                
                if existing:
                    # Update existing
                    for key, value in settings_form.model_dump().items():
                        setattr(existing, key, value)
                    existing.updated_at = current_time
                    db.commit()
                    db.refresh(existing)
                    return GlobalSettingsModel.model_validate(existing)
                else:
                    # Create new
                    settings_data = settings_form.model_dump()
                    settings_data.update({
                        "id": "global",
                        "created_at": current_time,
                        "updated_at": current_time
                    })
                    new_settings = GlobalSettings(**settings_data)
                    db.add(new_settings)
                    db.commit()
                    db.refresh(new_settings)
                    return GlobalSettingsModel.model_validate(new_settings)
        except Exception:
            return None


class ClientOrganizationTable:
    def create_client(
        self, client_form: ClientOrganizationForm, api_key: str, key_hash: str = None
    ) -> Optional[ClientOrganizationModel]:
        """Create a new client organization"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                client_data = client_form.model_dump()
                client_data.update({
                    "id": f"client_{client_form.name.lower().replace(' ', '_')}_{current_time}",
                    "openrouter_api_key": api_key,
                    "openrouter_key_hash": key_hash,
                    "is_active": 1,  # Ensure is_active is set
                    "created_at": current_time,
                    "updated_at": current_time
                })
                
                new_client = ClientOrganization(**client_data)
                db.add(new_client)
                db.commit()
                db.refresh(new_client)
                return ClientOrganizationModel.model_validate(new_client)
        except Exception:
            return None

    def get_client_by_id(self, client_id: str) -> Optional[ClientOrganizationModel]:
        """Get client organization by ID"""
        try:
            with get_db() as db:
                client = db.query(ClientOrganization).filter_by(id=client_id, is_active=1).first()
                if client:
                    return ClientOrganizationModel.model_validate(client)
                return None
        except Exception:
            return None
    
    def get_client_by_api_key(self, api_key: str) -> Optional[ClientOrganizationModel]:
        """Get client organization by API key"""
        try:
            with get_db() as db:
                client = db.query(ClientOrganization).filter_by(
                    openrouter_api_key=api_key,
                    is_active=1
                ).first()
                if client:
                    return ClientOrganizationModel.model_validate(client)
                return None
        except Exception:
            return None

    def get_all_active_clients(self) -> List[ClientOrganizationModel]:
        """Get all active client organizations"""
        try:
            with get_db() as db:
                clients = db.query(ClientOrganization).filter_by(is_active=1).all()
                return [ClientOrganizationModel.model_validate(c) for c in clients]
        except Exception:
            return []

    def update_client(
        self, client_id: str, updates: dict
    ) -> Optional[ClientOrganizationModel]:
        """Update client organization"""
        try:
            with get_db() as db:
                client = db.query(ClientOrganization).filter_by(id=client_id).first()
                if client:
                    for key, value in updates.items():
                        setattr(client, key, value)
                    client.updated_at = int(time.time())
                    db.commit()
                    db.refresh(client)
                    return ClientOrganizationModel.model_validate(client)
                return None
        except Exception:
            return None

    def deactivate_client(self, client_id: str) -> bool:
        """Deactivate a client organization"""
        try:
            with get_db() as db:
                client = db.query(ClientOrganization).filter_by(id=client_id).first()
                if client:
                    client.is_active = 0
                    client.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception:
            return False


class UserClientMappingTable:
    def create_mapping(
        self, mapping_form: UserClientMappingForm
    ) -> Optional[UserClientMappingModel]:
        """Create a new user-client mapping"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                mapping_data = mapping_form.model_dump()
                mapping_data.update({
                    "id": f"{mapping_form.user_id}_{mapping_form.client_org_id}",
                    "is_active": 1,  # Ensure is_active is set
                    "created_at": current_time,
                    "updated_at": current_time
                })
                
                new_mapping = UserClientMapping(**mapping_data)
                db.add(new_mapping)
                db.commit()
                db.refresh(new_mapping)
                return UserClientMappingModel.model_validate(new_mapping)
        except Exception:
            return None

    def get_mapping_by_user_id(
        self, user_id: str
    ) -> Optional[UserClientMappingModel]:
        """Get mapping by user ID"""
        try:
            with get_db() as db:
                mapping = db.query(UserClientMapping).filter_by(
                    user_id=user_id, is_active=1
                ).first()
                if mapping:
                    return UserClientMappingModel.model_validate(mapping)
                return None
        except Exception:
            return None

    def get_mappings_by_client_id(
        self, client_org_id: str
    ) -> List[UserClientMappingModel]:
        """Get all mappings for a client organization"""
        try:
            with get_db() as db:
                mappings = db.query(UserClientMapping).filter_by(
                    client_org_id=client_org_id, is_active=1
                ).all()
                return [UserClientMappingModel.model_validate(m) for m in mappings]
        except Exception:
            return []

    def deactivate_mapping(self, user_id: str) -> bool:
        """Deactivate a user-client mapping"""
        try:
            with get_db() as db:
                mapping = db.query(UserClientMapping).filter_by(
                    user_id=user_id
                ).first()
                if mapping:
                    mapping.is_active = 0
                    mapping.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception:
            return False
    
    def update_mapping(self, user_id: str, updates: dict) -> bool:
        """Update a user-client mapping"""
        try:
            with get_db() as db:
                mapping = db.query(UserClientMapping).filter_by(
                    user_id=user_id, is_active=1
                ).first()
                if mapping:
                    for key, value in updates.items():
                        setattr(mapping, key, value)
                    mapping.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Failed to update mapping for user {user_id}: {e}")
            return False


class ClientUsageTable:
    """
    Option 1: Simplified usage tracking with daily summaries + live counters
    """
    
    def record_usage(
        self,
        client_org_id: str,
        user_id: str,
        openrouter_user_id: str,
        model_name: str,
        usage_date: date,
        input_tokens: int = 0,
        output_tokens: int = 0,
        raw_cost: float = 0.0,
        markup_cost: float = 0.0,
        provider: str = None,
        request_metadata: dict = None
    ) -> bool:
        """
        Record API usage with per-user and per-model tracking
        Updates live counters for real-time UI and daily summaries
        Includes transaction safety and retry logic for concurrent access
        """
        
        # Retry logic for handling concurrent access
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                with get_db() as db:
                    # Begin explicit transaction for atomicity
                    db.begin()
                    
                    today = date.today()
                    current_time = int(time.time())
                    total_tokens = input_tokens + output_tokens
                    
                    try:
                        # 1. Update client-level live counter with row-level locking
                        live_counter = db.query(ClientLiveCounters).filter_by(
                            client_org_id=client_org_id
                        ).with_for_update().first()  # Pessimistic locking
                        
                        if live_counter:
                            if live_counter.current_date != today:
                                self._rollup_to_daily_summary(db, live_counter)
                                live_counter.current_date = today
                                live_counter.today_tokens = 0
                                live_counter.today_requests = 0
                                live_counter.today_raw_cost = 0.0
                                live_counter.today_markup_cost = 0.0
                            
                            live_counter.today_tokens += total_tokens
                            live_counter.today_requests += 1
                            live_counter.today_raw_cost += raw_cost
                            live_counter.today_markup_cost += markup_cost
                            live_counter.last_updated = current_time
                        else:
                            live_counter = ClientLiveCounters(
                                client_org_id=client_org_id,
                                current_date=today,
                                today_tokens=total_tokens,
                                today_requests=1,
                                today_raw_cost=raw_cost,
                                today_markup_cost=markup_cost,
                                last_updated=current_time
                            )
                            db.add(live_counter)
                        
                        # 2. Update per-user daily usage
                        user_usage_id = f"{client_org_id}:{user_id}:{usage_date}"
                        user_usage = db.query(ClientUserDailyUsage).filter_by(id=user_usage_id).first()
                        
                        if user_usage:
                            user_usage.total_tokens += total_tokens
                            user_usage.total_requests += 1
                            user_usage.raw_cost += raw_cost
                            user_usage.markup_cost += markup_cost
                            user_usage.updated_at = current_time
                        else:
                            user_usage = ClientUserDailyUsage(
                                id=user_usage_id,
                                client_org_id=client_org_id,
                                user_id=user_id,
                                openrouter_user_id=openrouter_user_id,
                                usage_date=usage_date,
                                total_tokens=total_tokens,
                                total_requests=1,
                                raw_cost=raw_cost,
                                markup_cost=markup_cost,
                                created_at=current_time,
                                updated_at=current_time
                            )
                            db.add(user_usage)
                        
                        # 3. Update per-model daily usage
                        model_usage_id = f"{client_org_id}:{model_name}:{usage_date}"
                        model_usage = db.query(ClientModelDailyUsage).filter_by(id=model_usage_id).first()
                        
                        if model_usage:
                            model_usage.total_tokens += total_tokens
                            model_usage.total_requests += 1
                            model_usage.raw_cost += raw_cost
                            model_usage.markup_cost += markup_cost
                            model_usage.updated_at = current_time
                        else:
                            model_usage = ClientModelDailyUsage(
                                id=model_usage_id,
                                client_org_id=client_org_id,
                                model_name=model_name,
                                usage_date=usage_date,
                                total_tokens=total_tokens,
                                total_requests=1,
                                raw_cost=raw_cost,
                                markup_cost=markup_cost,
                                provider=provider,
                                created_at=current_time,
                                updated_at=current_time
                            )
                            db.add(model_usage)
                        
                        # Commit all changes atomically
                        db.commit()
                        return True
                        
                    except Exception as inner_e:
                        # Rollback transaction on error
                        db.rollback()
                        raise inner_e
                    
            except Exception as e:
                # Handle specific retry-able exceptions
                if attempt < max_retries - 1:
                    if "database is locked" in str(e).lower() or "deadlock" in str(e).lower():
                        log.warning(f"Database conflict on attempt {attempt + 1}/{max_retries}: {e}")
                        import time
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                
                # Final attempt failed or non-retryable error
                log.error(f"Failed to record usage for {client_org_id}: {e}")
                return False
                
        # All retries exhausted
        log.error(f"All retry attempts exhausted for usage recording: {client_org_id}")
        return False
    
    def _rollup_to_daily_summary(self, db, live_counter: ClientLiveCounters):
        """Move yesterday's live counters to daily summary table"""
        if live_counter.today_tokens > 0:  # Only create summary if there was usage
            summary_id = f"{live_counter.client_org_id}_{live_counter.current_date.isoformat()}"
            daily_summary = ClientDailyUsage(
                id=summary_id,
                client_org_id=live_counter.client_org_id,
                usage_date=live_counter.current_date,
                total_tokens=live_counter.today_tokens,
                total_requests=live_counter.today_requests,
                raw_cost=live_counter.today_raw_cost,
                markup_cost=live_counter.today_markup_cost,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            db.add(daily_summary)
    
    def get_usage_stats_by_client(
        self, client_org_id: str, use_client_timezone: bool = True
    ) -> ClientUsageStatsResponse:
        """Get hybrid usage stats for Option 1 - real-time today + daily history"""
        try:
            with get_db() as db:
                # Get today's live data
                live_counter = db.query(ClientLiveCounters).filter_by(
                    client_org_id=client_org_id
                ).first()
                
                today_data = {
                    'tokens': 0,
                    'cost': 0.0,
                    'requests': 0,
                    'last_updated': 'No usage today'
                }
                
                if live_counter:
                    if live_counter.current_date == date.today():
                        # Live counter is current - use its data
                        today_data = {
                            'tokens': live_counter.today_tokens,
                            'cost': live_counter.today_markup_cost,
                            'requests': live_counter.today_requests,
                            'last_updated': datetime.fromtimestamp(live_counter.last_updated).strftime('%H:%M:%S')
                        }
                    else:
                        # Live counter is stale - rollover and reset for today
                        log.warning(f"Stale live counter detected for client {client_org_id}. Date: {live_counter.current_date}, Today: {date.today()}")
                        
                        # Perform rollover if there was usage yesterday
                        if live_counter.today_tokens > 0:
                            self._rollup_to_daily_summary(db, live_counter)
                        
                        # Fallback: Check if today's data exists in daily summaries
                        today = date.today()
                        today_summary = db.query(ClientDailyUsage).filter_by(
                            client_org_id=client_org_id,
                            usage_date=today
                        ).first()
                        
                        if today_summary:
                            # Found today's data in daily summaries - populate live counter
                            live_counter.current_date = today
                            live_counter.today_tokens = today_summary.total_tokens
                            live_counter.today_requests = today_summary.total_requests
                            live_counter.today_raw_cost = today_summary.raw_cost
                            live_counter.today_markup_cost = today_summary.markup_cost
                            live_counter.last_updated = int(time.time())
                            
                            today_data = {
                                'tokens': today_summary.total_tokens,
                                'cost': today_summary.markup_cost,
                                'requests': today_summary.total_requests,
                                'last_updated': 'Restored from daily summary'
                            }
                            
                            log.info(f"Restored live counter from daily summary for client {client_org_id}: {today_summary.total_tokens} tokens")
                        else:
                            # No today's data found - reset to zero
                            live_counter.current_date = today
                            live_counter.today_tokens = 0
                            live_counter.today_requests = 0
                            live_counter.today_raw_cost = 0.0
                            live_counter.today_markup_cost = 0.0
                            live_counter.last_updated = int(time.time())
                            
                            today_data['last_updated'] = 'Reset to today'
                        
                        # Commit the reset/restore
                        db.commit()
                else:
                    # No live counter exists - check daily summaries for today's data
                    today = date.today()
                    today_summary = db.query(ClientDailyUsage).filter_by(
                        client_org_id=client_org_id,
                        usage_date=today
                    ).first()
                    
                    if today_summary:
                        # Create live counter from daily summary
                        live_counter = ClientLiveCounters(
                            client_org_id=client_org_id,
                            current_date=today,
                            today_tokens=today_summary.total_tokens,
                            today_requests=today_summary.total_requests,
                            today_raw_cost=today_summary.raw_cost,
                            today_markup_cost=today_summary.markup_cost,
                            last_updated=int(time.time())
                        )
                        db.add(live_counter)
                        db.commit()
                        
                        today_data = {
                            'tokens': today_summary.total_tokens,
                            'cost': today_summary.markup_cost,
                            'requests': today_summary.total_requests,
                            'last_updated': 'Created from daily summary'
                        }
                        
                        log.info(f"Created live counter from daily summary for client {client_org_id}: {today_summary.total_tokens} tokens")
                
                # Get daily history (last 30 days)
                daily_records = db.query(ClientDailyUsage).filter(
                    ClientDailyUsage.client_org_id == client_org_id
                ).order_by(ClientDailyUsage.usage_date.desc()).limit(30).all()
                
                daily_history = []
                for record in daily_records:
                    daily_history.append({
                        'date': record.usage_date.isoformat(),
                        'tokens': record.total_tokens,
                        'cost': record.markup_cost,
                        'requests': record.total_requests
                    })
                
                # Calculate this month totals
                current_month = date.today().replace(day=1)
                month_records = db.query(ClientDailyUsage).filter(
                    ClientDailyUsage.client_org_id == client_org_id,
                    ClientDailyUsage.usage_date >= current_month
                ).all()
                
                month_tokens = sum(r.total_tokens for r in month_records)
                month_cost = sum(r.markup_cost for r in month_records)
                month_requests = sum(r.total_requests for r in month_records)
                days_active = len(month_records)
                
                # Add today's usage to month totals
                month_tokens += today_data['tokens']
                month_cost += today_data['cost']
                month_requests += today_data['requests']
                if today_data['tokens'] > 0:
                    days_active += 1
                
                this_month = {
                    'tokens': month_tokens,
                    'cost': month_cost,
                    'requests': month_requests,
                    'days_active': days_active
                }
                
                # Get client name
                client_name = "Unknown"
                try:
                    client = ClientOrganizationDB.get_client_by_id(client_org_id)
                    if client:
                        client_name = client.name
                except:
                    pass
                
                return ClientUsageStatsResponse(
                    today=today_data,
                    this_month=this_month,
                    daily_history=daily_history,
                    client_org_name=client_name
                )
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            return ClientUsageStatsResponse(
                today={'tokens': 0, 'cost': 0.0, 'requests': 0, 'last_updated': 'Error'},
                this_month={'tokens': 0, 'cost': 0.0, 'requests': 0, 'days_active': 0},
                daily_history=[],
                client_org_name="Error"
            )
    
    def get_usage_by_user(
        self, client_org_id: str, start_date: date = None, end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get usage breakdown by user for a client organization"""
        try:
            with get_db() as db:
                # Default to current month (from 1st day until now) if no dates provided
                if not end_date:
                    end_date = date.today()
                if not start_date:
                    start_date = end_date.replace(day=1)  # First day of current month
                
                # Query per-user daily usage
                user_records = db.query(ClientUserDailyUsage).filter(
                    ClientUserDailyUsage.client_org_id == client_org_id,
                    ClientUserDailyUsage.usage_date >= start_date,
                    ClientUserDailyUsage.usage_date <= end_date
                ).all()
                
                # Aggregate by user
                user_totals = {}
                for record in user_records:
                    if record.user_id not in user_totals:
                        user_totals[record.user_id] = {
                            'user_id': record.user_id,
                            'openrouter_user_id': record.openrouter_user_id,
                            'total_tokens': 0,
                            'total_requests': 0,
                            'raw_cost': 0.0,
                            'markup_cost': 0.0,
                            'days_active': set()
                        }
                    
                    user_totals[record.user_id]['total_tokens'] += record.total_tokens
                    user_totals[record.user_id]['total_requests'] += record.total_requests
                    user_totals[record.user_id]['raw_cost'] += record.raw_cost
                    user_totals[record.user_id]['markup_cost'] += record.markup_cost
                    user_totals[record.user_id]['days_active'].add(record.usage_date)
                
                # Convert to list and add days active count
                result = []
                for user_data in user_totals.values():
                    user_data['days_active'] = len(user_data['days_active'])
                    result.append(user_data)
                
                # Sort by markup cost descending
                result.sort(key=lambda x: x['markup_cost'], reverse=True)
                
                return result
        except Exception as e:
            print(f"Error getting user usage: {e}")
            return []
    
    def get_usage_by_model(
        self, client_org_id: str, start_date: date = None, end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get usage breakdown by model for a client organization - shows ALL 12 available models"""
        try:
            with get_db() as db:
                # Default to current month (from 1st day until now) if no dates provided
                if not end_date:
                    end_date = date.today()
                if not start_date:
                    start_date = end_date.replace(day=1)  # First day of current month
                
                # Query per-model daily usage
                model_records = db.query(ClientModelDailyUsage).filter(
                    ClientModelDailyUsage.client_org_id == client_org_id,
                    ClientModelDailyUsage.usage_date >= start_date,
                    ClientModelDailyUsage.usage_date <= end_date
                ).all()
                
                # Aggregate by model (only models with usage)
                usage_by_model = {}
                for record in model_records:
                    if record.model_name not in usage_by_model:
                        usage_by_model[record.model_name] = {
                            'total_tokens': 0,
                            'total_requests': 0,
                            'raw_cost': 0.0,
                            'markup_cost': 0.0,
                            'days_used': set(),
                            'provider': record.provider
                        }
                    
                    usage_by_model[record.model_name]['total_tokens'] += record.total_tokens
                    usage_by_model[record.model_name]['total_requests'] += record.total_requests
                    usage_by_model[record.model_name]['raw_cost'] += record.raw_cost
                    usage_by_model[record.model_name]['markup_cost'] += record.markup_cost
                    usage_by_model[record.model_name]['days_used'].add(record.usage_date)
                
                # Define ALL 12 available models (matching frontend fallbackPricingData)
                all_models = [
                    {'id': 'anthropic/claude-sonnet-4', 'name': 'Claude Sonnet 4', 'provider': 'Anthropic'},
                    {'id': 'google/gemini-2.5-flash', 'name': 'Gemini 2.5 Flash', 'provider': 'Google'},
                    {'id': 'google/gemini-2.5-pro', 'name': 'Gemini 2.5 Pro', 'provider': 'Google'},
                    {'id': 'deepseek/deepseek-chat-v3-0324', 'name': 'DeepSeek Chat v3', 'provider': 'DeepSeek'},
                    {'id': 'anthropic/claude-3.7-sonnet', 'name': 'Claude 3.7 Sonnet', 'provider': 'Anthropic'},
                    {'id': 'google/gemini-2.5-flash-lite-preview-06-17', 'name': 'Gemini 2.5 Flash Lite', 'provider': 'Google'},
                    {'id': 'openai/gpt-4.1', 'name': 'GPT-4.1', 'provider': 'OpenAI'},
                    {'id': 'x-ai/grok-4', 'name': 'Grok 4', 'provider': 'xAI'},
                    {'id': 'openai/gpt-4o-mini', 'name': 'GPT-4o Mini', 'provider': 'OpenAI'},
                    {'id': 'openai/o4-mini-high', 'name': 'O4 Mini High', 'provider': 'OpenAI'},
                    {'id': 'openai/o3', 'name': 'O3', 'provider': 'OpenAI'},
                    {'id': 'openai/chatgpt-4o-latest', 'name': 'ChatGPT-4o Latest', 'provider': 'OpenAI'}
                ]
                
                # Create result with ALL 12 models, merging usage data where available
                result = []
                for model in all_models:
                    model_id = model['id']
                    usage = usage_by_model.get(model_id, {
                        'total_tokens': 0,
                        'total_requests': 0,
                        'raw_cost': 0.0,
                        'markup_cost': 0.0,  # This is the key field - 1.3x markup cost
                        'days_used': set(),
                        'provider': model['provider']
                    })
                    
                    result.append({
                        'model_name': model_id,
                        'provider': usage['provider'],
                        'total_tokens': usage['total_tokens'],
                        'total_requests': usage['total_requests'],
                        'raw_cost': usage['raw_cost'],
                        'markup_cost': usage['markup_cost'],  # 1.3x markup rate applied
                        'days_used': len(usage['days_used'])  # Convert set to count
                    })
                
                # Sort by markup cost descending (models with usage first)
                result.sort(key=lambda x: x['markup_cost'], reverse=True)
                
                return result
        except Exception as e:
            print(f"Error getting model usage: {e}")
            return []

    def get_all_clients_usage_stats(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[ClientBillingResponse]:
        """Get usage statistics for all clients for billing purposes"""
        try:
            with get_db() as db:
                # Get all active clients
                clients = ClientOrganizationDB.get_all_active_clients()
                billing_data = []
                
                for client in clients:
                    stats = self.get_usage_stats_by_client(client.id)
                    if stats.this_month['tokens'] > 0:  # Only include clients with usage
                        profit_margin = stats.this_month['cost'] - (stats.this_month['cost'] / client.markup_rate)
                        billing_data.append(ClientBillingResponse(
                            client_org_id=client.id,
                            client_name=client.name,
                            total_tokens=stats.this_month['tokens'],
                            raw_cost=stats.this_month['cost'] / client.markup_rate,
                            markup_cost=stats.this_month['cost'],
                            profit_margin=profit_margin,
                            total_requests=stats.this_month['requests'],
                            days_active=stats.this_month['days_active']
                        ))
                
                return billing_data
        except Exception:
            return []

    def perform_daily_rollover_all_clients(self) -> Dict[str, Any]:
        """
        Perform daily rollover for all client organizations
        This should be called at midnight to ensure proper date transitions
        """
        try:
            with get_db() as db:
                # Get all live counters that need rollover
                live_counters = db.query(ClientLiveCounters).filter(
                    ClientLiveCounters.current_date < date.today()
                ).all()
                
                rollover_count = 0
                for live_counter in live_counters:
                    try:
                        # Perform rollover for this client
                        self._rollup_to_daily_summary(db, live_counter)
                        
                        # Reset counter for today
                        live_counter.current_date = date.today()
                        live_counter.today_tokens = 0
                        live_counter.today_requests = 0
                        live_counter.today_raw_cost = 0.0
                        live_counter.today_markup_cost = 0.0
                        live_counter.last_updated = int(time.time())
                        
                        rollover_count += 1
                        
                    except Exception as e:
                        log.error(f"Failed to rollover client {live_counter.client_org_id}: {e}")
                
                db.commit()
                
                return {
                    "success": True,
                    "rollovers_performed": rollover_count,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Daily rollover failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


####################
# Processed Generation Management
####################

class ProcessedGenerationTable:
    """Database operations for generation deduplication"""

    def is_generation_processed(self, generation_id: str, client_org_id: str) -> bool:
        """Check if a generation has already been processed"""
        try:
            with get_db() as db:
                processed = db.query(ProcessedGeneration).filter_by(
                    id=generation_id,
                    client_org_id=client_org_id
                ).first()
                return processed is not None
        except Exception as e:
            log.error(f"Error checking processed generation {generation_id}: {e}")
            return False

    def mark_generation_processed(self, generation_id: str, client_org_id: str, 
                                 generation_date: date, total_cost: float, 
                                 total_tokens: int) -> bool:
        """Mark a generation as processed"""
        try:
            with get_db() as db:
                processed_gen = ProcessedGeneration(
                    id=generation_id,
                    client_org_id=client_org_id,
                    generation_date=generation_date,
                    processed_at=int(time.time()),
                    total_cost=total_cost,
                    total_tokens=total_tokens
                )
                db.add(processed_gen)
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error marking generation {generation_id} as processed: {e}")
            return False

    def cleanup_old_processed_generations(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """
        Clean up old processed generation records to prevent table bloat.
        Returns detailed statistics about the cleanup operation.
        
        Args:
            days_to_keep: Number of days of records to keep (default: 90)
            
        Returns:
            Dict with cleanup statistics including records deleted, storage saved, etc.
        """
        cleanup_start_time = time.time()
        
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)
            cutoff_timestamp = int(time.time()) - (days_to_keep * 24 * 3600)
            
            with get_db() as db:
                # First, get statistics before cleanup for logging
                total_records_query = db.query(ProcessedGeneration).count()
                records_to_delete_query = db.query(ProcessedGeneration).filter(
                    ProcessedGeneration.processed_at < cutoff_timestamp
                ).count()
                
                # Get breakdown by organization for audit trail
                org_breakdown_query = db.query(
                    ProcessedGeneration.client_org_id,
                    db.func.count(ProcessedGeneration.id).label('count'),
                    db.func.sum(ProcessedGeneration.total_tokens).label('tokens'),
                    db.func.sum(ProcessedGeneration.total_cost).label('cost')
                ).filter(
                    ProcessedGeneration.processed_at < cutoff_timestamp
                ).group_by(ProcessedGeneration.client_org_id).all()
                
                org_stats = {}
                total_old_tokens = 0
                total_old_cost = 0.0
                
                for org_id, count, tokens, cost in org_breakdown_query:
                    org_stats[org_id] = {
                        "records": count,
                        "tokens": tokens or 0,
                        "cost": cost or 0.0
                    }
                    total_old_tokens += tokens or 0
                    total_old_cost += cost or 0.0
                
                # Perform the actual cleanup
                deleted_count = db.query(ProcessedGeneration).filter(
                    ProcessedGeneration.processed_at < cutoff_timestamp
                ).delete()
                
                db.commit()
                
                # Calculate cleanup duration and storage estimates
                cleanup_duration = time.time() - cleanup_start_time
                records_remaining = total_records_query - deleted_count
                
                # Estimate storage savings (approximate)
                avg_record_size_bytes = 100  # Rough estimate per record
                storage_saved_kb = (deleted_count * avg_record_size_bytes) / 1024
                
                # Log cleanup operation to audit table
                cleanup_log_entry = ProcessedGenerationCleanupLog(
                    cleanup_date=date.today(),
                    cutoff_date=cutoff_date,
                    days_retained=days_to_keep,
                    records_before=total_records_query,
                    records_deleted=deleted_count,
                    records_remaining=records_remaining,
                    old_tokens_removed=total_old_tokens,
                    old_cost_removed=total_old_cost,
                    storage_saved_kb=storage_saved_kb,
                    cleanup_duration_seconds=cleanup_duration,
                    success=True,
                    created_at=int(time.time())
                )
                db.add(cleanup_log_entry)
                db.commit()
                
                cleanup_result = {
                    "success": True,
                    "cutoff_date": cutoff_date.isoformat(),
                    "days_to_keep": days_to_keep,
                    "records_before": total_records_query,
                    "records_deleted": deleted_count,
                    "records_remaining": records_remaining,
                    "old_tokens_removed": total_old_tokens,
                    "old_cost_removed": total_old_cost,
                    "storage_saved_kb": round(storage_saved_kb, 2),
                    "cleanup_duration_seconds": round(cleanup_duration, 3),
                    "organization_breakdown": org_stats,
                    "cleanup_timestamp": int(time.time())
                }
                
                # Enhanced logging for production monitoring
                if deleted_count > 0:
                    log.info(f"🧹 Processed generations cleanup completed: "
                           f"{deleted_count:,} records deleted ({records_remaining:,} remaining), "
                           f"{total_old_tokens:,} tokens, ${total_old_cost:.6f} removed, "
                           f"~{storage_saved_kb:.1f}KB saved in {cleanup_duration:.2f}s")
                    
                    # Log organization breakdown for audit
                    for org_id, stats in org_stats.items():
                        log.debug(f"  • {org_id}: {stats['records']} records, "
                                f"{stats['tokens']:,} tokens, ${stats['cost']:.6f}")
                else:
                    log.debug(f"Processed generations cleanup: No old records found (cutoff: {cutoff_date})")
                
                return cleanup_result
                
        except Exception as e:
            cleanup_duration = time.time() - cleanup_start_time
            
            # Log failed cleanup to audit table (if possible)
            try:
                with get_db() as db:
                    cutoff_date = date.today() - timedelta(days=days_to_keep)
                    cleanup_log_entry = ProcessedGenerationCleanupLog(
                        cleanup_date=date.today(),
                        cutoff_date=cutoff_date,
                        days_retained=days_to_keep,
                        records_before=0,
                        records_deleted=0,
                        records_remaining=0,
                        old_tokens_removed=0,
                        old_cost_removed=0.0,
                        storage_saved_kb=0.0,
                        cleanup_duration_seconds=cleanup_duration,
                        success=False,
                        error_message=str(e)[:500],  # Truncate long error messages
                        created_at=int(time.time())
                    )
                    db.add(cleanup_log_entry)
                    db.commit()
            except Exception as log_error:
                log.error(f"Failed to log cleanup error to audit table: {log_error}")
            
            error_result = {
                "success": False,
                "error": str(e),
                "days_to_keep": days_to_keep,
                "cleanup_duration_seconds": round(cleanup_duration, 3),
                "cleanup_timestamp": int(time.time())
            }
            
            log.error(f"❌ Error cleaning up processed generations: {e}")
            return error_result

    def get_processed_generations_stats(self, client_org_id: str, 
                                      start_date: date = None, 
                                      end_date: date = None) -> Dict[str, Any]:
        """Get statistics about processed generations for debugging"""
        try:
            with get_db() as db:
                query = db.query(ProcessedGeneration).filter_by(client_org_id=client_org_id)
                
                if start_date:
                    query = query.filter(ProcessedGeneration.generation_date >= start_date)
                if end_date:
                    query = query.filter(ProcessedGeneration.generation_date <= end_date)
                
                generations = query.all()
                
                total_cost = sum(g.total_cost for g in generations)
                total_tokens = sum(g.total_tokens for g in generations)
                
                return {
                    "client_org_id": client_org_id,
                    "total_processed": len(generations),
                    "total_cost": total_cost,
                    "total_tokens": total_tokens,
                    "date_range": {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None
                    }
                }
        except Exception as e:
            log.error(f"Error getting processed generation stats: {e}")
            return {}


# Singleton instances
GlobalSettingsDB = GlobalSettingsTable()
ClientOrganizationDB = ClientOrganizationTable()
UserClientMappingDB = UserClientMappingTable()
ClientUsageDB = ClientUsageTable()
ProcessedGenerationDB = ProcessedGenerationTable()