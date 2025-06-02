"""
FastMCP Server Manager for Open WebUI

This module manages FastMCP server instances and provides a unified interface
for tool discovery and execution.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pytz

from fastmcp.server import FastMCP
from fastmcp.client import Client

log = logging.getLogger(__name__)

class FastMCPManager:
    """Manages FastMCP server instances and client connections"""
    
    def __init__(self):
        self.servers: Dict[str, FastMCP] = {}
        self.clients: Dict[str, Client] = {}
        self._initialize_default_servers()
    
    def _initialize_default_servers(self):
        """Initialize default MCP servers"""
        # Create a time server
        time_server = FastMCP(
            name="TimeServer",
            instructions="A server that provides time-related functionality"
        )
        
        @time_server.tool()
        def get_current_time(timezone: str = "UTC", format: str = "human") -> str:
            """Get the current date and time
            
            Args:
                timezone: Timezone (default: UTC) - e.g., 'UTC', 'US/Eastern', 'Europe/London'
                format: Format type - 'human', 'iso', or 'timestamp'
            
            Returns:
                Current time in the specified timezone and format
            """
            try:
                if timezone.upper() == "UTC":
                    tz = pytz.UTC
                else:
                    tz = pytz.timezone(timezone)
                    
                now = datetime.now(tz)
                
                if format == "iso":
                    return now.isoformat()
                elif format == "timestamp":
                    return str(int(now.timestamp()))
                else:  # human format
                    return now.strftime("%Y-%m-%d %H:%M:%S %Z")
                    
            except Exception as e:
                return f"Error getting time: {str(e)}"
        
        self.register_server("time_server", time_server)
    
    def register_server(self, name: str, server: FastMCP):
        """Register a FastMCP server"""
        self.servers[name] = server
        # Create a client for this server
        self.clients[name] = Client(server)
        log.info(f"Registered MCP server: {name}")
    
    def get_server_names(self) -> List[str]:
        """Get list of registered server names"""
        return list(self.servers.keys())
    
    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all registered servers"""
        all_tools = []
        
        for server_name, client in self.clients.items():
            try:
                async with client:
                    tools = await client.list_tools()
                    
                    for tool in tools:
                        tool_dict = {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema,
                            "mcp_server_name": server_name,
                            "mcp_server_idx": list(self.servers.keys()).index(server_name)
                        }
                        all_tools.append(tool_dict)
            
            except Exception as e:
                log.exception(f"Error getting tools from server {server_name}: {e}")
        
        return all_tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on a specific server"""
        if server_name not in self.clients:
            raise ValueError(f"Server {server_name} not found")
        
        client = self.clients[server_name]
        
        try:
            async with client:
                result = await client.call_tool(tool_name, arguments)
                return result
        except Exception as e:
            log.exception(f"Error calling tool {tool_name} on server {server_name}: {e}")
            raise

# Global manager instance
mcp_manager = FastMCPManager()

def get_mcp_manager() -> FastMCPManager:
    """Get the global MCP manager instance"""
    return mcp_manager
