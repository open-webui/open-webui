from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from typing import Optional

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.config import get_config, save_config
from open_webui.config import BannerModel


router = APIRouter()



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
    # Get company_id from the authenticated user
    company_id = user.company_id
    
    # Update app state config
    request.app.state.config.DEFAULT_MODELS = form_data.DEFAULT_MODELS
    request.app.state.config.MODEL_ORDER_LIST = form_data.MODEL_ORDER_LIST
    
    # Get current config and update it
    current_config = get_config(company_id)
    if "models" not in current_config:
        current_config["models"] = {}
    current_config["models"]["DEFAULT_MODELS"] = form_data.DEFAULT_MODELS
    current_config["models"]["MODEL_ORDER_LIST"] = form_data.MODEL_ORDER_LIST
    
    # Save the updated config
    save_config(current_config, company_id)
    
    return {
        "DEFAULT_MODELS": form_data.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": form_data.MODEL_ORDER_LIST,
    }


class PromptSuggestion(BaseModel):
    title: list[str]
    content: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: list[PromptSuggestion]


@router.post("/suggestions", response_model=list[PromptSuggestion])
async def set_default_suggestions(
    request: Request, form_data: SetDefaultSuggestionsForm, user=Depends(get_admin_user)
):
    # Get company_id from the authenticated user
    company_id = user.company_id
    
    data = form_data.model_dump()
    request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS = data["suggestions"]
    
    # Get current config and update it
    current_config = get_config(company_id)
    if "ui" not in current_config:
        current_config["ui"] = {}
    current_config["ui"]["prompt_suggestions"] = data["suggestions"]
    
    # Save the updated config
    save_config(current_config, company_id)
    
    return request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS


############################
# SetBanners
############################


class SetBannersForm(BaseModel):
    banners: list[BannerModel]


@router.post("/banners", response_model=list[BannerModel])
async def set_banners(
    request: Request, form_data: SetBannersForm, user=Depends(get_admin_user)
):
    # Get company_id from the authenticated user
    company_id = user.company_id
    
    data = form_data.model_dump()
    request.app.state.config.BANNERS = data["banners"]
    
    # Get current config and update it
    current_config = get_config(company_id)
    if "banners" not in current_config:
        current_config["banners"] = []
    current_config["banners"] = data["banners"]
    
    # Save the updated config
    save_config(current_config, company_id)
    
    return request.app.state.config.BANNERS


@router.get("/banners", response_model=list[BannerModel])
async def get_banners(
    request: Request,
    user=Depends(get_verified_user),
):
    return request.app.state.config.BANNERS
