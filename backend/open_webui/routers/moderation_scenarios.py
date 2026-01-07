import logging
import random
import time
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
from open_webui.models.scenarios import (
    Scenarios,
    ScenarioAssignments,
    ScenarioAssignmentForm,
    ScenarioAssignmentModel,
    AssignmentStatus,
)
from open_webui.internal.db import get_db

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
    concern_level: Optional[int] = None
    concern_reason: Optional[str] = None
    satisfaction_level: Optional[int] = None
    satisfaction_reason: Optional[str] = None
    next_action: Optional[str] = None
    decided_at: Optional[int] = None
    highlights_saved_at: Optional[int] = None
    saved_at: Optional[int] = None
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
            concern_level=form_data.concern_level,
            concern_reason=form_data.concern_reason,
            satisfaction_level=form_data.satisfaction_level,
            satisfaction_reason=form_data.satisfaction_reason,
            next_action=form_data.next_action,
            decided_at=form_data.decided_at,
            highlights_saved_at=form_data.highlights_saved_at,
            saved_at=form_data.saved_at,
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


# New scenario assignment endpoints

class ScenarioAssignRequest(BaseModel):
    participant_id: str
    child_profile_id: Optional[str] = None
    assignment_position: Optional[int] = None
    alpha: Optional[float] = 1.0  # Weighted sampling alpha parameter


class ScenarioAssignResponse(BaseModel):
    assignment_id: str
    scenario_id: str
    prompt_text: str
    response_text: str
    assignment_position: Optional[int] = None
    sampling_audit: Optional[dict] = None


@router.post("/moderation/scenarios/assign", response_model=ScenarioAssignResponse)
async def assign_scenario(
    request: ScenarioAssignRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    Assign a scenario to a participant using weighted sampling.
    Atomically creates assignment and increments n_assigned counter.
    """
    try:
        if user.id != request.participant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Perform weighted sampling
        result = Scenarios.weighted_sample(
            participant_id=request.participant_id,
            alpha=request.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No eligible scenarios available")
        
        selected_scenario, sampling_audit = result
        
        # Create assignment atomically (in a transaction)
        with get_db() as db:
            # Create assignment
            form = ScenarioAssignmentForm(
                participant_id=request.participant_id,
                child_profile_id=request.child_profile_id,
                assignment_position=request.assignment_position,
                alpha=request.alpha,
            )
            assignment = ScenarioAssignments.create(form, selected_scenario.scenario_id, sampling_audit)
            
            # Increment n_assigned counter
            Scenarios.increment_counter(selected_scenario.scenario_id, "n_assigned")
            
            db.commit()
        
        return ScenarioAssignResponse(
            assignment_id=assignment.assignment_id,
            scenario_id=selected_scenario.scenario_id,
            prompt_text=selected_scenario.prompt_text,
            response_text=selected_scenario.response_text,
            assignment_position=assignment.assignment_position,
            sampling_audit=sampling_audit,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error assigning scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ScenarioStatusUpdateRequest(BaseModel):
    assignment_id: str
    skip_stage: Optional[str] = None
    skip_reason: Optional[str] = None
    skip_reason_text: Optional[str] = None


@router.post("/moderation/scenarios/start")
async def start_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as started"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        updated = ScenarioAssignments.update_status(
            request.assignment_id,
            AssignmentStatus.STARTED,
            started_at=ts,
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {"status": "started", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error starting scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/complete")
async def complete_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as completed and calculate issue_any"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Calculate issue_any from highlights count
        from open_webui.models.selections import Selections
        highlights = Selections.get_selections_by_assignment(request.assignment_id)
        issue_any = 1 if len(highlights) > 0 else 0
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.COMPLETED,
                ended_at=ts,
                issue_any=issue_any,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_completed counter
            Scenarios.increment_counter(assignment.scenario_id, "n_completed")
            db.commit()
        
        return {
            "status": "completed",
            "assignment_id": request.assignment_id,
            "issue_any": issue_any,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error completing scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/skip")
async def skip_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as skipped"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.SKIPPED,
                ended_at=ts,
                issue_any=None,
                skip_stage=request.skip_stage,
                skip_reason=request.skip_reason,
                skip_reason_text=request.skip_reason_text,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_skipped counter
            Scenarios.increment_counter(assignment.scenario_id, "n_skipped")
            db.commit()
        
        return {"status": "skipped", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error skipping scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/abandon")
async def abandon_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as abandoned and trigger reassignment"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.ABANDONED,
                ended_at=ts,
                issue_any=None,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_abandoned counter
            Scenarios.increment_counter(assignment.scenario_id, "n_abandoned")
            db.commit()
        
        # Trigger reassignment (create new assignment in same session slot)
        reassign_form = ScenarioAssignmentForm(
            participant_id=assignment.participant_id,
            child_profile_id=assignment.child_profile_id,
            assignment_position=assignment.assignment_position,
            alpha=assignment.alpha or 1.0,
        )
        
        # Perform weighted sampling for reassignment
        result = Scenarios.weighted_sample(
            participant_id=assignment.participant_id,
            alpha=assignment.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if result:
            new_scenario, sampling_audit = result
            with get_db() as db:
                new_assignment = ScenarioAssignments.create(
                    reassign_form,
                    new_scenario.scenario_id,
                    sampling_audit,
                )
                Scenarios.increment_counter(new_scenario.scenario_id, "n_assigned")
                db.commit()
            
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": True,
                "new_assignment_id": new_assignment.assignment_id,
                "new_scenario_id": new_scenario.scenario_id,
            }
        else:
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": False,
                "message": "No eligible scenarios available for reassignment",
            }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error abandoning scenario: {e}")
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


# New scenario assignment endpoints

class ScenarioAssignRequest(BaseModel):
    participant_id: str
    child_profile_id: Optional[str] = None
    assignment_position: Optional[int] = None
    alpha: Optional[float] = 1.0  # Weighted sampling alpha parameter


class ScenarioAssignResponse(BaseModel):
    assignment_id: str
    scenario_id: str
    prompt_text: str
    response_text: str
    assignment_position: Optional[int] = None
    sampling_audit: Optional[dict] = None


@router.post("/moderation/scenarios/assign", response_model=ScenarioAssignResponse)
async def assign_scenario(
    request: ScenarioAssignRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    Assign a scenario to a participant using weighted sampling.
    Atomically creates assignment and increments n_assigned counter.
    """
    try:
        if user.id != request.participant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Perform weighted sampling
        result = Scenarios.weighted_sample(
            participant_id=request.participant_id,
            alpha=request.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No eligible scenarios available")
        
        selected_scenario, sampling_audit = result
        
        # Create assignment atomically (in a transaction)
        with get_db() as db:
            # Create assignment
            form = ScenarioAssignmentForm(
                participant_id=request.participant_id,
                child_profile_id=request.child_profile_id,
                assignment_position=request.assignment_position,
                alpha=request.alpha,
            )
            assignment = ScenarioAssignments.create(form, selected_scenario.scenario_id, sampling_audit)
            
            # Increment n_assigned counter
            Scenarios.increment_counter(selected_scenario.scenario_id, "n_assigned")
            
            db.commit()
        
        return ScenarioAssignResponse(
            assignment_id=assignment.assignment_id,
            scenario_id=selected_scenario.scenario_id,
            prompt_text=selected_scenario.prompt_text,
            response_text=selected_scenario.response_text,
            assignment_position=assignment.assignment_position,
            sampling_audit=sampling_audit,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error assigning scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ScenarioStatusUpdateRequest(BaseModel):
    assignment_id: str
    skip_stage: Optional[str] = None
    skip_reason: Optional[str] = None
    skip_reason_text: Optional[str] = None


@router.post("/moderation/scenarios/start")
async def start_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as started"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        updated = ScenarioAssignments.update_status(
            request.assignment_id,
            AssignmentStatus.STARTED,
            started_at=ts,
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {"status": "started", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error starting scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/complete")
async def complete_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as completed and calculate issue_any"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Calculate issue_any from highlights count
        from open_webui.models.selections import Selections
        highlights = Selections.get_selections_by_assignment(request.assignment_id)
        issue_any = 1 if len(highlights) > 0 else 0
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.COMPLETED,
                ended_at=ts,
                issue_any=issue_any,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_completed counter
            Scenarios.increment_counter(assignment.scenario_id, "n_completed")
            db.commit()
        
        return {
            "status": "completed",
            "assignment_id": request.assignment_id,
            "issue_any": issue_any,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error completing scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/skip")
async def skip_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as skipped"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.SKIPPED,
                ended_at=ts,
                issue_any=None,
                skip_stage=request.skip_stage,
                skip_reason=request.skip_reason,
                skip_reason_text=request.skip_reason_text,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_skipped counter
            Scenarios.increment_counter(assignment.scenario_id, "n_skipped")
            db.commit()
        
        return {"status": "skipped", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error skipping scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/abandon")
async def abandon_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as abandoned and trigger reassignment"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.ABANDONED,
                ended_at=ts,
                issue_any=None,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_abandoned counter
            Scenarios.increment_counter(assignment.scenario_id, "n_abandoned")
            db.commit()
        
        # Trigger reassignment (create new assignment in same session slot)
        reassign_form = ScenarioAssignmentForm(
            participant_id=assignment.participant_id,
            child_profile_id=assignment.child_profile_id,
            assignment_position=assignment.assignment_position,
            alpha=assignment.alpha or 1.0,
        )
        
        # Perform weighted sampling for reassignment
        result = Scenarios.weighted_sample(
            participant_id=assignment.participant_id,
            alpha=assignment.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if result:
            new_scenario, sampling_audit = result
            with get_db() as db:
                new_assignment = ScenarioAssignments.create(
                    reassign_form,
                    new_scenario.scenario_id,
                    sampling_audit,
                )
                Scenarios.increment_counter(new_scenario.scenario_id, "n_assigned")
                db.commit()
            
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": True,
                "new_assignment_id": new_assignment.assignment_id,
                "new_scenario_id": new_scenario.scenario_id,
            }
        else:
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": False,
                "message": "No eligible scenarios available for reassignment",
            }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error abandoning scenario: {e}")
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


# New scenario assignment endpoints

class ScenarioAssignRequest(BaseModel):
    participant_id: str
    child_profile_id: Optional[str] = None
    assignment_position: Optional[int] = None
    alpha: Optional[float] = 1.0  # Weighted sampling alpha parameter


class ScenarioAssignResponse(BaseModel):
    assignment_id: str
    scenario_id: str
    prompt_text: str
    response_text: str
    assignment_position: Optional[int] = None
    sampling_audit: Optional[dict] = None


@router.post("/moderation/scenarios/assign", response_model=ScenarioAssignResponse)
async def assign_scenario(
    request: ScenarioAssignRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    Assign a scenario to a participant using weighted sampling.
    Atomically creates assignment and increments n_assigned counter.
    """
    try:
        if user.id != request.participant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Perform weighted sampling
        result = Scenarios.weighted_sample(
            participant_id=request.participant_id,
            alpha=request.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No eligible scenarios available")
        
        selected_scenario, sampling_audit = result
        
        # Create assignment atomically (in a transaction)
        with get_db() as db:
            # Create assignment
            form = ScenarioAssignmentForm(
                participant_id=request.participant_id,
                child_profile_id=request.child_profile_id,
                assignment_position=request.assignment_position,
                alpha=request.alpha,
            )
            assignment = ScenarioAssignments.create(form, selected_scenario.scenario_id, sampling_audit)
            
            # Increment n_assigned counter
            Scenarios.increment_counter(selected_scenario.scenario_id, "n_assigned")
            
            db.commit()
        
        return ScenarioAssignResponse(
            assignment_id=assignment.assignment_id,
            scenario_id=selected_scenario.scenario_id,
            prompt_text=selected_scenario.prompt_text,
            response_text=selected_scenario.response_text,
            assignment_position=assignment.assignment_position,
            sampling_audit=sampling_audit,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error assigning scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ScenarioStatusUpdateRequest(BaseModel):
    assignment_id: str
    skip_stage: Optional[str] = None
    skip_reason: Optional[str] = None
    skip_reason_text: Optional[str] = None


@router.post("/moderation/scenarios/start")
async def start_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as started"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        updated = ScenarioAssignments.update_status(
            request.assignment_id,
            AssignmentStatus.STARTED,
            started_at=ts,
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {"status": "started", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error starting scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/complete")
async def complete_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as completed and calculate issue_any"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Calculate issue_any from highlights count
        from open_webui.models.selections import Selections
        highlights = Selections.get_selections_by_assignment(request.assignment_id)
        issue_any = 1 if len(highlights) > 0 else 0
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.COMPLETED,
                ended_at=ts,
                issue_any=issue_any,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_completed counter
            Scenarios.increment_counter(assignment.scenario_id, "n_completed")
            db.commit()
        
        return {
            "status": "completed",
            "assignment_id": request.assignment_id,
            "issue_any": issue_any,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error completing scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/skip")
async def skip_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as skipped"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.SKIPPED,
                ended_at=ts,
                issue_any=None,
                skip_stage=request.skip_stage,
                skip_reason=request.skip_reason,
                skip_reason_text=request.skip_reason_text,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_skipped counter
            Scenarios.increment_counter(assignment.scenario_id, "n_skipped")
            db.commit()
        
        return {"status": "skipped", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error skipping scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/abandon")
async def abandon_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as abandoned and trigger reassignment"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.ABANDONED,
                ended_at=ts,
                issue_any=None,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_abandoned counter
            Scenarios.increment_counter(assignment.scenario_id, "n_abandoned")
            db.commit()
        
        # Trigger reassignment (create new assignment in same session slot)
        reassign_form = ScenarioAssignmentForm(
            participant_id=assignment.participant_id,
            child_profile_id=assignment.child_profile_id,
            assignment_position=assignment.assignment_position,
            alpha=assignment.alpha or 1.0,
        )
        
        # Perform weighted sampling for reassignment
        result = Scenarios.weighted_sample(
            participant_id=assignment.participant_id,
            alpha=assignment.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if result:
            new_scenario, sampling_audit = result
            with get_db() as db:
                new_assignment = ScenarioAssignments.create(
                    reassign_form,
                    new_scenario.scenario_id,
                    sampling_audit,
                )
                Scenarios.increment_counter(new_scenario.scenario_id, "n_assigned")
                db.commit()
            
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": True,
                "new_assignment_id": new_assignment.assignment_id,
                "new_scenario_id": new_scenario.scenario_id,
            }
        else:
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": False,
                "message": "No eligible scenarios available for reassignment",
            }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error abandoning scenario: {e}")
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


# New scenario assignment endpoints

class ScenarioAssignRequest(BaseModel):
    participant_id: str
    child_profile_id: Optional[str] = None
    assignment_position: Optional[int] = None
    alpha: Optional[float] = 1.0  # Weighted sampling alpha parameter


class ScenarioAssignResponse(BaseModel):
    assignment_id: str
    scenario_id: str
    prompt_text: str
    response_text: str
    assignment_position: Optional[int] = None
    sampling_audit: Optional[dict] = None


@router.post("/moderation/scenarios/assign", response_model=ScenarioAssignResponse)
async def assign_scenario(
    request: ScenarioAssignRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    Assign a scenario to a participant using weighted sampling.
    Atomically creates assignment and increments n_assigned counter.
    """
    try:
        if user.id != request.participant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Perform weighted sampling
        result = Scenarios.weighted_sample(
            participant_id=request.participant_id,
            alpha=request.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No eligible scenarios available")
        
        selected_scenario, sampling_audit = result
        
        # Create assignment atomically (in a transaction)
        with get_db() as db:
            # Create assignment
            form = ScenarioAssignmentForm(
                participant_id=request.participant_id,
                child_profile_id=request.child_profile_id,
                assignment_position=request.assignment_position,
                alpha=request.alpha,
            )
            assignment = ScenarioAssignments.create(form, selected_scenario.scenario_id, sampling_audit)
            
            # Increment n_assigned counter
            Scenarios.increment_counter(selected_scenario.scenario_id, "n_assigned")
            
            db.commit()
        
        return ScenarioAssignResponse(
            assignment_id=assignment.assignment_id,
            scenario_id=selected_scenario.scenario_id,
            prompt_text=selected_scenario.prompt_text,
            response_text=selected_scenario.response_text,
            assignment_position=assignment.assignment_position,
            sampling_audit=sampling_audit,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error assigning scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ScenarioStatusUpdateRequest(BaseModel):
    assignment_id: str
    skip_stage: Optional[str] = None
    skip_reason: Optional[str] = None
    skip_reason_text: Optional[str] = None


@router.post("/moderation/scenarios/start")
async def start_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as started"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        updated = ScenarioAssignments.update_status(
            request.assignment_id,
            AssignmentStatus.STARTED,
            started_at=ts,
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {"status": "started", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error starting scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/complete")
async def complete_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as completed and calculate issue_any"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Calculate issue_any from highlights count
        from open_webui.models.selections import Selections
        highlights = Selections.get_selections_by_assignment(request.assignment_id)
        issue_any = 1 if len(highlights) > 0 else 0
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.COMPLETED,
                ended_at=ts,
                issue_any=issue_any,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_completed counter
            Scenarios.increment_counter(assignment.scenario_id, "n_completed")
            db.commit()
        
        return {
            "status": "completed",
            "assignment_id": request.assignment_id,
            "issue_any": issue_any,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error completing scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/skip")
async def skip_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as skipped"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.SKIPPED,
                ended_at=ts,
                issue_any=None,
                skip_stage=request.skip_stage,
                skip_reason=request.skip_reason,
                skip_reason_text=request.skip_reason_text,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_skipped counter
            Scenarios.increment_counter(assignment.scenario_id, "n_skipped")
            db.commit()
        
        return {"status": "skipped", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error skipping scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/abandon")
async def abandon_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as abandoned and trigger reassignment"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.ABANDONED,
                ended_at=ts,
                issue_any=None,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_abandoned counter
            Scenarios.increment_counter(assignment.scenario_id, "n_abandoned")
            db.commit()
        
        # Trigger reassignment (create new assignment in same session slot)
        reassign_form = ScenarioAssignmentForm(
            participant_id=assignment.participant_id,
            child_profile_id=assignment.child_profile_id,
            assignment_position=assignment.assignment_position,
            alpha=assignment.alpha or 1.0,
        )
        
        # Perform weighted sampling for reassignment
        result = Scenarios.weighted_sample(
            participant_id=assignment.participant_id,
            alpha=assignment.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if result:
            new_scenario, sampling_audit = result
            with get_db() as db:
                new_assignment = ScenarioAssignments.create(
                    reassign_form,
                    new_scenario.scenario_id,
                    sampling_audit,
                )
                Scenarios.increment_counter(new_scenario.scenario_id, "n_assigned")
                db.commit()
            
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": True,
                "new_assignment_id": new_assignment.assignment_id,
                "new_scenario_id": new_scenario.scenario_id,
            }
        else:
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": False,
                "message": "No eligible scenarios available for reassignment",
            }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error abandoning scenario: {e}")
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


# New scenario assignment endpoints

class ScenarioAssignRequest(BaseModel):
    participant_id: str
    child_profile_id: Optional[str] = None
    assignment_position: Optional[int] = None
    alpha: Optional[float] = 1.0  # Weighted sampling alpha parameter


class ScenarioAssignResponse(BaseModel):
    assignment_id: str
    scenario_id: str
    prompt_text: str
    response_text: str
    assignment_position: Optional[int] = None
    sampling_audit: Optional[dict] = None


@router.post("/moderation/scenarios/assign", response_model=ScenarioAssignResponse)
async def assign_scenario(
    request: ScenarioAssignRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    Assign a scenario to a participant using weighted sampling.
    Atomically creates assignment and increments n_assigned counter.
    """
    try:
        if user.id != request.participant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Perform weighted sampling
        result = Scenarios.weighted_sample(
            participant_id=request.participant_id,
            alpha=request.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No eligible scenarios available")
        
        selected_scenario, sampling_audit = result
        
        # Create assignment atomically (in a transaction)
        with get_db() as db:
            # Create assignment
            form = ScenarioAssignmentForm(
                participant_id=request.participant_id,
                child_profile_id=request.child_profile_id,
                assignment_position=request.assignment_position,
                alpha=request.alpha,
            )
            assignment = ScenarioAssignments.create(form, selected_scenario.scenario_id, sampling_audit)
            
            # Increment n_assigned counter
            Scenarios.increment_counter(selected_scenario.scenario_id, "n_assigned")
            
            db.commit()
        
        return ScenarioAssignResponse(
            assignment_id=assignment.assignment_id,
            scenario_id=selected_scenario.scenario_id,
            prompt_text=selected_scenario.prompt_text,
            response_text=selected_scenario.response_text,
            assignment_position=assignment.assignment_position,
            sampling_audit=sampling_audit,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error assigning scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ScenarioStatusUpdateRequest(BaseModel):
    assignment_id: str
    skip_stage: Optional[str] = None
    skip_reason: Optional[str] = None
    skip_reason_text: Optional[str] = None


@router.post("/moderation/scenarios/start")
async def start_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as started"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        updated = ScenarioAssignments.update_status(
            request.assignment_id,
            AssignmentStatus.STARTED,
            started_at=ts,
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {"status": "started", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error starting scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/complete")
async def complete_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as completed and calculate issue_any"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Calculate issue_any from highlights count
        from open_webui.models.selections import Selections
        highlights = Selections.get_selections_by_assignment(request.assignment_id)
        issue_any = 1 if len(highlights) > 0 else 0
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.COMPLETED,
                ended_at=ts,
                issue_any=issue_any,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_completed counter
            Scenarios.increment_counter(assignment.scenario_id, "n_completed")
            db.commit()
        
        return {
            "status": "completed",
            "assignment_id": request.assignment_id,
            "issue_any": issue_any,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error completing scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/skip")
async def skip_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as skipped"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.SKIPPED,
                ended_at=ts,
                issue_any=None,
                skip_stage=request.skip_stage,
                skip_reason=request.skip_reason,
                skip_reason_text=request.skip_reason_text,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_skipped counter
            Scenarios.increment_counter(assignment.scenario_id, "n_skipped")
            db.commit()
        
        return {"status": "skipped", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error skipping scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/abandon")
async def abandon_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as abandoned and trigger reassignment"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.ABANDONED,
                ended_at=ts,
                issue_any=None,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_abandoned counter
            Scenarios.increment_counter(assignment.scenario_id, "n_abandoned")
            db.commit()
        
        # Trigger reassignment (create new assignment in same session slot)
        reassign_form = ScenarioAssignmentForm(
            participant_id=assignment.participant_id,
            child_profile_id=assignment.child_profile_id,
            assignment_position=assignment.assignment_position,
            alpha=assignment.alpha or 1.0,
        )
        
        # Perform weighted sampling for reassignment
        result = Scenarios.weighted_sample(
            participant_id=assignment.participant_id,
            alpha=assignment.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if result:
            new_scenario, sampling_audit = result
            with get_db() as db:
                new_assignment = ScenarioAssignments.create(
                    reassign_form,
                    new_scenario.scenario_id,
                    sampling_audit,
                )
                Scenarios.increment_counter(new_scenario.scenario_id, "n_assigned")
                db.commit()
            
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": True,
                "new_assignment_id": new_assignment.assignment_id,
                "new_scenario_id": new_scenario.scenario_id,
            }
        else:
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": False,
                "message": "No eligible scenarios available for reassignment",
            }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error abandoning scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/moderation/scenarios/available")
async def get_available_scenarios(
    child_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """
    Get available scenarios for the current session that the user hasn't seen yet.
    Returns random scenario indices independent of child characteristics.
    """
    try:
        # Get all sessions for this user to find seen scenarios
        all_sessions = ModerationSessions.get_sessions_by_user(user.id, child_id)
        seen_scenario_indices = set()
        
        for session in all_sessions:
            seen_scenario_indices.add(session.scenario_index)
        
        # Get child profile to verify it exists
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
        
        # Return all unseen scenarios in random order (independent of characteristics)
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


# New scenario assignment endpoints

class ScenarioAssignRequest(BaseModel):
    participant_id: str
    child_profile_id: Optional[str] = None
    assignment_position: Optional[int] = None
    alpha: Optional[float] = 1.0  # Weighted sampling alpha parameter


class ScenarioAssignResponse(BaseModel):
    assignment_id: str
    scenario_id: str
    prompt_text: str
    response_text: str
    assignment_position: Optional[int] = None
    sampling_audit: Optional[dict] = None


@router.post("/moderation/scenarios/assign", response_model=ScenarioAssignResponse)
async def assign_scenario(
    request: ScenarioAssignRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    Assign a scenario to a participant using weighted sampling.
    Atomically creates assignment and increments n_assigned counter.
    """
    try:
        if user.id != request.participant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Perform weighted sampling
        result = Scenarios.weighted_sample(
            participant_id=request.participant_id,
            alpha=request.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No eligible scenarios available")
        
        selected_scenario, sampling_audit = result
        
        # Create assignment atomically (in a transaction)
        with get_db() as db:
            # Create assignment
            form = ScenarioAssignmentForm(
                participant_id=request.participant_id,
                child_profile_id=request.child_profile_id,
                assignment_position=request.assignment_position,
                alpha=request.alpha,
            )
            assignment = ScenarioAssignments.create(form, selected_scenario.scenario_id, sampling_audit)
            
            # Increment n_assigned counter
            Scenarios.increment_counter(selected_scenario.scenario_id, "n_assigned")
            
            db.commit()
        
        return ScenarioAssignResponse(
            assignment_id=assignment.assignment_id,
            scenario_id=selected_scenario.scenario_id,
            prompt_text=selected_scenario.prompt_text,
            response_text=selected_scenario.response_text,
            assignment_position=assignment.assignment_position,
            sampling_audit=sampling_audit,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error assigning scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ScenarioStatusUpdateRequest(BaseModel):
    assignment_id: str
    skip_stage: Optional[str] = None
    skip_reason: Optional[str] = None
    skip_reason_text: Optional[str] = None


@router.post("/moderation/scenarios/start")
async def start_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as started"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        updated = ScenarioAssignments.update_status(
            request.assignment_id,
            AssignmentStatus.STARTED,
            started_at=ts,
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {"status": "started", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error starting scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/complete")
async def complete_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as completed and calculate issue_any"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        # Calculate issue_any from highlights count
        from open_webui.models.selections import Selections
        highlights = Selections.get_selections_by_assignment(request.assignment_id)
        issue_any = 1 if len(highlights) > 0 else 0
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.COMPLETED,
                ended_at=ts,
                issue_any=issue_any,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_completed counter
            Scenarios.increment_counter(assignment.scenario_id, "n_completed")
            db.commit()
        
        return {
            "status": "completed",
            "assignment_id": request.assignment_id,
            "issue_any": issue_any,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error completing scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/skip")
async def skip_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as skipped"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.SKIPPED,
                ended_at=ts,
                issue_any=None,
                skip_stage=request.skip_stage,
                skip_reason=request.skip_reason,
                skip_reason_text=request.skip_reason_text,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_skipped counter
            Scenarios.increment_counter(assignment.scenario_id, "n_skipped")
            db.commit()
        
        return {"status": "skipped", "assignment_id": request.assignment_id}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error skipping scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/abandon")
async def abandon_scenario(
    request: ScenarioStatusUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Mark a scenario assignment as abandoned and trigger reassignment"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        ts = int(time.time() * 1000)
        
        # Update assignment and increment counter atomically
        with get_db() as db:
            updated = ScenarioAssignments.update_status(
                request.assignment_id,
                AssignmentStatus.ABANDONED,
                ended_at=ts,
                issue_any=None,
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            # Increment n_abandoned counter
            Scenarios.increment_counter(assignment.scenario_id, "n_abandoned")
            db.commit()
        
        # Trigger reassignment (create new assignment in same session slot)
        reassign_form = ScenarioAssignmentForm(
            participant_id=assignment.participant_id,
            child_profile_id=assignment.child_profile_id,
            assignment_position=assignment.assignment_position,
            alpha=assignment.alpha or 1.0,
        )
        
        # Perform weighted sampling for reassignment
        result = Scenarios.weighted_sample(
            participant_id=assignment.participant_id,
            alpha=assignment.alpha or 1.0,
            is_active=True,
            is_validated=True,
        )
        
        if result:
            new_scenario, sampling_audit = result
            with get_db() as db:
                new_assignment = ScenarioAssignments.create(
                    reassign_form,
                    new_scenario.scenario_id,
                    sampling_audit,
                )
                Scenarios.increment_counter(new_scenario.scenario_id, "n_assigned")
                db.commit()
            
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": True,
                "new_assignment_id": new_assignment.assignment_id,
                "new_scenario_id": new_scenario.scenario_id,
            }
        else:
            return {
                "status": "abandoned",
                "assignment_id": request.assignment_id,
                "reassigned": False,
                "message": "No eligible scenarios available for reassignment",
            }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error abandoning scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")