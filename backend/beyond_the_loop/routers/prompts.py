from typing import Optional

from beyond_the_loop.models.prompts import (
    PromptForm,
    PromptUserResponse,
    PromptModel,
    Prompts, PromptBookmarkForm,
)
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, status, Request
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_access, has_permission

router = APIRouter()

############################
# GetPrompts
############################


@router.get("/", response_model=list[PromptModel])
async def get_prompts(user=Depends(get_verified_user)):
    return Prompts.get_prompts_by_user_and_company(user.id, user.company_id, "read")


@router.get("/list", response_model=list[PromptUserResponse])
async def get_prompt_list(user=Depends(get_verified_user)):
    prompts = Prompts.get_prompts_by_user_and_company(user.id, user.company_id, "read")
    sorted_prompts = sorted(prompts, key=lambda m: not m.bookmarked_by_user)
    return sorted_prompts


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

    prompt = Prompts.get_prompt_by_command_and_company(form_data.command, user.company_id)
    if prompt is None:
        prompt = Prompts.insert_new_prompt(user.id, user.company_id, form_data)

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
    prompt = Prompts.get_prompt_by_command_and_company(f"/{command}", user.company_id)

    if prompt:
        if (
            prompt.user_id == user.id
            or has_access(user.id, "read", prompt.access_control)
        ):
            return prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

# @router.post("/command/{command}/bookmark/update", response_model=Optional[PromptModel])
# async def get_prompt_by_command(command: str, form_data: PromptBookmarkForm, user=Depends(get_verified_user)):
#     prompt = Prompts.get_prompt_by_command_and_company(f"/{command}", user.company_id)

#     if prompt:
#         if (
#             prompt.user_id == user.id
#             or has_access(user.id, "read", prompt.access_control)
#         ):
#             prompt.bookmarked = form_data.bookmarked
#             Prompts.update_prompt_by_command_and_company(f"/{command}", prompt, user.company_id)
#             return prompt
#     else:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=ERROR_MESSAGES.NOT_FOUND,
#         )
@router.post("/command/{command}/bookmark/update")
async def update_prompt_bookmark(command: str, user=Depends(get_verified_user)):
    prompt = Prompts.get_prompt_by_command_and_company_or_system(f"/{command}", user.company_id)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    bookmarked =Prompts.toggle_bookmark(prompt.command, user.id)
    return {"prompt_command": prompt.command, "bookmarked_by_user": bookmarked}

############################
# UpdatePromptByCommand
############################


@router.post("/command/{command}/update", response_model=Optional[PromptModel])
async def update_prompt_by_command(
    command: str,
    form_data: PromptForm,
    user=Depends(get_verified_user),
):
    prompt = Prompts.get_prompt_by_command_and_company(f"/{command}", user.company_id)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if prompt.prebuilt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
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

    prompt = Prompts.update_prompt_by_command_and_company(f"/{command}", form_data, user.company_id)
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
    prompt = Prompts.get_prompt_by_command_and_company(f"/{command}", user.company_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if prompt.prebuilt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
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

    result = Prompts.delete_prompt_by_command_and_company(f"/{command}", user.company_id)
    return result
