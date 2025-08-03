"""
Webhook Router - HTTP endpoints for webhook processing
Handles OpenRouter webhooks and manual synchronization
"""

import logging
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
from open_webui.utils.auth import get_admin_user
from ..models.requests import UsageWebhookPayload, UsageSyncRequest, ManualUsageRequest
from ..models.responses import WebhookResponse, SyncResponse
from ..services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

webhook_router = APIRouter()
webhook_service = WebhookService()


@webhook_router.post("/webhook/openrouter-usage", response_model=WebhookResponse)
async def openrouter_usage_webhook(
    payload: UsageWebhookPayload,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for OpenRouter usage notifications
    Note: OpenRouter doesn't have native webhooks, but this endpoint
    can receive usage data from other integrations
    """
    try:
        # Process webhook in background to avoid blocking
        async def process_in_background():
            try:
                await webhook_service.process_webhook(payload)
            except Exception as e:
                logger.error(f"Background webhook processing failed: {e}", exc_info=True)
        
        background_tasks.add_task(process_in_background)
        
        return WebhookResponse(status="success", message="Usage recorded")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhook_router.post("/sync/openrouter-usage", response_model=SyncResponse)
async def sync_openrouter_usage(
    request: UsageSyncRequest,
    user=Depends(get_admin_user)
):
    """
    DEPRECATED: OpenRouter bulk sync endpoint
    
    This endpoint has been disabled because the OpenRouter API does not provide
    a bulk generations endpoint (/api/v1/generations). Previous attempts to use
    this functionality resulted in 404 errors.
    
    Real-time usage tracking via webhooks is the primary method for collecting usage data.
    This endpoint is maintained for backward compatibility but will return a deprecation message.
    """
    try:
        result = await webhook_service.sync_openrouter_usage(request)
        return SyncResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhook_router.post("/usage/manual-record")
async def manual_record_usage(
    request: ManualUsageRequest,
    user=Depends(get_admin_user)
):
    """Manually record usage (for testing or corrections)"""
    try:
        result = await webhook_service.manual_record_usage(
            request.model, request.tokens, request.cost
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhook_router.get("/webhook/status")
async def get_webhook_service_status(user=Depends(get_admin_user)):
    """
    Get the status of webhook service and its storage backends
    Shows InfluxDB integration status and dual-write mode configuration
    """
    try:
        status = await webhook_service.get_service_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))