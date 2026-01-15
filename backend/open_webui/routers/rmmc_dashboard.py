"""
Tenant Dashboard Router
Proxies dashboard requests to rag-platform backend.
All sensitive data and Timestream queries are handled by rag-platform.
"""

import logging
import re
from typing import Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.models.tenants import Tenants
from open_webui.models.rmmc_dashboard import (
    TenantDashboardInfo,
    TenantDashboardConfig,
    AvailableTenantDashboards,
    OverviewResponse,
    OverviewMetric,
    LineMetrics,
    IncidentsResponse,
    Incident,
    TimeSeriesResponse,
    TimeSeriesPoint,
    IntensityResponse,
    IntensityStats,
    PartialRingResponse,
    PartialRingData,
    ImageUrlResponse,
    CacheClearResponse,
    OrientationResponse,
    OrientationBin,
    SystemHealthResponse,
    DeviceHealth,
)
from open_webui.services import timestream

logger = logging.getLogger(__name__)

router = APIRouter()

def _normalize_dashboard_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def _candidate_dashboard_ids_from_tenant(tenant) -> Set[str]:
    """
    Derive a set of dashboard tenant IDs that a non-admin user can access.

    We intentionally avoid introducing new schema fields by matching the rag-platform
    dashboard ID against identifiers already present on the tenant row.
    """
    candidates: Set[str] = set()

    def add(value: Optional[str]) -> None:
        if not value:
            return
        raw = value.strip().lower()
        if raw:
            candidates.add(raw)
        normalized = _normalize_dashboard_id(raw)
        if normalized:
            candidates.add(normalized)

    add(getattr(tenant, "s3_bucket", None))
    add(getattr(tenant, "table_name", None))
    add(getattr(tenant, "system_config_client_name", None))

    bucket = (getattr(tenant, "s3_bucket", "") or "").strip().lower()
    if bucket:
        tokens = [t for t in re.split(r"[^a-z0-9]+", bucket) if t]
        if tokens:
            first = tokens[0]
            last = tokens[-1]
            candidates.update({first, last, f"{first}_{last}", f"{first}{last}"})

    return {c for c in candidates if c}


def _get_allowed_dashboard_ids(user) -> Optional[Set[str]]:
    """
    Returns:
      - None for admin users (meaning "all dashboards allowed")
      - A set of allowed dashboard tenant IDs for non-admin users
    """
    if getattr(user, "role", None) == "admin":
        return None

    user_tenant_id = getattr(user, "tenant_id", None)
    if not user_tenant_id:
        raise HTTPException(status_code=403, detail="User is not associated with a tenant")

    tenant = Tenants.get_tenant_by_id(user_tenant_id)
    if not tenant:
        raise HTTPException(status_code=403, detail="Tenant not found for user")

    allowed = _candidate_dashboard_ids_from_tenant(tenant)
    if not allowed:
        raise HTTPException(status_code=403, detail="Tenant is not configured for dashboards")
    return allowed


def _require_dashboard_access(user, dashboard_tenant_id: str) -> None:
    allowed = _get_allowed_dashboard_ids(user)
    if allowed is None:
        return
    if dashboard_tenant_id.lower() not in allowed:
        raise HTTPException(status_code=403, detail="Dashboard is not available for this tenant")


# =============================================================================
# TENANT DISCOVERY ENDPOINTS
# =============================================================================

@router.get("/tenants", response_model=AvailableTenantDashboards)
async def get_available_dashboards(user=Depends(get_verified_user)):
    """Get list of available tenant dashboards"""
    try:
        tenants = await timestream.get_available_tenants()
        allowed = _get_allowed_dashboard_ids(user)
        if allowed is not None:
            tenants = [t for t in tenants if (t.get("id") or "").lower() in allowed]
        return AvailableTenantDashboards(
            tenants=[TenantDashboardInfo(**t) for t in tenants]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get available dashboards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}/config", response_model=TenantDashboardConfig)
async def get_tenant_config(tenant_id: str, user=Depends(get_verified_user)):
    """Get configuration for a specific tenant dashboard"""
    _require_dashboard_access(user, tenant_id)
    try:
        config = await timestream.get_tenant_config(tenant_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Tenant dashboard not found: {tenant_id}")
        return TenantDashboardConfig(**config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tenant config for {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# OVERVIEW ENDPOINTS
# =============================================================================

@router.get("/tenants/{tenant_id}/overview", response_model=OverviewResponse)
async def get_overview(
    tenant_id: str,
    days: int = Query(default=7, ge=1, le=30),
    user=Depends(get_verified_user)
):
    """Get overview DPMO metrics for all lines of a tenant"""
    _require_dashboard_access(user, tenant_id)
    try:
        metrics = await timestream.get_overview_metrics(tenant_id=tenant_id, days=days)
        return OverviewResponse(
            tenant_id=tenant_id,
            metrics=[OverviewMetric(**m) for m in metrics],
            period_days=days,
        )
    except Exception as e:
        logger.error(f"Failed to get overview metrics for {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LINE-SPECIFIC ENDPOINTS
# =============================================================================

@router.get("/tenants/{tenant_id}/lines/{line_id}/metrics", response_model=LineMetrics)
async def get_line_metrics(
    tenant_id: str,
    line_id: str,
    system: str = Query(default="uvbc"),
    days: int = Query(default=7, ge=1, le=30),
    user=Depends(get_verified_user)
):
    """Get detailed metrics for a specific line"""
    _require_dashboard_access(user, tenant_id)
    try:
        metrics = await timestream.get_line_metrics(
            tenant_id=tenant_id,
            line_id=line_id,
            system=system,
            days=days
        )
        if "error" in metrics:
            raise HTTPException(status_code=400, detail=metrics["error"])
        return LineMetrics(**metrics)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get line metrics for {tenant_id}/{line_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}/lines/{line_id}/incidents", response_model=IncidentsResponse)
async def get_line_incidents(
    tenant_id: str,
    line_id: str,
    system: str = Query(default="washer"),
    limit: int = Query(default=50, ge=1, le=200),
    large_only: bool = Query(default=False),
    days: int = Query(default=7, ge=1, le=30),
    user=Depends(get_verified_user)
):
    """Get incident records for a line"""
    _require_dashboard_access(user, tenant_id)
    try:
        incidents = await timestream.get_incidents(
            tenant_id=tenant_id,
            line_id=line_id,
            system=system,
            limit=limit,
            large_only=large_only,
            days=days,
        )
        return IncidentsResponse(
            tenant_id=tenant_id,
            line_id=line_id,
            incidents=[Incident(**i) for i in incidents],
            total=len(incidents),
        )
    except Exception as e:
        logger.error(f"Failed to get incidents for {tenant_id}/{line_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}/lines/{line_id}/timeseries", response_model=TimeSeriesResponse)
async def get_line_timeseries(
    tenant_id: str,
    line_id: str,
    metric: str = Query(default="down"),
    system: str = Query(default="uvbc"),
    days: int = Query(default=14, ge=1, le=30),
    user=Depends(get_verified_user)
):
    """Get time series data for charting"""
    _require_dashboard_access(user, tenant_id)
    try:
        data = await timestream.get_time_series(
            tenant_id=tenant_id,
            line_id=line_id,
            system=system,
            metric=metric,
            days=days,
        )
        return TimeSeriesResponse(
            tenant_id=tenant_id,
            line_id=line_id,
            metric=metric,
            data=[TimeSeriesPoint(**d) for d in data],
            period_days=days,
        )
    except Exception as e:
        logger.error(f"Failed to get time series for {tenant_id}/{line_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}/lines/{line_id}/orientation", response_model=OrientationResponse)
async def get_line_orientation(
    tenant_id: str,
    line_id: str,
    system: str = Query(default="washer"),
    defect_type: str = Query(default="down"),
    days: int = Query(default=7, ge=1, le=30),
    bin_size: int = Query(default=100, ge=10, le=500),
    user=Depends(get_verified_user)
):
    """Get defect location distribution (x-position histogram)"""
    _require_dashboard_access(user, tenant_id)
    try:
        result = await timestream.get_orientation_data(
            tenant_id=tenant_id,
            line_id=line_id,
            system=system,
            defect_type=defect_type,
            days=days,
            bin_size=bin_size,
        )
        return OrientationResponse(
            tenant_id=tenant_id,
            line_id=line_id,
            system=system,
            defect_type=result.get("defect_type", defect_type),
            bin_size=result.get("bin_size", bin_size),
            data=[OrientationBin(**d) for d in result.get("data", [])],
        )
    except Exception as e:
        logger.error(f"Failed to get orientation for {tenant_id}/{line_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# UVBC-SPECIFIC ENDPOINTS
# =============================================================================

@router.get("/tenants/{tenant_id}/uvbc/{line_id}/intensity", response_model=IntensityResponse)
async def get_uvbc_intensity(
    tenant_id: str,
    line_id: str,
    days: int = Query(default=7, ge=1, le=30),
    user=Depends(get_verified_user)
):
    """Get UVBC ring intensity data for a line"""
    _require_dashboard_access(user, tenant_id)
    try:
        result = await timestream.get_uvbc_intensity(tenant_id=tenant_id, line_id=line_id, days=days)
        intensity_data = result.get("data", [])
        return IntensityResponse(
            tenant_id=tenant_id,
            line_id=line_id,
            data=[IntensityStats(**d) for d in intensity_data],
        )
    except Exception as e:
        logger.error(f"Failed to get UVBC intensity for {tenant_id}/{line_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}/uvbc/{line_id}/partials", response_model=PartialRingResponse)
async def get_partial_ring_data(
    tenant_id: str,
    line_id: str,
    days: int = Query(default=7, ge=1, le=30),
    user=Depends(get_verified_user)
):
    """Get partial ring percentage distribution"""
    _require_dashboard_access(user, tenant_id)
    try:
        data = await timestream.get_partial_ring_data(tenant_id=tenant_id, line_id=line_id, days=days)
        return PartialRingResponse(
            tenant_id=tenant_id,
            line_id=line_id,
            data=[PartialRingData(**d) for d in data],
        )
    except Exception as e:
        logger.error(f"Failed to get partial ring data for {tenant_id}/{line_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@router.get("/tenants/{tenant_id}/incidents/{uuid}/image-url", response_model=ImageUrlResponse)
async def get_incident_image_url(
    tenant_id: str,
    uuid: str,
    user=Depends(get_verified_user)
):
    """Get image URL for an incident"""
    _require_dashboard_access(user, tenant_id)
    if not uuid:
        raise HTTPException(status_code=400, detail="UUID is required")

    try:
        image_url = await timestream.generate_incident_image_url(tenant_id=tenant_id, uuid=uuid)
        if not image_url:
            raise HTTPException(status_code=404, detail="Image not found")
        return ImageUrlResponse(tenant_id=tenant_id, uuid=uuid, image_url=image_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image URL for {uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear", response_model=CacheClearResponse)
async def clear_cache(user=Depends(get_admin_user)):
    """Clear all dashboard caches (admin only)"""
    try:
        await timestream.clear_cache()
        return CacheClearResponse(status="ok", message="Cache cleared successfully")
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SYSTEM HEALTH ENDPOINTS
# =============================================================================

@router.get("/tenants/{tenant_id}/health", response_model=SystemHealthResponse)
async def get_system_health(
    tenant_id: str,
    minutes: int = Query(default=30, ge=5, le=120),
    user=Depends(get_verified_user)
):
    """Get system health status for all devices of a tenant"""
    _require_dashboard_access(user, tenant_id)
    try:
        result = await timestream.get_system_health(tenant_id=tenant_id, minutes=minutes)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return SystemHealthResponse(
            tenant_id=tenant_id,
            devices=[DeviceHealth(**d) for d in result.get("devices", [])],
            timestamp=result.get("timestamp", "")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system health for {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
