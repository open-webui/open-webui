"""
MCP Apps Pydantic Models.

These models handle tool metadata parsing, visibility filtering,
and UI resource management for MCP Apps extension.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


class McpUiResourceCsp(BaseModel):
    """
    CSP configuration from resource metadata per MCP ext-apps spec.

    Maps to Content Security Policy directives for the inner iframe.
    @see https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx
    """

    connectDomains: Optional[List[str]] = None
    """Origins for network requests (fetch/XHR/WebSocket) - maps to connect-src"""

    resourceDomains: Optional[List[str]] = None
    """Origins for static resources (scripts, images, styles, fonts)"""

    frameDomains: Optional[List[str]] = None
    """Origins for nested iframes - maps to frame-src"""

    baseUriDomains: Optional[List[str]] = None
    """Allowed base URIs - maps to base-uri"""


class MCPUIPermissions(BaseModel):
    """Permissions declared by MCP server for UI resource."""
    camera: Optional[Dict] = None
    microphone: Optional[Dict] = None
    geolocation: Optional[Dict] = None
    clipboardWrite: Optional[Dict] = Field(None, alias="clipboard-write")

    class Config:
        populate_by_name = True


class MCPUIMetadata(BaseModel):
    """UI metadata from tool's _meta.ui field."""
    resourceUri: Optional[str] = None
    visibility: Optional[List[Literal["model", "app"]]] = None
    permissions: Optional[MCPUIPermissions] = None


class MCPToolMeta(BaseModel):
    """Tool metadata structure supporting both nested and flat formats."""
    ui: Optional[MCPUIMetadata] = None
    # Deprecated flat format (for backwards compatibility)
    ui_resourceUri: Optional[str] = Field(None, alias="ui/resourceUri")

    def get_resource_uri(self) -> Optional[str]:
        """
        Get resource URI from either format.

        Supports:
        - Nested: _meta.ui.resourceUri
        - Flat: _meta["ui/resourceUri"]

        Returns None if no UI resource is declared.
        """
        if self.ui and self.ui.resourceUri:
            uri = self.ui.resourceUri
        else:
            uri = self.ui_resourceUri

        # Validate URI format
        if uri and uri.startswith("ui://"):
            return uri
        return None

    def get_visibility(self) -> List[str]:
        """
        Get visibility list from metadata.

        Returns default ["model", "app"] if not specified.
        """
        if self.ui and self.ui.visibility:
            return self.ui.visibility
        return ["model", "app"]

    def is_model_only(self) -> bool:
        """
        Check if tool is only visible to the model (LLM).

        Tools with visibility=["model"] should not be callable by apps.
        """
        visibility = self.get_visibility()
        return visibility == ["model"]

    def is_app_only(self) -> bool:
        """
        Check if tool is only visible to apps.

        Tools with visibility=["app"] should not be shown to the LLM.
        """
        visibility = self.get_visibility()
        return visibility == ["app"]

    def is_visible_to_model(self) -> bool:
        """Check if tool should be visible to the model (LLM)."""
        return "model" in self.get_visibility()

    def is_visible_to_app(self) -> bool:
        """Check if tool can be called by apps."""
        return "app" in self.get_visibility()

    def get_permissions(self) -> Optional[MCPUIPermissions]:
        """Get UI permissions if declared."""
        if self.ui:
            return self.ui.permissions
        return None


class MCPAppResource(BaseModel):
    """
    Fetched UI resource content per MCP ext-apps spec.

    The csp field contains CSP directives from _meta.ui.csp.
    """

    uri: str
    content: str  # HTML content
    mimeType: str = "text/html"
    csp: Optional[McpUiResourceCsp] = None
    """CSP configuration from resource _meta.ui.csp"""
    permissions: Optional[MCPUIPermissions] = None
    """Permissions from resource _meta.ui.permissions"""


class MCPAppConfig(BaseModel):
    """MCP Apps configuration settings."""
    enabled: bool = False


class MCPServerConfig(BaseModel):
    """Extended MCP server configuration with apps settings."""
    enable_mcp_apps: bool = True  # Per-server toggle


# Request/Response Models

class ReadResourceRequest(BaseModel):
    """Request to read a UI resource."""
    server_id: str
    uri: str


class ReadResourceResponse(BaseModel):
    """Response containing UI resource."""
    resource: MCPAppResource


class ToolCallRequest(BaseModel):
    """Request from app to call a tool."""
    server_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    """Response from tool call."""
    content: List[Dict[str, Any]]
    structuredContent: Optional[Any] = None
    isError: bool = False


# Alias for router compatibility
MCPToolResult = ToolCallResponse


def parse_tool_meta(meta: Optional[Dict[str, Any]]) -> Optional[MCPToolMeta]:
    """
    Parse tool _meta field into MCPToolMeta.

    Args:
        meta: The _meta dictionary from a tool definition

    Returns:
        MCPToolMeta if valid, None otherwise
    """
    if not meta:
        return None

    try:
        return MCPToolMeta.model_validate(meta)
    except Exception:
        return None


def get_tool_resource_uri(tool: Dict[str, Any]) -> Optional[str]:
    """
    Extract UI resource URI from a tool definition.

    Args:
        tool: Tool definition with potential _meta.ui.resourceUri

    Returns:
        Resource URI if present and valid, None otherwise
    """
    meta = tool.get("_meta")
    if not meta:
        return None

    parsed = parse_tool_meta(meta)
    if parsed:
        return parsed.get_resource_uri()
    return None


def is_tool_visible_to_model(tool: Dict[str, Any]) -> bool:
    """
    Check if a tool should be visible to the LLM.

    Args:
        tool: Tool definition

    Returns:
        True if tool should be shown to model
    """
    meta = tool.get("_meta")
    if not meta:
        return True  # Default: visible to model

    parsed = parse_tool_meta(meta)
    if parsed:
        return parsed.is_visible_to_model()
    return True


def is_tool_visible_to_app(tool: Dict[str, Any]) -> bool:
    """
    Check if a tool can be called by apps.

    Args:
        tool: Tool definition

    Returns:
        True if tool can be called by apps
    """
    meta = tool.get("_meta")
    if not meta:
        return True  # Default: callable by apps

    parsed = parse_tool_meta(meta)
    if parsed:
        return parsed.is_visible_to_app()
    return True
