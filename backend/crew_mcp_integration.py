#!/usr/bin/env python3
"""
CrewAI MCP Integration for Open WebUI
Simple integration using MCPServerAdapter with stdio transport for FastMCP time server
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Azure OpenAI Configuration
class AzureConfig(BaseModel):
    """Azure OpenAI configuration from environment variables"""

    api_key: str = os.getenv("CREWAI_AZURE_OPENAI_API_KEY", "")
    endpoint: str = os.getenv("CREWAI_AZURE_OPENAI_ENDPOINT", "")
    deployment: str = os.getenv("CREWAI_AZURE_OPENAI_DEPLOYMENT_NAME", "o3-mini")
    api_version: str = os.getenv(
        "CREWAI_AZURE_OPENAI_API_VERSION", "2024-12-01-preview"
    )

    def validate_config(self) -> bool:
        """Validate that required Azure configuration is present"""
        if not self.api_key or not self.endpoint:
            logger.error(
                "Missing required Azure OpenAI configuration. Please set CREWAI_AZURE_OPENAI_API_KEY and CREWAI_AZURE_OPENAI_ENDPOINT environment variables."
            )
            return False
        return True


class CrewMCPManager:
    """Manager for CrewAI with MCP integration"""

    def __init__(self):
        self.azure_config = AzureConfig()
        if not self.azure_config.validate_config():
            raise ValueError("Invalid Azure OpenAI configuration")
        self.backend_dir = Path(__file__).parent
        self.time_server_path = self.backend_dir / "fastmcp_time_server.py"
        self.news_server_path = self.backend_dir / "fastmcp_news_server.py"

    def get_azure_llm_config(self) -> LLM:
        """Get Azure OpenAI LLM configuration for CrewAI"""
        # Set environment variables for LiteLLM/CrewAI Azure OpenAI
        os.environ["AZURE_API_KEY"] = self.azure_config.api_key
        os.environ["AZURE_API_BASE"] = self.azure_config.endpoint
        os.environ["AZURE_API_VERSION"] = self.azure_config.api_version

        # Also set the alternative environment variable names
        os.environ["OPENAI_API_KEY"] = self.azure_config.api_key
        os.environ["OPENAI_API_BASE"] = self.azure_config.endpoint

        # Create LLM instance with Azure configuration
        # Use the environment variables approach which CrewAI handles better
        return LLM(model=f"azure/{self.azure_config.deployment}", temperature=0.1)

    def run_time_crew(self, query: str = "What's the current time?") -> str:
        """
        Run a CrewAI crew with MCP time server tools

        Args:
            query: The time-related query to process

        Returns:
            The crew's response
        """
        if not self.time_server_path.exists():
            raise FileNotFoundError(f"Time server not found at {self.time_server_path}")

        logger.info(f"Starting CrewAI MCP integration for query: {query}")

        # Configure stdio server parameters for FastMCP time server
        server_params = StdioServerParameters(
            command="python3",
            args=[str(self.time_server_path)],
            env=dict(os.environ),  # Pass current environment
        )

        try:
            # Use MCPServerAdapter with context manager for automatic cleanup
            with MCPServerAdapter(server_params) as mcp_tools:
                logger.info(f"Available MCP tools: {[tool.name for tool in mcp_tools]}")

                # Create Azure OpenAI LLM
                llm = self.get_azure_llm_config()

                # Create time specialist agent with MCP tools
                time_agent = Agent(
                    role="Time Specialist",
                    goal="Provide accurate time information using available time tools",
                    backstory="I am an AI specialist focused on time-related queries. I have access to time tools via MCP and can provide current time in various formats and timezones.",
                    tools=mcp_tools,  # Pass MCP tools to agent
                    llm=llm,
                    verbose=True,
                )

                # Create task for time query
                time_task = Task(
                    description=f"Process this time-related query: {query}. Use the available time tools to get accurate information.",
                    expected_output="A clear and accurate response to the time query with proper formatting.",
                    agent=time_agent,
                )

                # Create and execute crew
                time_crew = Crew(
                    agents=[time_agent],
                    tasks=[time_task],
                    process=Process.sequential,
                    verbose=True,
                )

                # Execute the crew
                logger.info("Executing CrewAI crew...")
                result = time_crew.kickoff()
                return str(result)

        except Exception as e:
            logger.error(f"Error in CrewAI MCP integration: {e}")
            raise

    def run_news_crew(self, query: str = "Get the latest news headlines") -> str:
        """
        Run a CrewAI crew with MCP news server tools

        Args:
            query: The news-related query to process

        Returns:
            The crew's response
        """
        if not self.news_server_path.exists():
            raise FileNotFoundError(f"News server not found at {self.news_server_path}")

        logger.info(f"Starting CrewAI MCP news integration for query: {query}")

        # Configure stdio server parameters for FastMCP news server
        server_params = StdioServerParameters(
            command="python3",
            args=[str(self.news_server_path)],
            env=dict(os.environ),  # Pass current environment (includes Azure credentials)
        )

        try:
            # Use MCPServerAdapter with context manager for automatic cleanup
            with MCPServerAdapter(server_params) as mcp_tools:
                logger.info(f"Available MCP news tools: {[tool.name for tool in mcp_tools]}")

                # Create Azure OpenAI LLM
                llm = self.get_azure_llm_config()

                # Create news specialist agent with MCP tools
                news_agent = Agent(
                    role="News Specialist",
                    goal="Provide current news information and analysis using available news tools",
                    backstory="I am an AI specialist focused on news and current events. I have access to NewsDesk via MCP tools and can fetch the latest headlines, analyze news trends, and provide relevant news information based on user queries.",
                    tools=mcp_tools,  # Pass MCP tools to agent
                    llm=llm,
                    verbose=True,
                )

                # Create task for news query
                news_task = Task(
                    description=f"Process this news-related query: {query}. Use the available news tools to get current headlines and relevant information. If the query asks for specific topics, filter or search for relevant articles.",
                    expected_output="A clear and informative response with current news headlines, properly formatted with sources and publication dates when available.",
                    agent=news_agent,
                )

                # Create and execute crew
                news_crew = Crew(
                    agents=[news_agent],
                    tasks=[news_task],
                    process=Process.sequential,
                    verbose=True,
                )

                # Execute the crew
                logger.info("Executing CrewAI news crew...")
                result = news_crew.kickoff()
                return str(result)

        except Exception as e:
            logger.error(f"Error in CrewAI MCP news integration: {e}")
            raise

    def run_multi_server_crew(self, query: str) -> str:
        """
        Run a CrewAI crew with tools from ALL available MCP servers

        Args:
            query: The query to process

        Returns:
            The crew's response using all available tools
        """
        logger.info(f"Starting CrewAI multi-server integration for query: {query}")

        available_servers = self.get_available_servers()
        all_tools = []

        if not available_servers:
            raise FileNotFoundError("No MCP servers found")

        try:
            # Create a list to hold all MCP adapters for proper cleanup
            adapters = []
            
            # Initialize all servers and collect their tools
            for server_name, server_path in available_servers.items():
                try:
                    server_params = StdioServerParameters(
                        command="python3",
                        args=[str(server_path)],
                        env=dict(os.environ),
                    )
                    
                    adapter = MCPServerAdapter(server_params)
                    adapter.__enter__()  # Start the server
                    adapters.append(adapter)
                    
                    # Add all tools from this server
                    for tool in adapter:
                        all_tools.append(tool)
                    
                    logger.info(f"Connected to {server_name} with {len(list(adapter))} tools")
                except Exception as e:
                    logger.error(f"Failed to connect to {server_name}: {e}")
                    continue

            if not all_tools:
                raise RuntimeError("No tools available from any MCP server")

            logger.info(f"Total available tools from all servers: {[tool.name for tool in all_tools]}")

            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Create a universal agent that can use all available MCP tools
            universal_agent = Agent(
                role="Universal AI Assistant",
                goal="Provide comprehensive assistance using all available tools and resources",
                backstory="I am an AI assistant with access to multiple specialized tools including time services, news feeds, and other MCP-enabled capabilities. I can combine information from different sources to provide complete and accurate responses.",
                tools=all_tools,  # Pass ALL MCP tools from all servers
                llm=llm,
                verbose=True,
            )

            # Create task that can utilize any/all tools as needed
            universal_task = Task(
                description=f"Process this query: {query}. Use any relevant tools from the available MCP servers to provide a comprehensive response. You have access to time tools, news tools, and other capabilities.",
                expected_output="A comprehensive response using appropriate tools and information sources, properly formatted and with relevant details.",
                agent=universal_agent,
            )

            # Create and execute crew
            universal_crew = Crew(
                agents=[universal_agent],
                tasks=[universal_task],
                process=Process.sequential,
                verbose=True,
            )

            # Execute the crew
            logger.info("Executing CrewAI universal crew with all available tools...")
            result = universal_crew.kickoff()
            
            # Clean up all adapters
            for adapter in adapters:
                try:
                    adapter.__exit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error cleaning up adapter: {e}")
            
            return str(result)

        except Exception as e:
            # Ensure cleanup happens even on error
            for adapter in adapters:
                try:
                    adapter.__exit__(None, None, None)
                except:
                    pass
            logger.error(f"Error in CrewAI multi-server integration: {e}")
            raise

    def get_available_servers(self) -> dict:
        """Get all available MCP servers dynamically"""
        servers = {}
        
        # Define known servers (can be extended in the future)
        known_servers = {
            "time_server": self.time_server_path,
            "news_server": self.news_server_path,
        }
        
        # Add any other fastmcp_*.py servers found in the backend directory
        for server_file in self.backend_dir.glob("fastmcp_*.py"):
            server_name = server_file.stem  # Remove .py extension
            if server_name not in known_servers:
                servers[server_name] = server_file
                logger.info(f"Discovered additional MCP server: {server_name}")
        
        # Add known servers
        servers.update(known_servers)
        
        # Filter to only existing servers
        return {name: path for name, path in servers.items() if path.exists()}

    def get_available_tools(self) -> list:
        """Get list of available MCP tools from all discovered servers"""
        all_tools = []
        available_servers = self.get_available_servers()
        
        for server_name, server_path in available_servers.items():
            server_params = StdioServerParameters(
                command="python3",
                args=[str(server_path)],
                env=dict(os.environ),
            )
            
            try:
                with MCPServerAdapter(server_params) as server_tools:
                    for tool in server_tools:
                        all_tools.append({
                            "name": tool.name, 
                            "description": tool.description,
                            "server": server_name
                        })
                    logger.info(f"Found {len(list(server_tools))} tools from {server_name}")
            except Exception as e:
                logger.error(f"Error getting tools from {server_name}: {e}")
        
        return all_tools


# Simple CLI interface for testing
def main():
    """Main function for testing the CrewAI MCP integration"""
    manager = CrewMCPManager()

    print("🚀 Starting CrewAI MCP Integration Test")
    print("=" * 50)

    try:
        # Test server discovery
        print("\n📡 Available MCP Servers:")
        available_servers = manager.get_available_servers()
        for server_name, server_path in available_servers.items():
            print(f"   ✓ {server_name}: {server_path}")

        # Test getting available tools first
        tools = manager.get_available_tools()
        print(f"\n📋 Available MCP Tools: {len(tools)}")
        for tool in tools:
            print(f"   - {tool['name']} ({tool['server']}): {tool['description']}")

        if not tools:
            print("❌ No MCP tools available. Check FastMCP servers.")
            return

        # Test individual server capabilities
        if any(tool['server'] == 'time_server' for tool in tools):
            print(f"\n🕐 Testing Time Server:")
            print(f"Query: 'What's the current time in UTC?'")
            result = manager.run_time_crew("What's the current time in UTC?")
            print("Result:", result[:200] + "..." if len(result) > 200 else result)

        if any(tool['server'] == 'news_server' for tool in tools):
            print(f"\n📰 Testing News Server:")
            print(f"Query: 'Get the latest news headlines'")
            result = manager.run_news_crew("Get the latest news headlines")
            print("Result:", result[:200] + "..." if len(result) > 200 else result)

        # Test multi-server capability
        if len(available_servers) > 1:
            print(f"\n🌐 Testing Multi-Server Integration:")
            print(f"Query: 'Provide current time and latest news summary'")
            result = manager.run_multi_server_crew("Provide current time and latest news summary")
            print("Multi-Server Result:", result[:300] + "..." if len(result) > 300 else result)
        else:
            print(f"\n⚠️  Only one server available. Multi-server test skipped.")
            
        print(f"\n✅ All tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
