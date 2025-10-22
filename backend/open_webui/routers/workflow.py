import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.models.moderation import ModerationSession
from open_webui.models.child_profiles import ChildProfile
from open_webui.models.exit_quiz import ExitQuizResponse
from open_webui.internal.db import get_db

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/workflow/reset")
async def reset_user_workflow(user: UserModel = Depends(get_verified_user)) -> Dict[str, Any]:
    """
    Reset entire user workflow - clears all progress and starts fresh.
    Increments attempt_number for next moderation session.
    """
    try:
        with get_db() as db:
            # Get the current max attempt number across all tables for this user
            max_moderation_attempt = db.query(func.max(ModerationSession.attempt_number)).filter(
                ModerationSession.user_id == user.id
            ).scalar() or 0
            
            max_child_attempt = db.query(func.max(ChildProfile.attempt_number)).filter(
                ChildProfile.user_id == user.id
            ).scalar() or 0
            
            max_exit_attempt = db.query(func.max(ExitQuizResponse.attempt_number)).filter(
                ExitQuizResponse.user_id == user.id
            ).scalar() or 0
            
            # Calculate next attempt number
            new_attempt_number = max(max_moderation_attempt, max_child_attempt, max_exit_attempt) + 1
            
            # Mark all existing records as not current
            # Mark all child profiles for this user as not current (regardless of current flag)
            db.query(ChildProfile).filter(
                ChildProfile.user_id == user.id
            ).update({"is_current": False})
            
            # Mark all exit quiz responses for this user as not current
            db.query(ExitQuizResponse).filter(
                ExitQuizResponse.user_id == user.id
            ).update({"is_current": False})
            
            db.commit()
            
            log.info(f"Reset workflow for user {user.id}, new attempt number: {new_attempt_number}")
            
            return {
                "status": "success", 
                "new_attempt": new_attempt_number,
                "message": "Workflow reset successfully"
            }
            
    except Exception as e:
        log.error(f"Error resetting workflow for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset workflow")


@router.get("/workflow/current-attempt")
async def get_current_attempt(user: UserModel = Depends(get_verified_user)) -> Dict[str, Any]:
    """
    Get the current attempt number for the user across all workflow tables.
    """
    try:
        with get_db() as db:
            # Get the current max attempt number across all tables for this user
            max_moderation_attempt = db.query(func.max(ModerationSession.attempt_number)).filter(
                ModerationSession.user_id == user.id
            ).scalar() or 0
            
            max_child_attempt = db.query(func.max(ChildProfile.attempt_number)).filter(
                ChildProfile.user_id == user.id
            ).scalar() or 0
            
            max_exit_attempt = db.query(func.max(ExitQuizResponse.attempt_number)).filter(
                ExitQuizResponse.user_id == user.id
            ).scalar() or 0
            
            current_attempt = max(max_moderation_attempt, max_child_attempt, max_exit_attempt)
            
            return {
                "current_attempt": current_attempt,
                "moderation_attempt": max_moderation_attempt,
                "child_attempt": max_child_attempt,
                "exit_attempt": max_exit_attempt
            }
            
    except Exception as e:
        log.error(f"Error getting current attempt for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current attempt")
