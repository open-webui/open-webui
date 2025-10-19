from typing import Optional

from open_webui.models.prompts import (
    PromptForm,
    PromptUserResponse,
    PromptModel,
    Prompts,
)
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, status, Request
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.utils.super_admin import is_super_admin

router = APIRouter()

############################
# GetPrompts
############################


@router.get("/", response_model=list[PromptModel])
async def get_prompts(user=Depends(get_verified_user)):
    # if user.role == "admin":
    #     prompts = Prompts.get_prompts()
    # else:
    prompts = Prompts.get_prompts_by_user_id(user.id, "read")

    return prompts


@router.get("/list", response_model=list[PromptUserResponse])
async def get_prompt_list(user=Depends(get_verified_user)):
    # if user.role == "admin":
    #     prompts = Prompts.get_prompts()
    # else:
    prompts = Prompts.get_prompts_by_user_id(user.id, "write")

    return prompts


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
        creator_user_id = user.id
        if is_super_admin(user):
            assign_to = form_data.model_dump().get('assign_to_email')
            if assign_to:
                from open_webui.models.users import Users
                target_user = Users.get_user_by_email(assign_to)
                if target_user:
                    creator_user_id = target_user.id
        
        prompt = Prompts.insert_new_prompt(creator_user_id, form_data)

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


# @router.get("/command/{command}", response_model=Optional[PromptModel])
# async def get_prompt_by_command(command: str, user=Depends(get_verified_user)):
#     prompt = Prompts.get_prompt_by_command(f"/{command}")

#     if prompt:
#         if (
#             user.role == "admin"
#             or prompt.user_id == user.id
#             or has_access(user.id, "read", prompt.access_control)
#         ):
#             return prompt
#     else:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=ERROR_MESSAGES.NOT_FOUND,
#         )


@router.get("/command/{command}", response_model=Optional[PromptModel])
async def get_prompt_by_command(command: str, user=Depends(get_verified_user)):
    from open_webui.utils.workspace_access import item_assigned_to_user_groups
    
    prompt = Prompts.get_prompt_by_command(f"/{command}")

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if (prompt.user_id == user.id or 
        has_access(user.id, "read", prompt.access_control) or
        item_assigned_to_user_groups(user.id, prompt, "read")):
        return prompt

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
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

    if is_super_admin(user):
        assign_to = form_data.model_dump().get('assign_to_email')
        if assign_to:
            from open_webui.models.users import Users
            target_user = Users.get_user_by_email(assign_to)
            if target_user:
                prompt = Prompts.update_prompt_by_command(f"/{command}", form_data)
                if prompt:
                    from open_webui.internal.db import get_db
                    from open_webui.models.prompts import Prompt
                    with get_db() as db:
                        db.query(Prompt).filter_by(command=f"/{command}").update({"user_id": target_user.id})
                        db.commit()
                    prompt = Prompts.get_prompt_by_command(f"/{command}")
                return prompt

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

    if (
        prompt.user_id != user.id
        and not has_access(user.id, "write", prompt.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Prompts.delete_prompt_by_command(f"/{command}")
    return result
