from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from open_webui.models.prompts import (
    PromptForm,
    PromptUserResponse,
    PromptAccessResponse,
    PromptModel,
    Prompts,
)
from open_webui.models.prompt_history import (
    PromptHistories,
    PromptHistoryModel,
    PromptHistoryResponse,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session
from pydantic import BaseModel


class PromptVersionUpdateForm(BaseModel):
    version_id: str

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
    prompt = Prompts.get_prompt_by_command(command, db=db)

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

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ERROR_MESSAGES.NOT_FOUND,
    )


############################
# GetPromptById
############################


@router.get("/id/{prompt_id}", response_model=Optional[PromptAccessResponse])
async def get_prompt_by_id(
    prompt_id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)

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

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
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
    prompt = Prompts.get_prompt_by_command(command, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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

    # Use the command from the found prompt
    updated_prompt = Prompts.update_prompt_by_command(
        prompt.command, form_data, user.id, db=db
    )
    if updated_prompt:
        return updated_prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post("/command/{command}/set/version", response_model=Optional[PromptModel])
async def set_prompt_version(
    command: str,
    form_data: PromptVersionUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    prompt = Prompts.get_prompt_by_command(command, db=db)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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

    updated_prompt = Prompts.update_prompt_version(
        prompt.command, form_data.version_id, db=db
    )
    if updated_prompt:
        return updated_prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# DeletePromptByCommand
############################


@router.delete("/command/{command}/delete", response_model=bool)
async def delete_prompt_by_command(
    command: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    prompt = Prompts.get_prompt_by_command(command, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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

    result = Prompts.delete_prompt_by_command(prompt.command, db=db)
    return result


############################
# Prompt History Endpoints
############################


@router.get("/command/{command}/history", response_model=list[PromptHistoryResponse])
async def get_prompt_history(
    command: str,
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get version history for a prompt."""
    prompt = Prompts.get_prompt_by_command(command, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or prompt.user_id == user.id
        or has_access(user.id, "read", prompt.access_control, db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    history = PromptHistories.get_history_by_prompt_id(
        prompt.id, limit=limit, offset=offset, db=db
    )
    return history


@router.get(
    "/command/{command}/history/{history_id}", response_model=PromptHistoryModel
)
async def get_prompt_history_entry(
    command: str,
    history_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get a specific version from history."""
    prompt = Prompts.get_prompt_by_command(command, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or prompt.user_id == user.id
        or has_access(user.id, "read", prompt.access_control, db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    history_entry = PromptHistories.get_history_entry_by_id(history_id, db=db)
    if not history_entry or history_entry.prompt_id != prompt.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    return history_entry


@router.delete(
    "/command/{command}/history/{history_id}", response_model=bool
)
async def delete_prompt_history_entry(
    command: str,
    history_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Delete a history entry. Cannot delete the active production version."""
    prompt = Prompts.get_prompt_by_command(command, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        user.role == "admin"
        or prompt.user_id == user.id
        or has_access(user.id, "write", prompt.access_control, db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Cannot delete active production version
    if prompt.version_id == history_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the active production version",
        )

    success = PromptHistories.delete_history_entry(history_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    return success


@router.get("/command/{command}/history/diff")
async def get_prompt_diff(
    command: str,
    from_id: str,
    to_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get diff between two versions."""
    prompt = Prompts.get_prompt_by_command(command, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or prompt.user_id == user.id
        or has_access(user.id, "read", prompt.access_control, db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    diff = PromptHistories.compute_diff(from_id, to_id, db=db)
    if not diff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both history entries not found",
        )

    return diff
