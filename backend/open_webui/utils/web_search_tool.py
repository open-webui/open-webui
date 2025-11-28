"""
Built-in Web Search Tools for Open WebUI
Provides web search and fetch capabilities as native tools that models can call directly.
Uses Exa API for both search and content fetching.
"""

import logging
from typing import Optional, List
from pydantic import BaseModel
from fastapi import Request

from open_webui.retrieval.web.exa import search_exa, fetch_exa_contents

log = logging.getLogger(__name__)


class WebSearchTools:
    """
    Built-in tools that provide web search and content fetching functionality.
    
    Provides two tools:
    1. web_search - Search the web for information, returns URLs with snippets
    2. web_fetch - Fetch full content from specific URLs
    
    Configuration is managed through the admin panel web search settings.
    """

    class Valves(BaseModel):
        """Configuration placeholder - settings are managed via admin panel"""
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def web_search(
        self,
        query: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search the web for information about a query.

        This tool searches the web using Exa and returns relevant results including
        titles, URLs, and content snippets. Use this to find relevant pages, then
        use web_fetch to get full content from the most relevant URLs.

        Args:
            query: The search query to execute. Should be clear and specific.

        Returns:
            Formatted search results containing:
            - List of results with titles, URLs, and snippets
            - Use the URLs with web_fetch to get full content
        """
        log.info(f"WEB SEARCH: query='{query}'")

        if not __request__:
            log.error("WEB SEARCH: Request context not available")
            return "Error: Request context not available"

        try:
            config = __request__.app.state.config
            
            if not config.EXA_API_KEY:
                return "Error: Exa API key not configured. Please set it in Admin Settings > Web Search."

            # Get search settings from config
            num_results = getattr(config, 'EXA_SEARCH_NUM_RESULTS', 10)
            search_type = getattr(config, 'EXA_SEARCH_TYPE', 'auto')
            include_domains = getattr(config, 'EXA_INCLUDE_DOMAINS', [])
            exclude_domains = getattr(config, 'EXA_EXCLUDE_DOMAINS', [])

            # Perform the search
            results = search_exa(
                api_key=config.EXA_API_KEY,
                query=query,
                num_results=num_results,
                search_type=search_type,
                include_domains=include_domains if include_domains else None,
                exclude_domains=exclude_domains if exclude_domains else None,
            )

            if not results:
                return f"No results found for query: '{query}'"

            # Format results for the model
            formatted_results = [
                f"## Search Results for: {query}\n",
                f"Found {len(results)} results.\n\n",
            ]

            for idx, result in enumerate(results, 1):
                formatted_results.append(f"### Result {idx}\n")
                if result.title:
                    formatted_results.append(f"**Title:** {result.title}\n")
                formatted_results.append(f"**URL:** {result.link}\n")
                if result.snippet:
                    formatted_results.append(f"**Snippet:** {result.snippet}\n")
                formatted_results.append("\n")

            formatted_results.append("\n---\n")
            formatted_results.append("*Use web_fetch with specific URLs to get full page content.*\n")

            return "".join(formatted_results)

        except Exception as e:
            log.error(f"Web search error: {e}", exc_info=True)
            return f"Error performing web search: {str(e)}"

    async def web_fetch(
        self,
        urls: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Fetch the full content from one or more URLs.

        This tool retrieves the full text content from web pages. Use this after
        web_search to get detailed information from specific pages.

        Args:
            urls: One or more URLs to fetch, separated by commas or newlines.
                  Example: "https://example.com/page1, https://example.com/page2"

        Returns:
            Full text content from each URL, formatted for easy reading.
        """
        log.info(f"WEB FETCH: urls='{urls}'")

        if not __request__:
            log.error("WEB FETCH: Request context not available")
            return "Error: Request context not available"

        try:
            config = __request__.app.state.config
            
            if not config.EXA_API_KEY:
                return "Error: Exa API key not configured. Please set it in Admin Settings > Web Search."

            # Parse URLs from the input string
            url_list = self._parse_urls(urls)
            
            if not url_list:
                return "Error: No valid URLs provided. Please provide URLs separated by commas or newlines."

            # Limit to reasonable number of URLs
            max_urls = 5
            if len(url_list) > max_urls:
                log.warning(f"WEB FETCH: Limiting from {len(url_list)} to {max_urls} URLs")
                url_list = url_list[:max_urls]

            # Get fetch settings from config
            max_characters = getattr(config, 'EXA_CONTENTS_MAX_CHARACTERS', 10000)
            livecrawl = getattr(config, 'EXA_CONTENTS_LIVECRAWL', 'fallback')

            # Fetch content
            results = fetch_exa_contents(
                api_key=config.EXA_API_KEY,
                urls=url_list,
                max_characters=max_characters,
                livecrawl=livecrawl,
            )

            if not results:
                return f"Could not fetch content from the provided URLs."

            # Format results for the model
            formatted_results = [
                f"## Fetched Content\n",
                f"Retrieved content from {len(results)} URL(s).\n\n",
            ]

            for idx, result in enumerate(results, 1):
                formatted_results.append(f"### Page {idx}: {result.title or 'Untitled'}\n")
                formatted_results.append(f"**URL:** {result.url}\n")
                if result.published_date:
                    formatted_results.append(f"**Published:** {result.published_date}\n")
                if result.author:
                    formatted_results.append(f"**Author:** {result.author}\n")
                formatted_results.append(f"\n**Content:**\n\n{result.text}\n")
                formatted_results.append("\n---\n\n")

            return "".join(formatted_results)

        except Exception as e:
            log.error(f"Web fetch error: {e}", exc_info=True)
            return f"Error fetching content: {str(e)}"

    def _parse_urls(self, urls_input: str) -> List[str]:
        """Parse URLs from a string that may contain commas, newlines, or spaces."""
        # Replace common separators with a standard delimiter
        normalized = urls_input.replace('\n', ',').replace('\r', ',').replace(' ', ',')
        
        # Split and filter
        url_list = []
        for url in normalized.split(','):
            url = url.strip()
            if url and (url.startswith('http://') or url.startswith('https://')):
                url_list.append(url)
        
        return url_list


# Singleton instance
_web_search_tools_instance = None


def get_web_search_tools_instance():
    """Get or create the singleton WebSearchTools instance"""
    global _web_search_tools_instance
    if _web_search_tools_instance is None:
        _web_search_tools_instance = WebSearchTools()
    return _web_search_tools_instance
