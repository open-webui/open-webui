"""
Result models - DTOs for calculation results
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date as DateType, datetime
from pydantic import BaseModel, Field


class DailyUsageData(BaseModel):
    """Daily usage data point"""
    
    date: DateType = Field(..., description="Usage date")
    tokens: int = Field(0, description="Total tokens used")
    cost: float = Field(0.0, description="Total cost with markup")
    requests: int = Field(0, description="Total requests made")
    
    # Optional breakdown
    input_tokens: Optional[int] = Field(None, description="Input tokens")
    output_tokens: Optional[int] = Field(None, description="Output tokens")
    raw_cost: Optional[float] = Field(None, description="Cost before markup")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15",
                "tokens": 5000,
                "cost": 0.15,
                "requests": 10
            }
        }


class MonthlyUsageData(BaseModel):
    """Monthly usage summary"""
    
    tokens: int = Field(0, description="Total tokens this month")
    cost: float = Field(0.0, description="Total cost this month")
    requests: int = Field(0, description="Total requests this month")
    days_active: int = Field(0, description="Days with usage")
    
    # Additional metrics
    average_daily_tokens: float = Field(0.0, description="Average tokens per day")
    average_daily_cost: float = Field(0.0, description="Average cost per day")
    projected_month_cost: Optional[float] = Field(None, description="Projected month-end cost")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tokens": 150000,
                "cost": 4.5,
                "requests": 300,
                "days_active": 15,
                "average_daily_tokens": 10000,
                "average_daily_cost": 0.3
            }
        }


class UserUsageData(BaseModel):
    """Per-user usage data"""
    
    user_id: str = Field(..., description="User ID")
    user_name: Optional[str] = Field(None, description="User display name")
    tokens: int = Field(0, description="Total tokens used")
    cost: float = Field(0.0, description="Total cost")
    requests: int = Field(0, description="Total requests")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    
    # Usage breakdown
    models_used: Optional[Dict[str, int]] = Field(None, description="Token count by model")
    daily_usage: Optional[List[DailyUsageData]] = Field(None, description="Daily breakdown")


class ModelUsageData(BaseModel):
    """Per-model usage data"""
    
    model_name: str = Field(..., description="Model name")
    provider: Optional[str] = Field(None, description="Model provider")
    tokens: int = Field(0, description="Total tokens used")
    cost: float = Field(0.0, description="Total cost")
    requests: int = Field(0, description="Total requests")
    
    # Cost breakdown
    input_tokens: Optional[int] = Field(None, description="Input tokens")
    output_tokens: Optional[int] = Field(None, description="Output tokens")
    average_cost_per_request: Optional[float] = Field(None, description="Average cost per request")


class ClientUsageStats(BaseModel):
    """Complete usage statistics for a client"""
    
    client_org_id: str = Field(..., description="Client organization ID")
    client_org_name: str = Field(..., description="Client organization name")
    
    # Current period data
    today: DailyUsageData = Field(..., description="Today's usage")
    this_month: MonthlyUsageData = Field(..., description="This month's usage")
    
    # Historical data
    daily_history: List[DailyUsageData] = Field(
        default_factory=list, 
        description="Daily usage history"
    )
    
    # Optional breakdowns
    user_breakdown: Optional[List[UserUsageData]] = Field(
        None, 
        description="Usage by user"
    )
    model_breakdown: Optional[List[ModelUsageData]] = Field(
        None, 
        description="Usage by model"
    )
    
    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.now)
    timezone: str = Field("Europe/Warsaw", description="Client timezone")
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_org_id": "org_123",
                "client_org_name": "Example Corp",
                "today": {
                    "date": "2024-01-15",
                    "tokens": 5000,
                    "cost": 0.15,
                    "requests": 10
                },
                "this_month": {
                    "tokens": 150000,
                    "cost": 4.5,
                    "requests": 300,
                    "days_active": 15
                },
                "daily_history": []
            }
        }