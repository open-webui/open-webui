import smtplib
import ssl
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import secrets
import time
from pathlib import Path
from fastapi.templating import Jinja2Templates

from open_webui.config import PersistentConfig

log = logging.getLogger(__name__)

SMTP_SERVER = PersistentConfig(
    "SMTP_SERVER",
    "email.smtp.server",
    os.environ.get("SMTP_SERVER", "localhost"),
)

SMTP_PORT = PersistentConfig(
    "SMTP_PORT",
    "email.smtp.port",
    int(os.environ.get("SMTP_PORT", "587")),
)

SMTP_USERNAME = PersistentConfig(
    "SMTP_USERNAME",
    "email.smtp.username",
    os.environ.get("SMTP_USERNAME", "noreply@localhost"),
)

SMTP_PASSWORD = PersistentConfig(
    "SMTP_PASSWORD",
    "email.smtp.password",
    os.environ.get("SMTP_PASSWORD", ""),
)

SMTP_USE_TLS = PersistentConfig(
    "SMTP_USE_TLS",
    "email.smtp.use_tls",
    os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
)

# Get the directory where this file is located
CURRENT_DIR = Path(__file__).parent
TEMPLATES_DIR = str(CURRENT_DIR.parent / "templates")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def render_email_template(template_name: str, **kwargs) -> str:
    """Render an email template using FastAPI's Jinja2Templates."""
    try:
        # Render the template with the provided context
        template_path = f"email/{template_name}.html"
        rendered_template = templates.get_template(template_path).render(**kwargs)
        return rendered_template
    except Exception as e:
        log.error(f"Error rendering email template {template_name}: {str(e)}")
        return ""


def generate_numeric_token() -> str:
    return f"{secrets.randbelow(900000) + 100000:06d}"


def generate_token_expiry(minutes: int = 10) -> int:
    return int(time.time()) + (minutes * 60)


def send_email(
    to_email: str, subject: str, body: str, html_body: Optional[str] = None
) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USERNAME.value
        msg["To"] = to_email

        text_part = MIMEText(body, "plain")
        msg.attach(text_part)

        if html_body:
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

        context = ssl.create_default_context()

        with smtplib.SMTP(SMTP_SERVER.value, SMTP_PORT.value) as server:
            if SMTP_USE_TLS.value:
                server.starttls(context=context)

            if SMTP_USERNAME.value and SMTP_PASSWORD.value:
                server.login(SMTP_USERNAME.value, SMTP_PASSWORD.value)

            server.sendmail(SMTP_USERNAME.value, to_email, msg.as_string())

        log.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        log.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def send_verification_email(to_email: str) -> tuple[bool, str]:
    # Generate a 6-digit verification code
    verification_code = generate_numeric_token()

    subject = "Verify your email address"

    html_body = render_email_template(
        "verification", verification_code=verification_code
    )

    success = send_email(to_email, subject, "", html_body)
    return success, verification_code


def send_password_reset_email(to_email: str) -> tuple[bool, str]:
    # Generate a 6-digit reset code
    reset_code = generate_numeric_token()

    subject = "Reset your password"

    html_body = render_email_template("password_reset", reset_code=reset_code)

    success = send_email(to_email, subject, "", html_body)
    return success, reset_code


def is_token_expired(expires_at: int) -> bool:
    return int(time.time()) > expires_at
