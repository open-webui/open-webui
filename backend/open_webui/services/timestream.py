"""
Dashboard Data Service
Proxies requests to the rag-platform backend for tenant dashboard data.
All sensitive Timestream queries and tenant configurations are handled by rag-platform.
"""

import os
import logging
import aiohttp
import json
import asyncio
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# RAG Platform endpoint - configured via environment
RAG_PLATFORM_URL = os.getenv("RAG_PLATFORM_URL", "http://localhost:9000/2015-03-31/functions/function/invocations")

# The AWS Lambda runtime container only processes one invocation at a time. The
# local emulator can crash if it receives overlapping requests, so we serialize
# calls through a single async lock.
_rag_platform_lock = asyncio.Lock()


async def _invoke_rag_platform(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke the rag-platform Lambda for dashboard data.

    Args:
        action: The dashboard action to perform (e.g., "dashboard_overview", "dashboard_line_metrics")
        params: Parameters for the action

    Returns:
        Response data from rag-platform
    """
    payload = {
        "action": action,
        "params": params
    }

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with _rag_platform_lock:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        RAG_PLATFORM_URL,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Rag-platform error: {response.status} - {error_text}")
                            raise Exception(f"Rag-platform returned {response.status}")

                        raw_text = await response.text()
                        try:
                            result = json.loads(raw_text)
                        except json.JSONDecodeError as e:
                            logger.error(
                                "Failed to decode rag-platform response as JSON: "
                                f"status={response.status} content_type={response.headers.get('Content-Type')} "
                                f"error={e} body_prefix={raw_text[:500]!r}"
                            )
                            raise Exception("Dashboard backend returned invalid JSON") from e

                        # Handle Lambda response format (may have statusCode/body wrapper)
                        if isinstance(result, dict) and "statusCode" in result:
                            if result.get("statusCode") != 200:
                                raise Exception(
                                    f"Lambda returned status {result.get('statusCode')}: {result.get('body')}"
                                )
                            body = result.get("body", "{}")
                            if isinstance(body, str):
                                return json.loads(body)
                            return body

                        return result
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_error = e
            if attempt < 2:
                await asyncio.sleep(0.25 * (2**attempt))
                continue
            logger.error(f"Failed to connect to rag-platform: {e}")
            raise Exception(f"Failed to connect to dashboard backend: {str(e)}") from e

    raise Exception(f"Failed to connect to dashboard backend: {last_error}")


async def get_available_tenants() -> List[Dict[str, str]]:
    """Get list of available tenant dashboards"""
    result = await _invoke_rag_platform("dashboard_get_tenants", {})
    return result.get("tenants", [])


async def get_tenant_config(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get dashboard configuration for a tenant"""
    result = await _invoke_rag_platform("dashboard_get_config", {"tenant_id": tenant_id})
    return result.get("config")


async def get_overview_metrics(tenant_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """Get overview DPMO metrics for all lines of a tenant"""
    result = await _invoke_rag_platform("dashboard_overview", {
        "tenant_id": tenant_id,
        "days": days
    })
    return result.get("metrics", [])


async def get_line_metrics(tenant_id: str, line_id: str, system: str = "uvbc", days: int = 7) -> Dict[str, Any]:
    """Get detailed metrics for a specific line"""
    result = await _invoke_rag_platform("dashboard_line_metrics", {
        "tenant_id": tenant_id,
        "line_id": line_id,
        "system": system,
        "days": days
    })
    return result.get("metrics", {})


async def get_incidents(
    tenant_id: str,
    line_id: str,
    system: str = "washer",
    limit: int = 50,
    large_only: bool = False,
    days: int = 7
) -> List[Dict[str, Any]]:
    """Get incident records for a line"""
    result = await _invoke_rag_platform("dashboard_incidents", {
        "tenant_id": tenant_id,
        "line_id": line_id,
        "system": system,
        "limit": limit,
        "large_only": large_only,
        "days": days
    })
    return result.get("incidents", [])


async def get_time_series(
    tenant_id: str,
    line_id: str,
    system: str = "uvbc",
    metric: str = "down",
    days: int = 14
) -> List[Dict[str, Any]]:
    """Get time series data for charting"""
    result = await _invoke_rag_platform("dashboard_timeseries", {
        "tenant_id": tenant_id,
        "line_id": line_id,
        "system": system,
        "metric": metric,
        "days": days
    })
    return result.get("data", [])


async def get_uvbc_intensity(tenant_id: str, line_id: str, days: int = 7, mode: str = "daily") -> Dict[str, Any]:
    """Get UVBC ring intensity data"""
    result = await _invoke_rag_platform("dashboard_uvbc_intensity", {
        "tenant_id": tenant_id,
        "line_id": line_id,
        "days": days,
        "mode": mode
    })
    return result


async def get_orientation_data(
    tenant_id: str,
    line_id: str,
    system: str = "washer",
    defect_type: str = "down",
    days: int = 7,
    bin_size: int = 100
) -> Dict[str, Any]:
    """Get defect location distribution (x-position histogram)"""
    result = await _invoke_rag_platform("dashboard_orientation", {
        "tenant_id": tenant_id,
        "line_id": line_id,
        "system": system,
        "defect_type": defect_type,
        "days": days,
        "bin_size": bin_size
    })
    return result


async def get_partial_ring_data(tenant_id: str, line_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """Get partial ring percentage distribution"""
    result = await _invoke_rag_platform("dashboard_partial_rings", {
        "tenant_id": tenant_id,
        "line_id": line_id,
        "days": days
    })
    return result.get("data", [])


async def generate_incident_image_url(tenant_id: str, uuid: str) -> Optional[str]:
    """Generate URL for incident image"""
    result = await _invoke_rag_platform("dashboard_incident_image", {
        "tenant_id": tenant_id,
        "uuid": uuid
    })
    return result.get("image_url")


async def clear_cache() -> None:
    """Clear dashboard caches on rag-platform"""
    await _invoke_rag_platform("dashboard_clear_cache", {})


async def get_system_health(tenant_id: str, minutes: int = 30) -> Dict[str, Any]:
    """Get system health status for all devices of a tenant"""
    result = await _invoke_rag_platform("dashboard_system_health", {
        "tenant_id": tenant_id,
        "minutes": minutes
    })
    return result
