"""
ClapNClaw Google Calendar Tool — uses workspace OAuth tokens via ClapNClaw backend proxy.
"""

import logging

from open_webui.clapnclaw.client import clapnclaw_client

log = logging.getLogger(__name__)


class Tools:
    """Google Calendar integration via ClapNClaw OAuth proxy."""

    class Valves:
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def get_events(
        self,
        days: int = 1,
        __user__: dict = {},
    ) -> str:
        """
        Get upcoming calendar events.
        :param days: Number of days ahead to look (default 1 = today).
        :return: JSON string with calendar events.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/calendar/events",
                {"days": days, "action": "list"},
            )
            return str(result)
        except Exception as e:
            log.error(f"get_events error: {e}")
            return f"Error fetching calendar events: {e}"

    async def create_event(
        self,
        title: str,
        start: str,
        end: str,
        description: str = "",
        __user__: dict = {},
    ) -> str:
        """
        Create a new calendar event.
        :param title: Event title.
        :param start: Start time in ISO 8601 format.
        :param end: End time in ISO 8601 format.
        :param description: Optional event description.
        :return: Confirmation with event link.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/calendar/events",
                {
                    "action": "create",
                    "title": title,
                    "start": start,
                    "end": end,
                    "description": description,
                },
            )
            return str(result)
        except Exception as e:
            log.error(f"create_event error: {e}")
            return f"Error creating event: {e}"
