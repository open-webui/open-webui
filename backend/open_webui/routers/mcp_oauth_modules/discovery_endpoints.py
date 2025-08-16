"""
MCP OAuth discovery and configuration endpoints.
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.models.mcp_servers import MCPServers
from open_webui.utils.mcp.auth import mcp_oauth_manager
from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{server_id}/oauth/discover-from-mcp")
async def discover_oauth_from_mcp_server(
    server_id: str, request: Request, user=Depends(get_verified_user)
):
    """Discover OAuth configuration from MCP server using auto-discovery."""
    
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        body = await request.json()
        mcp_server_url = body.get("mcp_server_url", "").strip()

        if not mcp_server_url:
            raise HTTPException(400, "mcp_server_url is required")

        # Use configured WEBUI_URL instead of request.base_url for proper HTTPS support
        base_url = str(request.app.state.config.WEBUI_URL).rstrip("/")

        result = await mcp_oauth_manager.discover_oauth_from_mcp_server(
            server_id=server_id,
            mcp_server_url=mcp_server_url,
            base_url=base_url,
            user_id=user.id,
        )

        if result["success"]:
            log.info(f"OAuth discovery completed for server {server.name} by user {user.email}")

        return result

    except Exception as e:
        log.error(f"Error in MCP OAuth discovery for server {server_id}: {e}")
        raise HTTPException(500, f"MCP OAuth discovery failed: {str(e)}")


@router.post("/{server_id}/oauth/discover")
async def discover_oauth_configuration(
    server_id: str,
    request: Request,
    user=Depends(get_verified_user),
    issuer_url: str = None,
    scopes: str = None,
    use_dcr: bool = True,
):
    """Discover OAuth configuration using metadata discovery and optionally DCR"""

    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    if not issuer_url:
        raise HTTPException(400, "issuer_url is required")

    try:
        scopes_list = scopes.split() if scopes else []
        # Use configured WEBUI_URL instead of request.base_url for proper HTTPS support
        base_url = str(request.app.state.config.WEBUI_URL).rstrip("/")

        result = await mcp_oauth_manager.discover_and_configure_oauth(
            server_id=server_id,
            issuer_url=issuer_url,
            scopes=scopes_list,
            use_dcr=use_dcr,
            base_url=base_url,
        )

        if result["success"]:
            log.info(
                f"OAuth discovery completed for server {server.name} by user {user.email}"
            )

        return result

    except Exception as e:
        log.error(f"Error in OAuth discovery for server {server_id}: {e}")
        raise HTTPException(500, f"OAuth discovery failed: {str(e)}")


@router.post("/{server_id}/oauth/configure-manual")
async def configure_manual_oauth(
    server_id: str, request: Request, user=Depends(get_verified_user)
):
    """
    Configure manual OAuth settings for an MCP server.
    
    This endpoint allows users to manually configure OAuth settings through the frontend's
    Advanced Configuration section, supporting all the manual fields like issuer_url,
    authorize_url, token_url, client_id, client_secret, etc.
    """
    
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        body = await request.json()
        
        # Extract manual OAuth configuration from request
        oauth_config = {
            "enabled": True,
            "config_method": body.get("config_method", "manual"),
            # OAuth 2.1 endpoints
            "issuer_url": body.get("issuer_url", "").strip() or None,
            "authorize_url": body.get("authorize_url", "").strip() or None,
            "token_url": body.get("token_url", "").strip() or None,
            # Client credentials
            "client_id": body.get("client_id", "").strip() or None,
            "client_secret": body.get("client_secret", "").strip() or None,
            # OAuth parameters
            "scopes": body.get("scopes", []),
            "use_pkce": body.get("use_pkce", True),
            "audience": body.get("audience", "").strip() or None,
            "resource": body.get("resource", "").strip() or None,
        }
        
        # Validate required fields for manual configuration
        if oauth_config["config_method"] == "manual":
            if not oauth_config["client_id"]:
                raise HTTPException(400, "client_id is required for manual OAuth configuration")
            
            # For manual config, we need either full endpoints or issuer_url for discovery
            has_endpoints = oauth_config["authorize_url"] and oauth_config["token_url"]
            has_issuer = oauth_config["issuer_url"]
            
            if not (has_endpoints or has_issuer):
                raise HTTPException(400, "Either (authorize_url + token_url) or issuer_url is required for manual OAuth configuration")
        
        # Update server with OAuth configuration
        from open_webui.models.mcp_servers import MCPServerUpdateForm
        
        MCPServers.update_mcp_server_by_id(
            server_id,
            MCPServerUpdateForm(oauth_config=oauth_config),
            user.id
        )
        
        log.info(f"Manual OAuth configuration saved for server {server.name} by user {user.email}")
        
        return {
            "success": True,
            "message": "Manual OAuth configuration saved successfully",
            "oauth_config": oauth_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error saving manual OAuth configuration for server {server_id}: {e}")
        raise HTTPException(500, f"Failed to save OAuth configuration: {str(e)}") 