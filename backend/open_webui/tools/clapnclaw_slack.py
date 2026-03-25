"""
ClapNClaw Slack Tool — uses workspace OAuth tokens via ClapNClaw backend proxy.
"""

import logging

from open_webui.clapnclaw.client import clapnclaw_client

log = logging.getLogger(__name__)


class Tools:
    """Slack integration via ClapNClaw OAuth proxy."""

    class Valves:
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def read_messages(
        self,
        channel: str = "",
        query: str = "",
        max_results: int = 20,
        __user__: dict = {},
    ) -> str:
        """
        Read messages from Slack channels.
        :param channel: Channel name to read from (empty = search all).
        :param query: Search query to filter messages.
        :param max_results: Maximum number of messages.
        :return: JSON string with messages.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/slack/messages",
                {"channel": channel, "query": query, "max_results": max_results},
            )
            return str(result)
        except Exception as e:
            log.error(f"read_messages error: {e}")
            return f"Error reading Slack messages: {e}"

    async def send_message(
        self,
        channel: str,
        text: str,
        __user__: dict = {},
    ) -> str:
        """
        Send a message to a Slack channel.
        :param channel: Channel name or ID.
        :param text: Message text.
        :return: Confirmation message.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/slack/messages",
                {"channel": channel, "text": text, "action": "send"},
            )
            return str(result)
        except Exception as e:
            log.error(f"send_message error: {e}")
            return f"Error sending Slack message: {e}"
