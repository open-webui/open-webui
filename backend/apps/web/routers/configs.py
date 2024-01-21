from fastapi import Response, Request
from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union
import json
import os
import base64

from fastapi import APIRouter
from pydantic import BaseModel
import time
import uuid

from apps.web.models.users import Users

from utils.utils import get_password_hash, get_current_user, create_token
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
    request: Request, form_data: SetDefaultModelsForm, user=Depends(get_current_user)
):
    if user.role == "admin":
        request.app.state.DEFAULT_MODELS = form_data.models
        return request.app.state.DEFAULT_MODELS
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


@router.post("/default/suggestions", response_model=List[PromptSuggestion])
async def set_global_default_suggestions(
    request: Request,
    form_data: SetDefaultSuggestionsForm,
    user=Depends(get_current_user),
):
    if user.role == "admin":
        data = form_data.model_dump()
        request.app.state.DEFAULT_PROMPT_SUGGESTIONS = data["suggestions"]
        return request.app.state.DEFAULT_PROMPT_SUGGESTIONS
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
############################
# GetUIConfig
############################


@router.get("/ui", response_model=list)
async def get_ui_config():
    config_dir = './data/config/ui'
    if not os.path.isdir(config_dir):
        return []

    config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
    configs = []

    for f in config_files:
        with open(os.path.join(config_dir, f), 'r') as file:
            config = json.load(file)
            org_logo = config['orgLogo']
            org_logo = clean_logo(org_logo, config_dir)
            configs.append(config)

    return configs


def clean_logo(logo, config_dir):
    for theme in ['light', 'dark']:
        if not logo[theme].startswith(('http', 'data:image')):
            image_path = os.path.join(config_dir, logo[theme])
            if os.path.isfile(image_path):
                logo[theme] = convert_image_to_base64(image_path)
            else:
                logo[theme] = None
    return logo


def convert_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        encoded_image = "data:image/png;base64," + encoded_image
    return encoded_image
