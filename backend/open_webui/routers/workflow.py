import logging
import time
from typing import Dict, Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from open_webui.utils.auth import (
    get_verified_user,
    get_admin_user,
    is_interviewee_user,
    get_user_type,
)
from open_webui.models.users import User, UserModel, Users
from open_webui.models.moderation import (
    ModerationSession,
    ModerationSessions,
    ModerationSessionActivity,
)
from open_webui.models.child_profiles import ChildProfile, ChildProfiles
from open_webui.models.exit_quiz import ExitQuizResponse, ExitQuizzes
from open_webui.models.assignment_time_tracking import AssignmentSessionActivity
from open_webui.models.scenarios import ScenarioAssignments
from open_webui.models.workflow_draft import (
    WorkflowDraft,
    get_draft,
    save_draft,
    delete_draft,
)
from open_webui.internal.db import get_db

log = logging.getLogger(__name__)

router = APIRouter()


def get_current_attempt_number(user_id: str) -> int:
    """Return the current attempt number for a user.
    Uses user.current_attempt_number if set (after a reset); otherwise max across moderation, child_profile, exit_quiz.
    """
    with get_db() as db:
        user_row = db.query(User).filter(User.id == user_id).first()
        if user_row and getattr(user_row, "current_attempt_number", None) is not None:
            log.debug(
                f"Using stored current_attempt_number for user {user_id}: {user_row.current_attempt_number}"
            )
            return user_row.current_attempt_number
        max_mod = (
            db.query(func.max(ModerationSession.attempt_number))
            .filter(ModerationSession.user_id == user_id)
            .scalar()
            or 0
        )
        max_child = (
            db.query(func.max(ChildProfile.attempt_number))
            .filter(ChildProfile.user_id == user_id)
            .scalar()
            or 0
        )
        max_exit = (
            db.query(func.max(ExitQuizResponse.attempt_number))
            .filter(ExitQuizResponse.user_id == user_id)
            .scalar()
            or 0
        )
        computed = max(max_mod, max_child, max_exit, 1)  # Default to 1 if no records
        log.debug(
            f"Computed current_attempt_number for user {user_id}: {computed} (mod:{max_mod}, child:{max_child}, exit:{max_exit})"
        )
        return computed


class WorkflowStateResponse(BaseModel):
    next_route: str
    substep: str | None = None
    progress_by_section: dict


def _default_progress() -> dict:
    """Minimal progress dict when backend cannot compute full state."""
    return {
        "instructions_completed": False,
        "has_child_profile": False,
        "moderation_completed_count": 0,
        "moderation_total": 12,
        "moderation_finalized": False,
        "exit_survey_completed": False,
    }


@router.get("/workflow/state")
async def get_workflow_state(
    user: UserModel = Depends(get_verified_user),
) -> WorkflowStateResponse:
    """
    Compute current workflow state for the user to resume progress on login.
    Sections: kids/profile -> moderation-scenario -> exit-survey -> completion
    """
    try:
        with get_db() as db:
            progress = _default_progress()

            # Instructions completed
            instructions_at = getattr(user, "instructions_completed_at", None)
            progress["instructions_completed"] = instructions_at is not None

            # Child profiles
            try:
                latest_child = ChildProfiles.get_latest_child_profile_any(user.id)
                if latest_child:
                    progress["has_child_profile"] = True
            except Exception as e:
                log.warning(f"Failed to get child profiles for user {user.id}: {e}")

            # Moderation progress: count unique scenarios that have a terminal decision
            # Terminal = initial_decision in (accept_original, moderate, not_applicable)
            # OR attention check passed (is_attention_check and attention_check_passed)
            # Exclude sessions created before last workflow reset.
            # Filter sessions by latest_child so count and total refer to the same child.
            try:
                latest_child = ChildProfiles.get_latest_child_profile_any(user.id)
                child_id_for_mod = latest_child.id if latest_child else None
                sessions = ModerationSessions.get_sessions_by_user(
                    user.id, child_id=child_id_for_mod
                )
                workflow_reset_at = getattr(user, "workflow_reset_at", None)
                if workflow_reset_at:
                    sessions = [s for s in sessions if s.created_at > workflow_reset_at]
                decided = set()
                for s in sessions:
                    if s.initial_decision in (
                        "accept_original",
                        "moderate",
                        "not_applicable",
                    ):
                        decided.add(s.scenario_index)
                    elif getattr(s, "is_attention_check", False) and getattr(
                        s, "attention_check_passed", False
                    ):
                        decided.add(s.scenario_index)
                progress["moderation_completed_count"] = len(decided)

                # moderation_total: use assignment count when available, else 12
                if latest_child:
                    try:
                        current_attempt = get_current_attempt_number(user.id)
                        assignments = ScenarioAssignments.get_assignments_by_child(
                            latest_child.id,
                            attempt_number=current_attempt,
                        )
                        if assignments:
                            progress["moderation_total"] = len(assignments)
                    except Exception as ae:
                        log.debug(
                            f"Could not get assignment count for user {user.id}: {ae}"
                        )
            except Exception as e:
                log.warning(
                    f"Failed to get moderation sessions for user {user.id}: {e}"
                )

            # Check if moderation has been finalized (user clicked "Done")
            try:
                latest_child = ChildProfiles.get_latest_child_profile_any(user.id)
                if latest_child:
                    from open_webui.models.workflow_draft import get_draft

                    draft = get_draft(user.id, latest_child.id, "moderation")
                    if draft and draft.data:
                        progress["moderation_finalized"] = draft.data.get(
                            "moderation_finalized", False
                        )
            except Exception as e:
                log.debug(
                    f"Failed to check moderation finalized status for user {user.id}: {e}"
                )

            # Exit survey completion (filter by current attempt number)
            try:
                current_attempt = get_current_attempt_number(user.id)
                latest_exit = (
                    db.query(ExitQuizResponse)
                    .filter(
                        ExitQuizResponse.user_id == user.id,
                        ExitQuizResponse.attempt_number == current_attempt,
                    )
                    .order_by(ExitQuizResponse.created_at.desc())
                    .first()
                )
                progress["exit_survey_completed"] = latest_exit is not None
            except Exception as e:
                log.warning(f"Failed to get exit survey status for user {user.id}: {e}")

            # Determine user type based on STUDY_ID whitelist
            try:
                study_id = getattr(user, "study_id", None)
                user_type = get_user_type(user, study_id)
            except Exception as e:
                log.warning(
                    f"get_user_type failed for user {user.id}: {e}, defaulting to interviewee"
                )
                user_type = "interviewee"

            # Determine next route based on user type
            # Prolific users (with prolific_pid) always go to assignment-instructions, never /parent
            is_prolific = getattr(user, "prolific_pid", None) is not None
            if user_type == "parent":
                next_for_parent = (
                    "/assignment-instructions" if is_prolific else "/parent"
                )
                return WorkflowStateResponse(
                    next_route=next_for_parent,
                    substep=None,
                    progress_by_section=progress,
                )

            if user_type == "child":
                return WorkflowStateResponse(
                    next_route="/", substep=None, progress_by_section=progress
                )

            # For interviewees, follow the workflow
            # Block kids/profile until instructions completed
            if not progress["instructions_completed"]:
                return WorkflowStateResponse(
                    next_route="/assignment-instructions",
                    substep=None,
                    progress_by_section=progress,
                )
            if not progress["has_child_profile"]:
                return WorkflowStateResponse(
                    next_route="/kids/profile",
                    substep=None,
                    progress_by_section=progress,
                )

            # Only show moderation-scenario for interviewees
            if (
                user_type == "interviewee"
                and progress["moderation_completed_count"]
                < progress["moderation_total"]
            ):
                return WorkflowStateResponse(
                    next_route="/moderation-scenario",
                    substep=None,
                    progress_by_section=progress,
                )

            if not progress["exit_survey_completed"]:
                return WorkflowStateResponse(
                    next_route="/exit-survey",
                    substep=None,
                    progress_by_section=progress,
                )

            return WorkflowStateResponse(
                next_route="/completion", substep=None, progress_by_section=progress
            )

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error computing workflow state for user {user.id}: {e}")
        # Return fallback state so sidebar can display steps instead of failing silently
        progress = _default_progress()
        return WorkflowStateResponse(
            next_route="/kids/profile",
            substep=None,
            progress_by_section=progress,
        )


class InstructionsCompleteResponse(BaseModel):
    status: str
    message: str


@router.post("/workflow/instructions-complete")
async def mark_instructions_complete(
    user: UserModel = Depends(get_verified_user),
) -> InstructionsCompleteResponse:
    """Mark that the user has completed reading assignment instructions."""
    try:
        ts = int(time.time() * 1000)
        with get_db() as db:
            db.query(User).filter(User.id == user.id).update(
                {"instructions_completed_at": ts}
            )
            db.commit()
        return InstructionsCompleteResponse(
            status="success", message="Instructions marked complete"
        )
    except Exception as e:
        log.error(f"Error marking instructions complete for user {user.id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to mark instructions complete"
        )


class DraftGetResponse(BaseModel):
    data: dict | None
    updated_at: int | None


class DraftSaveRequest(BaseModel):
    child_id: str
    draft_type: str  # "exit_survey" | "moderation"
    data: dict


@router.get("/workflow/draft")
async def get_workflow_draft(
    child_id: str,
    draft_type: str,
    user: UserModel = Depends(get_verified_user),
) -> DraftGetResponse:
    """Get workflow draft (exit survey or moderation) for user+child."""
    if draft_type not in ("exit_survey", "moderation"):
        raise HTTPException(status_code=400, detail="Invalid draft_type")
    try:
        draft = get_draft(user.id, child_id, draft_type)
        if draft:
            return DraftGetResponse(data=draft.data, updated_at=draft.updated_at)
        return DraftGetResponse(data=None, updated_at=None)
    except Exception:
        log.exception("Error getting workflow draft")
        raise HTTPException(status_code=500, detail="Failed to get draft")


@router.post("/workflow/draft")
async def save_workflow_draft(
    payload: DraftSaveRequest,
    user: UserModel = Depends(get_verified_user),
) -> DraftGetResponse:
    """Save workflow draft (exit survey or moderation) for user+child."""
    if payload.draft_type not in ("exit_survey", "moderation"):
        raise HTTPException(status_code=400, detail="Invalid draft_type")
    try:
        draft = save_draft(user.id, payload.child_id, payload.draft_type, payload.data)
        return DraftGetResponse(data=draft.data, updated_at=draft.updated_at)
    except Exception:
        log.exception("Error saving workflow draft")
        raise HTTPException(status_code=500, detail="Failed to save draft")


@router.delete("/workflow/draft")
async def delete_workflow_draft(
    child_id: str,
    draft_type: str,
    user: UserModel = Depends(get_verified_user),
) -> Dict[str, Any]:
    """Delete workflow draft for user+child."""
    if draft_type not in ("exit_survey", "moderation"):
        raise HTTPException(status_code=400, detail="Invalid draft_type")
    try:
        deleted = delete_draft(user.id, child_id, draft_type)
        return {"status": "success", "deleted": deleted}
    except Exception:
        log.exception("Error deleting workflow draft")
        raise HTTPException(status_code=500, detail="Failed to delete draft")


@router.post("/workflow/reset")
async def reset_user_workflow(
    user: UserModel = Depends(get_verified_user),
) -> Dict[str, Any]:
    """
    Reset entire user workflow - clears all progress and starts fresh.
    Increments attempt_number for next moderation session.
    """
    try:
        with get_db() as db:
            # Get the current max attempt number across all tables for this user
            max_moderation_attempt = (
                db.query(func.max(ModerationSession.attempt_number))
                .filter(ModerationSession.user_id == user.id)
                .scalar()
                or 0
            )

            max_child_attempt = (
                db.query(func.max(ChildProfile.attempt_number))
                .filter(ChildProfile.user_id == user.id)
                .scalar()
                or 0
            )

            max_exit_attempt = (
                db.query(func.max(ExitQuizResponse.attempt_number))
                .filter(ExitQuizResponse.user_id == user.id)
                .scalar()
                or 0
            )

            # Calculate next attempt number
            new_attempt_number = (
                max(max_moderation_attempt, max_child_attempt, max_exit_attempt) + 1
            )

            # Child profiles persist across attempts - do NOT set is_current=False.
            # The list of children is stable; only workflow progress (moderation, exit survey) resets.

            # Note: Exit quiz and scenario assignments use attempt_number for filtering,
            # so no need to mark old records - they're automatically excluded by attempt_number filter

            # Record workflow reset timestamp so moderation_completed_count excludes pre-reset sessions
            reset_ts = int(time.time() * 1000)
            # Clear instructions_completed_at and persist next attempt number so new sessions use it
            db.query(User).filter(User.id == user.id).update(
                {
                    "workflow_reset_at": reset_ts,
                    "instructions_completed_at": None,
                    "current_attempt_number": new_attempt_number,
                }
            )

            # Clear workflow drafts (exit survey, moderation) for this user
            db.query(WorkflowDraft).filter(WorkflowDraft.user_id == user.id).delete()

            # Note: scenario_assignments now use attempt_number, so old assignments
            # are automatically excluded when fetching by current attempt_number

            db.commit()

            # Verify the update worked
            updated_user = db.query(User).filter(User.id == user.id).first()
            stored_attempt = (
                getattr(updated_user, "current_attempt_number", None)
                if updated_user
                else None
            )

            log.info(
                f"Reset workflow for user {user.id}, new attempt number: {new_attempt_number}, "
                f"stored in DB: {stored_attempt}"
            )

            return {
                "status": "success",
                "new_attempt": new_attempt_number,
                "message": "Workflow reset successfully",
            }

    except Exception as e:
        log.error(f"Error resetting workflow for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset workflow")


@router.get("/workflow/current-attempt")
async def get_current_attempt(
    user: UserModel = Depends(get_verified_user),
) -> Dict[str, Any]:
    """
    Get the current attempt number for the user across all workflow tables.
    """
    try:
        current_attempt = get_current_attempt_number(user.id)
        with get_db() as db:
            max_moderation_attempt = (
                db.query(func.max(ModerationSession.attempt_number))
                .filter(ModerationSession.user_id == user.id)
                .scalar()
                or 0
            )
            max_child_attempt = (
                db.query(func.max(ChildProfile.attempt_number))
                .filter(ChildProfile.user_id == user.id)
                .scalar()
                or 0
            )
            max_exit_attempt = (
                db.query(func.max(ExitQuizResponse.attempt_number))
                .filter(ExitQuizResponse.user_id == user.id)
                .scalar()
                or 0
            )
            return {
                "current_attempt": current_attempt,
                "moderation_attempt": max_moderation_attempt,
                "child_attempt": max_child_attempt,
                "exit_attempt": max_exit_attempt,
            }
    except Exception as e:
        log.error(f"Error getting current attempt for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current attempt")


@router.get("/workflow/session-info")
async def get_session_info(
    user: UserModel = Depends(get_verified_user),
) -> Dict[str, Any]:
    """
    Get current session information for a user.
    """
    try:
        return {
            "prolific_pid": user.prolific_pid,
            "study_id": user.study_id,
            "current_session_id": user.current_session_id,
            "session_number": user.session_number,
            "is_prolific_user": user.prolific_pid is not None,
        }

    except Exception as e:
        log.error(f"Error getting session info for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session info")


@router.post("/workflow/reset-moderation")
async def reset_moderation_workflow(
    user: UserModel = Depends(get_verified_user),
) -> Dict[str, Any]:
    """
    Reset only moderation workflow - increments attempt_number for moderation sessions only.
    Does NOT reset child profiles or exit quiz responses.
    """
    try:
        with get_db() as db:
            # Get the current max attempt number from moderation sessions only
            max_moderation_attempt = (
                db.query(func.max(ModerationSession.attempt_number))
                .filter(ModerationSession.user_id == user.id)
                .scalar()
                or 0
            )

            # Calculate next attempt number
            new_attempt_number = max_moderation_attempt + 1

            # Get list of completed scenario indices before marking as not current
            completed_scenario_indices = (
                ModerationSessions.get_completed_scenario_indices(user.id)
            )

            # Mark all existing moderation sessions as not current
            db.query(ModerationSession).filter(
                ModerationSession.user_id == user.id
            ).update({"is_final_version": False})

            db.commit()

            log.info(
                f"Reset moderation workflow for user {user.id}, new attempt number: {new_attempt_number}"
            )

            return {
                "status": "success",
                "new_attempt": new_attempt_number,
                "completed_scenario_indices": completed_scenario_indices,
                "message": "Moderation workflow reset successfully",
            }

    except Exception as e:
        log.error(f"Error resetting moderation workflow for user {user.id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to reset moderation workflow"
        )


@router.get("/workflow/completed-scenarios")
async def get_completed_scenarios(
    user: UserModel = Depends(get_verified_user),
) -> Dict[str, Any]:
    """
    Get all scenario indices that user has completed across all attempts.
    """
    try:
        completed_scenario_indices = ModerationSessions.get_completed_scenario_indices(
            user.id
        )

        return {
            "completed_scenario_indices": completed_scenario_indices,
            "count": len(completed_scenario_indices),
        }

    except Exception as e:
        log.error(f"Error getting completed scenarios for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get completed scenarios")


@router.get("/workflow/study-status")
async def get_study_status(
    user: UserModel = Depends(get_verified_user),
) -> Dict[str, Any]:
    """
    Get study completion status and whether user can retake quiz.
    Uses calendar date comparison (not 24-hour duration) to check if it's a new day.
    """
    try:
        with get_db() as db:
            # Get the latest exit quiz response for this user (current attempt)
            current_attempt = get_current_attempt_number(user.id)
            latest_exit_quiz = (
                db.query(ExitQuizResponse)
                .filter(
                    ExitQuizResponse.user_id == user.id,
                    ExitQuizResponse.attempt_number == current_attempt,
                )
                .order_by(ExitQuizResponse.created_at.desc())
                .first()
            )

            if not latest_exit_quiz:
                return {
                    "completed_at": None,
                    "completion_date": None,
                    "can_retake": False,
                    "current_attempt": 1,
                    "message": "No completion found",
                }

            # Convert timestamp to date
            completion_timestamp = latest_exit_quiz.created_at
            completion_date = datetime.fromtimestamp(
                completion_timestamp / 1000, tz=timezone.utc
            ).date()
            current_date = datetime.now(timezone.utc).date()

            # Check if it's a new calendar day
            can_retake = completion_date != current_date

            # Get current moderation attempt number
            max_moderation_attempt = (
                db.query(func.max(ModerationSession.attempt_number))
                .filter(ModerationSession.user_id == user.id)
                .scalar()
                or 0
            )

            return {
                "completed_at": completion_timestamp,
                "completion_date": completion_date.isoformat(),
                "can_retake": can_retake,
                "current_attempt": max_moderation_attempt + 1,
                "message": "Study status retrieved successfully",
            }

    except Exception as e:
        log.error(f"Error getting study status for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get study status")


@router.get("/workflow/admin/user-submissions/{user_id}")
async def get_user_submissions(
    user_id: str, user: UserModel = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Admin endpoint to get all quiz submission data for a specific user.
    Returns child profiles, moderation sessions (all versions), exit quiz responses, and session activity totals.
    """
    try:
        # Get user info
        target_user = Users.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get all data for the user
        child_profiles = ChildProfiles.get_child_profiles_by_user(user_id)
        moderation_sessions = ModerationSessions.get_sessions_by_user(user_id)
        exit_quiz_responses = ExitQuizzes.get_responses_by_user(user_id)

        # Aggregate session activity totals per (user, child, session)
        session_activity_totals = {}
        with get_db() as db:
            # Group by user_id, child_id, session_number and sum the deltas
            results = (
                db.query(
                    ModerationSessionActivity.user_id,
                    ModerationSessionActivity.child_id,
                    ModerationSessionActivity.session_number,
                    func.sum(ModerationSessionActivity.active_ms_delta).label(
                        "total_active_ms"
                    ),
                )
                .filter(ModerationSessionActivity.user_id == user_id)
                .group_by(
                    ModerationSessionActivity.user_id,
                    ModerationSessionActivity.child_id,
                    ModerationSessionActivity.session_number,
                )
                .all()
            )
            for row in results:
                key = f"{row.user_id}::{row.child_id}::{row.session_number}"
                session_activity_totals[key] = int(row.total_active_ms or 0)

        # Aggregate assignment time totals per (user, session)
        assignment_time_totals = {}
        with get_db() as db:
            # Group by user_id, session_number and sum the deltas
            results = (
                db.query(
                    AssignmentSessionActivity.user_id,
                    AssignmentSessionActivity.session_number,
                    func.sum(AssignmentSessionActivity.active_ms_delta).label(
                        "total_active_ms"
                    ),
                )
                .filter(AssignmentSessionActivity.user_id == user_id)
                .group_by(
                    AssignmentSessionActivity.user_id,
                    AssignmentSessionActivity.session_number,
                )
                .all()
            )
            for row in results:
                key = f"{row.user_id}::{row.session_number}"
                assignment_time_totals[key] = int(row.total_active_ms or 0)

        return {
            "user_info": {
                "id": target_user.id,
                "name": target_user.name,
                "email": target_user.email,
            },
            "child_profiles": [profile.model_dump() for profile in child_profiles],
            "moderation_sessions": [
                session.model_dump() for session in moderation_sessions
            ],
            "exit_quiz_responses": [
                response.model_dump() for response in exit_quiz_responses
            ],
            "session_activity_totals": session_activity_totals,
            "assignment_time_totals": assignment_time_totals,
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting user submissions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user submissions")


class FinalizeModerationForm(BaseModel):
    child_id: str | None = None
    session_number: int | None = None


@router.post("/workflow/moderation/finalize")
async def finalize_moderation(
    form: FinalizeModerationForm, user: UserModel = Depends(get_verified_user)
) -> Dict[str, Any]:
    """
    Mark the last-chosen (latest) submission per scenario as final for the current user.
    Optional filters: child_id, session_number.
    Groups by (child_id, scenario_index, attempt_number[, session_number]) and sets the latest created row final.
    """
    try:
        updated = 0
        with get_db() as db:
            query = db.query(ModerationSession).filter(
                ModerationSession.user_id == user.id
            )
            if form.child_id:
                query = query.filter(ModerationSession.child_id == form.child_id)
            # Only filter by session_number if column exists and form provides it
            if form.session_number is not None:
                try:
                    query = query.filter(
                        ModerationSession.session_number == form.session_number
                    )
                except Exception:
                    # Older schemas may not have session_number; ignore filter
                    pass

            rows: list[ModerationSession] = query.all()

            # Group rows by scenario identity
            from collections import defaultdict

            groups = defaultdict(list)

            for r in rows:
                try:
                    sn = getattr(r, "session_number", None)
                except Exception:
                    sn = None
                key = (
                    r.child_id,
                    r.scenario_index,
                    r.attempt_number,
                    sn if form.session_number is not None else None,
                )
                groups[key].append(r)

            for key, items in groups.items():
                # Pick the latest by created_at
                items.sort(key=lambda x: x.created_at or 0, reverse=True)
                winner = items[0]
                # Clear all finals in the group
                for r in items:
                    if r.is_final_version:
                        r.is_final_version = False
                # Mark winner as final
                if not winner.is_final_version:
                    winner.is_final_version = True
                    updated += 1

            db.commit()

        return {"updated": updated}
    except Exception as e:
        log.error(f"Error finalizing moderation for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to finalize moderation")
