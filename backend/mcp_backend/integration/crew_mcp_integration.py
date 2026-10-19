#!/usr/bin/env python3
"""
CrewAI MCP Integration for Open WebUI
Simple integration using MCPServerAdapter with stdio transport for FastMCP time server
"""

import os
import re
import sys
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
# Department SharePoint adapters keyed by uppercase dept name (e.g. "MPO", "PMO").
# Populated dynamically at startup from *_sharepoint_server.py scripts.
_sharepoint_adapters: dict = {}
_adapters_initialized = False


def _extract_token_usage(crew_output) -> dict:
    """
    Extract token usage from a CrewAI CrewOutput object.
    Returns a dict with prompt_tokens, completion_tokens, total_tokens.
    Returns empty totals if the information is unavailable.
    """
    try:
        usage = getattr(crew_output, "token_usage", None)
        if usage is not None:
            return {
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            }
    except Exception as exc:
        logger.warning(f"Could not extract token usage from crew output: {exc}")
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


# Azure OpenAI Configuration
class AzureConfig(BaseModel):
    """Azure OpenAI configuration from environment variables"""

    api_key: str = os.getenv("CREWAI_AZURE_OPENAI_API_KEY", "")
    endpoint: str = os.getenv("CREWAI_AZURE_OPENAI_ENDPOINT", "")
    deployment: str = os.getenv("CREWAI_AZURE_OPENAI_DEPLOYMENT_NAME", "")
    api_version: str = os.getenv("CREWAI_AZURE_OPENAI_API_VERSION", "")

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
        # Discover SharePoint server scripts dynamically.
        # Any *_sharepoint_server.py in the servers directory is a department server.
        self._sharepoint_server_paths = self._discover_sharepoint_servers()

        # User token for OBO flow (delegate access)
        self.user_jwt_token = None

    def _discover_sharepoint_servers(self) -> dict:
        """Read SHAREPOINT_DEPARTMENTS env var to determine active departments.

        Returns a dict mapping uppercase department key → Path to the generic
        server script, e.g. {"MPO": Path(".../generic_sharepoint_server_multi_dept.py")}

        ADDING A NEW SHAREPOINT DEPARTMENT — zero code changes required here.
        Add the prefix to the SHAREPOINT_DEPARTMENTS env var (comma-separated)
        and set the {DEPT}_SHP_* environment variables. No application files
        need to be created or modified.
        """
        generic_server_path = (
            self.backend_dir
            / "mcp_backend"
            / "servers"
            / "generic_sharepoint_server_multi_dept.py"
        )
        departments_env = os.getenv("SHAREPOINT_DEPARTMENTS", "")
        result = {}
        for dept in departments_env.split(","):
            dept = dept.strip().upper()
            if dept:
                result[dept] = generic_server_path
                logger.info(f"Configured SharePoint department: {dept}")
        if not result:
            logger.warning(
                "SHAREPOINT_DEPARTMENTS is not set — SharePoint CrewAI crews will be unavailable. "
                "Set SHAREPOINT_DEPARTMENTS=MPO,PMO (comma-separated) to enable SharePoint integration."
            )
        return result

    def set_user_token(self, token: str):
        """Set the user's JWT token for OBO authentication"""
        self.user_jwt_token = token
        logger.info(f"User JWT token set for OBO flow: {bool(token)}")

        # Set as environment variable for SharePoint MCP servers to use
        if token:
            os.environ["USER_JWT_TOKEN"] = token
            logger.info(f"✅ Set USER_JWT_TOKEN in environment (length: {len(token)})")
        elif "USER_JWT_TOKEN" in os.environ:
            del os.environ["USER_JWT_TOKEN"]
            logger.info("🗑️ Cleared USER_JWT_TOKEN from environment")

    def initialize_mcp_adapters(self):
        """Initialize all MCP server adapters once at startup"""
        global _time_server_adapter, _news_server_adapter, _sharepoint_adapters, _adapters_initialized

        if _adapters_initialized:
            logger.info("MCP adapters already initialized, skipping...")
            return

        logger.info("🚀 Initializing MCP server adapters...")

        # Initialize Time Server
        try:
            time_server_params = StdioServerParameters(
                command=sys.executable,
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
                command=sys.executable,
                args=[str(self.news_server_path)],
                env=dict(os.environ),  # Pass environment variables
            )
            adapter = MCPServerAdapter(news_server_params)
            _news_server_adapter = adapter.__enter__()  # Get the tools from __enter__()
            logger.info("✅ News server adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize News server: {e}")
            _news_server_adapter = None

        # Initialize SharePoint servers for all configured departments
        for dept_key, server_path in self._sharepoint_server_paths.items():
            try:
                params = StdioServerParameters(
                    command=sys.executable,
                    args=[str(server_path), dept_key],
                    env={
                        key: value
                        for key, value in os.environ.items()
                        if key.startswith("SHP_") or key.startswith(f"{dept_key}_SHP_")
                    },  # Pass global and department specific environment variables
                )
                adapter = MCPServerAdapter(params)
                _sharepoint_adapters[dept_key] = adapter.__enter__()
                logger.info(f"✅ {dept_key} SharePoint server adapter initialized")
            except Exception as e:
                logger.error(
                    f"❌ Failed to initialize {dept_key} SharePoint server: {e}"
                )
                _sharepoint_adapters[dept_key] = None

        _adapters_initialized = True

        # Report initialization status
        sp_ok = sum(1 for v in _sharepoint_adapters.values() if v is not None)
        initialized_count = (
            sum(
                [
                    _time_server_adapter is not None,
                    _news_server_adapter is not None,
                ]
            )
            + sp_ok
        )
        total = 2 + len(self._sharepoint_server_paths)
        logger.info(
            f"🎉 MCP server initialization complete: {initialized_count}/{total} adapters initialized"
        )

    def cleanup_mcp_adapters(self):
        """Cleanup all MCP server adapters on shutdown"""
        global _time_server_adapter, _news_server_adapter, _sharepoint_adapters, _adapters_initialized

        logger.info("🧹 Cleaning up MCP server adapters...")

        for adapter_name, adapter in [
            ("Time", _time_server_adapter),
            ("News", _news_server_adapter),
        ]:
            if adapter is not None:
                try:
                    adapter.__exit__(None, None, None)
                    logger.info(f"✅ {adapter_name} server adapter cleaned up")
                except Exception as e:
                    logger.error(f"❌ Error cleaning up {adapter_name} adapter: {e}")

        for dept_key, adapter in _sharepoint_adapters.items():
            if adapter is not None:
                try:
                    adapter.__exit__(None, None, None)
                    logger.info(f"✅ {dept_key} SharePoint server adapter cleaned up")
                except Exception as e:
                    logger.error(
                        f"❌ Error cleaning up {dept_key} SharePoint adapter: {e}"
                    )

        _time_server_adapter = None
        _news_server_adapter = None
        _sharepoint_adapters.clear()
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

        logger.info("Starting CrewAI MCP integration (query_len=%d)", len(query))

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

            # Extract token usage from the crew result
            token_usage = _extract_token_usage(result)
            return str(result), token_usage

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

        logger.info("Starting CrewAI MCP news integration (query_len=%d)", len(query))

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

            # Extract token usage from the crew result
            token_usage = _extract_token_usage(result)
            return str(result), token_usage

        except Exception as e:
            logger.error(f"Error in CrewAI MCP news integration: {e}")
            raise

    def run_sharepoint_crew(
        self, department: str, query: str = "Search SharePoint documents"
    ) -> tuple[str, dict[str, int]]:
        """
        Run a CrewAI crew with MCP SharePoint server tools for a given department.

        Args:
            department: Department key, e.g. "MPO" or "PMO".  Case-insensitive.
            query: The SharePoint-related query to process.

        Returns:
            (result_str, token_usage) tuple.
        """
        dept_key = department.upper()
        dept_lower = dept_key.lower()

        server_path = self._sharepoint_server_paths.get(dept_key)
        if not server_path or not server_path.exists():
            raise FileNotFoundError(
                f"{dept_key} SharePoint server not found at {server_path}"
            )

        logger.info(
            "Starting CrewAI MCP SharePoint integration (query_len=%d)", len(query)
        )
        logger.info(f"Using {dept_key} SharePoint server: {server_path}")
        logger.info(
            "🔄 Initializing fresh SharePoint adapter with user token from environment"
        )

        try:
            # Create adapter with current environment (includes USER_JWT_TOKEN set by set_user_token())
            sharepoint_params = StdioServerParameters(
                command=sys.executable,
                args=[str(server_path), dept_key],
                env={
                    key: value
                    for key, value in os.environ.items()
                    if key.startswith("SHP_")
                    or key.startswith(f"{dept_key}_SHP_")
                    or key == "USER_JWT_TOKEN"
                },  # Fresh environment snapshot with USER_JWT_TOKEN
            )

            # Use context manager for automatic cleanup
            adapter = MCPServerAdapter(sharepoint_params)
            mcp_tools = adapter.__enter__()  # Get the tools from adapter

            logger.info(
                f"✅ {dept_key} SharePoint adapter initialized with {len(list(mcp_tools))} tools"
            )
            logger.info(
                f"Available MCP SharePoint tools: {[tool.name for tool in mcp_tools]}"
            )

            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Create SharePoint specialist agent with MCP tools
            sharepoint_agent = Agent(
                role="SharePoint Document Specialist",
                goal="Find and retrieve relevant information from SharePoint using FAST search or list files in specific folders",
                backstory=f"""I am a SharePoint document specialist who uses the Microsoft Graph Search API for lightning-fast document searches and folder listings.

    🚨 CRITICAL RULES:
    1. For LISTING/COUNTING files in a specific folder → Use {dept_lower}_list_folder_contents
    2. For SEARCHING content across documents → Use {dept_lower}_search_documents_fast
    3. If search snippet doesn't have the complete answer, use {dept_lower}_get_document_by_id to get full content
    4. NEVER answer from training data - ONLY from SharePoint results
    5. If no documents found, say so - don't make up answers
    
    RESPONSE FORMAT:
    - Provide ONLY the final answer extracted from SharePoint
    - Do NOT show your reasoning process ("Thought:", "Action:", etc.)
    - Include document name and source when applicable
    - Be direct and concise""",
                tools=mcp_tools,
                llm=llm,
                verbose=CREW_VERBOSE,
                max_iter=5,
                allow_delegation=False,
            )

            # Create SharePoint task with smart routing
            sharepoint_task = Task(
                description=f"""Retrieve information from SharePoint for: {query}

    🔍 STEP 1 - DETERMINE REQUEST TYPE:
    
    A) If asking to LIST/COUNT files in a SPECIFIC FOLDER (keywords: "list", "show files", "count", "how many files", "in the folder", "in folder"):
       → Use {dept_lower}_list_folder_contents
       → Extract folder name from query (e.g., "Canchat Demo", "Documents/Reports")
       → Call: {dept_lower}_list_folder_contents(folder_path="<folder_name>")
       → If successful: Return the list of files found
       → If folder not found: FALLBACK to {dept_lower}_search_documents_fast(query="<folder_name>", limit=10) to find documents
    
    B) If asking for CONTENT/INFORMATION ABOUT something (keywords: "tell me about", "what is", "explain", "information about", "details on"):
       → STEP 1: Use {dept_lower}_search_documents_fast
         • Call: {dept_lower}_search_documents_fast(query="{query}", limit=10)
       
       → STEP 2: Analyze results:
         • If ANY FILES found (is_folder=false): GO TO STEP 3
         • If ONLY folders found (all is_folder=true): GO TO STEP 4
       
       → STEP 3: Process FILES:
         • If file has useful summary: Extract and respond
         • If need full content: Use {dept_lower}_get_document_by_id(web_url=..., item_id=...)
         • DONE - provide answer to user
       
       → STEP 4: MANDATORY REFINED SEARCH (when only folders found):
         • Try search with hyphenated version: {dept_lower}_search_documents_fast(query="Budget-2025", limit=10)
         • If no files, try: {dept_lower}_search_documents_fast(query="Budget 2025 pdf", limit=10)
         • If files found: Use {dept_lower}_get_document_by_id to retrieve content
         • If still no files after 2 refined searches: Tell user no document files found, only folders exist
       
       → NEVER try to retrieve folder content with {dept_lower}_get_document_by_id

    🚨 ABSOLUTE RULES:
    - For "Tell me about X" queries: Prioritize finding DOCUMENT CONTENT, not folder structure
    - Search returns folders + files: Use the FILES first, ignore folders unless no files exist
    - Search returns ONLY folders: Try refined search with specific terms before listing folder contents
    - Only use {dept_lower}_get_document_by_id for actual FILES (is_folder=false)
    - Do NOT retry the same tool with same input more than once
    - Include document names and sources in your final answer
    - If you get an error suggesting to use search, DO IT - don't give up
    - If you receive a permission/access denied error (🔒), STOP and tell the user they don't have access
    - Do NOT say "no information found" when it's actually a permissions issue
    - 404 errors on folders mean you tried to get a folder as a document - use {dept_lower}_list_folder_contents instead
                """,
                expected_output="""A DIRECT, CONCISE answer to the user's question without showing any reasoning process.

    FORMAT REQUIREMENTS:
    - Start immediately with the answer (NO "Thought:", "Action:", or process explanations)
    - Extract the key information from the search results
    - Include document name and source for credibility
    - Keep response focused on what was asked
    - Maximum 2-3 sentences unless more detail is specifically requested

    EXAMPLE RESPONSES:
    - Success: "Canada's new high-speed railway is proposed to span approximately 1,000 km, according to the document '2025-12-05-Alto-Letter to MPO.pdf' from the Major Projects Office."
    - Permission Error: "You do not have permission to access the requested documents. Please contact your SharePoint administrator for access."
    - Not Found: "No documents found matching your query in accessible SharePoint locations."

    AVOID:  
    - Showing reasoning ("Thought:", "I will use tool X")
    - Dumping entire document contents
    - Being overly verbose
    - Including process descriptions
    - Saying "no information found" when it's a permissions issue""",
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
            logger.info(f"Executing CrewAI {dept_key} SharePoint crew...")
            result = sharepoint_crew.kickoff()

            # Cleanup adapter
            try:
                adapter.__exit__(None, None, None)
                logger.info(f"✅ Cleaned up {dept_key} SharePoint adapter")
            except Exception as e:
                logger.warning(f"Failed to cleanup adapter: {e}")

            token_usage = _extract_token_usage(result)
            return str(result), token_usage

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Error in CrewAI MCP {dept_key} SharePoint integration: {error_msg}"
            )

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
                    + "For local development, SharePoint integration requires deployment to environments with proper OAuth2 configuration (dev/staging/production).",
                    {},
                )
            elif "No documents found" in error_msg or "no results" in error_msg:
                return (
                    "I searched the available SharePoint documents but could not find information related to your query. The documents may not contain this information, or it might be located in a different location.",
                    {},
                )
            else:
                return (
                    f"I encountered an issue while searching SharePoint documents: {error_msg}. Please try rephrasing your query or contact support if the problem persists.",
                    {},
                )

    def run_intelligent_crew(self, query: str, selected_tools: list = None) -> tuple:
        """
        Route a query to the appropriate specialist crew based on selected_tools.

        Args:
            query: The query to process.
            selected_tools: List of tool IDs selected by the user (optional).

        Returns:
            A 3-tuple of (result_str, token_usage_dict, mcp_process_name).
        """
        logger.info("Starting intelligent router (query_len=%d)", len(query))
        logger.info(f"Selected tools: {selected_tools}")

        try:
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
                # Detect any department SharePoint server dynamically.
                # Tool IDs follow the pattern "mcp_{dept}_sharepoint_server_*".
                for tool in selected_tools:
                    m = re.match(r"mcp_([a-z0-9]+)_sharepoint_server", tool.lower())
                    if m:
                        dept = m.group(1).upper()
                        specialist_key = f"{dept}_SHAREPOINT"
                        if specialist_key not in available_specialists:
                            available_specialists.append(specialist_key)
            else:
                # If no tools selected, only non-SharePoint specialists are available by default
                available_specialists = ["TIME", "NEWS"]

            logger.info(f"Available specialists: {available_specialists}")

            # FAST PATH: If user explicitly selected tools for a single specialist,
            # skip router overhead and go straight to the specialist crew.
            if len(available_specialists) == 1:
                specialist = available_specialists[0]
                logger.info(
                    f"🚀 FAST PATH: Single specialist detected ({specialist}), skipping router crew overhead"
                )

                if specialist == "TIME":
                    result_str, token_usage = self.run_time_crew(query)
                    return result_str, token_usage, "time_server"
                elif specialist == "NEWS":
                    result_str, token_usage = self.run_news_crew(query)
                    return result_str, token_usage, "news_server"
                elif specialist.endswith("_SHAREPOINT"):
                    dept = specialist[: -len("_SHAREPOINT")]
                    result_str, token_usage = self.run_sharepoint_crew(dept, query)
                    return result_str, token_usage, f"{dept.lower()}_sharepoint_server"

            # Multiple specialists - simple priority routing
            logger.info("Multiple specialists available - using simple routing")

            if "TIME" in available_specialists:
                result_str, token_usage = self.run_time_crew(query)
                return result_str, token_usage, "time_server"
            elif "NEWS" in available_specialists:
                result_str, token_usage = self.run_news_crew(query)
                return result_str, token_usage, "news_server"
            else:
                # Route to the first available SharePoint specialist
                for specialist in available_specialists:
                    if specialist.endswith("_SHAREPOINT"):
                        dept = specialist[: -len("_SHAREPOINT")]
                        result_str, token_usage = self.run_sharepoint_crew(dept, query)
                        return (
                            result_str,
                            token_usage,
                            f"{dept.lower()}_sharepoint_server",
                        )

            return (
                "I apologize, but I was unable to process your request at this time.",
                {},
                None,
            )

        except Exception as e:
            logger.error(f"Error in intelligent routing: {e}")
            # Emergency fallback - route based on selected tools only
            logger.info("Using emergency fallback routing...")

            if selected_tools:
                has_time = any("time" in tool.lower() for tool in selected_tools)
                has_news = any(
                    "news" in tool.lower() or "headline" in tool.lower()
                    for tool in selected_tools
                )

                if has_time:
                    logger.info("Emergency fallback: TIME")
                    result_str, token_usage = self.run_time_crew(query)
                    return result_str, token_usage, "time_server"
                elif has_news:
                    logger.info("Emergency fallback: NEWS")
                    result_str, token_usage = self.run_news_crew(query)
                    return result_str, token_usage, "news_server"
                else:
                    # Try SharePoint fallback
                    for tool in selected_tools:
                        m = re.match(r"mcp_([a-z0-9]+)_sharepoint_server", tool.lower())
                        if m:
                            dept = m.group(1).upper()
                            logger.info(f"Emergency fallback: {dept} SHAREPOINT")
                            result_str, token_usage = self.run_sharepoint_crew(
                                dept, query
                            )
                            return (
                                result_str,
                                token_usage,
                                f"{dept.lower()}_sharepoint_server",
                            )

            logger.info("Emergency fallback: TIME (default)")
            result_str, token_usage = self.run_time_crew(query)
            return result_str, token_usage, "time_server"

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

        # Add any other fastmcp_*.py servers discovered in the servers directory
        servers_dir = self.backend_dir / "mcp_backend" / "servers"
        for server_file in servers_dir.glob("fastmcp_*.py"):
            server_name = server_file.stem
            servers[server_name] = server_file
            logger.info(f"Discovered additional MCP server: {server_name}")

        # Fixed known servers
        known_servers = {
            "time_server": self.time_server_path,
            "news_server": self.news_server_path,
        }
        # Dynamically discovered SharePoint servers
        for dept_key, path in self._sharepoint_server_paths.items():
            known_servers[f"{dept_key.lower()}_sharepoint_server"] = path

        servers.update(known_servers)

        # Filter to only existing servers
        return {name: path for name, path in servers.items() if path.exists()}

    def get_available_tools(self) -> list:
        """Get list of available MCP tools from all initialized adapters"""
        global _time_server_adapter, _news_server_adapter, _sharepoint_adapters

        all_tools = []

        adapters = {
            "time_server": _time_server_adapter,
            "news_server": _news_server_adapter,
        }
        for dept_key, adapter in _sharepoint_adapters.items():
            adapters[f"{dept_key.lower()}_sharepoint_server"] = adapter

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

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
