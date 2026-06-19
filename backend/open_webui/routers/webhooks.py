from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.models.webhook_logs import WebhookDeliveryLogModel, WebhookDeliveryLogs
from open_webui.utils.auth import get_admin_user
from open_webui.utils.webhook import post_webhook

router = APIRouter()

@router.get('/logs', response_model=list[WebhookDeliveryLogModel])
async def get_webhook_logs(skip: int = 0, limit: int = 50, user=Depends(get_admin_user)):
    """Fetch recent webhook delivery logs."""
    logs = await WebhookDeliveryLogs.get_logs(skip=skip, limit=limit)
    return logs

@router.post('/logs/{log_id}/retry', response_model=bool)
async def retry_webhook_delivery(log_id: str, user=Depends(get_admin_user)):
    """Manually force trigger a retry for a specific webhook log entry."""
    log_entry = await WebhookDeliveryLogs.get_log_by_id(log_id)
    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Webhook log entry not found'
        )
    
    # We create a new log entry via post_webhook
    # But wait, post_webhook will create a NEW log entry.
    # To keep it simple, we just call post_webhook with the original payload,
    # which will generate a new log entry and attempt delivery.
    success = await post_webhook(
        name="Manual Retry",
        url=log_entry.url,
        message=log_entry.payload.get('summary') or log_entry.payload.get('text') or log_entry.payload.get('content') or '',
        event_data=log_entry.payload
    )
    return success
