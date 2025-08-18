"""
MCP Client Manager and Connection Testing
"""
import asyncio
import logging
import json
import ssl
from typing import Optional, Dict, Any
from datetime import timedelta
import httpx

from .core import (
    MCP_AVAILABLE, streamablehttp_client, ClientSession,
    create_mcp_client_info
)
from .client import MCPStreamHTTPClient

from open_webui.models.mcp_servers import MCPServerModel, MCPServers
from open_webui.env import WEBUI_SECRET_KEY
from open_webui.utils.auth import decrypt_data

log = logging.getLogger(__name__)


def create_insecure_httpx_client_factory():
    """Create httpx client factory that bypasses SSL verification for corporate environments"""
    def client_factory():
        # Import the MCP SDK client factory to inherit defaults
        from mcp.shared._httpx_utils import create_mcp_http_client
        
        # Create the default MCP client first to get its configuration
        default_client = create_mcp_http_client()
        
        # Get attributes safely
        timeout = getattr(default_client, 'timeout', httpx.Timeout(30.0))
        
        # Close the default client since we're not using it
        default_client.close()
        
        # Create a new client with SSL verification disabled
        return httpx.AsyncClient(
            verify=False,  # Disable SSL verification
            timeout=timeout,
        )
    
    return client_factory


class MCPClientManager:
    """Manages MCP server interactions using official SDK stateless pattern"""

    def __init__(self):
        pass

    async def disconnect_server(self, server_id: str):
        """Disconnect from an MCP server - no-op since we use stateless connections"""
        log.debug("Disconnect server %s - no-op with stateless pattern", server_id)
        pass

    def get_client(self, server_id: str) -> Optional[MCPStreamHTTPClient]:
        """Get MCP client for a server - creates a new stateless client"""
        server = MCPServers.get_mcp_server_by_id(server_id)
        if not server:
            return None
        return MCPStreamHTTPClient(server)

    async def disconnect_all(self):
        """Disconnect from all MCP servers - no-op since we use stateless connections"""
        log.debug("Disconnect all servers - no-op with stateless pattern")
        pass

    async def test_server_connection(self, server: MCPServerModel) -> Dict[str, Any]:
        """Test connection to an MCP server using the official SDK pattern"""
        if not MCP_AVAILABLE:
            return {
                "success": False,
                "message": "MCP SDK not available. Please install the MCP package: pip install mcp",
            }

        try:
            log.info("Testing connection to MCP server: %s", server.http_url)

            # Prepare authentication headers - let MCP SDK handle protocol headers
            headers = {
                # Don't override Accept and Content-Type - let MCP SDK handle them
                # "Accept": "application/json, text/event-stream",  # SDK sets this
                # "MCP-Protocol-Version": "2025-06-18",  # SDK sets this  
                # "Content-Type": "application/json",  # SDK sets this
                "User-Agent": "Open WebUI - MCP Client/0.6.22",
            }

            # Add OAuth authentication if configured
            oauth_failed = False
            if server.oauth_config:
                try:
                    from open_webui.models.mcp_servers import MCPOAuthConfig
                    from .auth import MCPOAuthManager

                    oauth_config = MCPOAuthConfig(**server.oauth_config)
                    if oauth_config.enabled:
                        oauth_manager = MCPOAuthManager()
                        access_token = await oauth_manager.get_access_token(server.id)
                        
                        if access_token:
                            headers["Authorization"] = f"Bearer {access_token}"
                            log.info(f"Using OAuth token for server {server.name}")
                            log.debug(f"OAuth token (first 20 chars): {access_token[:20]}...")
                        else:
                            oauth_failed = True
                            log.warning(f"OAuth token not available for server {server.name}")
                except Exception as e:
                    oauth_failed = True
                    log.warning(f"OAuth authentication failed for server {server.name}: {e}")

            # Add manual headers if present (can supplement or override OAuth)
            if server.headers:
                if "encrypted" in server.headers:
                    decrypted_headers_json = decrypt_data(
                        server.headers["encrypted"], WEBUI_SECRET_KEY
                    )
                    decrypted_headers = json.loads(decrypted_headers_json)
                    headers.update(decrypted_headers)
                else:
                    headers.update(server.headers)

            # Check if we have any authentication
            has_auth = any(
                key.lower() in ["authorization", "x-api-key", "x-auth-token"]
                for key in headers.keys()
            )

            if oauth_failed and not has_auth:
                from .exceptions import MCPAuthenticationError
                
                # Create structured authentication error for OAuth
                auth_error = MCPAuthenticationError(
                    message=f"OAuth token missing or expired for server {server.name}. Please re-authenticate.",
                    server_id=server.id,
                    server_name=server.name,
                    challenge_type="oauth",
                    requires_reauth=True,
                    auth_url=None,
                    instructions="Please click the login button to authenticate with the OAuth provider."
                )
                
                return {
                    "success": False,
                    "message": str(auth_error),
                    "error_type": "authentication",
                    "server_id": auth_error.server_id,
                    "server_name": auth_error.server_name,
                    "challenge_type": auth_error.challenge_type,
                    "requires_reauth": auth_error.requires_reauth,
                    "auth_url": auth_error.auth_url,
                    "instructions": auth_error.instructions
                }

            # Use the official MCP SDK pattern - this handles all cleanup automatically
            log.info(
                "Attempting to connect to MCP server with headers: %s", list(headers.keys())
            )
            
            # First try with normal SSL verification
            return await self._attempt_connection(server, headers)
            
        except asyncio.TimeoutError:
            log.error("Connection test timed out for %s", server.http_url)
            return {
                "success": False,
                "message": "Connection test timed out. The MCP server may be unresponsive or the URL may be incorrect.",
            }
        except Exception as e:
            error_msg = str(e)
            log.error("Connection test failed: %s", e)
            log.error("Exception type: %s", type(e).__name__)

            # Import traceback for better error handling
            import traceback

            # Try to extract HTTP error details from nested exceptions
            http_error_details = self._extract_http_error_details(e)

            # Log full traceback for debugging
            full_traceback = traceback.format_exc()
            log.error("Full traceback: %s", full_traceback)
            
            # Try to extract HTTP status from traceback if not found in exception details
            if not http_error_details and "HTTP/1.1" in full_traceback:
                import re
                # Look for HTTP status codes in the traceback
                http_pattern = r'HTTP/1\.1 (\d{3})'
                match = re.search(http_pattern, full_traceback)
                if match:
                    status_code = int(match.group(1))
                    log.info("Extracted HTTP status code from traceback: %d", status_code)
                    http_error_details = {
                        "status_code": status_code,
                        "url": server.http_url,
                        "response_text": f"HTTP {status_code} response detected in traceback"
                    }

            # Check if this is an SSL error and retry with bypass
            if self._is_ssl_error(e, error_msg):
                log.warning("SSL error detected for %s, attempting connection with SSL bypass", server.name)
                log.debug("Original SSL error: %s", error_msg)
                try:
                    result = await self._attempt_connection_with_ssl_bypass(server, headers)
                    log.info("SSL bypass successful for %s", server.name)
                    return result
                except Exception as retry_e:
                    log.error("SSL bypass attempt also failed for %s: %s", server.name, retry_e)
                    return self._create_ssl_error_response(e, error_msg)
            else:
                log.debug("Not an SSL error, error type: %s", type(e).__name__)

            # Provide more specific error messages based on HTTP status or error patterns
            if http_error_details:
                return self._create_http_error_response(http_error_details)
            elif "404 Not Found" in error_msg or "HTTP/1.1 404" in str(e):
                # Handle case where we can detect 404 from logs but not exception details
                return {
                    "success": False,
                    "message": f"MCP Endpoint Not Found (404): The MCP server endpoint does not exist.\n\nPossible solutions:\n• Check if the URL path is correct\n• Try different endpoint paths like '/mcp-server', '/api/mcp', or '/api/v1/mcp'\n• Verify the MCP server is properly configured\n• Contact the server administrator\n\nTechnical details: {error_msg}",
                    "error_type": "mcp_endpoint_not_found",
                    "status_code": 404
                }
            elif "TaskGroup" in error_msg:
                # Check if this is a wrapped authentication error
                if "AUTHENTICATION_REQUIRED:" in str(e):
                    # Extract the authentication error from the traceback
                    import re
                    auth_match = re.search(r'AUTHENTICATION_REQUIRED: (.+)', str(e))
                    if auth_match:
                        auth_error = auth_match.group(1)
                        return {
                            "success": False,
                            "message": f"Authentication required to access tools: {auth_error}",
                            "error_type": "authentication_required", 
                            "oauth_setup_needed": True,
                            "server_id": server.id
                        }
                
                return {
                    "success": False,
                    "message": f"MCP protocol error during capability fetching. This usually indicates the server returned an unexpected response or has compatibility issues. Details: {error_msg}",
                }
            elif "Failed to fetch tools" in error_msg:
                # Check if this is an authentication requirement
                if error_msg.startswith("AUTHENTICATION_REQUIRED:"):
                    # Extract the actual error message
                    auth_error = error_msg.replace("AUTHENTICATION_REQUIRED: ", "")
                    return {
                        "success": False,
                        "message": f"Authentication required to access tools: {auth_error}",
                        "error_type": "authentication_required",
                        "oauth_setup_needed": True,
                        "server_id": server.id
                    }
                else:
                    return {
                        "success": False,
                        "message": error_msg,  # Use the detailed tools fetching error
                    }
            elif "Connection refused" in error_msg or "ConnectError" in error_msg:
                return {
                    "success": False,
                    "message": "Connection refused. Please check the server URL and ensure the MCP server is running.",
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection test failed: {error_msg}",
                }

    async def _attempt_connection(self, server: MCPServerModel, headers: Dict[str, str]) -> Dict[str, Any]:
        """Attempt connection with normal SSL verification"""
        async with streamablehttp_client(
            url=server.http_url, headers=headers, timeout=timedelta(seconds=30)
        ) as (read_stream, write_stream, get_session_id):
            return await self._test_mcp_session(read_stream, write_stream, get_session_id)

    async def _attempt_connection_with_ssl_bypass(self, server: MCPServerModel, headers: Dict[str, str]) -> Dict[str, Any]:
        """Attempt connection with SSL verification bypassed"""
        log.info("Creating insecure httpx client factory for SSL bypass")
        insecure_client_factory = create_insecure_httpx_client_factory()
        
        log.info("Attempting SSL bypass connection to %s", server.http_url)
        async with streamablehttp_client(
            url=server.http_url, 
            headers=headers, 
            timeout=timedelta(seconds=30),
            httpx_client_factory=insecure_client_factory
        ) as (read_stream, write_stream, get_session_id):
            log.info("SSL bypass connection established, testing MCP session")
            result = await self._test_mcp_session(read_stream, write_stream, get_session_id)
            if result["success"]:
                # Add warning about SSL bypass
                result["ssl_bypass_used"] = True
                result["message"] = f"✅ Connection successful (SSL verification bypassed for corporate environment). {result.get('message', '')}"
                log.info("SSL bypass connection successful")
            return result

    async def _test_mcp_session(self, read_stream, write_stream, get_session_id) -> Dict[str, Any]:
        """Test MCP session capabilities"""
        log.info("MCP stream connection established, creating session")
        # Create session using the official pattern
        async with ClientSession(
            read_stream, write_stream,
            client_info=create_mcp_client_info()
        ) as session:
            # Initialize the connection
            log.info("Initializing MCP session")
            await session.initialize()

            # Get capabilities with individual error handling
            log.info("Fetching MCP server capabilities")
            tools_result = None
            prompts_result = None
            resources_result = None

            try:
                log.info("Fetching tools from MCP server")
                tools_result = await session.list_tools()
                log.info(
                    "Successfully fetched %d tools", len(tools_result.tools) if tools_result and tools_result.tools else 0
                )
            except Exception as e:
                log.error("Failed to fetch tools: %s", e)
                error_msg = str(e)
                
                # Check for authentication-related errors
                if any(auth_term in error_msg.lower() for auth_term in [
                    "authentication required", "unauthorized", "authentication failed",
                    "token expired", "invalid token", "access denied", "forbidden",
                    "oauth", "login required", "credentials required"
                ]):
                    # This is an authentication error - return structured error for OAuth setup
                    raise Exception(f"AUTHENTICATION_REQUIRED: {error_msg}")
                else:
                    # Generic tool fetching error
                    raise Exception(f"Failed to fetch tools from MCP server: {error_msg}")

            try:
                log.info("Fetching prompts from MCP server")
                prompts_result = await session.list_prompts()
                log.info(
                    "Successfully fetched %d prompts", len(prompts_result.prompts) if prompts_result and prompts_result.prompts else 0
                )
            except Exception as e:
                log.warning("Failed to fetch prompts (non-critical): %s", e)
                # Prompts failure is non-critical, continue

            try:
                log.info("Fetching resources from MCP server")
                resources_result = await session.list_resources()
                log.info(
                    "Successfully fetched %d resources", len(resources_result.resources) if resources_result and resources_result.resources else 0
                )
            except Exception as e:
                log.warning("Failed to fetch resources (non-critical): %s", e)
                # Resources failure is non-critical, continue

            session_id = get_session_id() if get_session_id else None

            log.info(
                "MCP server test successful - %d tools found", len(tools_result.tools) if tools_result else 0
            )

            return {
                "success": True,
                "message": "Connection successful",
                "tools": [
                    {
                        "name": tool.name,
                        "description": getattr(tool, "description", ""),
                    }
                    for tool in (tools_result.tools if tools_result else [])
                ],
                "prompts": len(prompts_result.prompts) if prompts_result else 0,
                "resources": len(resources_result.resources)
                if resources_result
                else 0,
                "session_id": session_id,
            }

    def _extract_http_error_details(self, e: Exception) -> Optional[Dict[str, Any]]:
        """Extract HTTP error details from nested exceptions."""
        http_error_details = None

        # Handle ExceptionGroup from MCP SDK (anyio TaskGroups)
        def extract_from_exception_group(exc):
            """Recursively extract exceptions from ExceptionGroup"""
            if hasattr(exc, "exceptions"):  # ExceptionGroup has .exceptions attribute
                for nested_exc in exc.exceptions:
                    # Recursively check nested ExceptionGroups
                    result = extract_from_exception_group(nested_exc)
                    if result:
                        return result
                    # Check if this nested exception is an HTTP error
                    if "HTTPStatusError" in str(type(nested_exc)):
                        return nested_exc
            return None

        # First check if this is an ExceptionGroup
        if "ExceptionGroup" in str(type(e)) or "TaskGroup" in str(e):
            log.error("Detected MCP SDK ExceptionGroup, extracting nested errors")
            http_exception = extract_from_exception_group(e)
            if http_exception:
                log.error("Found nested HTTP exception: %s", http_exception)
                e = http_exception  # Replace the main exception with the HTTP error

        # Walk through the exception chain to find HTTP errors
        current_exception = e
        while current_exception:
            # Check for httpx.HTTPStatusError
            if "HTTPStatusError" in str(type(current_exception)):
                try:
                    # Extract status code and response details
                    if hasattr(current_exception, "response"):
                        response = current_exception.response
                        status_code = response.status_code
                        url = str(response.url)

                        # Try to get response text if available
                        response_text = ""
                        try:
                            if hasattr(response, "text"):
                                response_text = response.text[:500]  # Limit to 500 chars
                            elif hasattr(response, "content"):
                                response_text = response.content.decode(
                                    "utf-8", errors="ignore"
                                )[:500]
                        except:
                            response_text = "Unable to read response body"

                        http_error_details = {
                            "status_code": status_code,
                            "url": url,
                            "response_text": response_text,
                        }
                        log.error(
                            "HTTP Error Details - Status: %s, URL: %s, Response: %s",
                            status_code,
                            url,
                            response_text,
                        )
                        break
                except Exception as parse_error:
                    log.error("Failed to parse HTTP error details: %s", parse_error)

            # Move to the next exception in the chain
            if hasattr(current_exception, "__cause__"):
                current_exception = current_exception.__cause__
            elif hasattr(current_exception, "__context__"):
                current_exception = current_exception.__context__
            else:
                break

        return http_error_details

    def _create_http_error_response(self, http_error_details: Dict[str, Any]) -> Dict[str, Any]:
        """Create appropriate error response based on HTTP status code."""
        status_code = http_error_details["status_code"]
        response_text = http_error_details["response_text"]

        if status_code == 400:
            return {
                "success": False,
                "message": f"Bad Request (400): The MCP server rejected the request. This usually indicates invalid parameters or malformed request. Server response: {response_text}",
            }
        elif status_code == 401:
            return {
                "success": False,
                "message": f"Unauthorized (401): Authentication failed. Please check your API key or credentials. Server response: {response_text}",
            }
        elif status_code == 403:
            return {
                "success": False,
                "message": f"Forbidden (403): Access denied. Your credentials may not have permission to access this MCP server. Server response: {response_text}",
            }
        elif status_code == 404:
            return {
                "success": False,
                "message": f"MCP Endpoint Not Found (404): The MCP server endpoint '/mcp' does not exist on this server.\n\nPossible solutions:\n• Check if the URL path is correct (maybe try '/mcp-server' or '/api/mcp')\n• Verify the MCP server is properly configured\n• Contact the server administrator\n\nServer response: {response_text}",
                "error_type": "mcp_endpoint_not_found",
                "suggested_urls": [
                    http_error_details["url"].replace("/mcp", "/mcp-server"),
                    http_error_details["url"].replace("/mcp", "/api/mcp"),
                    http_error_details["url"].replace("/mcp", "/api/v1/mcp")
                ]
            }
        elif status_code == 500:
            return {
                "success": False,
                "message": f"Internal Server Error (500): The MCP server encountered an error. Server response: {response_text}",
            }
        elif status_code == 502:
            return {
                "success": False,
                "message": f"Bad Gateway (502): The MCP server is unreachable or returned an invalid response. Server response: {response_text}",
            }
        elif status_code == 503:
            return {
                "success": False,
                "message": f"Service Unavailable (503): The MCP server is temporarily unavailable. Server response: {response_text}",
            }
        else:
            return {
                "success": False,
                "message": f"HTTP Error {status_code}: {response_text}",
            }

    def _is_ssl_error(self, exception: Exception, error_msg: str) -> bool:
        """Check if the error is SSL/TLS related, including nested ExceptionGroup errors"""
        ssl_indicators = [
            "SSL",
            "TLS", 
            "certificate",
            "CERTIFICATE_VERIFY_FAILED",
            "unable to get local issuer certificate",
            "certificate verify failed",
            "self signed certificate",
            "hostname doesn't match",
            "certificate has expired",
            "SSLError",
            "ssl.SSLError",
            "ConnectError"
        ]
        
        # Check error message first
        error_lower = error_msg.lower()
        if any(indicator.lower() in error_lower for indicator in ssl_indicators):
            return True
        
        # Function to recursively check ExceptionGroup
        def check_exception_recursively(exc) -> bool:
            # Check if this exception itself contains SSL indicators
            exc_str = str(exc).lower()
            exc_type = str(type(exc)).lower()
            
            if any(indicator.lower() in exc_str for indicator in ssl_indicators):
                return True
            if any(indicator.lower() in exc_type for indicator in ssl_indicators):
                return True
                
            # If this is an ExceptionGroup, check all nested exceptions
            if hasattr(exc, "exceptions"):  # ExceptionGroup has .exceptions attribute
                for nested_exc in exc.exceptions:
                    if check_exception_recursively(nested_exc):
                        return True
                        
            # Check exception chain (__cause__, __context__)
            if hasattr(exc, '__cause__') and exc.__cause__:
                if check_exception_recursively(exc.__cause__):
                    return True
            if hasattr(exc, '__context__') and exc.__context__:
                if check_exception_recursively(exc.__context__):
                    return True
                    
            return False
            
        return check_exception_recursively(exception)

    def _create_ssl_error_response(self, _exception: Exception, error_msg: str) -> Dict[str, Any]:
        """Create a detailed SSL error response for the UI"""
        error_lower = error_msg.lower()
        
        # Specific SSL error types with user-friendly messages
        if "certificate_verify_failed" in error_lower or "unable to get local issuer certificate" in error_lower:
            return {
                "success": False,
                "message": "SSL Certificate Verification Failed: The server's SSL certificate could not be verified. This usually means:\n• The certificate is self-signed\n• The certificate authority (CA) is not trusted\n• Certificate chain is incomplete\n\nSolution: Install the server's CA certificate or contact your system administrator.",
                "error_type": "ssl_verification_failed",
                "technical_details": error_msg
            }
        elif "self signed certificate" in error_lower:
            return {
                "success": False,
                "message": "Self-Signed Certificate: The server is using a self-signed SSL certificate that is not trusted by default.\n\nSolution: Install the server's certificate as a trusted CA or contact your system administrator.",
                "error_type": "ssl_self_signed",
                "technical_details": error_msg
            }
        elif "hostname doesn't match" in error_lower or "hostname mismatch" in error_lower:
            return {
                "success": False,
                "message": "SSL Hostname Mismatch: The server's SSL certificate was issued for a different hostname.\n\nSolution: Use the correct hostname in the URL or contact your system administrator.",
                "error_type": "ssl_hostname_mismatch", 
                "technical_details": error_msg
            }
        elif "certificate has expired" in error_lower or "expired" in error_lower:
            return {
                "success": False,
                "message": "SSL Certificate Expired: The server's SSL certificate has expired.\n\nSolution: Contact your system administrator to renew the certificate.",
                "error_type": "ssl_expired",
                "technical_details": error_msg
            }
        else:
            return {
                "success": False,
                "message": f"SSL/TLS Error: There was a problem with the secure connection to the server.\n\nTechnical details: {error_msg}\n\nSolution: Contact your system administrator or check the server's SSL configuration.",
                "error_type": "ssl_generic",
                "technical_details": error_msg
            }