"""
ClapNClaw Google Drive Tool — uses workspace OAuth tokens via ClapNClaw backend proxy.
"""

import logging

from open_webui.clapnclaw.client import clapnclaw_client

log = logging.getLogger(__name__)


class Tools:
    """Google Drive integration via ClapNClaw OAuth proxy."""

    class Valves:
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def search_files(
        self,
        query: str,
        max_results: int = 10,
        __user__: dict = {},
    ) -> str:
        """
        Search files in Google Drive.
        :param query: Search query string.
        :param max_results: Maximum number of results.
        :return: JSON string with file metadata.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/drive/search",
                {"query": query, "max_results": max_results},
            )
            return str(result)
        except Exception as e:
            log.error(f"search_files error: {e}")
            return f"Error searching Drive: {e}"

    async def get_content(
        self,
        file_id: str,
        __user__: dict = {},
    ) -> str:
        """
        Get the text content of a Google Drive file.
        :param file_id: The Google Drive file ID.
        :return: File content as text.
        """
        try:
            result = await clapnclaw_client.get(f"/api/tools/drive/content/{file_id}")
            return str(result)
        except Exception as e:
            log.error(f"get_content error: {e}")
            return f"Error getting file content: {e}"
