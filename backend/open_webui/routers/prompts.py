from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging

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
from open_webui.utils.hardcoded_tools import (
    get_hardcoded_tools,
    get_hardcoded_tool_by_command,
    is_hardcoded_tool
)

log = logging.getLogger(__name__)

router = APIRouter()

############################
# GetPrompts
############################


@router.get("/", response_model=list[PromptModel])
async def get_prompts(
    user=Depends(get_verified_user),
    include_hardcoded: bool = True
):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        prompts = Prompts.get_prompts()
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "read")

    # Add hardcoded tools to the list
    if include_hardcoded:
        hardcoded_tools = get_hardcoded_tools()
        log.info(f"[PROMPTS API /] Adding {len(hardcoded_tools)} hardcoded tools")

        for tool in hardcoded_tools:
            prompts.append(
                PromptModel(
                    command=f"/{tool.command}",
                    user_id="system",
                    title=tool.name,
                    content=f"(하드코딩된 도구 - 소스코드에 정의됨)\n\n{tool.description}",
                    timestamp=0,
                    access_control=None,
                    prompt_type="hardcoded_tool",
                    persona_value=None,
                    tool_description=tool.description,
                    tool_priority=0,
                    validation_rules=None
                )
            )

    return prompts


@router.get("/list", response_model=list[PromptUserResponse])
async def get_prompt_list(
    user=Depends(get_verified_user),
    include_hardcoded: bool = True
):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        prompts = Prompts.get_prompts()
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "write")

    # Add hardcoded tools to the list
    if include_hardcoded:
        hardcoded_tools = get_hardcoded_tools()
        log.info(f"[PROMPTS API] Adding {len(hardcoded_tools)} hardcoded tools to prompts list")

        for tool in hardcoded_tools:
            # Convert HardcodedToolMetadata to PromptUserResponse format
            # Use a system user ID to indicate it's a system tool
            prompts.append(
                PromptUserResponse(
                    command=f"/{tool.command}",  # Add / prefix for consistency
                    user_id="system",  # Mark as system-owned
                    title=tool.name,
                    content=f"(하드코딩된 도구 - 소스코드에 정의됨)\n\n{tool.description}",
                    timestamp=0,  # Use 0 to indicate it's not a DB entry
                    access_control=None,  # Public access
                    prompt_type="hardcoded_tool",
                    persona_value=None,
                    tool_description=tool.description,
                    tool_priority=0,
                    validation_rules=None,
                    user=None  # No user info for hardcoded tools
                )
            )

    return prompts


############################
# Hardcoded Tools API
############################


@router.get("/hardcoded", response_model=list[PromptUserResponse])
async def get_hardcoded_tools_list(user=Depends(get_verified_user)):
    """Get all hardcoded tools (source code-defined tools)"""
    hardcoded_tools = get_hardcoded_tools()
    log.info(f"[PROMPTS API] Returning {len(hardcoded_tools)} hardcoded tools")

    prompts = []
    for tool in hardcoded_tools:
        prompts.append(
            PromptUserResponse(
                command=f"/{tool.command}",
                user_id="system",
                title=tool.name,
                content=f"(하드코딩된 도구 - 소스코드에 정의됨)\n\n{tool.description}\n\n시스템 프롬프트:\n{tool.system_prompt[:500]}...",
                timestamp=0,
                access_control=None,
                prompt_type="hardcoded_tool",
                persona_value=None,
                tool_description=tool.description,
                tool_priority=0,
                validation_rules=None,
                user=None
            )
        )

    return prompts


############################
# Persona-based Prompt APIs
############################


@router.get("/by-type/{prompt_type}", response_model=list[PromptModel])
async def get_prompts_by_type(
    prompt_type: str,
    user=Depends(get_verified_user)
):
    """Get all prompts of a specific type (base, proficiency, style)"""
    prompts = Prompts.get_prompts_by_type(prompt_type)

    # Filter by access control
    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}
    accessible_prompts = [
        prompt
        for prompt in prompts
        if user.role == "admin"
        or prompt.user_id == user.id
        or has_access(user.id, "read", prompt.access_control, user_group_ids)
    ]

    return accessible_prompts


@router.get("/by-persona", response_model=list[PromptModel])
async def get_prompts_by_persona(
    prompt_type: str,
    persona_value: str,
    user=Depends(get_verified_user)
):
    """Get prompts matching both type and persona value"""
    prompts = Prompts.get_prompts_by_persona(prompt_type, persona_value)

    # Filter by access control
    from open_webui.models.groups import Groups
    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}
    accessible_prompts = [
        prompt
        for prompt in prompts
        if user.role == "admin"
        or prompt.user_id == user.id
        or has_access(user.id, "read", prompt.access_control, user_group_ids)
    ]

    return accessible_prompts


############################
# CreateNewPrompt
############################


@router.post("/create", response_model=Optional[PromptModel])
async def create_new_prompt(
    request: Request, form_data: PromptForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not (
        has_permission(
            user.id, "workspace.prompts", request.app.state.config.USER_PERMISSIONS
        )
        or has_permission(
            user.id,
            "workspace.prompts_import",
            request.app.state.config.USER_PERMISSIONS,
        )
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
    # First check if it's a hardcoded tool
    if is_hardcoded_tool(command):
        tool = get_hardcoded_tool_by_command(command)
        if tool:
            log.info(f"[PROMPTS API] Returning hardcoded tool: {command}")
            # Return as PromptModel format
            return PromptModel(
                command=f"/{tool.command}",
                user_id="system",
                title=tool.name,
                content=f"(하드코딩된 도구 - 소스코드에 정의됨)\n\n{tool.description}",
                timestamp=0,
                access_control=None,
                prompt_type="hardcoded_tool",
                persona_value=None,
                tool_description=tool.description,
                tool_priority=0,
                validation_rules=None
            )

    # Check DB prompts
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
