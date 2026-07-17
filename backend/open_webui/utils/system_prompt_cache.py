"""In-process LRU+TTL cache for resolved Langfuse system prompts.

When Redis is configured at runtime, entries are also stored in Redis so
multi-worker deployments share warm cache.  In-process LRU is always used as
the fast L1 layer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Any

from open_webui.env import REDIS_KEY_PREFIX
from open_webui.utils.redis import get_redis_client

log = logging.getLogger(__name__)

DEFAULT_MAX_SIZE = 256
CACHE_WARM_CLOCK_SKEW_SECONDS = 5
DEFAULT_FETCH_FAILURE_BACKOFF_SECONDS = 60

_REDIS_KEY_PREFIX = f'{REDIS_KEY_PREFIX}:system_prompt_cache'


@dataclass(frozen=True)
class CachedSystemPrompt:
    content: str
    cached_at: float
    ttl_seconds: int
    prompt_name: str | None = None
    prompt_version: str | None = None


@dataclass(frozen=True)
class StaleServePolicy:
    """How to behave when Langfuse fetch fails or is temporarily unavailable."""

    failure_backoff_seconds: int = DEFAULT_FETCH_FAILURE_BACKOFF_SECONDS

    def effective_ttl_on_failure(self, binding_ttl: int) -> int:
        """Extend effective TTL so stale content stays warm during backoff."""
        return max(binding_ttl, self.failure_backoff_seconds)


STALE_SERVE_POLICY = StaleServePolicy()


def binding_cache_ttl_seconds(binding, default_ttl: int) -> int:
    if binding.cache_ttl_seconds is not None:
        return binding.cache_ttl_seconds
    return default_ttl


def is_binding_db_cache_warm(binding, *, default_ttl: int) -> bool:
    """Return True when binding DB cache fields hold a non-expired prompt."""
    if not binding.cached_content:
        return False
    if binding.cached_at is None:
        return False

    ttl = binding_cache_ttl_seconds(binding, default_ttl)
    if ttl <= 0:
        return False

    age_seconds = time.time() - binding.cached_at
    return (age_seconds + CACHE_WARM_CLOCK_SKEW_SECONDS) < ttl


def is_cache_entry_warm(entry: CachedSystemPrompt) -> bool:
    if entry.ttl_seconds <= 0:
        return False
    age_seconds = time.time() - entry.cached_at
    return (age_seconds + CACHE_WARM_CLOCK_SKEW_SECONDS) < entry.ttl_seconds


class SystemPromptCache:
    def __init__(self, max_size: int = DEFAULT_MAX_SIZE):
        self._max_size = max_size
        self._entries: OrderedDict[str, CachedSystemPrompt] = OrderedDict()
        self._lock = Lock()
        self._fetch_failures: dict[str, float] = {}
        self._fetch_locks: dict[str, asyncio.Lock] = {}
        self._fetch_locks_guard = Lock()

    def get(self, model_id: str) -> CachedSystemPrompt | None:
        with self._lock:
            entry = self._entries.get(model_id)
            if not entry:
                return None
            if not is_cache_entry_warm(entry):
                return None
            self._entries.move_to_end(model_id)
            return entry

    def set(
        self,
        model_id: str,
        content: str,
        *,
        ttl_seconds: int,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
        cached_at: float | None = None,
    ) -> CachedSystemPrompt:
        entry = CachedSystemPrompt(
            content=content,
            cached_at=cached_at if cached_at is not None else time.time(),
            ttl_seconds=ttl_seconds,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
        )
        with self._lock:
            self._entries[model_id] = entry
            self._entries.move_to_end(model_id)
            self._fetch_failures.pop(model_id, None)
            while len(self._entries) > self._max_size:
                self._entries.popitem(last=False)
        _redis_set(model_id, entry)
        return entry

    def invalidate(self, model_id: str, *, redis: bool = True) -> None:
        with self._lock:
            self._entries.pop(model_id, None)
            self._fetch_failures.pop(model_id, None)
        if redis:
            _redis_delete(model_id)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._fetch_failures.clear()
        _redis_clear_all()

    def record_fetch_failure(self, model_id: str) -> None:
        with self._lock:
            self._fetch_failures[model_id] = time.time()

    def is_fetch_backoff_active(
        self,
        model_id: str,
        *,
        policy: StaleServePolicy = STALE_SERVE_POLICY,
    ) -> bool:
        with self._lock:
            failed_at = self._fetch_failures.get(model_id)
        if failed_at is None:
            return False
        return (time.time() - failed_at) < policy.failure_backoff_seconds

    def serve_stale_from_binding(
        self,
        model_id: str,
        binding,
        *,
        default_ttl: int,
        policy: StaleServePolicy = STALE_SERVE_POLICY,
    ) -> CachedSystemPrompt | None:
        """Refill LRU from binding stale DB cache and extend effective TTL."""
        if not binding.cached_content:
            return None

        ttl = binding_cache_ttl_seconds(binding, default_ttl)
        effective_ttl = policy.effective_ttl_on_failure(ttl)
        return self.set(
            model_id,
            binding.cached_content,
            ttl_seconds=effective_ttl,
            prompt_name=binding.external_name,
            prompt_version=binding.cached_version,
            cached_at=time.time(),
        )

    async def acquire_fetch_lock(self, model_id: str) -> asyncio.Lock:
        with self._fetch_locks_guard:
            lock = self._fetch_locks.get(model_id)
            if lock is None:
                lock = asyncio.Lock()
                self._fetch_locks[model_id] = lock
            return lock


SYSTEM_PROMPT_CACHE = SystemPromptCache()


def _redis_key(model_id: str) -> str:
    return f'{_REDIS_KEY_PREFIX}:{model_id}'


def _serialize_entry(entry: CachedSystemPrompt) -> str:
    return json.dumps(
        {
            'content': entry.content,
            'cached_at': entry.cached_at,
            'ttl_seconds': entry.ttl_seconds,
            'prompt_name': entry.prompt_name,
            'prompt_version': entry.prompt_version,
        }
    )


def _deserialize_entry(raw: str) -> CachedSystemPrompt | None:
    try:
        data = json.loads(raw)
        return CachedSystemPrompt(
            content=data['content'],
            cached_at=float(data['cached_at']),
            ttl_seconds=int(data['ttl_seconds']),
            prompt_name=data.get('prompt_name'),
            prompt_version=data.get('prompt_version'),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        log.debug('Invalid system prompt cache payload in Redis', exc_info=True)
        return None


def _redis_set(model_id: str, entry: CachedSystemPrompt) -> None:
    client = get_redis_client(async_mode=False)
    if client is None:
        return
    try:
        client.set(_redis_key(model_id), _serialize_entry(entry), ex=max(entry.ttl_seconds, 1))
    except Exception:
        log.debug('Failed to write system prompt cache to Redis', exc_info=True)


def _redis_delete(model_id: str) -> None:
    client = get_redis_client(async_mode=False)
    if client is None:
        return
    try:
        client.delete(_redis_key(model_id))
    except Exception:
        log.debug('Failed to delete system prompt cache from Redis', exc_info=True)


def _redis_clear_all() -> None:
    client = get_redis_client(async_mode=False)
    if client is None:
        return
    pattern = f'{_REDIS_KEY_PREFIX}:*'
    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        log.debug('Failed to clear system prompt cache in Redis', exc_info=True)


def _redis_lookup_checked(model_id: str) -> tuple[bool, CachedSystemPrompt | None]:
    """Return ``(redis_checked, entry)``.

    ``redis_checked`` is False when Redis is unavailable or the read failed.
    """
    client = get_redis_client(async_mode=False)
    if client is None:
        return False, None
    try:
        raw = client.get(_redis_key(model_id))
        if not raw:
            return True, None
        entry = _deserialize_entry(raw)
        if entry is None or not is_cache_entry_warm(entry):
            return True, None
        return True, entry
    except Exception:
        log.debug('Failed to read system prompt cache from Redis', exc_info=True)
        return False, None


def _store_l1_from_entry(model_id: str, entry: CachedSystemPrompt) -> CachedSystemPrompt:
    return SYSTEM_PROMPT_CACHE.set(
        model_id,
        entry.content,
        ttl_seconds=entry.ttl_seconds,
        prompt_name=entry.prompt_name,
        prompt_version=entry.prompt_version,
        cached_at=entry.cached_at,
    )


def get_cached_system_prompt(model_id: str) -> CachedSystemPrompt | None:
    """Return a warm L1 entry, or refill L1 from Redis on miss."""
    l1_entry = SYSTEM_PROMPT_CACHE.get(model_id)
    if l1_entry is not None:
        return l1_entry

    redis_checked, redis_entry = _redis_lookup_checked(model_id)
    if redis_checked and redis_entry is not None:
        return _store_l1_from_entry(model_id, redis_entry)
    return None


async def get_cached_system_prompt_async(model_id: str) -> CachedSystemPrompt | None:
    """Async-safe getter: L1 is checked in-process; Redis I/O runs in a thread."""
    l1_entry = SYSTEM_PROMPT_CACHE.get(model_id)
    if l1_entry is not None:
        return l1_entry

    redis_checked, redis_entry = await asyncio.to_thread(_redis_lookup_checked, model_id)
    if redis_checked and redis_entry is not None:
        return _store_l1_from_entry(model_id, redis_entry)
    return None


def set_cached_system_prompt(
    model_id: str,
    content: str,
    *,
    ttl_seconds: int,
    prompt_name: str | None = None,
    prompt_version: str | None = None,
    cached_at: float | None = None,
) -> CachedSystemPrompt:
    return SYSTEM_PROMPT_CACHE.set(
        model_id,
        content,
        ttl_seconds=ttl_seconds,
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        cached_at=cached_at,
    )


def invalidate_system_prompt_cache(model_id: str) -> None:
    SYSTEM_PROMPT_CACHE.invalidate(model_id)


def record_system_prompt_fetch_failure(model_id: str) -> None:
    SYSTEM_PROMPT_CACHE.record_fetch_failure(model_id)


def is_system_prompt_fetch_backoff_active(model_id: str) -> bool:
    return SYSTEM_PROMPT_CACHE.is_fetch_backoff_active(model_id)


def serve_stale_system_prompt_from_binding(
    model_id: str,
    binding,
    *,
    default_ttl: int,
) -> CachedSystemPrompt | None:
    return SYSTEM_PROMPT_CACHE.serve_stale_from_binding(
        model_id,
        binding,
        default_ttl=default_ttl,
    )


async def acquire_system_prompt_fetch_lock(model_id: str) -> asyncio.Lock:
    return await SYSTEM_PROMPT_CACHE.acquire_fetch_lock(model_id)


def is_newer_cache_write(
    existing_cached_at: int | None,
    existing_cached_version: str | None,
    new_cached_at: int,
    new_cached_version: str | None,
) -> bool:
    """Return True when a cache write should replace the stored binding row."""
    if existing_cached_at is None:
        return True
    if new_cached_at > existing_cached_at:
        return True
    if new_cached_at < existing_cached_at:
        return False

    existing_key = _cache_version_sort_key(existing_cached_version)
    new_key = _cache_version_sort_key(new_cached_version)
    return new_key >= existing_key


def _cache_version_sort_key(version: str | None) -> tuple[int, Any]:
    if version is None:
        return (0, '')
    try:
        return (1, int(version))
    except ValueError:
        return (2, version)
