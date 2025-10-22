import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.models.moderation import (
    ModerationSessions,
    ModerationSessionForm,
    ModerationSessionModel,
)

log = logging.getLogger(__name__)

router = APIRouter()


class ModerationSessionPayload(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    child_id: str
    scenario_index: int
    attempt_number: int
    version_number: int
    scenario_prompt: str
    original_response: str
    initial_decision: Optional[str] = None
    strategies: Optional[List[str]] = None
    custom_instructions: Optional[List[str]] = None
    highlighted_texts: Optional[List[str]] = None
    refactored_response: Optional[str] = None
    is_final_version: Optional[bool] = False
    session_metadata: Optional[dict] = None


@router.post("/moderation/sessions", response_model=ModerationSessionModel)
async def create_or_update_session(
    form_data: ModerationSessionPayload,
    user: UserModel = Depends(get_verified_user),
):
    """Create or update a moderation session version row"""
    try:
        if user.id != form_data.user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        form = ModerationSessionForm(
            session_id=form_data.session_id,
            user_id=form_data.user_id,
            child_id=form_data.child_id,
            scenario_index=form_data.scenario_index,
            attempt_number=form_data.attempt_number,
            version_number=form_data.version_number,
            scenario_prompt=form_data.scenario_prompt,
            original_response=form_data.original_response,
            initial_decision=form_data.initial_decision,
            strategies=form_data.strategies,
            custom_instructions=form_data.custom_instructions,
            highlighted_texts=form_data.highlighted_texts,
            refactored_response=form_data.refactored_response,
            is_final_version=form_data.is_final_version,
            session_metadata=form_data.session_metadata,
        )
        
        result = ModerationSessions.upsert(form)
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error upserting moderation session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/moderation/sessions", response_model=List[ModerationSessionModel])
async def list_sessions(
    child_id: Optional[str] = None,
    user: UserModel = Depends(get_verified_user),
):
    """List moderation sessions for the current user"""
    try:
        sessions = ModerationSessions.get_sessions_by_user(user.id, child_id=child_id)
        return sessions
    except Exception as e:
        log.error(f"Error listing moderation sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/moderation/sessions/{session_id}", response_model=ModerationSessionModel)
async def get_session(
    session_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """Get a specific moderation session"""
    try:
        session = ModerationSessions.get_session_by_id(session_id, user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Moderation session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching moderation session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/moderation/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """Delete a moderation session"""
    try:
        success = ModerationSessions.delete_session(session_id, user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Moderation session not found")
        return {"message": "Moderation session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting moderation session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")