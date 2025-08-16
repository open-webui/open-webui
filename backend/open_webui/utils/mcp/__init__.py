"""
MCP (Model Context Protocol) Client Package
Official MCP Python SDK integration for Open WebUI
"""

from .core import MCP_AVAILABLE, MCP_PROTOCOL_VERSION, create_mcp_client_info
from .auth import DatabaseTokenStorage, MCPOAuthManager
from .client import MCPStreamHTTPClient  
from .manager import MCPClientManager
from .validation import validate_server_access, validate_server_connected, validate_servers_batch_access
from .common import validate_http_url, validate_mcp_allowlist, get_mcp_client_with_validation, encrypt_headers_if_present

# Global instances
mcp_manager = MCPClientManager()
mcp_oauth_manager = MCPOAuthManager()

__all__ = [
    'MCP_AVAILABLE',
    'MCP_PROTOCOL_VERSION', 
    'create_mcp_client_info',
    'DatabaseTokenStorage',
    'MCPOAuthManager',
    'MCPStreamHTTPClient',
    'MCPClientManager',
    'mcp_manager',
    'mcp_oauth_manager',
    'validate_server_access',
    'validate_server_connected', 
    'validate_servers_batch_access',
    'validate_http_url',
    'validate_mcp_allowlist',
    'get_mcp_client_with_validation',
    'encrypt_headers_if_present'
]