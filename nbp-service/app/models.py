"""
Data models for NBP Service
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class ExchangeRateResponse(BaseModel):
    """Exchange rate response model"""
    currency: str = Field(default="USD", description="Currency code")
    rate: float = Field(description="Exchange rate to PLN")
    date: str = Field(description="Date of the exchange rate")
    source: str = Field(description="Data source (mock/nbp)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(description="Service health status")
    mode: str = Field(description="Service mode (mock/live)")
    timestamp: datetime = Field(description="Current timestamp")


class NBPApiResponse(BaseModel):
    """NBP API response model"""
    table: str
    currency: str
    code: str
    rates: List[dict]