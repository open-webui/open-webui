"""
MCP (Model Context Protocol) Router

This module handles MCP server connections and tool discovery/execution using FastMCP.
It follows the same patterns as the Ollama and OpenAI routers for consistency.
"""

import logging
import json
from typing import Optional, Dict, List, Any

from fastmcp.client import Client
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user, get_verified_user
from mcp_backend.management.mcp_manager import mcp_manager
from mcp_backend.models.mcp_servers import MCPServers

log = logging.getLogger(__name__)

########################################
#
# Utility functions
#
##########################################


async def create_mcp_client(url: str, headers: Optional[Dict] = None):
    """Create FastMCP client connection to MCP server"""
    try:
        # FastMCP Client can connect to URLs, FastMCP servers, or stdio processes
        client = Client(url)
        return client
    except Exception as e:
        log.exception(f"Failed to create MCP client for {url}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"MCP: Unable to connect to server at {url}. Please check the URL and try again.",
        )


def get_mcp_api_config(idx: int, url: str, configs: Dict) -> Dict:
    """Get API configuration for MCP server"""
    return configs.get(str(idx), configs.get(url, {}))


def get_config_value(request: Request, key: str, default=None):
    """Helper function to get config values that handles both dict and object formats"""
    config = request.app.state.config
    if isinstance(config, dict):
        return config.get(key, default)
    else:
        return getattr(config, key, default)


def set_config_value(request: Request, key: str, value):
    """Helper function to set config values that handles both dict and object formats"""
    config = request.app.state.config
    if isinstance(config, dict):
        config[key] = value
    else:
        setattr(config, key, value)


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.head("/")
@router.get("/")
async def get_status():
    return {"status": True}


class ConnectionVerificationForm(BaseModel):
    url: str
    key: Optional[str] = None


@router.post("/verify")
async def verify_connection(
    request: Request,
    form_data: ConnectionVerificationForm,
    user=Depends(get_admin_user),
):
    """Verify connection to MCP server using FastMCP client"""
    url = form_data.url

    # Special case: if URL is empty or 'built-in', verify FastMCP manager
    if not url or url.lower() in ["built-in", "fastmcp", "local"]:
        try:
            if (
                hasattr(request.app.state, "mcp_manager")
                and request.app.state.mcp_manager
            ):
                tools = await request.app.state.mcp_manager.get_all_tools()
                return {
                    "status": "connected",
                    "message": "FastMCP manager is working",
                    "tools_count": len(tools),
                    "capabilities": {"tools": True},
                }
            else:
                return {
                    "status": "failed",
                    "error": "FastMCP manager not initialized",
                    "message": "FastMCP manager not available",
                }
        except Exception as e:
            log.exception(f"FastMCP manager verification failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "message": "FastMCP manager verification failed",
            }

    # For external MCP servers
    try:
        # Try to connect and get available tools using FastMCP
        client = await create_mcp_client(url)
        async with client:
            tools = await client.list_tools()

            return {
                "status": "connected",
                "message": f"MCP server at {url} responding to tools list",
                "tools_count": len(tools),
                "capabilities": {"tools": True},
            }

    except Exception as e:
        log.exception(f"MCP connection verification failed for {url}: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "message": "Connection verification failed",
        }


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    """Get MCP configuration"""
    builtin_info = await get_builtin_servers(request, user)

    return {
        "ENABLE_MCP_API": get_config_value(request, "ENABLE_MCP_API", False),
        "MCP_BASE_URLS": get_config_value(request, "MCP_BASE_URLS", []),
        "MCP_API_CONFIGS": get_config_value(request, "MCP_API_CONFIGS", {}),
        "BUILTIN_SERVERS": builtin_info["servers"],
    }


class MCPConfigForm(BaseModel):
    ENABLE_MCP_API: Optional[bool] = None
    MCP_BASE_URLS: List[str]
    MCP_API_CONFIGS: Dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: MCPConfigForm, user=Depends(get_admin_user)
):
    """Update MCP configuration"""
    set_config_value(request, "ENABLE_MCP_API", form_data.ENABLE_MCP_API)
    set_config_value(request, "MCP_BASE_URLS", form_data.MCP_BASE_URLS)
    set_config_value(request, "MCP_API_CONFIGS", form_data.MCP_API_CONFIGS)

    # Remove the API configs that are not in the API URLS
    base_urls = get_config_value(request, "MCP_BASE_URLS", [])
    keys = list(map(str, range(len(base_urls))))
    api_configs = get_config_value(request, "MCP_API_CONFIGS", {})
    filtered_configs = {key: value for key, value in api_configs.items() if key in keys}
    set_config_value(request, "MCP_API_CONFIGS", filtered_configs)

    return {
        "ENABLE_MCP_API": get_config_value(request, "ENABLE_MCP_API", False),
        "MCP_BASE_URLS": get_config_value(request, "MCP_BASE_URLS", []),
        "MCP_API_CONFIGS": get_config_value(request, "MCP_API_CONFIGS", {}),
    }


async def get_tools_from_mcp_server(url: str, idx: int, api_config: Dict):
    """Get tools from a specific MCP server using FastMCP client"""
    try:
        client = await create_mcp_client(url)
        async with client:
            tools = await client.list_tools()
            return tools
    except Exception as e:
        log.exception(f"Failed to get tools from MCP server {url}: {e}")
        return []


async def get_all_mcp_tools(request: Request) -> Dict[str, List]:
    """Get all tools from all configured MCP servers"""
    all_tools = []

    # First, get tools from FastMCP manager (built-in servers)
    try:
        if hasattr(request.app.state, "mcp_manager") and request.app.state.mcp_manager:
            fastmcp_tools = await request.app.state.mcp_manager.get_all_tools()
            all_tools.extend(fastmcp_tools)
            log.info(f"Got {len(fastmcp_tools)} tools from FastMCP manager")
    except Exception as e:
        log.exception(f"Error getting tools from FastMCP manager: {e}")

    # Then, get tools from external MCP servers (if any configured)
    try:
        # Handle both dict and object config formats
        config = request.app.state.config
        if isinstance(config, dict):
            urls = config.get("MCP_BASE_URLS", []) or []
            api_configs = config.get("MCP_API_CONFIGS", {}) or {}
        else:
            urls = getattr(config, "MCP_BASE_URLS", []) or []
            api_configs = getattr(config, "MCP_API_CONFIGS", {}) or {}

        for idx, url in enumerate(urls):
            if url and url.strip():  # Skip empty URLs
                try:
                    api_config = get_mcp_api_config(idx, url, api_configs)
                    tools = await get_tools_from_mcp_server(url, idx, api_config)

                    # Add server info and prefix if configured
                    prefix_id = api_config.get("prefix_id", None)
                    for tool in tools:
                        tool_dict = {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": (
                                tool.inputSchema.model_dump()
                                if hasattr(tool.inputSchema, "model_dump")
                                else tool.inputSchema
                            ),
                            "mcp_server_url": url,
                            "mcp_server_idx": idx,
                        }

                        if prefix_id:
                            tool_dict["name"] = f"{prefix_id}.{tool_dict['name']}"

                        all_tools.append(tool_dict)

                except Exception as e:
                    log.exception(
                        f"Error getting tools from external MCP server {url}: {e}"
                    )
                    continue

    except Exception as e:
        log.exception(f"Error getting external MCP tools: {e}")

    return {"tools": all_tools}


@router.get("/tools")
async def get_mcp_tools(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    """Get available tools from MCP servers"""
    if url_idx is not None:
        # For backward compatibility with external MCP servers
        urls = get_config_value(request, "MCP_BASE_URLS", []) or []
        if url_idx >= len(urls):
            raise HTTPException(status_code=404, detail="External MCP server not found")

        url = urls[url_idx]
        api_configs = get_config_value(request, "MCP_API_CONFIGS", {}) or {}
        api_config = get_mcp_api_config(url_idx, url, api_configs)

        try:
            tools = await get_tools_from_mcp_server(url, url_idx, api_config)

            # Add server info and prefix if configured
            prefix_id = api_config.get("prefix_id", None)
            tools_list = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": (
                        tool.inputSchema.model_dump()
                        if hasattr(tool.inputSchema, "model_dump")
                        else tool.inputSchema
                    ),
                    "mcp_server_url": url,
                    "mcp_server_idx": url_idx,
                }

                if prefix_id:
                    tool_dict["name"] = f"{prefix_id}.{tool_dict['name']}"

                tools_list.append(tool_dict)

            return {"tools": tools_list}

        except Exception as e:
            log.exception(f"Error getting tools from external MCP server {url}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting tools from external MCP server: {str(e)}",
            )
    else:
        # Get tools from all MCP servers (both built-in and external)
        result = await get_all_mcp_tools(request)
        return result


class MCPToolCallForm(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None
    server_idx: Optional[int] = None


@router.post("/tools/call")
async def call_mcp_tool(
    request: Request, form_data: MCPToolCallForm, user=Depends(get_verified_user)
):
    """Call a tool on FastMCP manager"""
    tool_name = form_data.name
    arguments = form_data.arguments or {}

    try:
        if hasattr(request.app.state, "mcp_manager") and request.app.state.mcp_manager:
            # Find which server has this tool
            server_name = None
            server_names = request.app.state.mcp_manager.get_running_servers()

            # Handle prefixed tool names (e.g., "mcp_server_1/search_news" -> "search_news")
            clean_tool_name = tool_name
            if "/" in tool_name:
                clean_tool_name = tool_name.split("/")[-1]
            elif "." in tool_name:
                clean_tool_name = tool_name.split(".")[-1]

            log.info(
                f"Looking for tool '{tool_name}' (clean name: '{clean_tool_name}') across servers: {server_names}"
            )

            for name in server_names:
                try:
                    # Get tools from this server to check if it has our tool
                    tools = await request.app.state.mcp_manager.get_tools_from_server(
                        name
                    )
                    tool_names = [tool.get("name", "") for tool in tools]
                    log.info(f"Server '{name}' has tools: {tool_names}")

                    # Check both original and clean tool names
                    if tool_name in tool_names or clean_tool_name in tool_names:
                        server_name = name
                        # Use the clean tool name for the actual call
                        tool_name = clean_tool_name
                        log.info(f"Found tool '{clean_tool_name}' on server '{name}'")
                        break
                except Exception as e:
                    log.warning(f"Failed to get tools from server {name}: {e}")
                    continue

            if not server_name:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool '{tool_name}' not found on any available MCP server",
                )

            result = await request.app.state.mcp_manager.call_tool(
                server_name, tool_name, arguments
            )

            # Handle FastMCP result format
            if isinstance(result, list) and len(result) > 0:
                # FastMCP returns a list of content objects
                content = []
                for item in result:
                    if hasattr(item, "text"):
                        content.append({"type": "text", "text": item.text})
                    else:
                        content.append({"type": "text", "text": str(item)})
                return {"content": content}
            else:
                # Fallback for other formats
                return {"content": [{"type": "text", "text": str(result)}]}
        else:
            raise HTTPException(status_code=500, detail="FastMCP manager not available")

    except Exception as e:
        log.exception(f"Error calling MCP tool {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error calling MCP tool: {str(e)}")


class UrlForm(BaseModel):
    urls: List[str]


@router.get("/urls")
async def get_urls(request: Request, user=Depends(get_admin_user)):
    """Get MCP server URLs"""
    return {"MCP_BASE_URLS": get_config_value(request, "MCP_BASE_URLS", [])}


@router.post("/urls/update")
async def update_urls(
    request: Request, form_data: UrlForm, user=Depends(get_admin_user)
):
    """Update MCP server URLs"""
    urls = [url.strip() for url in form_data.urls if url.strip()]
    set_config_value(request, "MCP_BASE_URLS", urls)

    return {"MCP_BASE_URLS": get_config_value(request, "MCP_BASE_URLS", [])}


@router.get("/servers/builtin")
async def get_builtin_servers(request: Request, user=Depends(get_admin_user)):
    """Get information about built-in MCP servers"""
    if hasattr(request.app.state, "mcp_manager") and request.app.state.mcp_manager:
        server_names = request.app.state.mcp_manager.get_server_names()
        servers = []

        # Only include actual built-in servers
        builtin_server_names = ["time_server", "news_server"]

        for name in server_names:
            if name not in builtin_server_names:
                continue  # Skip non-built-in servers

            status = request.app.state.mcp_manager.get_server_status(name)
            config = request.app.state.mcp_manager.server_configs.get(name, {})

            # Get tools count for this server
            tools_count = 0
            try:
                tools = await request.app.state.mcp_manager.get_tools_from_server(name)
                tools_count = len(tools)
            except Exception:
                pass

            servers.append(
                {
                    "name": name,
                    "display_name": name.replace("_", " ").title(),
                    "status": status,
                    "transport": config.get("transport", "stdio"),
                    "tools_count": tools_count,
                    "description": get_server_description(name),
                }
            )

        return {"servers": servers}
    else:
        return {"servers": []}


def get_server_description(name: str) -> str:
    """Get description for built-in servers"""
    descriptions = {
        "time_server": "Provides current time and timezone information",
        "news_server": "Provides latest news headlines from NewsDesk",
    }
    return descriptions.get(name, f"Built-in MCP server: {name}")


@router.post("/servers/builtin/{server_name}/restart")
async def restart_builtin_server(
    request: Request, server_name: str, user=Depends(get_admin_user)
):
    """Restart a built-in MCP server"""
    try:
        # Check if this is a valid built-in server
        builtin_server_names = ["time_server", "news_server"]
        if server_name not in builtin_server_names:
            raise HTTPException(
                status_code=404, detail=f"Built-in server '{server_name}' not found"
            )

        if (
            not hasattr(request.app.state, "mcp_manager")
            or not request.app.state.mcp_manager
        ):
            raise HTTPException(status_code=500, detail="MCP manager not available")

        # Restart the server
        success = await request.app.state.mcp_manager.restart_server(server_name)
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to restart server {server_name}"
            )

        return {"message": f"Built-in server {server_name} restarted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error restarting built-in MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error restarting built-in server: {str(e)}"
        )


# Pydantic models for external server management
class MCPServerForm(BaseModel):
    name: str
    description: Optional[str] = None
    command: str
    args: Optional[List[str]] = []
    env: Optional[Dict[str, str]] = {}
    transport: str = "stdio"  # "stdio" or "http"
    url: Optional[str] = None
    port: Optional[int] = None
    is_active: Optional[bool] = True


class MCPServerUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    transport: Optional[str] = None
    url: Optional[str] = None
    port: Optional[int] = None
    is_active: Optional[bool] = None


##########################################
#
# External MCP Server Management
#
##########################################


@router.get("/servers/external")
async def get_external_servers(request: Request, user=Depends(get_admin_user)):
    """Get all external (user-created) MCP servers"""
    try:
        servers = MCPServers.get_user_created_servers()

        # Convert to dictionaries and enrich with runtime status from MCP manager
        server_dicts = []
        for server in servers:
            # Convert Pydantic model to dict
            server_dict = server.model_dump()

            if (
                hasattr(request.app.state, "mcp_manager")
                and request.app.state.mcp_manager
            ):
                status = request.app.state.mcp_manager.get_server_status(server.name)
                server_dict["runtime_status"] = status

                # Get tools count if server is running
                if status == "running":
                    try:
                        tools = (
                            await request.app.state.mcp_manager.get_tools_from_server(
                                server.name
                            )
                        )
                        server_dict["tools_count"] = len(tools)
                    except Exception:
                        server_dict["tools_count"] = 0
                else:
                    server_dict["tools_count"] = 0
            else:
                server_dict["runtime_status"] = "unknown"
                server_dict["tools_count"] = 0

            server_dicts.append(server_dict)

        return {"servers": server_dicts}
    except Exception as e:
        log.exception(f"Error getting external MCP servers: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting external servers: {str(e)}"
        )


@router.post("/servers/external")
async def create_external_server(
    request: Request, form_data: MCPServerForm, user=Depends(get_admin_user)
):
    """Create a new external MCP server"""
    try:
        # Check if server name already exists
        existing_server = MCPServers.get_server_by_name(form_data.name)
        if existing_server:
            raise HTTPException(
                status_code=400,
                detail=f"Server with name '{form_data.name}' already exists",
            )

        # Validate transport-specific fields
        if form_data.transport == "http" and not form_data.url and not form_data.port:
            raise HTTPException(
                status_code=400, detail="HTTP transport requires either URL or port"
            )

        # Create server in database
        server_data = {
            "name": form_data.name,
            "description": form_data.description,
            "user_id": user.id,
            "server_type": "user_created",
            "command": form_data.command,
            "args": form_data.args or [],
            "env": form_data.env or {},
            "transport": form_data.transport,
            "url": form_data.url,
            "port": form_data.port,
            "is_active": form_data.is_active,
            "is_deletable": True,
        }

        server = MCPServers.insert_new_server(**server_data)
        if not server:
            raise HTTPException(
                status_code=500, detail="Failed to create server in database"
            )

        # Add server configuration to MCP manager
        if hasattr(request.app.state, "mcp_manager") and request.app.state.mcp_manager:
            try:
                # Build command list
                command_list = [form_data.command] + (form_data.args or [])

                # Build URL for HTTP transport
                server_url = form_data.url
                if form_data.transport == "http" and form_data.port and not server_url:
                    server_url = f"http://localhost:{form_data.port}/sse"

                request.app.state.mcp_manager.add_server_config(
                    name=form_data.name,
                    command=command_list,
                    env=form_data.env,
                    transport=form_data.transport,
                    url=server_url,
                )

                # Start server if it should be active
                if form_data.is_active:
                    success = await request.app.state.mcp_manager.start_server(
                        form_data.name
                    )
                    if not success:
                        log.warning(
                            f"Failed to start server {form_data.name} after creation"
                        )

            except Exception as e:
                log.exception(f"Error adding server to MCP manager: {e}")
                # Don't fail the entire operation, just log the warning

        return {"server": server, "message": "External MCP server created successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating external MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error creating external server: {str(e)}"
        )


@router.get("/servers/external/{server_id}")
async def get_external_server(server_id: str, user=Depends(get_admin_user)):
    """Get a specific external MCP server by ID"""
    try:
        server = MCPServers.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        if server.server_type != "user_created":
            raise HTTPException(
                status_code=400, detail="Server is not an external server"
            )

        # Convert to dict for response
        server_dict = server.model_dump()
        return {"server": server_dict}
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting external MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting external server: {str(e)}"
        )


@router.put("/servers/external/{server_id}")
async def update_external_server(
    request: Request,
    server_id: str,
    form_data: MCPServerUpdateForm,
    user=Depends(get_admin_user),
):
    """Update an external MCP server"""
    try:
        # Get existing server
        existing_server = MCPServers.get_server_by_id(server_id)
        if not existing_server:
            raise HTTPException(status_code=404, detail="Server not found")

        if existing_server.server_type != "user_created":
            raise HTTPException(status_code=400, detail="Cannot update built-in server")

        # Check if new name conflicts with existing servers
        if form_data.name and form_data.name != existing_server.name:
            existing_with_name = MCPServers.get_server_by_name(form_data.name)
            if existing_with_name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Server with name '{form_data.name}' already exists",
                )

        # Build update data (only include non-None values)
        update_data = {}
        for field, value in form_data.model_dump().items():
            if value is not None:
                update_data[field] = value

        # Update server in database
        server = MCPServers.update_server_by_id(server_id, update_data)
        if not server:
            raise HTTPException(status_code=500, detail="Failed to update server")

        # Update MCP manager configuration if server name or config changed
        if hasattr(request.app.state, "mcp_manager") and request.app.state.mcp_manager:
            try:
                old_name = existing_server.name
                new_name = server.name

                # If name changed, we need to remove old config and add new one
                if old_name != new_name:
                    await request.app.state.mcp_manager.stop_server(old_name)
                    # Remove old configuration
                    if old_name in request.app.state.mcp_manager.server_configs:
                        del request.app.state.mcp_manager.server_configs[old_name]

                # Add/update server configuration
                command_list = [server.command] + (server.args or [])
                server_url = server.url
                if server.transport == "http" and server.port and not server_url:
                    server_url = f"http://localhost:{server.port}/sse"

                request.app.state.mcp_manager.add_server_config(
                    name=new_name,
                    command=command_list,
                    env=server.env or {},
                    transport=server.transport,
                    url=server_url,
                )

                # Restart server if it should be active
                if server.is_active:
                    success = await request.app.state.mcp_manager.start_server(new_name)
                    if not success:
                        log.warning(f"Failed to start server {new_name} after update")
                else:
                    await request.app.state.mcp_manager.stop_server(new_name)

            except Exception as e:
                log.exception(f"Error updating server in MCP manager: {e}")

        return {"server": server, "message": "External MCP server updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating external MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error updating external server: {str(e)}"
        )


@router.delete("/servers/external/{server_id}")
async def delete_external_server(
    request: Request, server_id: str, user=Depends(get_admin_user)
):
    """Delete an external MCP server"""
    try:
        # Get existing server
        server = MCPServers.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        if server.server_type != "user_created":
            raise HTTPException(status_code=400, detail="Cannot delete built-in server")

        if not server.is_deletable:
            raise HTTPException(status_code=400, detail="Server is not deletable")

        # Stop and remove from MCP manager first
        if hasattr(request.app.state, "mcp_manager") and request.app.state.mcp_manager:
            try:
                await request.app.state.mcp_manager.stop_server(server.name)
                # Remove configuration
                if server.name in request.app.state.mcp_manager.server_configs:
                    del request.app.state.mcp_manager.server_configs[server.name]
            except Exception as e:
                log.exception(f"Error removing server from MCP manager: {e}")

        # Delete from database
        success = MCPServers.delete_server_by_id(server_id)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to delete server from database"
            )

        return {"message": "External MCP server deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting external MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting external server: {str(e)}"
        )


@router.post("/servers/external/{server_id}/start")
async def start_external_server(
    request: Request, server_id: str, user=Depends(get_admin_user)
):
    """Start an external MCP server"""
    try:
        # Get server from database
        server = MCPServers.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        if server.server_type != "user_created":
            raise HTTPException(
                status_code=400, detail="Cannot start built-in server this way"
            )

        if (
            not hasattr(request.app.state, "mcp_manager")
            or not request.app.state.mcp_manager
        ):
            raise HTTPException(status_code=500, detail="MCP manager not available")

        # Ensure server configuration is in MCP manager
        command_list = [server.command] + (server.args or [])
        server_url = server.url
        if server.transport == "http" and server.port and not server_url:
            server_url = f"http://localhost:{server.port}/sse"

        request.app.state.mcp_manager.add_server_config(
            name=server.name,
            command=command_list,
            env=server.env or {},
            transport=server.transport,
            url=server_url,
        )

        # Start the server
        success = await request.app.state.mcp_manager.start_server(server.name)
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to start server {server.name}"
            )

        # Update server status in database
        MCPServers.update_server_status(server_id, True)

        return {"message": f"Server {server.name} started successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error starting external MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error starting external server: {str(e)}"
        )


@router.post("/servers/external/{server_id}/stop")
async def stop_external_server(
    request: Request, server_id: str, user=Depends(get_admin_user)
):
    """Stop an external MCP server"""
    try:
        # Get server from database
        server = MCPServers.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        if server.server_type != "user_created":
            raise HTTPException(
                status_code=400, detail="Cannot stop built-in server this way"
            )

        if (
            not hasattr(request.app.state, "mcp_manager")
            or not request.app.state.mcp_manager
        ):
            raise HTTPException(status_code=500, detail="MCP manager not available")

        # Stop the server
        success = await request.app.state.mcp_manager.stop_server(server.name)
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to stop server {server.name}"
            )

        # Update server status in database
        MCPServers.update_server_status(server_id, False)

        return {"message": f"Server {server.name} stopped successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error stopping external MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error stopping external server: {str(e)}"
        )


@router.post("/servers/external/{server_id}/restart")
async def restart_external_server(
    request: Request, server_id: str, user=Depends(get_admin_user)
):
    """Restart an external MCP server"""
    try:
        # Get server from database
        server = MCPServers.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        if server.server_type != "user_created":
            raise HTTPException(
                status_code=400, detail="Cannot restart built-in server this way"
            )

        if (
            not hasattr(request.app.state, "mcp_manager")
            or not request.app.state.mcp_manager
        ):
            raise HTTPException(status_code=500, detail="MCP manager not available")

        # Restart the server
        success = await request.app.state.mcp_manager.restart_server(server.name)
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to restart server {server.name}"
            )

        # Update server status in database
        MCPServers.update_server_status(server_id, True)

        return {"message": f"Server {server.name} restarted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error restarting external MCP server: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error restarting external server: {str(e)}"
        )
