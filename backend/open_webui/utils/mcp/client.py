"""
MCP StreamHTTP Client Implementation
"""
import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import timedelta

from .core import (
    MCP_AVAILABLE, streamablehttp_client, ClientSession, Tool,
    create_mcp_client_info
)
from .auth import MCPOAuthManager

from open_webui.models.mcp_servers import MCPServerModel
from open_webui.env import WEBUI_SECRET_KEY
from open_webui.utils.auth import decrypt_data

log = logging.getLogger(__name__)


class MCPStreamHTTPClient:
    """
    Official MCP client using Streamable HTTP transport
    Follows the official MCP specification and uses the official Python SDK
    """

    def __init__(self, server: MCPServerModel):
        self.server = server
        self.tools_cache: Optional[List[Tool]] = None
        self.prompts_cache: Optional[List[Any]] = None
        self.resources_cache: Optional[List[Any]] = None

    async def _execute_with_session(self, operation, timeout_seconds: int = 30):
        """Execute an operation with a properly configured MCP session."""
        if not MCP_AVAILABLE:
            raise Exception("MCP SDK not available")

        headers = await self._get_headers()
        tried_refresh = False

        # Try normal connection first, with refresh-on-401 retry, then fallback to SSL bypass
        for attempt in range(2):
            try:
                async with streamablehttp_client(
                    url=self.server.http_url,
                    headers=headers,
                    timeout=timedelta(seconds=timeout_seconds)
                ) as (read_stream, write_stream, get_session_id):
                    async with ClientSession(
                        read_stream, write_stream,
                        client_info=create_mcp_client_info()
                    ) as session:
                        await session.initialize()
                        return await operation(session)
            except Exception as e:
                error_msg = str(e)
                # If we got an auth error and haven't tried refresh yet, refresh and retry once
                if (not tried_refresh) and self._is_authentication_error(e)[0]:
                    try:
                        log.info("401/auth error detected. Attempting token refresh and retry for server %s", self.server.name)
                        refreshed = await MCPOAuthManager().refresh_access_token(self.server.id)
                        if refreshed:
                            tried_refresh = True
                            headers = await self._get_headers()  # reload headers with new token
                            continue  # retry loop
                        else:
                            log.warning("Token refresh failed or unavailable for server %s", self.server.name)
                    except Exception as refresh_error:
                        log.error("Token refresh attempt failed: %s", refresh_error)
                # Check if it's an SSL error and retry with bypass
                if self._is_ssl_error(e, error_msg):
                    log.warning("SSL error in MCP client, attempting with SSL bypass: %s", error_msg)
                    from .manager import create_insecure_httpx_client_factory
                    insecure_client_factory = create_insecure_httpx_client_factory()
                    async with streamablehttp_client(
                        url=self.server.http_url,
                        headers=headers,
                        timeout=timedelta(seconds=timeout_seconds),
                        httpx_client_factory=insecure_client_factory
                    ) as (read_stream, write_stream, get_session_id):
                        async with ClientSession(
                            read_stream, write_stream,
                            client_info=create_mcp_client_info()
                        ) as session:
                            await session.initialize()
                            return await operation(session)
                # Re-raise non-SSL/non-auth cases or after refresh retry
                raise

    def _is_ssl_error(self, exception: Exception, error_msg: str) -> bool:
        """Check if the error is SSL/TLS related, including nested ExceptionGroup errors"""
        ssl_indicators = [
            "SSL", "TLS", "certificate", "CERTIFICATE_VERIFY_FAILED",
            "unable to get local issuer certificate", "certificate verify failed",
            "self signed certificate", "hostname doesn't match",
            "certificate has expired", "SSLError", "ssl.SSLError", "ConnectError"
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


    async def _get_headers(self):
        """Prepare authentication headers for MCP requests with OAuth + manual headers support"""
        headers = {
            "User-Agent": "Open WebUI - MCP Client/1.0",
        }

        oauth_failed = False

        # 1. Try OAuth first if configured
        if self.server.oauth_config:
            try:
                from open_webui.models.mcp_servers import MCPOAuthConfig

                oauth_config = MCPOAuthConfig(**self.server.oauth_config)

                if oauth_config.enabled:
                    # Use the integrated OAuth manager
                    oauth_manager = MCPOAuthManager()
                    access_token = await oauth_manager.get_access_token(self.server.id)

                    if access_token:
                        headers["Authorization"] = f"Bearer {access_token}"
                        log.debug(f"Using OAuth token for server {self.server.name}")
                    else:
                        oauth_failed = True
                        log.warning(
                            f"OAuth token not available for server {self.server.name}"
                        )
            except Exception as e:
                # Check if this is an encryption mismatch error for OAuth tokens
                from .exceptions import MCPEncryptionMismatchError
                if isinstance(e, MCPEncryptionMismatchError):
                    # Re-raise encryption mismatch errors for OAuth tokens
                    raise e
                
                oauth_failed = True
                log.warning(
                    f"OAuth authentication failed for server {self.server.name}: {e}"
                )

        # 2. Add manual headers (can supplement or override OAuth)
        if self.server.headers:
            # Check if headers are encrypted
            if (
                isinstance(self.server.headers, dict)
                and "encrypted" in self.server.headers
            ):
                try:
                    decrypted_headers_json = decrypt_data(
                        self.server.headers["encrypted"], WEBUI_SECRET_KEY
                    )
                    decrypted_headers = json.loads(decrypted_headers_json)
                    headers.update(decrypted_headers)
                    log.debug(
                        f"Using encrypted manual headers for server {self.server.name}"
                    )
                except Exception as e:
                    # Encryption failure - likely key mismatch
                    from .exceptions import MCPEncryptionMismatchError
                    
                    log.error(f"Failed to decrypt headers for MCP server {self.server.name}: {e}")
                    raise MCPEncryptionMismatchError(
                        message=f"Encryption key mismatch for MCP server '{self.server.name}'. The server configuration appears to be encrypted with a different key.",
                        server_id=self.server.id,
                        server_name=self.server.name,
                        original_exception=e
                    )
            else:
                headers.update(self.server.headers)
                log.debug(f"Using manual headers for server {self.server.name}")

        # 3. Check if we have any authentication
        has_auth = any(
            key.lower() in ["authorization", "x-api-key", "x-auth-token"]
            for key in headers.keys()
        )

        if oauth_failed and not has_auth:
            # OAuth was configured but failed, and no manual auth headers
            from .exceptions import MCPAuthenticationError
            
            # Determine if this is missing tokens vs expired tokens
            challenge_type = "oauth"
            requires_reauth = True
            error_message = f"OAuth token missing or expired for server {self.server.name}. Please re-authenticate."
            
            raise MCPAuthenticationError(
                message=error_message,
                server_id=self.server.id,
                server_name=self.server.name,
                tool_name="unknown",  # Tool name not available at header validation level
                challenge_type=challenge_type,
                requires_reauth=requires_reauth,
                auth_url=None,
                instructions="Please click the login button to authenticate with the OAuth provider."
            )

        return headers

    async def connect(self) -> bool:
        """Test connection using the official SDK pattern - same as test method"""
        try:
            log.info(
                f"Connecting to MCP server: {self.server.name} at {self.server.http_url}"
            )

            async def connect_operation(session):
                tools_result = await session.list_tools()
                self.tools_cache = tools_result.tools
                return True

            await self._execute_with_session(connect_operation)
            log.info(f"Successfully connected to MCP server: {self.server.name}")
            return True

        except Exception as e:
            log.error("Failed to connect to MCP server %s: %s", self.server.name, e)
            return False

    async def disconnect(self):
        """Disconnect - no longer needed with official SDK pattern"""
        # Clear caches
        self.tools_cache = None
        self.prompts_cache = None
        self.resources_cache = None
        log.debug("Disconnected from MCP server: %s", self.server.name)

    async def get_available_tools(self) -> List[Tool]:
        """Get list of available tools from MCP server using official SDK pattern"""
        # Return cached tools if available
        if self.tools_cache:
            return self.tools_cache

        try:
            async def get_tools_operation(session):
                tools_result = await session.list_tools()
                self.tools_cache = tools_result.tools
                return self.tools_cache

            return await self._execute_with_session(get_tools_operation, timeout_seconds=10)

        except Exception as e:
            log.error("Failed to get tools from MCP server %s: %s", self.server.name, e)

            # Check if this is an authentication error
            is_auth_error, challenge_type, auth_url, instructions = self._is_authentication_error(e)
            if is_auth_error:
                from open_webui.utils.mcp.exceptions import MCPAuthenticationError

                # Extract a cleaner error message for display
                error_message = str(e)
                if "TaskGroup" in error_message or "ExceptionGroup" in error_message:
                    # Try to extract the actual HTTP error from nested exceptions
                    if "401 Unauthorized" in error_message:
                        if "Client error '401 Unauthorized' for url" in error_message:
                            error_message = "401 Unauthorized - Authentication token expired or invalid"
                        else:
                            error_message = "401 Unauthorized"
                    elif "HTTPStatusError" in error_message and "401" in error_message:
                        error_message = "401 Unauthorized - Authentication required"
                    else:
                        # Look for nested exceptions in ExceptionGroup
                        import re
                        # Try to find a more meaningful error in the nested exceptions
                        match = re.search(r"HTTPStatusError.*?'([^']*)'", error_message)
                        if match:
                            error_message = match.group(1)
                        else:
                            error_message = "Authentication failed - token expired or invalid"

                raise MCPAuthenticationError(
                    message=error_message,
                    server_id=self.server.id,
                    server_name=self.server.name,
                    tool_name="get_available_tools",
                    challenge_type=challenge_type,
                    requires_reauth=True,
                    auth_url=auth_url,
                    instructions=instructions,
                    original_exception=e
                )

            # Not an auth error, re-raise the exception so calling code can handle it properly
            raise e

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool with arguments using official SDK pattern"""
        try:
            async def call_tool_operation(session):
                result = await session.call_tool(tool_name, arguments)

                # Properly handle the CallToolResult object
                if hasattr(result, "content") and result.content:
                    # result.content is a list of content objects
                    content_texts = []
                    for content_item in result.content:
                        if hasattr(content_item, "text"):
                            content_texts.append(content_item.text)
                        elif (
                            isinstance(content_item, dict)
                            and "text" in content_item
                        ):
                            content_texts.append(content_item["text"])
                        else:
                            # Handle other content types
                            content_texts.append(str(content_item))

                    return (
                        "\n".join(content_texts)
                        if content_texts
                        else "No content returned"
                    )
                else:
                    return result

            return await self._execute_with_session(call_tool_operation, timeout_seconds=10)

        except asyncio.TimeoutError:
            log.error("Timeout calling tool %s on %s", tool_name, self.server.name)
            raise Exception(f"Tool call timeout: {tool_name}")
        except Exception as e:
            log.error("Failed to call tool %s: %s", tool_name, e)
            log.error("Exception type: %s", type(e).__name__)

            # Try to extract more details from the exception
            if hasattr(e, "__cause__") and e.__cause__:
                log.error("Underlying cause: %s", e.__cause__)

            if hasattr(e, "args") and e.args:
                log.error("Exception args: %s", e.args)

            # Import traceback for better error details
            import traceback

            log.error("Full traceback: %s", traceback.format_exc())

            # Check if this is an authentication error
            is_auth_error, challenge_type, auth_url, instructions = self._is_authentication_error(e)
            if is_auth_error:
                from open_webui.utils.mcp.exceptions import MCPAuthenticationError

                # Extract a cleaner error message for display
                error_message = str(e)
                if "TaskGroup" in error_message or "ExceptionGroup" in error_message:
                    # Try to extract the actual HTTP error from nested exceptions
                    if "401 Unauthorized" in error_message:
                        if "Client error '401 Unauthorized' for url" in error_message:
                            error_message = "401 Unauthorized - Authentication token expired or invalid"
                        else:
                            error_message = "401 Unauthorized"
                    elif "HTTPStatusError" in error_message and "401" in error_message:
                        error_message = "401 Unauthorized - Authentication required"
                    else:
                        # Look for nested exceptions in ExceptionGroup
                        import re
                        # Try to find a more meaningful error in the nested exceptions
                        match = re.search(r"HTTPStatusError.*?'([^']*)'", error_message)
                        if match:
                            error_message = match.group(1)
                        else:
                            error_message = "Authentication failed - token expired or invalid"

                raise MCPAuthenticationError(
                    message=error_message,
                    server_id=self.server.id,
                    server_name=self.server.name,
                    tool_name=tool_name,
                    challenge_type=challenge_type,
                    requires_reauth=True,
                    auth_url=auth_url,
                    instructions=instructions,
                    original_exception=e
                )

            raise

    def _is_authentication_error(self, exception: Exception) -> tuple[bool, str, str, str]:
        """Detect 401/authentication errors and determine challenge type.

        Returns:
            tuple: (is_auth_error, challenge_type, auth_url, instructions)
        """
        error_str = str(exception).lower()
        auth_indicators = [
            "401", "unauthorized", "authentication required",
            "token expired", "invalid token", "access denied",
            "forbidden", "oauth", "login required", "credentials required"
        ]

        # Check main exception message
        is_auth_error = any(indicator in error_str for indicator in auth_indicators)

        # Function to recursively check ExceptionGroup and exception chains
        def check_exception_recursively(exc, depth=0, max_depth=15) -> bool:
            if depth >= max_depth:
                return False

            # Check current exception for auth indicators
            exc_str = str(exc).lower()
            if any(indicator in exc_str for indicator in auth_indicators):
                return True

            # Check for httpx.HTTPStatusError
            if "HTTPStatusError" in str(type(exc)):
                if hasattr(exc, "response"):
                    response = exc.response
                    if (hasattr(response, "status_code") and response.status_code == 401):
                        return True

            # If this is an ExceptionGroup, check all nested exceptions
            if hasattr(exc, "exceptions"):  # ExceptionGroup has .exceptions attribute
                for nested_exc in exc.exceptions:
                    if check_exception_recursively(nested_exc, depth + 1, max_depth):
                        return True

            # Check exception chain (__cause__, __context__)
            if hasattr(exc, '__cause__') and exc.__cause__:
                if check_exception_recursively(exc.__cause__, depth + 1, max_depth):
                    return True
            if hasattr(exc, '__context__') and exc.__context__:
                if check_exception_recursively(exc.__context__, depth + 1, max_depth):
                    return True

            return False

        # Check if this is an ExceptionGroup or TaskGroup error
        if not is_auth_error and ("ExceptionGroup" in str(type(exception)) or "TaskGroup" in str(exception)):
            log.debug("Detected ExceptionGroup/TaskGroup, checking nested exceptions for auth errors")
            is_auth_error = check_exception_recursively(exception)

        # Fallback: Check exception chain for HTTP status errors (original logic)
        if not is_auth_error:
            current_exception = exception
            max_depth = 10
            depth = 0

            while current_exception and depth < max_depth:
                depth += 1

                # Check for httpx.HTTPStatusError
                if "HTTPStatusError" in str(type(current_exception)):
                    if hasattr(current_exception, "response"):
                        response = current_exception.response
                        if (hasattr(response, "status_code") and response.status_code == 401):
                            is_auth_error = True
                            break

                # Move to next exception in chain
                current_exception = getattr(current_exception, "__cause__", None)

        if not is_auth_error:
            return False, "none", None, None

        # Determine challenge type based on server configuration first, then error patterns
        challenge_type = "manual"  # Default to manual
        auth_url = None
        instructions = None

        # Check server's OAuth configuration first
        if self.server.oauth_config:
            oauth_enabled = False
            try:
                if isinstance(self.server.oauth_config, dict):
                    oauth_enabled = self.server.oauth_config.get("enabled", False)
                else:
                    # Try to parse as MCPOAuthConfig
                    try:
                        from open_webui.models.mcp_servers import MCPOAuthConfig
                        oauth_config = MCPOAuthConfig(**self.server.oauth_config)
                        oauth_enabled = oauth_config.enabled
                    except Exception:
                        # Fallback to dict access
                        oauth_enabled = getattr(self.server.oauth_config, 'enabled', False)

                if oauth_enabled:
                    challenge_type = "oauth"
                    log.info(f"Server {self.server.name} has OAuth enabled, setting challenge_type to oauth")
            except Exception as e:
                log.warning(f"Failed to check OAuth config for server {self.server.name}: {e}")

        # Fallback to error pattern detection if OAuth not detected from config
        if challenge_type == "manual":
            # Check for OAuth-specific patterns in error message
            oauth_patterns = ["oauth", "authorization_code", "redirect_uri", "client_id", "access_token", "refresh_token"]
            if any(pattern in error_str for pattern in oauth_patterns):
                challenge_type = "oauth"
                # Try to extract auth URL from error message
                import re
                url_match = re.search(r'https?://[^\s<>"{}|\\^`\[\]]+', str(exception))
                if url_match:
                    auth_url = url_match.group(0)

            # Check for API key patterns
            elif any(pattern in error_str for pattern in ["api_key", "api-key", "apikey", "bearer token"]):
                challenge_type = "api_key"
                instructions = "Please update your API key in the MCP server configuration."

            # Check for token refresh patterns (still OAuth but expired)
            elif any(pattern in error_str for pattern in ["token expired", "token_expired", "expired_token"]):
                challenge_type = "oauth"  # Likely OAuth token refresh needed

        # Set appropriate instructions based on challenge type
        if challenge_type == "oauth" and not instructions:
            instructions = f"OAuth token expired or invalid for {self.server.name}. Please re-authenticate."
        elif challenge_type == "manual" and not instructions:
            instructions = f"Authentication failed. Please check your credentials and server configuration for {self.server.name}."

        return True, challenge_type, auth_url, instructions

    async def get_available_prompts(self) -> List[Any]:
        """Get list of available prompts from MCP server using official SDK pattern"""
        if self.prompts_cache:
            return self.prompts_cache

        try:
            async def get_prompts_operation(session):
                result = await session.list_prompts()
                prompts = result.prompts if hasattr(result, "prompts") else []
                self.prompts_cache = prompts
                return prompts

            return await self._execute_with_session(get_prompts_operation)

        except Exception as e:
            log.error(
                f"Failed to get available prompts from MCP server {self.server.name}: {e}"
            )
            return []

    async def get_prompt(
        self, prompt_name: str, arguments: Optional[Dict[str, str]] = None
    ) -> Any:
        """Get a specific prompt with arguments using official SDK pattern"""
        try:
            async def get_prompt_operation(session):
                result = await session.get_prompt(prompt_name, arguments or {})
                return result.messages if hasattr(result, "messages") else result

            return await self._execute_with_session(get_prompt_operation)

        except Exception as e:
            log.error(
                f"Failed to get prompt {prompt_name} from MCP server {self.server.name}: {e}"
            )
            raise

    async def get_available_resources(self) -> List[Any]:
        """Get list of available resources from MCP server using official SDK pattern"""
        if self.resources_cache:
            return self.resources_cache

        try:
            async def get_resources_operation(session):
                result = await session.list_resources()
                resources = result.resources if hasattr(result, "resources") else []
                self.resources_cache = resources
                return resources

            return await self._execute_with_session(get_resources_operation)

        except Exception as e:
            log.error(
                f"Failed to get available resources from MCP server {self.server.name}: {e}"
            )
            return []

    async def read_resource(self, resource_uri: str) -> Any:
        """Read a specific resource using official SDK pattern"""
        try:
            async def read_resource_operation(session):
                result = await session.read_resource(resource_uri)
                return result.contents if hasattr(result, "contents") else result

            return await self._execute_with_session(read_resource_operation)

        except Exception as e:
            log.error(
                f"Failed to read resource {resource_uri} from MCP server {self.server.name}: {e}"
            )
            raise