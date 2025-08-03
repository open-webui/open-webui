"""
Simple in-memory cache service for exchange rates
In production, this would use Redis
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio


class CacheService:
    """In-memory cache for exchange rates"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.utcnow() < expiry:
                return value
            else:
                # Remove expired entry
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL in seconds"""
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)
    
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries from cache"""
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if current_time >= expiry
        ]
        for key in expired_keys:
            del self._cache[key]