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
        Run crews from multiple servers sequentially and combine results.
        This avoids the async event loop issues by using the working individual crew methods.

        Args:
            query: The query to process

        Returns:
            Combined response from multiple crews
        """
        logger.info(f"Starting multi-server CrewAI integration for query: {query}")

        available_servers = self.get_available_servers()
        if not available_servers:
            raise FileNotFoundError("No MCP servers found")

        results = []
        
        # Check what servers are available and run the appropriate crews
        has_time_server = any('time' in name.lower() for name in available_servers.keys())
        has_news_server = any('news' in name.lower() for name in available_servers.keys())
        
        try:
            # Run time crew if available
            if has_time_server:
                logger.info("Running time crew for multi-server query")
                try:
                    time_result = self.run_time_crew(query)
                    results.append(f"Time Information:\n{time_result}")
                except Exception as e:
                    logger.error(f"Time crew failed: {e}")
                    results.append("Time Information: Could not retrieve time information.")
            
            # Run news crew if available
            if has_news_server:
                logger.info("Running news crew for multi-server query")
                try:
                    news_result = self.run_news_crew(query)
                    results.append(f"News Information:\n{news_result}")
                except Exception as e:
                    logger.error(f"News crew failed: {e}")
                    results.append("News Information: Could not retrieve news information.")
            
            if not results:
                return "No specialized crews available to handle this query."
            
            # Combine results
            combined_result = "\n\n".join(results)
            logger.info(f"Multi-server crew completed with {len(results)} results")
            return combined_result
            
        except Exception as e:
            logger.error(f"Error in CrewAI multi-server integration: {e}")
            raise

    def run_intelligent_crew(self, query: str, selected_tools: list = None) -> str:
        """
        Intelligent router crew that analyzes the query and makes smart routing decisions
        to coordinate with appropriate specialist agents (time, news, etc.) based on the 
        user's actual needs and intent, not keywords.
        
        Args:
            query: The query to process
            selected_tools: List of tool IDs selected by the user (optional)
            
        Returns:
            The crew's response using intelligent routing and coordination
        """
        logger.info(f"Starting intelligent router for query: {query}")
        logger.info(f"Selected tools: {selected_tools}")
        
        try:
            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()
            
            # Determine available specialists based on selected tools
            available_specialists = []
            if selected_tools:
                if any('time' in tool.lower() for tool in selected_tools):
                    available_specialists.append("TIME")
                if any('news' in tool.lower() or 'headline' in tool.lower() for tool in selected_tools):
                    available_specialists.append("NEWS")
            else:
                # If no tools selected, all specialists are available
                available_specialists = ["TIME", "NEWS"]
            
            logger.info(f"Available specialists: {available_specialists}")
            
            # Create router agent that makes intelligent routing decisions
            router_agent = Agent(
                role="Intelligent Query Router",
                goal="Analyze user queries and make smart routing decisions to appropriate specialists",
                backstory=f"""You are an intelligent query router. Your job is to understand what the user 
                is actually asking for and make routing decisions accordingly. 

                Available specialists:
                - TIME: Handles current time, dates, timezones, scheduling, time-related calculations
                - NEWS: Handles current news, headlines, articles, breaking news, news search
                
                Available specialists for this query: {', '.join(available_specialists)}
                
                Your job is to analyze the user's intent and decide:
                1. Which specialist(s) can best answer their question
                2. What specific information each specialist should provide
                3. Whether one specialist is sufficient or multiple are needed
                
                Focus on the user's actual intent and information needs, not just keywords.""",
                verbose=True,
                allow_delegation=False,
                llm=llm
            )
            
            # Create routing decision task
            routing_task = Task(
                description=f"""Analyze this user query and make a routing decision: "{query}"

Available specialists: {', '.join(available_specialists)}

Based on what the user is actually asking for, decide:

1. ROUTING DECISION: Which specialist(s) should handle this query?
   - Choose TIME if the user needs: current time, date, timezone info, time calculations, scheduling
   - Choose NEWS if the user needs: current news, headlines, breaking news, articles, news search  
   - Choose BOTH if the user needs information from both domains
   - Choose the most relevant one if the query could go either way

2. QUERY ADAPTATION: What specific question should each chosen specialist answer?
   - For TIME specialist: Adapt the query to focus on time-related aspects
   - For NEWS specialist: Adapt the query to focus on news-related aspects
   - Make sure each specialist gets a clear, focused query

3. COORDINATION: How should the results be presented?
   - Single specialist: Direct response
   - Multiple specialists: Combined response with clear organization

Think carefully about the user's actual intent and information needs.""",
                expected_output="""Provide your routing decision in this exact format:

ROUTING_DECISION: [TIME|NEWS|BOTH]
TIME_QUERY: [specific query for time specialist or NONE]
NEWS_QUERY: [specific query for news specialist or NONE]
PRESENTATION: [brief note on how to present results]

Be decisive and specific. Only route to specialists that are actually needed.""",
                agent=router_agent,
            )
            
            # Execute routing decision
            routing_crew = Crew(
                agents=[router_agent],
                tasks=[routing_task],
                process=Process.sequential,
                verbose=True,
            )
            
            logger.info("Executing routing decision...")
            routing_result = routing_crew.kickoff()
            logger.info(f"Routing decision result: {routing_result}")
            
            # Parse the routing decision
            routing_str = str(routing_result)
            
            # Extract structured routing information
            routing_decision = None
            time_query = None
            news_query = None
            
            for line in routing_str.split('\n'):
                line = line.strip()
                if line.startswith('ROUTING_DECISION:'):
                    routing_decision = line.split(':', 1)[1].strip()
                elif line.startswith('TIME_QUERY:'):
                    time_query_raw = line.split(':', 1)[1].strip()
                    time_query = time_query_raw if time_query_raw != 'NONE' else None
                elif line.startswith('NEWS_QUERY:'):
                    news_query_raw = line.split(':', 1)[1].strip()
                    news_query = news_query_raw if news_query_raw != 'NONE' else None
            
            logger.info(f"Parsed routing - decision: {routing_decision}, time_query: {time_query}, news_query: {news_query}")
            
            # Execute the routing decision
            responses = []
            
            # Route to time specialist if needed and available
            if time_query and "TIME" in available_specialists:
                logger.info(f"Routing to TIME specialist with query: {time_query}")
                try:
                    time_response = self.run_time_crew(time_query)
                    responses.append(time_response)
                except Exception as e:
                    logger.error(f"Error from TIME specialist: {e}")
                    responses.append("Unable to retrieve time information at this moment.")
            
            # Route to news specialist if needed and available
            if news_query and "NEWS" in available_specialists:
                logger.info(f"Routing to NEWS specialist with query: {news_query}")
                try:
                    news_response = self.run_news_crew(news_query)
                    responses.append(news_response)
                except Exception as e:
                    logger.error(f"Error from NEWS specialist: {e}")
                    responses.append("Unable to retrieve news information at this moment.")
            
            # If no routing was determined or no responses, make a smart fallback decision
            if not responses:
                logger.info("No responses from routing decision, making intelligent fallback...")
                # Analyze the query content to make a smart guess
                query_lower = query.lower()
                
                # Check for time-related content
                time_indicators = ['time', 'date', 'when', 'now', 'today', 'tomorrow', 'clock', 'timezone', 'hour', 'minute', 'second', 'current time']
                news_indicators = ['news', 'headline', 'breaking', 'article', 'current events', 'happening', 'latest', 'today news', 'update']
                
                has_time_indicators = any(indicator in query_lower for indicator in time_indicators)
                has_news_indicators = any(indicator in query_lower for indicator in news_indicators)
                
                if has_time_indicators and "TIME" in available_specialists:
                    logger.info("Fallback: routing to TIME specialist based on query analysis")
                    time_response = self.run_time_crew(query)
                    responses.append(time_response)
                elif has_news_indicators and "NEWS" in available_specialists:
                    logger.info("Fallback: routing to NEWS specialist based on query analysis")
                    news_response = self.run_news_crew(query)
                    responses.append(news_response)
                else:
                    # Default to first available specialist
                    if "TIME" in available_specialists:
                        logger.info("Fallback: defaulting to TIME specialist")
                        time_response = self.run_time_crew(query)
                        responses.append(time_response)
                    elif "NEWS" in available_specialists:
                        logger.info("Fallback: defaulting to NEWS specialist")
                        news_response = self.run_news_crew(query)
                        responses.append(news_response)
            
            # Return the response(s)
            if len(responses) == 1:
                logger.info("Returning single specialist response")
                return responses[0]
            elif len(responses) > 1:
                logger.info("Combining multiple specialist responses")
                # Multiple responses - combine them intelligently
                return "\n\n".join(responses)
            else:
                logger.warning("No responses generated")
                return "I apologize, but I was unable to process your request at this time."
                
        except Exception as e:
            logger.error(f"Error in intelligent routing: {e}")
            # Emergency fallback - route to most appropriate specialist
            logger.info("Using emergency fallback routing...")
            
            if selected_tools:
                # Use selected tools to determine routing
                has_time = any('time' in tool.lower() for tool in selected_tools)
                has_news = any('news' in tool.lower() or 'headline' in tool.lower() for tool in selected_tools)
                
                if has_time and not has_news:
                    logger.info("Emergency fallback: TIME only")
                    return self.run_time_crew(query)
                elif has_news and not has_time:
                    logger.info("Emergency fallback: NEWS only")
                    return self.run_news_crew(query)
                elif has_time and has_news:
                    # Both selected - route to most appropriate based on query content
                    query_lower = query.lower()
                    if any(word in query_lower for word in ['news', 'headline', 'breaking', 'article']):
                        logger.info("Emergency fallback: NEWS (both selected, news priority)")
                        return self.run_news_crew(query)
                    else:
                        logger.info("Emergency fallback: TIME (both selected, time priority)")
                        return self.run_time_crew(query)
                else:
                    logger.info("Emergency fallback: TIME (default)")
                    return self.run_time_crew(query)
            else:
                # No tools selected - analyze query content
                query_lower = query.lower()
                if any(word in query_lower for word in ['news', 'headline', 'breaking', 'article', 'current events']):
                    logger.info("Emergency fallback: NEWS (query analysis)")
                    return self.run_news_crew(query)
                else:
                    logger.info("Emergency fallback: TIME (default)")
                    return self.run_time_crew(query)

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
