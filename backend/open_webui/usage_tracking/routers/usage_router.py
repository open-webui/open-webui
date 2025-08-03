"""
Usage Router - HTTP endpoints for usage tracking and analytics
Handles real-time usage data and organizational statistics
"""

from fastapi import APIRouter, Depends
from open_webui.utils.auth import get_current_user
from ..models.responses import (
    UsageStatsResponse, OrganizationUsageSummaryResponse,
    UserUsageResponse, ModelUsageResponse
)
from ..services.usage_service import UsageService
from ..services.billing_service import BillingService

usage_router = APIRouter()
usage_service = UsageService()
billing_service = BillingService()


@usage_router.get("/usage/real-time/{client_org_id}", response_model=UsageStatsResponse)
async def get_real_time_usage(
    client_org_id: str,
    user=Depends(get_current_user)
):
    """Get real-time usage data for a client organization"""
    try:
        result = usage_service.get_real_time_usage(client_org_id)
        return UsageStatsResponse(**result)
        
    except Exception as e:
        # Return minimal stats on error
        return UsageStatsResponse(
            client_org_id=client_org_id,
            date="error",
            tokens=0,
            requests=0,
            cost=0.0,
            last_updated="error",
            error=str(e)
        )


@usage_router.get("/my-organization/usage-summary", response_model=OrganizationUsageSummaryResponse)
async def get_my_organization_usage_summary(user=Depends(get_current_user)):
    """Get admin-focused daily breakdown for current organization (no real-time)"""
    try:
        result = await usage_service.get_organization_usage_summary()
        return OrganizationUsageSummaryResponse(**result)
        
    except Exception as e:
        return OrganizationUsageSummaryResponse(
            success=False,
            error=str(e),
            stats={},
            client_id="error"
        )


@usage_router.get("/my-organization/usage-by-user", response_model=UserUsageResponse)
async def get_my_organization_usage_by_user(user=Depends(get_current_user)):
    """Get usage breakdown by user for the current organization (environment-based)"""
    try:
        result = await billing_service.get_user_usage_breakdown()
        return UserUsageResponse(**result)
        
    except Exception as e:
        from open_webui.config import ORGANIZATION_NAME
        return UserUsageResponse(
            success=False,
            error=str(e),
            user_usage=[],
            organization_name=ORGANIZATION_NAME or "My Organization",
            total_users=0
        )


@usage_router.get("/my-organization/usage-by-model", response_model=ModelUsageResponse)
async def get_my_organization_usage_by_model(user=Depends(get_current_user)):
    """Get usage breakdown by model for the current organization (environment-based)"""
    try:
        result = await billing_service.get_model_usage_breakdown()
        return ModelUsageResponse(**result)
        
    except Exception as e:
        return ModelUsageResponse(
            success=False,
            error=str(e),
            model_usage=[]
        )