import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.open_webui.utils.access_control import has_access
from open_webui.utils.auth import get_verified_user
from open_webui.utils.mcp.client import MCPClient
from open_webui.models.groups import Groups

log = logging.getLogger(__name__)

router = APIRouter()


async def get_mcp_client_with_auth(
    server_config: dict, request: Request, user
) -> MCPClient:
    """Create and connect an authenticated MCP client"""
    auth_type = server_config.get("auth_type", "none")
    headers = {}
    server_id = server_config.get("info", {}).get("id")

    if auth_type == "bearer":
        headers["Authorization"] = f"Bearer {server_config.get('key', '')}"
    elif auth_type == "session":
        headers["Authorization"] = f"Bearer {request.state.token.credentials}"
    elif auth_type == "oauth_2.1":
        splits = server_id.split(":")
        server_id = splits[-1] if len(splits) > 1 else server_id

        oauth_token = await request.app.state.oauth_client_manager.get_oauth_token(
            user.id, f"mcp:{server_id}"
        )

        if oauth_token:
            headers["Authorization"] = f"Bearer {oauth_token.get('access_token', '')}"

    client = MCPClient()
    await client.connect(
        url=server_config.get("url", ""),
        headers=headers if headers else None,
    )
    return client


class MCPPromptResponse(BaseModel):
    name: str
    description: Optional[str] = None
    arguments: Optional[List[dict]] = None
    server_id: str
    server_name: str
    command: str
    user_id: str
    access_control: dict | None


class MCPPromptContentResponse(BaseModel):
    name: str
    description: Optional[str] = None
    messages: List[dict]
    server_id: str


############################
# GetMCPPrompts
############################


@router.get("/", response_model=List[MCPPromptResponse])
async def get_mcp_prompts(request: Request, user=Depends(get_verified_user)):
    """Get all available MCP prompts from configured servers"""
    all_prompts = []

    for server in request.app.state.config.TOOL_SERVER_CONNECTIONS:
        if server.get("type", "openapi") != "mcp":
            continue

        server_id = server.get("info", {}).get("id")
        if not server_id:
            continue
        server_name = server.get("info", {}).get("name")
        client = None
        access_control = server.get("config", {}).get("access_control", None)
        user_id = f"server:mcp:{server.get('info', {}).get('id')}"

        try:
            client = await get_mcp_client_with_auth(server, request, user)
            prompts = await client.list_prompts()

            for prompt in prompts:
                all_prompts.append(
                    MCPPromptResponse(
                        name=prompt.get("name", ""),
                        description=prompt.get("description", ""),
                        arguments=prompt.get("arguments", []),
                        server_id=server_id,
                        server_name=server_name,
                        command="/" + server_id + ":" + prompt.get("name", ""),
                        user_id=user_id,
                        access_control=access_control,
                    )
                )

        except Exception as e:
            log.error(f"Error fetching prompts from MCP server {server_id}: {e}")
            continue
        finally:
            if client:
                await client.disconnect()
    if user.role == "admin":
        return all_prompts
    else:
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}
        prompts = [
            prompt
            for prompt in all_prompts
            if prompt.user_id == user.id
            or has_access(user.id, "read", prompt.access_control, user_group_ids)
        ]
        return prompts


############################
# RenderMCPPromptContent
############################
@router.get("/{server_id}/{prompt_name}", response_model=MCPPromptContentResponse)
async def get_mcp_prompt_content(
    server_id: str,
    prompt_name: str,
    request: Request,
    user=Depends(get_verified_user),
    arguments: Optional[str] = None,
):
    """Get the content of a specific MCP prompt"""

    # Find the server configuration
    server_config = None
    for server in request.app.state.config.TOOL_SERVER_CONNECTIONS:
        if (
            server.get("type", "openapi") == "mcp"
            and server.get("info", {}).get("id") == server_id
        ):
            server_config = server
            break

    if not server_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    user_id = f"server:mcp:{server_id}"
    access_control = server_config.get("config", {}).get("access_control", None)
    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}
    if not (
        user.role == "admin"
        or user.id == user_id
        or has_access(user.id, "read", access_control, user_group_ids)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    client = None
    try:
        client = await get_mcp_client_with_auth(server_config, request, user)

        # Parse arguments if provided
        prompt_arguments = {}
        if arguments:
            import json

            try:
                prompt_arguments = json.loads(arguments)
            except (json.JSONDecodeError, TypeError):
                prompt_arguments = {}

        prompt_result = await client.get_prompt(prompt_name, prompt_arguments)

        return MCPPromptContentResponse(
            name=prompt_name,
            description=prompt_result.get("description", ""),
            messages=prompt_result.get("messages", []),
            server_id=server_id,
        )

    except Exception as e:
        log.error(f"Error fetching prompt content from MCP server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching prompt: {str(e)}",
        )
    finally:
        if client:
            await client.disconnect()
