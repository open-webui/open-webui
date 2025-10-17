import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.models.exit_quiz import ExitQuizzes, ExitQuizModel, ExitQuizForm
from open_webui.models.users import UserModel


log = logging.getLogger(__name__)

router = APIRouter()


class ExitQuizResponse(BaseModel):
    id: str
    user_id: str
    child_id: str
    answers: dict
    score: Optional[dict] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int


@router.post("/exit-quiz", response_model=ExitQuizResponse)
async def create_exit_quiz_response(
    form_data: ExitQuizForm,
    current_user: UserModel = Depends(get_verified_user),
):
    try:
        res = ExitQuizzes.insert_new_response(form_data, current_user.id)
        if not res:
            raise HTTPException(status_code=500, detail="Failed to create exit quiz response")
        return ExitQuizResponse(**res.model_dump())
    except Exception as e:
        log.error(f"Error creating exit quiz response: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/exit-quiz", response_model=List[ExitQuizResponse])
async def list_exit_quiz_responses(
    child_id: Optional[str] = None,
    current_user: UserModel = Depends(get_verified_user),
):
    try:
        items = ExitQuizzes.get_responses_by_user(current_user.id, child_id=child_id)
        return [ExitQuizResponse(**i.model_dump()) for i in items]
    except Exception as e:
        log.error(f"Error listing exit quiz responses: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/exit-quiz/{id}", response_model=ExitQuizResponse)
async def get_exit_quiz_response(
    id: str,
    current_user: UserModel = Depends(get_verified_user),
):
    try:
        res = ExitQuizzes.get_response_by_id(id, current_user.id)
        if not res:
            raise HTTPException(status_code=404, detail="Exit quiz response not found")
        return ExitQuizResponse(**res.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching exit quiz response: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/exit-quiz/{id}", response_model=ExitQuizResponse)
async def update_exit_quiz_response(
    id: str,
    form_data: ExitQuizForm,
    current_user: UserModel = Depends(get_verified_user),
):
    try:
        res = ExitQuizzes.update_response_by_id(id, current_user.id, form_data)
        if not res:
            raise HTTPException(status_code=404, detail="Exit quiz response not found")
        return ExitQuizResponse(**res.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating exit quiz response: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/exit-quiz/{id}")
async def delete_exit_quiz_response(
    id: str,
    current_user: UserModel = Depends(get_verified_user),
):
    try:
        ok = ExitQuizzes.delete_response(id, current_user.id)
        if not ok:
            raise HTTPException(status_code=404, detail="Exit quiz response not found")
        return {"message": "Exit quiz response deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting exit quiz response: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


