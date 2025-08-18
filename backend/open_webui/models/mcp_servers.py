import logging
import time
import uuid
from typing import Optional, List, Dict, Any
from enum import Enum

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.models.users import Users, UserResponse
from open_webui.env import SRC_LOG_LEVELS, WEBUI_SECRET_KEY
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON, Boolean, Enum as SQLEnum

from open_webui.utils.access_control import has_access
from open_webui.utils.auth import encrypt_data, decrypt_data


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# MCP Server DB Schema
####################


# Removed MCPServerType - not needed, tools determine functionality


class MCPConnectionType(str, Enum):
    http_stream = (
        "http_stream"  # HTTP Stream Transport for secure authenticated connections
    )


class MCPServerStatus(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"
    connecting = "connecting"
    oauth_required = "oauth_required"  # New status for OAuth flow needed
    token_expired = "token_expired"  # New status for expired tokens


####################
# OAuth Configuration Models
####################


class MCPOAuthConfig(BaseModel):
    """OAuth 2.1 configuration for MCP servers with metadata discovery and DCR support"""

    enabled: bool = False

    # Configuration method
    config_method: str = "manual"  # "manual", "discovery", "dcr"

    # For metadata discovery
    issuer_url: Optional[str] = None  # Authorization server issuer URL
    discovered_metadata: Optional[Dict[str, Any]] = None  # Cached metadata

    # OAuth 2.1 endpoints (user-configurable or discovered)
    authorize_url: Optional[str] = None
    token_url: Optional[str] = None
    registration_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None

    # Client credentials (manual or from DCR)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

    # Dynamic Client Registration data
    dcr_registration_data: Optional[Dict[str, Any]] = None  # Full DCR response
    registration_access_token: Optional[str] = None  # For DCR updates
    registration_client_uri: Optional[str] = None  # For DCR management

    # OAuth parameters
    scopes: List[str] = []

    # OAuth 2.1 features
    use_pkce: bool = True  # PKCE for enhanced security
    audience: Optional[str] = None  # For JWT-based OAuth
    resource: Optional[str] = None  # For Microsoft-style OAuth

    # Third-party delegation support
    delegate_to_third_party: bool = False  # Delegate to external IdP
    third_party_issuer: Optional[str] = None  # External IdP issuer


class MCPServer(Base):
    __tablename__ = "mcp_server"

    id = Column(String, primary_key=True)
    user_id = Column(String)  # Creator/owner
    name = Column(String, nullable=False)
    # server_type removed - not needed, functionality determined by available tools
    connection_type = Column(SQLEnum(MCPConnectionType), nullable=False)

    # HTTP Stream Connection configuration
    http_url = Column(String, nullable=False)  # HTTP Stream endpoint URL
    headers = Column(JSONField)  # Authentication headers

    # OAuth 2.1 configuration
    oauth_config = Column(Text)  # MCPOAuthConfig as JSON string (encrypted at rest)
    oauth_tokens = Column(Text)  # Encrypted OAuth tokens as JSON string
    token_expires_at = Column(BigInteger)  # For quick expiry checks

    # available_tools removed; tools are stored in native Tools table

    # Server metadata
    status = Column(SQLEnum(MCPServerStatus), default=MCPServerStatus.disconnected)
    last_connected_at = Column(BigInteger)
    error_message = Column(Text)



    # Access control
    access_control = Column(JSON, nullable=True)  # Same pattern as tools

    # Timestamps
    created_at = Column(BigInteger, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, default=lambda: int(time.time()))

    # is_active removed from persisted model
    is_active = Column(Boolean, default=True)


####################
# Pydantic Models
####################


class MCPServerForm(BaseModel):
    name: str
    connection_type: MCPConnectionType = MCPConnectionType.http_stream
    http_url: str  # Required HTTP Stream endpoint
    headers: Optional[Dict[str, str]] = None  # Authentication headers

    # OAuth 2.1 configuration (optional) - allow both MCPOAuthConfig and raw dict
    oauth_config: Optional[Dict[str, Any]] = None

    access_control: Optional[Dict[str, Any]] = None


    @field_validator("access_control", mode="before")
    @classmethod
    def normalize_access_control(cls, v):
        # Treat string 'null' or empty string as None (public) ONLY if explicitly sent
        if v == "null" or v == "":
            return None
        # Keep empty dict as private
        if isinstance(v, dict) and len(v) == 0:
            return {}
        return v

    @field_validator("headers", mode="before")
    @classmethod
    def normalize_headers(cls, v):
        # Handle string 'null' from frontend
        if v == "null" or v == "":
            return None
        # Normalize empty dict/object to None for headers
        if isinstance(v, dict) and len(v) == 0:
            return None
        return v

    @field_validator("oauth_config", mode="before")
    @classmethod
    def normalize_oauth_config(cls, v):
        # Handle string 'null' from frontend
        if v == "null" or v == "":
            return None
        # Handle JSON string from database (for oauth_config)
        if isinstance(v, str) and v.strip():
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return v
        return v


class MCPServerUpdateForm(BaseModel):
    name: Optional[str] = None
    http_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None  # Authentication headers

    # OAuth 2.1 configuration (optional) - allow both MCPOAuthConfig and raw dict
    oauth_config: Optional[Dict[str, Any]] = None
    oauth_tokens: Optional[str] = None  # Encrypted OAuth tokens
    token_expires_at: Optional[int] = None  # Token expiration timestamp

    access_control: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


    @field_validator("access_control", mode="before")
    @classmethod
    def normalize_access_control(cls, v):
        if v == "null" or v == "":
            return None
        if isinstance(v, dict) and len(v) == 0:
            return {}
        return v

    @field_validator("headers", mode="before")
    @classmethod
    def normalize_headers(cls, v):
        if v == "null" or v == "":
            return None
        if isinstance(v, dict) and len(v) == 0:
            return None
        return v

    @field_validator("oauth_config", "oauth_tokens", "name", "http_url", mode="before")
    @classmethod
    def normalize_other_fields(cls, v):
        if v == "null" or v == "":
            return None
        return v

    # available_tools removed; use sync endpoints to populate Tools table


class MCPServerModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    connection_type: MCPConnectionType
    http_url: str
    headers: Optional[Dict[str, str]] = None

    # OAuth 2.1 fields
    oauth_config: Optional[Dict[str, Any]] = None
    oauth_tokens: Optional[str] = None  # Encrypted string
    token_expires_at: Optional[int] = None

    status: MCPServerStatus
    last_connected_at: Optional[int] = None
    error_message: Optional[str] = None
    # capabilities, available_tools removed from persisted model
    is_active: bool
    created_at: int
    updated_at: int
    access_control: Optional[Dict[str, Any]] = None


    @field_validator("oauth_config", mode="before")
    @classmethod
    def decrypt_oauth_config(cls, v):
        # Normalize empty
        if v is None or v == "" or v == "null":
            return None
        # Already dict/list
        if isinstance(v, (dict, list)):
            return v
        # Helper to parse possibly double-encoded JSON strings
        def _parse_json_maybe_twice(s: str):
            import json
            try:
                parsed = json.loads(s)
                # If result is a string containing JSON object/array, try again
                if isinstance(parsed, str) and parsed.strip().startswith(("{", "[")):
                    try:
                        return json.loads(parsed)
                    except Exception:
                        return parsed
                return parsed
            except Exception:
                return s
        # Attempt direct JSON first (legacy plain JSON at rest)
        if isinstance(v, str) and v.strip():
            parsed = _parse_json_maybe_twice(v)
            if not isinstance(parsed, str):
                return parsed
            # Attempt decrypt then JSON
            try:
                decrypted = decrypt_data(v, WEBUI_SECRET_KEY)
                parsed = _parse_json_maybe_twice(decrypted)
                return parsed
            except Exception:
                # If decryption fails, return as-is to avoid breaking callers
                return v
        return v

    @field_validator(
        "headers",
        "error_message",
        mode="before",
    )
    @classmethod
    def validate_nullable_fields(cls, v):
        # Handle string 'null' from database
        if v == "null" or v == "":
            return None
        # For headers/error_message: treat empty dict/object as None
        if isinstance(v, dict) and len(v) == 0:
            return None
        # Handle JSON string from database
        if isinstance(v, str) and v.strip():
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return v
        return v

    @field_validator("access_control", mode="before")
    @classmethod
    def validate_access_control(cls, v):
        # Treat explicit string null/empty as None (public), but keep empty dict as private {}
        if v == "null" or v == "":
            return None
        # Preserve {} to represent private access control
        if isinstance(v, dict):
            return v
        # Parse JSON string if necessary
        if isinstance(v, str) and v.strip():
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return v
        return v


class MCPServerResponse(MCPServerModel):
    user: Optional[UserResponse] = None


class MCPServerUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: MCPServerStatus
    # capabilities removed from user response
    is_active: bool
    is_public: bool

    # capabilities removed from user response


####################
# Database Operations
####################


class MCPServers:
    def insert_new_mcp_server(
        self, user_id: str, form_data: MCPServerForm
    ) -> Optional[MCPServerModel]:
        with get_db() as db:
            # Convert form data and handle JSON serialization
            form_dict = form_data.model_dump()

            # Preserve explicit None (public) from admins; only default when missing
            if "access_control" not in form_dict:
                form_dict["access_control"] = {}

            # Normalize oauth_config with expected keys for refresh
            if form_dict.get("oauth_config") and isinstance(form_dict["oauth_config"], dict):
                oc = form_dict["oauth_config"]
                normalized = {
                    **oc,
                    # ensure these keys exist to aid refresh fallback later
                    "authorize_url": oc.get("authorize_url"),
                    "token_url": oc.get("token_url"),
                    "client_id": oc.get("client_id"),
                    "client_secret": oc.get("client_secret"),
                    "issuer_url": oc.get("issuer_url"),
                    "scopes": oc.get("scopes") or oc.get("client_metadata", {}).get("scope") or [
                        "openid",
                        "email",
                        "profile",
                        "offline_access",
                    ],
                }
                form_dict["oauth_config"] = normalized

            # Convert oauth_config dict to encrypted string if present
            if form_dict.get("oauth_config") is not None:
                import json

                oauth_json = json.dumps(form_dict["oauth_config"])
                form_dict["oauth_config"] = encrypt_data(oauth_json, WEBUI_SECRET_KEY)

            mcp_server = MCPServer(
                **{
                    **form_dict,
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "updated_at": int(time.time()),
                }
            )
            db.add(mcp_server)
            db.commit()
            db.refresh(mcp_server)

            if mcp_server:
                return MCPServerModel.model_validate(mcp_server)
            return None

    def get_mcp_servers(self) -> List[MCPServerModel]:
        with get_db() as db:
            servers = db.query(MCPServer).filter(MCPServer.is_active == True).all()
            return [MCPServerModel.model_validate(server) for server in servers]

    def get_all_mcp_servers(self) -> List[MCPServerModel]:
        """Get all MCP servers including inactive ones (for UI display)"""
        with get_db() as db:
            servers = db.query(MCPServer).all()
            return [MCPServerModel.model_validate(server) for server in servers]

    def get_mcp_server_by_id(self, id: str) -> Optional[MCPServerModel]:
        with get_db() as db:
            server = db.query(MCPServer).filter(MCPServer.id == id).first()
            return MCPServerModel.model_validate(server) if server else None

    def get_mcp_servers_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> List[MCPServerModel]:
        servers = self.get_mcp_servers()
        return [
            server
            for server in servers
            if (
                server.user_id == user_id
                or has_access(user_id, permission, server.access_control)
            )
        ]

    def get_all_mcp_servers_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> List[MCPServerModel]:
        """Get all MCP servers (including inactive) accessible to the user for UI display"""
        servers = self.get_all_mcp_servers()
        return [
            server
            for server in servers
            if (
                server.user_id == user_id
                or has_access(user_id, permission, server.access_control)
            )
        ]

    def get_user_mcp_servers(self, user_id: str) -> List[MCPServerModel]:
        """Get only user's private MCP servers (including inactive ones for UI display)"""
        servers = (
            self.get_all_mcp_servers()
        )  # Use get_all_mcp_servers to include inactive ones
        return [
            server
            for server in servers
            if server.user_id == user_id
        ]

    def get_global_mcp_servers(self) -> List[MCPServerModel]:
        """Get only global (admin-managed) MCP servers (including inactive ones for UI display)"""
        servers = (
            self.get_all_mcp_servers()
        )  # Use get_all_mcp_servers to include inactive ones
        return [server for server in servers if server.access_control is None]

    def update_mcp_server_by_id(
        self, id: str, form_data: MCPServerUpdateForm, user_id: str
    ) -> Optional[MCPServerModel]:
        with get_db() as db:
            server = db.query(MCPServer).filter(MCPServer.id == id).first()
            if not server:
                return None

            # Check permissions
            if server.user_id != user_id and not has_access(
                user_id, "write", server.access_control
            ):
                return None

            update_data = form_data.model_dump(exclude_unset=True)
            update_data["updated_at"] = int(time.time())

            # Convert oauth_config dict to encrypted string if present
            if (
                "oauth_config" in update_data
                and update_data["oauth_config"] is not None
            ):
                from open_webui.utils.mcp.common import encrypt_oauth_config_if_needed
                update_data["oauth_config"] = encrypt_oauth_config_if_needed(update_data["oauth_config"])

            for key, value in update_data.items():
                setattr(server, key, value)

            db.commit()
            db.refresh(server)
            return MCPServerModel.model_validate(server)

    def update_mcp_server_status(
        self, id: str, status: MCPServerStatus, error_message: Optional[str] = None
    ) -> bool:
        with get_db() as db:
            server = db.query(MCPServer).filter(MCPServer.id == id).first()
            if not server:
                return False

            server.status = status
            server.error_message = error_message
            server.updated_at = int(time.time())

            if status == MCPServerStatus.connected:
                server.last_connected_at = int(time.time())

            db.commit()
            return True

    def delete_mcp_server_by_id(self, id: str, user_id: str) -> bool:
        with get_db() as db:
            server = db.query(MCPServer).filter(MCPServer.id == id).first()
            if not server:
                return False

            # Check permissions
            if server.user_id != user_id and not has_access(
                user_id, "write", server.access_control
            ):
                return False

            # Hard delete - actually remove the record
            db.delete(server)
            db.commit()
            return True


import uuid

MCPServers = MCPServers()
