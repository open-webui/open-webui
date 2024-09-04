from open_webui.config import BannerModel
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from open_webui.utils.utils import get_admin_user, get_verified_user


from open_webui.config import get_config, save_config

router = APIRouter()


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


class SetDefaultModelsForm(BaseModel):
    models: str


class PromptSuggestion(BaseModel):
    title: list[str]
    content: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: list[PromptSuggestion]


############################
# SetDefaultModels
############################


@router.post("/default/models", response_model=str)
async def set_global_default_models(
    request: Request, form_data: SetDefaultModelsForm, user=Depends(get_admin_user)
):
    request.app.state.config.DEFAULT_MODELS = form_data.models
    return request.app.state.config.DEFAULT_MODELS


@router.post("/default/suggestions", response_model=list[PromptSuggestion])
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
