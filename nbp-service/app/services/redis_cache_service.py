"""
Redis cache service for production deployment
Falls back to in-memory cache if Redis is not available
"""
import json
import logging
from typing import Any, Optional
from datetime import timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .cache_service import CacheService
from ..config import settings

logger = logging.getLogger(__name__)


class RedisCacheService:
    """Redis-based cache service with fallback to in-memory cache"""
    
    def __init__(self):
        self.redis_client = None
        self.fallback_cache = CacheService()  # In-memory fallback
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection if available"""
        if REDIS_AVAILABLE and settings.redis_url:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                self.redis_client = None
        else:
            logger.info("Using in-memory cache (Redis not configured)")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Fallback to in-memory cache
        return self.fallback_cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache with TTL"""
        ttl = ttl or settings.cache_ttl
        
        # Always set in fallback cache
        self.fallback_cache.set(key, value, ttl)
        
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(value, default=str)
                )
            except Exception as e:
                logger.error(f"Redis set error: {e}")
    
    async def clear(self):
        """Clear all cache entries"""
        self.fallback_cache.clear()
        
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()