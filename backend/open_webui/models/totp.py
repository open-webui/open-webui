from __future__ import annotations

import time

from open_webui.internal.db import Base, get_async_db_context
from open_webui.utils.totp import verify_backup_code
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, JSON, String, Text, delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class UserTOTP(Base):
    __tablename__ = 'user_totp'

    user_id = Column(String, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True, unique=True)
    secret = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=False)
    backup_codes = Column(JSON, nullable=True)
    last_used_at = Column(BigInteger, nullable=True)
    last_used_step = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class UserTOTPModel(BaseModel):
    user_id: str
    secret: str | None = None
    enabled: bool = False
    backup_codes: list[str] | None = None
    last_used_at: int | None = None
    last_used_step: int | None = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class UserTOTPsTable:
    async def get_user_totp_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> UserTOTPModel | None:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(UserTOTP).filter_by(user_id=user_id))
                user_totp = result.scalars().first()
                return UserTOTPModel.model_validate(user_totp) if user_totp else None
        except Exception:
            return None

    async def is_totp_enabled_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        user_totp = await self.get_user_totp_by_user_id(user_id, db=db)
        return bool(user_totp and user_totp.enabled and user_totp.secret)

    async def save_pending_secret_by_user_id(
        self, user_id: str, encrypted_secret: str, db: AsyncSession | None = None
    ) -> UserTOTPModel | None:
        try:
            async with get_async_db_context(db) as db:
                now = int(time.time())
                result = await db.execute(select(UserTOTP).filter_by(user_id=user_id))
                user_totp = result.scalars().first()

                if user_totp:
                    user_totp.secret = encrypted_secret
                    user_totp.enabled = False
                    user_totp.backup_codes = []
                    user_totp.last_used_step = None
                    user_totp.updated_at = now
                else:
                    user_totp = UserTOTP(
                        user_id=user_id,
                        secret=encrypted_secret,
                        enabled=False,
                        backup_codes=[],
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(user_totp)

                await db.commit()
                await db.refresh(user_totp)
                return UserTOTPModel.model_validate(user_totp)
        except Exception:
            return None

    async def enable_totp_by_user_id(
        self,
        user_id: str,
        backup_codes: list[str],
        last_used_step: int,
        db: AsyncSession | None = None,
    ) -> UserTOTPModel | None:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(UserTOTP).filter_by(user_id=user_id))
                user_totp = result.scalars().first()
                if not user_totp or not user_totp.secret:
                    return None

                now = int(time.time())
                user_totp.enabled = True
                user_totp.backup_codes = backup_codes
                user_totp.last_used_at = now
                user_totp.last_used_step = last_used_step
                user_totp.updated_at = now

                await db.commit()
                await db.refresh(user_totp)
                return UserTOTPModel.model_validate(user_totp)
        except Exception:
            return None

    async def disable_totp_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(UserTOTP).filter_by(user_id=user_id))
                user_totp = result.scalars().first()
                if not user_totp:
                    return True

                now = int(time.time())
                user_totp.secret = None
                user_totp.enabled = False
                user_totp.backup_codes = []
                user_totp.last_used_step = None
                user_totp.updated_at = now

                await db.commit()
                return True
        except Exception:
            return False

    async def delete_totp_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(UserTOTP).filter_by(user_id=user_id))
                await db.commit()
                return True
        except Exception:
            return False

    async def mark_totp_used_by_user_id(
        self, user_id: str, last_used_step: int, db: AsyncSession | None = None
    ) -> bool:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(UserTOTP).filter_by(user_id=user_id))
                user_totp = result.scalars().first()
                if not user_totp:
                    return False

                now = int(time.time())
                user_totp.last_used_at = now
                user_totp.last_used_step = last_used_step
                user_totp.updated_at = now

                await db.commit()
                return True
        except Exception:
            return False

    async def replace_backup_codes_by_user_id(
        self, user_id: str, backup_codes: list[str], db: AsyncSession | None = None
    ) -> UserTOTPModel | None:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(UserTOTP).filter_by(user_id=user_id))
                user_totp = result.scalars().first()
                if not user_totp or not user_totp.enabled:
                    return None

                now = int(time.time())
                user_totp.backup_codes = backup_codes
                user_totp.updated_at = now

                await db.commit()
                await db.refresh(user_totp)
                return UserTOTPModel.model_validate(user_totp)
        except Exception:
            return None

    async def consume_backup_code_by_user_id(
        self, user_id: str, backup_code: str, db: AsyncSession | None = None
    ) -> bool:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(UserTOTP).filter_by(user_id=user_id))
                user_totp = result.scalars().first()
                if not user_totp or not user_totp.enabled:
                    return False

                backup_codes = list(user_totp.backup_codes or [])
                for index, hashed_code in enumerate(backup_codes):
                    if verify_backup_code(backup_code, hashed_code):
                        remaining = backup_codes[:index] + backup_codes[index + 1 :]
                        now = int(time.time())
                        user_totp.backup_codes = remaining
                        user_totp.last_used_at = now
                        user_totp.updated_at = now
                        await db.commit()
                        return True

                return False
        except Exception:
            return False


UserTOTPs = UserTOTPsTable()
