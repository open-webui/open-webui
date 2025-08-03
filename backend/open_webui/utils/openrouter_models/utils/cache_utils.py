"""Cache utilities for multi-tier caching"""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime, timedelta
import json
import hashlib


class CacheTier(Enum):
    """Cache tier levels"""
    L1_MEMORY = "l1_memory"  # In-memory, hot data
    L2_REDIS = "l2_redis"    # Redis, shared data
    

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    tier: CacheTier
    created_at: datetime
    ttl: timedelta
    version: int = 1
    
    @property
    def expires_at(self) -> datetime:
        """Calculate expiration time"""
        return self.created_at + self.ttl
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        return datetime.now() > self.expires_at
    
    @property
    def time_to_refresh(self) -> timedelta:
        """Time until refresh needed (5 minutes before expiry)"""
        refresh_time = self.expires_at - timedelta(minutes=5)
        return refresh_time - datetime.now()
    
    @property
    def needs_refresh(self) -> bool:
        """Check if entry needs background refresh"""
        return self.time_to_refresh <= timedelta(0)
    
    def to_json(self) -> str:
        """Serialize to JSON for Redis storage"""
        return json.dumps({
            "key": self.key,
            "value": self.value,
            "tier": self.tier.value,
            "created_at": self.created_at.isoformat(),
            "ttl": self.ttl.total_seconds(),
            "version": self.version
        })
    
    @classmethod
    def from_json(cls, data: str) -> 'CacheEntry':
        """Deserialize from JSON"""
        obj = json.loads(data)
        return cls(
            key=obj["key"],
            value=obj["value"],
            tier=CacheTier(obj["tier"]),
            created_at=datetime.fromisoformat(obj["created_at"]),
            ttl=timedelta(seconds=obj["ttl"]),
            version=obj.get("version", 1)
        )


class CacheKey:
    """Cache key generator"""
    
    @staticmethod
    def generate(prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from prefix and parameters
        
        Args:
            prefix: Key prefix (e.g., "openrouter:models")
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            Generated cache key
        """
        parts = [prefix]
        
        # Add positional args
        for arg in args:
            parts.append(str(arg))
        
        # Add keyword args (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            parts.append(f"{key}:{value}")
        
        # Generate hash for long keys
        key_str = ":".join(parts)
        if len(key_str) > 100:
            # Use hash for long keys
            key_hash = hashlib.md5(key_str.encode()).hexdigest()[:8]
            return f"{prefix}:hash:{key_hash}"
        
        return key_str
    
    @staticmethod
    def models_list() -> str:
        """Cache key for models list"""
        return "openrouter:models:list"
    
    @staticmethod
    def model_by_id(model_id: str) -> str:
        """Cache key for specific model"""
        return f"openrouter:models:id:{model_id}"
    
    @staticmethod
    def health_check() -> str:
        """Cache key for health check"""
        return "openrouter:health"