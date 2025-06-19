"""
CrewAI MCP Router for Open WebUI
API endpoints for CrewAI integration with MCP servers
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user, get_verified_user

# Add the backend directory to the path to import crew_mcp_integration
backend_dir = Path(__file__).parent.parent.parent
sys.path.append(str(backend_dir))

try:
    from crew_mcp_integration import CrewMCPManager
except ImportError as e:
    logging.error(f"Failed to import CrewMCPManager: {e}")
    CrewMCPManager = None

log = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class CrewMCPQuery(BaseModel):
    query: str
    llm_config: Optional[Dict[str, Any]] = None


class CrewMCPResponse(BaseModel):
    result: str
    tools_used: list
    success: bool
    error: Optional[str] = None


class MCPToolsResponse(BaseModel):
    tools: list
    count: int


# Global manager instance
crew_mcp_manager = None
if CrewMCPManager:
    try:
        crew_mcp_manager = CrewMCPManager()
    except Exception as e:
        logging.error(f"Failed to initialize CrewMCPManager: {e}")


@router.get("/tools")
async def get_mcp_tools(user=Depends(get_verified_user)) -> MCPToolsResponse:
    """Get available MCP tools"""
    if not crew_mcp_manager:
        raise HTTPException(
            status_code=503,
            detail="CrewAI MCP integration not available. Check dependencies.",
        )

    try:
        tools = crew_mcp_manager.get_available_tools()
        return MCPToolsResponse(tools=tools, count=len(tools))
    except Exception as e:
        log.exception(f"Error getting MCP tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def run_crew_query(
    request: CrewMCPQuery, user=Depends(get_verified_user)
) -> CrewMCPResponse:
    """Run a CrewAI query with MCP tools"""
    if not crew_mcp_manager:
        return CrewMCPResponse(
            result="",
            tools_used=[],
            success=False,
            error="CrewAI MCP integration not available",
        )

    try:
        log.info(f"Running CrewAI query for user {user.id}: {request.query}")

        # Get available tools first
        tools = crew_mcp_manager.get_available_tools()
        if not tools:
            raise HTTPException(
                status_code=503,
                detail="No MCP tools available. Check MCP server configuration.",
            )

        # Intelligently route to appropriate crew based on query content
        query_lower = request.query.lower()
        news_keywords = ["news", "headlines", "article", "breaking", "latest news", "current events", "newsdesk"]
        time_keywords = ["time", "clock", "timezone", "date", "hour", "minute", "when is"]
        multi_keywords = ["and", "also", "both", "together", "combine", "plus"]
        
        # Check if query mentions both domains or asks for combined information
        is_news_query = any(keyword in query_lower for keyword in news_keywords)
        is_time_query = any(keyword in query_lower for keyword in time_keywords)
        is_multi_query = any(keyword in query_lower for keyword in multi_keywords)
        
        # Use multi-server crew if query involves multiple domains or explicitly requests combined info
        if (is_news_query and is_time_query) or (is_multi_query and (is_news_query or is_time_query)):
            log.info("Routing to multi-server crew for comprehensive query")
            result = crew_mcp_manager.run_multi_server_crew(request.query)
            used_tools = [tool["name"] for tool in tools]  # All tools potentially used
        elif is_news_query and not is_time_query:
            log.info("Routing to news crew based on query content")
            result = crew_mcp_manager.run_news_crew(request.query)
            used_tools = [tool["name"] for tool in tools if tool.get("server") == "news_server"]
        else:
            log.info("Routing to time crew based on query content")
            result = crew_mcp_manager.run_time_crew(request.query)
            used_tools = [tool["name"] for tool in tools if tool.get("server") == "time_server"]

        return CrewMCPResponse(
            result=result, tools_used=used_tools, success=True
        )

    except Exception as e:
        log.exception(f"Error running CrewAI query: {e}")
        return CrewMCPResponse(result="", tools_used=[], success=False, error=str(e))


@router.post("/multi")
async def run_multi_server_crew_query(
    request: CrewMCPQuery, user=Depends(get_verified_user)
) -> CrewMCPResponse:
    """Run a CrewAI query using ALL available MCP servers and tools simultaneously"""
    if not crew_mcp_manager:
        return CrewMCPResponse(
            result="",
            tools_used=[],
            success=False,
            error="CrewAI MCP integration not available",
        )

    try:
        log.info(f"Running CrewAI multi-server query for user {user.id}: {request.query}")

        # Get available tools first
        tools = crew_mcp_manager.get_available_tools()
        if not tools:
            raise HTTPException(
                status_code=503,
                detail="No MCP tools available. Check MCP server configuration.",
            )

        # Run the multi-server crew that can use ALL available tools
        result = crew_mcp_manager.run_multi_server_crew(request.query)

        return CrewMCPResponse(
            result=result, tools_used=[tool["name"] for tool in tools], success=True
        )

    except Exception as e:
        log.exception(f"Error running CrewAI multi-server query: {e}")
        return CrewMCPResponse(result="", tools_used=[], success=False, error=str(e))


@router.get("/status")
async def get_crew_mcp_status(user=Depends(get_verified_user)) -> dict:
    """Get CrewAI MCP integration status"""
    if not crew_mcp_manager:
        return {
            "status": "unavailable",
            "error": "CrewAI MCP integration not available",
            "tools_count": 0,
            "servers": {},
            "azure_config_present": False,
        }

    try:
        tools = crew_mcp_manager.get_available_tools()
        available_servers = crew_mcp_manager.get_available_servers()
        
        # Get server details
        server_details = {}
        for server_name, server_path in available_servers.items():
            server_tools = [tool for tool in tools if tool.get("server") == server_name]
            server_details[server_name] = {
                "available": True,
                "path": str(server_path),
                "tool_count": len(server_tools),
                "tools": [tool["name"] for tool in server_tools]
            }
        
        return {
            "status": "active" if tools else "inactive",
            "tools_count": len(tools),
            "servers": server_details,
            "azure_config_present": bool(crew_mcp_manager.azure_config.api_key),
            "multi_server_support": True,
        }
    except Exception as e:
        log.exception(f"Error getting CrewAI MCP status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "tools_count": 0,
            "servers": {},
            "azure_config_present": False,
        }
