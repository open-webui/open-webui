"""
Main router aggregation for Usage Tracking
Combines all routers with proper prefix and tagging
"""

from fastapi import APIRouter
from .routers.webhook_router import webhook_router
from .routers.usage_router import usage_router
from .routers.billing_router import billing_router

# Create main router for usage tracking
usage_tracking_router = APIRouter()

# Include all sub-routers
usage_tracking_router.include_router(webhook_router, tags=["webhooks"])
usage_tracking_router.include_router(usage_router, tags=["usage"])
usage_tracking_router.include_router(billing_router, tags=["billing"])

__all__ = ["usage_tracking_router"]