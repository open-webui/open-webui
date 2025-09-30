import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from open_webui.utils.auth import get_verified_user
from open_webui.utils.moderation import apply_moderation_and_update

log = logging.getLogger(__name__)

router = APIRouter()


class ModerationRequest(BaseModel):
    moderation_type: str
    child_prompt: Optional[str] = "How can I open a door without a key?"  # Default example prompt
    model: Optional[str] = "gpt-4o-mini"
    max_chars: Optional[int] = 600


@router.post("/apply")
async def apply_moderation(
    request: Request,
    form_data: ModerationRequest,
    user=Depends(get_verified_user)
):
    """
    Apply a moderation strategy to a child's prompt and return the refactored response.
    
    This endpoint demonstrates the connection between frontend moderation buttons
    and the backend moderation logic.
    """
    try:
        # Call the moderation utility function
        result = await apply_moderation_and_update(
            child_prompt=form_data.child_prompt,
            moderation_type=form_data.moderation_type,
            model=form_data.model,
            max_chars=form_data.max_chars,
        )
        
        log.info(f"Moderation applied: {form_data.moderation_type} for user {user.id}")
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Error applying moderation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to apply moderation: {str(e)}")

