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
from sqlalchemy import JSON, BigInteger, Column, Text, delete, select

log = logging.getLogger(__name__)

API_CONFIG_KEYS = ('openai.api_configs', 'ollama.api_configs')
DICT_CONFIG_KEY_ALIASES = {
    'openai.api_configs': ('OPENAI_API_CONFIGS',),
    'ollama.api_configs': ('OLLAMA_API_CONFIGS',),
    'rag.mineru_params': ('MINERU_PARAMS',),
    'rag.docling_params': ('DOCLING_PARAMS',),
    'web.search.linkup_search_params': ('LINKUP_SEARCH_PARAMS',),
    'image_generation.automatic1111.api_params': ('AUTOMATIC1111_PARAMS',),
    'image_generation.openai.params': ('IMAGES_OPENAI_API_PARAMS',),
    'audio.tts.openai.params': ('AUDIO_TTS_OPENAI_PARAMS',),
    'models.default_metadata': ('DEFAULT_MODEL_METADATA',),
    'models.default_params': ('DEFAULT_MODEL_PARAMS',),
    'user.permissions': ('USER_PERMISSIONS',),
}
DICT_CONFIG_KEYS = tuple(DICT_CONFIG_KEY_ALIASES)
API_CONFIG_FIELDS = (
    'enable',
    'key',
    'prefix_id',
    'tags',
    'model_ids',
    'connection_type',
    'provider',
    'auth_type',
    'headers',
    'azure',
    'api_version',
    'extra_params',
)


def _split_api_config_fragment(fragment: str) -> tuple[str, list[str]] | None:
    if not fragment:
        return None

    first, _, rest = fragment.partition('.')
    if first.isdigit() and rest:
        return first, rest.split('.')

    match: tuple[int, str] | None = None
    for field in API_CONFIG_FIELDS:
        marker = f'.{field}'
        marker_index = fragment.rfind(marker)
        if marker_index != -1 and (match is None or marker_index > match[0]):
            match = (marker_index, field)

    if match:
        marker_index, field = match
        connection_key = fragment[:marker_index]
        field_path = fragment[marker_index + 1 :]
        if connection_key:
            return connection_key, field_path.split('.')

    return None


def _assign_path(target: dict, path: list[str], value: Any) -> None:
    current = target
    for part in path[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[path[-1]] = value


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
        async with get_async_db() as db:
            await db.execute(delete(Config))
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

    @staticmethod
    async def rename_prefix(old_prefix: str, new_prefix: str) -> None:
        """Move persisted config keys from one dotted prefix to another."""
        if not Config.PERSISTENT_ENABLED:
            return

        async with get_async_db() as db:
            result = await db.execute(select(Config).where(Config.key.like(f'{old_prefix}.%')))
            rows = result.scalars().all()
            if not rows:
                return

            now = int(time.time())
            moved_count = 0
            deleted_count = 0
            for row in rows:
                new_key = f'{new_prefix}.{row.key.removeprefix(f"{old_prefix}.")}'
                existing = await db.get(Config, new_key)
                if existing is None:
                    db.add(Config(key=new_key, value=row.value, updated_at=now))
                    moved_count += 1
                else:
                    deleted_count += 1
                await db.delete(row)

            await db.commit()
            log.info(
                'Renamed %d config keys from %s.* to %s.*; deleted %d old duplicates',
                moved_count,
                old_prefix,
                new_prefix,
                deleted_count,
            )

    @staticmethod
    async def repair_flattened_dict_configs() -> None:
        """Reassemble dict config values flattened by the per-key migration."""
        if not Config.PERSISTENT_ENABLED:
            return

        async with get_async_db() as db:
            repaired_keys: list[str] = []
            orphan_keys: list[str] = []

            for config_key, aliases in DICT_CONFIG_KEY_ALIASES.items():
                prefixes = (config_key, *aliases)
                rows = []
                for key_prefix in prefixes:
                    result = await db.execute(select(Config).where(Config.key.like(f'{key_prefix}.%')))
                    rows.extend(result.scalars().all())
                if not rows:
                    continue

                existing = await db.get(Config, config_key)
                repaired = existing.value if existing and isinstance(existing.value, dict) else {}

                repaired_any = False
                for row in rows:
                    fragment = None
                    for key_prefix in prefixes:
                        prefix = f'{key_prefix}.'
                        if row.key.startswith(prefix):
                            fragment = row.key.removeprefix(prefix)
                            break
                    if fragment is None:
                        continue

                    if config_key in API_CONFIG_KEYS:
                        split = _split_api_config_fragment(fragment)
                        if not split:
                            continue
                        object_key, field_path = split
                    else:
                        object_key, field_path = None, fragment.split('.')

                    target = repaired
                    if object_key is not None:
                        target = repaired.setdefault(object_key, {})
                        if not isinstance(target, dict):
                            continue

                    _assign_path(target, field_path, row.value)
                    orphan_keys.append(row.key)
                    repaired_any = True

                if not repaired_any:
                    continue

                if existing:
                    existing.value = repaired
                    existing.updated_at = int(time.time())
                else:
                    db.add(Config(key=config_key, value=repaired, updated_at=int(time.time())))
                repaired_keys.append(config_key)

            if orphan_keys:
                await db.execute(delete(Config).where(Config.key.in_(orphan_keys)))

            if repaired_keys or orphan_keys:
                await db.commit()
                log.info('Repaired flattened dict config rows for %s', ', '.join(repaired_keys))
