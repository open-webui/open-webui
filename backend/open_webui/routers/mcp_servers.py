import logging
import asyncio
import json
import time
import os
from typing import Optional, List, Dict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.models.mcp_servers import (
    MCPServerForm,
    MCPServerUpdateForm,
    MCPServerModel,
    MCPServerResponse,
    MCPServerUserResponse,
    MCPServers,
    MCPServerStatus,
    MCPConnectionType,
)
from open_webui.models.users import Users
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.utils.mcp.validation import validate_server_access
from open_webui.utils.mcp.common import validate_http_url, validate_mcp_allowlist, encrypt_headers_if_present
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.mcp_client_official import mcp_manager

from open_webui.utils.mcp_tools import (
    sync_mcp_server_tools_to_database,
    delete_mcp_server_tools_from_database,
    sync_single_mcp_tool_to_database,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


class MCPServerTestRequest(BaseModel):
    http_url: str
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


############################
# MCP Server Management
############################


@router.get("/", response_model=List[MCPServerUserResponse])
async def get_mcp_servers(user=Depends(get_verified_user)):
    """Get all MCP servers accessible to the user (including inactive for UI display)"""
    # Use permission-aware fetch to include public/global and group-shared servers the user can read
    servers = MCPServers.get_mcp_servers_by_user_id(user.id, "read")
    return [
        MCPServerUserResponse(
            id=server.id,
            name=server.name,
            status=server.status,
            is_active=server.is_active,
            is_public=(server.access_control is None),
        )
        for server in servers
    ]


@router.get("/admin", response_model=List[MCPServerResponse])
async def get_all_mcp_servers(user=Depends(get_admin_user)):
    """Get all MCP servers (admin only) including inactive ones"""
    servers = MCPServers.get_all_mcp_servers()

    # Add user information
    server_responses = []
    for server in servers:
        user_info = Users.get_user_by_id(server.user_id)
        server_responses.append(
            MCPServerResponse(**server.model_dump(), user=user_info)
        )

    return server_responses


@router.get("/user", response_model=List[MCPServerUserResponse])
async def get_user_mcp_servers(user=Depends(get_verified_user)):
    """Get user's private MCP servers only"""
    try:
        servers = MCPServers.get_user_mcp_servers(user.id)
        return [
            MCPServerUserResponse(
                id=server.id,
                name=server.name,
                status=server.status,
                is_active=server.is_active,
                is_public=(server.access_control is None),
            )
            for server in servers
        ]
    except asyncio.TimeoutError:
        log.error(f"Timeout getting user MCP servers for user {user.id}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timeout while fetching MCP servers",
        )
    except Exception as e:
        log.error(f"Error getting user MCP servers for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch MCP servers",
        )


@router.get("/{id}", response_model=MCPServerModel)
async def get_mcp_server_by_id(id: str, user=Depends(get_verified_user)):
    """Get a specific MCP server by ID"""
    return validate_server_access(id, user, "read")


@router.post("/", response_model=MCPServerModel)
async def create_mcp_server(
    request: Request, form_data: MCPServerForm, user=Depends(get_verified_user)
):
    """Create a new MCP server (HTTP Stream only for security)"""
    # Validate HTTP Stream URL and allowlist
    validate_http_url(form_data.http_url)
    validate_mcp_allowlist(request, form_data.http_url)

    # Enforce access control restrictions
    if user.role != "admin":
        # Normal users cannot make servers public or share with groups: force private
        form_data.access_control = {}
    else:
        # Admins: if explicitly public, access_control must be None; otherwise leave as provided/dict
        if hasattr(form_data, "access_control") and form_data.access_control is not None:
            # keep as-is (private or group-shared)
            pass

    # Encrypt headers if provided
    if form_data.headers:
        form_data.headers = encrypt_headers_if_present(form_data.headers)

    server = MCPServers.insert_new_mcp_server(user.id, form_data)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    # Test the HTTP Stream connection and wait for result
    try:
        await test_mcp_server_connection(server.id)
    except Exception as e:
        # Do not fail creation on auth or transient errors; status and error_message are set inside
        log.info(f"Deferred connection test after creation due to error: {e}")

    # Sync MCP tools to database for this server (non-blocking)
    asyncio.create_task(sync_mcp_server_tools_to_database(user, server.id))

    # Get updated server with connection status
    updated_server = MCPServers.get_mcp_server_by_id(server.id)
    return updated_server if updated_server else server



@router.put("/{id}", response_model=MCPServerModel)
async def update_mcp_server(
    id: str, form_data: MCPServerUpdateForm, user=Depends(get_verified_user)
):
    """Update an MCP server"""
    # Enforce access control restrictions for non-admin users if attempting to change visibility/sharing
    if user.role != "admin":
        payload = form_data.model_dump(exclude_unset=True)
        if "access_control" in payload:
            ac = payload["access_control"]
            # Disallow public (None) and any group-based sharing
            if ac is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators can make MCP servers public",
                )
            # ac may be dict with read/write keys
            def _has_group_ids(d: dict) -> bool:
                try:
                    read_groups = (d.get("read", {}) or {}).get("group_ids", [])
                    write_groups = (d.get("write", {}) or {}).get("group_ids", [])
                    return bool(read_groups) or bool(write_groups)
                except Exception:
                    return False
            if isinstance(ac, dict) and _has_group_ids(ac):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators can share MCP servers with groups",
                )

    # Encrypt headers if provided
    if form_data.headers:
        form_data.headers = encrypt_headers_if_present(form_data.headers)

    server = MCPServers.update_mcp_server_by_id(id, form_data, user.id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # No cache to clear - tools are stored in database

    # Test the connection if connection details changed
    if any(
        field in form_data.model_dump(exclude_unset=True)
        for field in ["http_url", "headers", "access_control"]
    ):
        await test_mcp_server_connection(id)
        # Get updated server with new connection status
        server = MCPServers.get_mcp_server_by_id(id)

    # Sync MCP tools to database after any update (non-blocking)
    asyncio.create_task(sync_mcp_server_tools_to_database(user, id))

    return server


@router.post("/{id}/toggle")
async def toggle_mcp_server(id: str, user=Depends(get_verified_user)):
    """Toggle MCP server active status"""
    server = MCPServers.get_mcp_server_by_id(id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check permissions
    if server.user_id != user.id and not has_access(
        user.id, "write", server.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Toggle the active status
    updated_server = MCPServers.update_mcp_server_by_id(
        id, MCPServerUpdateForm(is_active=not server.is_active), user.id
    )

    if not updated_server:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle server status",
        )

    # No cache to clear - tools are stored in database

    # Sync or cleanup MCP tools after toggle (wait for completion)
    if updated_server.is_active:
        await sync_mcp_server_tools_to_database(user, id)
    else:
        await delete_mcp_server_tools_from_database(id)

    action = "enabled" if updated_server.is_active else "disabled"
    return {
        "success": True,
        "message": f"Server {action} successfully",
        "is_active": updated_server.is_active,
    }


@router.delete("/{id}")
async def delete_mcp_server(id: str, user=Depends(get_verified_user)):
    """Permanently delete an MCP server"""
    # Get server info before deletion
    server = MCPServers.get_mcp_server_by_id(id)

    # Disconnect the server before deletion
    await mcp_manager.disconnect_server(id)

    result = MCPServers.delete_mcp_server_by_id(id, user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Delete MCP tools for this server (wait for completion)
    await delete_mcp_server_tools_from_database(id)

    return {"success": True}


@router.post("/{id}/test")
async def test_server_connection(id: str, user=Depends(get_verified_user)):
    """Test MCP server connection"""
    server = validate_server_access(id, user, "read")

    try:
        success = await test_mcp_server_connection(id)
        if success:
            return {"success": True}
        else:
            # If test_mcp_server_connection returns False, get the server status for error details
            server = MCPServers.get_mcp_server_by_id(id)
            error_message = server.error_message if server and server.error_message else "Connection failed"
            
            # Extract HTTP status from error message and raise appropriate HTTPException
            if "404" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"success": False, "message": error_message}
                )
            elif "401" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"success": False, "message": error_message}
                )
            elif "403" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"success": False, "message": error_message}
                )
            elif "500" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"success": False, "message": error_message}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"success": False, "message": error_message}
                )
    except HTTPException:
        # Re-raise HTTPExceptions (like our 404, 401, etc.) without modification
        raise
    except Exception as e:
        log.error(f"Test server connection failed: {e}")
        
        # Check if this is an MCPAuthenticationError and preserve the structured error
        from open_webui.utils.mcp.exceptions import MCPAuthenticationError, MCPEncryptionMismatchError
        if isinstance(e, MCPAuthenticationError):
            # For authentication errors, return 401 with structured data
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False, 
                    "message": str(e),
                    "error_type": "authentication",
                    "server_id": e.server_id,
                    "server_name": e.server_name,
                    "challenge_type": e.challenge_type,
                    "requires_reauth": e.requires_reauth,
                    "auth_url": e.auth_url,
                    "instructions": e.instructions
                }
            )
        elif isinstance(e, MCPEncryptionMismatchError):
            # For encryption errors, return 422 with structured data
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "message": str(e),
                    "error_type": "encryption_mismatch",
                    "server_id": e.server_id,
                    "server_name": e.server_name,
                    "instructions": "The encryption key for this MCP server is invalid due to mismatch encryption key. Please remove and add the server again with the correct encryption key."
                }
            )
        
        # For other errors, return 500 with error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": str(e)}
        )


@router.post("/test")
async def test_mcp_server_config(
    test_request: MCPServerTestRequest, user=Depends(get_verified_user)
):
    """Test MCP HTTP Stream server configuration without saving"""
    try:
        # Create a temporary server model for testing
        from open_webui.models.mcp_servers import MCPServerModel

        temp_server = MCPServerModel(
            id="test",
            user_id=user.id,
            name="Test Server",
            connection_type=MCPConnectionType.http_stream,
            http_url=test_request.http_url,
            headers=test_request.headers,
            description="Test connection",
            status=MCPServerStatus.disconnected,
            is_active=True,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        # Test HTTP Stream connection by trying to connect and list tools
        log.info(f"Starting MCP server test for: {test_request.http_url}")

        # Create a temporary client to test the connection
        try:
            # For temporary servers, we need to create a client directly
            from open_webui.utils.mcp.core import streamablehttp_client, ClientSession, create_mcp_client_info
            
            async with streamablehttp_client(temp_server.http_url) as (read, write, _):
                async with ClientSession(read, write, client_info=create_mcp_client_info()) as session:
                    await session.initialize()
                    
                    # Try to list tools to verify full functionality
                    tools_result = await session.list_tools()
                    tools = tools_result.tools if hasattr(tools_result, 'tools') else []
                    
                    log.info(f"Successfully connected to test server, found {len(tools)} tools")
                    
                    response = {
                        "success": True,
                        "message": "Connection successful",
                        "tools": [{"name": tool.name, "description": tool.description} for tool in tools[:5]]
                    }
                    log.info(f"Returning success response: {response}")
                    return response
                    
        except Exception as test_error:
            log.error(f"Test connection failed: {test_error}")
            
            # Extract meaningful error message from TaskGroup/ExceptionGroup
            error_message = str(test_error)
            log.info(f"Raw error message: {error_message}")
            log.info(f"Error type: {type(test_error)}")
            
            # For TaskGroup/ExceptionGroup, dive into the actual exceptions
            if "TaskGroup" in error_message or "ExceptionGroup" in error_message:
                try:
                    # Access the nested exceptions
                    if hasattr(test_error, 'exceptions'):
                        # ExceptionGroup has exceptions attribute
                        nested_exceptions = test_error.exceptions
                        log.info(f"Found {len(nested_exceptions)} nested exceptions")
                        for i, exc in enumerate(nested_exceptions):
                            log.info(f"Nested exception {i}: {type(exc)} - {exc}")
                            exc_str = str(exc)
                            if "401" in exc_str or "Unauthorized" in exc_str:
                                error_message = "401 Unauthorized - Authentication required"
                                break
                            elif "403" in exc_str or "Forbidden" in exc_str:
                                error_message = "403 Forbidden - Access denied"
                                break
                            elif "404" in exc_str or "Not Found" in exc_str:
                                error_message = "404 Not Found - Server endpoint not found"
                                break
                            elif "500" in exc_str or "Internal Server Error" in exc_str:
                                error_message = "500 Internal Server Error - Server error"
                                break
                    elif hasattr(test_error, '__cause__') and test_error.__cause__:
                        # Check the cause chain
                        cause = test_error.__cause__
                        log.info(f"Found cause: {type(cause)} - {cause}")
                        cause_str = str(cause)
                        if "401" in cause_str or "Unauthorized" in cause_str:
                            error_message = "401 Unauthorized - Authentication required"
                        elif "403" in cause_str or "Forbidden" in cause_str:
                            error_message = "403 Forbidden - Access denied"
                        elif "404" in cause_str or "Not Found" in cause_str:
                            error_message = "404 Not Found - Server endpoint not found"
                        elif "500" in cause_str or "Internal Server Error" in cause_str:
                            error_message = "500 Internal Server Error - Server error"
                        else:
                            error_message = "Connection failed - Unable to connect to MCP server"
                    else:
                        error_message = "Connection failed - Unable to connect to MCP server"
                except Exception as extract_error:
                    log.warning(f"Failed to extract nested error: {extract_error}")
                    error_message = "Connection failed - Unable to connect to MCP server"
            
            log.info(f"Processed error message: {error_message}")
            
            response = {"success": False, "message": error_message}
            log.info(f"Returning error response: {response}")
            return response

    except Exception as e:
        log.error(f"Error testing MCP server configuration: {e}")
        return {"success": False, "message": str(e)}


############################
# Helper Functions
############################


async def test_mcp_server_connection(server_id: str) -> bool:
    """Test HTTP Stream connection to an MCP server and update its status"""
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server:
        return False

    try:
        MCPServers.update_mcp_server_status(server_id, MCPServerStatus.connecting)

        # Instead of using test_server_connection, try to actually initialize the server
        # This will properly trigger authentication errors like tool execution does
        client = mcp_manager.get_client(server_id)
        if not client:
            error_message = f"MCP server {server_id} ({server.name}) not available"
            MCPServers.update_mcp_server_status(server_id, MCPServerStatus.error, error_message)
            return False

        # Try to get available tools - this will trigger auth errors
        log.info(f"Testing connection to {server.name} by getting available tools")
        try:
            tools = await client.get_available_tools()
            log.info(f"Successfully connected to {server.name}, found {len(tools)} tools")
            MCPServers.update_mcp_server_status(server_id, MCPServerStatus.connected)
            return True
        except Exception as init_error:
            log.error(f"Initialization failed for {server.name}: {init_error}")
            
            # Extract meaningful error information from MCP SDK exceptions
            
            # Check if this is already an MCPAuthenticationError or MCPEncryptionMismatchError and re-raise it
            from open_webui.utils.mcp.exceptions import MCPAuthenticationError, MCPEncryptionMismatchError
            if isinstance(init_error, (MCPAuthenticationError, MCPEncryptionMismatchError)):
                log.info(f"Re-raising MCP structured error for {server.name}")
                raise init_error
            
            # Not an auth error, just a regular failure - extract HTTP status if possible
            error_str = str(init_error)
            
            # Extract HTTP status from nested TaskGroup exceptions
            extracted_status = None
            if "TaskGroup" in error_str or "ExceptionGroup" in error_str:
                try:
                    # Try to access nested exceptions in TaskGroup/ExceptionGroup
                    if hasattr(init_error, 'exceptions'):
                        for exc in init_error.exceptions:
                            exc_str = str(exc)
                            
                            # If this is another ExceptionGroup, recursively check its exceptions
                            if hasattr(exc, 'exceptions'):
                                for sub_exc in exc.exceptions:
                                    sub_exc_str = str(sub_exc)
                                    if ("404" in sub_exc_str or "Not Found" in sub_exc_str or 
                                        "-32600" in sub_exc_str or "session terminated" in sub_exc_str.lower()):
                                        extracted_status = "404 Not Found - MCP server endpoint not found"
                                        break
                                    elif "401" in sub_exc_str or "Unauthorized" in sub_exc_str:
                                        extracted_status = "401 Unauthorized - Authentication required"
                                        break
                                    elif "403" in sub_exc_str or "Forbidden" in sub_exc_str:
                                        extracted_status = "403 Forbidden - Access denied"
                                        break
                                    elif "500" in sub_exc_str or "Internal Server Error" in sub_exc_str:
                                        extracted_status = "500 Internal Server Error - Server error"
                                        break
                                    elif "429" in sub_exc_str or "Too Many Requests" in sub_exc_str:
                                        extracted_status = "429 Too Many Requests - Rate limit exceeded"
                                        break
                                if extracted_status:
                                    break
                            
                            # Check current level exception
                            if ("404" in exc_str or "Not Found" in exc_str or 
                                "-32600" in exc_str or "session terminated" in exc_str.lower()):
                                extracted_status = "404 Not Found - MCP server endpoint not found"
                                break
                            elif "401" in exc_str or "Unauthorized" in exc_str:
                                extracted_status = "401 Unauthorized - Authentication required"
                                break
                            elif "403" in exc_str or "Forbidden" in exc_str:
                                extracted_status = "403 Forbidden - Access denied"
                                break
                            elif "500" in exc_str or "Internal Server Error" in exc_str:
                                extracted_status = "500 Internal Server Error - Server error"
                                break
                            elif "429" in exc_str or "Too Many Requests" in exc_str:
                                extracted_status = "429 Too Many Requests - Rate limit exceeded"
                                break
                    elif hasattr(init_error, '__cause__') and init_error.__cause__:
                        cause_str = str(init_error.__cause__)
                        if "404" in cause_str or "Not Found" in cause_str:
                            extracted_status = "404 Not Found - MCP server endpoint not found"
                        elif "401" in cause_str or "Unauthorized" in cause_str:
                            extracted_status = "401 Unauthorized - Authentication required"
                        elif "403" in cause_str or "Forbidden" in cause_str:
                            extracted_status = "403 Forbidden - Access denied"
                        elif "500" in cause_str or "Internal Server Error" in cause_str:
                            extracted_status = "500 Internal Server Error - Server error"
                        elif "429" in cause_str or "Too Many Requests" in cause_str:
                            extracted_status = "429 Too Many Requests - Rate limit exceeded"
                except Exception:
                    # If we can't extract nested errors, continue with original logic
                    pass
            
            # Use extracted status or fallback to checking the main error string
            if extracted_status:
                error_str = extracted_status
            elif "404" in error_str or "Not Found" in error_str:
                error_str = "404 Not Found - MCP server endpoint not found"
            elif "401" in error_str or "Unauthorized" in error_str:
                error_str = "401 Unauthorized - Authentication required"
            elif "403" in error_str or "Forbidden" in error_str:
                error_str = "403 Forbidden - Access denied"
            elif "500" in error_str or "Internal Server Error" in error_str:
                error_str = "500 Internal Server Error - Server error"
            elif "429" in error_str or "Too Many Requests" in error_str:
                error_str = "429 Too Many Requests - Rate limit exceeded"
            else:
                # If no specific status found, default to connection error
                error_str = "Connection failed - Unable to connect to MCP server"
            
            MCPServers.update_mcp_server_status(server_id, MCPServerStatus.error, error_str)
            return False

    except Exception as e:
        # Check if this is already an MCPAuthenticationError or MCPEncryptionMismatchError and re-raise it
        from open_webui.utils.mcp.exceptions import MCPAuthenticationError, MCPEncryptionMismatchError
        if isinstance(e, (MCPAuthenticationError, MCPEncryptionMismatchError)):
            # Update status but re-raise the structured error
            MCPServers.update_mcp_server_status(server_id, MCPServerStatus.error, str(e))
            raise e
        
        log.error(f"Error testing MCP server {server_id}: {e}")
        MCPServers.update_mcp_server_status(server_id, MCPServerStatus.error, str(e))
        return False




@router.post("/{server_id}/sync-tools")
async def sync_server_tools_to_db(server_id: str, user=Depends(get_verified_user)):
    """Sync all tools from a specific MCP server to the database"""
    try:
        # Check if user has access to this server
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

        await sync_mcp_server_tools_to_database(user, server_id)
        return {
            "success": True,
            "message": f"Tools from server {server.name} synced successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to sync tools from server {server_id}: {e}")
        
        # Check if this is an MCPAuthenticationError and preserve the structured error
        from open_webui.utils.mcp.exceptions import MCPAuthenticationError, MCPEncryptionMismatchError
        if isinstance(e, MCPAuthenticationError):
            # For authentication errors, return 401 with structured data
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False, 
                    "message": str(e),
                    "error_type": "authentication",
                    "server_id": e.server_id,
                    "server_name": e.server_name,
                    "challenge_type": e.challenge_type,
                    "requires_reauth": e.requires_reauth,
                    "auth_url": e.auth_url,
                    "instructions": e.instructions
                }
            )
        elif isinstance(e, MCPEncryptionMismatchError):
            # For encryption errors, return 422 with structured data
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "message": str(e),
                    "error_type": "encryption_mismatch",
                    "server_id": e.server_id,
                    "server_name": e.server_name,
                    "instructions": "The encryption key for this MCP server is invalid due to mismatch encryption key. Please remove and add the server again with the correct encryption key."
                }
            )
        
        # For other errors, return 500 with error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": str(e)}
        )


@router.post("/{server_id}/tools/{tool_name}/sync")
async def sync_single_tool_to_db(
    server_id: str, tool_name: str, user=Depends(get_verified_user)
):
    """Sync a single MCP tool to the database"""
    try:
        # Check if user has access to this server
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

        await sync_single_mcp_tool_to_database(user, server_id, tool_name)
        return {
            "success": True,
            "message": f"Tool {tool_name} from server {server.name} synced successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to sync tool {tool_name} from server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync tool: {str(e)}",
        )