"""
Request DTOs for Usage Tracking API
All request validation models using Pydantic
"""

from typing import Optional
from pydantic import BaseModel, Field


class UsageWebhookPayload(BaseModel):
    """OpenRouter usage webhook payload structure"""
    api_key: str
    user_id: Optional[str] = None
    model: str
    tokens_used: int
    cost: float
    timestamp: str
    external_user: Optional[str] = None
    request_id: Optional[str] = None


class UsageSyncRequest(BaseModel):
    """Manual usage sync request"""
    days_back: int = Field(default=1, ge=1, le=30)


class ManualUsageRequest(BaseModel):
    """Manual usage recording request"""
    model: str
    tokens: int = Field(gt=0)
    cost: float = Field(gt=0.0)