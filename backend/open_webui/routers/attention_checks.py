import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.models.attention_checks import AttentionChecks, AttentionCheckQuestionModel, AttentionCheckResponseModel
from open_webui.models.users import UserModel, Users
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()


class PostResponseForm(BaseModel):
    question_id: str
    response: str


@router.get("/attention-checks/questions", response_model=list[AttentionCheckQuestionModel])
async def list_questions(user: UserModel = Depends(get_verified_user)):
    try:
        AttentionChecks.seed_default_questions()
        return AttentionChecks.list_questions()
    except Exception as e:
        log.error(f"List attention questions failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/attention-checks", response_model=AttentionCheckResponseModel)
async def post_response(form: PostResponseForm, user: UserModel = Depends(get_verified_user)):
    try:
        session_number = getattr(user, "session_number", None)
        return AttentionChecks.insert_response(user.id, session_number, form.question_id, form.response)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        log.error(f"Insert attention response failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/attention-checks", response_model=list[AttentionCheckResponseModel])
async def list_user_responses(user: UserModel = Depends(get_verified_user)):
    try:
        return AttentionChecks.list_responses_by_user(user.id)
    except Exception as e:
        log.error(f"List attention responses failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


