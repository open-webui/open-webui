import asyncio
import logging
import smtplib
from email.message import EmailMessage

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def send_email(config, to_address: str, subject: str, body: str) -> bool:
    delivery_mode = (config.EMAIL_DELIVERY_MODE or "log").lower()
    if delivery_mode == "mailtrap":
        delivery_mode = "smtp"

    if delivery_mode == "log":
        log.info(
            "Email delivery mode=log to=%s subject=%s body=%s",
            to_address,
            subject,
            body,
        )
        return True

    if delivery_mode != "smtp":
        log.error("Unsupported EMAIL_DELIVERY_MODE: %s", delivery_mode)
        return False

    if not config.EMAIL_HOST or not config.EMAIL_PORT or not config.EMAIL_FROM:
        log.error("SMTP configuration incomplete; cannot send email.")
        return False

    message = EmailMessage()
    message["From"] = config.EMAIL_FROM
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    def _send():
        if config.EMAIL_USE_SSL:
            server = smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT, timeout=10)
        else:
            server = smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT, timeout=10)
        try:
            if not config.EMAIL_USE_SSL and config.EMAIL_USE_TLS:
                server.starttls()
            if config.EMAIL_USER or config.EMAIL_PASSWORD:
                server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
            server.send_message(message)
        finally:
            server.quit()

    try:
        await asyncio.to_thread(_send)
        return True
    except Exception as exc:
        log.error("Failed to send email via SMTP: %s", exc)
        return False
