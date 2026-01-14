"""
Pydantic models for Tenant Dashboard API responses
Generic models - no sensitive tenant configurations
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# =============================================================================
# TENANT CONFIGURATION MODELS
# =============================================================================

class TenantDashboardInfo(BaseModel):
    """Basic tenant dashboard info"""
    id: str
    display_name: str


class TenantDashboardConfig(BaseModel):
    """Tenant dashboard configuration (populated by rag-platform)"""
    id: str
    display_name: str
    available_lines: List[str]
    available_systems: List[str]
    line_systems: Optional[Dict[str, List[str]]] = None
    metrics: Dict[str, Dict[str, str]]
    default_period_days: int = 7


class AvailableTenantDashboards(BaseModel):
    """List of available tenant dashboards"""
    tenants: List[TenantDashboardInfo]


# =============================================================================
# METRICS MODELS
# =============================================================================

class OverviewMetric(BaseModel):
    """Single line/device overview metric"""
    device_id: Optional[str] = None
    line: Optional[str] = None
    system: Optional[str] = None
    total_units: int
    defect_count: int
    dpmo: float
    change_percent: float = 0.0


class OverviewResponse(BaseModel):
    """Overview metrics for all lines"""
    tenant_id: str
    metrics: List[OverviewMetric]
    period_days: int = 7


class LineMetrics(BaseModel):
    """Detailed metrics for a specific line"""
    tenant_id: str
    line_id: str
    system: str
    device_id: Optional[str] = None
    avg_fps: float = 0.0
    metrics: Dict[str, Any] = {}


# =============================================================================
# INCIDENT MODELS
# =============================================================================

class Incident(BaseModel):
    """Single incident record"""
    time: str
    device_id: Optional[str] = None
    line_id: str
    system: str
    inc_hits: int
    down: int
    inverted: int
    down_conf: float
    inverted_conf: float
    uuid: Optional[str] = None
    image_url: Optional[str] = None


class IncidentsResponse(BaseModel):
    """List of incidents"""
    tenant_id: str
    line_id: str
    incidents: List[Incident]
    total: int


# =============================================================================
# TIME SERIES MODELS
# =============================================================================

class TimeSeriesPoint(BaseModel):
    """Single time series data point"""
    time: str
    value: float


class TimeSeriesResponse(BaseModel):
    """Time series data for charting"""
    tenant_id: str
    line_id: str
    metric: str
    data: List[TimeSeriesPoint]
    period_days: int


# =============================================================================
# UVBC SPECIFIC MODELS
# =============================================================================

class IntensityStats(BaseModel):
    """UVBC ring intensity statistics"""
    time: str
    ring: int
    average_intensity: float
    min_intensity: float
    max_intensity: float
    median_intensity: float
    std_deviation: float


class IntensityResponse(BaseModel):
    """UVBC intensity data"""
    tenant_id: str
    line_id: str
    data: List[IntensityStats]


class PartialRingData(BaseModel):
    """Partial ring percentage distribution"""
    ring_percentage: float
    count: int


class PartialRingResponse(BaseModel):
    """Partial ring data response"""
    tenant_id: str
    line_id: str
    data: List[PartialRingData]


# =============================================================================
# UTILITY MODELS
# =============================================================================

class ImageUrlResponse(BaseModel):
    """Incident image URL response"""
    tenant_id: str
    uuid: str
    image_url: str


class CacheClearResponse(BaseModel):
    """Cache clear response"""
    status: str
    message: str
