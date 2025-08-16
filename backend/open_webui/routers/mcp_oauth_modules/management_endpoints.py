"""
MCP OAuth management endpoints (callback, status, disconnect, test).
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from open_webui.utils.auth import get_verified_user
from open_webui.models.mcp_servers import MCPServers, MCPServerStatus
from open_webui.utils.mcp.auth import mcp_oauth_manager
from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request, code: str = None, state: str = None, error: str = None
):
    """Handle OAuth callback from authorization server."""
    
    if error:
        error_description = request.query_params.get("error_description", "Unknown error")
        log.error(f"OAuth callback error: {error} - {error_description}")
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
                    .error {{ color: #d32f2f; }}
                </style>
            </head>
            <body>
                <h1 class="error">OAuth Authentication Failed</h1>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Description:</strong> {error_description}</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """,
            status_code=400
        )

    if not code or not state:
        log.error("OAuth callback missing code or state parameter")
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth Error</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 50px; text-align: center; }
                    .error { color: #d32f2f; }
                </style>
            </head>
            <body>
                <h1 class="error">OAuth Authentication Failed</h1>
                <p>Missing required parameters (code or state)</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """,
            status_code=400
        )

    try:
        # Use configured WEBUI_URL for proper HTTPS support
        base_url = str(request.app.state.config.WEBUI_URL).rstrip("/")
        
        # Handle the OAuth callback
        result = await mcp_oauth_manager.handle_oauth_callback(code, state, base_url)

        if result["success"]:
            server_id = result.get("server_id", "unknown")
            flow_type = result.get("flow_type", "unknown")
            
            log.info(f"OAuth callback successful for server {server_id} using {flow_type}")
            
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>OAuth Success</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
                        .success {{ color: #2e7d32; }}
                        .info {{ color: #1976d2; margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <h1 class="success">✅ OAuth Authentication Successful!</h1>
                    <p>Your MCP server has been authenticated successfully.</p>
                    <div class="info">
                        <p><strong>Server ID:</strong> {server_id}</p>
                        <p><strong>Flow Type:</strong> {flow_type}</p>
                    </div>
                    <p><strong>You can now close this window and return to the application.</strong></p>
                    <script>
                        // Auto-close after 3 seconds
                        setTimeout(() => {{ window.close(); }}, 3000);
                    </script>
                </body>
                </html>
                """
            )
        else:
            error_msg = result.get("error", "Unknown error occurred")
            log.error(f"OAuth callback failed: {error_msg}")
            
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>OAuth Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
                        .error {{ color: #d32f2f; }}
                    </style>
                </head>
                <body>
                    <h1 class="error">OAuth Authentication Failed</h1>
                    <p><strong>Error:</strong> {error_msg}</p>
                    <p>Please close this window and try again.</p>
                </body>
                </html>
                """,
                status_code=400
            )

    except Exception as e:
        log.error(f"Error processing OAuth callback: {e}")
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
                    .error {{ color: #d32f2f; }}
                </style>
            </head>
            <body>
                <h1 class="error">OAuth Processing Error</h1>
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """,
            status_code=500
        )


@router.post("/{server_id}/oauth/disconnect")
async def disconnect_oauth(server_id: str, user=Depends(get_verified_user)):
    """Disconnect OAuth authentication for a server."""
    
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        await mcp_oauth_manager.clear_tokens(server_id)
        log.info(f"OAuth disconnected for server {server.name} by user {user.email}")
        
        return {
            "success": True,
            "message": "OAuth authentication disconnected successfully"
        }
    except Exception as e:
        log.error(f"Error disconnecting OAuth for server {server_id}: {e}")
        raise HTTPException(500, f"Failed to disconnect OAuth: {str(e)}")


@router.get("/{server_id}/oauth/status")
async def get_oauth_status(server_id: str, user=Depends(get_verified_user)):
    """Get OAuth status for a server."""
    
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
    """Test OAuth connection to an MCP server."""
    
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    # Check permissions
    if server.user_id != user.id and not has_access(user.id, "write", server.access_control):
        raise HTTPException(403, "Access denied to this MCP server")

    try:
        # Import here to avoid circular imports
        from open_webui.utils.mcp.manager import MCPServerManager
        
        manager = MCPServerManager()
        result = await manager.test_mcp_server_connection(server_id, user.id)
        
        if result["success"]:
            log.info(f"OAuth connection test successful for server {server.name}")
        else:
            log.warning(f"OAuth connection test failed for server {server.name}: {result.get('error')}")
        
        return result
        
    except Exception as e:
        log.error(f"Error testing OAuth connection for server {server_id}: {e}")
        raise HTTPException(500, f"Failed to test OAuth connection: {str(e)}")


@router.get("/oauth/check-completion/{server_id}")
async def check_oauth_completion(
    server_id: str, user=Depends(get_verified_user)
):
    """Check if OAuth flow has been completed for a given server ID."""
    
    try:
        # Get the specific server by ID
        server = MCPServers.get_mcp_server_by_id(server_id)
        
        if not server:
            return {
                "completed": False,
                "server_id": server_id,
                "message": "Server not found"
            }
        
        # Check if user has access to this server
        if server.user_id != user.id:
            return {
                "completed": False,
                "server_id": server_id,
                "message": "Access denied"
            }
        
        # Check if server has completed OAuth flow (has valid tokens and is connected)
        if server.oauth_tokens and server.status == MCPServerStatus.connected:
            return {
                "completed": True,
                "server_id": server_id,
                "server_name": server.name,
                "message": "OAuth flow completed successfully"
            }
        elif server.status == MCPServerStatus.oauth_required:
            return {
                "completed": False,
                "server_id": server_id,
                "message": "OAuth flow still required"
            }
        elif server.status == MCPServerStatus.token_expired:
            return {
                "completed": False,
                "server_id": server_id,
                "message": "OAuth tokens expired, re-authentication needed"
            }
        else:
            return {
                "completed": False,
                "server_id": server_id,
                "message": "OAuth flow still in progress"
            }
            
    except Exception as e:
        log.error(f"Error checking OAuth completion for server {server_id}: {e}")
        return {"completed": False, "error": str(e)}


@router.delete("/oauth/cleanup/{state_token}")
async def cleanup_oauth_state(
    state_token: str, user=Depends(get_verified_user)
):
    """Clean up OAuth state from Redis."""
    
    try:
        result = await mcp_oauth_manager.cleanup_oauth_state(state_token)
        return result
    except Exception as e:
        log.error(f"Error cleaning up OAuth state {state_token}: {e}")
        raise HTTPException(500, f"Failed to cleanup OAuth state: {str(e)}") 