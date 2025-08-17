"""
Core MCP utilities and SDK imports
"""
import logging

# MCP Protocol Version - 2025-06-18 specification
MCP_PROTOCOL_VERSION = "2025-06-18"

# Initialize logger
log = logging.getLogger(__name__)

try:
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.auth import OAuthClientProvider, TokenStorage
    from mcp.shared.auth import (
        OAuthClientInformationFull,
        OAuthClientMetadata,
        OAuthToken,
    )
    from mcp.types import Tool, Implementation, ClientCapabilities

    MCP_AVAILABLE = True
except ImportError as e:
    log.warning(
        "Official MCP Python SDK not installed. MCP functionality will be disabled. Run: pip install mcp"
    )
    MCP_AVAILABLE = False

    # Define dummy classes to prevent import errors
    class ClientSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def initialize(self):
            pass

        async def list_tools(self):
            return []

        async def list_prompts(self):
            return []

        async def list_resources(self):
            return []

        async def call_tool(self, *args, **kwargs):
            return None

    class Tool:
        def __init__(self, name="", description=""):
            self.name = name
            self.description = description

    def streamablehttp_client(*args, **kwargs):
        class DummyClient:
            async def __aenter__(self):
                return None, None, lambda: None

            async def __aexit__(self, *args):
                pass

        return DummyClient()


def create_mcp_client_info() -> Implementation:
    """Create MCP client implementation info following official SDK examples."""
    return Implementation(
        name="open-webui-mcp-client",
        version="0.6.22"
    )


# Client capabilities are handled automatically by the SDK during initialization