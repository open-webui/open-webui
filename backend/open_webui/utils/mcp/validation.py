"""
Common MCP server validation utilities
"""
import logging
from typing import Optional
from fastapi import HTTPException, status

from open_webui.models.mcp_servers import MCPServers, MCPServerStatus
from open_webui.models.users import UserModel
from open_webui.utils.access_control import has_access
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)


def validate_server_access(
    server_id: str, user: UserModel, permission: str = "read"
) -> Optional[object]:
    """
    Validate server existence and user access permissions.
    
    Args:
        server_id: The MCP server ID
        user: The user requesting access
        permission: Required permission level ("read", "write", "execute")
        
    Returns:
        The server object if validation passes
        
    Raises:
        HTTPException: If server not found or access denied
    """
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="MCP server not found"
        )

    # Check access permissions
    if server.user_id != user.id and not has_access(
        user.id, permission, server.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return server


def validate_server_connected(server_id: str, user: UserModel) -> object:
    """
    Validate server exists, user has access, and server is connected.
    
    Args:
        server_id: The MCP server ID
        user: The user requesting access
        
    Returns:
        The server object if validation passes
        
    Raises:
        HTTPException: If server not found, access denied, or not connected
    """
    server = validate_server_access(server_id, user, "execute")
    
    # Check if server is connected
    if server.status != MCPServerStatus.connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP server is not connected",
        )
    
    return server


def validate_servers_batch_access(
    server_ids: list[str], user: UserModel, permission: str = "read"
) -> list[object]:
    """
    Validate multiple servers for batch operations.
    
    Args:
        server_ids: List of MCP server IDs
        user: The user requesting access
        permission: Required permission level
        
    Returns:
        List of accessible server objects
        
    Raises:
        HTTPException: If no accessible servers found
    """
    accessible_servers = []
    
    for server_id in server_ids:
        try:
            server = validate_server_access(server_id, user, permission)
            accessible_servers.append(server)
        except HTTPException:
            # Skip inaccessible servers in batch operations
            continue
    
    if not accessible_servers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No accessible servers found in the provided list",
        )
    
    return accessible_servers