import logging
import asyncio
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from open_webui.models.mcp_servers import (
    MCPServers,
    MCPServerStatus,
    MCPServerUpdateForm,
)
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_access
from open_webui.utils.mcp_client_official import mcp_manager
from open_webui.utils.mcp.validation import validate_server_connected
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


class MCPToolCallRequest(BaseModel):
    server_id: str
    tool_name: str
    arguments: Dict[str, Any]
    stream: bool = True


class MCPToolListRequest(BaseModel):
    server_id: str


############################
# MCP Tool Execution
############################


@router.get("/servers/{server_id}/tools")
async def get_mcp_server_tools(server_id: str, user=Depends(get_verified_user)):
    """Get available tools from an MCP server"""
    server = validate_server_connected(server_id, user)

    # Get client
    client = mcp_manager.get_client(server_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found"
        )

    try:
        tools = await client.get_available_tools()
        return {"tools": tools}
    except Exception as e:
        log.error(f"Failed to get tools from MCP server {server_id}: {e}")
        
        # Check for encryption mismatch errors
        from open_webui.utils.mcp.exceptions import MCPEncryptionMismatchError
        if isinstance(e, MCPEncryptionMismatchError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_type": "encryption_mismatch",
                    "message": str(e),
                    "server_id": e.server_id,
                    "server_name": e.server_name,
                    "instructions": "The encryption key for this MCP server is invalid due to mismatch encryption key. Please remove and add the server again with the correct encryption key."
                }
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tools",
        )


@router.post("/servers/{server_id}/tools/{tool_name}/call")
async def call_mcp_tool(
    server_id: str,
    tool_name: str,
    request: MCPToolCallRequest,
    user=Depends(get_verified_user),
):
    """Call an MCP tool with HTTP streaming response"""
    server = validate_server_connected(server_id, user)

    # Get client
    client = mcp_manager.get_client(server_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found"
        )

    if request.stream:
        return StreamingResponse(
            stream_mcp_tool_call(client, tool_name, request.arguments, user.id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    else:
        try:
            result = await client.call_tool(tool_name, request.arguments)
            return {"result": result}
        except Exception as e:
            log.error(f"Failed to call MCP tool {tool_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tool execution failed: {str(e)}",
            )


async def stream_mcp_tool_call(
    client, tool_name: str, arguments: Dict[str, Any], user_id: str
):
    """Stream MCP tool execution results via HTTP streaming"""
    try:
        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'tool': tool_name, 'arguments': arguments})}\n\n"

        # Execute the tool
        try:
            result = await client.call_tool(tool_name, arguments)

            # Send progress events if the result contains streaming data
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list):
                    for item in content:
                        yield f"data: {json.dumps({'type': 'progress', 'content': item})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'progress', 'content': content})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"

        except Exception as tool_error:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(tool_error)})}\n\n"

    except Exception as e:
        log.error(f"Error in streaming MCP tool call: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Streaming failed'})}\n\n"

    finally:
        # Send done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/tools/call")
async def call_mcp_tool_by_request(
    request: MCPToolCallRequest, user=Depends(get_verified_user)
):
    """Call an MCP tool via request body (alternative endpoint)"""
    return await call_mcp_tool(request.server_id, request.tool_name, request, user)


############################
# MCP Server Status and Monitoring
############################


@router.get("/servers/status")
async def get_mcp_servers_status(user=Depends(get_verified_user)):
    """Get status of all accessible MCP servers"""
    servers = MCPServers.get_mcp_servers_by_user_id(user.id)

    status_info = []
    for server in servers:
        is_connected = server.status == MCPServerStatus.connected

        status_info.append(
            {
                "id": server.id,
                "name": server.name,
                "status": server.status,
                "is_connected": is_connected,
                "last_connected_at": server.last_connected_at,
                "error_message": server.error_message,
                # available_tools no longer stored; count is unknown without a live query
                "tools_count": None,
            }
        )

    return {"servers": status_info}


@router.post("/servers/{server_id}/reconnect")
async def reconnect_mcp_server(server_id: str, user=Depends(get_verified_user)):
    """Reconnect to an MCP server"""
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found"
        )

    # Check access permissions
    if server.user_id != user.id and not has_access(
        user.id, "write", server.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        # Disconnect if already connected
        await mcp_manager.disconnect_server(server_id)

        # Use the same working pattern as other connection methods
        result = await mcp_manager.test_server_connection(server)

        if result["success"]:
            # Update server with available tools from the test result
            tools = result.get("tools", [])
            MCPServers.update_mcp_server_by_id(
                server_id, MCPServerUpdateForm(available_tools=tools), server.user_id
            )

            MCPServers.update_mcp_server_status(server_id, MCPServerStatus.connected)
            return {"success": True, "message": "Reconnected successfully"}
        else:
            MCPServers.update_mcp_server_status(
                server_id,
                MCPServerStatus.error,
                result.get("message", "Failed to reconnect"),
            )
            return {
                "success": False,
                "message": result.get("message", "Reconnection failed"),
            }

    except Exception as e:
        log.error(f"Error reconnecting to MCP server {server_id}: {e}")
        MCPServers.update_mcp_server_status(server_id, MCPServerStatus.ERROR, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reconnection failed",
        )
