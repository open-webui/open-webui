from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel, Field
import logging
from typing import Dict, Any, Optional

# Configure logging
log = logging.getLogger(__name__)
# You might want to set a specific log level, e.g., logging.INFO
# logging.basicConfig(level=logging.INFO)


# Placeholder for your Lago integration logic
# Example:
# from backend.open_webui.moneta.utils import lago_client
# async def update_lago_customer(user_data: dict):
#     try:
#         # Replace with your actual Lago API call
#         log.info(f"Updating Lago for user {user_data.get('email')}")
#         # lago_client.create_or_update_customer(...)
#         await asyncio.sleep(0.1) # Simulate async operation
#         log.info(f"Successfully updated Lago for user {user_data.get('email')}")
#     except Exception as e:
#         log.error(f"Lago update failed for user {user_data.get('email')}: {e}")
#         # Depending on requirements, you might want to raise an exception here
#         # or implement retry logic


# Define the structure of the user data within the webhook payload
# Based on inspection of Auths.insert_new_auth and UserModel
class WebhookUserPayload(BaseModel):
    id: str
    name: str
    email: str
    role: str
    profile_image_url: str
    last_active_at: Optional[int] = None
    updated_at: Optional[int] = None
    created_at: Optional[int] = None
    api_key: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    info: Optional[Dict[str, Any]] = None
    oauth_sub: Optional[str] = None


# Define the overall webhook payload structure
class WebhookPayload(BaseModel):
    action: str
    message: str
    user: WebhookUserPayload


# Create the FastAPI router
router = APIRouter()

# POST /moneta/webhook
@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def moneta_webhook(payload: WebhookPayload, request: Request):
    """
    Receives webhook events from OpenWebUI.
    Currently processes 'signup' events for Lago integration.
    """
    log.info(f"Received webhook event. Action: {payload.action}, User Email: {payload.user.email}")

    if payload.action == "signup":
        log.info(f"Processing 'signup' event for user: {payload.user.email}")

        try:
            # Placeholder for calling your Lago integration logic
            # await update_lago_customer(payload.user.model_dump())
            log.info(f"Placeholder: Lago processing for {payload.user.email} would execute here.")
            # Simulate some async work if needed
            # await asyncio.sleep(0.1)

            return {"status": "accepted", "action": payload.action, "user_email": payload.user.email}

        except Exception as e:
            log.error(f"Error processing signup webhook for user {payload.user.email}: {e}", exc_info=True)
            # Return an error status to the webhook sender if processing fails critically
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process signup event for Lago: {e}"
            )
    else:
        # Handle other potential future actions if needed, or just acknowledge them
        log.warning(f"Received unhandled webhook action: {payload.action}. Ignoring.")
        return {"status": "ignored", "action": payload.action}

# Example of how you might add other hook-related endpoints or utilities
# GET /moneta/webhook/status
@router.get("/webhook/status")
async def get_hooks_status():
    return {"status": "running"}
