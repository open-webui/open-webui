from fastapi import Response, Request
from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union

from fastapi import APIRouter
from pydantic import BaseModel
import time
import uuid

from config import BannerModel

from apps.webui.models.users import Users

from utils.utils import (
    get_password_hash,
    get_current_user,
    get_admin_user,
    create_token,
)
from utils.misc import get_gravatar_url, validate_email_format
from constants import ERROR_MESSAGES

router = APIRouter()


class SetDefaultModelsForm(BaseModel):
    models: str


class PromptSuggestion(BaseModel):
    title: List[str]
    content: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: List[PromptSuggestion]


############################
# SetDefaultModels
############################


@router.post("/default/models", response_model=str)
async def set_global_default_models(
    request: Request, form_data: SetDefaultModelsForm, user=Depends(get_admin_user)
):
    request.app.state.config.DEFAULT_MODELS = form_data.models
    return request.app.state.config.DEFAULT_MODELS


@router.post("/default/suggestions", response_model=List[PromptSuggestion])
async def set_global_default_suggestions(
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
    banners: List[BannerModel]


@router.post("/banners", response_model=List[BannerModel])
async def set_banners(
    request: Request,
    form_data: SetBannersForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.BANNERS = data["banners"]
    return request.app.state.config.BANNERS


@router.get("/banners", response_model=List[BannerModel])
async def get_banners(
    request: Request,
    user=Depends(get_current_user),
):
    return request.app.state.config.BANNERS
