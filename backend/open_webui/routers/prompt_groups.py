from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from open_webui.models.prompt_groups import (
    PromptGroupForm,
    PromptGroupModel,
    PromptGroupUserResponse,
    PromptGroupWithPromptsResponse,
    PromptGroupListResponse,
    PromptGroupMappingForm,
    PromptGroupMappingModel,
    PromptGroups,
    PromptGroupMappings,
)
from open_webui.models.prompts import PromptModel, Prompts
from open_webui.models.users import Users
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.utils.prompt_composer import compose_prompts_from_group

router = APIRouter()

############################
# Get Available Persona Values
############################


@router.get("/personas/available", response_model=dict)
async def get_available_personas(user=Depends(get_verified_user)):
    """
    Get all currently available persona values from configured prompts.
    Returns proficiency levels and response styles that are actually configured.
    """
    # Get all proficiency prompts
    proficiency_prompts = Prompts.get_prompts_by_type("proficiency")

    # Get all style prompts
    style_prompts = Prompts.get_prompts_by_type("style")

    # Extract unique persona values
    proficiency_levels = sorted(list(set(
        p.persona_value for p in proficiency_prompts
        if p.persona_value is not None
    )))

    response_styles = sorted(list(set(
        p.persona_value for p in style_prompts
        if p.persona_value is not None
    )))

    # Get prompt details for each persona value
    proficiency_details = [
        {
            "value": value,
            "prompts": [
                {"command": p.command, "title": p.title}
                for p in proficiency_prompts
                if p.persona_value == value
            ]
        }
        for value in proficiency_levels
    ]

    style_details = [
        {
            "value": value,
            "prompts": [
                {"command": p.command, "title": p.title}
                for p in style_prompts
                if p.persona_value == value
            ]
        }
        for value in response_styles
    ]

    return {
        "proficiency_levels": proficiency_details,
        "response_styles": style_details
    }


@router.get("/{group_id}/personas/available", response_model=dict)
async def get_group_available_personas(
    group_id: str,
    user=Depends(get_verified_user)
):
    """
    Get available persona values for a specific group.
    Shows only the proficiency levels and response styles configured in this group.
    """
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "read", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Get all prompts in this group
    prompts = PromptGroupMappings.get_prompts_by_group_id(group_id)

    # Filter by type
    proficiency_prompts = [p for p in prompts if p.prompt_type == "proficiency"]
    style_prompts = [p for p in prompts if p.prompt_type == "style"]

    # Extract unique persona values
    proficiency_levels = sorted(list(set(
        p.persona_value for p in proficiency_prompts
        if p.persona_value is not None
    )))

    response_styles = sorted(list(set(
        p.persona_value for p in style_prompts
        if p.persona_value is not None
    )))

    # Get details
    proficiency_details = [
        {
            "value": value,
            "prompts": [
                {"command": p.command, "title": p.title}
                for p in proficiency_prompts
                if p.persona_value == value
            ]
        }
        for value in proficiency_levels
    ]

    style_details = [
        {
            "value": value,
            "prompts": [
                {"command": p.command, "title": p.title}
                for p in style_prompts
                if p.persona_value == value
            ]
        }
        for value in response_styles
    ]

    return {
        "group_id": group_id,
        "group_name": group.name,
        "proficiency_levels": proficiency_details,
        "response_styles": style_details
    }


############################
# Get All Prompt Groups
############################


@router.get("/", response_model=list[PromptGroupUserResponse])
async def get_prompt_groups(user=Depends(get_verified_user)):
    """Get all accessible prompt groups"""
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        groups = PromptGroups.get_all_groups()
    else:
        groups = PromptGroups.get_groups_by_user_id(user.id, "read")

    return groups


@router.get("/list", response_model=list[PromptGroupListResponse])
async def get_prompt_group_list(user=Depends(get_verified_user)):
    """Get prompt groups with write access, including prompts"""
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        groups = PromptGroups.get_all_groups()
    else:
        groups = PromptGroups.get_groups_by_user_id(user.id, "write")

    # Add prompts to each group
    result = []
    for group in groups:
        prompts = PromptGroupMappings.get_prompts_by_group_id(group.id)
        result.append(
            PromptGroupListResponse(
                **group.model_dump(exclude={"user"}),
                prompts=prompts,
            )
        )

    return result


############################
# Create Prompt Group
############################


@router.post("/create", response_model=Optional[PromptGroupModel])
async def create_prompt_group(
    request: Request,
    form_data: PromptGroupForm,
    user=Depends(get_verified_user),
):
    """Create a new prompt group"""
    if user.role != "admin" and not has_permission(
        user.id, "workspace.prompts", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    group = PromptGroups.insert_new_group(user.id, form_data)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return group


############################
# Default Group Management
############################


@router.get("/default", response_model=dict)
async def get_default_group(
    request: Request,
    user=Depends(get_admin_user),
):
    """Get the current default prompt group ID (admin only)"""
    default_group_id = request.app.state.config.DEFAULT_PROMPT_GROUP_ID

    return {
        "default_group_id": default_group_id,
    }


class SetDefaultGroupForm(BaseModel):
    group_id: Optional[str] = None


@router.post("/default/set", response_model=dict)
async def set_default_group(
    request: Request,
    form_data: SetDefaultGroupForm,
    user=Depends(get_admin_user),
):
    """Set the default prompt group ID (admin only)"""
    # Validate group exists if not None
    if form_data.group_id is not None:
        group = PromptGroups.get_group_by_id(form_data.group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

    # Update config
    request.app.state.config.DEFAULT_PROMPT_GROUP_ID = form_data.group_id

    return {
        "default_group_id": form_data.group_id,
        "message": "Default prompt group updated successfully",
    }


############################
# Get Prompt Group by ID
############################


@router.get("/{group_id}", response_model=Optional[PromptGroupWithPromptsResponse])
async def get_prompt_group_by_id(
    group_id: str,
    user=Depends(get_verified_user),
):
    """Get a prompt group with its prompts"""
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "read", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Get prompts in the group
    prompts = PromptGroupMappings.get_prompts_by_group_id(group_id)

    # Get user info
    user_info = Users.get_user_by_id(group.user_id)

    return PromptGroupWithPromptsResponse(
        **group.model_dump(),
        prompts=prompts,
        user=user_info.model_dump() if user_info else None,
    )


############################
# Update Prompt Group
############################


@router.post("/{group_id}/update", response_model=Optional[PromptGroupModel])
async def update_prompt_group(
    group_id: str,
    form_data: PromptGroupForm,
    user=Depends(get_verified_user),
):
    """Update a prompt group"""
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "write", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    updated_group = PromptGroups.update_group_by_id(group_id, form_data)
    if not updated_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return updated_group


############################
# Delete Prompt Group
############################


@router.delete("/{group_id}/delete", response_model=bool)
async def delete_prompt_group(
    group_id: str,
    user=Depends(get_verified_user),
):
    """Delete a prompt group"""
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "write", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    success = PromptGroups.delete_group_by_id(group_id)
    return success


############################
# Prompt-Group Mapping APIs
############################


@router.post("/{group_id}/prompts/add", response_model=Optional[PromptGroupMappingModel])
async def add_prompt_to_group(
    group_id: str,
    form_data: PromptGroupMappingForm,
    user=Depends(get_verified_user),
):
    """Add a prompt to a group"""
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "write", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    mapping = PromptGroupMappings.add_prompt_to_group(group_id, form_data)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return mapping


@router.delete("/{group_id}/prompts/{prompt_command}", response_model=bool)
async def remove_prompt_from_group(
    group_id: str,
    prompt_command: str,
    user=Depends(get_verified_user),
):
    """Remove a prompt from a group"""
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "write", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Add leading slash if not present
    if not prompt_command.startswith("/"):
        prompt_command = f"/{prompt_command}"

    success = PromptGroupMappings.remove_prompt_from_group(group_id, prompt_command)
    return success


@router.get("/{group_id}/prompts", response_model=list[PromptModel])
async def get_group_prompts(
    group_id: str,
    user=Depends(get_verified_user),
):
    """Get all prompts in a group"""
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "read", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    prompts = PromptGroupMappings.get_prompts_by_group_id(group_id)
    return prompts


@router.post("/{group_id}/prompts/reorder", response_model=bool)
async def reorder_group_prompts(
    group_id: str,
    mappings: list[PromptGroupMappingForm],
    user=Depends(get_verified_user),
):
    """Reorder prompts in a group"""
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "write", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    success = PromptGroupMappings.reorder_prompts(group_id, mappings)
    return success


############################
# Compose Prompts (Preview)
############################


class ComposePreviewForm(BaseModel):
    proficiency_level: Optional[int] = None
    response_style: Optional[str] = None


@router.post("/{group_id}/compose", response_model=dict)
async def preview_composed_prompt(
    group_id: str,
    form_data: ComposePreviewForm,
    user=Depends(get_verified_user),
):
    """Preview the composed prompt for given persona values"""
    group = PromptGroups.get_group_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access
    if not (
        user.role == "admin"
        or group.user_id == user.id
        or has_access(user.id, "read", group.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    composed = compose_prompts_from_group(
        group_id,
        form_data.proficiency_level,
        form_data.response_style,
    )

    return {
        "group_id": group_id,
        "proficiency_level": form_data.proficiency_level,
        "response_style": form_data.response_style,
        "composed_prompt": composed,
    }
