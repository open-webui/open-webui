"""
FastMCP Server Manager for Open WebUI

This module manages FastMCP server instances and client connections.
It does not define tools directly - tools should exist only in external MCP servers.
"""

import logging
import subprocess
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastmcp.client import Client

log = logging.getLogger(__name__)

class FastMCPManager:
    """Manages FastMCP server instances and client connections"""
    
    def __init__(self):
        self.clients: Dict[str, Client] = {}
        self.server_processes: Dict[str, subprocess.Popen] = {}
        self.server_configs: Dict[str, Dict[str, Any]] = {}
    
    def add_server_config(
        self, 
        name: str, 
        command: List[str], 
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        transport: str = "stdio",
        url: Optional[str] = None
    ):
        """Add configuration for an external MCP server
        
        Args:
            name: Server name/identifier
            command: Command to start the server (e.g., ['python', 'fastmcp_news_server.py'])
            working_dir: Working directory for the server process
            env: Environment variables for the server process
            transport: Transport type ('stdio' or 'http')
            url: URL for HTTP transport
        """
        self.server_configs[name] = {
            'command': command,
            'working_dir': working_dir,
            'env': env,
            'transport': transport,
            'url': url
        }
        log.info(f"Added server configuration: {name} ({transport})")
    
    async def start_server(self, name: str) -> bool:
        """Start an external MCP server process
        
        Args:
            name: Server name to start
            
        Returns:
            True if server started successfully, False otherwise
        """
        if name not in self.server_configs:
            log.error(f"No configuration found for server: {name}")
            return False
        
        if name in self.server_processes:
            if self.server_processes[name].poll() is None:
                log.info(f"Server {name} is already running")
                return True
            else:
                # Process has terminated, remove it
                del self.server_processes[name]
        
        config = self.server_configs[name]
        
        try:
            # Check if this is an HTTP server (has --http in command)
            is_http_server = "--http" in config['command']
            
            if is_http_server:
                # Start HTTP server - no stdio pipes needed
                process = subprocess.Popen(
                    config['command'],
                    cwd=config.get('working_dir'),
                    env=config.get('env'),
                    text=True
                )
                
                self.server_processes[name] = process
                
                # For HTTP servers, create client connection to the URL
                # Extract port from command
                port = None
                if "--http" in config['command']:
                    http_index = config['command'].index("--http")
                    if http_index + 1 < len(config['command']):
                        port = config['command'][http_index + 1]
                
                if port:
                    # Wait a moment for server to start
                    await asyncio.sleep(1)
                    
                    # Create client connection to HTTP endpoint
                    url = f"http://localhost:{port}/sse"
                    client = Client(url)
                    self.clients[name] = client
                
                log.info(f"Started HTTP MCP server: {name} on port {port}")
                return True
            else:
                # Start stdio server with pipes
                process = subprocess.Popen(
                    config['command'],
                    cwd=config.get('working_dir'),
                    env=config.get('env'),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                self.server_processes[name] = process
                
                # Create a client connection to the server
                # For stdio transport, we need to connect to the process
                client = Client()
                await client.connect_stdio(process.stdin, process.stdout)
                self.clients[name] = client
                
                log.info(f"Started stdio MCP server: {name}")
                return True
            
        except Exception as e:
            log.exception(f"Failed to start server {name}: {e}")
            return False
    
    async def stop_server(self, name: str) -> bool:
        """Stop an external MCP server process
        
        Args:
            name: Server name to stop
            
        Returns:
            True if server stopped successfully, False otherwise
        """
        try:
            # Close client connection
            if name in self.clients:
                try:
                    # For HTTP clients, we may not need to explicitly close
                    if hasattr(self.clients[name], 'close'):
                        await self.clients[name].close()
                except Exception as e:
                    log.warning(f"Error closing client for {name}: {e}")
                finally:
                    del self.clients[name]
            
            # Terminate server process
            if name in self.server_processes:
                process = self.server_processes[name]
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                
                del self.server_processes[name]
            
            log.info(f"Stopped MCP server: {name}")
            return True
            
        except Exception as e:
            log.exception(f"Failed to stop server {name}: {e}")
            return False
    
    async def restart_server(self, name: str) -> bool:
        """Restart an external MCP server
        
        Args:
            name: Server name to restart
            
        Returns:
            True if server restarted successfully, False otherwise
        """
        await self.stop_server(name)
        return await self.start_server(name)
    
    def get_server_status(self, name: str) -> str:
        """Get the status of a server
        
        Args:
            name: Server name
            
        Returns:
            Status string: 'running', 'stopped', 'not_configured'
        """
        if name not in self.server_configs:
            return 'not_configured'
        
        if name in self.server_processes:
            if self.server_processes[name].poll() is None:
                return 'running'
            else:
                # Process has terminated
                del self.server_processes[name]
                return 'stopped'
        
        return 'stopped'
    
    def get_server_names(self) -> List[str]:
        """Get list of configured server names"""
        return list(self.server_configs.keys())
    
    def get_running_servers(self) -> List[str]:
        """Get list of currently running server names"""
        running = []
        for name in self.server_configs.keys():
            if self.get_server_status(name) == 'running':
                running.append(name)
        return running
    
    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all connected MCP servers"""
        all_tools = []
        
        for server_name in self.server_configs.keys():
            if self.get_server_status(server_name) != 'running':
                continue
                
            try:
                config = self.server_configs[server_name]
                
                if config.get('transport') == 'http':
                    # For HTTP servers, create a new client connection
                    url = config.get('url')
                    if url:
                        client = Client(url)
                        async with client:
                            tools = await client.list_tools()
                            
                            for tool in tools:
                                tool_dict = {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema,
                                    "mcp_server_name": server_name,
                                    "mcp_server_idx": list(self.server_configs.keys()).index(server_name)
                                }
                                all_tools.append(tool_dict)
                else:
                    # For stdio servers, use the stored client connection
                    if server_name in self.clients:
                        client = self.clients[server_name]
                        tools = await client.list_tools()
                        
                        for tool in tools:
                            tool_dict = {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema,
                                "mcp_server_name": server_name,
                                "mcp_server_idx": list(self.server_configs.keys()).index(server_name)
                            }
                            all_tools.append(tool_dict)
            
            except Exception as e:
                log.exception(f"Error getting tools from server {server_name}: {e}")
        
        return all_tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on a specific MCP server
        
        Args:
            server_name: Name of the server to call the tool on
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Result from the tool execution
            
        Raises:
            ValueError: If server is not found or not running
            Exception: If tool execution fails
        """
        if server_name not in self.server_configs:
            raise ValueError(f"Server {server_name} not configured")
        
        config = self.server_configs[server_name]
        
        try:
            # For HTTP servers, create a new client connection for each call
            if config.get('transport') == 'http':
                url = config.get('url')
                if not url:
                    raise ValueError(f"No URL configured for HTTP server {server_name}")
                
                # Create new client connection for HTTP servers
                client = Client(url)
                async with client:
                    result = await client.call_tool(tool_name, arguments)
                    return result
            else:
                # For stdio servers, use the stored client connection
                if self.get_server_status(server_name) != 'running':
                    raise ValueError(f"Server {server_name} is not running")
                
                if server_name not in self.clients:
                    raise ValueError(f"No client connection for server {server_name}")
                
                client = self.clients[server_name]
                result = await client.call_tool(tool_name, arguments)
                return result
                
        except Exception as e:
            log.exception(f"Error calling tool {tool_name} on server {server_name}: {e}")
            raise
    
    async def initialize_default_servers(self):
        """Initialize and start default MCP servers with HTTP transport"""
        # Add configuration for time server (HTTP on port 8083)
        backend_dir = Path(__file__).parent.parent
        time_server_path = backend_dir / "fastmcp_time_server.py"
        
        if time_server_path.exists():
            self.add_server_config(
                name="time_server_http",
                command=["python", str(time_server_path), "--http", "8083"],
                working_dir=str(backend_dir),
                transport="http",
                url="http://localhost:8083/sse"
            )
            
            # Start the time server
            await self.start_server("time_server_http")
        
        # Add configuration for news server (HTTP on port 8084)
        news_server_path = backend_dir / "fastmcp_news_server.py"
        
        if news_server_path.exists():
            self.add_server_config(
                name="news_server_http",
                command=["python", str(news_server_path), "--http", "8084"],
                working_dir=str(backend_dir),
                transport="http",
                url="http://localhost:8084/sse"
            )
            
            # Start the news server
            await self.start_server("news_server_http")
    
    async def cleanup(self):
        """Clean up all server processes and connections"""
        for server_name in list(self.server_configs.keys()):
            await self.stop_server(server_name)
    
    async def get_tools_from_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get tools from a specific server"""
        if server_name not in self.server_configs:
            return []
            
        if self.get_server_status(server_name) != 'running':
            return []
        
        try:
            config = self.server_configs[server_name]
            
            if config.get('transport') == 'http':
                # For HTTP servers, create a new client connection
                url = config.get('url')
                if url:
                    client = Client(url)
                    async with client:
                        tools = await client.list_tools()
                        
                        tool_list = []
                        for tool in tools:
                            tool_dict = {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema,
                                "mcp_server_name": server_name
                            }
                            tool_list.append(tool_dict)
                        
                        return tool_list
            else:
                # For stdio servers, use stored client
                if server_name in self.clients:
                    client = self.clients[server_name]
                    tools = await client.list_tools()
                    
                    tool_list = []
                    for tool in tools:
                        tool_dict = {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema,
                            "mcp_server_name": server_name
                        }
                        tool_list.append(tool_dict)
                    
                    return tool_list
                    
        except Exception as e:
            log.exception(f"Error getting tools from server {server_name}: {e}")
        
        return []

# Global manager instance
mcp_manager = FastMCPManager()

def get_mcp_manager() -> FastMCPManager:
    """Get the global MCP manager instance"""
    return mcp_manager
