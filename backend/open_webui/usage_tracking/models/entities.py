"""
Domain entities for Usage Tracking
Core business objects and data structures
"""

from typing import Dict, Any, Optional
from datetime import date
from pydantic import BaseModel


class UsageRecord(BaseModel):
    """Core usage record entity"""
    client_org_id: str
    user_id: str
    openrouter_user_id: str
    model_name: str
    usage_date: date
    input_tokens: int
    output_tokens: int
    raw_cost: float
    markup_cost: float
    provider: str
    request_metadata: Dict[str, Any]


class ClientInfo(BaseModel):
    """Client organization information"""
    id: str
    name: str
    markup_rate: float
    is_active: bool
    openrouter_api_key: Optional[str] = None


class BillingInfo(BaseModel):
    """Billing calculation data"""
    user_id: str
    user_name: str
    user_email: str
    created_date: str
    days_remaining_when_added: int
    billing_proportion: float
    monthly_cost_pln: float