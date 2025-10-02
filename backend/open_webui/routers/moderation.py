import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

from open_webui.utils.auth import get_verified_user
from open_webui.utils.moderation import multi_moderations_openai

log = logging.getLogger(__name__)

router = APIRouter()


class ModerationRequest(BaseModel):
    moderation_types: List[str]  # Standard moderation type names
    child_prompt: Optional[str] = "Who is Trump? Is he a good guy?"  # Default example prompt
    model: Optional[str] = "gpt-4o-mini"
    max_chars: Optional[int] = 600
    custom_instructions: List[str] = []  # Optional custom instruction texts


@router.post("/apply")
async def apply_moderation(
    request: Request,
    form_data: ModerationRequest,
    user=Depends(get_verified_user)
):
    """
    Apply multiple moderation strategies at once to a child's prompt and return the refactored response.
    
    Based on Viki's updated multi-moderation logic. Allows parents to select one or more
    moderation strategies that will be combined into a single refactored response.
    
    This endpoint demonstrates the connection between frontend moderation buttons
    and the backend moderation logic.
    """
    try:
        # Get OpenAI API key from app state
        api_key = None
        if hasattr(request.app.state.config, 'OPENAI_API_KEYS'):
            keys = request.app.state.config.OPENAI_API_KEYS
            if isinstance(keys, list) and len(keys) > 0:
                api_key = keys[0]  # Use the first API key
        
        if not api_key:
            raise HTTPException(
                status_code=500, 
                detail="OpenAI API key not configured. Please configure it in Admin Settings > Connections."
            )
        
        # Call the moderation utility function with multiple moderation types
        result = await multi_moderations_openai(
            child_prompt=form_data.child_prompt,
            moderation_types=form_data.moderation_types,
            api_key=api_key,
            model=form_data.model,
            max_chars=form_data.max_chars,
            custom_instructions=form_data.custom_instructions,
        )
        
        strategies_info = ', '.join(form_data.moderation_types)
        if form_data.custom_instructions:
            strategies_info += f" + {len(form_data.custom_instructions)} custom"
        log.info(f"Moderation applied: {strategies_info} for user {user.id}")
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Error applying moderation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to apply moderation: {str(e)}")


