#!/usr/bin/env python3
"""
CrewAI MCP Integration for Open WebUI
Simple integration using MCPServerAdapter with stdio transport for FastMCP time server
"""

import os
import logging
from pathlib import Path
from pydantic import BaseModel

# Disable CrewAI telemetry to avoid connection timeout errors
os.environ["OTEL_SDK_DISABLED"] = "true"

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CrewAI verbosity control - disable in production for cleaner logs
CREW_VERBOSE = os.getenv("CREW_VERBOSE", "false").lower() == "true"

# Module-level MCP server adapters - initialized once and reused
_time_server_adapter = None
_news_server_adapter = None
_mpo_sharepoint_server_adapter = None
_adapters_initialized = False


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
        self.backend_dir = Path(__file__).parent.parent.parent  # Go up to backend dir
        self.time_server_path = (
            self.backend_dir / "mcp_backend" / "servers" / "fastmcp_time_server.py"
        )
        self.news_server_path = (
            self.backend_dir / "mcp_backend" / "servers" / "fastmcp_news_server.py"
        )
        # SharePoint server paths - use new multi-department implementation
        self.mpo_sharepoint_server_path = (
            self.backend_dir / "mcp_backend" / "servers" / "mpo_sharepoint_server.py"
        )

        # Legacy generic SharePoint server (fallback)
        self.sharepoint_server_path = (
            self.backend_dir
            / "mcp_backend"
            / "servers"
            / "generic_sharepoint_server_multi_dept.py"
        )

        # User token for OBO flow
        self.user_jwt_token = None

    def set_user_token(self, token: str):
        """Set the user's JWT token for OBO authentication"""
        self.user_jwt_token = token
        logger.info(f"User JWT token set for OBO flow: {bool(token)}")

        # Set as environment variable for SharePoint MCP servers to use
        if token:
            os.environ["USER_JWT_TOKEN"] = token
        elif "USER_JWT_TOKEN" in os.environ:
            del os.environ["USER_JWT_TOKEN"]

    def initialize_mcp_adapters(self):
        """Initialize all MCP server adapters once at startup"""
        global _time_server_adapter, _news_server_adapter, _mpo_sharepoint_server_adapter, _adapters_initialized

        if _adapters_initialized:
            logger.info("MCP adapters already initialized, skipping...")
            return

        logger.info("🚀 Initializing MCP server adapters...")

        # Initialize Time Server
        try:
            time_server_params = StdioServerParameters(
                command="python",
                args=[str(self.time_server_path)],
                env=dict(os.environ),  # Pass environment variables
            )
            adapter = MCPServerAdapter(time_server_params)
            _time_server_adapter = adapter.__enter__()  # Get the tools from __enter__()
            logger.info("✅ Time server adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Time server: {e}")
            _time_server_adapter = None

        # Initialize News Server
        try:
            news_server_params = StdioServerParameters(
                command="python",
                args=[str(self.news_server_path)],
                env=dict(os.environ),  # Pass environment variables
            )
            adapter = MCPServerAdapter(news_server_params)
            _news_server_adapter = adapter.__enter__()  # Get the tools from __enter__()
            logger.info("✅ News server adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize News server: {e}")
            _news_server_adapter = None

        # Initialize MPO SharePoint Server - always try to initialize
        try:
            mpo_sharepoint_params = StdioServerParameters(
                command="python",
                args=[str(self.mpo_sharepoint_server_path)],
                env=dict(
                    os.environ
                ),  # Pass environment variables so .env vars are available
            )
            adapter = MCPServerAdapter(mpo_sharepoint_params)
            _mpo_sharepoint_server_adapter = (
                adapter.__enter__()
            )  # Get the tools from __enter__()
            logger.info("✅ MPO SharePoint server adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize MPO SharePoint server: {e}")
            logger.error(
                f"   This is expected in local dev without MPO_SHP_* environment variables"
            )
            _mpo_sharepoint_server_adapter = None

        _adapters_initialized = True

        # Report initialization status
        initialized_count = sum(
            [
                _time_server_adapter is not None,
                _news_server_adapter is not None,
                _mpo_sharepoint_server_adapter is not None,
            ]
        )
        logger.info(
            f"🎉 MCP server initialization complete: {initialized_count}/3 adapters initialized"
        )

    def cleanup_mcp_adapters(self):
        """Cleanup all MCP server adapters on shutdown"""
        global _time_server_adapter, _news_server_adapter, _mpo_sharepoint_server_adapter, _adapters_initialized

        logger.info("🧹 Cleaning up MCP server adapters...")

        for adapter_name, adapter in [
            ("Time", _time_server_adapter),
            ("News", _news_server_adapter),
            ("MPO SharePoint", _mpo_sharepoint_server_adapter),
        ]:
            if adapter is not None:
                try:
                    adapter.__exit__(None, None, None)
                    logger.info(f"✅ {adapter_name} server adapter cleaned up")
                except Exception as e:
                    logger.error(f"❌ Error cleaning up {adapter_name} adapter: {e}")

        _time_server_adapter = None
        _news_server_adapter = None
        _mpo_sharepoint_server_adapter = None
        _adapters_initialized = False

        logger.info("🎉 All MCP server adapters cleaned up")

    def get_azure_llm_config(self) -> LLM:
        """Get Azure OpenAI LLM configuration for CrewAI"""
        # Set environment variables for LiteLLM/CrewAI Azure OpenAI
        # CrewAI 1.7.2 uses LiteLLM which requires specific Azure env var format
        os.environ["AZURE_API_KEY"] = self.azure_config.api_key
        os.environ["AZURE_API_BASE"] = self.azure_config.endpoint
        os.environ["AZURE_API_VERSION"] = self.azure_config.api_version

        # Create LLM instance with Azure configuration
        # CrewAI 1.7.2 LiteLLM format: azure/<deployment_name>
        # Must NOT include base_url or api_key - LiteLLM reads from env vars
        # Add timeout to prevent hanging in K8s environments
        # O3-mini doesn't support temperature or max_completion_tokens parameters
        return LLM(
            model=f"azure/{self.azure_config.deployment}",
            timeout=30,  # 30 second timeout per LLM API call
        )

    def run_time_crew(self, query: str = "What's the current time?") -> str:
        """
        Run a CrewAI crew with MCP time server tools

        Args:
            query: The time-related query to process

        Returns:
            The crew's response
        """
        global _time_server_adapter

        if not self.time_server_path.exists():
            raise FileNotFoundError(f"Time server not found at {self.time_server_path}")

        if _time_server_adapter is None:
            raise RuntimeError(
                "Time server adapter not initialized. Call initialize_mcp_adapters() first."
            )

        logger.info(f"Starting CrewAI MCP integration for query: {query}")

        try:
            # Use the pre-initialized time server adapter (already contains tools from __enter__())
            mcp_tools = _time_server_adapter
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
                verbose=CREW_VERBOSE,
                max_iter=3,  # Limit iterations to prevent excessive thinking
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
                verbose=CREW_VERBOSE,
            )

            # Execute the crew
            logger.info("Executing CrewAI crew...")
            result = time_crew.kickoff()
            logger.info("CrewAI crew execution completed successfully")
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
        global _news_server_adapter

        if not self.news_server_path.exists():
            raise FileNotFoundError(f"News server not found at {self.news_server_path}")

        if _news_server_adapter is None:
            raise RuntimeError(
                "News server adapter not initialized. Call initialize_mcp_adapters() first."
            )

        logger.info(f"Starting CrewAI MCP news integration for query: {query}")

        try:
            # Use the pre-initialized news server adapter (already contains tools from __enter__())
            mcp_tools = _news_server_adapter
            logger.info(
                f"Available MCP news tools: {[tool.name for tool in mcp_tools]}"
            )

            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Create news specialist agent with MCP tools
            news_agent = Agent(
                role="News Specialist",
                goal="Provide current news information exactly as returned by news tools, preserving original formatting and language",
                backstory="I am an AI specialist focused on news and current events. I have access to NewsDesk via MCP tools and can fetch the latest headlines. My role is to pass through the news information exactly as provided by the tools, preserving all formatting, emojis, language (French/English), and structure without translation or summarization.",
                tools=mcp_tools,  # Pass MCP tools to agent
                llm=llm,
                verbose=CREW_VERBOSE,
                max_iter=5,  # Limit iterations to prevent excessive thinking
            )

            # Create task for news query
            news_task = Task(
                description=f"Process this news-related query: {query}. Use the available news tools to get current headlines and relevant information. If the query asks for specific topics, filter or search for relevant articles.",
                expected_output="Return the news information EXACTLY as provided by the news tools, preserving all original formatting, emojis, language, and structure. Do NOT translate, summarize, or reformat the content. Simply pass through the original response from the news tools with minimal additional commentary.",
                agent=news_agent,
            )

            # Create and execute crew
            news_crew = Crew(
                agents=[news_agent],
                tasks=[news_task],
                process=Process.sequential,
                verbose=CREW_VERBOSE,
            )

            # Execute the crew
            logger.info("Executing CrewAI news crew...")
            result = news_crew.kickoff()
            return str(result)

        except Exception as e:
            logger.error(f"Error in CrewAI MCP news integration: {e}")
            raise

    def run_sharepoint_crew(self, query: str = "Search SharePoint documents") -> str:
        """
        Run a CrewAI crew with MCP SharePoint server tools (MPO SharePoint only)

        Args:
            query: The SharePoint-related query to process

        Returns:
            The crew's response
        """
        global _mpo_sharepoint_server_adapter

        if not self.mpo_sharepoint_server_path.exists():
            raise FileNotFoundError(
                f"MPO SharePoint server not found at {self.mpo_sharepoint_server_path}"
            )

        if _mpo_sharepoint_server_adapter is None:
            raise RuntimeError(
                "MPO SharePoint server adapter not initialized. Call initialize_mcp_adapters() first."
            )

        logger.info(f"Starting CrewAI MCP SharePoint integration for query: {query}")
        logger.info(f"Using MPO SharePoint server: {self.mpo_sharepoint_server_path}")

        try:
            # Use the pre-initialized MPO SharePoint server adapter (already contains tools from __enter__())
            mcp_tools = _mpo_sharepoint_server_adapter
            logger.info(
                f"Available MCP SharePoint tools: {[tool.name for tool in mcp_tools]}"
            )

            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Create SharePoint specialist agent with MCP tools
            sharepoint_agent = Agent(
                role="SharePoint Document Specialist",
                goal="Find and retrieve relevant information from SharePoint by analyzing all documents comprehensively using parallel processing for optimal speed and accuracy",
                backstory="I am a SharePoint document specialist who uses advanced parallel processing to analyze entire SharePoint collections efficiently. I use the analyze_all_documents_for_content tool which traverses every folder, downloads all documents, and analyzes their content concurrently using up to 8 parallel threads. This approach bypasses unreliable search APIs and ensures I find all relevant documents quickly - typically in 20-60 seconds even for large collections. I provide focused, intelligent answers based on the most relevant documents I discover.",
                tools=mcp_tools,  # Pass MCP tools to agent
                llm=llm,
                verbose=CREW_VERBOSE,
                max_iter=5,  # Limit iterations to prevent excessive thinking in high-latency environments
            )

            # Create task for SharePoint query
            sharepoint_task = Task(
                description=f"""Process this SharePoint-related query: {query}
                
Available tools:
- analyze_all_documents_for_content: PRIMARY TOOL - Analyzes all documents using parallel processing
- get_all_documents_comprehensive: Get all documents by traversing every folder (used internally by analyze tool)
- get_sharepoint_document_content: Retrieve individual document content (used internally)
- check_sharepoint_permissions: Test connection and permissions (for debugging only)
                
PRIMARY STRATEGY:
Use analyze_all_documents_for_content with the user's search terms. This tool:
- Traverses every SharePoint folder to find all documents
- Analyzes each document's content using parallel processing (8 concurrent threads)
- Uses smart caching to avoid re-downloading documents
- Terminates early when enough high-quality results are found
- Typical performance: 20-60 seconds for large collections
- Returns documents sorted by relevance with content matches

CRITICAL AUTHENTICATION RULE:
If ANY tool returns an error with "authentication_failed": true or "DELEGATED ACCESS MODE" in the message:
- STOP IMMEDIATELY - Do NOT proceed with the task
- Do NOT attempt to retry with made-up tokens
- Do NOT make up or hallucinate answers
- REPORT the authentication failure to the user clearly
- Inform the user that valid authentication credentials are required to access SharePoint
- Do NOT use any information from your training data to answer the question

RESPONSE STRATEGY (only if authentication succeeds):
1. Call analyze_all_documents_for_content with the user's search terms
2. Extract the KEY ANSWER from the most relevant document(s)
3. Provide a CONCISE, DIRECT response to the user's question
4. Include document name and source for credibility
5. Focus on the specific information requested
6. DON'T dump entire document contents in your response
                """,
                expected_output="""Provide a CONCISE, INTELLIGENT answer to the user's specific question based on SharePoint search results.

CRITICAL: If authentication fails, respond ONLY with:
"Unable to access SharePoint documents due to authentication failure. Valid user credentials are required to access SharePoint with delegated permissions. Please ensure you are properly authenticated, or contact your administrator to configure application access mode by setting SHP_USE_DELEGATED_ACCESS=false."

Do NOT make up answers. Do NOT use information from your training data. Do NOT proceed if authentication fails.

RESPONSE RULES (only if authentication succeeds):
- Extract the key answer from the most relevant document
- Provide a direct response to what the user asked for
- Include document name and source for credibility
- Keep your answer focused and concise
- DON'T copy-paste entire document contents
- Focus on the specific information requested

EXAMPLE GOOD RESPONSE (when authentication succeeds):
"Based on the document 'MPO - Transformative strategies.pdf' from the Major Projects Office, Canada's first high-speed railway is projected to span approximately 1,000 km from Toronto to Québec City, reaching speeds of up to 300 km/hour."

AVOID: Dumping entire document contents, being overly verbose, or making up information when authentication fails.""",
                agent=sharepoint_agent,
            )

            # Create and execute crew
            sharepoint_crew = Crew(
                agents=[sharepoint_agent],
                tasks=[sharepoint_task],
                process=Process.sequential,
                verbose=CREW_VERBOSE,
            )

            # Execute the crew
            logger.info("Executing CrewAI SharePoint crew...")
            result = sharepoint_crew.kickoff()
            return str(result)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in CrewAI MCP SharePoint integration: {error_msg}")

            # Provide specific error messages based on the type of failure
            if (
                "Authentication" in error_msg
                or "access token" in error_msg
                or "401" in error_msg
            ):
                return (
                    "SharePoint access failed due to authentication issues. This may be because:\n\n"
                    + "1. You're in a local development environment where OAuth2 proxy is not configured\n"
                    + "2. Your authentication token has expired\n"
                    + "3. You don't have the necessary SharePoint permissions\n\n"
                    + "For local development, SharePoint integration requires deployment to environments with proper OAuth2 configuration (dev/staging/production)."
                )
            elif "No documents found" in error_msg or "no results" in error_msg:
                return "I searched the available SharePoint documents but could not find information related to your query. The documents may not contain this information, or it might be located in a different SharePoint site or folder that I don't have access to."
            else:
                return f"I encountered an issue while searching SharePoint documents: {error_msg}. Please try rephrasing your query or contact support if the problem persists."

            # Don't re-raise in production to avoid exposing internal errors
            # raise

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
        has_time_server = any(
            "time" in name.lower() for name in available_servers.keys()
        )
        has_news_server = any(
            "news" in name.lower() for name in available_servers.keys()
        )
        has_sharepoint_server = any(
            "sharepoint" in name.lower() for name in available_servers.keys()
        )

        try:
            # Run time crew if available
            if has_time_server:
                logger.info("Running time crew for multi-server query")
                try:
                    time_result = self.run_time_crew(query)
                    results.append(f"Time Information:\n{time_result}")
                except Exception as e:
                    logger.error(f"Time crew failed: {e}")
                    results.append(
                        "Time Information: Could not retrieve time information."
                    )

            # Run news crew if available
            if has_news_server:
                logger.info("Running news crew for multi-server query")
                try:
                    news_result = self.run_news_crew(query)
                    results.append(f"News Information:\n{news_result}")
                except Exception as e:
                    logger.error(f"News crew failed: {e}")
                    results.append(
                        "News Information: Could not retrieve news information."
                    )

            # Run SharePoint crew if available
            if has_sharepoint_server:
                logger.info("Running SharePoint crew for multi-server query")
                try:
                    sharepoint_result = self.run_sharepoint_crew(query)
                    results.append(f"SharePoint Information:\n{sharepoint_result}")
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"SharePoint crew failed: {error_msg}")

                    # Provide helpful error message for authentication issues
                    if "Authentication" in error_msg or "access token" in error_msg:
                        results.append(
                            "SharePoint Information: SharePoint access requires proper authentication. "
                            "This feature is available in deployed environments with OAuth2 configuration."
                        )
                    else:
                        results.append(
                            "SharePoint Information: Could not retrieve SharePoint information."
                        )

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
                if any("time" in tool.lower() for tool in selected_tools):
                    available_specialists.append("TIME")
                if any(
                    "news" in tool.lower() or "headline" in tool.lower()
                    for tool in selected_tools
                ):
                    available_specialists.append("NEWS")
                if any(
                    "sharepoint" in tool.lower()
                    or "document" in tool.lower()
                    or "search" in tool.lower()
                    for tool in selected_tools
                ):
                    available_specialists.append("SHAREPOINT")
            else:
                # If no tools selected, all specialists are available
                available_specialists = ["TIME", "NEWS", "SHAREPOINT"]

            logger.info(f"Available specialists: {available_specialists}")

            # FAST PATH: If user explicitly selected tools for a single specialist, skip router overhead
            if len(available_specialists) == 1:
                specialist = available_specialists[0]
                logger.info(
                    f"🚀 FAST PATH: Single specialist detected ({specialist}), skipping router crew overhead"
                )

                if specialist == "TIME":
                    return self.run_time_crew(query)
                elif specialist == "NEWS":
                    return self.run_news_crew(query)
                elif specialist == "SHAREPOINT":
                    return self.run_sharepoint_crew(query)

            logger.info(
                "Using intelligent router (multiple specialists or auto-detect mode)"
            )

            # Create router agent that makes intelligent routing decisions
            router_agent = Agent(
                role="Intelligent Query Router",
                goal="Analyze user queries and make smart routing decisions to appropriate specialists",
                backstory=f"""You are an intelligent query router. Your job is to understand what the user 
                is actually asking for and make routing decisions accordingly. 

                Available specialists:
                - TIME: Handles current time, dates, timezones, scheduling, time-related calculations
                - NEWS: Handles current news, headlines, articles, breaking news, news search
                - SHAREPOINT: Handles SharePoint document search, retrieval, and content access
                
                Available specialists for this query: {", ".join(available_specialists)}
                
                Your job is to analyze the user's intent and decide:
                1. Which specialist(s) can best answer their question
                2. What specific information each specialist should provide
                3. Whether one specialist is sufficient or multiple are needed
                
                Focus on the user's actual intent and information needs, not just keywords.""",
                verbose=CREW_VERBOSE,
                allow_delegation=False,
                llm=llm,
                max_iter=3,  # Limit iterations - routing should be fast and decisive
            )

            # Create routing decision task
            routing_task = Task(
                description=f"""Analyze this user query and make a routing decision: "{query}"

Available specialists: {", ".join(available_specialists)}

Based on what the user is actually asking for, decide:

1. ROUTING DECISION: Which specialist(s) should handle this query?
   - Choose TIME if the user needs: current time, date, timezone info, time calculations, scheduling
   - Choose NEWS if the user needs: current news, headlines, breaking news, articles, news search  
   - Choose SHAREPOINT if the user needs: SharePoint documents, file search, document retrieval, content access
   - Choose multiple specialists if the user needs information from multiple domains
   - Choose the most relevant one if the query could go either way

2. QUERY ADAPTATION: What specific question should each chosen specialist answer?
   - For TIME specialist: Adapt the query to focus on time-related aspects
   - For NEWS specialist: Adapt the query to focus on news-related aspects
   - For SHAREPOINT specialist: Adapt the query to focus on document/content search aspects
   - Make sure each specialist gets a clear, focused query

3. COORDINATION: How should the results be presented?
   - Single specialist: Direct response
   - Multiple specialists: Combined response with clear organization

Think carefully about the user's actual intent and information needs.""",
                expected_output="""Provide your routing decision in this exact format:

ROUTING_DECISION: [TIME|NEWS|SHAREPOINT|TIME+NEWS|TIME+SHAREPOINT|NEWS+SHAREPOINT|TIME+NEWS+SHAREPOINT]
TIME_QUERY: [specific query for time specialist or NONE]
NEWS_QUERY: [specific query for news specialist or NONE]
SHAREPOINT_QUERY: [specific query for sharepoint specialist or NONE]
PRESENTATION: [brief note on how to present results]

Be decisive and specific. Only route to specialists that are actually needed.""",
                agent=router_agent,
            )

            # Execute routing decision
            routing_crew = Crew(
                agents=[router_agent],
                tasks=[routing_task],
                process=Process.sequential,
                verbose=CREW_VERBOSE,
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
            sharepoint_query = None

            for line in routing_str.split("\n"):
                line = line.strip()
                if line.startswith("ROUTING_DECISION:"):
                    routing_decision = line.split(":", 1)[1].strip()
                elif line.startswith("TIME_QUERY:"):
                    time_query_raw = line.split(":", 1)[1].strip()
                    time_query = time_query_raw if time_query_raw != "NONE" else None
                elif line.startswith("NEWS_QUERY:"):
                    news_query_raw = line.split(":", 1)[1].strip()
                    news_query = news_query_raw if news_query_raw != "NONE" else None
                elif line.startswith("SHAREPOINT_QUERY:"):
                    sharepoint_query_raw = line.split(":", 1)[1].strip()
                    sharepoint_query = (
                        sharepoint_query_raw if sharepoint_query_raw != "NONE" else None
                    )

            logger.info(
                f"Parsed routing - decision: {routing_decision}, time_query: {time_query}, news_query: {news_query}, sharepoint_query: {sharepoint_query}"
            )

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
                    responses.append(
                        "Unable to retrieve time information at this moment."
                    )

            # Route to news specialist if needed and available
            if news_query and "NEWS" in available_specialists:
                logger.info(f"Routing to NEWS specialist with query: {news_query}")
                try:
                    news_response = self.run_news_crew(news_query)
                    responses.append(news_response)
                except Exception as e:
                    logger.error(f"Error from NEWS specialist: {e}")
                    responses.append(
                        "Unable to retrieve news information at this moment."
                    )

            # Route to sharepoint specialist if needed and available
            if sharepoint_query and "SHAREPOINT" in available_specialists:
                logger.info(
                    f"Routing to SHAREPOINT specialist with query: {sharepoint_query}"
                )
                try:
                    sharepoint_response = self.run_sharepoint_crew(sharepoint_query)
                    responses.append(sharepoint_response)
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error from SHAREPOINT specialist: {error_msg}")

                    # Provide helpful error message for authentication issues
                    if (
                        "Authentication" in error_msg
                        or "access token" in error_msg
                        or "OAuth" in error_msg
                    ):
                        responses.append(
                            "SharePoint access is currently unavailable due to authentication requirements. "
                            "This feature requires OAuth2 proxy integration which is configured in deployed environments (dev/staging/production). "
                            "For local development, SharePoint functionality is limited."
                        )
                    else:
                        responses.append(
                            "Unable to retrieve SharePoint information at this moment."
                        )

            # If no routing was determined or no responses, use simple fallback
            if not responses:
                logger.info(
                    "No responses from routing decision, using simple fallback..."
                )
                # Default to first available specialist
                if "TIME" in available_specialists:
                    logger.info("Fallback: defaulting to TIME specialist")
                    time_response = self.run_time_crew(query)
                    responses.append(time_response)
                elif "NEWS" in available_specialists:
                    logger.info("Fallback: defaulting to NEWS specialist")
                    news_response = self.run_news_crew(query)
                    responses.append(news_response)
                elif "SHAREPOINT" in available_specialists:
                    logger.info("Fallback: defaulting to SHAREPOINT specialist")
                    sharepoint_response = self.run_sharepoint_crew(query)
                    responses.append(sharepoint_response)

            # Return the response(s)
            if len(responses) == 1:
                logger.info("Returning single specialist response")
                return responses[0]
            elif len(responses) > 1:
                logger.info("Combining multiple specialist responses")
                # Multiple responses - combine them intelligently with proper structure
                # Create a unified response that maintains Open WebUI compatibility
                combined_response = self._combine_specialist_responses(responses, query)
                return combined_response
            else:
                logger.warning("No responses generated")
                return "I apologize, but I was unable to process your request at this time."

        except Exception as e:
            logger.error(f"Error in intelligent routing: {e}")
            # Emergency fallback - route based on selected tools only
            logger.info("Using emergency fallback routing...")

            if selected_tools:
                # Use selected tools to determine routing
                has_time = any("time" in tool.lower() for tool in selected_tools)
                has_news = any(
                    "news" in tool.lower() or "headline" in tool.lower()
                    for tool in selected_tools
                )

                if has_time and not has_news:
                    logger.info("Emergency fallback: TIME only")
                    return self.run_time_crew(query)
                elif has_news and not has_time:
                    logger.info("Emergency fallback: NEWS only")
                    return self.run_news_crew(query)
                elif has_time and has_news:
                    # Both selected - default to time (or could be news, doesn't matter)
                    logger.info("Emergency fallback: TIME (both selected)")
                    return self.run_time_crew(query)
                else:
                    logger.info("Emergency fallback: TIME (default)")
                    return self.run_time_crew(query)
            else:
                # No tools selected - default to time
                logger.info("Emergency fallback: TIME (no tools selected)")
                return self.run_time_crew(query)

    def _combine_specialist_responses(
        self, responses: list, original_query: str
    ) -> str:
        """
        Combine multiple specialist responses in a structured way that maintains
        compatibility with Open WebUI's chat naming and tagging systems.
        """
        logger.info(f"Combining {len(responses)} specialist responses")

        # For now, use a simple structured combination that preserves key information
        # This should work better with Open WebUI's automated analysis systems

        if len(responses) == 1:
            return responses[0]

        # Create a structured combination with clear sections
        combined_parts = []

        for i, response in enumerate(responses):
            # Add each response with minimal formatting
            if i == 0:
                combined_parts.append(response.strip())
            else:
                combined_parts.append(f"\n{response.strip()}")

        # Join with double line breaks for clear separation
        return "\n\n".join(combined_parts)

    def get_available_servers(self) -> dict:
        """Get all available MCP servers dynamically"""
        servers = {}

        # Define known servers (using MPO SharePoint, not generic SharePoint)
        known_servers = {
            "time_server": self.time_server_path,
            "news_server": self.news_server_path,
            "mpo_sharepoint_server": self.mpo_sharepoint_server_path,
        }

        # Add any other fastmcp_*.py servers found in the backend directory
        servers_dir = self.backend_dir / "mcp_backend" / "servers"
        for server_file in servers_dir.glob("fastmcp_*.py"):
            server_name = server_file.stem  # Remove .py extension
            if server_name not in known_servers:
                servers[server_name] = server_file
                logger.info(f"Discovered additional MCP server: {server_name}")

        # Add known servers
        servers.update(known_servers)

        # Filter to only existing servers
        return {name: path for name, path in servers.items() if path.exists()}

    def get_available_tools(self) -> list:
        """Get list of available MCP tools from all initialized adapters"""
        global _time_server_adapter, _news_server_adapter, _mpo_sharepoint_server_adapter

        all_tools = []

        # Only expose the 3 official tools: time, news, and MPO SharePoint
        # The adapters already contain the tools from __enter__()
        adapters = {
            "time_server": _time_server_adapter,
            "news_server": _news_server_adapter,
            "mpo_sharepoint_server": _mpo_sharepoint_server_adapter,
        }

        for server_name, tools in adapters.items():
            if tools is not None:
                try:
                    for tool in tools:
                        all_tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "server": server_name,
                            }
                        )
                    logger.info(f"Found {len(list(tools))} tools from {server_name}")
                except Exception as e:
                    logger.error(f"Error getting tools from {server_name}: {e}")

        return all_tools


# Simple CLI interface for testing
def main():
    """Main function for testing the CrewAI MCP integration"""
    manager = CrewMCPManager()

    # Initialize MCP adapters once
    manager.initialize_mcp_adapters()

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
        if any(tool["server"] == "time_server" for tool in tools):
            print("\n🕐 Testing Time Server:")
            print("Query: 'What's the current time in UTC?'")
            result = manager.run_time_crew("What's the current time in UTC?")
            print("Result:", result[:200] + "..." if len(result) > 200 else result)

        if any(tool["server"] == "news_server" for tool in tools):
            print("\n📰 Testing News Server:")
            print("Query: 'Get the latest news headlines'")
            result = manager.run_news_crew("Get the latest news headlines")
            print("Result:", result[:200] + "..." if len(result) > 200 else result)

        # Test multi-server capability
        if len(available_servers) > 1:
            print("\n🌐 Testing Multi-Server Integration:")
            print("Query: 'Provide current time and latest news summary'")
            result = manager.run_multi_server_crew(
                "Provide current time and latest news summary"
            )
            print(
                "Multi-Server Result:",
                result[:300] + "..." if len(result) > 300 else result,
            )
        else:
            print("\n⚠️  Only one server available. Multi-server test skipped.")

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
