from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from open_webui.models.users import Users, UserModel
from open_webui.models.feedbacks import (
    FeedbackModel,
    FeedbackResponse,
    FeedbackForm,
    FeedbackUserResponse,
    FeedbackListResponse,
    Feedbacks,
    RatingData,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user

router = APIRouter()


############################
# MessageFeedbackForm
############################


class MessageFeedbackForm(BaseModel):
    rating: Optional[str] = None  # "good", "bad", or None
    chat_id: str
    message_id: str


############################
# GetConfig
############################


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_EVALUATION_ARENA_MODELS": request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS,
        "EVALUATION_ARENA_MODELS": request.app.state.config.EVALUATION_ARENA_MODELS,
    }


############################
# UpdateConfig
############################


class UpdateConfigForm(BaseModel):
    ENABLE_EVALUATION_ARENA_MODELS: Optional[bool] = None
    EVALUATION_ARENA_MODELS: Optional[list[dict]] = None


@router.post("/config")
async def update_config(
    request: Request,
    form_data: UpdateConfigForm,
    user=Depends(get_admin_user),
):
    config = request.app.state.config
    if form_data.ENABLE_EVALUATION_ARENA_MODELS is not None:
        config.ENABLE_EVALUATION_ARENA_MODELS = form_data.ENABLE_EVALUATION_ARENA_MODELS
    if form_data.EVALUATION_ARENA_MODELS is not None:
        config.EVALUATION_ARENA_MODELS = form_data.EVALUATION_ARENA_MODELS
    return {
        "ENABLE_EVALUATION_ARENA_MODELS": config.ENABLE_EVALUATION_ARENA_MODELS,
        "EVALUATION_ARENA_MODELS": config.EVALUATION_ARENA_MODELS,
    }


@router.get("/feedbacks/all", response_model=list[FeedbackResponse])
async def get_all_feedbacks(user=Depends(get_admin_user)):
    feedbacks = Feedbacks.get_all_feedbacks()
    return feedbacks


@router.delete("/feedbacks/all")
async def delete_all_feedbacks(user=Depends(get_admin_user)):
    success = Feedbacks.delete_all_feedbacks()
    return success


@router.get("/feedbacks/all/export", response_model=list[FeedbackModel])
async def get_all_feedbacks(user=Depends(get_admin_user)):
    feedbacks = Feedbacks.get_all_feedbacks()
    return feedbacks


@router.get("/feedbacks/user", response_model=list[FeedbackUserResponse])
async def get_feedbacks(user=Depends(get_verified_user)):
    feedbacks = Feedbacks.get_feedbacks_by_user_id(user.id)
    return feedbacks


@router.delete("/feedbacks", response_model=bool)
async def delete_feedbacks(user=Depends(get_verified_user)):
    success = Feedbacks.delete_feedbacks_by_user_id(user.id)
    return success


PAGE_ITEM_COUNT = 30


@router.get("/feedbacks/list", response_model=FeedbackListResponse)
async def get_feedbacks(
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_admin_user),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    result = Feedbacks.get_feedback_items(filter=filter, skip=skip, limit=limit)
    return result


@router.post("/feedback", response_model=FeedbackModel)
async def create_feedback(
    request: Request,
    form_data: FeedbackForm,
    user=Depends(get_verified_user),
):
    feedback = Feedbacks.insert_new_feedback(user_id=user.id, form_data=form_data)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return feedback


@router.get("/feedback/{id}", response_model=FeedbackModel)
async def get_feedback_by_id(id: str, user=Depends(get_verified_user)):
    if user.role == "admin":
        feedback = Feedbacks.get_feedback_by_id(id=id)
    else:
        feedback = Feedbacks.get_feedback_by_id_and_user_id(id=id, user_id=user.id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return feedback


@router.post("/feedback/{id}", response_model=FeedbackModel)
async def update_feedback_by_id(
    id: str, form_data: FeedbackForm, user=Depends(get_verified_user)
):
    if user.role == "admin":
        feedback = Feedbacks.update_feedback_by_id(id=id, form_data=form_data)
    else:
        feedback = Feedbacks.update_feedback_by_id_and_user_id(
            id=id, user_id=user.id, form_data=form_data
        )

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return feedback


@router.delete("/feedback/{id}")
async def delete_feedback_by_id(id: str, user=Depends(get_verified_user)):
    if user.role == "admin":
        success = Feedbacks.delete_feedback_by_id(id=id)
    else:
        success = Feedbacks.delete_feedback_by_id_and_user_id(id=id, user_id=user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return success


############################
# Message Feedback APIs
############################


@router.post("/feedback/message", response_model=Optional[FeedbackModel])
async def upsert_message_feedback(
    form_data: MessageFeedbackForm,
    user=Depends(get_verified_user),
):
    """메시지 피드백 생성/업데이트/삭제"""
    from open_webui.models.chats import Chats

    # 권한 확인: 사용자가 해당 chat의 소유자인지 확인
    chat = Chats.get_chat_by_id_and_user_id(form_data.chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # 기존 피드백 조회
    existing = Feedbacks.get_feedback_by_chat_id_and_message_id(
        form_data.chat_id, form_data.message_id
    )

    # rating이 None이면 피드백 삭제
    if form_data.rating is None:
        if existing:
            success = Feedbacks.delete_feedback_by_id_and_user_id(
                existing.id, user.id
            )
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        return None

    # 피드백 데이터 생성
    feedback_form = FeedbackForm(
        type="message_feedback",
        data=RatingData(rating=form_data.rating),
        meta={"chat_id": form_data.chat_id, "message_id": form_data.message_id},
    )

    if existing:
        # 업데이트
        feedback = Feedbacks.update_feedback_by_id_and_user_id(
            existing.id, user.id, feedback_form
        )
    else:
        # 생성
        feedback = Feedbacks.insert_new_feedback(user.id, feedback_form)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return feedback


@router.get(
    "/feedback/message/{chat_id}/{message_id}",
    response_model=Optional[FeedbackModel],
)
async def get_message_feedback(
    chat_id: str,
    message_id: str,
    user=Depends(get_verified_user),
):
    """특정 메시지의 피드백 조회"""
    from open_webui.models.chats import Chats

    # 권한 확인
    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    feedback = Feedbacks.get_feedback_by_chat_id_and_message_id(chat_id, message_id)
    return feedback


@router.get("/feedback/chat/{chat_id}")
async def get_chat_feedbacks(
    chat_id: str,
    user=Depends(get_verified_user),
):
    """특정 chat의 모든 메시지 피드백 조회"""
    from open_webui.models.chats import Chats

    # 권한 확인
    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    feedback_map = Feedbacks.get_feedbacks_by_chat_id(chat_id)
    return feedback_map
