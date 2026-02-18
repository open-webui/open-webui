import logging
import random
import time
import hashlib
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.models.users import UserModel
from open_webui.routers.workflow import get_current_attempt_number
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
    ScenarioModel,
    ScenarioForm,
    AssignmentStatus,
    AttentionCheckScenarios,
    AttentionCheckScenarioForm,
    Scenario,
    AttentionCheckScenario,
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
    highlighted_texts: Optional[List[dict]] = None
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
        )

        if not result:
            raise HTTPException(
                status_code=404, detail="No eligible scenarios available"
            )

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
            assignment = ScenarioAssignments.create(
                form, selected_scenario.scenario_id, sampling_audit
            )

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
    duration_seconds: Optional[int] = None
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
                duration_seconds=request.duration_seconds,
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
                duration_seconds=request.duration_seconds,
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
                duration_seconds=request.duration_seconds,
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
                "new_prompt_text": new_scenario.prompt_text,
                "new_response_text": new_scenario.response_text,
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


class ScenarioDurationUpdateRequest(BaseModel):
    assignment_id: str
    duration_seconds: int


class ScenarioDurationUpdateResponse(BaseModel):
    status: str
    assignment_id: str
    duration_seconds: int


@router.post(
    "/moderation/scenarios/update-duration",
    response_model=ScenarioDurationUpdateResponse,
)
async def update_scenario_duration(
    request: ScenarioDurationUpdateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Update the duration_seconds for a scenario assignment without changing its status"""
    try:
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

        updated = ScenarioAssignments.update_duration(
            request.assignment_id,
            request.duration_seconds,
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {
            "status": "duration_updated",
            "assignment_id": request.assignment_id,
            "duration_seconds": updated.duration_seconds,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating scenario duration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Highlights endpoints (using Selection table)
class HighlightCreateRequest(BaseModel):
    assignment_id: str
    selected_text: str
    source: str  # 'prompt' | 'response'
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    context: Optional[str] = None


class HighlightResponse(BaseModel):
    id: str
    assignment_id: str
    selected_text: str
    source: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    created_at: int


@router.post("/moderation/highlights", response_model=HighlightResponse)
async def create_highlight(
    request: HighlightCreateRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Create a highlight for an assignment using Selection table"""
    try:
        # Get assignment to verify ownership
        assignment = ScenarioAssignments.get_by_id(request.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Create selection record with offsets
        from open_webui.models.selections import SelectionForm, Selections

        form = SelectionForm(
            chat_id=f"assignment_{request.assignment_id}",
            message_id=f"{request.assignment_id}:{request.source}",
            role="user" if request.source == "prompt" else "assistant",
            selected_text=request.selected_text,
            assignment_id=request.assignment_id,
            source=request.source,
            start_offset=request.start_offset,
            end_offset=request.end_offset,
            context=request.context,
        )

        selection = Selections.insert_new_selection(form, user.id)
        if not selection:
            raise HTTPException(status_code=500, detail="Failed to create highlight")

        return HighlightResponse(
            id=selection.id,
            assignment_id=selection.assignment_id or request.assignment_id,
            selected_text=selection.selected_text,
            source=selection.source or request.source,
            start_offset=selection.start_offset,
            end_offset=selection.end_offset,
            created_at=selection.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating highlight: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/moderation/highlights/{assignment_id}", response_model=List[HighlightResponse]
)
async def get_highlights(
    assignment_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """Get all highlights for an assignment using Selection table"""
    try:
        assignment = ScenarioAssignments.get_by_id(assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if assignment.participant_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

        from open_webui.models.selections import Selections

        selections = Selections.get_selections_by_assignment(assignment_id)

        return [
            HighlightResponse(
                id=s.id,
                assignment_id=s.assignment_id or assignment_id,
                selected_text=s.selected_text,
                source=s.source or "response",
                start_offset=s.start_offset,
                end_offset=s.end_offset,
                created_at=s.created_at,
            )
            for s in selections
        ]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting highlights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class AttentionCheckResponse(BaseModel):
    scenario_id: str
    prompt_text: str
    response_text: str
    trait_theme: Optional[str] = None
    trait_phrase: Optional[str] = None
    sentiment: Optional[str] = None


@router.get(
    "/moderation/attention-checks/random", response_model=AttentionCheckResponse
)
async def get_random_attention_check(
    user: UserModel = Depends(get_verified_user),
):
    """
    Get a random active attention check scenario.
    Uses simple random sampling (not weighted, since attention checks don't need balancing).
    """
    try:
        attention_check = AttentionCheckScenarios.get_random(is_active=True)

        if not attention_check:
            raise HTTPException(
                status_code=404, detail="No active attention check scenarios available"
            )

        return AttentionCheckResponse(
            scenario_id=attention_check.scenario_id,
            prompt_text=attention_check.prompt_text,
            response_text=attention_check.response_text,
            trait_theme=attention_check.trait_theme,
            trait_phrase=attention_check.trait_phrase,
            sentiment=attention_check.sentiment,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting random attention check: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class AssignmentWithScenario(BaseModel):
    assignment_id: str
    scenario_id: str
    prompt_text: str
    response_text: str
    assignment_position: int
    status: str
    assigned_at: int
    started_at: Optional[int] = None


@router.get(
    "/moderation/scenarios/assignments/{child_id}",
    response_model=List[AssignmentWithScenario],
)
async def get_assignments_for_child(
    child_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """
    Get existing scenario assignments for a child profile.
    Returns assignments with status 'assigned' or 'started', ordered by assignment_position.
    """
    try:
        # Verify the child profile belongs to the user
        child_profile = ChildProfiles.get_child_profile_by_id(child_id, user.id)
        if not child_profile:
            raise HTTPException(status_code=404, detail="Child profile not found")

        # Get current attempt number for the user
        current_attempt = get_current_attempt_number(user.id)

        log.info(
            f"Getting assignments for child {child_id}, user {user.id}, "
            f"current_attempt: {current_attempt}"
        )

        # Get assignments for this child, filtered to assigned/started status and current attempt
        assignments = ScenarioAssignments.get_assignments_by_child(
            child_id,
            status_filter=[
                AssignmentStatus.ASSIGNED.value,
                AssignmentStatus.STARTED.value,
            ],
            attempt_number=current_attempt,
        )

        log.info(
            f"Found {len(assignments)} assignments for child {child_id}, attempt {current_attempt}"
        )

        # Join with scenarios table to get prompt_text and response_text
        result = []
        for assignment in assignments:
            scenario = Scenarios.get_by_id(assignment.scenario_id)
            if scenario:
                result.append(
                    AssignmentWithScenario(
                        assignment_id=assignment.assignment_id,
                        scenario_id=assignment.scenario_id,
                        prompt_text=scenario.prompt_text,
                        response_text=scenario.response_text,
                        assignment_position=assignment.assignment_position or 0,
                        status=assignment.status,
                        assigned_at=assignment.assigned_at,
                        started_at=assignment.started_at,
                    )
                )

        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting assignments for child {child_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== ADMIN ENDPOINTS ==========


class ScenarioUpdateRequest(BaseModel):
    is_active: Optional[bool] = None


class ScenarioListResponse(BaseModel):
    scenarios: List[ScenarioModel]
    total: int
    active_count: int
    inactive_count: int


class ScenarioStatsResponse(BaseModel):
    total_scenarios: int
    active_scenarios: int
    inactive_scenarios: int
    total_assignments: int
    total_completed: int
    total_skipped: int
    total_abandoned: int


@router.post("/admin/scenarios/upload")
async def upload_scenarios_admin(
    file: UploadFile = File(...),
    set_name: str = Form("pilot"),
    source: str = Form("admin_upload"),
    deactivate_previous: bool = Form(False),
    user: UserModel = Depends(get_admin_user),
):
    """Admin endpoint to upload scenarios from a JSON file. Always creates new scenarios with UUID-based IDs."""
    import json

    try:
        if not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="File must be a JSON file")

        contents = await file.read()
        scenarios_data = json.loads(contents.decode("utf-8"))

        if not isinstance(scenarios_data, list):
            raise HTTPException(
                status_code=400, detail="JSON must contain a list of scenarios"
            )

        # Deactivate previous scenarios if requested
        deactivated_count = 0
        if deactivate_previous:
            deactivated_count = Scenarios.deactivate_by_set_name(set_name)
            log.info(
                f"Deactivated {deactivated_count} previous scenarios with set_name='{set_name}'"
            )

        loaded_count = 0
        error_count = 0
        errors = []
        ts = int(time.time() * 1000)

        with get_db() as db:
            for idx, scenario_data in enumerate(scenarios_data, 1):
                try:
                    # Accept multiple field name formats for flexibility
                    prompt_text = (
                        scenario_data.get("child_prompt")
                        or scenario_data.get("prompt_text")
                        or scenario_data.get("prompt", "")
                    )
                    response_text = (
                        scenario_data.get("model_response")
                        or scenario_data.get("response_text")
                        or scenario_data.get("response", "")
                    )

                    if not prompt_text or not response_text:
                        error_count += 1
                        errors.append(f"Scenario {idx}: Missing prompt or response")
                        continue

                    # Trait: top-level or nested in big_five (pilot_scenarios format)
                    big_five = scenario_data.get("big_five") or {}
                    trait = scenario_data.get("trait") or (
                        big_five.get("trait") if isinstance(big_five, dict) else None
                    )
                    trait_level = (
                        big_five.get("level") if isinstance(big_five, dict) else None
                    )

                    # Generate new UUID-based scenario_id for each upload
                    scenario_id = f"scenario_{uuid.uuid4()}"

                    # Create new scenario directly (always new, never update)
                    obj = Scenario(
                        scenario_id=scenario_id,
                        prompt_text=prompt_text,
                        response_text=response_text,
                        set_name=set_name,
                        trait=trait,
                        polarity=scenario_data.get("polarity"),
                        prompt_style=scenario_data.get("prompt_style"),
                        domain=scenario_data.get("domain"),
                        persona_id=scenario_data.get("persona_id"),
                        age_band=scenario_data.get("age_band"),
                        gender_identity=scenario_data.get("gender_identity"),
                        context=scenario_data.get("context"),
                        piaget_stage=scenario_data.get("piaget_stage"),
                        trait_level=trait_level,
                        intent=scenario_data.get("intent"),
                        subdomain=scenario_data.get("subdomain"),
                        safety_notes=scenario_data.get("safety_notes"),
                        source=source,
                        model_name=scenario_data.get("model_name"),
                        is_active=True,
                        n_assigned=0,
                        n_completed=0,
                        n_skipped=0,
                        n_abandoned=0,
                        created_at=ts,
                        updated_at=ts,
                    )
                    db.add(obj)
                    loaded_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"Scenario {idx}: {str(e)}")

            db.commit()

        return {
            "status": "success",
            "loaded": loaded_count,
            "updated": 0,  # Always 0 since we always create new
            "deactivated_count": deactivated_count,
            "errors": error_count,
            "total": len(scenarios_data),
            "error_details": errors[:10] if errors else [],
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        log.error(f"Error uploading scenarios: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error uploading scenarios: {str(e)}"
        )


@router.get("/admin/scenarios", response_model=ScenarioListResponse)
async def list_scenarios_admin(
    is_active: Optional[bool] = None,
    trait: Optional[str] = None,
    polarity: Optional[str] = None,
    domain: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    user: UserModel = Depends(get_admin_user),
):
    """Admin endpoint to list all scenarios with filtering and pagination"""
    try:
        all_scenarios = Scenarios.get_all(is_active=is_active)

        # Apply filters
        filtered = all_scenarios
        if trait:
            filtered = [s for s in filtered if s.trait == trait]
        if polarity:
            filtered = [s for s in filtered if s.polarity == polarity]
        if domain:
            filtered = [s for s in filtered if s.domain == domain]

        # Calculate stats
        active_count = sum(1 for s in filtered if s.is_active)
        inactive_count = len(filtered) - active_count

        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered[start_idx:end_idx]

        return ScenarioListResponse(
            scenarios=paginated,
            total=len(filtered),
            active_count=active_count,
            inactive_count=inactive_count,
        )
    except Exception as e:
        log.error(f"Error listing scenarios: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/admin/scenarios/stats", response_model=ScenarioStatsResponse)
async def get_scenario_stats_admin(
    user: UserModel = Depends(get_admin_user),
):
    """Admin endpoint to get aggregate statistics about scenarios"""
    try:
        all_scenarios = Scenarios.get_all()
        active_scenarios = [s for s in all_scenarios if s.is_active]

        total_assignments = sum(s.n_assigned for s in all_scenarios)
        total_completed = sum(s.n_completed for s in all_scenarios)
        total_skipped = sum(s.n_skipped for s in all_scenarios)
        total_abandoned = sum(s.n_abandoned for s in all_scenarios)

        return ScenarioStatsResponse(
            total_scenarios=len(all_scenarios),
            active_scenarios=len(active_scenarios),
            inactive_scenarios=len(all_scenarios) - len(active_scenarios),
            total_assignments=total_assignments,
            total_completed=total_completed,
            total_skipped=total_skipped,
            total_abandoned=total_abandoned,
        )
    except Exception as e:
        log.error(f"Error getting scenario stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/admin/scenarios/{scenario_id}")
async def update_scenario_admin(
    scenario_id: str,
    request: ScenarioUpdateRequest,
    user: UserModel = Depends(get_admin_user),
):
    """Admin endpoint to update a scenario (e.g., toggle is_active)"""
    try:
        scenario = Scenarios.get_by_id(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        form = ScenarioForm(
            prompt_text=scenario.prompt_text,
            response_text=scenario.response_text,
            set_name=scenario.set_name,
            trait=scenario.trait,
            polarity=scenario.polarity,
            prompt_style=scenario.prompt_style,
            domain=scenario.domain,
            source=scenario.source,
            model_name=scenario.model_name,
            is_active=(
                request.is_active
                if request.is_active is not None
                else scenario.is_active
            ),
        )

        updated = Scenarios.upsert(form)
        return {"status": "success", "scenario": updated}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/admin/attention-checks/upload")
async def upload_attention_checks_admin(
    file: UploadFile = File(...),
    set_name: str = Form("default"),
    source: str = Form("admin_upload"),
    deactivate_previous: bool = Form(False),
    user: UserModel = Depends(get_admin_user),
):
    """Admin endpoint to upload attention check scenarios from JSON file. Always creates new attention checks with UUID-based IDs."""
    import json

    try:
        if not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="File must be a JSON file")

        contents = await file.read()
        data = json.loads(contents.decode("utf-8"))

        # Support both array format and object with scenarios array
        if isinstance(data, dict) and "scenarios" in data:
            scenarios_data = data["scenarios"]
        elif isinstance(data, list):
            scenarios_data = data
        else:
            raise HTTPException(
                status_code=400,
                detail="JSON must contain a list of scenarios or object with 'scenarios' array",
            )

        # Deactivate previous attention checks if requested
        deactivated_count = 0
        if deactivate_previous:
            deactivated_count = AttentionCheckScenarios.deactivate_by_set_name(set_name)
            log.info(
                f"Deactivated {deactivated_count} previous attention checks with set_name='{set_name}'"
            )

        loaded_count = 0
        error_count = 0
        errors = []
        ts = int(time.time() * 1000)

        with get_db() as db:
            for idx, scenario_data in enumerate(scenarios_data, 1):
                try:
                    # Accept multiple field name formats for flexibility (same as scenario upload)
                    prompt_text = (
                        scenario_data.get("child_prompt")
                        or scenario_data.get("prompt_text")
                        or scenario_data.get("prompt", "")
                    )
                    response_text = (
                        scenario_data.get("model_response")
                        or scenario_data.get("response_text")
                        or scenario_data.get("response", "")
                    )

                    if not prompt_text or not response_text:
                        error_count += 1
                        errors.append(
                            f"Attention check {idx}: Missing prompt or response"
                        )
                        continue

                    # Generate new UUID-based scenario_id for each upload
                    scenario_id = f"ac_{uuid.uuid4()}"

                    # Create new attention check directly (always new, never update)
                    obj = AttentionCheckScenario(
                        scenario_id=scenario_id,
                        prompt_text=prompt_text,
                        response_text=response_text,
                        trait_theme=scenario_data.get("trait_theme"),
                        trait_phrase=scenario_data.get("trait_phrase"),
                        sentiment=scenario_data.get("sentiment"),
                        trait_index=scenario_data.get("trait_index"),
                        prompt_index=scenario_data.get("prompt_index"),
                        set_name=set_name,
                        is_active=True,
                        source=source,
                        created_at=ts,
                        updated_at=ts,
                    )
                    db.add(obj)
                    loaded_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"Attention check {idx}: {str(e)}")

            db.commit()

        return {
            "status": "success",
            "loaded": loaded_count,
            "updated": 0,  # Always 0 since we always create new
            "deactivated_count": deactivated_count,
            "errors": error_count,
            "total": len(scenarios_data),
            "error_details": errors[:10] if errors else [],
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        log.error(f"Error uploading attention checks: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error uploading attention checks: {str(e)}"
        )


@router.get("/admin/attention-checks")
async def list_attention_checks_admin(
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
    user: UserModel = Depends(get_admin_user),
):
    """Admin endpoint to list all attention check scenarios"""
    try:
        all_checks = AttentionCheckScenarios.get_all(is_active=is_active)

        active_count = sum(1 for ac in all_checks if ac.is_active)
        inactive_count = len(all_checks) - active_count

        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = all_checks[start_idx:end_idx]

        return {
            "attention_checks": paginated,
            "total": len(all_checks),
            "active_count": active_count,
            "inactive_count": inactive_count,
        }
    except Exception as e:
        log.error(f"Error listing attention checks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/admin/attention-checks/{scenario_id}")
async def update_attention_check_admin(
    scenario_id: str,
    is_active: Optional[bool] = None,
    user: UserModel = Depends(get_admin_user),
):
    """Admin endpoint to update an attention check scenario"""
    try:
        ac = AttentionCheckScenarios.get_by_id(scenario_id)
        if not ac:
            raise HTTPException(
                status_code=404, detail="Attention check scenario not found"
            )

        form = AttentionCheckScenarioForm(
            prompt_text=ac.prompt_text,
            response_text=ac.response_text,
            trait_theme=ac.trait_theme,
            trait_phrase=ac.trait_phrase,
            sentiment=ac.sentiment,
            trait_index=ac.trait_index,
            prompt_index=ac.prompt_index,
            set_name=ac.set_name,
            is_active=is_active if is_active is not None else ac.is_active,
            source=ac.source,
        )

        updated = AttentionCheckScenarios.upsert(form)
        return {"status": "success", "attention_check": updated}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating attention check: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/admin/scenarios/set-names")
async def get_scenario_set_names(user: UserModel = Depends(get_admin_user)):
    """Get all distinct set_name values for scenarios"""
    try:
        set_names = Scenarios.get_distinct_set_names()
        return {"set_names": set_names}
    except Exception as e:
        log.error(f"Error getting scenario set names: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/admin/attention-checks/set-names")
async def get_attention_check_set_names(user: UserModel = Depends(get_admin_user)):
    """Get all distinct set_name values for attention checks"""
    try:
        set_names = AttentionCheckScenarios.get_distinct_set_names()
        return {"set_names": set_names}
    except Exception as e:
        log.error(f"Error getting attention check set names: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class SetActiveSetRequest(BaseModel):
    set_name: Optional[str] = None


@router.post("/admin/scenarios/set-active-set")
async def set_active_scenario_set(
    request: SetActiveSetRequest,
    user: UserModel = Depends(get_admin_user),
):
    """Set which set_name should be active. Activates all scenarios with that set_name and deactivates all others."""
    try:
        result = Scenarios.set_active_set(request.set_name)
        return {
            "status": "success",
            "activated": result["activated"],
            "deactivated": result["deactivated"],
            "set_name": request.set_name,
        }
    except Exception as e:
        log.error(f"Error setting active scenario set: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/admin/attention-checks/set-active-set")
async def set_active_attention_check_set(
    request: SetActiveSetRequest,
    user: UserModel = Depends(get_admin_user),
):
    """Set which set_name should be active. Activates all attention checks with that set_name and deactivates all others."""
    try:
        result = AttentionCheckScenarios.set_active_set(request.set_name)
        return {
            "status": "success",
            "activated": result["activated"],
            "deactivated": result["deactivated"],
            "set_name": request.set_name,
        }
    except Exception as e:
        log.error(f"Error setting active attention check set: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class SessionActivityPayload(BaseModel):
    user_id: str
    child_id: str
    session_number: int
    active_ms_cumulative: int


@router.post(
    "/moderation/session-activity", response_model=ModerationSessionActivityModel
)
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
        unseen_scenarios = [
            idx for idx in all_scenarios if idx not in seen_scenario_indices
        ]

        if not unseen_scenarios:
            # All scenarios have been seen, return empty list
            return {"available_scenarios": []}

        # Return all unseen scenarios in random order (independent of characteristics)
        random.shuffle(unseen_scenarios)

        return {
            "available_scenarios": unseen_scenarios,
            "total_seen": len(seen_scenario_indices),
            "total_available": len(unseen_scenarios),
            "session_number": user.session_number,
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting available scenarios: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
