import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Iterable

from open_webui.config import (
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_SENDER_NAME,
    SMTP_USERNAME,
    WEBUI_NAME,
    WEBUI_URL,
)

log = logging.getLogger(__name__)


def is_email_configured() -> bool:
    return all(
        [
            SMTP_SERVER.value,
            SMTP_USERNAME.value,
            SMTP_PASSWORD.value,
        ]
    )


def _build_message(subject: str, body: str, to_addrs: Iterable[str]) -> tuple[str, str]:
    sender_name = SMTP_SENDER_NAME.value or WEBUI_NAME.value or "Open WebUI"
    from_addr = SMTP_USERNAME.value

    message = MIMEText(body, "plain", "utf-8")
    message["From"] = formataddr((sender_name, from_addr))
    message["To"] = ", ".join(to_addrs)
    message["Subject"] = subject

    return message.as_string(), from_addr


async def send_email(subject: str, body: str, to_addrs: list[str]) -> None:
    if not is_email_configured():
        log.warning("SMTP configuration incomplete; skipping email sending.")
        return

    message, from_addr = _build_message(subject, body, to_addrs)

    def _send():
        with smtplib.SMTP(SMTP_SERVER.value, int(SMTP_PORT.value)) as server:
            server.starttls()
            server.login(SMTP_USERNAME.value, SMTP_PASSWORD.value)
            server.sendmail(from_addr, to_addrs, message)

    try:
        await asyncio.to_thread(_send)
    except Exception as exc:
        log.exception("Failed to send email notification: %s", exc)


async def send_channel_message_email(recipient, sender, channel, message) -> None:
    if not recipient.email:
        return

    sender_name = sender.name if sender else "Someone"
    channel_name = channel.name if channel else "channel"
    preview = (message.content or "").strip()
    if len(preview) > 500:
        preview = f"{preview[:497]}..."

    webui_url = WEBUI_URL.value or ""
    link = f"{webui_url.rstrip('/')}/channels/{channel.id}" if channel else webui_url

    subject = f"[{WEBUI_NAME.value or 'Open WebUI'}] New message in #{channel_name}"
    body = (
        f"Hi {recipient.name},\n\n"
        f"{sender_name} posted a new message in #{channel_name}:\n\n"
        f"{preview or '(No text provided)'}\n\n"
        f"View the conversation: {link}\n\n"
        f"--\n{WEBUI_NAME.value or 'Open WebUI'}"
    )

    await send_email(subject, body, [recipient.email])
