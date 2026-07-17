"""In-process LRU+TTL cache for resolved Langfuse system prompts."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

DEFAULT_MAX_SIZE = 256


@dataclass(frozen=True)
class CachedSystemPrompt:
    content: str
    cached_at: float
    ttl_seconds: int
    prompt_name: str | None = None
    prompt_version: str | None = None


class SystemPromptCache:
    def __init__(self, max_size: int = DEFAULT_MAX_SIZE):
        self._max_size = max_size
        self._entries: OrderedDict[str, CachedSystemPrompt] = OrderedDict()
        self._lock = Lock()

    def get(self, model_id: str) -> CachedSystemPrompt | None:
        with self._lock:
            entry = self._entries.get(model_id)
            if not entry:
                return None
            if (time.time() - entry.cached_at) >= entry.ttl_seconds:
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
            while len(self._entries) > self._max_size:
                self._entries.popitem(last=False)
        return entry

    def invalidate(self, model_id: str) -> None:
        with self._lock:
            self._entries.pop(model_id, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


SYSTEM_PROMPT_CACHE = SystemPromptCache()


def get_cached_system_prompt(model_id: str) -> CachedSystemPrompt | None:
    return SYSTEM_PROMPT_CACHE.get(model_id)


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


def binding_cache_ttl_seconds(binding, default_ttl: int) -> int:
    return binding.cache_ttl_seconds or default_ttl


def is_binding_db_cache_warm(binding, *, default_ttl: int) -> bool:
    """Return True when binding DB cache fields hold a non-expired prompt."""
    if not binding.cached_content:
        return False
    if binding.cached_at is None:
        return False

    ttl = binding_cache_ttl_seconds(binding, default_ttl)
    return (time.time() - binding.cached_at) < ttl
