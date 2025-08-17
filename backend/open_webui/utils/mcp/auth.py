"""
MCP OAuth and authentication handling
"""
import asyncio
import base64
import hashlib
import json
import logging
import secrets
import re
import time
import threading
from typing import Optional, Dict, Any
from urllib.parse import urlencode, urlparse

from .core import (
    MCP_AVAILABLE, MCP_PROTOCOL_VERSION, 
    TokenStorage, OAuthClientInformationFull, OAuthClientMetadata, OAuthToken,
    OAuthClientProvider, streamablehttp_client, ClientSession,
    create_mcp_client_info
)

from open_webui.models.mcp_servers import MCPServerModel, MCPServers, MCPServerStatus
from open_webui.env import WEBUI_SECRET_KEY
from open_webui.config import REDIS_URL, WEBUI_URL
from open_webui.utils.auth import decrypt_data, encrypt_data
from open_webui.utils.redis import get_redis_connection

log = logging.getLogger(__name__)


def _extract_exp_from_jwt(access_token: str) -> Optional[int]:
    """Extract exp (unix epoch seconds) from a JWT access token without verification."""
    try:
        if not access_token or access_token.count(".") != 2:
            return None
        header_b64, payload_b64, _ = access_token.split(".")
        # Base64url decode with padding
        def b64url_decode(data: str) -> bytes:
            padding = '=' * (-len(data) % 4)
            return base64.urlsafe_b64decode(data + padding)

        payload_bytes = b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8", errors="ignore"))
        exp = payload.get("exp")
        if isinstance(exp, int):
            return exp
        # Sometimes exp can be string
        if isinstance(exp, str) and exp.isdigit():
            return int(exp)
        return None
    except Exception:
        return None


class DatabaseTokenStorage(TokenStorage):
    """Token storage implementation using Open WebUI database."""

    def __init__(self, server_id: str, user_id: str = None):
        self.server_id = server_id
        self.user_id = user_id

        # If user_id not provided, try to get it from the server record
        if not self.user_id:
            server = MCPServers.get_mcp_server_by_id(server_id)
            if server:
                self.user_id = server.user_id

    async def get_tokens(self) -> OAuthToken | None:
        """Get stored OAuth tokens from database."""
        server = MCPServers.get_mcp_server_by_id(self.server_id)
        if not server or not server.oauth_tokens:
            return None

        try:
            # Try to load as plain JSON first (new format)
            try:
                token_data = json.loads(server.oauth_tokens)
                return OAuthToken(**token_data)
            except json.JSONDecodeError:
                # Fall back to decryption for old encrypted tokens
                try:
                    decrypted_tokens = decrypt_data(server.oauth_tokens, WEBUI_SECRET_KEY)
                    token_data = json.loads(decrypted_tokens)
                    return OAuthToken(**token_data)
                except Exception as decrypt_error:
                    log.error(f"Failed to decrypt OAuth tokens for server {self.server_id}: {decrypt_error}")
                    # Check if this is an encryption key mismatch
                    if "padding" in str(decrypt_error).lower() or "decrypt" in str(decrypt_error).lower():
                        from .exceptions import MCPEncryptionMismatchError
                        server = MCPServers.get_mcp_server_by_id(self.server_id)
                        server_name = server.name if server else "Unknown"
                        raise MCPEncryptionMismatchError(
                            message=f"OAuth token encryption key mismatch for server '{server_name}'. The server's OAuth tokens are encrypted with a different key.",
                            server_id=self.server_id,
                            server_name=server_name,
                            original_exception=decrypt_error
                        )
                    return None
        except Exception as e:
            # Re-raise MCPEncryptionMismatchError without wrapping
            from .exceptions import MCPEncryptionMismatchError
            if isinstance(e, MCPEncryptionMismatchError):
                raise e
            log.error(f"Failed to load OAuth tokens for server {self.server_id}: {e}")
            return None

    async def set_tokens(self, tokens: OAuthToken | None) -> None:
        """Store OAuth tokens in database."""
        try:
            from open_webui.models.mcp_servers import MCPServerUpdateForm

            if not self.user_id:
                raise ValueError(f"User ID required to update server {self.server_id}")

            if tokens is None:
                # Clear tokens
                MCPServers.update_mcp_server_by_id(
                    self.server_id, 
                    MCPServerUpdateForm(oauth_tokens=None, token_expires_at=None), 
                    self.user_id
                )
                log.info(f"OAuth tokens cleared for server {self.server_id}")
            else:
                # Serialize tokens
                token_data = (
                    tokens.model_dump()
                    if hasattr(tokens, "model_dump")
                    else dict(tokens)
                )
                token_json = json.dumps(token_data)

                # Extract expiration timestamp from token
                expires_at = None
                if hasattr(tokens, 'expires_at') and tokens.expires_at:
                    expires_at = tokens.expires_at
                elif hasattr(tokens, 'expires_in') and tokens.expires_in:
                    expires_at = int(time.time()) + tokens.expires_in
                elif 'expires_in' in token_data and token_data['expires_in']:
                    expires_at = int(time.time()) + token_data['expires_in']
                else:
                    # Derive from JWT exp if available
                    access_token = token_data.get('access_token')
                    jwt_exp = _extract_exp_from_jwt(access_token) if access_token else None
                    if jwt_exp:
                        expires_at = jwt_exp

                # Encrypt tokens at rest
                encrypted_tokens = encrypt_data(token_json, WEBUI_SECRET_KEY)

                # Update server with encrypted tokens AND expiration timestamp
                MCPServers.update_mcp_server_by_id(
                    self.server_id,
                    MCPServerUpdateForm(
                        oauth_tokens=encrypted_tokens,
                        token_expires_at=expires_at
                    ),
                    self.user_id,
                )
                log.info(f"OAuth tokens stored (encrypted) for server {self.server_id}")
        except Exception as e:
            log.error(f"Failed to store OAuth tokens for server {self.server_id}: {e}")
            raise

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        """Get stored client information from database."""
        server = MCPServers.get_mcp_server_by_id(self.server_id)
        if not server or not server.oauth_config:
            return None

        oauth_config = server.oauth_config
        if not isinstance(oauth_config, dict):
            return None

        client_info_data = oauth_config.get("client_info")
        if not client_info_data:
            return None

        try:
            return OAuthClientInformationFull(**client_info_data)
        except Exception as e:
            log.error(f"Failed to load client info for server {self.server_id}: {e}")
            return None

    async def set_client_info(
        self, client_info: OAuthClientInformationFull | None
    ) -> None:
        """Store client information in database."""
        try:
            from open_webui.models.mcp_servers import MCPServerUpdateForm

            if not self.user_id:
                raise ValueError(f"User ID required to update server {self.server_id}")

            server = MCPServers.get_mcp_server_by_id(self.server_id)
            if not server:
                raise ValueError(f"Server {self.server_id} not found")

            # Update oauth_config with client info
            oauth_config = server.oauth_config or {}
            if not isinstance(oauth_config, dict):
                oauth_config = {}

            oauth_config["client_info"] = (
                client_info.model_dump()
                if hasattr(client_info, "model_dump")
                else dict(client_info)
            )

            MCPServers.update_mcp_server_by_id(
                self.server_id,
                MCPServerUpdateForm(oauth_config=oauth_config),
                self.user_id,
            )
            log.info(f"OAuth client info stored for server {self.server_id}")
        except Exception as e:
            log.error(f"Failed to store client info for server {self.server_id}: {e}")
            raise


class MCPOAuthManager:
    """OAuth manager using the official MCP SDK."""

    def __init__(self):
        self.redis_client = (
            get_redis_connection(REDIS_URL, None, decode_responses=True)
            if REDIS_URL
            else None
        )

    async def discover_and_initiate_oauth(
        self, 
        server_id: str, 
        mcp_server_url: str, 
        base_url: str, 
        user_id: str = None,
        # Optional direct OAuth parameters
        direct_oauth_issuer: str = None,
        direct_oauth_client_id: str = None,
        direct_oauth_scopes: list[str] = None,
        direct_oauth_resource: str = None
    ) -> Dict[str, Any]:
        """
        Unified OAuth discovery and initiation method.
        
        This method attempts OAuth discovery in the following order:
        1. Try existing manual OAuth configuration (if already configured)
        2. Try MCP server auto-discovery (WWW-Authenticate header) - works for CCIQ, Neon
        3. Fall back to direct OAuth if parameters provided - works for Azure AD direct
        4. Return error if no method works
        
        Args:
            server_id: MCP server ID
            mcp_server_url: MCP server URL
            base_url: Base URL for redirects
            user_id: User ID for token storage
            direct_oauth_issuer: Optional direct OAuth issuer URL
            direct_oauth_client_id: Optional direct OAuth client ID  
            direct_oauth_scopes: Optional direct OAuth scopes
            direct_oauth_resource: Optional direct OAuth resource parameter
        """
        if not MCP_AVAILABLE:
            return {"success": False, "error": "MCP SDK not available"}

        try:
            log.info(f"Starting unified OAuth discovery for MCP server: {mcp_server_url}")

            # STEP 1: Try existing manual OAuth configuration first (if server already configured)
            if server_id:  # Only check for existing servers, not new ones
                try:
                    server = MCPServers.get_mcp_server_by_id(server_id)
                    if server and server.oauth_config:
                        oauth_config = server.oauth_config
                        if isinstance(oauth_config, dict) and oauth_config.get("enabled"):
                            log.info(f"Using existing manual OAuth configuration for {server.name}")
                            return await self.start_oauth_flow(server_id, user_id, base_url)
                except Exception as e:
                    log.info(f"Manual OAuth config failed: {e}")

            # STEP 2: Try MCP server auto-discovery (this works for CCIQ, Neon, etc.)
            try:
                result = await self.discover_oauth_from_mcp_server(
                    server_id, mcp_server_url, base_url, user_id
                )
                if result.get("success"):
                    log.info(f"MCP auto-discovery successful for {mcp_server_url}")
                    return result
                else:
                    log.info(f"MCP auto-discovery failed: {result.get('error')}")
            except Exception as e:
                log.info(f"MCP auto-discovery exception: {e}")

            # STEP 3: Try direct OAuth if parameters provided
            if direct_oauth_issuer and direct_oauth_client_id:
                log.info(f"Attempting direct OAuth flow for {mcp_server_url}")
                return await self.initiate_direct_oauth_flow(
                    server_id=server_id,
                    issuer_url=direct_oauth_issuer,
                    client_id=direct_oauth_client_id,
                    scopes=direct_oauth_scopes or [],
                    base_url=base_url,
                    user_id=user_id,
                    resource=direct_oauth_resource
                )

            # STEP 4: No OAuth method worked
            return {
                "success": False,
                "error": "OAuth discovery failed. Server does not support auto-discovery and no direct OAuth parameters provided.",
                "suggestions": [
                    "Check if the MCP server supports OAuth",
                    "Verify the server URL is correct", 
                    "Configure manual OAuth settings in Advanced Configuration",
                    "Try providing direct OAuth parameters (issuer, client_id)",
                    "Check server documentation for authentication requirements"
                ]
            }

        except Exception as e:
            log.error(f"Unified OAuth discovery failed for {mcp_server_url}: {e}")
            return {
                "success": False, 
                "error": f"OAuth discovery failed: {str(e)}"
            }

    async def discover_oauth_from_mcp_server(
        self, server_id: str, mcp_server_url: str, base_url: str, user_id: str = None
    ) -> Dict[str, Any]:
        """Discover OAuth configuration from MCP server using SDK."""
        if not MCP_AVAILABLE:
            return {"success": False, "error": "MCP SDK not available"}

        try:
            log.info(f"Starting OAuth discovery for MCP server: {mcp_server_url}")

            # Create token storage for this server
            token_storage = DatabaseTokenStorage(server_id, user_id)

            # Create OAuth client metadata following the SDK example
            client_metadata = OAuthClientMetadata(
                client_name="Open WebUI",
                redirect_uris=[f"{base_url}/api/v1/mcp-servers/oauth/callback"],
                grant_types=["authorization_code", "refresh_token"],
                response_types=["code"],
                token_endpoint_auth_method="client_secret_post",
            )

            # Try to connect without auth first to see if OAuth is required
            try:
                async with streamablehttp_client(mcp_server_url) as (
                    read,
                    write,
                    get_session_id,
                ):
                    async with ClientSession(
                        read, write, 
                        client_info=create_mcp_client_info()
                    ) as session:
                        await session.initialize()
                        # If we get here without OAuth, the server doesn't require it
                        return {
                            "success": False,
                            "error": "Server does not require OAuth authentication",
                        }
            except Exception as e:
                # Check for 401 errors indicating OAuth is required
                return self._handle_oauth_discovery_exception(
                    e, server_id, mcp_server_url, client_metadata, user_id
                )

        except Exception as e:
            log.error(f"OAuth discovery failed: {e}")
            
            # Check if this is a manual config exception
            if hasattr(e, 'needs_manual_config'):
                # Re-raise to be handled by the router
                raise e
            
            return {"success": False, "error": f"OAuth discovery failed: {str(e)}"}

    def _handle_oauth_discovery_exception(
        self, e: Exception, server_id: str, mcp_server_url: str, 
        client_metadata: OAuthClientMetadata, user_id: str
    ) -> Dict[str, Any]:
        """Handle OAuth discovery exception and check for 401 errors."""
        error_str = str(e)
        found_401 = False

        # Check if the main exception string contains 401
        if "401" in error_str and "Unauthorized" in error_str:
            found_401 = True
            log.info("Found 401 Unauthorized in main exception message")

        # Try to extract HTTPStatusError from the exception chain
        if not found_401:
            found_401 = self._extract_401_from_exception_chain(e)

        if found_401:
            log.info("Server requires OAuth authentication - 401 detected")
            return self._create_oauth_config(server_id, mcp_server_url, client_metadata, user_id)
        else:
            log.error(f"Could not find 401 response in exception chain. Exception type: {type(e)}")
            return {"success": False, "error": f"Connection failed: {error_str}"}

    def _extract_401_from_exception_chain(self, e: Exception) -> bool:
        """Extract 401 errors from nested exception chains."""
        # Handle ExceptionGroup from MCP SDK (anyio TaskGroups)
        if "ExceptionGroup" in str(type(e)) or "TaskGroup" in str(e):
            log.info("Detected MCP SDK ExceptionGroup, extracting nested errors")

            # Walk through the exception chain to find HTTP errors
            current_exception = e
            max_depth = 10
            depth = 0

            while current_exception and depth < max_depth:
                depth += 1

                # Check for httpx.HTTPStatusError
                if "HTTPStatusError" in str(type(current_exception)):
                    if hasattr(current_exception, "response"):
                        response = current_exception.response
                        if (
                            hasattr(response, "status_code")
                            and response.status_code == 401
                        ):
                            log.info(f"Found 401 status in HTTPStatusError at depth {depth}")
                            return True

                # Check if it's an ExceptionGroup and look at nested exceptions
                if hasattr(current_exception, "exceptions"):
                    for nested_exception in current_exception.exceptions:
                        if "HTTPStatusError" in str(type(nested_exception)):
                            if hasattr(nested_exception, "response"):
                                response = nested_exception.response
                                if (
                                    hasattr(response, "status_code")
                                    and response.status_code == 401
                                ):
                                    log.info("Found 401 in nested HTTPStatusError")
                                    return True
                        # Also check nested exception messages
                        if "401" in str(nested_exception) and "Unauthorized" in str(nested_exception):
                            log.info("Found 401 in nested exception message")
                            return True

                # Move to next exception in chain
                next_exception = None
                if (
                    hasattr(current_exception, "__cause__")
                    and current_exception.__cause__
                ):
                    next_exception = current_exception.__cause__
                elif (
                    hasattr(current_exception, "__context__")
                    and current_exception.__context__
                ):
                    next_exception = current_exception.__context__

                current_exception = next_exception

        return False

    def _create_oauth_config(
        self, server_id: str, mcp_server_url: str, 
        client_metadata: OAuthClientMetadata, user_id: str
    ) -> Dict[str, Any]:
        """Create OAuth configuration for the server."""
        # Convert client_metadata to dict safely
        client_metadata_dict = (
            client_metadata.model_dump()
            if hasattr(client_metadata, "model_dump")
            else dict(client_metadata)
        )

        # Convert AnyUrl objects to strings for JSON serialization
        if "redirect_uris" in client_metadata_dict:
            client_metadata_dict["redirect_uris"] = [
                str(uri) for uri in client_metadata_dict["redirect_uris"]
            ]

        oauth_config = {
            "enabled": True,
            "config_method": "auto",
            "client_metadata": client_metadata_dict,
        }

        # Create or update permanent server with OAuth config
        return self._update_existing_server(server_id, oauth_config, user_id)

    def _create_permanent_server(
        self, server_id: str, mcp_server_url: str, oauth_config: Dict, user_id: str
    ) -> Dict[str, Any]:
        """Create permanent server immediately instead of temporary."""
        from open_webui.models.mcp_servers import MCPServerForm
        import json

        # Try to get the original server name from Redis temporary data
        server_name = "MCP"  # Default fallback name
        if server_id.startswith("temp_mcp_") and self.redis_client:
            try:
                redis_key = f"open-webui:temp_mcp_server:{server_id}"
                temp_data_json = self.redis_client.get(redis_key)
                if temp_data_json:
                    temp_data = json.loads(temp_data_json)
                    server_name = temp_data.get("name", "MCP")
                    log.info(f"Retrieved original server name '{server_name}' from temporary data")
            except Exception as e:
                log.warning(f"Failed to retrieve original server name from Redis: {e}")

        server_form = MCPServerForm(
            name=server_name,
            http_url=mcp_server_url,
            oauth_config=oauth_config,
        )

        permanent_server = MCPServers.insert_new_mcp_server(user_id, server_form)
        if permanent_server:
            server_id = permanent_server.id
            log.info(f"Created permanent server {server_id} with OAuth config")
            return {
                "success": True,
                "config_method": "auto",
                "oauth_required": True,
                "client_metadata": oauth_config["client_metadata"],
                "server_id": server_id,
            }
        else:
            log.error("Failed to create permanent server")
            return {"success": False, "error": "Failed to create server"}

    def _update_existing_server(
        self, server_id: str, oauth_config: Dict, user_id: str
    ) -> Dict[str, Any]:
        """Update existing permanent server with OAuth config."""
        from open_webui.models.mcp_servers import MCPServerUpdateForm

        if user_id:
            MCPServers.update_mcp_server_by_id(
                server_id,
                MCPServerUpdateForm(oauth_config=oauth_config),
                user_id,
            )
        else:
            # Fallback: update without user_id if not provided
            server = MCPServers.get_mcp_server_by_id(server_id)
            if server:
                MCPServers.update_mcp_server_by_id(
                    server_id,
                    MCPServerUpdateForm(oauth_config=oauth_config),
                    server.user_id,
                )

        return {
            "success": True,
            "config_method": "auto",
            "oauth_required": True,
            "client_metadata": oauth_config["client_metadata"],
            "server_id": server_id,
        }

    async def start_oauth_flow(
        self, server_id: str, user_id: str, base_url: str, scopes: list = None
    ) -> Dict[str, Any]:
        """Start OAuth flow using the official MCP SDK."""
        if not MCP_AVAILABLE:
            return {"success": False, "error": "MCP SDK not available"}

        try:
            # Get permanent server from database
            server = MCPServers.get_mcp_server_by_id(server_id)
            if not server:
                return {"success": False, "error": "Server not found"}
            oauth_config = server.oauth_config

            # Get OAuth configuration from server
            if not oauth_config or not isinstance(oauth_config, dict):
                return {
                    "success": False,
                    "error": "OAuth not configured for this server",
                }

            client_metadata_dict = oauth_config.get("client_metadata", {})
            if not client_metadata_dict:
                return {"success": False, "error": "OAuth client metadata not found"}

            # Create token storage and OAuth provider
            token_storage = DatabaseTokenStorage(server_id, user_id)
            client_metadata = OAuthClientMetadata.model_validate(client_metadata_dict)

            # Implement OAuth metadata discovery
            log.info(f"Attempting OAuth metadata discovery for server {server_id}")
            return await self._perform_oauth_metadata_discovery(
                server, client_metadata_dict, user_id, base_url, scopes
            )

        except Exception as e:
            log.error(f"Failed to start OAuth flow: {e}")
            
            # Check if this is a manual config exception and re-raise it
            if hasattr(e, 'needs_manual_config'):
                raise e
                
            return {"success": False, "error": str(e)}

    async def _perform_oauth_metadata_discovery(
        self, server: MCPServerModel, client_metadata_dict: Dict, 
        user_id: str, base_url: str, scopes: list
    ) -> Dict[str, Any]:
        """Perform OAuth metadata discovery from MCP server."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    server.http_url,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
                    },
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "id": 1,
                        "params": {},
                    },
                    timeout=10.0,
                )

                if response.status_code == 401:
                    www_auth_header = response.headers.get("WWW-Authenticate", "")
                    log.info(f"Got WWW-Authenticate header: {www_auth_header}")

                    # Parse authorization server URL and fetch metadata
                    auth_server_url = self._parse_auth_server_url(www_auth_header, server.http_url)
                    metadata = await self._fetch_oauth_metadata(client, auth_server_url, www_auth_header)

                    if metadata:
                        return await self._complete_oauth_flow_setup(
                            metadata, server, client_metadata_dict, user_id, base_url, scopes
                        )

                # If we get here, OAuth metadata discovery failed
                error_msg = "OAuth metadata discovery failed - server does not support automatic OAuth configuration"
                
                # Create a custom exception with needs_manual_config info
                class OAuthConfigException(Exception):
                    def __init__(self, message):
                        super().__init__(message)
                        self.needs_manual_config = True
                
                raise OAuthConfigException(error_msg)

        except Exception as discovery_error:
            log.error(f"OAuth metadata discovery failed: {discovery_error}")
            
            # Create a custom exception with needs_manual_config info
            class OAuthConfigException(Exception):
                def __init__(self, message):
                    super().__init__(message)
                    self.needs_manual_config = True
            
            raise OAuthConfigException(f"OAuth metadata discovery failed - server does not support automatic OAuth configuration")

    def _parse_auth_server_url(self, www_auth_header: str, server_url: str) -> str:
        """Parse authorization server URL from WWW-Authenticate header."""
        auth_server_url = None

        # Try to extract realm or authorization server URL
        if "realm=" in www_auth_header:
            realm_match = re.search(r'realm="([^"]+)"', www_auth_header)
            if realm_match:
                realm = realm_match.group(1)
                log.info(f"Found realm: {realm}")

                # If realm looks like a URL, use it as auth server
                if realm.startswith(("http://", "https://")):
                    auth_server_url = realm
                else:
                    # Try common patterns for auth server discovery
                    base_domain = server_url.split("/")[2]  # Extract domain
                    auth_server_url = f"https://{base_domain}"

        if not auth_server_url:
            # Fallback: try to infer from MCP server URL
            parsed = urlparse(server_url)
            auth_server_url = f"{parsed.scheme}://{parsed.netloc}"

        log.info(f"Using authorization server URL: {auth_server_url}")
        return auth_server_url

    async def _fetch_oauth_metadata(
        self, client, auth_server_url: str, www_auth_header: str
    ) -> Optional[Dict]:
        """Fetch OAuth metadata from various discovery endpoints."""
        metadata = None

        # Method 1: Check for resource_metadata URL (RFC 9728)
        resource_metadata_url = None
        if "resource_metadata=" in www_auth_header:
            resource_match = re.search(r'resource_metadata="([^"]+)"', www_auth_header)
            if resource_match:
                resource_metadata_url = resource_match.group(1)
                log.info(f"Found resource_metadata URL: {resource_metadata_url}")

        # Try resource metadata first
        if resource_metadata_url:
            try:
                resource_response = await client.get(resource_metadata_url, timeout=10.0)
                if resource_response.status_code == 200:
                    resource_data = resource_response.json()
                    auth_servers = resource_data.get("authorization_servers", [])
                    if auth_servers:
                        auth_server_url = auth_servers[0]
                        log.info(f"Using auth server from resource metadata: {auth_server_url}")
            except Exception as e:
                log.warning(f"Failed to fetch resource metadata: {e}")

        # Method 2: Try standard OAuth Authorization Server Metadata (RFC 8414)
        metadata_url = f"{auth_server_url}/.well-known/oauth-authorization-server"
        try:
            log.info(f"Trying OAuth metadata at {metadata_url}")
            metadata_response = await client.get(metadata_url, timeout=10.0)
            if metadata_response.status_code == 200:
                metadata = metadata_response.json()
                log.info(f"Retrieved OAuth metadata from {metadata_url}")
        except Exception as e:
            log.warning(f"Failed to fetch OAuth metadata: {e}")

        # Method 3: Try OpenID Connect Discovery (fallback)
        if not metadata:
            oidc_url = f"{auth_server_url}/.well-known/openid-configuration"
            try:
                log.info(f"Trying OpenID Connect Discovery at {oidc_url}")
                oidc_response = await client.get(oidc_url, timeout=10.0)
                if oidc_response.status_code == 200:
                    metadata = oidc_response.json()
                    log.info(f"Retrieved OpenID Connect metadata from {oidc_url}")
            except Exception as e:
                log.warning(f"Failed to fetch OpenID Connect metadata: {e}")

        return metadata

    async def _complete_oauth_flow_setup(
        self, metadata: Dict, server: MCPServerModel, client_metadata_dict: Dict,
        user_id: str, base_url: str, scopes: list
    ) -> Dict[str, Any]:
        """Complete OAuth flow setup with Dynamic Client Registration."""
        authorization_endpoint = metadata.get("authorization_endpoint")
        token_endpoint = metadata.get("token_endpoint")

        if not authorization_endpoint:
            log.error("No authorization_endpoint found in OAuth metadata")
            return {"success": False, "error": "No authorization endpoint found"}

        # Try Dynamic Client Registration (DCR) if supported
        client_id = None
        client_secret = None

        registration_endpoint = metadata.get("registration_endpoint")
        if registration_endpoint:
            client_id, client_secret = await self._attempt_dynamic_client_registration(
                registration_endpoint, base_url, scopes
            )

        # If no client_id and no DCR endpoint, suggest manual configuration
        if not client_id and not registration_endpoint:
            return {
                "success": False,
                "error": "OAuth server does not support Dynamic Client Registration",
                "details": "This OAuth server requires manual client registration.",
                "needs_manual_config": True,
                "authorization_endpoint": authorization_endpoint,
                "token_endpoint": token_endpoint,
            }

        # Fallback to placeholder if DCR failed
        if not client_id:
            log.warning("No client_id available - using placeholder (OAuth will fail)")
            client_id = "placeholder_client_id"

        # Generate state and store OAuth state in Redis
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        default_scopes = metadata.get("scopes_supported", ["openid", "email", "profile", "groups", "offline_access"])
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": f"{base_url}/api/v1/mcp-servers/oauth/callback",
            "scope": " ".join(scopes or default_scopes),
            "state": state,
        }
        
        # Auto-detect Azure AD and set resource parameter to client_id for proper token audience
        issuer_url = metadata.get("issuer", "")
        resource = None
        if issuer_url and "login.microsoftonline.com" in issuer_url:
            # Don't add resource to authorization URL - Azure AD doesn't support it there
            # Only store it for token exchange
            resource = client_id
            log.debug(f"Azure AD detected, will use app-specific scope for token exchange")

        await self._store_oauth_state(
            state, server.id, user_id, metadata, client_metadata_dict, client_id, client_secret, server.http_url, resource
        )

        auth_url = f"{authorization_endpoint}?{urlencode(params)}"

        # Persist discovered endpoints and client info on server for future refresh fallbacks
        try:
            from open_webui.models.mcp_servers import MCPServerUpdateForm, MCPServers
            current_cfg = server.oauth_config or {}
            if not isinstance(current_cfg, dict):
                current_cfg = {}
            merged = {
                **current_cfg,
                "authorize_url": authorization_endpoint,
                "token_url": token_endpoint or current_cfg.get("token_url"),
                "registration_endpoint": registration_endpoint or current_cfg.get("registration_endpoint"),
                "client_id": client_id or current_cfg.get("client_id"),
                "client_secret": client_secret or current_cfg.get("client_secret"),
                "issuer_url": issuer_url or current_cfg.get("issuer_url"),
            }
            MCPServers.update_mcp_server_by_id(
                server.id,
                MCPServerUpdateForm(oauth_config=merged),
                user_id
            )
        except Exception as persist_err:
            log.warning(f"Failed to persist OAuth metadata to server config: {persist_err}")

        return {
            "success": True,
            "authorization_url": auth_url,
            "state": state,
            "metadata_discovered": True,
            "client_registered": client_id != "placeholder_client_id",
        }

    async def _attempt_dynamic_client_registration(
        self, registration_endpoint: str, base_url: str, scopes: list
    ) -> tuple[Optional[str], Optional[str]]:
        """Attempt Dynamic Client Registration (DCR)."""
        log.info(f"Attempting Dynamic Client Registration at {registration_endpoint}")
        
        try:
            import httpx
            
            dcr_request = {
                "client_name": "Open WebUI",
                "redirect_uris": [f"{base_url}/api/v1/mcp-servers/oauth/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post",
                "scope": " ".join(scopes or ["openid", "email", "profile", "groups", "offline_access"]),
            }

            async with httpx.AsyncClient() as client:
                dcr_response = await client.post(
                    registration_endpoint,
                    json=dcr_request,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0,
                )

                if dcr_response.status_code in [200, 201]:
                    dcr_data = dcr_response.json()
                    client_id = dcr_data.get("client_id")
                    client_secret = dcr_data.get("client_secret")
                    log.info(f"DCR successful - got client_id: {client_id[:8] if client_id else 'None'}...")
                    return client_id, client_secret
                else:
                    log.warning(f"DCR failed with status {dcr_response.status_code}: {dcr_response.text}")
                    
        except Exception as dcr_error:
            log.warning(f"DCR failed: {dcr_error}")
            
        return None, None

    async def _store_oauth_state(
        self, state: str, server_id: str, user_id: str, metadata: Dict,
        client_metadata_dict: Dict, client_id: str, client_secret: str, server_url: str,
        resource: str = None
    ) -> None:
        """Store OAuth state in Redis."""
        state_data = {
            "server_id": server_id,
            "user_id": user_id,
            "timestamp": time.time(),
            "oauth_metadata": metadata,
            "client_metadata": client_metadata_dict,
            "client_id": client_id,
            "client_secret": client_secret,
            "resource": resource,  # Add resource parameter for token exchange
            "oauth_provider_config": {
                "server_url": server_url,
                "client_metadata": client_metadata_dict,
            },
        }

        if self.redis_client:
            redis_key = f"open-webui:oauth_state:{state}"
            log.debug(f"Storing OAuth state in Redis: {redis_key}")
            self.redis_client.setex(
                redis_key,
                600,  # 10 minutes
                json.dumps(state_data),
            )
            log.debug(f"OAuth state stored successfully")
        else:
            log.warning("Redis not available, OAuth state cannot be stored")

    async def handle_oauth_callback(
        self, code: str, state: str, base_url: str = None
    ) -> Dict[str, Any]:
        """Handle OAuth callback using the official MCP SDK."""
        log.info(f"Processing OAuth callback for state: {state}")

        if not MCP_AVAILABLE:
            return {"success": False, "error": "MCP SDK not available"}

        try:
            # Retrieve state from Redis
            if not self.redis_client:
                return {"success": False, "error": "Redis required for OAuth state management"}

            log.debug(f"Looking up OAuth state in Redis")
            state_data_json = self.redis_client.get(f"open-webui:oauth_state:{state}")
            if not state_data_json:
                log.error(f"OAuth state not found in Redis: {state}")
                return {"success": False, "error": "Invalid or expired OAuth state"}

            state_data = json.loads(state_data_json)
            server_id = state_data["server_id"]
            user_id = state_data["user_id"]
            oauth_provider_config = state_data.get("oauth_provider_config", {})

            log.debug(f"Retrieved OAuth state for server: {server_id}")

            # Create token storage and exchange code for tokens
            token_storage = DatabaseTokenStorage(server_id, user_id)
            flow_type = state_data.get("flow_type", "mcp_proxy")  # Default to old behavior

            if flow_type == "direct_oauth":
                # Use direct OAuth 2.1 flow with any compliant provider
                await self._exchange_direct_oauth_code_for_tokens(
                    code, state_data, base_url, token_storage
                )
            elif oauth_provider_config:
                # Use legacy MCP proxy flow
                await self._exchange_oauth_code_for_tokens(
                    code, state_data, base_url, token_storage
                )
            else:
                # No OAuth provider configuration - this should not happen in normal flow
                raise Exception("No OAuth configuration found for token exchange")

            log.info(f"OAuth flow completed successfully for server {server_id}")

            # Update server status to connected since OAuth tokens are now available
            MCPServers.update_mcp_server_status(server_id, MCPServerStatus.connected)
            log.info(f"Updated server {server_id} status to connected")

            # Update Redis OAuth state to mark as completed
            await self._mark_oauth_state_completed(state, server_id)

            return {
                "success": True,
                "server_id": server_id,
                "flow_type": flow_type,
                "message": "OAuth authentication completed successfully",
            }

        except Exception as e:
            log.error(f"OAuth callback handling failed: {e}")
            return {"success": False, "error": str(e)}

    async def _exchange_oauth_code_for_tokens(
        self, code: str, state_data: Dict, base_url: str, token_storage: DatabaseTokenStorage
    ) -> None:
        """Exchange authorization code for real tokens using standard OAuth 2.1 flow."""
        try:
            import httpx

            # Get OAuth metadata from state
            oauth_metadata = state_data.get("oauth_metadata", {})
            client_id = state_data.get("client_id")
            client_secret = state_data.get("client_secret")
            resource = state_data.get("resource")  # Resource parameter for token audience
            token_endpoint = oauth_metadata.get("token_endpoint")

            if not all([token_endpoint, client_id, client_secret]):
                raise Exception("Missing OAuth configuration for token exchange")

            # Use base_url from parameter or fallback to main WEBUI_URL
            if not base_url:
                base_url = str(WEBUI_URL).rstrip("/")

            # Prepare token exchange request
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{base_url}/api/v1/mcp-servers/oauth/callback",
                "client_id": client_id,
                "client_secret": client_secret,
            }
            
            # Add resource parameter if present (needed for Azure AD to get proper token audience)
            if resource:
                # For Azure AD v2.0, use scope instead of resource parameter
                if "login.microsoftonline.com" in state_data.get("oauth_metadata", {}).get("issuer", ""):
                    # Azure AD v2.0 - use application-specific scope instead of resource parameter
                    # Format: {client_id}/.default to get all permissions for the app
                    app_scope = f"{resource}/.default"
                    current_scopes = token_data.get("scope", "").split()
                    if app_scope not in current_scopes:
                        # Replace generic scopes with app-specific scope for proper audience, include offline_access
                        token_data["scope"] = f"openid email profile offline_access {app_scope}"
                    log.debug(f"Using Azure AD app-specific scope: {app_scope}")
                else:
                    # Non-Azure AD - use resource parameter
                    token_data["resource"] = resource
                    log.debug(f"Using resource parameter for token exchange")

            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    token_response = response.json()

                    # Create OAuth token from response
                    expires_in = token_response.get("expires_in")
                    expires_at = None
                    if isinstance(expires_in, int):
                        expires_at = int(time.time()) + expires_in
                    else:
                        # Derive from JWT exp if possible
                        jwt_exp = _extract_exp_from_jwt(token_response.get("access_token"))
                        if jwt_exp:
                            expires_at = jwt_exp

                    real_token = OAuthToken(
                        access_token=token_response["access_token"],
                        token_type=token_response.get("token_type", "Bearer"),
                        expires_at=expires_at,
                        refresh_token=token_response.get("refresh_token"),
                        scope=token_response.get("scope"),
                    )

                    await token_storage.set_tokens(real_token)
                    # Persist token endpoint and client info for refresh fallback
                    try:
                        from open_webui.models.mcp_servers import MCPServerUpdateForm, MCPServers
                        server = MCPServers.get_mcp_server_by_id(token_storage.server_id)
                        current_cfg = server.oauth_config or {}
                        if not isinstance(current_cfg, dict):
                            current_cfg = {}
                        merged = {
                            **current_cfg,
                            "token_url": token_endpoint or current_cfg.get("token_url"),
                            "client_id": client_id or current_cfg.get("client_id"),
                            "client_secret": client_secret or current_cfg.get("client_secret"),
                        }
                        MCPServers.update_mcp_server_by_id(
                            token_storage.server_id,
                            MCPServerUpdateForm(oauth_config=merged),
                            token_storage.user_id,
                        )
                    except Exception as persist_err:
                        log.warning(f"Failed to persist token endpoint/client info: {persist_err}")
                    log.info(f"Successfully exchanged OAuth code for real tokens")
                else:
                    raise Exception(f"Token exchange failed with status {response.status_code}: {response.text}")

        except Exception as token_error:
            log.error(f"Failed to exchange OAuth code for real tokens: {token_error}")
            # For MCP proxy flow, we should also fail properly instead of using fake tokens
            raise token_error

    async def _mark_oauth_state_completed(self, state: str, server_id: str) -> None:
        """Mark OAuth state as completed in Redis."""
        redis_key = f"open-webui:oauth_state:{state}"
        if self.redis_client and self.redis_client.exists(redis_key):
            # Update the state to mark completion
            try:
                state_data_json = self.redis_client.get(redis_key)
                if state_data_json:
                    state_data = json.loads(state_data_json)
                    state_data["completed"] = True
                    state_data["completed_at"] = time.time()
                    
                    # Store updated state with shorter expiry (1 minute for cleanup)
                    self.redis_client.setex(redis_key, 60, json.dumps(state_data))
                    log.debug(f"Marked OAuth state as completed for server: {server_id}")
            except Exception as e:
                log.error(f"Failed to mark OAuth state as completed: {e}")
        else:
            log.debug(f"OAuth state not found in Redis for cleanup: {redis_key}")

    async def get_access_token(self, server_id: str) -> Optional[str]:
        """Get valid access token for server."""
        if not MCP_AVAILABLE:
            return None

        try:
            server = MCPServers.get_mcp_server_by_id(server_id)
            if not server:
                return None

            token_storage = DatabaseTokenStorage(server_id, server.user_id)
            tokens = await token_storage.get_tokens()

            if not tokens:
                return None

            # Proactive refresh: 5 minutes before expiry
            refresh_threshold = 300  # seconds
            now = time.time()

            # If DB has an expiry, use it; otherwise try to derive from JWT and persist for next time
            effective_expires_at = server.token_expires_at
            if not effective_expires_at and getattr(tokens, 'access_token', None):
                jwt_exp = _extract_exp_from_jwt(tokens.access_token)
                if jwt_exp:
                    effective_expires_at = jwt_exp
                    # Persist derived expiry for future checks
                    await token_storage.set_tokens(tokens)

            if effective_expires_at and now >= (effective_expires_at - refresh_threshold):
                # Token expired or nearing expiry, try to refresh
                if tokens.refresh_token:
                    refreshed_tokens = None

                    ### Use HTTP refresh - SDK doesnt work
                    refreshed_tokens = await self._refresh_tokens_via_http(server)

                    if refreshed_tokens:
                        log.debug(f"Refreshed tokens for server {server_id}")
                        # Persist refreshed tokens to update token_expires_at
                        await token_storage.set_tokens(refreshed_tokens)
                        return refreshed_tokens.access_token
                # Return existing token to allow a 401 and trigger background refresh retry
                return tokens.access_token

            return tokens.access_token
        except Exception as e:
            # Re-raise encryption mismatch errors without wrapping
            from .exceptions import MCPEncryptionMismatchError
            if isinstance(e, MCPEncryptionMismatchError):
                raise e
            
            log.error(f"Failed to get access token for server {server_id}: {e}")
            return None

    async def _refresh_tokens_via_http(self, server) -> Optional[OAuthToken]:
        """Fallback: refresh tokens directly via token endpoint using stored client info."""
        try:
            import httpx
            token_storage = DatabaseTokenStorage(server.id, server.user_id)
            tokens = await token_storage.get_tokens()
            if not tokens or not getattr(tokens, 'refresh_token', None):
                return None

            client_info = await token_storage.get_client_info()
            oauth_cfg = getattr(client_info, 'oauth_provider_config', {}) if client_info else {}
            # Try several locations for token endpoint
            token_endpoint = (
                (oauth_cfg.get('oauth_metadata', {}) or {}).get('token_endpoint')
                or oauth_cfg.get('token_endpoint')
                or (server.oauth_config or {}).get('token_url')
            )
            client_metadata = getattr(client_info, 'client_metadata', None)
            client_id = getattr(client_metadata, 'client_id', None) if client_metadata else (server.oauth_config or {}).get('client_id')
            client_secret = getattr(client_metadata, 'client_secret', None) if client_metadata else (server.oauth_config or {}).get('client_secret')
            issuer = (oauth_cfg.get('oauth_metadata', {}) or {}).get('issuer') if oauth_cfg else (server.oauth_config or {}).get('issuer_url', '')

            if not token_endpoint or not client_id:
                log.warning("HTTP refresh missing token_endpoint or client_id")
                return None

            data = {
                'grant_type': 'refresh_token',
                'refresh_token': tokens.refresh_token,
                'client_id': client_id,
            }
            if client_secret:
                data['client_secret'] = client_secret

            # Azure AD v2 requires scopes rather than resource
            if issuer and 'login.microsoftonline.com' in issuer:
                app_scope = f"{client_id}/.default"
                data['scope'] = f"openid email profile offline_access {app_scope}"

            async with httpx.AsyncClient() as client:
                resp = await client.post(token_endpoint, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10.0)
                if resp.status_code != 200:
                    log.warning(f"HTTP refresh failed: {resp.status_code} {resp.text}")
                    return None
                tr = resp.json()
                expires_in = tr.get('expires_in')
                expires_at = None
                if isinstance(expires_in, int):
                    expires_at = int(time.time()) + expires_in
                else:
                    jwt_exp = _extract_exp_from_jwt(tr.get('access_token'))
                    if jwt_exp:
                        expires_at = jwt_exp
                return OAuthToken(
                    access_token=tr['access_token'],
                    token_type=tr.get('token_type', 'Bearer'),
                    expires_at=expires_at,
                    refresh_token=tr.get('refresh_token', tokens.refresh_token),
                    scope=tr.get('scope'),
                )
        except Exception as e:
            # Re-raise encryption mismatch errors for OAuth tokens
            from .exceptions import MCPEncryptionMismatchError
            if isinstance(e, MCPEncryptionMismatchError):
                raise e
            
            log.error(f"HTTP refresh error: {e}")
            return None

    async def discover_and_configure_oauth(
        self, server_id: str, base_url: str
    ) -> Dict[str, Any]:
        """Discover OAuth configuration for server."""
        server = MCPServers.get_mcp_server_by_id(server_id)
        if not server:
            return {"success": False, "error": "Server not found"}

        return await self.discover_oauth_from_mcp_server(
            server_id, server.http_url, base_url
        )

    async def clear_tokens(self, server_id: str) -> None:
        """Clear OAuth tokens for a server."""
        try:
            server = MCPServers.get_mcp_server_by_id(server_id)
            if not server:
                raise ValueError(f"Server {server_id} not found")

            token_storage = DatabaseTokenStorage(server_id, server.user_id)
            # Clear tokens by setting to None
            await token_storage.set_tokens(None)
            log.info(f"OAuth tokens cleared for server {server_id}")
        except Exception as e:
            log.error(f"Failed to clear tokens for server {server_id}: {e}")
            raise

    def _schedule_redis_cleanup(self, redis_key: str, delay_seconds: int = 90):
        """Schedule Redis key cleanup after a delay (non-blocking)."""
        if not self.redis_client:
            return

        def cleanup_after_delay():
            time.sleep(delay_seconds)
            try:
                if self.redis_client.exists(redis_key):
                    self.redis_client.delete(redis_key)
                    log.debug(f"Cleaned up OAuth state from Redis")
            except Exception as e:
                log.warning(f"Failed to cleanup OAuth state from Redis: {e}")

        # Run cleanup in background thread
        cleanup_thread = threading.Thread(target=cleanup_after_delay, daemon=True)
        cleanup_thread.start()

    async def cleanup_oauth_state(self, state_token: str) -> Dict[str, Any]:
        """Immediately cleanup OAuth state from Redis after successful completion."""
        if not self.redis_client:
            return {"success": False, "error": "Redis not available"}

        try:
            redis_key = f"open-webui:oauth_state:{state_token}"
            if self.redis_client.exists(redis_key):
                self.redis_client.delete(redis_key)
                log.debug(f"OAuth state cleaned up from Redis")
                return {"success": True, "message": "OAuth state cleaned up"}
            else:
                return {"success": True, "message": "OAuth state already cleaned up"}
        except Exception as e:
            log.error(f"Failed to cleanup OAuth state: {e}")
            return {"success": False, "error": str(e)}

    async def get_oauth_status(self, server_id: str) -> Dict[str, Any]:
        """Get OAuth status for a server."""
        try:
            server = MCPServers.get_mcp_server_by_id(server_id)
            if not server:
                return {"success": False, "error": "Server not found"}

            oauth_config = server.oauth_config
            if not oauth_config or not isinstance(oauth_config, dict):
                return {
                    "success": False,
                    "authenticated": False,
                    "message": "OAuth not configured",
                }

            # Check if we have valid tokens
            token_storage = DatabaseTokenStorage(server_id, server.user_id)
            tokens = await token_storage.get_tokens()

            if tokens and tokens.access_token:
                # Check if token is still valid
                expires_at = getattr(tokens, 'expires_at', None)
                if not expires_at or time.time() < expires_at:
                    return {
                        "success": True,
                        "authenticated": True,
                        "message": "OAuth authenticated",
                    }
                else:
                    return {
                        "success": True,
                        "authenticated": False,
                        "message": "OAuth token expired",
                    }
            else:
                return {
                    "success": True,
                    "authenticated": False,
                    "message": "OAuth configured but not authenticated",
                }

        except Exception as e:
            log.error(f"Failed to get OAuth status for server {server_id}: {e}")
            return {"success": False, "error": str(e)}

    async def discover_direct_oauth_metadata(self, issuer_url: str) -> Dict[str, Any]:
        """Discover OAuth 2.1 authorization server metadata from any compliant provider."""
        try:
            import httpx
            
            # Normalize issuer URL - remove trailing slash
            issuer_url = issuer_url.rstrip('/')
            
            # Try standard OAuth 2.1 metadata discovery endpoint
            metadata_url = f"{issuer_url}/.well-known/oauth-authorization-server"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(metadata_url, timeout=10.0)
                
                if response.status_code == 200:
                    metadata = response.json()
                    
                    # Validate required OAuth 2.1 endpoints
                    required_endpoints = ['authorization_endpoint', 'token_endpoint']
                    for endpoint in required_endpoints:
                        if endpoint not in metadata:
                            raise Exception(f"Missing required endpoint: {endpoint}")
                    
                    log.info(f"Successfully discovered OAuth metadata from {metadata_url}")
                    return {
                        "success": True,
                        "metadata": metadata,
                        "issuer": issuer_url
                    }
                else:
                    raise Exception(f"Metadata discovery failed with status {response.status_code}")
                    
        except Exception as e:
            log.error(f"Failed to discover OAuth metadata from {issuer_url}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_pkce_challenge(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge for OAuth 2.1 security."""
        # Generate cryptographically secure random code verifier
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Create SHA256 hash of code verifier for the challenge
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge

    async def initiate_direct_oauth_flow(
        self, 
        server_id: str, 
        issuer_url: str,
        client_id: str,
        scopes: list[str],
        base_url: str,
        user_id: str = None,
        resource: str = None
    ) -> Dict[str, Any]:
        """Initiate direct OAuth 2.1 flow with any compliant authorization server using PKCE."""
        try:
            # Discover OAuth metadata
            metadata_result = await self.discover_direct_oauth_metadata(issuer_url)
            if not metadata_result["success"]:
                return metadata_result
            
            metadata = metadata_result["metadata"]
            
            # Generate PKCE parameters for security
            code_verifier, code_challenge = self._generate_pkce_challenge()
            
            # Generate secure state parameter
            state = secrets.token_urlsafe(32)
            
            # Store OAuth state in Redis for security
            state_data = {
                "server_id": server_id,
                "user_id": user_id,
                "issuer_url": issuer_url,
                "client_id": client_id,
                "code_verifier": code_verifier,
                "oauth_metadata": metadata,
                "resource": resource,  # Store resource for token exchange
                "created_at": time.time(),
                "flow_type": "direct_oauth"  # Mark as direct flow
            }
            
            if self.redis_client:
                redis_key = f"open-webui:oauth_state:{state}"
                self.redis_client.setex(
                    redis_key, 
                    600,  # 10 minutes expiry
                    json.dumps(state_data)
                )
            
            # Build authorization URL with PKCE parameters
            auth_params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": f"{base_url}/api/v1/mcp-servers/oauth/callback",
                "scope": " ".join(scopes) if scopes else "openid email profile groups offline_access",
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"  # SHA256 for PKCE
            }
            
            # Note: resource parameter is NOT added to authorization URL as Azure AD doesn't support it there
            # The resource parameter is stored in state_data and will be used during token exchange
            
            authorization_url = f"{metadata['authorization_endpoint']}?{urllib.parse.urlencode(auth_params)}"
            
            log.info(f"Generated direct OAuth authorization URL for server {server_id}")
            
            return {
                "success": True,
                "authorization_url": authorization_url,
                "state": state,
                "flow_type": "direct_oauth"
            }
            
        except Exception as e:
            log.error(f"Failed to initiate direct OAuth flow for server {server_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _exchange_direct_oauth_code_for_tokens(
        self, code: str, state_data: Dict, base_url: str, token_storage: DatabaseTokenStorage
    ) -> None:
        """Exchange authorization code for real tokens using direct OAuth 2.1 flow with any compliant provider."""
        try:
            import httpx
            
            # Get OAuth metadata and PKCE verifier from state
            oauth_metadata = state_data.get("oauth_metadata", {})
            client_id = state_data.get("client_id")
            code_verifier = state_data.get("code_verifier")
            resource = state_data.get("resource")  # Resource parameter for token audience
            token_endpoint = oauth_metadata.get("token_endpoint")
            
            if not all([token_endpoint, client_id, code_verifier]):
                raise Exception("Missing OAuth configuration for direct token exchange")
            
            # Use base_url from parameter or fallback to main WEBUI_URL
            if not base_url:
                base_url = str(WEBUI_URL).rstrip("/")
            
            # Prepare token exchange request with PKCE
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{base_url}/api/v1/mcp-servers/oauth/callback",
                "client_id": client_id,
                "code_verifier": code_verifier  # PKCE verifier instead of client_secret
            }
            
            # Add resource parameter - for Azure AD, use scope instead of resource parameter
            if resource:
                # For Azure AD v2.0, use scope instead of resource parameter
                if "login.microsoftonline.com" in state_data.get("issuer_url", ""):
                    # Azure AD v2.0 - use application-specific scope instead of resource parameter
                    app_scope = f"{resource}/.default"
                    token_data["scope"] = f"openid email profile offline_access {app_scope}"
                    log.debug(f"Using Azure AD app-specific scope: {app_scope}")
                else:
                    # Non-Azure AD - use resource parameter
                    token_data["resource"] = resource
 
            # Exchange code for real OAuth tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )
                 
                if response.status_code == 200:
                    token_response = response.json()
                     
                    # Create OAuth token from authorization server response
                    expires_in = token_response.get("expires_in")
                    expires_at = None
                    if isinstance(expires_in, int):
                        expires_at = int(time.time()) + expires_in
                    else:
                        jwt_exp = _extract_exp_from_jwt(token_response.get("access_token"))
                        if jwt_exp:
                            expires_at = jwt_exp
                     
                    real_token = OAuthToken(
                        access_token=token_response["access_token"],
                        token_type=token_response.get("token_type", "Bearer"),
                        expires_at=expires_at,
                        refresh_token=token_response.get("refresh_token"),
                        scope=token_response.get("scope"),
                    )
                     
                    await token_storage.set_tokens(real_token)
                    # Persist token endpoint and client info for refresh fallback
                    try:
                        from open_webui.models.mcp_servers import MCPServerUpdateForm, MCPServers
                        server = MCPServers.get_mcp_server_by_id(token_storage.server_id)
                        current_cfg = server.oauth_config or {}
                        if not isinstance(current_cfg, dict):
                            current_cfg = {}
                        merged = {
                            **current_cfg,
                            "token_url": token_endpoint or current_cfg.get("token_url"),
                            "client_id": client_id or current_cfg.get("client_id"),
                        }
                        MCPServers.update_mcp_server_by_id(
                            token_storage.server_id,
                            MCPServerUpdateForm(oauth_config=merged),
                            token_storage.user_id,
                        )
                    except Exception as persist_err:
                        log.warning(f"Failed to persist token endpoint/client info (direct): {persist_err}")
                    log.info(f"Successfully exchanged OAuth code for real access tokens")
                else:
                    error_details = ""
                    try:
                        error_details = response.json()
                    except:
                        error_details = response.text
                    raise Exception(f"Direct token exchange failed with status {response.status_code}: {error_details}")
                     
        except Exception as token_error:
            log.error(f"Failed to exchange OAuth code for real access tokens: {token_error}")
            # For direct OAuth, we should NOT fall back to fake tokens - this is a real failure
            raise token_error

    async def refresh_access_token(self, server_id: str) -> Optional[str]:
        """Force a refresh using the stored refresh_token and return the new access token."""
        if not MCP_AVAILABLE:
            return None
        try:
            server = MCPServers.get_mcp_server_by_id(server_id)
            if not server:
                return None
            token_storage = DatabaseTokenStorage(server_id, server.user_id)
            tokens = await token_storage.get_tokens()
            if not tokens or not getattr(tokens, "refresh_token", None):
                log.warning(f"No refresh_token available for server {server_id}")
                return None
            refreshed_tokens = None
            try:
                client_info = await token_storage.get_client_info()
                # Provide no-op handlers; not used for refresh
                oauth_provider = OAuthClientProvider(
                    client_info, token_storage, lambda url: None, lambda *args, **kwargs: None
                )
                refreshed_tokens = await oauth_provider.refresh_tokens()
            except Exception as sdk_error:
                log.warning(f"SDK refresh failed, falling back to HTTP refresh: {sdk_error}")
                refreshed_tokens = await self._refresh_tokens_via_http(server)
            if refreshed_tokens and getattr(refreshed_tokens, "access_token", None):
                # Persist refreshed tokens so token_expires_at is updated
                await token_storage.set_tokens(refreshed_tokens)
                log.info(f"Successfully refreshed access token for server {server_id}")
                return refreshed_tokens.access_token
            log.warning(f"Refresh attempt did not return new tokens for server {server_id}")
            return None
        except Exception as e:
            log.error(f"Failed to refresh access token for server {server_id}: {e}")
            return None