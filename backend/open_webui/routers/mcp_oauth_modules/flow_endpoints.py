"""
MCP OAuth flow initiation endpoints.
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.models.mcp_servers import MCPServers
from open_webui.utils.mcp.auth import mcp_oauth_manager
from open_webui.config import WEBUI_URL
from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)
router = APIRouter()


async def create_permanent_server_from_temp(
    temp_server_id: str, server_name: str, mcp_server_url: str, headers: dict, user_id: str
) -> str:
    """Create a permanent MCP server from temporary data."""
    try:
        from open_webui.models.mcp_servers import MCPServerForm
        
        create_form = MCPServerForm(
            name=server_name,
            http_url=mcp_server_url,
            headers=headers,
            access_control={},
        )
        
        server = MCPServers.insert_new_mcp_server(user_id, create_form)
        log.info(f"Created permanent MCP server {server.id} from temp {temp_server_id}")
        return server.id
        
    except Exception as e:
        log.error(f"Failed to create permanent server from temp {temp_server_id}: {e}")
        raise


@router.post("/oauth/start-with-discovery")
async def start_oauth_flow_with_discovery(
    request: Request, user: UserModel = Depends(get_verified_user)
):
    """Start OAuth flow with server discovery for new servers."""
    
    
    
    try:
        body = await request.json()
        server_name = body.get("serverName", "").strip()
        mcp_server_url = body.get("mcpServerUrl", "").strip()
        headers = body.get("headers", {})

        if not server_name:
            raise HTTPException(400, "serverName is required")
        if not mcp_server_url:
            raise HTTPException(400, "mcpServerUrl is required")

        # Create permanent server first
        server_id = await create_permanent_server_from_temp(
            "temp_new", server_name, mcp_server_url, headers, user.id
        )

        # Use configured WEBUI_URL for proper HTTPS support
        base_url = str(WEBUI_URL).rstrip("/")

        # Try OAuth discovery
        result = await mcp_oauth_manager.discover_oauth_from_mcp_server(
            server_id=server_id,
            mcp_server_url=mcp_server_url,
            base_url=base_url,
            user_id=user.id,
        )

        if result["success"]:
            log.info(f"OAuth flow started with discovery for new server {server_name}")
            return {
                **result,
                "server_id": server_id,  # Return the permanent server ID
                "message": "OAuth flow started successfully"
            }
        else:
            # Clean up server if OAuth discovery failed
            try:
                MCPServers.delete_mcp_server_by_id(server_id, user.id)
            except Exception as cleanup_error:
                log.warning(f"Failed to cleanup server {server_id}: {cleanup_error}")
            
            return result

    except Exception as e:
        log.error(f"Error starting OAuth flow with discovery: {e}")

       

        # Check if this is a "needs manual config" error
        error_str = str(e)
        is_manual_config_needed = (
            "does not support Dynamic Client Registration" in error_str
            or "needs_manual_config" in error_str
            or hasattr(e, 'needs_manual_config')
        )
        
        if is_manual_config_needed:
            # Provide a clear, actionable error message
            server_info = "This MCP server"
            if "github" in mcp_server_url.lower():
                server_info = "GitHub's MCP server"
            elif "neon" in mcp_server_url.lower():
                server_info = "Neon's MCP server"
                
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "OAuth configuration required",
                    "message": f"{server_info} requires OAuth authentication but doesn't support automatic setup.\n\nNext steps:\n• Contact your administrator to set up OAuth client credentials\n• Or check if the server supports API key authentication instead",
                    "needs_manual_config": True,
                    "show_alternatives": True,
                    "server_type": "oauth_manual",
                },
            )
        else:
            raise HTTPException(500, f"OAuth setup failed: {str(e)}")


@router.post("/{server_id}/oauth/start")
async def start_oauth_flow(
    server_id: str, request: Request, user=Depends(get_verified_user)
):
    """Start OAuth flow for an existing server with pre-configured OAuth settings."""

    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    if not server.oauth_config:
        raise HTTPException(400, "OAuth not configured for this server")

    try:
        # Use configured WEBUI_URL for proper HTTPS support
        base_url = str(WEBUI_URL).rstrip("/")
        result = await mcp_oauth_manager.start_oauth_flow(
            server_id=server_id,
            user_id=user.id,
            base_url=base_url,
        )

        log.info(f"OAuth flow started for server {server.name} by user {user.email}")
        return result

    except Exception as e:
        log.error(f"Error starting OAuth flow for server {server_id}: {e}")
        raise HTTPException(500, f"Failed to start OAuth flow: {str(e)}")


@router.post("/{server_id}/oauth/direct-start")
async def start_direct_oauth_flow(
    server_id: str, request: Request, user=Depends(get_verified_user)
):
    """Start direct OAuth flow bypassing MCP server discovery."""
    
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        body = await request.json()
        issuer_url = body.get("issuer_url", "").strip()
        client_id = body.get("client_id", "").strip()
        scopes = body.get("scopes", [])
        resource = body.get("resource", "").strip() or None  # Optional resource parameter
        
        if not issuer_url:
            raise HTTPException(400, "issuer_url is required for direct OAuth flow")
        if not client_id:
            raise HTTPException(400, "client_id is required for direct OAuth flow")
        
        # Use configured WEBUI_URL for proper HTTPS support
        base_url = str(WEBUI_URL).rstrip("/")
        
        result = await mcp_oauth_manager.initiate_direct_oauth_flow(
            server_id=server_id,
            issuer_url=issuer_url,
            client_id=client_id,
            scopes=scopes,
            base_url=base_url,
            user_id=user.id,
            resource=resource
        )
        
        if result["success"]:
            log.info(f"Direct OAuth flow initiated for server {server.name} by user {user.email}")
        
        return result
        
    except Exception as e:
        log.error(f"Error starting direct OAuth flow for server {server_id}: {e}")
        raise HTTPException(500, f"Failed to start direct OAuth flow: {str(e)}")


@router.post("/{server_id}/oauth/unified-start")
async def start_unified_oauth_flow(
    server_id: str, request: Request, user=Depends(get_verified_user)
):
    """
    Unified OAuth flow that tries auto-discovery first, then direct OAuth if configured.
    
    This endpoint replaces the need for separate discovery and direct OAuth endpoints.
    It automatically detects what the MCP server supports and uses the appropriate flow.
    """
    
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        body = await request.json()
        
        # Optional direct OAuth parameters (for fallback)
        direct_oauth_issuer = body.get("issuer_url", "").strip() or None
        direct_oauth_client_id = body.get("client_id", "").strip() or None
        direct_oauth_scopes = body.get("scopes", [])
        direct_oauth_resource = body.get("resource", "").strip() or None
        
        # Use configured WEBUI_URL for proper HTTPS support
        base_url = str(WEBUI_URL).rstrip("/")
        
        # Use the unified OAuth discovery method
        result = await mcp_oauth_manager.discover_and_initiate_oauth(
            server_id=server_id,
            mcp_server_url=server.http_url,
            base_url=base_url,
            user_id=user.id,
            direct_oauth_issuer=direct_oauth_issuer,
            direct_oauth_client_id=direct_oauth_client_id,
            direct_oauth_scopes=direct_oauth_scopes,
            direct_oauth_resource=direct_oauth_resource
        )
        
        if result["success"]:
            log.info(f"Unified OAuth flow initiated for server {server.name} by user {user.email}")
        
        return result
        
    except Exception as e:
        log.error(f"Error in unified OAuth flow for server {server_id}: {e}")
        raise HTTPException(500, f"Failed to start OAuth flow: {str(e)}") 