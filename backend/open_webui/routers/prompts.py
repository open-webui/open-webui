from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from open_webui.models.prompts import (
    PromptForm,
    PromptUserResponse,
    PromptModel,
    Prompts,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.utils.task import validate_prompt_references

router = APIRouter()


def _prepare_validation(
    form_data: PromptForm, user
) -> tuple[list[dict], Optional[list[dict]]]:
    """
    Prepare prompt data for validation. Centralizes the logic for getting prompts
    and simulating post-save state.

    Returns: (all_prompts_dict, accessible_prompts_dict)
    """
    all_prompts = Prompts.get_prompts()
    accessible_prompts = (
        None
        if user.role == "admin"
        else Prompts.get_prompts_by_user_id(user.id, "read")
    )

    # Convert to dict format
    all_prompts_dict = [
        {"command": p.command, "content": p.content} for p in all_prompts
    ]

    # Update map with NEW content to simulate post-save state
    validated_command = form_data.command.lstrip("/")
    found = False
    for p in all_prompts_dict:
        if p["command"].lstrip("/") == validated_command:
            p["content"] = form_data.content
            found = True
            break
    if not found:
        all_prompts_dict.append(
            {"command": form_data.command, "content": form_data.content}
        )

    accessible_prompts_dict = (
        None
        if accessible_prompts is None
        else [{"command": p.command, "content": p.content} for p in accessible_prompts]
    )

    return all_prompts_dict, accessible_prompts_dict


############################
# ValidatePrompt
############################


@router.post("/validate")
async def validate_prompt(form_data: PromptForm, user=Depends(get_verified_user)):
    """
    Validate a prompt for circular dependencies, non-existent references, etc.
    Returns validation errors and warnings without saving.
    """
    all_prompts_dict, accessible_prompts_dict = _prepare_validation(form_data, user)

    validation = validate_prompt_references(
        form_data.command.lstrip("/"),
        form_data.content,
        all_prompts_dict,
        accessible_prompts_dict,
    )

    return validation


############################
# GetPrompts
############################


@router.get("/", response_model=list[PromptModel])
async def get_prompts(user=Depends(get_verified_user)):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        prompts = Prompts.get_prompts()
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "read")

    return prompts


@router.get("/list", response_model=list[PromptUserResponse])
async def get_prompt_list(user=Depends(get_verified_user)):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        prompts = Prompts.get_prompts()
    else:
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
        all_prompts_dict, accessible_prompts_dict = _prepare_validation(form_data, user)

        validation = validate_prompt_references(
            form_data.command.lstrip("/"),
            form_data.content,
            all_prompts_dict,
            accessible_prompts_dict,
        )

        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(validation["errors"]),
            )

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

    all_prompts_dict, accessible_prompts_dict = _prepare_validation(form_data, user)

    validation = validate_prompt_references(
        form_data.command.lstrip("/"),
        form_data.content,
        all_prompts_dict,
        accessible_prompts_dict,
    )

    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(validation["errors"]),
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
