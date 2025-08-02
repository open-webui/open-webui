"""
Domain Models for Organization Usage Tracking
Pure business entities with no external dependencies (Clean Architecture Domain Layer)
"""
from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


####################
# Core Domain Models (Pydantic)
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


####################
# Input/Output Models (Forms and Responses)
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
    """Admin-focused daily breakdown stats (no real-time)"""
    current_month: dict  # Current month totals and summary
    daily_breakdown: List[dict]  # Daily summaries for current month
    monthly_summary: dict  # Statistical summary for the month
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
# Value Objects and DTOs
####################


class UsageRecordDTO(BaseModel):
    """Data Transfer Object for usage recording operations"""
    client_org_id: str
    user_id: str
    openrouter_user_id: str
    model_name: str
    usage_date: date
    input_tokens: int = 0
    output_tokens: int = 0
    raw_cost: float = 0.0
    markup_cost: float = 0.0
    provider: Optional[str] = None
    request_metadata: Optional[dict] = None

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens"""
        return self.input_tokens + self.output_tokens


# ProcessedGenerationInfo removed - InfluxDB-First architecture
# handles deduplication via request_id tags, no longer needed


class CleanupStatsResult(BaseModel):
    """Result of cleanup operations with detailed statistics"""
    success: bool
    cutoff_date: str
    days_to_keep: int
    records_before: int
    records_deleted: int
    records_remaining: int
    old_tokens_removed: int
    old_cost_removed: float
    storage_saved_kb: float
    cleanup_duration_seconds: float
    organization_breakdown: Dict[str, Dict[str, Any]]
    cleanup_timestamp: int
    error: Optional[str] = None