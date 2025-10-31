import logging
import random
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.models.moderation import (
    ModerationSessions,
    ModerationSessionForm,
    ModerationSessionModel,
    ModerationSessionActivities,
    ModerationSessionActivityForm,
    ModerationSessionActivityModel,
)
from open_webui.models.child_profiles import ChildProfiles

log = logging.getLogger(__name__)

router = APIRouter()


class ModerationSessionPayload(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    child_id: str
    scenario_index: int
    attempt_number: int
    version_number: int
    session_number: int = 1
    scenario_prompt: str
    original_response: str
    initial_decision: Optional[str] = None
    strategies: Optional[List[str]] = None
    custom_instructions: Optional[List[str]] = None
    highlighted_texts: Optional[List[str]] = None
    refactored_response: Optional[str] = None
    is_final_version: Optional[bool] = False
    session_metadata: Optional[dict] = None
    # Attention check tracking
    is_attention_check: Optional[bool] = False
    attention_check_selected: Optional[bool] = False
    attention_check_passed: Optional[bool] = False


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
            session_number=form_data.session_number,
            scenario_prompt=form_data.scenario_prompt,
            original_response=form_data.original_response,
            initial_decision=form_data.initial_decision,
            strategies=form_data.strategies,
            custom_instructions=form_data.custom_instructions,
            highlighted_texts=form_data.highlighted_texts,
            refactored_response=form_data.refactored_response,
            is_final_version=form_data.is_final_version,
            session_metadata=form_data.session_metadata,
            is_attention_check=form_data.is_attention_check,
            attention_check_selected=form_data.attention_check_selected,
            attention_check_passed=form_data.attention_check_passed,
        )
        
        result = ModerationSessions.upsert(form)
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error upserting moderation session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class SessionActivityPayload(BaseModel):
    user_id: str
    child_id: str
    session_number: int
    active_ms_cumulative: int


@router.post("/moderation/session-activity", response_model=ModerationSessionActivityModel)
async def post_session_activity(
    payload: SessionActivityPayload,
    user: UserModel = Depends(get_verified_user),
):
    try:
        if user.id != payload.user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        form = ModerationSessionActivityForm(
            user_id=payload.user_id,
            child_id=payload.child_id,
            session_number=payload.session_number,
            active_ms_cumulative=max(0, int(payload.active_ms_cumulative)),
        )
        return ModerationSessionActivities.add_activity(form)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error posting session activity: {e}")
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


@router.get("/moderation/scenarios/available")
async def get_available_scenarios(
    child_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """
    Get available scenarios for the current session that the user hasn't seen yet.
    Prioritizes scenarios matching the child's personality characteristics.
    """
    try:
        # Get all sessions for this user to find seen scenarios
        all_sessions = ModerationSessions.get_sessions_by_user(user.id, child_id)
        seen_scenario_indices = set()
        
        for session in all_sessions:
            seen_scenario_indices.add(session.scenario_index)
        
        # Get child profile to understand personality characteristics
        child_profiles = ChildProfiles.get_child_profiles_by_user(user.id)
        child_profile = None
        for profile in child_profiles:
            if profile.id == child_id:
                child_profile = profile
                break
        
        if not child_profile:
            raise HTTPException(status_code=404, detail="Child profile not found")
        
        # Define all available scenarios (0-11 based on the frontend)
        all_scenarios = list(range(12))  # 0-11 inclusive
        
        # Filter out seen scenarios
        unseen_scenarios = [idx for idx in all_scenarios if idx not in seen_scenario_indices]
        
        if not unseen_scenarios:
            # All scenarios have been seen, return empty list
            return {"available_scenarios": []}
        
        # For now, return all unseen scenarios in random order
        # TODO: Implement personality-based prioritization when personality data is available
        random.shuffle(unseen_scenarios)
        
        return {
            "available_scenarios": unseen_scenarios,
            "total_seen": len(seen_scenario_indices),
            "total_available": len(unseen_scenarios),
            "session_number": user.session_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting available scenarios: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")