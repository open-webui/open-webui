"""
Redis cache utility for user settings, permissions, roles, and group data.

This module provides caching functionality to speed up retrieval of:
- User settings (inherited from group admin)
- User roles
- User permissions
- Group membership
- API keys and virtual keys (inherited from group admin)

All cache entries are automatically invalidated when data changes to ensure consistency.
"""

import json
import logging
import redis
from typing import Optional, Any, List
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from open_webui.env import REDIS_URL
from open_webui.socket.utils import get_redis_pool

log = logging.getLogger(__name__)

# Cache TTL in seconds (default: 1 hour)
DEFAULT_CACHE_TTL = 3600

# Cache key prefixes
CACHE_PREFIX_USER_ROLE = "cache:user:role"
CACHE_PREFIX_USER_SETTINGS = "cache:user:settings"
CACHE_PREFIX_USER_PERMISSIONS = "cache:user:permissions"
CACHE_PREFIX_USER_GROUPS = "cache:user:groups"
CACHE_PREFIX_GROUP_ADMIN_CONFIG = "cache:group:admin_config"
CACHE_PREFIX_GROUP_MEMBERS = "cache:group:members"
CACHE_PREFIX_AUTH_USER = "cache:auth:user"
CACHE_PREFIX_AUTH_API_KEY = "cache:auth:api_key"


class CacheManager:
    """Manages Redis caching for user and group data."""
    
    def __init__(self, redis_url: str = REDIS_URL):
        """Initialize cache manager with Redis connection pool."""
        self.redis_url = redis_url
        self.pool = get_redis_pool(redis_url)
        self.redis = redis.Redis(connection_pool=self.pool)
        self._redis_available = None  # Cache Redis availability check
        self._last_connection_error = None  # Track last connection error to reduce log spam
    
    def _check_redis_available(self) -> bool:
        """Check if Redis is available. Caches result to avoid repeated checks."""
        if self._redis_available is None:
            try:
                self.redis.ping()
                self._redis_available = True
                self._last_connection_error = None
            except Exception:
                self._redis_available = False
        return self._redis_available
    
    def _get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Quick check if Redis is available
        if not self._check_redis_available():
            return None
            
        try:
            value = self.redis.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (ConnectionError, TimeoutError, RedisError) as e:
            # Only log connection errors once per unique error message to reduce spam
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, falling back to database. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False  # Mark as unavailable
            return None
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error for cache key {key}: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error getting cache key {key}: {e}", exc_info=True)
            return None
    
    def _set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
        """Set value in cache with TTL."""
        # Quick check if Redis is available
        if not self._check_redis_available():
            return False
            
        try:
            serialized = json.dumps(value)
            self.redis.setex(key, ttl, serialized)
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            # Only log connection errors once per unique error message to reduce spam
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping cache write. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False  # Mark as unavailable
            return False
        except Exception as e:
            log.error(f"Unexpected error setting cache key {key}: {e}", exc_info=True)
            return False
    
    def _delete(self, key: str) -> bool:
        """Delete key from cache."""
        # Quick check if Redis is available
        if not self._check_redis_available():
            return False
            
        try:
            self.redis.delete(key)
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            # Only log connection errors once per unique error message to reduce spam
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping cache delete. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False  # Mark as unavailable
            return False
        except Exception as e:
            log.error(f"Unexpected error deleting cache key {key}: {e}", exc_info=True)
            return False
    
    def _delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern. Returns count of deleted keys."""
        # Quick check if Redis is available
        if not self._check_redis_available():
            return 0
            
        try:
            count = 0
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    count += self.redis.delete(*keys)
                if cursor == 0:
                    break
            return count
        except (ConnectionError, TimeoutError, RedisError) as e:
            # Only log connection errors once per unique error message to reduce spam
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping pattern delete. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False  # Mark as unavailable
            return 0
        except Exception as e:
            log.error(f"Unexpected error deleting pattern {pattern}: {e}", exc_info=True)
            return 0
    
    # User role caching
    def get_user_role(self, user_id: str) -> Optional[str]:
        """Get cached user role."""
        key = f"{CACHE_PREFIX_USER_ROLE}:{user_id}"
        return self._get(key)
    
    def set_user_role(self, user_id: str, role: str) -> bool:
        """Cache user role."""
        key = f"{CACHE_PREFIX_USER_ROLE}:{user_id}"
        return self._set(key, role)
    
    def invalidate_user_role(self, user_id: str) -> bool:
        """Invalidate cached user role."""
        key = f"{CACHE_PREFIX_USER_ROLE}:{user_id}"
        return self._delete(key)
    
    # User settings caching (inherited from group admin)
    def get_user_settings(self, user_id: str, config_path: str) -> Optional[Any]:
        """Get cached user settings for a specific config path."""
        key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
        return self._get(key)
    
    def set_user_settings(self, user_id: str, config_path: str, value: Any) -> bool:
        """Cache user settings for a specific config path."""
        key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
        return self._set(key, value)
    
    def invalidate_user_settings(self, user_id: str, config_path: Optional[str] = None) -> int:
        """Invalidate cached user settings. If config_path is None, invalidates all settings for user."""
        if config_path:
            key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
            return 1 if self._delete(key) else 0
        else:
            pattern = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:*"
            return self._delete_pattern(pattern)
    
    # User permissions caching
    def get_user_permissions(self, user_id: str) -> Optional[dict]:
        """Get cached user permissions."""
        key = f"{CACHE_PREFIX_USER_PERMISSIONS}:{user_id}"
        return self._get(key)
    
    def set_user_permissions(self, user_id: str, permissions: dict) -> bool:
        """Cache user permissions."""
        key = f"{CACHE_PREFIX_USER_PERMISSIONS}:{user_id}"
        return self._set(key, permissions)
    
    def invalidate_user_permissions(self, user_id: str) -> bool:
        """Invalidate cached user permissions."""
        key = f"{CACHE_PREFIX_USER_PERMISSIONS}:{user_id}"
        return self._delete(key)
    
    # User groups caching
    def get_user_groups(self, user_id: str) -> Optional[List[dict]]:
        """Get cached user groups."""
        key = f"{CACHE_PREFIX_USER_GROUPS}:{user_id}"
        return self._get(key)
    
    def set_user_groups(self, user_id: str, groups: List[dict]) -> bool:
        """Cache user groups."""
        key = f"{CACHE_PREFIX_USER_GROUPS}:{user_id}"
        return self._set(key, groups)
    
    def invalidate_user_groups(self, user_id: str) -> bool:
        """Invalidate cached user groups."""
        key = f"{CACHE_PREFIX_USER_GROUPS}:{user_id}"
        return self._delete(key)
    
    # Group admin config caching
    def get_group_admin_config(self, group_id: str, config_path: str) -> Optional[Any]:
        """Get cached group admin config for a specific config path."""
        key = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG}:{group_id}:{config_path}"
        return self._get(key)
    
    def set_group_admin_config(self, group_id: str, config_path: str, value: Any) -> bool:
        """Cache group admin config for a specific config path."""
        key = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG}:{group_id}:{config_path}"
        return self._set(key, value)
    
    def invalidate_group_admin_config(self, group_id: str, config_path: Optional[str] = None) -> int:
        """Invalidate cached group admin config. If config_path is None, invalidates all configs for group."""
        if config_path:
            key = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG}:{group_id}:{config_path}"
            return 1 if self._delete(key) else 0
        else:
            pattern = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG}:{group_id}:*"
            return self._delete_pattern(pattern)
    
    # Group members caching
    def get_group_members(self, group_id: str) -> Optional[List[str]]:
        """Get cached group members."""
        key = f"{CACHE_PREFIX_GROUP_MEMBERS}:{group_id}"
        return self._get(key)
    
    def set_group_members(self, group_id: str, members: List[str]) -> bool:
        """Cache group members."""
        key = f"{CACHE_PREFIX_GROUP_MEMBERS}:{group_id}"
        return self._set(key, members)
    
    def invalidate_group_members(self, group_id: str) -> bool:
        """Invalidate cached group members."""
        key = f"{CACHE_PREFIX_GROUP_MEMBERS}:{group_id}"
        return self._delete(key)
    
    # Bulk invalidation methods
    def invalidate_all_user_data(self, user_id: str) -> int:
        """Invalidate all cached data for a user (role, settings, permissions, groups, auth)."""
        count = 0
        count += 1 if self.invalidate_user_role(user_id) else 0
        count += self.invalidate_user_settings(user_id)
        count += 1 if self.invalidate_user_permissions(user_id) else 0
        count += 1 if self.invalidate_user_groups(user_id) else 0
        count += 1 if self.invalidate_auth_user(user_id) else 0
        return count
    
    def invalidate_all_group_data(self, group_id: str) -> int:
        """Invalidate all cached data for a group (admin config, members)."""
        count = 0
        count += self.invalidate_group_admin_config(group_id)
        count += 1 if self.invalidate_group_members(group_id) else 0
        return count
    
    def invalidate_group_member_users(self, group_id: str) -> int:
        """Invalidate cache for all users who are members of this group."""
        members = self.get_group_members(group_id)
        if not members:
            return 0
        
        count = 0
        for user_id in members:
            count += self.invalidate_all_user_data(user_id)
        return count
    
    # Authentication caching
    def get_auth_user(self, user_id: str) -> Optional[dict]:
        """Get cached user object for authentication."""
        key = f"{CACHE_PREFIX_AUTH_USER}:{user_id}"
        return self._get(key)
    
    def set_auth_user(self, user_id: str, user_data: dict, ttl: int = 600) -> bool:
        """Cache user object for authentication. Default TTL: 10 minutes."""
        key = f"{CACHE_PREFIX_AUTH_USER}:{user_id}"
        return self._set(key, user_data, ttl)
    
    def invalidate_auth_user(self, user_id: str) -> bool:
        """Invalidate cached user authentication data."""
        key = f"{CACHE_PREFIX_AUTH_USER}:{user_id}"
        return self._delete(key)
    
    # API Key caching
    def get_api_key_user(self, api_key_hash: str) -> Optional[str]:
        """Get cached user_id for API key. Returns user_id if found."""
        key = f"{CACHE_PREFIX_AUTH_API_KEY}:{api_key_hash}"
        return self._get(key)
    
    def set_api_key_user(self, api_key_hash: str, user_id: str, ttl: int = 1800) -> bool:
        """Cache API key to user_id mapping. Default TTL: 30 minutes."""
        key = f"{CACHE_PREFIX_AUTH_API_KEY}:{api_key_hash}"
        return self._set(key, user_id, ttl)
    
    def invalidate_api_key(self, api_key_hash: str) -> bool:
        """Invalidate cached API key mapping."""
        key = f"{CACHE_PREFIX_AUTH_API_KEY}:{api_key_hash}"
        return self._delete(key)
    
    def invalidate_all_api_keys_for_user(self, user_id: str) -> int:
        """Invalidate all API keys for a user. Note: This requires scanning, use sparingly."""
        # Quick check if Redis is available
        if not self._check_redis_available():
            return 0
            
        # This is less efficient, but needed when user's API key changes
        # Consider storing reverse mapping (user_id -> api_key_hashes) for better performance
        pattern = f"{CACHE_PREFIX_AUTH_API_KEY}:*"
        count = 0
        cursor = 0
        try:
            while True:
                cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                for key in keys:
                    cached_user_id = self._get(key)
                    if cached_user_id == user_id:
                        self._delete(key)
                        count += 1
                if cursor == 0:
                    break
        except (ConnectionError, TimeoutError, RedisError) as e:
            # Only log connection errors once per unique error message to reduce spam
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping API key invalidation. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False  # Mark as unavailable
        except Exception as e:
            log.warning(f"Error invalidating API keys for user {user_id}: {e}")
        return count


# Global cache manager instance
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

