from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union, Optional

from fastapi import APIRouter
from pydantic import BaseModel
import json

from apps.webui.internal.db import get_db
from apps.webui.models.prompts import Prompts, PromptForm, PromptModel

from utils.utils import get_current_user, get_admin_user
from constants import ERROR_MESSAGES

router = APIRouter()

############################
# GetPrompts
############################


@router.get("/", response_model=List[PromptModel])
async def get_prompts(user=Depends(get_current_user), db=Depends(get_db)):
    return Prompts.get_prompts(db)


############################
# CreateNewPrompt
############################


@router.post("/create", response_model=Optional[PromptModel])
async def create_new_prompt(
    form_data: PromptForm, user=Depends(get_admin_user), db=Depends(get_db)
):
    prompt = Prompts.get_prompt_by_command(db, form_data.command)
    if prompt == None:
        prompt = Prompts.insert_new_prompt(db, user.id, form_data)

        if prompt:
            return prompt
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.COMMAND_TAKEN,
    )


############################
# GetPromptByCommand
############################


@router.get("/command/{command}", response_model=Optional[PromptModel])
async def get_prompt_by_command(
    command: str, user=Depends(get_current_user), db=Depends(get_db)
):
    prompt = Prompts.get_prompt_by_command(db, f"/{command}")

    if prompt:
        return prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdatePromptByCommand
############################


@router.post("/command/{command}/update", response_model=Optional[PromptModel])
async def update_prompt_by_command(
    command: str,
    form_data: PromptForm,
    user=Depends(get_admin_user),
    db=Depends(get_db),
):
    prompt = Prompts.update_prompt_by_command(db, f"/{command}", form_data)
    if prompt:
        return prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# DeletePromptByCommand
############################


@router.delete("/command/{command}/delete", response_model=bool)
async def delete_prompt_by_command(
    command: str, user=Depends(get_admin_user), db=Depends(get_db)
):
    result = Prompts.delete_prompt_by_command(db, f"/{command}")
    return result
