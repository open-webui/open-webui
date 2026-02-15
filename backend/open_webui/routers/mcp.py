"""
MCP (Model Context Protocol) Router.

Provides endpoints for:
- Reading UI resources from MCP servers
- Calling MCP tools
- Listing resources and prompts
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.utils.mcp.client import MCPClient
from open_webui.utils.mcp.models import (
    MCPAppResource,
    MCPToolResult,
    MCPUIPermissions,
    McpUiResourceCsp,
)
from open_webui.utils.tools import has_tool_server_access

log = logging.getLogger(__name__)

router = APIRouter()


class ReadResourceRequest(BaseModel):
    server_id: str
    uri: str


class ReadResourceResponse(BaseModel):
    resource: MCPAppResource


class CallToolRequest(BaseModel):
    server_id: str
    tool_name: str
    arguments: dict = {}


class ListResourcesRequest(BaseModel):
    server_id: str


class ListPromptsRequest(BaseModel):
    server_id: str


async def get_mcp_client_and_connection(
    request: Request, server_id: str, user: UserModel, check_mcp_apps: bool = False
) -> tuple[MCPClient, dict]:
    """
    Get or create an MCP client for the given server.
    Validates access control and returns the client and connection config.

    Args:
        check_mcp_apps: If True, also checks if MCP Apps are enabled globally and per-server.
    """
    # Check global MCP Apps enable flag (only for MCP Apps operations)
    if check_mcp_apps:
        mcp_apps_enabled = getattr(request.app.state.config, "ENABLE_MCP_APPS", True)
        if not mcp_apps_enabled:
            raise HTTPException(
                status_code=403, detail="MCP Apps are disabled globally"
            )

    # Find server connection in config
    tool_servers = request.app.state.config.TOOL_SERVER_CONNECTIONS
    server_connection = None

    for server in tool_servers:
        if (
            server.get("type", "") == "mcp"
            and server.get("info", {}).get("id", "") == server_id
        ):
            server_connection = server
            break

    if not server_connection:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_id}' not found")

    # Check per-server MCP Apps enable flag (only for MCP Apps operations)
    if check_mcp_apps:
        server_mcp_apps_enabled = server_connection.get("config", {}).get(
            "enable_mcp_apps", True
        )
        if not server_mcp_apps_enabled:
            raise HTTPException(
                status_code=403, detail=f"MCP Apps are disabled for server '{server_id}'"
            )

    # Check access control
    if not has_tool_server_access(user, server_connection):
        raise HTTPException(
            status_code=403, detail=f"Access denied to MCP server '{server_id}'"
        )

    # Build headers for authentication
    headers = {}
    auth_type = server_connection.get("auth_type", "")
    if auth_type == "bearer":
        headers["Authorization"] = f"Bearer {server_connection.get('key', '')}"

    connection_headers = server_connection.get("headers", None)
    if connection_headers:
        if isinstance(connection_headers, list):
            for header in connection_headers:
                headers[header.get("key", "")] = header.get("value", "")
        elif isinstance(connection_headers, dict):
            headers.update(connection_headers)

    # Create and connect client
    client = MCPClient()
    # Get MCP Apps enabled status for capability announcement
    mcp_apps_enabled = getattr(request.app.state.config, "ENABLE_MCP_APPS", True)
    try:
        await client.connect(
            url=server_connection.get("url", ""),
            headers=headers if headers else None,
            enable_mcp_apps=mcp_apps_enabled,
        )
    except Exception as e:
        log.error(f"Failed to connect to MCP server '{server_id}': {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to MCP server: {str(e)}"
        )

    return client, server_connection


@router.post("/resource", response_model=ReadResourceResponse)
async def read_resource(
    request: Request,
    body: ReadResourceRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    Read a UI resource from an MCP server.

    The URI should start with 'ui://' for UI resources.
    Extracts _meta.ui.csp and _meta.ui.permissions from resource metadata.
    """
    if not body.uri.startswith("ui://"):
        raise HTTPException(
            status_code=400, detail="Invalid resource URI. Must start with 'ui://'"
        )

    # Check MCP Apps is enabled (global + per-server)
    client, _ = await get_mcp_client_and_connection(
        request, body.server_id, user, check_mcp_apps=True
    )

    try:
        # First list resources to get metadata (where _meta.ui.csp lives)
        resources_list = await client.list_resources()
        resource_meta = None

        # Find the resource matching our URI to get its metadata
        if resources_list:
            for res in resources_list:
                # Convert AnyUrl to string for comparison
                if str(res.get("uri")) == body.uri:
                    resource_meta = res.get("meta")
                    break

        # Read the resource content
        contents = await client.read_resource(body.uri)

        if not contents:
            raise HTTPException(status_code=404, detail="Resource not found")

        # Parse the resource content from contents array
        content = ""
        mime_type = "text/html"

        for item in contents:
            # Get content based on type
            if item.get("text"):
                content = item.get("text", "")
            elif item.get("blob"):
                # Handle binary content (base64 encoded)
                content = item.get("blob", "")

            # Get mime type
            if item.get("mimeType"):
                mime_type = item.get("mimeType")

        # Extract CSP and permissions from resource metadata (_meta.ui)
        csp = None
        permissions = None

        if resource_meta:
            ui_meta = resource_meta.get("ui", {})

            # Extract CSP per MCP ext-apps spec
            csp_data = ui_meta.get("csp")
            if csp_data:
                csp = McpUiResourceCsp(
                    connectDomains=csp_data.get("connectDomains"),
                    resourceDomains=csp_data.get("resourceDomains"),
                    frameDomains=csp_data.get("frameDomains"),
                    baseUriDomains=csp_data.get("baseUriDomains"),
                )

            # Extract permissions per MCP ext-apps spec
            permissions_data = ui_meta.get("permissions")
            if permissions_data:
                permissions = MCPUIPermissions(**permissions_data)

        # Build response
        resource = MCPAppResource(
            uri=body.uri,
            mimeType=mime_type,
            content=content,
            csp=csp,
            permissions=permissions,
        )

        return ReadResourceResponse(resource=resource)

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to read resource '{body.uri}': {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to read resource: {str(e)}"
        )
    finally:
        await client.disconnect()


@router.post("/tool/call")
async def call_tool(
    request: Request,
    body: CallToolRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    Call a tool on an MCP server from an app context.

    Returns the tool result in MCP content format.
    """
    # Check MCP Apps is enabled (global + per-server)
    client, _ = await get_mcp_client_and_connection(
        request, body.server_id, user, check_mcp_apps=True
    )

    try:
        result = await client.call_tool(body.tool_name, body.arguments)

        # Format result
        if result is None:
            return MCPToolResult(
                content=[{"type": "text", "text": ""}],
                isError=False,
            )

        # If result is already in MCP format
        if isinstance(result, list):
            return MCPToolResult(
                content=result,
                isError=False,
            )

        # Wrap in text content
        return MCPToolResult(
            content=[{"type": "text", "text": str(result)}],
            isError=False,
        )

    except Exception as e:
        log.error(f"Tool call failed for '{body.tool_name}': {e}")
        return MCPToolResult(
            content=[{"type": "text", "text": str(e)}],
            isError=True,
        )
    finally:
        await client.disconnect()


@router.post("/resources")
async def list_resources(
    request: Request,
    body: ListResourcesRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    List available resources from an MCP server.
    """
    client, _ = await get_mcp_client_and_connection(request, body.server_id, user)

    try:
        resources = await client.list_resources()
        return {"resources": resources or []}

    except Exception as e:
        log.error(f"Failed to list resources: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list resources: {str(e)}"
        )
    finally:
        await client.disconnect()


@router.post("/prompts")
async def list_prompts(
    request: Request,
    body: ListPromptsRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    List available prompts from an MCP server.
    """
    client, _ = await get_mcp_client_and_connection(request, body.server_id, user)

    try:
        prompts = await client.list_prompts()
        return {"prompts": prompts or []}

    except Exception as e:
        log.error(f"Failed to list prompts: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list prompts: {str(e)}"
        )
    finally:
        await client.disconnect()
