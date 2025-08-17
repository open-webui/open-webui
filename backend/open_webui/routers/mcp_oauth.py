import logging
import urllib.parse
import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from starlette.responses import RedirectResponse

from open_webui.models.mcp_servers import MCPServers, MCPServerForm
from open_webui.utils.mcp_client_official import mcp_oauth_manager
from open_webui.utils.auth import get_verified_user
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import UserModel
from open_webui.config import WEBUI_URL
from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


async def create_permanent_server_from_temp(
    temp_server_id: str, user_id: str
) -> Optional[str]:
    """Create a permanent MCP server from temporary server data after successful OAuth"""

    try:
        # Get temporary server data from Redis
        redis_key = f"open-webui:temp_mcp_server:{temp_server_id}"
        temp_data_json = mcp_oauth_manager.redis_client.get(redis_key)

        if not temp_data_json:
            log.error(f"Temporary server data not found for {temp_server_id}")
            return None

        temp_data = json.loads(temp_data_json)

        # Create permanent server in database
        server_form = MCPServerForm(
            name=temp_data["name"],
            http_url=temp_data["http_url"],
            headers=temp_data.get("headers", {}),
            oauth_config=temp_data.get(
                "oauth_config"
            ),  # Include OAuth config if available
        )

        permanent_server = MCPServers.insert_new_mcp_server(user_id, server_form)
        if not permanent_server:
            log.error(
                f"Failed to create permanent server from temporary {temp_server_id}"
            )
            return None

        # Transfer OAuth tokens from temporary server to permanent server
        try:
            temp_token_storage = DatabaseTokenStorage(temp_server_id, user_id)
            permanent_token_storage = DatabaseTokenStorage(permanent_server.id, user_id)

            tokens = await temp_token_storage.get_tokens()
            if tokens:
                await permanent_token_storage.set_tokens(tokens)
                log.info(
                    f"Transferred OAuth tokens from temporary {temp_server_id} to permanent {permanent_server.id}"
                )
            else:
                log.warning(
                    f"No OAuth tokens found for temporary server {temp_server_id}"
                )
        except Exception as token_error:
            log.error(f"Failed to transfer OAuth tokens: {token_error}")

        # Clean up temporary data
        mcp_oauth_manager.redis_client.delete(redis_key)

        log.info(
            f"Created permanent server {permanent_server.id} from temporary {temp_server_id}"
        )
        return permanent_server.id

    except Exception as e:
        log.error(
            f"Error creating permanent server from temporary {temp_server_id}: {e}"
        )
        return None


@router.post("/oauth/start-with-discovery")
async def start_oauth_flow_with_discovery(
    request: Request, user: UserModel = Depends(get_verified_user)
):
    """Start OAuth flow with discovery for a new MCP server (direct DB record)."""
    try:
        body = await request.json()
        server_name = body.get("serverName", "").strip()
        mcp_server_url = body.get("mcpServerUrl", "").strip()
        headers = body.get("headers", {})

        if not server_name:
            raise HTTPException(400, "Server name is required")
        if not mcp_server_url:
            raise HTTPException(400, "MCP server URL is required")

        # Create permanent server directly
        server_form = MCPServerForm(
            name=server_name,
            http_url=mcp_server_url,
            headers=headers,
        )
        permanent_server = MCPServers.insert_new_mcp_server(user.id, server_form)
        if not permanent_server:
            raise HTTPException(500, "Failed to create server")

        # Use configured WEBUI_URL for proper HTTPS support
        base_url = str(WEBUI_URL).rstrip("/")

        # Begin discovery/update against the new server id
        result = await mcp_oauth_manager.discover_oauth_from_mcp_server(
            server_id=permanent_server.id,
            mcp_server_url=mcp_server_url,
            base_url=base_url,
            user_id=user.id,
        )

        if result.get("success"):
            # Immediately start OAuth flow and return authorization URL
            oauth_start = await mcp_oauth_manager.start_oauth_flow(
                server_id=permanent_server.id,
                user_id=user.id,
                base_url=base_url,
            )
            if oauth_start.get("success"):
                return {**oauth_start, "server_id": permanent_server.id}
            # If OAuth start failed, clean up and return the error
            try:
                MCPServers.delete_mcp_server_by_id(permanent_server.id, user.id)
            except Exception:
                pass
            return oauth_start
        # If discovery failed, delete the created server
        try:
            MCPServers.delete_mcp_server_by_id(permanent_server.id, user.id)
        except Exception:
            pass
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error in start_oauth_flow_with_discovery: {e}")
        raise HTTPException(500, "Failed to start OAuth flow")


@router.post("/{server_id}/oauth/start")
async def start_oauth_flow(
    server_id: str, request: Request, user=Depends(get_verified_user)
):
    """Start interactive OAuth flow"""

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


@router.post("/{server_id}/oauth/discover-from-mcp")
async def discover_oauth_from_mcp_server(
    server_id: str, request: Request, user=Depends(get_verified_user)
):
    """Discover OAuth configuration from MCP server using Protected Resource Metadata (RFC 9728)"""

    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        body = await request.json()
        mcp_server_url = body.get("mcp_server_url")

        if not mcp_server_url:
            raise HTTPException(400, "mcp_server_url is required")

        # Use configured WEBUI_URL instead of request.base_url for proper HTTPS support
        base_url = str(WEBUI_URL).rstrip("/")

        result = await mcp_oauth_manager.discover_oauth_from_mcp_server(
            server_id=server_id,
            mcp_server_url=mcp_server_url,
            base_url=base_url,
            user_id=user.id,
        )

        if result["success"]:
            log.info(
                f"MCP OAuth discovery completed for server {server.name} by user {user.email}"
            )

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
    scopes: Optional[str] = None,
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
        base_url = str(WEBUI_URL).rstrip("/")

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


@router.post("/{server_id}/oauth/direct-start")
async def start_direct_oauth_flow(
    server_id: str, request: Request, user=Depends(get_verified_user)
):
    """Start direct OAuth 2.1 flow with any compliant authorization server (bypassing MCP server proxy)"""
    
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


@router.get("/oauth/callback")
async def oauth_callback(
    code: str,
    state: str,
    request: Request,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Handle OAuth callback"""

    if error:
        # OAuth provider returned error
        error_msg = error_description or error
        log.warning(f"OAuth callback received error: {error_msg}")

        # Redirect to dedicated error page
        from urllib.parse import urlencode

        error_params = {"error": error, "error_description": error_description or ""}
        base_url = str(WEBUI_URL).rstrip("/")
        return RedirectResponse(
            url=f"{base_url}/oauth/error?{urlencode(error_params)}"
        )

    try:
        # Use configured WEBUI_URL instead of request.base_url for proper HTTPS support
        base_url = str(WEBUI_URL).rstrip("/")
        result = await mcp_oauth_manager.handle_oauth_callback(
            code=code, state=state, base_url=base_url
        )

        if result.get("success"):
            log.info(
                f"OAuth callback completed successfully for server {result['server_id']}"
            )

            # Redirect to dedicated success page with server ID
            from urllib.parse import urlencode

            success_params = {"server_id": result["server_id"]}
            return RedirectResponse(
                url=f"{base_url}/oauth/success?{urlencode(success_params)}"
            )
        else:
            error_msg = result.get("error", "Unknown OAuth error")
            log.error(f"OAuth callback failed: {error_msg}")

            # Redirect to dedicated error page
            from urllib.parse import urlencode

            error_params = {
                "error": "authentication_failed",
                "error_description": error_msg,
            }
            return RedirectResponse(
                url=f"{base_url}/oauth/error?{urlencode(error_params)}"
            )
    except Exception as e:
        log.error(f"Error handling OAuth callback: {e}")

        # Redirect to dedicated error page
        from urllib.parse import urlencode

        error_params = {"error": "callback_error", "error_description": str(e)}
        base_url = str(WEBUI_URL).rstrip("/")
        return RedirectResponse(
            url=f"{base_url}/oauth/error?{urlencode(error_params)}"
        )


@router.post("/{server_id}/oauth/disconnect")
async def disconnect_oauth(server_id: str, user=Depends(get_verified_user)):
    """Disconnect OAuth (clear tokens)"""

    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        await mcp_oauth_manager.clear_tokens(server_id)
        log.info(f"OAuth tokens cleared for server {server.name} by user {user.email}")
        return {"success": True, "message": "OAuth disconnected successfully"}
    except Exception as e:
        log.error(f"Error disconnecting OAuth for server {server_id}: {e}")
        raise HTTPException(500, f"Failed to disconnect OAuth: {str(e)}")


@router.get("/{server_id}/oauth/status")
async def get_oauth_status(server_id: str, user=Depends(get_verified_user)):
    """Get OAuth connection status"""

    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        status = await mcp_oauth_manager.get_oauth_status(server_id)
        return status
    except Exception as e:
        log.error(f"Error getting OAuth status for server {server_id}: {e}")
        raise HTTPException(500, f"Failed to get OAuth status: {str(e)}")


@router.post("/{server_id}/oauth/test")
async def test_oauth_connection(server_id: str, user=Depends(get_verified_user)):
    """Test OAuth connection by attempting to get access token"""

    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        access_token = await mcp_oauth_manager.get_access_token(server_id)

        if access_token:
            return {
                "success": True,
                "message": "OAuth connection is valid",
                "has_token": True,
            }
        else:
            return {
                "success": False,
                "message": "OAuth token is missing or expired",
                "has_token": False,
                "needs_reauth": True,
            }

    except Exception as e:
        log.error(f"Error testing OAuth connection for server {server_id}: {e}")
        return {
            "success": False,
            "message": f"OAuth connection test failed: {str(e)}",
            "has_token": False,
            "needs_reauth": True,
        }


@router.get("/oauth/check-completion/{state_token}")
async def check_oauth_completion(
    state_token: str, user: UserModel = Depends(get_verified_user)
):
    """Check if OAuth flow has completed by looking up the state in Redis"""
    try:
        # Look up OAuth state in Redis
        redis_key = f"open-webui:oauth_state:{state_token}"
        state_data_json = mcp_oauth_manager.redis_client.get(redis_key)

        if not state_data_json:
            return {"completed": False, "error": "OAuth state not found or expired"}

        state_data = json.loads(state_data_json)

        # Check if this state belongs to the requesting user
        if state_data.get("user_id") != user.id:
            raise HTTPException(403, "Access denied")

        # Check if OAuth flow has been completed
        if state_data.get("completed"):
            final_server_id = state_data.get("final_server_id")
            if final_server_id:
                # OAuth completed and server was created
                return {
                    "completed": True,
                    "server_id": final_server_id,
                    "message": "OAuth completed successfully, server created in database",
                }

        # OAuth not yet completed
        server_id = state_data.get("server_id")
        return {
            "completed": False,
            "server_id": server_id,
            "message": "OAuth flow still in progress",
        }

    except json.JSONDecodeError:
        return {"completed": False, "error": "Invalid OAuth state data"}
    except Exception as e:
        log.error(f"Error checking OAuth completion: {e}")
        raise HTTPException(500, f"Failed to check OAuth completion: {str(e)}")


@router.delete("/oauth/cleanup/{state_token}")
async def cleanup_oauth_state(
    state_token: str, user: UserModel = Depends(get_verified_user)
):
    """Cleanup OAuth state from Redis after successful completion"""
    try:
        result = await mcp_oauth_manager.cleanup_oauth_state(state_token)
        return result
    except Exception as e:
        log.error(f"Error cleaning up OAuth state: {e}")
        raise HTTPException(500, f"Failed to cleanup OAuth state: {str(e)}")
