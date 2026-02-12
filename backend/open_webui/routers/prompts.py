from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from open_webui.models.prompts import (
    PromptForm,
    PromptUserResponse,
    PromptAccessResponse,
    PromptAccessListResponse,
    PromptModel,
    Prompts,
)
from open_webui.models.access_grants import AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.prompt_history import (
    PromptHistories,
    PromptHistoryModel,
    PromptHistoryResponse,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session
from pydantic import BaseModel


class PromptVersionUpdateForm(BaseModel):
    version_id: str


class PromptMetadataForm(BaseModel):
    name: str
    command: str
    tags: Optional[list[str]] = None


router = APIRouter()

PAGE_ITEM_COUNT = 30


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


@router.get("/tags", response_model=list[str])
async def get_prompt_tags(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        return Prompts.get_tags(db=db)
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "read", db=db)
        tags = set()
        for prompt in prompts:
            if prompt.tags:
                tags.update(prompt.tags)
        return sorted(list(tags))


@router.get("/list", response_model=PromptAccessListResponse)
async def get_prompt_list(
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    tag: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if view_option:
        filter["view_option"] = view_option
    if tag:
        filter["tag"] = tag
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    if not (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL):
        groups = Groups.get_groups_by_member_id(user.id, db=db)
        if groups:
            filter["group_ids"] = [group.id for group in groups]

        filter["user_id"] = user.id

    result = Prompts.search_prompts(
        user.id, filter=filter, skip=skip, limit=limit, db=db
    )

    return PromptAccessListResponse(
        items=[
            PromptAccessResponse(
                **prompt.model_dump(),
                write_access=(
                    (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                    or user.id == prompt.user_id
                    or AccessGrants.has_access(
                        user_id=user.id,
                        resource_type="prompt",
                        resource_id=prompt.id,
                        permission="write",
                        db=db,
                    )
                ),
            )
            for prompt in result.items
        ],
        total=result.total,
    )


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
            or AccessGrants.has_access(
                user_id=user.id,
                resource_type="prompt",
                resource_id=prompt.id,
                permission="read",
                db=db,
            )
        ):
            return PromptAccessResponse(
                **prompt.model_dump(),
                write_access=(
                    (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                    or user.id == prompt.user_id
                    or AccessGrants.has_access(
                        user_id=user.id,
                        resource_type="prompt",
                        resource_id=prompt.id,
                        permission="write",
                        db=db,
                    )
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
            or AccessGrants.has_access(
                user_id=user.id,
                resource_type="prompt",
                resource_id=prompt.id,
                permission="read",
                db=db,
            )
        ):
            return PromptAccessResponse(
                **prompt.model_dump(),
                write_access=(
                    (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                    or user.id == prompt.user_id
                    or AccessGrants.has_access(
                        user_id=user.id,
                        resource_type="prompt",
                        resource_id=prompt.id,
                        permission="write",
                        db=db,
                    )
                ),
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ERROR_MESSAGES.NOT_FOUND,
    )


############################
# UpdatePromptById
############################


@router.post("/id/{prompt_id}/update", response_model=Optional[PromptModel])
async def update_prompt_by_id(
    prompt_id: str,
    form_data: PromptForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Is the user the original creator, in a group with write access, or an admin
    if (
        prompt.user_id != user.id
        and not AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="write",
            db=db,
        )
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Check for command collision if command is being changed
    if form_data.command != prompt.command:
        existing_prompt = Prompts.get_prompt_by_command(form_data.command, db=db)
        if existing_prompt and existing_prompt.id != prompt.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Command '/{form_data.command}' is already in use by another prompt",
            )

    # Use the ID from the found prompt
    updated_prompt = Prompts.update_prompt_by_id(prompt.id, form_data, user.id, db=db)
    if updated_prompt:
        return updated_prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# UpdatePromptMetadata
############################


@router.post("/id/{prompt_id}/update/meta", response_model=Optional[PromptModel])
async def update_prompt_metadata(
    prompt_id: str,
    form_data: PromptMetadataForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Update prompt name and command only (no history created)."""
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        prompt.user_id != user.id
        and not AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="write",
            db=db,
        )
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Check for command collision if command is being changed
    if form_data.command != prompt.command:
        existing_prompt = Prompts.get_prompt_by_command(form_data.command, db=db)
        if existing_prompt and existing_prompt.id != prompt.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Command '/{form_data.command}' is already in use",
            )

    updated_prompt = Prompts.update_prompt_metadata(
        prompt.id, form_data.name, form_data.command, form_data.tags, db=db
    )
    if updated_prompt:
        return updated_prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post("/id/{prompt_id}/update/version", response_model=Optional[PromptModel])
async def set_prompt_version(
    prompt_id: str,
    form_data: PromptVersionUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        prompt.user_id != user.id
        and not AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="write",
            db=db,
        )
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    updated_prompt = Prompts.update_prompt_version(
        prompt.id, form_data.version_id, db=db
    )
    if updated_prompt:
        return updated_prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# UpdatePromptAccessById
############################


class PromptAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post("/id/{prompt_id}/access/update", response_model=Optional[PromptModel])
async def update_prompt_access_by_id(
    prompt_id: str,
    form_data: PromptAccessGrantsForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        prompt.user_id != user.id
        and not AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="write",
            db=db,
        )
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    AccessGrants.set_access_grants("prompt", prompt_id, form_data.access_grants, db=db)

    return Prompts.get_prompt_by_id(prompt_id, db=db)


############################
# DeletePromptById
############################


@router.delete("/id/{prompt_id}/delete", response_model=bool)
async def delete_prompt_by_id(
    prompt_id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        prompt.user_id != user.id
        and not AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="write",
            db=db,
        )
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Prompts.delete_prompt_by_id(prompt.id, db=db)
    return result


############################
# Prompt History Endpoints
############################


@router.get("/id/{prompt_id}/history", response_model=list[PromptHistoryResponse])
async def get_prompt_history(
    prompt_id: str,
    page: int = 0,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get version history for a prompt."""
    PAGE_SIZE = 20

    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or prompt.user_id == user.id
        or AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="read",
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    history = PromptHistories.get_history_by_prompt_id(
        prompt.id, limit=PAGE_SIZE, offset=page * PAGE_SIZE, db=db
    )
    return history


@router.get("/id/{prompt_id}/history/{history_id}", response_model=PromptHistoryModel)
async def get_prompt_history_entry(
    prompt_id: str,
    history_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get a specific version from history."""
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or prompt.user_id == user.id
        or AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="read",
            db=db,
        )
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


@router.delete("/id/{prompt_id}/history/{history_id}", response_model=bool)
async def delete_prompt_history_entry(
    prompt_id: str,
    history_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Delete a history entry. Cannot delete the active production version."""
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        user.role == "admin"
        or prompt.user_id == user.id
        or AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="write",
            db=db,
        )
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


@router.get("/id/{prompt_id}/history/diff")
async def get_prompt_diff(
    prompt_id: str,
    from_id: str,
    to_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get diff between two versions."""
    prompt = Prompts.get_prompt_by_id(prompt_id, db=db)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or prompt.user_id == user.id
        or AccessGrants.has_access(
            user_id=user.id,
            resource_type="prompt",
            resource_id=prompt.id,
            permission="read",
            db=db,
        )
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
