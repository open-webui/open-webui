import time
from typing import Optional, List
from datetime import datetime, date

from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Float, Date, Index
from sqlalchemy.orm import relationship


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


class ClientOrganization(Base):
    __tablename__ = "client_organizations"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    openrouter_api_key = Column(Text, nullable=False, unique=True)  # Dedicated key per client
    openrouter_key_hash = Column(String, nullable=True)  # OpenRouter's key identifier
    markup_rate = Column(Float, default=1.3)
    monthly_limit = Column(Float, nullable=True)  # Optional spending limit
    billing_email = Column(String, nullable=True)
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
                    openrouter_api_key=api_key, is_active=1
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


class ClientUsageTable:
    """
    Option 1: Simplified usage tracking with daily summaries + live counters
    """
    
    def record_usage(
        self,
        client_org_id: str,
        tokens: int = 0,
        raw_cost: float = 0.0,
        markup_cost: float = 0.0,
        model_name: str = None
    ) -> bool:
        """
        Record API usage - update live counters immediately for real-time UI
        """
        try:
            with get_db() as db:
                today = date.today()
                current_time = int(time.time())
                
                # Get or create live counter for today
                live_counter = db.query(ClientLiveCounters).filter_by(
                    client_org_id=client_org_id
                ).first()
                
                if live_counter:
                    # Check if it's still today
                    if live_counter.current_date != today:
                        # New day - reset counters after storing yesterday's data
                        self._rollup_to_daily_summary(db, live_counter)
                        live_counter.current_date = today
                        live_counter.today_tokens = 0
                        live_counter.today_requests = 0
                        live_counter.today_raw_cost = 0.0
                        live_counter.today_markup_cost = 0.0
                    
                    # Update today's counters
                    live_counter.today_tokens += tokens
                    live_counter.today_requests += 1
                    live_counter.today_raw_cost += raw_cost
                    live_counter.today_markup_cost += markup_cost
                    live_counter.last_updated = current_time
                else:
                    # Create new live counter
                    live_counter = ClientLiveCounters(
                        client_org_id=client_org_id,
                        current_date=today,
                        today_tokens=tokens,
                        today_requests=1,
                        today_raw_cost=raw_cost,
                        today_markup_cost=markup_cost,
                        last_updated=current_time
                    )
                    db.add(live_counter)
                
                db.commit()
                return True
        except Exception as e:
            print(f"Error recording usage: {e}")
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
        self, client_org_id: str
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
                
                if live_counter and live_counter.current_date == date.today():
                    today_data = {
                        'tokens': live_counter.today_tokens,
                        'cost': live_counter.today_markup_cost,
                        'requests': live_counter.today_requests,
                        'last_updated': datetime.fromtimestamp(live_counter.last_updated).strftime('%H:%M:%S')
                    }
                
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


# Singleton instances
GlobalSettingsDB = GlobalSettingsTable()
ClientOrganizationDB = ClientOrganizationTable()
UserClientMappingDB = UserClientMappingTable()
ClientUsageDB = ClientUsageTable()