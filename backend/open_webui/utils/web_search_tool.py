"""
Built-in Web Search Tool for Open WebUI
Provides web search capability as a native tool that models can call directly
"""

import logging
import aiohttp
import asyncio
import re
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import Request

from open_webui.routers.retrieval import search_web
from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)


def extract_title(text: str) -> Optional[str]:
    """
    Extracts the title from Jina Reader response.

    :param text: The input string containing the title.
    :return: The extracted title string, or None if the title is not found.
    """
    match = re.search(r'Title: (.*)\n', text)
    return match.group(1).strip() if match else None


def clean_urls(text: str) -> str:
    """
    Cleans URLs from a string containing structured text.

    :param text: The input string containing the URLs.
    :return: The cleaned string with URLs removed.
    """
    return re.sub(r'\((http[^)]+)\)', '', text)


class WebSearchTool:
    """
    Built-in tool that provides web search functionality to language models.
    This tool allows models to search the web and receive structured results
    that they can use to provide informed responses.
    """

    class Valves(BaseModel):
        """Configuration options for the web search tool"""
        JINA_API_KEY: str = Field(
            default="",
            description="(Optional) Jina API key. Allows higher rate limit when fetching full content."
        )
        DISABLE_JINA_CACHING: bool = Field(
            default=False,
            description="Bypass Jina cache when scraping content"
        )
        CLEAN_CONTENT: bool = Field(
            default=True,
            description="Remove links and image URLs from scraped content to reduce tokens"
        )
        FETCH_FULL_CONTENT: bool = Field(
            default=True,
            description="Fetch full content from URLs using Jina Reader (disable to only return snippets)"
        )
        MAX_CONCURRENT_REQUESTS: int = Field(
            default=5,
            description="Maximum number of concurrent Jina Reader requests"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def _fetch_jina_content(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[str]:
        """
        Fetch full content from a URL using Jina Reader.

        Args:
            session: aiohttp ClientSession for making requests
            url: The URL to fetch content from

        Returns:
            The full content as markdown, or None if fetching failed
        """
        try:
            jina_url = f"https://r.jina.ai/{url}"
            headers = {
                "X-No-Cache": "true" if self.valves.DISABLE_JINA_CACHING else "false",
                "X-With-Generated-Alt": "true",
            }

            if self.valves.JINA_API_KEY:
                headers["Authorization"] = f"Bearer {self.valves.JINA_API_KEY}"

            async with session.get(jina_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                content = await response.text()

                # Clean URLs if configured
                if self.valves.CLEAN_CONTENT:
                    content = clean_urls(content)

                return content

        except Exception as e:
            log.warning(f"Failed to fetch content from {url} via Jina Reader: {e}")
            return None

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
            # Get the configured search engine from app config
            engine = __request__.app.state.config.WEB_SEARCH_ENGINE

            # Perform the search using existing search_web function
            results: list[SearchResult] = search_web(__request__, engine, query)

            if not results:
                return f"No results found for query: '{query}'"

            # Fetch full content concurrently if enabled
            full_contents = {}
            if self.valves.FETCH_FULL_CONTENT:
                log.info(f"🔍 WEB SEARCH TOOL: Fetching full content from {len(results)} URLs via Jina Reader")

                async with aiohttp.ClientSession() as session:
                    # Create semaphore to limit concurrent requests
                    semaphore = asyncio.Semaphore(self.valves.MAX_CONCURRENT_REQUESTS)

                    async def fetch_with_semaphore(url: str):
                        async with semaphore:
                            return url, await self._fetch_jina_content(session, url)

                    # Fetch all URLs concurrently
                    tasks = [fetch_with_semaphore(result.link) for result in results]
                    fetch_results = await asyncio.gather(*tasks)

                    # Store results in dict
                    full_contents = {url: content for url, content in fetch_results if content}

                log.info(f"🔍 WEB SEARCH TOOL: Successfully fetched content from {len(full_contents)}/{len(results)} URLs")

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
                    # Extract title from Jina content if available
                    jina_title = extract_title(content)
                    if jina_title:
                        formatted_results.append(f"**Extracted Title**: {jina_title}\n")
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
