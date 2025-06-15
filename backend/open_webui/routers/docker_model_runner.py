from contextlib import contextmanager
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from open_webui.models.users import UserModel
from open_webui.routers import openai
from open_webui.routers.openai import ConnectionVerificationForm
from open_webui.utils.auth import get_admin_user, get_verified_user

router = APIRouter()

@contextmanager
def _dmr_context(request: Request):
    orig_urls = request.app.state.config.OPENAI_API_BASE_URLS
    orig_keys = request.app.state.config.OPENAI_API_KEYS
    orig_configs = request.app.state.config.OPENAI_API_CONFIGS
    orig_models = request.app.state.OPENAI_MODELS
    request.app.state.config.OPENAI_API_BASE_URLS = request.app.state.config.DMR_BASE_URLS
    request.app.state.config.OPENAI_API_KEYS = request.app.state.config.DMR_API_KEYS
    request.app.state.config.OPENAI_API_CONFIGS = request.app.state.config.DMR_API_CONFIGS
    request.app.state.OPENAI_MODELS = request.app.state.DMR_MODELS
    try:
        yield
    finally:
        request.app.state.config.OPENAI_API_BASE_URLS = orig_urls
        request.app.state.config.OPENAI_API_KEYS = orig_keys
        request.app.state.config.OPENAI_API_CONFIGS = orig_configs
        request.app.state.OPENAI_MODELS = orig_models


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_DMR_API": request.app.state.config.ENABLE_DMR_API,
        "DMR_BASE_URLS": request.app.state.config.DMR_BASE_URLS,
        "DMR_API_KEYS": request.app.state.config.DMR_API_KEYS,
        "DMR_API_CONFIGS": request.app.state.config.DMR_API_CONFIGS,
    }


class DMRConfigForm(BaseModel):
    ENABLE_DMR_API: Optional[bool] = None
    DMR_BASE_URLS: list[str]
    DMR_API_KEYS: list[str] = []
    DMR_API_CONFIGS: dict = {}


@router.post("/config/update")
async def update_config(request: Request, form_data: DMRConfigForm, user=Depends(get_admin_user)):
    request.app.state.config.ENABLE_DMR_API = form_data.ENABLE_DMR_API
    request.app.state.config.DMR_BASE_URLS = form_data.DMR_BASE_URLS
    request.app.state.config.DMR_API_KEYS = form_data.DMR_API_KEYS
    request.app.state.config.DMR_API_CONFIGS = form_data.DMR_API_CONFIGS

    if len(request.app.state.config.DMR_API_KEYS) != len(request.app.state.config.DMR_BASE_URLS):
        if len(request.app.state.config.DMR_API_KEYS) > len(request.app.state.config.DMR_BASE_URLS):
            request.app.state.config.DMR_API_KEYS = request.app.state.config.DMR_API_KEYS[: len(request.app.state.config.DMR_BASE_URLS)]
        else:
            request.app.state.config.DMR_API_KEYS += [""] * (
                len(request.app.state.config.DMR_BASE_URLS) - len(request.app.state.config.DMR_API_KEYS)
            )

    keys = list(map(str, range(len(request.app.state.config.DMR_BASE_URLS))))
    request.app.state.config.DMR_API_CONFIGS = {
        k: v for k, v in request.app.state.config.DMR_API_CONFIGS.items() if k in keys
    }

    return {
        "ENABLE_DMR_API": request.app.state.config.ENABLE_DMR_API,
        "DMR_BASE_URLS": request.app.state.config.DMR_BASE_URLS,
        "DMR_API_KEYS": request.app.state.config.DMR_API_KEYS,
        "DMR_API_CONFIGS": request.app.state.config.DMR_API_CONFIGS,
    }


@router.post("/verify")
async def verify_connection(form_data: ConnectionVerificationForm, user=Depends(get_admin_user)):
    return await openai.verify_connection(form_data, user)


@router.get("/models")
@router.get("/models/{url_idx}")
async def get_models(request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)):
    with _dmr_context(request):
        return await openai.get_models(request, url_idx=url_idx, user=user)


@router.post("/chat/completions")
async def generate_chat_completion(request: Request, form_data: dict, user=Depends(get_verified_user)):
    with _dmr_context(request):
        return await openai.generate_chat_completion(request, form_data, user=user)


@router.post("/completions")
async def completions(request: Request, form_data: dict, user=Depends(get_verified_user)):
    with _dmr_context(request):
        return await openai.completions(request, form_data, user=user)


@router.post("/embeddings")
async def embeddings(request: Request, form_data: dict, user=Depends(get_verified_user)):
    with _dmr_context(request):
        return await openai.embeddings(request, form_data, user=user)


async def get_all_models(request: Request, user: UserModel = None):
    with _dmr_context(request):
        return await openai.get_all_models.__wrapped__(request, user)
