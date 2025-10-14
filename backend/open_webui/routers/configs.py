from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
import logging

from typing import Optional

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.config import get_config, save_config
from open_webui.config import BannerModel


router = APIRouter()
log = logging.getLogger(__name__)


############################
# Chat Lifetime Configuration
############################


class ChatLifetimeConfigForm(BaseModel):
    enabled: bool
    days: int
    preserve_pinned: bool
    preserve_archived: bool


@router.get("/chat-lifetime", response_model=ChatLifetimeConfigForm)
async def get_chat_lifetime_config(request: Request, user=Depends(get_admin_user)):
    return {
        "enabled": request.app.state.config.CHAT_LIFETIME_ENABLED,
        "days": request.app.state.config.CHAT_LIFETIME_DAYS,
        "preserve_pinned": request.app.state.config.CHAT_CLEANUP_PRESERVE_PINNED,
        "preserve_archived": request.app.state.config.CHAT_CLEANUP_PRESERVE_ARCHIVED,
    }


@router.post("/chat-lifetime", response_model=ChatLifetimeConfigForm)
async def update_chat_lifetime_config(
    request: Request, form_data: ChatLifetimeConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.CHAT_LIFETIME_ENABLED = form_data.enabled
    request.app.state.config.CHAT_LIFETIME_DAYS = form_data.days
    request.app.state.config.CHAT_CLEANUP_PRESERVE_PINNED = form_data.preserve_pinned
    request.app.state.config.CHAT_CLEANUP_PRESERVE_ARCHIVED = (
        form_data.preserve_archived
    )

    # Update the scheduler to reflect the new configuration
    try:
        from open_webui.scheduler import update_cleanup_schedule

        update_cleanup_schedule()
    except Exception as e:
        log.error(f"Failed to update chat cleanup schedule: {e}")

    return {
        "enabled": request.app.state.config.CHAT_LIFETIME_ENABLED,
        "days": request.app.state.config.CHAT_LIFETIME_DAYS,
        "preserve_pinned": request.app.state.config.CHAT_CLEANUP_PRESERVE_PINNED,
        "preserve_archived": request.app.state.config.CHAT_CLEANUP_PRESERVE_ARCHIVED,
    }


@router.get("/chat-lifetime/schedule")
async def get_chat_lifetime_schedule(request: Request, user=Depends(get_admin_user)):
    """Get information about the current chat lifetime cleanup schedule"""
    try:
        from open_webui.scheduler import get_schedule_info

        return get_schedule_info()
    except Exception as e:
        log.error(f"Failed to get schedule info: {e}")
        return {"enabled": False, "status": "error", "next_run": None, "error": str(e)}


############################
# ImportConfig
############################


class ImportConfigForm(BaseModel):
    config: dict


@router.post("/import", response_model=dict)
async def import_config(form_data: ImportConfigForm, user=Depends(get_admin_user)):
    save_config(form_data.config)
    return get_config()


############################
# ExportConfig
############################


@router.get("/export", response_model=dict)
async def export_config(user=Depends(get_admin_user)):
    return get_config()


############################
# SetDefaultModels
############################
class ModelsConfigForm(BaseModel):
    DEFAULT_MODELS: Optional[str]
    MODEL_ORDER_LIST: Optional[list[str]]


@router.get("/models", response_model=ModelsConfigForm)
async def get_models_config(request: Request, user=Depends(get_admin_user)):
    return {
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }


@router.post("/models", response_model=ModelsConfigForm)
async def set_models_config(
    request: Request, form_data: ModelsConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.DEFAULT_MODELS = form_data.DEFAULT_MODELS
    request.app.state.config.MODEL_ORDER_LIST = form_data.MODEL_ORDER_LIST
    return {
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }


class PromptSuggestion(BaseModel):
    title: list[str]
    content: str
    lang: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: list[PromptSuggestion]


@router.post("/suggestions", response_model=list[PromptSuggestion])
async def set_default_suggestions(
    request: Request,
    form_data: SetDefaultSuggestionsForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS = data["suggestions"]
    return request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS


############################
# SetBanners
############################


class SetBannersForm(BaseModel):
    banners: list[BannerModel]


@router.post("/banners", response_model=list[BannerModel])
async def set_banners(
    request: Request,
    form_data: SetBannersForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.BANNERS = data["banners"]
    return request.app.state.config.BANNERS


@router.get("/banners", response_model=list[BannerModel])
async def get_banners(
    request: Request,
    user=Depends(get_verified_user),
):
    return request.app.state.config.BANNERS
