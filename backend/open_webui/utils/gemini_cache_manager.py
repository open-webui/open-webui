"""
Gemini Global Cache Manager

Manages GLOBAL prompt caching for Gemini API in multi-user environment.

IMPORTANT SECURITY:
- Only cache content that is SHARED across all users (system prompts, tool specs)
- NEVER cache user-specific data (questions, thread history, private data)
- Store selection (file_search stores) is per-request, NOT cached

This cache manager ensures multi-user safety by only caching admin-defined
prompts and tool specifications that are identical for all users.
"""

import logging
import hashlib
from typing import Optional, Dict
from datetime import datetime, timedelta
from google import genai
from google.genai import types

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))

# Tool spec version - increment when prompts/tools are modified
# This is used in cache key generation to automatically invalidate old caches
TOOL_SPEC_VERSION = "v1.0.0"


class GeminiCacheManager:
    """
    Manages Gemini Global Cache for system prompts and tool specifications.

    Cache Strategy (Multi-user safe):
    - Cache Key: SHA256(model_id + tool_spec_version + stage + system_text)
    - TTL: 1 hour (configurable)
    - Max caches: 50 (LRU eviction)
    - Registry persistence: In-memory (TODO: move to Redis/DB for multi-process)

    Security:
    - ✅ Cache: system prompt, tool specs (global, admin-defined)
    - ❌ Never cache: user questions, thread history, store selections

    Usage:
        cache_manager = GeminiCacheManager(client)
        cached_content_name = cache_manager.get_or_create_cache(
            model_id="models/gemini-3-pro-preview",
            system_prompt=composed_system_prompt,
            stage="execution"
        )
    """

    def __init__(self, client: genai.Client, max_caches: int = 50):
        """
        Initialize cache manager.

        Args:
            client: Gemini API client
            max_caches: Maximum number of caches to keep (LRU eviction)
        """
        self.client = client
        self.max_caches = max_caches
        self._cache_registry: Dict[str, CacheEntry] = {}

    def generate_cache_key(
        self,
        model_id: str,
        system_prompt: str,
        stage: str  # "gating" or "execution"
    ) -> str:
        """
        Generate SHA256-based cache key.

        This key uniquely identifies a cached content based on:
        - Model ID (different models have different caches)
        - Tool spec version (auto-invalidate when prompts change)
        - Stage (gating vs execution have different prompts)
        - System prompt text (the actual content being cached)

        Args:
            model_id: Model identifier (e.g., "models/gemini-3-pro-preview")
            system_prompt: Full composed system prompt text
            stage: "gating" (base only) or "execution" (base + proficiency + style + tools)

        Returns:
            SHA256 hash (hex string)
        """
        key_material = "\n".join([
            model_id,
            TOOL_SPEC_VERSION,
            stage,
            system_prompt
        ])
        return hashlib.sha256(key_material.encode()).hexdigest()

    def get_or_create_cache(
        self,
        model_id: str,
        system_prompt: str,
        stage: str,
        ttl_seconds: int = 3600
    ) -> Optional[str]:
        """
        Get existing global cache or create new one.

        This method implements the core caching logic:
        1. Generate cache key based on model + version + stage + prompt
        2. Check if cache exists and is valid (within TTL)
        3. If valid, return cached_content name (cache hit!)
        4. If expired or missing, create new cache and register it

        Args:
            model_id: Model identifier (e.g., "models/gemini-3-pro-preview")
            system_prompt: System prompt text (MUST be global/shared content)
            stage: "gating" or "execution"
            ttl_seconds: Cache TTL in seconds (default: 1 hour)

        Returns:
            CachedContent name if successful (e.g., "cachedContents/abc123"),
            None if cache creation failed or prompt too small
        """
        # CRITICAL: Gemini context caching minimum token requirements vary by model
        # For Korean/English mixed text: ~4.54 chars/token observed
        #
        # Model-specific minimums (as of 2026-01):
        # - Flash models (2.5-flash, etc.): 2048 tokens → 10240 chars
        # - Pro models (3-pro-preview, etc.): May have different requirements
        #
        # To be safe, use the highest known requirement across all models
        MIN_CHARS_FOR_CACHE = 10240  # 2048 tokens × 4.54 chars/token ≈ 9298, rounded to 10240

        # Add padding if prompt is too short
        padded_prompt = system_prompt
        if len(system_prompt) < MIN_CHARS_FOR_CACHE:
            padding_needed = MIN_CHARS_FOR_CACHE - len(system_prompt)
            # Add invisible padding that LLM will ignore
            # Use repeated whitespace and harmless text
            padding = "\n\n" + "---\n" + "[CACHE_PADDING] " * (padding_needed // 17)
            padded_prompt = system_prompt + padding
            log.info(f"[CACHE] Added {len(padding)} chars padding to reach minimum (original: {len(system_prompt)} chars)")

        cache_key = self.generate_cache_key(model_id, padded_prompt, stage)

        # Check if cache exists and is valid
        if cache_key in self._cache_registry:
            entry = self._cache_registry[cache_key]
            if entry.is_valid():
                log.info(f"[GLOBAL CACHE HIT] {cache_key[:16]}... (stage: {stage})")
                entry.update_access_time()
                return entry.cache_name
            else:
                log.info(f"[GLOBAL CACHE EXPIRED] {cache_key[:16]}... (stage: {stage})")
                # Remove expired cache
                try:
                    self.client.caches.delete(name=entry.cache_name)
                except Exception as e:
                    log.warning(f"[CACHE] Failed to delete expired cache: {e}")
                del self._cache_registry[cache_key]

        # Create new cache
        try:
            log.info(f"[GLOBAL CACHE CREATE] {cache_key[:16]}... (stage: {stage})")
            log.debug(f"  Model: {model_id}")
            log.debug(f"  Original prompt length: {len(system_prompt)} chars")
            log.debug(f"  Padded prompt length: {len(padded_prompt)} chars")
            log.debug(f"  TTL: {ttl_seconds}s")

            cached_content = self.client.caches.create(
                model=model_id,
                config=types.CreateCachedContentConfig(
                    contents=[
                        {
                            "role": "user",
                            "parts": [{"text": padded_prompt}]
                        }
                    ],
                    ttl=f"{ttl_seconds}s"
                )
            )

            # Register cache in our local registry
            self._cache_registry[cache_key] = CacheEntry(
                cache_name=cached_content.name,
                cache_key=cache_key,
                model_id=model_id,
                stage=stage,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=ttl_seconds
            )

            # Evict old caches if we've exceeded the limit
            self._evict_if_needed()

            log.info(f"[GLOBAL CACHE CREATED] {cached_content.name}")
            return cached_content.name

        except Exception as e:
            log.error(f"[CACHE] Failed to create cache: {e}")
            log.exception(e)
            return None

    def invalidate_by_version(self):
        """
        Invalidate all caches when TOOL_SPEC_VERSION changes.

        Note: In practice, caches with old version will naturally miss
        since cache_key includes version. This method is here for
        documentation purposes and potential future use.
        """
        log.info(f"[CACHE] Version {TOOL_SPEC_VERSION} in use")
        log.info("[CACHE] Old version caches will naturally miss (cache keys are version-specific)")

    def _evict_if_needed(self):
        """
        Evict least recently used caches if limit exceeded.

        This implements LRU (Least Recently Used) eviction policy.
        When the cache registry exceeds max_caches, we remove the
        oldest entries based on last_accessed time.
        """
        if len(self._cache_registry) <= self.max_caches:
            return

        log.warning(f"[CACHE] Cache limit reached ({self.max_caches}), evicting LRU entries")

        # Sort by last access time (oldest first)
        sorted_entries = sorted(
            self._cache_registry.items(),
            key=lambda x: x[1].last_accessed
        )

        # Remove oldest entries
        to_remove = len(self._cache_registry) - self.max_caches
        for i in range(to_remove):
            key, entry = sorted_entries[i]
            try:
                self.client.caches.delete(name=entry.cache_name)
                del self._cache_registry[key]
                log.info(f"[CACHE EVICTED] {key[:16]}... (stage: {entry.stage})")
            except Exception as e:
                log.error(f"[CACHE] Failed to evict cache {key[:16]}...: {e}")

    def get_stats(self) -> Dict:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics including:
            - total_caches: Total number of cached contents
            - max_caches: Maximum allowed caches
            - by_stage: Count of caches by stage (gating/execution)
            - by_model: Count of caches by model ID
            - tool_spec_version: Current tool spec version
        """
        total = len(self._cache_registry)
        by_stage = {"gating": 0, "execution": 0}
        by_model = {}

        for entry in self._cache_registry.values():
            by_stage[entry.stage] = by_stage.get(entry.stage, 0) + 1
            by_model[entry.model_id] = by_model.get(entry.model_id, 0) + 1

        return {
            "total_caches": total,
            "max_caches": self.max_caches,
            "by_stage": by_stage,
            "by_model": by_model,
            "tool_spec_version": TOOL_SPEC_VERSION
        }

    def clear_all_caches(self) -> Dict:
        """
        Clear all caches from registry and Gemini API.

        This is useful when prompts are modified and you want to force
        cache regeneration.

        Returns:
            Dictionary with deletion results:
            - deleted_count: Number of caches successfully deleted
            - failed_count: Number of caches that failed to delete
            - errors: List of error messages
        """
        log.info("[CACHE] Clearing all caches")

        deleted_count = 0
        failed_count = 0
        errors = []

        # Delete all caches from Gemini API
        for cache_key, entry in list(self._cache_registry.items()):
            try:
                self.client.caches.delete(name=entry.cache_name)
                del self._cache_registry[cache_key]
                deleted_count += 1
                log.info(f"[CACHE DELETED] {cache_key[:16]}... (stage: {entry.stage})")
            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to delete {cache_key[:16]}...: {str(e)}"
                errors.append(error_msg)
                log.error(f"[CACHE] {error_msg}")

        log.info(f"[CACHE] Clear completed - deleted: {deleted_count}, failed: {failed_count}")

        return {
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "errors": errors
        }

    def clear_caches_by_stage(self, stage: str) -> Dict:
        """
        Clear caches for a specific stage.

        Args:
            stage: Stage to clear ("gating" or "execution")

        Returns:
            Dictionary with deletion results
        """
        log.info(f"[CACHE] Clearing caches for stage: {stage}")

        deleted_count = 0
        failed_count = 0
        errors = []

        # Delete caches matching the stage
        for cache_key, entry in list(self._cache_registry.items()):
            if entry.stage == stage:
                try:
                    self.client.caches.delete(name=entry.cache_name)
                    del self._cache_registry[cache_key]
                    deleted_count += 1
                    log.info(f"[CACHE DELETED] {cache_key[:16]}... (stage: {entry.stage})")
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Failed to delete {cache_key[:16]}...: {str(e)}"
                    errors.append(error_msg)
                    log.error(f"[CACHE] {error_msg}")

        log.info(f"[CACHE] Clear completed for stage {stage} - deleted: {deleted_count}, failed: {failed_count}")

        return {
            "stage": stage,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "errors": errors
        }


class CacheEntry:
    """
    Represents a global cached content entry.

    This class tracks metadata about a cached content including:
    - Cache name (the actual Gemini API cache identifier)
    - Cache key (our local SHA256 hash)
    - Model ID
    - Stage (gating/execution)
    - Timestamps for TTL and LRU management
    """

    def __init__(
        self,
        cache_name: str,
        cache_key: str,
        model_id: str,
        stage: str,
        created_at: datetime,
        last_accessed: datetime,
        ttl_seconds: int
    ):
        self.cache_name = cache_name
        self.cache_key = cache_key
        self.model_id = model_id
        self.stage = stage
        self.created_at = created_at
        self.last_accessed = last_accessed
        self.ttl_seconds = ttl_seconds

    def is_valid(self) -> bool:
        """
        Check if cache is still valid (within TTL).

        Returns:
            True if cache has not expired, False otherwise
        """
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() < expiry

    def update_access_time(self):
        """
        Update last access time for LRU tracking.
        Called whenever the cache is used (cache hit).
        """
        self.last_accessed = datetime.now()
