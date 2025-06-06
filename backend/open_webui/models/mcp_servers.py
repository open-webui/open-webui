from typing import List, Union, Optional
import time
import uuid

from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, Integer


####################
# MCP Server DB Schema
####################


class MCPServer(Base):
    __tablename__ = "mcp_server"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    server_type = Column(String, default="user_created")  # "built_in" or "user_created"
    command = Column(Text, nullable=True)  # JSON string for command array
    args = Column(JSON, nullable=True, default=[])  # Command arguments
    env = Column(JSON, nullable=True, default={})  # Environment variables
    transport = Column(String, default="stdio")  # "stdio" or "http"
    url = Column(String, nullable=True)  # For HTTP transport
    port = Column(Integer, nullable=True)  # For HTTP transport
    is_active = Column(Boolean, default=True)
    is_deletable = Column(Boolean, default=True)
    capabilities = Column(JSON, nullable=True, default={})
    tools = Column(JSON, nullable=True, default=[])
    access_control = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class MCPServerModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    server_type: str = "user_created"
    command: Optional[str] = None
    args: Optional[List] = []
    env: Optional[dict] = {}
    transport: str = "stdio"
    url: Optional[str] = None
    port: Optional[int] = None
    is_active: bool = True
    is_deletable: bool = True
    capabilities: Optional[dict] = {}
    tools: Optional[List] = []
    access_control: Optional[dict] = None
    created_at: int
    updated_at: int


####################
# Forms
####################


class MCPServerForm(BaseModel):
    name: str
    description: Optional[str] = None
    server_type: str = "user_created"
    command: Optional[str] = None
    args: Optional[List] = []
    env: Optional[dict] = {}
    transport: str = "stdio"
    url: Optional[str] = None
    port: Optional[int] = None
    is_active: bool = True
    is_deletable: bool = True
    capabilities: Optional[dict] = {}
    tools: Optional[List] = []
    access_control: Optional[dict] = None


class MCPServerTable:
    def insert_new_server(
        self,
        name: str,
        description: str = None,
        user_id: str = None,
        server_type: str = "user_created",
        command: str = None,
        args: List = None,
        env: dict = None,
        transport: str = "stdio",
        url: str = None,
        port: int = None,
        is_active: bool = True,
        is_deletable: bool = True,
        capabilities: dict = None,
        tools: List = None,
        access_control: dict = None,
    ) -> Optional[MCPServerModel]:
        if args is None:
            args = []
        if env is None:
            env = {}
        if capabilities is None:
            capabilities = {}
        if tools is None:
            tools = []

        server_id = str(uuid.uuid4())
        
        try:
            with get_db() as db:
                server = MCPServerModel(
                    **{
                        "id": server_id,
                        "user_id": user_id,
                        "name": name,
                        "description": description,
                        "server_type": server_type,
                        "command": command,
                        "args": args,
                        "env": env,
                        "transport": transport,
                        "url": url,
                        "port": port,
                        "is_active": is_active,
                        "is_deletable": is_deletable,
                        "capabilities": capabilities,
                        "tools": tools,
                        "access_control": access_control,
                        "created_at": int(time.time()),
                        "updated_at": int(time.time()),
                    }
                )
                
                result = MCPServer(**server.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                
                if result:
                    return MCPServerModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            print(f"Error creating MCP server: {e}")
            return None

    def get_server_by_id(self, id: str) -> Optional[MCPServerModel]:
        try:
            with get_db() as db:
                server = db.query(MCPServer).filter_by(id=id).first()
                return MCPServerModel.model_validate(server) if server else None
        except Exception as e:
            print(f"Error getting MCP server by id: {e}")
            return None

    def get_server_by_name(self, name: str) -> Optional[MCPServerModel]:
        try:
            with get_db() as db:
                server = db.query(MCPServer).filter_by(name=name).first()
                return MCPServerModel.model_validate(server) if server else None
        except Exception as e:
            print(f"Error getting MCP server by name: {e}")
            return None

    def get_servers(self, user_id: str = None) -> List[MCPServerModel]:
        try:
            with get_db() as db:
                query = db.query(MCPServer)
                if user_id:
                    # If user_id is provided, get user's servers plus global servers (user_id is null)
                    query = query.filter((MCPServer.user_id == user_id) | (MCPServer.user_id.is_(None)))
                
                servers = [MCPServerModel.model_validate(server) for server in query.all()]
                return servers
        except Exception as e:
            print(f"Error getting MCP servers: {e}")
            return []

    def get_user_created_servers(self, user_id: str = None) -> List[MCPServerModel]:
        """Get only user-created (external) servers, excluding built-in ones"""
        try:
            with get_db() as db:
                query = db.query(MCPServer).filter_by(server_type="user_created")
                if user_id:
                    query = query.filter((MCPServer.user_id == user_id) | (MCPServer.user_id.is_(None)))
                
                servers = [MCPServerModel.model_validate(server) for server in query.all()]
                return servers
        except Exception as e:
            print(f"Error getting user-created MCP servers: {e}")
            return []

    def update_server_by_id(self, id: str, updated: dict) -> Optional[MCPServerModel]:
        try:
            with get_db() as db:
                server = db.query(MCPServer).filter_by(id=id).first()
                if not server:
                    return None
                
                # Update fields
                for key, value in updated.items():
                    if hasattr(server, key):
                        setattr(server, key, value)
                
                server.updated_at = int(time.time())
                db.commit()
                db.refresh(server)
                
                return MCPServerModel.model_validate(server)
        except Exception as e:
            print(f"Error updating MCP server: {e}")
            return None

    def delete_server_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                # Check if server exists and is deletable
                server = db.query(MCPServer).filter_by(id=id).first()
                if not server:
                    return False
                if not server.is_deletable:
                    return False
                
                db.delete(server)
                db.commit()
                return True
        except Exception as e:
            print(f"Error deleting MCP server: {e}")
            return False

    def update_server_tools(self, id: str, tools: List) -> Optional[MCPServerModel]:
        """Update the tools list for a server"""
        return self.update_server_by_id(id, {"tools": tools})

    def update_server_capabilities(self, id: str, capabilities: dict) -> Optional[MCPServerModel]:
        """Update the capabilities for a server"""
        return self.update_server_by_id(id, {"capabilities": capabilities})

    def update_server_status(self, id: str, is_active: bool) -> Optional[MCPServerModel]:
        """Update the active status of a server"""
        return self.update_server_by_id(id, {"is_active": is_active})


MCPServers = MCPServerTable()
