"""Renewable human sessions. Pending browser logins become the same session row."""

import time
from uuid import uuid4

from open_webui.internal.db import Base, get_async_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Index, Text, delete, select, update


class AuthSession(Base):
    __tablename__ = 'auth_session'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=True)
    refresh_token_id = Column(Text, nullable=True)
    data = Column(JSON, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    expires_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('idx_auth_session_user', 'user_id'),
        Index('idx_auth_session_expires', 'expires_at'),
    )


class AuthSessionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    refresh_token_id: str | None = None
    data: dict
    created_at: int
    updated_at: int
    expires_at: int


class AuthSessionsTable:
    async def get(self, session_id: str) -> AuthSessionModel | None:
        async with get_async_db() as db:
            row = await db.get(AuthSession, session_id)
            return AuthSessionModel.model_validate(row) if row else None

    async def create(self, **values) -> AuthSessionModel:
        now = int(time.time())
        row = AuthSession(id=str(uuid4()), created_at=now, updated_at=now, **values)
        async with get_async_db() as db:
            await db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
            db.add(row)
            await db.flush()
            result = AuthSessionModel.model_validate(row)
            await db.commit()
            return result

    async def change(self, session_id: str, conditions: list, **values) -> bool:
        async with get_async_db() as db:
            result = await db.execute(
                update(AuthSession)
                .where(AuthSession.id == session_id, *conditions)
                .values(updated_at=int(time.time()), **values)
                .execution_options(synchronize_session=False)
            )
            await db.commit()
            return result.rowcount == 1

    async def revoke(self, session_id: str, user_id: str) -> bool:
        async with get_async_db() as db:
            result = await db.execute(
                delete(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == user_id)
            )
            await db.commit()
            return result.rowcount == 1

    async def list(self, user_id: str) -> list[dict]:
        async with get_async_db() as db:
            rows = (
                await db.execute(
                    select(AuthSession)
                    .where(
                        AuthSession.user_id == user_id,
                        AuthSession.refresh_token_id.is_not(None),
                        AuthSession.expires_at > int(time.time()),
                    )
                    .order_by(AuthSession.created_at.desc())
                )
            ).scalars()
            return [
                {
                    **{key: getattr(row, key) for key in ('id', 'created_at', 'updated_at', 'expires_at')},
                    'name': row.data['name'],
                }
                for row in rows
            ]


AuthSessions = AuthSessionsTable()
