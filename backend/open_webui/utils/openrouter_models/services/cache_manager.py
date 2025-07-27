"""Cache management service for orchestrating cache operations"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ..repository.cached_repo import CachedOpenRouterRepository
from ..utils.monitoring import metrics

log = logging.getLogger(__name__)


class CacheManager:
    """Service for managing cache operations and warming"""
    
    def __init__(self, cached_repository: CachedOpenRouterRepository):
        self.cached_repo = cached_repository
        self._warm_cache_task: Optional[asyncio.Task] = None
        self._is_warming = False
    
    async def warm_cache(self):
        """Warm up cache on startup"""
        if self._is_warming:
            log.info("Cache warming already in progress")
            return
        
        self._is_warming = True
        try:
            log.info("Starting cache warming...")
            
            # Fetch all models to populate cache
            models = await self.cached_repo.fetch_all_models()
            log.info(f"Cache warmed with {len(models)} models")
            
            # Also warm individual model caches for frequently used models
            frequent_models = [
                "anthropic/claude-sonnet-4",
                "google/gemini-2.5-flash",
                "openai/gpt-4o-mini",
                "deepseek/deepseek-chat-v3-0324"
            ]
            
            for model_id in frequent_models:
                await self.cached_repo.fetch_model_by_id(model_id)
            
            log.info("Cache warming completed successfully")
            
        except Exception as e:
            log.error(f"Cache warming failed: {e}")
        finally:
            self._is_warming = False
    
    async def start_periodic_refresh(self, interval_minutes: int = 55):
        """
        Start periodic cache refresh
        
        Args:
            interval_minutes: Refresh interval (default 55 min for 1-hour cache)
        """
        if self._warm_cache_task and not self._warm_cache_task.done():
            log.warning("Periodic refresh already running")
            return
        
        async def _refresh_loop():
            while True:
                try:
                    await asyncio.sleep(interval_minutes * 60)
                    log.info("Starting periodic cache refresh")
                    await self.warm_cache()
                except asyncio.CancelledError:
                    log.info("Periodic cache refresh cancelled")
                    break
                except Exception as e:
                    log.error(f"Periodic refresh error: {e}")
        
        self._warm_cache_task = asyncio.create_task(_refresh_loop())
        log.info(f"Started periodic cache refresh every {interval_minutes} minutes")
    
    async def stop_periodic_refresh(self):
        """Stop periodic cache refresh"""
        if self._warm_cache_task:
            self._warm_cache_task.cancel()
            try:
                await self._warm_cache_task
            except asyncio.CancelledError:
                pass
            self._warm_cache_task = None
            log.info("Stopped periodic cache refresh")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        l1_cache = self.cached_repo.l1_cache
        l2_cache = self.cached_repo.l2_cache
        
        # Get metrics from monitoring
        perf_metrics = metrics.get_metrics()
        
        stats = {
            "l1_cache": {
                "size": len(l1_cache),
                "max_size": l1_cache.maxsize,
                "ttl_seconds": l1_cache.ttl,
                "hit_rate": perf_metrics.get("fetch_all_models", {}).get("cache_hit_rate", 0)
            },
            "l2_cache": {
                "size": len(l2_cache),
                "max_size": l2_cache.maxsize,
                "ttl_seconds": l2_cache.ttl
            },
            "performance": {
                "total_requests": perf_metrics.get("_summary", {}).get("total_operations", 0),
                "avg_response_time_ms": perf_metrics.get("fetch_all_models", {}).get("avg_time_ms", 0),
                "cache_hits": sum(
                    m.get("cache_hits", 0) 
                    for m in perf_metrics.values() 
                    if isinstance(m, dict)
                ),
                "cache_misses": sum(
                    m.get("cache_misses", 0) 
                    for m in perf_metrics.values() 
                    if isinstance(m, dict)
                )
            },
            "last_refresh": datetime.now().isoformat(),
            "is_warming": self._is_warming,
            "periodic_refresh_active": bool(
                self._warm_cache_task and not self._warm_cache_task.done()
            )
        }
        
        return stats
    
    async def invalidate_cache(self, pattern: Optional[str] = None):
        """
        Invalidate cache entries
        
        Args:
            pattern: Optional pattern to match keys for partial invalidation
        """
        await self.cached_repo.invalidate_cache(pattern)
        
        if pattern:
            log.info(f"Invalidated cache entries matching pattern: {pattern}")
        else:
            log.info("Invalidated all cache entries")
    
    async def force_refresh(self):
        """Force refresh all cached data"""
        log.info("Forcing cache refresh...")
        
        # Invalidate all caches
        await self.invalidate_cache()
        
        # Re-warm cache
        await self.warm_cache()
        
        log.info("Force refresh completed")