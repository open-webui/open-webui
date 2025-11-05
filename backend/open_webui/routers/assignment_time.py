import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.models.assignment_time_tracking import (
    AssignmentSessionActivities,
    AssignmentSessionActivityForm,
    AssignmentSessionActivityModel,
)

log = logging.getLogger(__name__)

router = APIRouter()


class AssignmentSessionActivityPayload(BaseModel):
    user_id: str
    child_id: Optional[str] = None
    attempt_number: int
    active_ms_cumulative: int


@router.post("/assignment/session-activity", response_model=AssignmentSessionActivityModel)
async def post_assignment_session_activity(
    payload: AssignmentSessionActivityPayload,
    user: UserModel = Depends(get_verified_user),
):
    try:
        if user.id != payload.user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        form = AssignmentSessionActivityForm(
            user_id=payload.user_id,
            child_id=payload.child_id,
            attempt_number=payload.attempt_number,
            active_ms_cumulative=max(0, int(payload.active_ms_cumulative)),
        )
        return AssignmentSessionActivities.add_activity(form)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error posting assignment session activity: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



