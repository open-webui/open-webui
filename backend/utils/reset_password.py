from datetime import datetime, timedelta
from string import Template
from typing import Literal

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel

import config
from apps.web.models.auths import Auths
from apps.web.models.users import Users

from .utils import create_token, decode_token


RESET_PASSWORD_MAIL_TEMPLATE = Template(r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>$webui_name Password Reset</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
  <div style="max-width: 600px; margin: 20px auto; border: 1px solid #ddd; border-radius: 8px; padding: 20px; text-align: center;">
    <h1>$webui_name:</h1>
    <h2>Password Reset Request</h2>
    <p>Hello,</p>
    <p>You recently requested to reset your password for your $webui_name account. To complete the process, please click the button below:</p>
    <a href="$reset_url" class="bg-gray-900 hover:bg-gray-800" style="color: rgb(236, 236, 236); background-color: #171717; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
    <p>If you can't click the button, copy and paste this link into your browser's address bar: $reset_url</p>
    <p>If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
    <div style="font-size: 12px; color: #666;">
      <p>&copy; $current_year $webui_name.</p>
    </div>
  </div>
</body>
</html>
""")


class ResetToken(BaseModel):
    purpose: Literal["password_reset"]
    sub: str
    # This key prevents the token from being used more than once
    key: str


async def send_password_reset_mail(
    *, email: str, frontend_url: str, email_conf: ConnectionConfig
) -> None:
    user = Users.get_user_by_email(email.lower())
    if user is None:
        return

    password_hash = Auths.get_hash_of_password(user.email)
    reset_token = create_token(
        data=ResetToken(
            purpose="password_reset", sub=user.id, key=password_hash
        ).model_dump(),
        expires_delta=timedelta(days=7),
    )

    reset_url = f"{frontend_url}/auth/reset-password?token={reset_token}"
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[user.email],
        body=RESET_PASSWORD_MAIL_TEMPLATE.substitute(
            reset_url=reset_url,
            current_year=datetime.now().year,
            webui_name=config.WEBUI_NAME,
        ),
        subtype=MessageType.html,
    )

    fm = FastMail(email_conf)
    await fm.send_message(message)


def validate_password_reset_token(token: str) -> str:
    reset_token = ResetToken.model_validate(decode_token(token))

    user = Users.get_user_by_id(reset_token.sub)

    if user is None:
        raise ValueError("Invalid user")

    if reset_token.key != Auths.get_hash_of_password(user.email):
        raise ValueError("Invalid token key")

    return user.id
