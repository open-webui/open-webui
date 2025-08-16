"""
MCP-specific exception classes for structured error handling.
"""

class MCPException(Exception):
    """Base exception for all MCP-related errors."""
    pass


class MCPAuthenticationError(MCPException):
    """Raised when MCP tool execution fails due to authentication issues."""
    
    def __init__(
        self, 
        message: str, 
        server_id: str, 
        server_name: str, 
        tool_name: str, 
        challenge_type: str = "manual",  # "oauth", "manual", "api_key", etc.
        requires_reauth: bool = True,
        auth_url: str = None,  # For OAuth challenges
        instructions: str = None,  # For manual challenges
        original_exception: Exception = None
    ):
        self.message = message
        self.server_id = server_id
        self.server_name = server_name
        self.tool_name = tool_name
        self.challenge_type = challenge_type
        self.requires_reauth = requires_reauth
        self.auth_url = auth_url
        self.instructions = instructions
        self.original_exception = original_exception
        super().__init__(message)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "error_type": "authentication_error",
            "message": self.message,
            "server_id": self.server_id,
            "server_name": self.server_name,
            "tool_name": self.tool_name,
            "requires_reauth": self.requires_reauth,
            "original_error": str(self.original_exception) if self.original_exception else None
        }


class MCPConnectionError(MCPException):
    """Raised when MCP server connection fails."""
    pass


class MCPToolNotFoundError(MCPException):
    """Raised when requested MCP tool is not available."""
    pass


class MCPEncryptionMismatchError(MCPException):
    """Raised when MCP server encryption key doesn't match."""
    
    def __init__(
        self, 
        message: str, 
        server_id: str, 
        server_name: str, 
        original_exception: Exception = None
    ):
        self.message = message
        self.server_id = server_id
        self.server_name = server_name
        self.original_exception = original_exception
        super().__init__(message)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "error_type": "encryption_mismatch",
            "message": self.message,
            "server_id": self.server_id,
            "server_name": self.server_name,
            "instructions": "The encryption key for this MCP server is invalid or has changed. Please remove and re-add the server with the correct encryption key.",
            "original_error": str(self.original_exception) if self.original_exception else None
        } 