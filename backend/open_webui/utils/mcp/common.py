"""
Common MCP utilities and shared patterns
"""
import logging
from typing import Dict, Any
from urllib.parse import urlparse
from fastapi import HTTPException, Request, status

log = logging.getLogger(__name__)


def validate_http_url(url: str) -> None:
    """
    Validate HTTP/HTTPS URL format.
    
    Args:
        url: URL to validate
        
    Raises:
        HTTPException: If URL format is invalid
    """
    if not url.startswith(("https://", "http://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HTTP Stream URL must be a valid HTTP/HTTPS URL",
        )


def validate_mcp_allowlist(request: Request, url: str) -> None:
    """
    Validate URL against MCP server allowlist if configured.
    
    Args:
        request: FastAPI request object containing app config
        url: URL to validate
        
    Raises:
        HTTPException: If domain not in allowlist
    """
    allowlist = request.app.state.config.MCP_SERVER_ALLOWLIST
    if allowlist and len(allowlist) > 0:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        domain_allowed = False
        for allowed_domain in allowlist:
            allowed_domain = allowed_domain.strip().lower()
            if allowed_domain and (
                domain == allowed_domain or domain.endswith("." + allowed_domain)
            ):
                domain_allowed = True
                break

        if not domain_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"MCP server domain '{domain}' is not in the allowed domains list. Contact your administrator.",
            )


def get_mcp_client_with_validation(server_id: str) -> object:
    """
    Get MCP client for a server with validation.
    
    Args:
        server_id: The MCP server ID
        
    Returns:
        MCP client instance
        
    Raises:
        HTTPException: If client not available
    """
    # Import here to avoid circular imports
    from open_webui.utils.mcp_client_official import mcp_manager
    
    client = mcp_manager.get_client(server_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="MCP server not found"
        )
    return client


def encrypt_headers_if_present(headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Encrypt headers if provided using the WebUI secret key.
    
    Args:
        headers: Headers dictionary to encrypt
        
    Returns:
        Encrypted headers dictionary or original if empty
    """
    if not headers:
        return headers
    
    # If headers are already stored in encrypted container, return as-is
    # Expected format: { "encrypted": "<ciphertext>" }
    if isinstance(headers, dict) and "encrypted" in headers and isinstance(headers.get("encrypted"), str):
        return headers
        
    import json
    from open_webui.utils.auth import encrypt_data
    from open_webui.env import WEBUI_SECRET_KEY
    
    headers_json = json.dumps(headers)
    return {"encrypted": encrypt_data(headers_json, WEBUI_SECRET_KEY)}


def encrypt_oauth_config_if_needed(oauth_config) -> str:
    """
    Encrypt OAuth config only if it's not already encrypted.
    
    Args:
        oauth_config: OAuth configuration dict or encrypted string
        
    Returns:
        Encrypted OAuth config string, or None if empty
    """
    if not oauth_config:
        return None
        
    # If it's already a string, it's likely already encrypted - return as-is
    if isinstance(oauth_config, str):
        return oauth_config
        
    # If it's a dict, it's plaintext - encrypt it
    if isinstance(oauth_config, dict):
        import json
        from open_webui.utils.auth import encrypt_data
        from open_webui.env import WEBUI_SECRET_KEY
        
        oauth_json = json.dumps(oauth_config)
        return encrypt_data(oauth_json, WEBUI_SECRET_KEY)
    
    # Fallback: convert to string and return (should not happen)
    return str(oauth_config) if oauth_config else None