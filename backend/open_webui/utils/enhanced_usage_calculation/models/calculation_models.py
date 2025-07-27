"""
Calculation models - DTOs for calculator operations
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import date as DateType, datetime
from pydantic import BaseModel, Field


class AggregationType(str, Enum):
    """Types of usage aggregation"""
    DAILY = "daily"
    MONTHLY = "monthly"
    USER = "user"
    MODEL = "model"
    CUSTOM = "custom"


class CalculationRequest(BaseModel):
    """Request parameters for usage calculation"""
    
    client_org_id: str = Field(..., description="Client organization ID")
    aggregation_type: AggregationType = Field(..., description="Type of aggregation")
    start_date: Optional[DateType] = Field(None, description="Start date for calculation")
    end_date: Optional[DateType] = Field(None, description="End date for calculation")
    use_client_timezone: bool = Field(True, description="Use client's timezone")
    prevent_double_counting: bool = Field(True, description="Enable double counting prevention")
    include_details: bool = Field(False, description="Include detailed breakdowns")
    
    # Optional filters
    user_ids: Optional[List[str]] = Field(None, description="Filter by specific users")
    model_names: Optional[List[str]] = Field(None, description="Filter by specific models")
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_org_id": "org_123",
                "aggregation_type": "monthly",
                "use_client_timezone": True,
                "prevent_double_counting": True
            }
        }


class CalculationContext(BaseModel):
    """Context for calculation execution"""
    
    request: CalculationRequest
    client_timezone: str = Field("Europe/Warsaw", description="Client's timezone")
    client_name: str = Field("Unknown", description="Client organization name")
    today: DateType = Field(..., description="Current date in client timezone")
    month_start: DateType = Field(..., description="Start of current month")
    calculation_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Performance tracking
    cache_hits: int = Field(0, description="Number of cache hits")
    cache_misses: int = Field(0, description="Number of cache misses")
    query_count: int = Field(0, description="Number of database queries")
    
    class Config:
        arbitrary_types_allowed = True


class CalculationResult(BaseModel):
    """Result of usage calculation"""
    
    success: bool = Field(..., description="Whether calculation succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Calculation results")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    # Performance metrics
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    cache_hit_rate: float = Field(0.0, description="Cache hit rate (0-1)")
    queries_executed: int = Field(0, description="Number of DB queries executed")
    
    # Metadata
    calculation_type: AggregationType
    timestamp: datetime = Field(default_factory=datetime.now)
    client_org_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_tokens": 150000,
                    "total_cost": 2.5,
                    "total_requests": 100
                },
                "execution_time_ms": 45.2,
                "cache_hit_rate": 0.8,
                "calculation_type": "monthly",
                "client_org_id": "org_123"
            }
        }