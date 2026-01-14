import hashlib
import hmac
import logging
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text, Index

from open_webui.env import SRC_LOG_LEVELS, WEBUI_SECRET_KEY
from open_webui.internal.db import Base, get_db

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class Email2FAChallenge(Base):
    __tablename__ = "email_2fa_challenge"

    id = Column(String(length=36), primary_key=True)
    user_id = Column(String(length=255), nullable=False)
    code_hash = Column(String(length=128), nullable=False)
    expires_at = Column(BigInteger, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    used = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_email_2fa_user_id", "user_id"),
        Index("idx_email_2fa_expires_at", "expires_at"),
    )


class Email2FAChallengeModel(BaseModel):
    id: str
    user_id: str
    expires_at: int
    created_at: int
    attempts: int
    max_attempts: int
    used: bool

    model_config = ConfigDict(from_attributes=True)


class Email2FAResult(BaseModel):
    user_id: Optional[str] = None
    error: Optional[str] = None
    expires_at: Optional[int] = None
    attempts_left: Optional[int] = None


class Email2FATable:
    def __init__(self):
        if not WEBUI_SECRET_KEY:
            raise Exception("WEBUI_SECRET_KEY is not set")
        self._secret = WEBUI_SECRET_KEY

    def _hash_code(self, code: str) -> str:
        payload = f"{code}:{self._secret}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def create_challenge(
        self, user_id: str, code: str, ttl_seconds: int, max_attempts: int
    ) -> Optional[Email2FAChallengeModel]:
        try:
            with get_db() as db:
                now = int(time.time())
                expires_at = now + ttl_seconds
                challenge_id = str(uuid.uuid4())

                db.query(Email2FAChallenge).filter_by(
                    user_id=user_id, used=False
                ).update({"used": True})

                result = Email2FAChallenge(
                    **{
                        "id": challenge_id,
                        "user_id": user_id,
                        "code_hash": self._hash_code(code),
                        "expires_at": expires_at,
                        "created_at": now,
                        "attempts": 0,
                        "max_attempts": max_attempts,
                        "used": False,
                    }
                )
                db.add(result)
                db.commit()
                db.refresh(result)
                return Email2FAChallengeModel.model_validate(result)
        except Exception as exc:
            log.error("Failed to create email 2FA challenge: %s", exc)
            return None

    def get_active_challenge(self, challenge_id: str) -> Optional[Email2FAChallenge]:
        try:
            with get_db() as db:
                return (
                    db.query(Email2FAChallenge)
                    .filter_by(id=challenge_id, used=False)
                    .first()
                )
        except Exception as exc:
            log.error("Failed to fetch email 2FA challenge: %s", exc)
            return None

    def verify_challenge(self, challenge_id: str, code: str) -> Email2FAResult:
        try:
            with get_db() as db:
                challenge = (
                    db.query(Email2FAChallenge)
                    .filter_by(id=challenge_id)
                    .with_for_update()
                    .first()
                )
                if not challenge or challenge.used:
                    return Email2FAResult(error="invalid")

                now = int(time.time())
                if now > challenge.expires_at:
                    challenge.used = True
                    db.commit()
                    return Email2FAResult(error="expired")

                if challenge.attempts >= challenge.max_attempts:
                    challenge.used = True
                    db.commit()
                    return Email2FAResult(error="max_attempts")

                expected = self._hash_code(code)
                if hmac.compare_digest(expected, challenge.code_hash):
                    challenge.used = True
                    db.commit()
                    return Email2FAResult(user_id=challenge.user_id)

                challenge.attempts += 1
                db.commit()
                attempts_left = max(challenge.max_attempts - challenge.attempts, 0)
                return Email2FAResult(
                    error="invalid", attempts_left=attempts_left, expires_at=challenge.expires_at
                )
        except Exception as exc:
            log.error("Failed to verify email 2FA challenge: %s", exc)
            return Email2FAResult(error="invalid")


Email2FA = Email2FATable()
