"""
Dashboard Data Service
Proxies requests to the rag-platform backend for tenant dashboard data.
All sensitive Timestream queries and tenant configurations are handled by rag-platform.
"""

import os
import logging
import aiohttp
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# RAG Platform endpoint - configured via environment
RAG_PLATFORM_URL = os.getenv("RAG_PLATFORM_URL", "http://localhost:9000/2015-03-31/functions/function/invocations")


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

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                RAG_PLATFORM_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Rag-platform error: {response.status} - {error_text}")
                    raise Exception(f"Rag-platform returned {response.status}")

                result = await response.json()

                # Handle Lambda response format (may have statusCode/body wrapper)
                if isinstance(result, dict) and "statusCode" in result:
                    if result.get("statusCode") != 200:
                        raise Exception(f"Lambda returned status {result.get('statusCode')}: {result.get('body')}")
                    body = result.get("body", "{}")
                    if isinstance(body, str):
                        import json
                        return json.loads(body)
                    return body

                return result
    except aiohttp.ClientError as e:
        logger.error(f"Failed to connect to rag-platform: {e}")
        raise Exception(f"Failed to connect to dashboard backend: {str(e)}")


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


async def get_uvbc_intensity(tenant_id: str, line_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """Get UVBC ring intensity data"""
    result = await _invoke_rag_platform("dashboard_uvbc_intensity", {
        "tenant_id": tenant_id,
        "line_id": line_id,
        "days": days
    })
    return result.get("data", [])


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
