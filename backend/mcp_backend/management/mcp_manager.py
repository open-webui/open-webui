"""
FastMCP Server Manager for Open WebUI

This module manages FastMCP server instances and client connections.
It does not define tools directly - tools should exist only in external MCP servers.
"""

import logging
import subprocess
import asyncio
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastmcp.client import Client
from fastmcp.client.transports import PythonStdioTransport

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
        url: Optional[str] = None,
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
            "command": command,
            "working_dir": working_dir,
            "env": env,
            "transport": transport,
            "url": url,
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
            is_http_server = "--http" in config["command"]

            if is_http_server:
                # Start HTTP server - no stdio pipes needed
                process = subprocess.Popen(
                    config["command"],
                    cwd=config.get("working_dir"),
                    env=config.get("env"),
                    text=True,
                )

                self.server_processes[name] = process

                # For HTTP servers, create client connection to the URL
                # Extract port from command
                port = None
                if "--http" in config["command"]:
                    http_index = config["command"].index("--http")
                    if http_index + 1 < len(config["command"]):
                        port = config["command"][http_index + 1]

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
                # For stdio servers, use PythonStdioTransport
                # Extract the script path from the command
                if len(config["command"]) >= 2 and config["command"][0] == "python":
                    script_path = config["command"][1]
                    args = config["command"][2:] if len(config["command"]) > 2 else []

                    # Create transport
                    transport = PythonStdioTransport(
                        script_path=script_path,
                        args=args,
                        env=config.get("env"),
                        cwd=config.get("working_dir"),
                    )

                    # Store the transport instead of the client for reuse
                    self.clients[name] = transport

                    log.info(f"Started stdio MCP server: {name}")
                    return True
                else:
                    log.error(
                        f"Invalid command format for stdio server {name}: {config['command']}"
                    )
                    return False

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
                    # For stdio transports, close the client which should handle cleanup
                    if hasattr(self.clients[name], "close"):
                        await self.clients[name].close()
                except Exception as e:
                    log.warning(f"Error closing client for {name}: {e}")
                finally:
                    del self.clients[name]

            # For stdio transports using PythonStdioTransport, the transport handles the subprocess
            # For HTTP servers, terminate any server processes we started
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
            return "not_configured"

        config = self.server_configs[name]

        # For stdio servers using PythonStdioTransport, check if transport exists
        if config.get("transport") == "stdio":
            if name in self.clients:
                return "running"
            else:
                return "stopped"

        # For HTTP servers, check process status
        if name in self.server_processes:
            if self.server_processes[name].poll() is None:
                return "running"
            else:
                # Process has terminated
                del self.server_processes[name]
                return "stopped"

        return "stopped"

    def get_server_names(self) -> List[str]:
        """Get list of configured server names"""
        return list(self.server_configs.keys())

    def get_running_servers(self) -> List[str]:
        """Get list of currently running server names"""
        running = []
        for name in self.server_configs.keys():
            if self.get_server_status(name) == "running":
                running.append(name)
        return running

    def list_servers(self) -> List[Dict[str, Any]]:
        """Get list of all configured servers with their status and information"""
        servers = []
        for name in self.server_configs.keys():
            config = self.server_configs[name]
            status = self.get_server_status(name)

            server_info = {
                "name": name,
                "status": status,
                "transport": config.get("transport", "stdio"),
                "command": config.get("command", []),
                "working_dir": config.get("working_dir"),
                "url": config.get("url"),
                "is_builtin": name
                in ["time_server", "news_server"],  # Mark built-in servers
            }
            servers.append(server_info)

        return servers

    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all connected MCP servers"""
        all_tools = []

        for server_name in self.server_configs.keys():
            if self.get_server_status(server_name) != "running":
                continue

            try:
                config = self.server_configs[server_name]

                if config.get("transport") == "http":
                    # For HTTP servers, create a new client connection
                    url = config.get("url")
                    if url:
                        client = Client(url)
                        async with client:
                            tools = await client.list_tools()

                            for tool in tools:
                                # Mark if this is a built-in server
                                is_builtin = server_name in [
                                    "time_server",
                                    "news_server",
                                ]
                                tool_dict = {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": (
                                        tool.inputSchema.model_dump()
                                        if hasattr(tool.inputSchema, "model_dump")
                                        else tool.inputSchema
                                    ),
                                    "mcp_server_name": server_name,
                                    "mcp_server_idx": list(
                                        self.server_configs.keys()
                                    ).index(server_name),
                                    "is_builtin": is_builtin,
                                }
                                all_tools.append(tool_dict)
                else:
                    # For stdio servers, use the stored transport to create a new client connection
                    if server_name in self.clients:
                        transport = self.clients[server_name]  # This is the transport
                        client = Client(transport)
                        async with client:
                            tools = await client.list_tools()

                            for tool in tools:
                                # Mark if this is a built-in server
                                is_builtin = server_name in [
                                    "time_server",
                                    "news_server",
                                ]
                                tool_dict = {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": (
                                        tool.inputSchema.model_dump()
                                        if hasattr(tool.inputSchema, "model_dump")
                                        else tool.inputSchema
                                    ),
                                    "mcp_server_name": server_name,
                                    "mcp_server_idx": list(
                                        self.server_configs.keys()
                                    ).index(server_name),
                                    "is_builtin": is_builtin,
                                }
                                all_tools.append(tool_dict)

            except Exception as e:
                log.exception(f"Error getting tools from server {server_name}: {e}")

        return all_tools

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
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
            if config.get("transport") == "http":
                url = config.get("url")
                if not url:
                    raise ValueError(f"No URL configured for HTTP server {server_name}")

                # Create new client connection for HTTP servers
                client = Client(url)
                async with client:
                    result = await client.call_tool(tool_name, arguments)
                    return result
            else:
                # For stdio servers, use the stored transport
                if self.get_server_status(server_name) != "running":
                    raise ValueError(f"Server {server_name} is not running")

                if server_name not in self.clients:
                    raise ValueError(f"No transport available for server {server_name}")

                transport = self.clients[server_name]
                client = Client(transport)
                async with client:
                    result = await client.call_tool(tool_name, arguments)
                    return result

        except Exception as e:
            log.exception(
                f"Error calling tool {tool_name} on server {server_name}: {e}"
            )
            raise

    async def initialize_default_servers(self):
        """Initialize and start default MCP servers with stdio transport"""
        # Add configuration for time server (stdio)
        backend_dir = Path(__file__).parent.parent.parent  # Go up to backend/ directory
        time_server_path = backend_dir / "mcp_backend" / "servers" / "fastmcp_time_server.py"
        
        log.info(f"Looking for time server at: {time_server_path}")
        log.info(f"Time server exists: {time_server_path.exists()}")

        if time_server_path.exists():
            self.add_server_config(
                name="time_server",
                command=["python", str(time_server_path)],
                working_dir=str(backend_dir),
                env=dict(os.environ),  # Pass current environment variables
                transport="stdio",
            )

            # Start the time server
            await self.start_server("time_server")
            log.info("Time server started successfully")
        else:
            log.warning(f"Time server not found at {time_server_path}")

        # Add configuration for news server (stdio)
        news_server_path = backend_dir / "mcp_backend" / "servers" / "fastmcp_news_server.py"
        
        log.info(f"Looking for news server at: {news_server_path}")
        log.info(f"News server exists: {news_server_path.exists()}")

        if news_server_path.exists():
            self.add_server_config(
                name="news_server",
                command=["python", str(news_server_path)],
                working_dir=str(backend_dir),
                env=dict(os.environ),  # Pass current environment variables
                transport="stdio",
            )

            # Start the news server
            await self.start_server("news_server")
            log.info("News server started successfully")
        else:
            log.warning(f"News server not found at {news_server_path}")

    async def initialize_external_servers(self):
        """Initialize external MCP servers from database"""
        try:
            # Import here to avoid circular imports
            from mcp_backend.models.mcp_servers import MCPServers

            # Get all active external servers from database
            servers = MCPServers.get_user_created_servers()

            for server in servers:
                if not server.is_active:
                    continue

                try:
                    # Build command list
                    command_list = [server.command] + (server.args or [])

                    # Build URL for HTTP transport
                    server_url = server.url
                    if server.transport == "http" and server.port and not server_url:
                        server_url = f"http://localhost:{server.port}/sse"

                    # Add server configuration
                    self.add_server_config(
                        name=server.name,
                        command=command_list,
                        env=server.env or {},
                        transport=server.transport,
                        url=server_url,
                    )

                    # Start the server
                    success = await self.start_server(server.name)
                    if success:
                        log.info(f"Successfully started external server: {server.name}")
                    else:
                        log.warning(f"Failed to start external server: {server.name}")

                except Exception as e:
                    log.exception(
                        f"Error initializing external server {server.name}: {e}"
                    )

        except Exception as e:
            log.exception(f"Error loading external servers from database: {e}")

    async def initialize_all_servers(self):
        """Initialize both built-in and external servers"""
        await self.initialize_default_servers()
        await self.initialize_external_servers()

    async def cleanup(self):
        """Clean up all server processes and connections"""
        for server_name in list(self.server_configs.keys()):
            await self.stop_server(server_name)

    async def get_tools_from_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get tools from a specific server"""
        if server_name not in self.server_configs:
            return []

        if self.get_server_status(server_name) != "running":
            return []

        try:
            config = self.server_configs[server_name]

            if config.get("transport") == "http":
                # For HTTP servers, create a new client connection
                url = config.get("url")
                if url:
                    client = Client(url)
                    async with client:
                        tools = await client.list_tools()

                        tool_list = []
                        for tool in tools:
                            # Mark if this is a built-in server
                            is_builtin = server_name in ["time_server", "news_server"]
                            tool_dict = {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": (
                                    tool.inputSchema.model_dump()
                                    if hasattr(tool.inputSchema, "model_dump")
                                    else tool.inputSchema
                                ),
                                "mcp_server_name": server_name,
                                "is_builtin": is_builtin,
                            }
                            tool_list.append(tool_dict)

                        return tool_list
            else:
                # For stdio servers, use stored transport to create client
                if server_name in self.clients:
                    transport = self.clients[server_name]
                    client = Client(transport)
                    async with client:
                        tools = await client.list_tools()

                        tool_list = []
                        for tool in tools:
                            # Mark if this is a built-in server
                            is_builtin = server_name in ["time_server", "news_server"]
                            tool_dict = {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": (
                                    tool.inputSchema.model_dump()
                                    if hasattr(tool.inputSchema, "model_dump")
                                    else tool.inputSchema
                                ),
                                "mcp_server_name": server_name,
                                "is_builtin": is_builtin,
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
