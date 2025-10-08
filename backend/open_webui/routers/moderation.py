import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

from open_webui.utils.auth import get_verified_user
from open_webui.utils.moderation import multi_moderations_openai, generate_second_pass_prompt

log = logging.getLogger(__name__)

router = APIRouter()


class ModerationRequest(BaseModel):
    moderation_types: List[str]  # Standard moderation type names
    child_prompt: Optional[str] = "Who is Trump? Is he a good guy?"  # Default example prompt
    model: Optional[str] = "gpt-4o-mini"
    max_chars: Optional[int] = 600
    custom_instructions: List[str] = []  # Optional custom instruction texts
    original_response: Optional[str] = None  # For refactoring mode
    highlighted_texts: List[str] = []  # Phrases parent flagged


class FollowUpPromptRequest(BaseModel):
    initial_prompt: str
    initial_response: str
    model: Optional[str] = "gpt-4o-mini"


@router.post("/apply")
async def apply_moderation(
    request: Request,
    form_data: ModerationRequest,
    user=Depends(get_verified_user)
):
    """
    Apply multiple moderation strategies to either:
    1. Generate a response (original_response=None)
    2. Refactor an existing response (original_response provided)
    
    Based on notebook (3) iterative moderation design. Allows parents to select one or more
    moderation strategies that will be combined into a single refactored response.
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
        
        # Call the moderation utility function with new parameters
        result = await multi_moderations_openai(
            child_prompt=form_data.child_prompt,
            moderation_types=form_data.moderation_types,
            original_response=form_data.original_response,
            highlighted_texts=form_data.highlighted_texts,
            api_key=api_key,
            model=form_data.model,
            max_chars=form_data.max_chars,
            custom_instructions=form_data.custom_instructions,
        )
        
        mode = "refactoring" if form_data.original_response else "generation"
        strategies_info = ', '.join(form_data.moderation_types)
        if form_data.custom_instructions:
            strategies_info += f" + {len(form_data.custom_instructions)} custom"
        log.info(f"Moderation applied ({mode} mode): {strategies_info} for user {user.id}")
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Error applying moderation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to apply moderation: {str(e)}")


@router.post("/generate-followup")
async def generate_followup(
    request: Request,
    form_data: FollowUpPromptRequest,
    user=Depends(get_verified_user)
):
    """
    Generate a realistic follow-up question a child might ask based on
    their initial prompt and the refactored response they received.
    
    Based on notebook (3) function 2.
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
        
        # Generate follow-up prompt
        followup = await generate_second_pass_prompt(
            initial_prompt=form_data.initial_prompt,
            initial_response=form_data.initial_response,
            api_key=api_key,
            model=form_data.model,
        )
        
        log.info(f"Follow-up prompt generated for user {user.id}")
        
        return {"child_followup_prompt": followup}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Error generating follow-up: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-up: {str(e)}")


