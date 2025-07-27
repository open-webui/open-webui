"""Cached repository decorator with multi-tier caching"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from cachetools import TTLCache
import json

from ..models.pricing_models import ModelPricing
from ..utils.cache_utils import CacheKey, CacheEntry, CacheTier
from ..utils.monitoring import TimedOperation, metrics
from .interface import ModelPricingRepository, RepositoryError

log = logging.getLogger(__name__)


class CachedOpenRouterRepository(ModelPricingRepository):
    """Repository decorator that adds smart caching to any ModelPricingRepository"""
    
    def __init__(
        self,
        repository: ModelPricingRepository,
        l1_ttl_minutes: int = 1,
        l2_ttl_minutes: int = 60,
        enable_background_refresh: bool = True
    ):
        self.repository = repository
        self.l1_ttl = timedelta(minutes=l1_ttl_minutes)
        self.l2_ttl = timedelta(minutes=l2_ttl_minutes)
        self.enable_background_refresh = enable_background_refresh
        
        # L1 cache - in-memory for hot data
        self.l1_cache = TTLCache(maxsize=100, ttl=l1_ttl_minutes * 60)
        
        # L2 cache would be Redis in production
        # For now, using another TTLCache as placeholder
        self.l2_cache = TTLCache(maxsize=1000, ttl=l2_ttl_minutes * 60)
        
        # Background refresh tracking
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        self._refresh_lock = asyncio.Lock()
    
    async def fetch_all_models(self) -> List[ModelPricing]:
        """
        Fetch all models with multi-tier caching
        
        Returns:
            List of ModelPricing objects
        """
        cache_key = CacheKey.models_list()
        
        with TimedOperation("fetch_all_models") as op:
            # Check L1 cache first
            cached = self._get_from_cache(cache_key, CacheTier.L1_MEMORY)
            if cached:
                op.set_cache_hit(True)
                log.debug("L1 cache hit for models list")
                self._maybe_schedule_refresh(cache_key, cached)
                return cached.value
            
            # Check L2 cache
            cached = self._get_from_cache(cache_key, CacheTier.L2_REDIS)
            if cached:
                op.set_cache_hit(True)
                log.debug("L2 cache hit for models list")
                # Promote to L1
                self._set_cache(cache_key, cached.value, CacheTier.L1_MEMORY)
                self._maybe_schedule_refresh(cache_key, cached)
                return cached.value
            
            op.set_cache_hit(False)
            
            # Cache miss - fetch from repository
            try:
                models = await self.repository.fetch_all_models()
                
                # Cache in both tiers
                self._set_cache(cache_key, models, CacheTier.L1_MEMORY)
                self._set_cache(cache_key, models, CacheTier.L2_REDIS)
                
                return models
                
            except RepositoryError as e:
                # Try to return stale data if available
                stale = self._get_stale_from_cache(cache_key)
                if stale:
                    log.warning(f"Returning stale data due to error: {e}")
                    return stale.value
                raise
    
    async def fetch_model_by_id(self, model_id: str) -> Optional[ModelPricing]:
        """
        Fetch specific model with caching
        
        Args:
            model_id: The model identifier
            
        Returns:
            ModelPricing object if found
        """
        cache_key = CacheKey.model_by_id(model_id)
        
        with TimedOperation("fetch_model_by_id") as op:
            # Check caches
            cached = self._get_from_cache(cache_key, CacheTier.L1_MEMORY)
            if cached:
                op.set_cache_hit(True)
                return cached.value
            
            cached = self._get_from_cache(cache_key, CacheTier.L2_REDIS)
            if cached:
                op.set_cache_hit(True)
                self._set_cache(cache_key, cached.value, CacheTier.L1_MEMORY)
                return cached.value
            
            op.set_cache_hit(False)
            
            # Fetch from repository
            model = await self.repository.fetch_model_by_id(model_id)
            
            if model:
                self._set_cache(cache_key, model, CacheTier.L1_MEMORY)
                self._set_cache(cache_key, model, CacheTier.L2_REDIS)
            
            return model
    
    async def health_check(self) -> bool:
        """Check repository health with caching"""
        cache_key = CacheKey.health_check()
        
        # Health check has shorter TTL (30 seconds)
        cached = self.l1_cache.get(cache_key)
        if cached is not None:
            return cached
        
        result = await self.repository.health_check()
        self.l1_cache[cache_key] = result
        
        return result
    
    async def invalidate_cache(self, partial_key: Optional[str] = None):
        """
        Invalidate cache entries
        
        Args:
            partial_key: If provided, invalidate only matching keys
        """
        if partial_key:
            # Invalidate specific keys
            keys_to_remove = []
            
            for key in list(self.l1_cache.keys()):
                if partial_key in str(key):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.l1_cache.pop(key, None)
                self.l2_cache.pop(key, None)
            
            log.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{partial_key}'")
        else:
            # Clear all caches
            self.l1_cache.clear()
            self.l2_cache.clear()
            log.info("Cleared all cache entries")
    
    def _get_from_cache(self, key: str, tier: CacheTier) -> Optional[CacheEntry]:
        """Get entry from specified cache tier"""
        cache = self.l1_cache if tier == CacheTier.L1_MEMORY else self.l2_cache
        
        try:
            value = cache.get(key)
            if value is not None:
                # For L2 cache, deserialize if needed
                if tier == CacheTier.L2_REDIS and isinstance(value, str):
                    return CacheEntry.from_json(value)
                elif isinstance(value, CacheEntry):
                    return value
                else:
                    # Wrap raw value in CacheEntry
                    return CacheEntry(
                        key=key,
                        value=value,
                        tier=tier,
                        created_at=datetime.now(),
                        ttl=self.l1_ttl if tier == CacheTier.L1_MEMORY else self.l2_ttl
                    )
        except Exception as e:
            log.error(f"Error getting from {tier.value} cache: {e}")
        
        return None
    
    def _set_cache(self, key: str, value: Any, tier: CacheTier):
        """Set entry in specified cache tier"""
        cache = self.l1_cache if tier == CacheTier.L1_MEMORY else self.l2_cache
        ttl = self.l1_ttl if tier == CacheTier.L1_MEMORY else self.l2_ttl
        
        entry = CacheEntry(
            key=key,
            value=value,
            tier=tier,
            created_at=datetime.now(),
            ttl=ttl
        )
        
        try:
            if tier == CacheTier.L2_REDIS:
                # For L2, we would serialize to Redis
                # For now, just store the entry
                cache[key] = entry
            else:
                cache[key] = entry
        except Exception as e:
            log.error(f"Error setting {tier.value} cache: {e}")
    
    def _get_stale_from_cache(self, key: str) -> Optional[CacheEntry]:
        """Get potentially stale data from any cache tier"""
        # Try L2 cache first (longer TTL)
        for cache in [self.l2_cache, self.l1_cache]:
            # Access internal data to get expired entries
            if hasattr(cache, '_cache'):
                entry = cache._cache.get(key)
                if entry:
                    return entry
        return None
    
    def _maybe_schedule_refresh(self, key: str, entry: CacheEntry):
        """Schedule background refresh if needed"""
        if not self.enable_background_refresh:
            return
        
        if entry.needs_refresh and key not in self._refresh_tasks:
            task = asyncio.create_task(self._background_refresh(key))
            self._refresh_tasks[key] = task
    
    async def _background_refresh(self, key: str):
        """Perform background refresh of cache entry"""
        async with self._refresh_lock:
            try:
                log.info(f"Starting background refresh for {key}")
                
                if key == CacheKey.models_list():
                    models = await self.repository.fetch_all_models()
                    self._set_cache(key, models, CacheTier.L1_MEMORY)
                    self._set_cache(key, models, CacheTier.L2_REDIS)
                    log.info(f"Background refresh completed for {key}")
                
            except Exception as e:
                log.error(f"Background refresh failed for {key}: {e}")
            finally:
                self._refresh_tasks.pop(key, None)