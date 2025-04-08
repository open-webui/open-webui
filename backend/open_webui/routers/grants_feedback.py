import logging
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.uos_feedback import (
    GrantsFeedbackModel,
    GrantsFeedback,
    GrantsFeedbackForm,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.models.users import Users

from fastapi import APIRouter, Depends, HTTPException, status, Request

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

#####################
# Post Feedback Initial
#####################


@router.post("/{chat_id}", response_model=GrantsFeedbackModel)
async def insert_new_feedback(
    chat_id: str,
    form_data: GrantsFeedbackForm,
    user=Depends(get_verified_user),
):
    feedback = GrantsFeedback.insert_new_feedback(
        user_id=user.id,
        chat_id=chat_id,
        feedback_str=form_data.feedback,
        # optional: pass form_data.extra_data or others if needed
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to insert feedback",
        )
    return feedback


@router.get("/{chat_id}", response_model=GrantsFeedbackModel)
async def get_feedback_by_user_id_and_chat_id(
    chat_id: str,
    user=Depends(get_verified_user),
) -> Optional[GrantsFeedbackModel]:
    feedback = GrantsFeedback.get_feedback_by_user_id_and_chat_id(
        user_id=user.id,
        chat_id=chat_id,
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found"
        )
    return feedback


@router.post("/update_feedback/{chat_id}", response_model=GrantsFeedbackModel)
async def update_feedback_by_user_id_and_chat_id(
    chat_id: str,
    form_data: GrantsFeedbackForm,  # structured input
    user=Depends(get_verified_user)
) -> GrantsFeedbackModel:
    feedback = GrantsFeedback.update_feedback_by_user_id_and_chat_id(
        user_id=user.id,
        chat_id=chat_id,
        feedback_str=form_data.feedback,  # extract from form
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found"
        )
    return feedback
