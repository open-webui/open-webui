import json
import logging
import smtplib
import time
import secrets
from typing import Optional
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


def send_email(
    *,
    subject: str,
    body: str,
    to_email: str,
    smtp_server: str,
    smtp_port: int,
    smtp_username: str = "",
    smtp_password: str = "",
    from_email: str,
):
    """发送纯文本邮件；默认使用 SMTPS (SSL) 直连端口，如 465"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10) as server:
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        server.sendmail(from_email, [to_email], msg.as_string())


def generate_verification_code(length: int = 6) -> str:
    alphabet = "0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class EmailVerificationManager:
    """Stores and validates email verification codes using Redis if available."""

    def __init__(self, redis=None, prefix: str = "signup:code"):
        self.redis = redis
        self.prefix = prefix
        self.memory_store: dict[str, dict] = {}

    def _now(self) -> int:
        return int(time.time())

    def _key(self, email: str) -> str:
        return f"{self.prefix}:{email.lower()}"

    def _delete(self, email: str):
        key = self._key(email)
        if self.redis:
            self.redis.delete(key)
        else:
            self.memory_store.pop(key, None)

    def _load_record(self, email: str) -> Optional[dict]:
        key = self._key(email)
        record = None
        if self.redis:
            raw = self.redis.get(key)
            if raw:
                try:
                    record = json.loads(raw)
                except Exception:
                    log.debug("Failed to decode email verification record for %s", email)
        else:
            record = self.memory_store.get(key)

        if not record:
            return None

        expires_at = record.get("expires_at")
        if expires_at and expires_at <= self._now():
            self._delete(email)
            return None

        return record

    def _save_record(self, email: str, record: dict, ttl: int):
        key = self._key(email)
        ttl = max(ttl, 1)
        if self.redis:
            self.redis.set(key, json.dumps(record), ex=ttl)
        else:
            self.memory_store[key] = record

    def can_send(self, email: str, send_interval: int) -> tuple[bool, int]:
        record = self._load_record(email)
        if not record:
            return True, 0

        sent_at = record.get("sent_at")
        if sent_at:
            delta = self._now() - sent_at
            remaining = send_interval - delta
            if remaining > 0:
                return False, remaining

        return True, 0

    def store_code(
        self,
        email: str,
        code: str,
        ttl: int,
        max_attempts: int,
        ip: Optional[str] = None,
    ):
        now = self._now()
        record = {
            "code": code,
            "expires_at": now + ttl,
            "attempts_left": max_attempts,
            "sent_at": now,
            **({"ip": ip} if ip else {}),
        }
        self._save_record(email, record, ttl)

    def validate_code(self, email: str, code: str) -> bool:
        record = self._load_record(email)
        if not record:
            return False

        ttl_left = max(record.get("expires_at", 0) - self._now(), 0)

        if record.get("code") != code:
            attempts_left = record.get("attempts_left", 1) - 1
            if attempts_left <= 0:
                self._delete(email)
            else:
                record["attempts_left"] = attempts_left
                self._save_record(email, record, ttl_left)
            return False

        self._delete(email)
        return True
