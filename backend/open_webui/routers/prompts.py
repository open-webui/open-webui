from typing import Optional

from open_webui.models.prompts import (
    PromptForm,
    PromptUserResponse,
    PromptModel,
    Prompts,
)
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission

router = APIRouter()

############################
# GetPrompts
############################


@router.get("/", response_model=list[PromptModel])
async def get_prompts(user=Depends(get_verified_user)):
    """Get all prompts (original behavior)"""
    if user.role == "admin":
        prompts = Prompts.get_prompts()
    else:
        # Non-admin users only see their own prompts
        prompts = Prompts.get_prompts_by_user_id(user.id)

    return prompts


@router.get("/list", response_model=list[PromptUserResponse])
async def get_prompt_list(user=Depends(get_verified_user)):
    """Get all prompts with user info (original behavior)"""
    if user.role == "admin":
        prompts = Prompts.get_prompts()
    else:
        # Non-admin users only see their own prompts
        prompts = Prompts.get_prompts_by_user_id(user.id)

    return prompts


# NEW PAGINATED ENDPOINTS
@router.get("/paginated", response_model=list[PromptModel])
async def get_prompts_paginated(
    user=Depends(get_verified_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
):
    """Get paginated prompts with optional search"""
    if user.role == "admin":
        prompts = Prompts.get_prompts_paginated(page=page, limit=limit, search=search)
    else:
        # Non-admin users only see their own prompts
        prompts = Prompts.get_prompts_by_user_id_paginated(
            user.id, page=page, limit=limit, search=search
        )

    return prompts


@router.get("/list/paginated", response_model=list[PromptUserResponse])
async def get_prompt_list_paginated(
    user=Depends(get_verified_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
):
    """Get paginated prompt list with user info and optional search"""
    if user.role == "admin":
        prompts = Prompts.get_prompts_with_users_paginated(
            page=page, limit=limit, search=search
        )
    else:
        # Non-admin users only see their own prompts
        prompts = Prompts.get_prompts_by_user_id_with_users_paginated(
            user.id, page=page, limit=limit, search=search
        )

    return prompts


@router.get("/count")
async def get_prompts_count(
    user=Depends(get_verified_user),
    search: Optional[str] = Query(None, description="Search query"),
):
    """Get total count of prompts with optional search filter"""
    if user.role == "admin":
        count = Prompts.get_prompts_count(search=search)
    else:
        # Non-admin users only see count of their own prompts
        count = Prompts.get_prompts_count_by_user_id(user.id, search=search)

    return {"count": count}


############################
# CreateNewPrompt
############################


@router.post("/create", response_model=Optional[PromptModel])
async def create_new_prompt(
    request: Request, form_data: PromptForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.prompts", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    prompt = Prompts.get_prompt_by_command(form_data.command)
    if prompt is None:
        prompt = Prompts.insert_new_prompt(user.id, form_data)

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
async def get_prompt_by_command(command: str, user=Depends(get_verified_user)):
    prompt = Prompts.get_prompt_by_command(f"/{command}")

    if prompt:
        if (
            user.role == "admin"
            or prompt.user_id == user.id
            or has_access(user.id, "read", prompt.access_control)
        ):
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
    user=Depends(get_verified_user),
):
    prompt = Prompts.get_prompt_by_command(f"/{command}")
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Is the user the original creator, in a group with write access, or an admin
    if (
        prompt.user_id != user.id
        and not has_access(user.id, "write", prompt.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    prompt = Prompts.update_prompt_by_command(f"/{command}", form_data)
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
async def delete_prompt_by_command(command: str, user=Depends(get_verified_user)):
    prompt = Prompts.get_prompt_by_command(f"/{command}")
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if prompt.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Prompts.delete_prompt_by_command(f"/{command}")
    return result
