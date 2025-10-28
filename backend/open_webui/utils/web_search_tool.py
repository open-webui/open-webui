"""
Built-in Web Search Tool for Open WebUI
Provides web search capability as a native tool that models can call directly
"""

import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import Request

from open_webui.routers.retrieval import search_web
from open_webui.retrieval.web.main import SearchResult
from open_webui.retrieval.web.utils import get_web_loader

log = logging.getLogger(__name__)


class WebSearchTool:
    """
    Built-in tool that provides web search functionality to language models.
    This tool allows models to search the web and receive structured results
    that they can use to provide informed responses.

    Configuration is managed through the admin panel web search settings.
    Uses the configured WEB_LOADER_ENGINE to fetch full content from URLs.
    """

    class Valves(BaseModel):
        """Configuration placeholder - settings are managed via admin panel"""
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def search_web(
        self,
        query: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search the web for information about a query.

        This tool searches the configured web search engine and returns relevant
        results including titles, URLs, and content snippets. The model can call
        this tool multiple times with different or refined queries if needed.

        Args:
            query: The search query to execute. Should be clear and specific.

        Returns:
            Formatted search results as a string containing:
            - Search query used
            - List of results with titles, URLs, and content snippets
            - Number of results found

        Example:
            To search for Python tutorials:
            query = "Python programming tutorials for beginners"
        """
        log.info(f"🔍 WEB SEARCH TOOL: Called with query='{query}'")
        log.info(f"🔍 WEB SEARCH TOOL: __request__ is {'present' if __request__ else 'None'}")
        log.info(f"🔍 WEB SEARCH TOOL: __user__ is {'present' if __user__ else 'None'}")

        if not __request__:
            log.error("🔍 WEB SEARCH TOOL: ERROR - Request context not available")
            return "Error: Request context not available"

        try:
            # Get configuration from app state
            config = __request__.app.state.config
            engine = config.WEB_SEARCH_ENGINE

            # Perform the search using existing search_web function
            results: list[SearchResult] = search_web(__request__, engine, query)

            if not results:
                return f"No results found for query: '{query}'"

            # Fetch full content using configured web loader if bypass is disabled
            full_contents = {}
            if not config.BYPASS_WEB_SEARCH_WEB_LOADER:
                try:
                    log.info(f"🔍 WEB SEARCH TOOL: Fetching full content from {len(results)} URLs using {config.WEB_LOADER_ENGINE} loader")

                    # Get URLs from search results
                    urls = [result.link for result in results]

                    # Use configured web loader to fetch content
                    web_loader = get_web_loader(
                        urls=urls,
                        verify_ssl=config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
                        requests_per_second=config.WEB_LOADER_CONCURRENT_REQUESTS,
                        trust_env=config.WEB_SEARCH_TRUST_ENV,
                    )

                    # Load documents
                    documents = list(web_loader.lazy_load())

                    # Map URLs to content
                    full_contents = {doc.metadata.get("source"): doc.page_content for doc in documents}

                    log.info(f"🔍 WEB SEARCH TOOL: Successfully fetched content from {len(full_contents)}/{len(results)} URLs")
                except Exception as e:
                    log.error(f"🔍 WEB SEARCH TOOL: Error fetching content: {e}", exc_info=True)

            # Format results for the model
            formatted_results = [
                f"**Search Query**: {query}\n",
                f"**Results Found**: {len(results)}\n",
                "\n---\n\n"
            ]

            for idx, result in enumerate(results, 1):
                formatted_results.append(f"**Result {idx}**\n")
                if result.title:
                    formatted_results.append(f"**Title**: {result.title}\n")
                formatted_results.append(f"**URL**: {result.link}\n")
                if result.snippet:
                    formatted_results.append(f"**Snippet**: {result.snippet}\n")

                # Add full content if available
                if result.link in full_contents:
                    content = full_contents[result.link]
                    formatted_results.append(f"\n**Full Content**:\n\n{content}\n")

                formatted_results.append("\n---\n\n")

            return "".join(formatted_results)

        except Exception as e:
            log.error(f"Web search error: {e}", exc_info=True)
            return f"Error performing web search: {str(e)}"


# Singleton instance
_web_search_tool_instance = None


def get_web_search_tool_instance():
    """Get or create the singleton WebSearchTool instance"""
    global _web_search_tool_instance
    if _web_search_tool_instance is None:
        _web_search_tool_instance = WebSearchTool()
    return _web_search_tool_instance
