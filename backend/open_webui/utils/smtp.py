import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from open_webui.config import SMTP_USERNAME, SMTP_HOST, SMTP_PORT, SMTP_PASSWORD


def send_email(receiver: str, subject: str, body: str):
    message = MIMEMultipart()
    message["From"] = SMTP_USERNAME.value
    message["To"] = receiver
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    if SMTP_PORT.value == "587":
        server = smtplib.SMTP(SMTP_HOST.value, int(SMTP_PORT.value))
        server.starttls()
    elif SMTP_PORT.value == "465":
        server = smtplib.SMTP_SSL(SMTP_HOST.value, int(SMTP_PORT.value))
    else:
        raise ValueError(f"Invalid SMTP port {SMTP_PORT.value}")

    try:
        server.login(SMTP_USERNAME.value, SMTP_PASSWORD.value)
        server.send_message(message)
    finally:
        server.quit()
