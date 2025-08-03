"""
Response DTOs for Usage Tracking API
All response models using Pydantic
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class WebhookResponse(BaseModel):
    """Webhook processing response"""
    status: str
    message: str


class SyncResultItem(BaseModel):
    """Individual sync result"""
    organization: str
    synced_generations: Optional[int] = None
    error: Optional[str] = None
    status: str


class SyncResponse(BaseModel):
    """Usage synchronization response"""
    status: str
    results: List[SyncResultItem]
    total_organizations: int


class UsageStatsResponse(BaseModel):
    """Real-time usage statistics response"""
    client_org_id: str
    date: str
    tokens: int
    requests: int
    cost: float
    last_updated: Any
    error: Optional[str] = None


class UserUsageItem(BaseModel):
    """Individual user usage data"""
    user_id: str
    user_name: str
    user_email: str
    external_user_id: str
    total_tokens: int
    markup_cost: float
    cost_pln: float
    days_active: int
    last_activity: Optional[str]
    user_mapping_enabled: bool
    error: Optional[str] = None


class UserUsageResponse(BaseModel):
    """User usage breakdown response"""
    success: bool
    user_usage: List[UserUsageItem]
    organization_name: str
    total_users: int
    user_mapping_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ModelUsageItem(BaseModel):
    """Individual model usage data"""
    model_name: str
    provider: str
    total_tokens: int
    markup_cost: float
    cost_pln: float
    days_used: int


class ModelUsageResponse(BaseModel):
    """Model usage breakdown response"""
    success: bool
    model_usage: List[ModelUsageItem]
    error: Optional[str] = None


class BillingResponse(BaseModel):
    """Subscription billing response"""
    success: bool
    subscription_data: Optional[Dict[str, Any]]
    error: Optional[str] = None


class ModelPricingItem(BaseModel):
    """Individual model pricing data"""
    id: str
    name: str
    provider: str
    price_per_million_input: float
    price_per_million_output: float
    context_length: int
    category: str


class ModelPricingResponse(BaseModel):
    """Model pricing response"""
    success: bool
    models: List[ModelPricingItem]
    last_updated: Optional[str] = None
    source: str
    error: Optional[str] = None


class OrganizationUsageSummaryResponse(BaseModel):
    """Organization usage summary response"""
    success: bool
    stats: Dict[str, Any]
    client_id: str
    error: Optional[str] = None