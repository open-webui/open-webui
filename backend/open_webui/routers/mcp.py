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
    builtin_info = await get_builtin_servers(request, user)
    
    return {
        "ENABLE_MCP_API": get_config_value(request, "ENABLE_MCP_API", False),
        "MCP_BASE_URLS": get_config_value(request, "MCP_BASE_URLS", []),
        "MCP_API_CONFIGS": get_config_value(request, "MCP_API_CONFIGS", {}),
        "BUILTIN_SERVERS": builtin_info["servers"]
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
    filtered_configs = {
        key: value
        for key, value in api_configs.items()
        if key in keys
    }
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
        if hasattr(request.app.state, 'mcp_manager') and request.app.state.mcp_manager:
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
                            "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema,
                            "mcp_server_url": url,
                            "mcp_server_idx": idx
                        }
                        
                        if prefix_id:
                            tool_dict["name"] = f"{prefix_id}.{tool_dict['name']}"
                        
                        all_tools.append(tool_dict)
                        
                except Exception as e:
                    log.exception(f"Error getting tools from external MCP server {url}: {e}")
                    continue
                    
    except Exception as e:
        log.exception(f"Error getting external MCP tools: {e}")
    
    return {"tools": all_tools}


@router.get("/tools")
async def get_mcp_tools(
    request: Request, 
    url_idx: Optional[int] = None,
    user=Depends(get_verified_user)
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
                    "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema,
                    "mcp_server_url": url,
                    "mcp_server_idx": url_idx
                }
                
                if prefix_id:
                    tool_dict["name"] = f"{prefix_id}.{tool_dict['name']}"
                
                tools_list.append(tool_dict)
            
            return {"tools": tools_list}
        
        except Exception as e:
            log.exception(f"Error getting tools from external MCP server {url}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting tools from external MCP server: {str(e)}"
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
    request: Request,
    form_data: MCPToolCallForm,
    user=Depends(get_verified_user)
):
    """Call a tool on FastMCP manager"""
    tool_name = form_data.name
    arguments = form_data.arguments or {}
    
    try:
        if hasattr(request.app.state, 'mcp_manager') and request.app.state.mcp_manager:
            # Find which server has this tool
            server_name = None
            server_names = request.app.state.mcp_manager.get_running_servers()
            
            # Handle prefixed tool names (e.g., "mcp_server_1/search_news" -> "search_news")
            clean_tool_name = tool_name
            if '/' in tool_name:
                clean_tool_name = tool_name.split('/')[-1]
            elif '.' in tool_name:
                clean_tool_name = tool_name.split('.')[-1]
            
            log.info(f"Looking for tool '{tool_name}' (clean name: '{clean_tool_name}') across servers: {server_names}")
            
            for name in server_names:
                try:
                    # Get tools from this server to check if it has our tool
                    tools = await request.app.state.mcp_manager.get_tools_from_server(name)
                    tool_names = [tool.get('name', '') for tool in tools]
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
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found on any available MCP server")
            
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
    if hasattr(request.app.state, 'mcp_manager') and request.app.state.mcp_manager:
        server_names = request.app.state.mcp_manager.get_server_names()
        servers = []
        
        for name in server_names:
            status = request.app.state.mcp_manager.get_server_status(name)
            config = request.app.state.mcp_manager.server_configs.get(name, {})
            
            # Get tools count for this server
            tools_count = 0
            try:
                tools = await request.app.state.mcp_manager.get_tools_from_server(name)
                tools_count = len(tools)
            except Exception:
                pass
            
            servers.append({
                "name": name,
                "display_name": name.replace('_', ' ').title(),
                "status": status,
                "transport": config.get('transport', 'stdio'),
                "tools_count": tools_count,
                "description": get_server_description(name)
            })
        
        return {"servers": servers}
    else:
        return {"servers": []}

def get_server_description(name: str) -> str:
    """Get description for built-in servers"""
    descriptions = {
        "time_server": "Provides current time and timezone information",
        "news_server": "Fetches latest news headlines and articles from NewsAPI"
    }
    return descriptions.get(name, f"Built-in MCP server: {name}")

@router.post("/servers/builtin/{server_name}/restart")
async def restart_builtin_server(
    request: Request, 
    server_name: str, 
    user=Depends(get_admin_user)
):
    """Restart a built-in MCP server"""
    if hasattr(request.app.state, 'mcp_manager') and request.app.state.mcp_manager:
        try:
            success = await request.app.state.mcp_manager.restart_server(server_name)
            if success:
                return {"status": "success", "message": f"Server {server_name} restarted successfully"}
            else:
                return {"status": "error", "message": f"Failed to restart server {server_name}"}
        except Exception as e:
            log.exception(f"Error restarting server {server_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Error restarting server: {str(e)}")
    else:
        raise HTTPException(status_code=500, detail="MCP manager not available")