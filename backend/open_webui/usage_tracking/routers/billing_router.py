"""
Billing Router - HTTP endpoints for billing and pricing
Handles subscription billing and model pricing information
"""

from fastapi import APIRouter, Depends
from open_webui.utils.auth import get_current_user
from ..models.responses import BillingResponse, ModelPricingResponse
from ..services.billing_service import BillingService
from ..services.pricing_service import PricingService

billing_router = APIRouter()
billing_service = BillingService()
pricing_service = PricingService()


@billing_router.get("/my-organization/subscription-billing", response_model=BillingResponse)
async def get_my_organization_subscription_billing(user=Depends(get_current_user)):
    """Get subscription billing data for the current organization (environment-based)"""
    try:
        result = billing_service.get_subscription_billing()
        return BillingResponse(**result)
        
    except Exception as e:
        import traceback
        print(f"Error in subscription billing: {e}")
        print(traceback.format_exc())
        return BillingResponse(
            success=False,
            error=str(e),
            subscription_data=None
        )


@billing_router.get("/model-pricing", response_model=ModelPricingResponse)
async def get_mai_model_pricing():
    """
    Get mAI model pricing information - dynamically fetched from OpenRouter API
    Prices are cached for 24 hours and refreshed daily at 13:00 CET
    """
    try:
        result = await pricing_service.get_model_pricing()
        return ModelPricingResponse(**result)
        
    except Exception as e:
        return ModelPricingResponse(
            success=False,
            error=str(e),
            models=[],
            source="error"
        )