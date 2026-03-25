"""
ClapNClaw Gmail Tool — uses workspace OAuth tokens via ClapNClaw backend proxy.
"""

import logging

from open_webui.clapnclaw.client import clapnclaw_client

log = logging.getLogger(__name__)


class Tools:
    """Gmail integration via ClapNClaw OAuth proxy."""

    class Valves:
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def get_emails(
        self,
        query: str = "is:unread",
        max_results: int = 10,
        __user__: dict = {},
    ) -> str:
        """
        Search Gmail emails using the workspace's connected Google account.
        :param query: Gmail search query (e.g. 'is:unread', 'from:boss@company.com').
        :param max_results: Maximum number of emails to return.
        :return: JSON string with email summaries.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/gmail/search",
                {"query": query, "max_results": max_results},
            )
            return str(result)
        except Exception as e:
            log.error(f"get_emails error: {e}")
            return f"Error fetching emails: {e}"

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        __user__: dict = {},
    ) -> str:
        """
        Send an email using the workspace's connected Gmail account.
        :param to: Recipient email address.
        :param subject: Email subject.
        :param body: Email body (plain text).
        :return: Confirmation message.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/gmail/send",
                {"to": to, "subject": subject, "body": body},
            )
            return str(result)
        except Exception as e:
            log.error(f"send_email error: {e}")
            return f"Error sending email: {e}"

    async def draft_reply(
        self,
        message_id: str,
        body: str,
        __user__: dict = {},
    ) -> str:
        """
        Create a draft reply to an email.
        :param message_id: The ID of the email to reply to.
        :param body: The reply body text.
        :return: Confirmation with draft ID.
        """
        try:
            result = await clapnclaw_client.post(
                "/api/tools/gmail/send",
                {"reply_to": message_id, "body": body, "draft": True},
            )
            return str(result)
        except Exception as e:
            log.error(f"draft_reply error: {e}")
            return f"Error creating draft: {e}"
