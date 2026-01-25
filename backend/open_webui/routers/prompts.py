from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from open_webui.models.prompts import (
    PromptForm,
    PromptUserResponse,
    PromptAccessResponse,
    PromptModel,
    Prompts,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

router = APIRouter()

############################
# GetPrompts
############################


@router.get("/", response_model=list[PromptModel])
async def get_prompts(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        prompts = Prompts.get_prompts(db=db)
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "read", db=db)

    return prompts


@router.get("/list", response_model=list[PromptAccessResponse])
async def get_prompt_list(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        prompts = Prompts.get_prompts(db=db)
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "read", db=db)

    return [
        PromptAccessResponse(
            **prompt.model_dump(),
            write_access=(
                (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                or user.id == prompt.user_id
                or has_access(user.id, "write", prompt.access_control, db=db)
            ),
        )
        for prompt in prompts
    ]


############################
# CreateNewPrompt
############################


@router.post("/create", response_model=Optional[PromptModel])
async def create_new_prompt(
    request: Request,
    form_data: PromptForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not (
        has_permission(
            user.id,
            "workspace.prompts",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
        or has_permission(
            user.id,
            "workspace.prompts_import",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    prompt = Prompts.get_prompt_by_command(form_data.command, db=db)
    if prompt is None:
        prompt = Prompts.insert_new_prompt(user.id, form_data, db=db)

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


@router.get("/command/{command}", response_model=Optional[PromptAccessResponse])
async def get_prompt_by_command(
    command: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    prompt = Prompts.get_prompt_by_command(f"/{command}", db=db)

    if prompt:
        if (
            user.role == "admin"
            or prompt.user_id == user.id
            or has_access(user.id, "read", prompt.access_control, db=db)
        ):
            return PromptAccessResponse(
                **prompt.model_dump(),
                write_access=(
                    (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                    or user.id == prompt.user_id
                    or has_access(user.id, "write", prompt.access_control, db=db)
                ),
            )
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
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    prompt = Prompts.get_prompt_by_command(f"/{command}", db=db)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Is the user the original creator, in a group with write access, or an admin
    if (
        prompt.user_id != user.id
        and not has_access(user.id, "write", prompt.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    prompt = Prompts.update_prompt_by_command(f"/{command}", form_data, db=db)
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
    command: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    prompt = Prompts.get_prompt_by_command(f"/{command}", db=db)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        prompt.user_id != user.id
        and not has_access(user.id, "write", prompt.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Prompts.delete_prompt_by_command(f"/{command}", db=db)
    return result
