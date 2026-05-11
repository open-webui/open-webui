"""
Gmail Send API Utility

Sends emails via Gmail API using OAuth tokens.
Uses the same OAuth infrastructure as Gmail sync.
"""

import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import aiohttp
import markdown
import re

logger = logging.getLogger(__name__)


# Email HTML template with styling for rich text rendering
EMAIL_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Trebuchet MS', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{ color: #1a1a1a; border-bottom: 2px solid #4f46e5; padding-bottom: 10px; }}
        h2 {{ color: #374151; margin-top: 24px; }}
        h3 {{ color: #4b5563; }}
        p {{ margin: 12px 0; }}
        ul, ol {{ margin: 12px 0; padding-left: 24px; }}
        li {{ margin: 6px 0; }}
        hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 24px 0; }}
        code {{
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.9em;
        }}
        pre {{
            background: #1f2937;
            color: #f9fafb;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            padding: 0;
            color: inherit;
        }}
        blockquote {{
            border-left: 4px solid #4f46e5;
            margin: 16px 0;
            padding: 12px 20px;
            background: #f9fafb;
        }}
        strong {{ color: #111827; }}
        .emoji {{ font-size: 1.2em; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }}
        th, td {{
            border: 1px solid #e5e7eb;
            padding: 10px;
            text-align: left;
        }}
        th {{ background: #f9fafb; font-weight: 600; }}
    </style>
</head>
<body>
{content}
</body>
</html>
"""


def markdown_to_html(md_content: str) -> str:
    """Convert markdown to styled HTML for email."""
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'nl2br'])
    html_content = md.convert(md_content)

    # Wrap in email template
    return EMAIL_HTML_TEMPLATE.format(content=html_content)


def strip_markdown(md_content: str) -> str:
    """Convert markdown to plain text for email fallback."""
    # Remove common markdown formatting
    text = md_content
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # Headers
    text = re.sub(r'`([^`]+)`', r'\1', text)  # Inline code
    text = re.sub(r'```[\s\S]*?```', '', text)  # Code blocks
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links
    return text


class GmailSender:
    """
    Sends emails via Gmail API.

    Uses OAuth token from user's Google login session.
    """

    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"

    def __init__(self, access_token: str, timeout: int = 30):
        """
        Initialize Gmail sender.

        Args:
            access_token: OAuth access token with gmail.send scope
            timeout: Request timeout in seconds
        """
        self.access_token = access_token
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        is_markdown: bool = False,
    ) -> dict:
        """
        Create a message for the Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or markdown)
            from_email: Sender email (optional, uses authenticated user)
            is_markdown: If True, convert markdown to HTML

        Returns:
            Gmail API message resource
        """
        if is_markdown:
            # Convert markdown to HTML and create multipart email
            html_body = markdown_to_html(body)
            plain_body = strip_markdown(body)

            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(plain_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
        else:
            msg = MIMEText(body, "plain")

        msg["to"] = to
        msg["subject"] = subject
        if from_email:
            msg["from"] = from_email

        # Encode to base64url format required by Gmail API
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        return {"raw": raw}

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        is_markdown: bool = True,
    ) -> dict:
        """
        Send an email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (markdown by default)
            is_markdown: If True (default), convert markdown to HTML

        Returns:
            Gmail API response with message ID

        Raises:
            Exception: If sending fails
        """
        url = f"{self.GMAIL_API_BASE}/users/me/messages/send"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        message = self._create_message(to, subject, body, is_markdown=is_markdown)

        try:
            session = await self._get_session()
            async with session.post(url, json=message, headers=headers) as resp:
                if resp.status == 401:
                    raise Exception("OAuth token expired or invalid")
                if resp.status == 403:
                    raise Exception("Gmail send permission not granted. User may need to re-authenticate.")
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Gmail send failed: {resp.status} - {error_text}")
                    raise Exception(f"Gmail API error: {resp.status}")

                result = await resp.json()
                logger.info(f"✅ Email sent successfully. Message ID: {result.get('id')}")
                return result

        except aiohttp.ClientError as e:
            logger.error(f"Network error sending email: {e}")
            raise Exception(f"Network error: {e}")
        finally:
            await self.close()


async def create_gmail_sender_for_user(
    oauth_manager,
    user_id: str,
) -> Optional[GmailSender]:
    """
    Create a Gmail sender for a user using their OAuth session.

    Args:
        oauth_manager: Open WebUI's OAuthManager instance
        user_id: User ID

    Returns:
        GmailSender or None if no valid session
    """
    from open_webui.models.oauth_sessions import OAuthSessions

    # Get Google OAuth session
    oauth_session = OAuthSessions.get_session_by_provider_and_user_id("google", user_id)
    if not oauth_session:
        logger.warning(f"No Google OAuth session for user {user_id}")
        return None

    # Get token (auto-refreshes if needed)
    try:
        token = await oauth_manager.get_oauth_token(
            user_id=user_id,
            session_id=oauth_session.id,
        )
    except Exception as e:
        logger.error(f"Failed to get OAuth token for user {user_id}: {e}")
        return None

    if not token or not token.get("access_token"):
        logger.warning(f"Invalid OAuth token for user {user_id}")
        return None

    # Check for Gmail send scope
    scope = token.get("scope", "")
    if "gmail.send" not in scope.lower():
        logger.warning(f"User {user_id} OAuth token missing gmail.send scope")
        return None

    return GmailSender(access_token=token.get("access_token"))
