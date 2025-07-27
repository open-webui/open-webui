"""
Webhook Router - HTTP endpoints for webhook processing
Handles OpenRouter webhooks and manual synchronization
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
from open_webui.utils.auth import get_admin_user
from ..models.requests import UsageWebhookPayload, UsageSyncRequest, ManualUsageRequest
from ..models.responses import WebhookResponse, SyncResponse
from ..services.webhook_service import WebhookService

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
                print(f"Background webhook processing failed: {e}")
        
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
    Manually sync usage data from OpenRouter API
    This is the primary method since OpenRouter doesn't have webhooks
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
        result = webhook_service.manual_record_usage(
            request.model, request.tokens, request.cost
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))