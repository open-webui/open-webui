"""
Data models for batch processing results
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field


class BatchOperationResult(BaseModel):
    """Base model for batch operation results"""
    success: bool
    operation: str
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ExchangeRateResult(BaseModel):
    """Result of exchange rate update operation"""
    success: bool
    usd_pln_rate: float
    effective_date: Optional[str] = None
    rate_source: str = "unknown"
    fetched_at: str
    error: Optional[str] = None


class PricingUpdateResult(BaseModel):
    """Result of model pricing update"""
    success: bool
    models_count: int = 0
    source: str = "unknown"
    last_updated: Optional[str] = None
    fetched_at: str
    error: Optional[str] = None


class ClientConsolidationStats(BaseModel):
    """Statistics for a single client's usage consolidation"""
    client_id: int
    client_name: str
    tokens: int
    requests: int
    raw_cost: float
    markup_cost: float
    markup_rate: float
    primary_model: Optional[str] = None
    data_validated: bool = True
    markup_cost_corrected: Optional[Dict[str, float]] = None
    # InfluxDB-First specific fields
    raw_records_processed: Optional[int] = None
    data_source: Optional[str] = None


class UsageConsolidationResult(BaseModel):
    """Result of daily usage consolidation"""
    success: bool
    processing_date: str
    clients_processed: int = 0
    total_records_verified: int = 0
    data_corrections: int = 0
    clients_data: List[ClientConsolidationStats] = Field(default_factory=list)
    error: Optional[str] = None
    # InfluxDB-First specific fields
    influxdb_records_processed: Optional[int] = None
    data_source: Optional[str] = None


class ClientMonthlyStats(BaseModel):
    """Monthly statistics for a single client"""
    client_id: int
    client_name: str
    days_with_usage: int
    days_in_month: int
    usage_percentage: float
    total_tokens: int
    total_requests: int
    total_raw_cost: float
    total_markup_cost: float
    average_daily_tokens: int
    max_daily_tokens: int
    most_used_model: Optional[str] = None
    last_usage_date: Optional[str] = None


class MonthlyTotalsResult(BaseModel):
    """Result of monthly totals calculation"""
    success: bool
    processing_date: str
    month_range: str
    clients_processed: int = 0
    monthly_summaries: List[ClientMonthlyStats] = Field(default_factory=list)
    overall_totals: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CleanupResult(BaseModel):
    """Result of data cleanup operation"""
    success: bool
    records_deleted: int = 0
    storage_saved_kb: int = 0
    error: Optional[str] = None


class BatchResult(BaseModel):
    """Overall batch processing result"""
    success: bool
    processing_date: str
    current_date: str
    batch_start_time: str
    completed_at: Optional[str] = None
    batch_duration_seconds: Optional[float] = None
    operations: List[BatchOperationResult] = Field(default_factory=list)
    error: Optional[str] = None
    # Additional fields
    batch_end_time: Optional[str] = None
    total_duration_seconds: Optional[float] = None
    data_source: Optional[str] = None


class InfluxDBBatchRunRecord(BaseModel):
    """Model for tracking InfluxDB batch processing runs"""
    id: Optional[int] = None
    processing_date: date
    batch_start_time: datetime
    batch_end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success: bool
    clients_processed: int = 0
    influxdb_records_processed: int = 0
    sqlite_summaries_created: int = 0
    data_corrections: int = 0
    error_message: Optional[str] = None
    data_source: str = "influxdb_first"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None