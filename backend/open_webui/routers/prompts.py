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
    # Normalize command: ensure it starts with /
    normalized_command = f"/{command.lstrip('/')}"

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
    prompt = Prompts.get_prompt_by_command(normalized_command)

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
    # Normalize command: ensure it starts with /
    normalized_command = f"/{command.lstrip('/')}"

    prompt = Prompts.get_prompt_by_command(normalized_command)
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

    prompt = Prompts.update_prompt_by_command(normalized_command, form_data)
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
    # Normalize command: ensure it starts with /
    normalized_command = f"/{command.lstrip('/')}"

    prompt = Prompts.get_prompt_by_command(normalized_command)
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

    result = Prompts.delete_prompt_by_command(normalized_command)
    return result


############################
# Langfuse Version Control
############################


@router.get("/command/{command}/versions", response_model=list[dict])
async def get_prompt_versions(command: str, user=Depends(get_admin_user)):
    """
    Get version history from Langfuse for a prompt.

    Returns list of all versions with version number, content, and timestamps.
    Only accessible by admin users.
    """
    from open_webui.integrations.langfuse_adapter import get_langfuse_adapter

    adapter = get_langfuse_adapter()
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse not configured or disabled"
        )

    try:
        # Normalize command: ensure it starts with /
        normalized_command = f"/{command.lstrip('/')}"

        # Get versions from Langfuse
        versions = adapter.get_prompt_versions(normalized_command)
        return versions
    except Exception as e:
        log.error(f"Failed to fetch versions for {command}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch versions: {str(e)}"
        )


@router.post("/command/{command}/rollback/{version}", response_model=bool)
async def rollback_prompt_version(
    command: str,
    version: int,
    user=Depends(get_admin_user)
):
    """
    Rollback a prompt to a specific Langfuse version.

    This fetches the specified version from Langfuse and updates the local DB.
    The update will also create a new version in Langfuse (rollback creates new version).
    Only accessible by admin users.
    """
    from open_webui.integrations.langfuse_adapter import get_langfuse_adapter

    adapter = get_langfuse_adapter()
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse not configured or disabled"
        )

    # Normalize command: ensure it starts with /
    normalized_command = f"/{command.lstrip('/')}"

    # Fetch specific version from Langfuse
    prompt_content = adapter.fetch_prompt_from_langfuse(normalized_command, version=version)
    if not prompt_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found in Langfuse"
        )

    # Get current prompt from local DB
    prompt = Prompts.get_prompt_by_command(normalized_command)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {normalized_command} not found in local database"
        )

    # Update local DB with rollback content
    form_data = PromptForm(
        command=prompt.command,
        title=prompt.title,
        content=prompt_content,  # Rollback content from Langfuse
        access_control=prompt.access_control,
        prompt_type=prompt.prompt_type,
        persona_value=prompt.persona_value,
        tool_description=prompt.tool_description,
        tool_priority=prompt.tool_priority,
        validation_rules=prompt.validation_rules,
    )

    updated = Prompts.update_prompt_by_command(normalized_command, form_data)
    if updated:
        log.info(f"[LANGFUSE] Rolled back prompt {normalized_command} to version {version}")
        return True
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update prompt in local database"
        )


@router.get("/group/{group_id}/usage", response_model=dict)
async def get_prompt_group_usage(
    group_id: str,
    user=Depends(get_admin_user),
    days: int = 7,
    limit: int = 20,
    offset: int = 0,
    summary: bool = False
):
    """
    Get usage statistics for a prompt group from Langfuse traces.

    Two modes:
    1. Summary mode (summary=true): Fast, returns trace list with metadata only (no tokens/latency)
    2. Detailed mode (summary=false): Fetches observations for accurate tokens/latency data

    Supports pagination via offset/limit parameters.

    Returns statistics on total calls, average latency, token usage,
    and list of recent traces for the specified prompt group.
    Only accessible by admin users.

    Args:
        group_id: Prompt group ID to get statistics for
        days: Number of days to look back (default: 7)
        limit: Maximum number of traces to fetch per page (default: 20)
        offset: Number of traces to skip for pagination (default: 0)
        summary: If true, return only metadata without detailed observations (default: false)
    """
    from open_webui.integrations.langfuse_adapter import get_langfuse_adapter

    adapter = get_langfuse_adapter()
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse not configured or disabled"
        )

    try:
        # Fetch traces and statistics from Langfuse
        result = adapter.get_traces_for_prompt_group(
            prompt_group_id=group_id,
            limit=limit,
            days=days,
            offset=offset,
            summary_only=summary
        )

        mode = "summary" if summary else "detailed"
        log.info(f"[LANGFUSE] Fetched {mode} usage stats for prompt group: {group_id} (offset={offset}, limit={limit})")

        return result
    except Exception as e:
        log.error(f"Failed to fetch usage stats for group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch usage statistics: {str(e)}"
        )


############################
# Migration to Langfuse
############################


@router.post("/migrate-to-langfuse", response_model=dict)
async def migrate_prompts_to_langfuse(user=Depends(get_admin_user)):
    """
    One-time migration endpoint to sync all existing prompts to Langfuse.

    Returns statistics on how many prompts were synced successfully.
    Only accessible by admin users.
    """
    from open_webui.integrations.langfuse_adapter import get_langfuse_adapter

    adapter = get_langfuse_adapter()
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse not configured or disabled"
        )

    try:
        # Get all prompts from local DB
        all_prompts = Prompts.get_prompts()

        synced = 0
        failed = 0
        errors = []

        log.info(f"[LANGFUSE MIGRATION] Starting migration of {len(all_prompts)} prompts...")

        for prompt in all_prompts:
            try:
                # Sync each prompt to Langfuse
                success = adapter.sync_prompt_to_langfuse(prompt)
                if success:
                    synced += 1
                    log.info(f"[LANGFUSE MIGRATION] ✓ Synced: {prompt.command}")
                else:
                    failed += 1
                    errors.append(f"Failed to sync {prompt.command} (no exception)")
                    log.warning(f"[LANGFUSE MIGRATION] ✗ Failed: {prompt.command}")
            except Exception as e:
                failed += 1
                error_msg = f"Failed to sync {prompt.command}: {str(e)}"
                errors.append(error_msg)
                log.error(f"[LANGFUSE MIGRATION] ✗ Error: {error_msg}")

        log.info(f"[LANGFUSE MIGRATION] Migration complete: {synced} synced, {failed} failed")

        return {
            "total": len(all_prompts),
            "synced": synced,
            "failed": failed,
            "errors": errors[:10]  # Return first 10 errors only
        }
    except Exception as e:
        log.error(f"[LANGFUSE MIGRATION] Migration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )
