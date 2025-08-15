"""
Official MCP (Model Context Protocol) Client Implementation
Using the official MCP Python SDK with Streamable HTTP Transport

This module provides a modular interface to the MCP package components.
The actual implementation has been split into focused modules for better maintainability.
"""

# Import everything from the modular MCP package
from .mcp import (
    MCP_AVAILABLE,
    MCP_PROTOCOL_VERSION,
    create_mcp_client_info,
    DatabaseTokenStorage,
    MCPOAuthManager,
    MCPStreamHTTPClient,
    MCPClientManager,
    mcp_manager,
    mcp_oauth_manager
)

# Maintain backward compatibility by exposing the same interface
__all__ = [
    'MCP_AVAILABLE',
    'MCP_PROTOCOL_VERSION', 
    'create_mcp_client_info',
    'DatabaseTokenStorage',
    'MCPOAuthManager',
    'MCPStreamHTTPClient',
    'MCPClientManager',
    'mcp_manager',
    'mcp_oauth_manager'
]