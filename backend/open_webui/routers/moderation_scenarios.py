import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.models.moderation import (
    ModerationScenarios,
    ModerationScenarioForm,
    ModerationApplieds,
    ModerationAppliedForm,
    ModerationQuestionAnswers,
    ModerationQuestionAnswerForm,
)

log = logging.getLogger(__name__)

router = APIRouter()


class ScenarioCreateForm(ModerationScenarioForm):
    scenario_id: Optional[str] = None


@router.post("/moderation/scenarios")
async def create_or_update_scenario(
    form_data: ScenarioCreateForm,
    user: UserModel = Depends(get_verified_user),
):
    try:
        if user.id != form_data.user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        result = ModerationScenarios.upsert(form_data, scenario_id=form_data.scenario_id)
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error upserting scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ScenarioPatchForm(BaseModel):
    is_applicable: Optional[bool] = None
    decision: Optional[str] = None
    decided_at: Optional[int] = None


@router.patch("/moderation/scenarios/{scenario_id}")
async def patch_scenario(
    scenario_id: str,
    form_data: ScenarioPatchForm,
    user: UserModel = Depends(get_verified_user),
):
    try:
        # Simple update via upsert: fetch and update
        existing = ModerationScenarios.upsert(
            ModerationScenarioForm(
                user_id=user.id,
                child_id="",
                scenario_prompt="",
                original_response="",
            ),
            scenario_id=scenario_id,
        )
        # Apply partial updates
        from open_webui.internal.db import get_db
        from open_webui.models.moderation import ModerationScenario
        with get_db() as db:
            obj = db.query(ModerationScenario).filter(ModerationScenario.id == scenario_id).first()
            if not obj:
                raise HTTPException(status_code=404, detail="Scenario not found")
            if form_data.is_applicable is not None:
                obj.is_applicable = form_data.is_applicable
            if form_data.decision is not None:
                obj.decision = form_data.decision
            if form_data.decided_at is not None:
                obj.decided_at = form_data.decided_at
            db.add(obj)
            db.commit()
        return {"status": True}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error patching scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/{scenario_id}/answers")
async def upsert_answer(
    scenario_id: str,
    form_data: ModerationQuestionAnswerForm,
    user: UserModel = Depends(get_verified_user),
):
    try:
        if form_data.scenario_id != scenario_id:
            raise HTTPException(status_code=400, detail="Scenario ID mismatch")
        result = ModerationQuestionAnswers.upsert(form_data)
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error upserting answer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/moderation/scenarios/{scenario_id}/versions")
async def create_version(
    scenario_id: str,
    form_data: ModerationAppliedForm,
    user: UserModel = Depends(get_verified_user),
):
    try:
        if form_data.scenario_id != scenario_id:
            raise HTTPException(status_code=400, detail="Scenario ID mismatch")
        result = ModerationApplieds.create_version(form_data)
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating version: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class ConfirmForm(BaseModel):
    version_index: int


@router.post("/moderation/scenarios/{scenario_id}/confirm")
async def confirm_version(
    scenario_id: str,
    form_data: ConfirmForm,
    user: UserModel = Depends(get_verified_user),
):
    try:
        ModerationApplieds.confirm_version(scenario_id, form_data.version_index)
        # Also set scenario decision to 'moderate' if not already
        from open_webui.internal.db import get_db
        from open_webui.models.moderation import ModerationScenario
        with get_db() as db:
            obj = db.query(ModerationScenario).filter(ModerationScenario.id == scenario_id).first()
            if obj and obj.decision is None:
                obj.decision = "moderate"
                db.add(obj)
                db.commit()
        return {"status": True}
    except Exception as e:
        log.error(f"Error confirming version: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class SelectionSaveForm(BaseModel):
    scenario_id: str
    text: str
    source: str  # 'prompt' | 'response'


@router.post("/moderation/scenarios/{scenario_id}/selections")
async def save_selection_for_scenario(
    scenario_id: str,
    form_data: SelectionSaveForm,
    user: UserModel = Depends(get_verified_user),
):
    try:
        if form_data.scenario_id != scenario_id:
            raise HTTPException(status_code=400, detail="Scenario ID mismatch")
        # Reuse selections table for storage
        from open_webui.models.selections import SelectionForm, Selections
        sel = Selections.insert_new_selection(
            SelectionForm(
                chat_id=scenario_id,
                message_id=f"{scenario_id}:{form_data.source}",
                role=("user" if form_data.source == "prompt" else "assistant"),
                selected_text=form_data.text,
                child_id=None,
                context=None,
                meta={"scenario_id": scenario_id, "source": form_data.source},
            ),
            user.id,
        )
        return sel.model_dump() if sel else {"status": False}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error saving selection for scenario: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


