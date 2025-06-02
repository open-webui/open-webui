"""
MCP (Model Context Protocol) Router

This module handles MCP server connections and tool discovery/execution using FastMCP.
It follows the same patterns as the Ollama and OpenAI routers for consistency.
"""

import logging
from typing import Optional, Dict, List, Any

from fastmcp.client import Client
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.mcp_manager import mcp_manager

log = logging.getLogger(__name__)

##########################################
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
            detail=f"MCP: Unable to connect to server at {url}. Please check the URL and try again."
        )





def get_mcp_api_config(idx: int, url: str, configs: Dict) -> Dict:
    """Get API configuration for MCP server"""
    return configs.get(str(idx), configs.get(url, {}))


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
    user=Depends(get_admin_user)
):
    """Verify connection to MCP server using FastMCP client"""
    url = form_data.url
    
    # Special case: if URL is empty or 'built-in', verify FastMCP manager
    if not url or url.lower() in ['built-in', 'fastmcp', 'local']:
        try:
            if hasattr(request.app.state, 'mcp_manager') and request.app.state.mcp_manager:
                tools = await request.app.state.mcp_manager.get_all_tools()
                return {
                    "status": "connected",
                    "message": "FastMCP manager is working",
                    "tools_count": len(tools),
                    "capabilities": {"tools": True}
                }
            else:
                return {
                    "status": "failed",
                    "error": "FastMCP manager not initialized",
                    "message": "FastMCP manager not available"
                }
        except Exception as e:
            log.exception(f"FastMCP manager verification failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "message": "FastMCP manager verification failed"
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
                "capabilities": {"tools": True}
            }
            
    except Exception as e:
        log.exception(f"MCP connection verification failed for {url}: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "message": "Connection verification failed"
        }


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    """Get MCP configuration"""
    return {
        "ENABLE_MCP_API": request.app.state.config.ENABLE_MCP_API,
        "MCP_BASE_URLS": request.app.state.config.MCP_BASE_URLS,
        "MCP_API_CONFIGS": request.app.state.config.MCP_API_CONFIGS,
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
    request.app.state.config.ENABLE_MCP_API = form_data.ENABLE_MCP_API
    request.app.state.config.MCP_BASE_URLS = form_data.MCP_BASE_URLS
    request.app.state.config.MCP_API_CONFIGS = form_data.MCP_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.MCP_BASE_URLS))))
    request.app.state.config.MCP_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.MCP_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_MCP_API": request.app.state.config.ENABLE_MCP_API,
        "MCP_BASE_URLS": request.app.state.config.MCP_BASE_URLS,
        "MCP_API_CONFIGS": request.app.state.config.MCP_API_CONFIGS,
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
    """Get all tools from built-in FastMCP manager"""
    all_tools = []
    
    # Get tools from built-in FastMCP manager
    try:
        if hasattr(request.app.state, 'mcp_manager') and request.app.state.mcp_manager:
            fastmcp_tools = await request.app.state.mcp_manager.get_all_tools()
            all_tools.extend(fastmcp_tools)
    except Exception as e:
        log.exception(f"Error getting tools from FastMCP manager: {e}")
    
    return {"tools": all_tools}


@router.get("/tools")
async def get_mcp_tools(
    request: Request, 
    url_idx: Optional[int] = None,
    user=Depends(get_verified_user)
):
    """Get available tools from MCP servers"""
    if url_idx is not None:
        # Get tools from specific MCP server
        if url_idx >= len(request.app.state.config.MCP_BASE_URLS):
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        url = request.app.state.config.MCP_BASE_URLS[url_idx]
        api_config = get_mcp_api_config(
            url_idx, url, request.app.state.config.MCP_API_CONFIGS
        )
        
        try:
            tools = await get_tools_from_mcp_server(url, url_idx, api_config)
            
            # Add server info and prefix if configured
            prefix_id = api_config.get("prefix_id", None)
            tools_list = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema,
                    "mcp_server_url": url,
                    "mcp_server_idx": url_idx
                }
                
                if prefix_id:
                    tool_dict["name"] = f"{prefix_id}.{tool_dict['name']}"
                
                tools_list.append(tool_dict)
            
            return {"tools": tools_list}
        
        except Exception as e:
            log.exception(f"Error getting tools from MCP server {url}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting tools from MCP server: {str(e)}"
            )
    else:
        # Get tools from all MCP servers
        result = await get_all_mcp_tools(request)
        return result


class MCPToolCallForm(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None
    server_idx: Optional[int] = None


@router.post("/tools/call")
async def call_mcp_tool(
    request: Request,
    form_data: MCPToolCallForm,
    user=Depends(get_verified_user)
):
    """Call a tool on FastMCP manager"""
    tool_name = form_data.name
    arguments = form_data.arguments or {}
    
    try:
        if hasattr(request.app.state, 'mcp_manager') and request.app.state.mcp_manager:
            # Get all available servers from the manager
            servers = request.app.state.mcp_manager.servers
            if not servers:
                raise HTTPException(status_code=500, detail="No MCP servers available")
            
            # Use the first available server (could be made configurable)
            server_name = next(iter(servers.keys()))
            result = await request.app.state.mcp_manager.call_tool(server_name, tool_name, arguments)
            
            # Handle FastMCP result format
            if isinstance(result, list) and len(result) > 0:
                # FastMCP returns a list of content objects
                content = []
                for item in result:
                    if hasattr(item, 'text'):
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
        raise HTTPException(
            status_code=500,
            detail=f"Error calling MCP tool: {str(e)}"
        )


class UrlForm(BaseModel):
    urls: List[str]


@router.get("/urls")
async def get_urls(request: Request, user=Depends(get_admin_user)):
    """Get MCP server URLs"""
    return {"MCP_BASE_URLS": request.app.state.config.MCP_BASE_URLS}


@router.post("/urls/update")
async def update_urls(
    request: Request, form_data: UrlForm, user=Depends(get_admin_user)
):
    """Update MCP server URLs"""
    urls = [url.strip() for url in form_data.urls if url.strip()]
    request.app.state.config.MCP_BASE_URLS = urls
    
    return {"MCP_BASE_URLS": request.app.state.config.MCP_BASE_URLS}