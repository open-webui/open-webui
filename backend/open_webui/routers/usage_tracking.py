"""
Usage Tracking Router for mAI - Clean API Architecture
Refactored from 866-line monolithic file to clean layered architecture

This file now serves as a thin import layer that delegates to the new
Clean API Architecture in the usage_tracking package.
"""

from fastapi import APIRouter
from open_webui.usage_tracking.main import usage_tracking_router

# Create the main router that maintains 100% API compatibility
router = APIRouter()

# Include the new clean architecture router
router.include_router(usage_tracking_router)

# This preserves all existing endpoints:
# POST /webhook/openrouter-usage
# POST /sync/openrouter-usage  
# GET /usage/real-time/{client_org_id}
# POST /usage/manual-record
# GET /my-organization/usage-summary
# GET /my-organization/usage-by-user
# GET /my-organization/usage-by-model
# GET /my-organization/subscription-billing
# GET /model-pricing