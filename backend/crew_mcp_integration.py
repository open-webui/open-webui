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
    api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "o3-mini")
    api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    
    def validate_config(self) -> bool:
        """Validate that required Azure configuration is present"""
        if not self.api_key or not self.endpoint:
            logger.error("Missing required Azure OpenAI configuration. Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables.")
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
        return LLM(
            model=f"azure/{self.azure_config.deployment}",
            temperature=0.1
        )
    
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
                    verbose=True
                )
                
                # Create task for time query
                time_task = Task(
                    description=f"Process this time-related query: {query}. Use the available time tools to get accurate information.",
                    expected_output="A clear and accurate response to the time query with proper formatting.",
                    agent=time_agent
                )
                
                # Create and execute crew
                time_crew = Crew(
                    agents=[time_agent],
                    tasks=[time_task],
                    process=Process.sequential,
                    verbose=True
                )
                
                # Execute the crew
                logger.info("Executing CrewAI crew...")
                result = time_crew.kickoff()
                return str(result)
                
        except Exception as e:
            logger.error(f"Error in CrewAI MCP integration: {e}")
            raise
    
    def get_available_tools(self) -> list:
        """Get list of available MCP tools without running a crew"""
        if not self.time_server_path.exists():
            return []
        
        server_params = StdioServerParameters(
            command="python3",
            args=[str(self.time_server_path)],
            env=dict(os.environ),
        )
        
        try:
            with MCPServerAdapter(server_params) as mcp_tools:
                return [{"name": tool.name, "description": tool.description} for tool in mcp_tools]
        except Exception as e:
            logger.error(f"Error getting MCP tools: {e}")
            return []

# Simple CLI interface for testing
def main():
    """Main function for testing the CrewAI MCP integration"""
    manager = CrewMCPManager()
    
    print("🚀 Starting CrewAI MCP Integration Test")
    print("=" * 50)
    
    try:
        # Test getting available tools first
        tools = manager.get_available_tools()
        print(f"📋 Available MCP Tools: {len(tools)}")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")
        
        if not tools:
            print("❌ No MCP tools available. Check FastMCP server.")
            return
        
        # Test with default query
        print(f"\n🤖 Running CrewAI with query: 'What's the current time in UTC?'")
        result = manager.run_time_crew("What's the current time in UTC?")
        print("\n📝 Crew Result:")
        print("-" * 30)
        print(result)
        
        # Test with timezone query
        print("\n" + "=" * 50)
        print(f"🤖 Running CrewAI with query: 'What time is it in New York?'")
        result2 = manager.run_time_crew("What time is it in New York (US/Eastern)?")
        print("\n📝 Crew Result (Timezone):")
        print("-" * 30)
        print(result2)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
