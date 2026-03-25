"""
ClapNClaw Web Search Tool — proxy web search through ClapNClaw backend.
"""

import logging

from open_webui.clapnclaw.client import clapnclaw_client

log = logging.getLogger(__name__)


class Tools:
    """Web search via ClapNClaw proxy."""

    class Valves:
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        __user__: dict = {},
    ) -> str:
        """
        Search the web for information.
        :param query: Search query.
        :param max_results: Maximum number of results.
        :return: JSON string with search results.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/web/search",
                {"query": query, "max_results": max_results},
            )
            return str(result)
        except Exception as e:
            log.error(f"search_web error: {e}")
            return f"Error searching web: {e}"
