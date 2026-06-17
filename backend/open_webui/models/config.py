"""Database-backed configuration with per-key storage.

Replaces the old single-row JSON blob machinery with a simple per-key model
mirroring cptr's Config.

Each config key is stored as its own row: key TEXT PK, value JSON.
Reads are direct DB lookups. Writes are explicit awaited upserts that raise on
failure (no more fire-and-forget create_task).
"""

from __future__ import annotations

import logging
import time
from typing import Any, ClassVar

from open_webui.internal.db import Base, get_async_db
from sqlalchemy import JSON, BigInteger, Column, Text, select

log = logging.getLogger(__name__)


# ── Model ────────────────────────────────────────────────────────────────────


class Config(Base):
    """Per-key config storage. Each row is one config key."""

    __tablename__ = 'config'

    key = Column(Text, primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(BigInteger, nullable=True)

    DEFAULTS: ClassVar[dict[str, Any]] = {}
    PERSISTENT_ENABLED: ClassVar[bool] = True
    OAUTH_PERSISTENT_ENABLED: ClassVar[bool] = False

    # ── Class methods ────────────────────────────────────────

    @classmethod
    def configure(
        cls,
        *,
        defaults: dict[str, Any] | None = None,
        enable_persistent: bool = True,
        enable_oauth_persistent: bool = False,
    ) -> None:
        cls.DEFAULTS = defaults or {}
        cls.PERSISTENT_ENABLED = enable_persistent
        cls.OAUTH_PERSISTENT_ENABLED = enable_oauth_persistent

    @classmethod
    def default_value(cls, key: str, default: Any = None) -> Any:
        return cls.DEFAULTS.get(key, default)

    @classmethod
    def persistent_enabled_for(cls, key: str) -> bool:
        if not cls.PERSISTENT_ENABLED:
            return False
        if key.startswith('oauth.') and not cls.OAUTH_PERSISTENT_ENABLED:
            return False
        return True

    @staticmethod
    async def get(key: str, default: Any = None) -> Any:
        """Get a config value by key. Returns default if not set."""
        if not Config.persistent_enabled_for(key):
            return Config.default_value(key, default)
        async with get_async_db() as db:
            row = await db.get(Config, key)
            return row.value if row else Config.default_value(key, default)

    @staticmethod
    async def get_many(*keys: str) -> dict:
        """Get multiple config values. Returns {key: value} for keys that exist."""
        disabled_values = {
            key: Config.default_value(key)
            for key in keys
            if not Config.persistent_enabled_for(key) and key in Config.DEFAULTS
        }
        enabled_keys = {key for key in keys if Config.persistent_enabled_for(key)}
        if not enabled_keys:
            return disabled_values
        async with get_async_db() as db:
            result = await db.execute(select(Config).where(Config.key.in_(enabled_keys)))
            values = {row.key: row.value for row in result.scalars().all()}
            return {
                key: values.get(key, Config.default_value(key))
                for key in keys
                if key in values or key in Config.DEFAULTS or key in disabled_values
            }

    @staticmethod
    async def get_namespace(namespace: str) -> dict:
        """Get all config keys under a dotted namespace."""
        default_values = {
            key: value
            for key, value in Config.DEFAULTS.items()
            if key.startswith(f'{namespace}.') and not Config.persistent_enabled_for(key)
        }
        if not Config.PERSISTENT_ENABLED:
            return default_values
        async with get_async_db() as db:
            result = await db.execute(select(Config).where(Config.key.like(f'{namespace}.%')))
            values = {row.key: row.value for row in result.scalars().all()}
            values.update(default_values)
            return values

    @staticmethod
    async def get_all() -> dict:
        """Get all config as {key: value}."""
        if not Config.PERSISTENT_ENABLED:
            return dict(Config.DEFAULTS)
        async with get_async_db() as db:
            result = await db.execute(select(Config))
            values = {row.key: row.value for row in result.scalars().all()}
            if not Config.OAUTH_PERSISTENT_ENABLED:
                values.update({key: value for key, value in Config.DEFAULTS.items() if key.startswith('oauth.')})
            return values

    @staticmethod
    async def upsert(updates: dict) -> None:
        """Upsert multiple config key-value pairs. Raises on failure."""
        async with get_async_db() as db:
            now = int(time.time())
            for key, value in updates.items():
                existing = await db.get(Config, key)
                if existing:
                    existing.value = value
                    existing.updated_at = now
                else:
                    db.add(Config(key=key, value=value, updated_at=now))
            await db.commit()

    @staticmethod
    async def delete(key: str) -> bool:
        """Delete a config key. Returns True if it existed."""
        async with get_async_db() as db:
            row = await db.get(Config, key)
            if row:
                await db.delete(row)
                await db.commit()
                return True
            return False

    @staticmethod
    async def clear() -> None:
        """Delete all config rows."""
        from sqlalchemy import delete as sa_delete

        async with get_async_db() as db:
            await db.execute(sa_delete(Config))
            await db.commit()

    @staticmethod
    async def seed_defaults(defaults: dict) -> None:
        """Insert keys that don't yet exist in the DB.

        Called at startup to ensure all known config keys have values.
        Existing DB values take precedence over defaults.
        """
        async with get_async_db() as db:
            result = await db.execute(select(Config.key))
            existing_keys = {row[0] for row in result.all()}

            now = int(time.time())
            new_count = 0
            for key, value in defaults.items():
                if key not in existing_keys:
                    db.add(Config(key=key, value=value, updated_at=now))
                    existing_keys.add(key)
                    new_count += 1

            if new_count:
                await db.commit()
                log.info('Seeded %d new config defaults', new_count)
