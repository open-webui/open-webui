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
import time
import threading
from typing import Optional, Any, List, Callable
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from open_webui.env import REDIS_URL
from open_webui.socket.utils import get_redis_pool, RedisLock

log = logging.getLogger(__name__)

# Cache TTL in seconds (default: 15 minutes for better consistency)
# Shorter TTL reduces stale data window if invalidation fails
DEFAULT_CACHE_TTL = 900  # 15 minutes (reduced from 1 hour)

# Cache key prefixes
CACHE_PREFIX_USER_ROLE = "cache:user:role"
CACHE_PREFIX_USER_SETTINGS = "cache:user:settings"
CACHE_PREFIX_USER_SETTINGS_KEYS = "cache:user:settings:keys"  # Set tracking all config_paths for a user
CACHE_PREFIX_USER_PERMISSIONS = "cache:user:permissions"
CACHE_PREFIX_USER_GROUPS = "cache:user:groups"
CACHE_PREFIX_GROUP_ADMIN_CONFIG = "cache:group:admin_config"
CACHE_PREFIX_GROUP_ADMIN_CONFIG_KEYS = "cache:group:admin_config:keys"  # Set tracking all config_paths for a group
CACHE_PREFIX_GROUP_MEMBERS = "cache:group:members"
CACHE_PREFIX_AUTH_USER = "cache:auth:user"
CACHE_PREFIX_AUTH_API_KEY = "cache:auth:api_key"
CACHE_PREFIX_USER_API_KEYS = "cache:user:api_keys"  # Reverse mapping: user_id -> Set of API key hashes


class CacheManager:
    """Manages Redis caching for user and group data."""
    
    def __init__(self, redis_url: str = REDIS_URL, use_master: bool = True):
        """
        Initialize cache manager with Redis connection pool.
        
        Args:
            redis_url: Redis connection URL (used if Sentinel is not configured)
            use_master: If True, use master connection (for writes). If False, use replica (for reads).
        """
        self.redis_url = redis_url
        self.use_master = use_master
        self.pool = get_redis_pool(redis_url, use_master=use_master)
        
        # Handle Sentinel connection wrapper
        if hasattr(self.pool, '_conn'):
            self.redis = self.pool._conn
        elif hasattr(self.pool, 'get_connection'):
            # For Sentinel connections, get the appropriate connection
            from open_webui.socket.utils import get_redis_master_connection, get_redis_replica_connection
            if use_master:
                self.redis = get_redis_master_connection()
            else:
                self.redis = get_redis_replica_connection()
            if self.redis is None:
                # Fallback to direct connection
                self.redis = redis.Redis(connection_pool=self.pool)
        else:
            # Standard connection pool
            self.redis = redis.Redis(connection_pool=self.pool)
        
        self._redis_available = None  # Cache Redis availability check
        self._last_connection_error = None  # Track last connection error to reduce log spam
        self._last_availability_check = 0  # Track when we last checked Redis availability
        self._availability_check_interval = 30  # Refresh availability check every 30 seconds
    
    def _check_redis_available(self) -> bool:
        """Check if Redis is available. Caches result but refreshes periodically.
        
        Refreshes availability check every 30 seconds to detect Redis recovery.
        """
        current_time = time.time()
        
        # Refresh check if enough time has passed or if never checked
        if (self._redis_available is None or 
            (not self._redis_available and 
             current_time - self._last_availability_check > self._availability_check_interval)):
            try:
                self.redis.ping()
                self._redis_available = True
                self._last_connection_error = None
                self._last_availability_check = current_time
            except Exception:
                self._redis_available = False
                self._last_availability_check = current_time
        
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
        """Delete all keys matching pattern. Returns count of deleted keys.
        
        DEPRECATED: This method uses SCAN which is slow in high-traffic environments.
        For bulk invalidation, use Set-based tracking methods like invalidate_user_settings()
        or invalidate_group_admin_config() which are O(N) on the user's keys, not all Redis keys.
        """
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
        """Get cached user settings for a specific config path.
        
        CRITICAL RBAC: Cache keys are scoped by user_id to ensure proper isolation.
        """
        key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
        cached = self._get(key)
        if cached is not None:
            log.debug(f"[RBAC_CACHE_GET] Cache HIT for user_id={user_id} config_path={config_path}")
        else:
            log.debug(f"[RBAC_CACHE_GET] Cache MISS for user_id={user_id} config_path={config_path}")
        return cached
    
    def set_user_settings(self, user_id: str, config_path: str, value: Any) -> bool:
        """Cache user settings for a specific config path.
        
        CRITICAL RBAC: Cache keys are scoped by user_id to ensure proper isolation.
        Also maintains a Set tracking all config_paths for this user for fast bulk invalidation.
        """
        if not self._check_redis_available():
            return False
        
        try:
            key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
            log.debug(f"[RBAC_CACHE_SET] Setting cache for user_id={user_id} config_path={config_path} value_length={len(str(value)) if value else 0}")
            serialized = json.dumps(value)
            self.redis.setex(key, DEFAULT_CACHE_TTL, serialized)
            
            # Track this config_path in a Set for fast bulk invalidation
            keys_set = f"{CACHE_PREFIX_USER_SETTINGS_KEYS}:{user_id}"
            self.redis.sadd(keys_set, config_path)
            # Refresh TTL on every add to prevent premature expiration
            self.redis.expire(keys_set, DEFAULT_CACHE_TTL + 60)  # Slightly longer TTL
            
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping cache write. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return False
        except Exception as e:
            log.error(f"Unexpected error setting cache key: {e}", exc_info=True)
            return False
    
    def invalidate_user_settings(self, user_id: str, config_path: Optional[str] = None) -> int:
        """Invalidate cached user settings. If config_path is None, invalidates all settings for user.
        
        Uses Set-based tracking for fast bulk invalidation (O(N) where N is number of keys for user,
        not all keys in Redis).
        """
        if not self._check_redis_available():
            return 0
        
        try:
            if config_path:
                # Single key invalidation
                key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
                deleted = self.redis.delete(key) > 0
                
                # Remove from tracking set
                keys_set = f"{CACHE_PREFIX_USER_SETTINGS_KEYS}:{user_id}"
                self.redis.srem(keys_set, config_path)
                
                return 1 if deleted else 0
            else:
                # Bulk invalidation: Use Set to get all config_paths, then delete in pipeline
                keys_set = f"{CACHE_PREFIX_USER_SETTINGS_KEYS}:{user_id}"
                config_paths = self.redis.smembers(keys_set)
                
                if not config_paths:
                    return 0
                
                # Use pipeline for atomic batch deletion (fast, single round trip)
                pipe = self.redis.pipeline()
                count = 0
                
                for config_path in config_paths:
                    key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
                    pipe.delete(key)
                    count += 1
                
                # Delete tracking set
                pipe.delete(keys_set)
                
                # Execute all deletions in one atomic operation
                pipe.execute()
                
                return count
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping cache invalidation. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return 0
        except Exception as e:
            log.error(f"Unexpected error invalidating user settings: {e}", exc_info=True)
            return 0
    
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
        """Cache group admin config for a specific config path.
        
        Also maintains a Set tracking all config_paths for this group for fast bulk invalidation.
        """
        if not self._check_redis_available():
            return False
        
        try:
            key = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG}:{group_id}:{config_path}"
            serialized = json.dumps(value)
            self.redis.setex(key, DEFAULT_CACHE_TTL, serialized)
            
            # Track this config_path in a Set for fast bulk invalidation
            keys_set = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG_KEYS}:{group_id}"
            self.redis.sadd(keys_set, config_path)
            # Refresh TTL on every add to prevent premature expiration
            self.redis.expire(keys_set, DEFAULT_CACHE_TTL + 60)  # Slightly longer TTL
            
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping cache write. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return False
        except Exception as e:
            log.error(f"Unexpected error setting cache key: {e}", exc_info=True)
            return False
    
    def invalidate_group_admin_config(self, group_id: str, config_path: Optional[str] = None) -> int:
        """Invalidate cached group admin config. If config_path is None, invalidates all configs for group.
        
        Uses Set-based tracking for fast bulk invalidation (O(N) where N is number of keys for group,
        not all keys in Redis).
        """
        if not self._check_redis_available():
            return 0
        
        try:
            if config_path:
                # Single key invalidation
                key = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG}:{group_id}:{config_path}"
                deleted = self.redis.delete(key) > 0
                
                # Remove from tracking set
                keys_set = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG_KEYS}:{group_id}"
                self.redis.srem(keys_set, config_path)
                
                return 1 if deleted else 0
            else:
                # Bulk invalidation: Use Set to get all config_paths, then delete in pipeline
                keys_set = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG_KEYS}:{group_id}"
                config_paths = self.redis.smembers(keys_set)
                
                if not config_paths:
                    return 0
                
                # Use pipeline for atomic batch deletion (fast, single round trip)
                pipe = self.redis.pipeline()
                count = 0
                
                for config_path in config_paths:
                    key = f"{CACHE_PREFIX_GROUP_ADMIN_CONFIG}:{group_id}:{config_path}"
                    pipe.delete(key)
                    count += 1
                
                # Delete tracking set
                pipe.delete(keys_set)
                
                # Execute all deletions in one atomic operation
                pipe.execute()
                
                return count
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping cache invalidation. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return 0
        except Exception as e:
            log.error(f"Unexpected error invalidating group admin config: {e}", exc_info=True)
            return 0
    
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
        """Invalidate all cached data for a user (role, settings, permissions, groups, auth).
        
        Uses Redis pipeline for batch operations to minimize round trips.
        """
        if not self._check_redis_available():
            return 0
        
        try:
            # Use pipeline for batch operations (single round trip)
            pipe = self.redis.pipeline()
            count = 0
            
            # Build all keys to delete
            user_role_key = f"{CACHE_PREFIX_USER_ROLE}:{user_id}"
            user_permissions_key = f"{CACHE_PREFIX_USER_PERMISSIONS}:{user_id}"
            user_groups_key = f"{CACHE_PREFIX_USER_GROUPS}:{user_id}"
            auth_user_key = f"{CACHE_PREFIX_AUTH_USER}:{user_id}"
            
            pipe.delete(user_role_key)
            pipe.delete(user_permissions_key)
            pipe.delete(user_groups_key)
            pipe.delete(auth_user_key)
            count += 4
            
            # Delete user settings (all config_paths) - use Set-based invalidation
            settings_keys_set = f"{CACHE_PREFIX_USER_SETTINGS_KEYS}:{user_id}"
            config_paths = self.redis.smembers(settings_keys_set)
            if config_paths:
                for config_path in config_paths:
                    settings_key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
                    pipe.delete(settings_key)
                    count += 1
                pipe.delete(settings_keys_set)
                count += 1
            
            # Execute all deletions in one atomic operation
            pipe.execute()
            
            return count
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping user data invalidation. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return 0
        except Exception as e:
            log.error(f"Unexpected error invalidating user data: {e}", exc_info=True)
            return 0
    
    def invalidate_all_group_data(self, group_id: str) -> int:
        """Invalidate all cached data for a group (admin config, members)."""
        count = 0
        count += self.invalidate_group_admin_config(group_id)
        count += 1 if self.invalidate_group_members(group_id) else 0
        return count
    
    def invalidate_group_member_users(self, group_id: str) -> int:
        """Invalidate cache for all users who are members of this group.
        
        Uses Redis pipeline for batch operations to minimize round trips and improve performance.
        Collects all data first, then builds pipeline to avoid nested Redis calls.
        
        CRITICAL: Falls back to database if cache is empty to ensure cache invalidation
        always works. This is essential for RBAC - when an admin updates their API key,
        all group members' cached API keys MUST be invalidated to prevent stale key usage.
        """
        if not self._check_redis_available():
            return 0
        
        members = self.get_group_members(group_id)
        
        # CRITICAL FIX: If cache is empty, fall back to database query
        # This ensures cache invalidation works even if group members cache is stale/empty
        # Without this fallback, users may continue using old API keys after admin updates
        if members is None or not members:
            try:
                from open_webui.models.groups import Groups
                db_members = Groups.get_group_user_ids_by_id(group_id)
                if db_members and isinstance(db_members, list):
                    members = db_members
                    log.info(
                        f"Cache fallback: Retrieved {len(members)} group members from database "
                        f"for group {group_id} (cache was empty)"
                    )
                else:
                    # No members found in database either - group may be empty or deleted
                    log.debug(f"No group members found for group {group_id} in cache or database")
                    return 0
            except Exception as e:
                log.warning(f"Failed to retrieve group members from database for group {group_id}: {e}")
                return 0
        
        try:
            # Collect all data first (before building pipeline) to avoid nested Redis calls
            # This ensures all smembers() calls happen before pipeline execution
            user_settings_data = {}  # user_id -> list of config_paths
            
            for user_id in members:
                settings_keys_set = f"{CACHE_PREFIX_USER_SETTINGS_KEYS}:{user_id}"
                config_paths = self.redis.smembers(settings_keys_set)
                if config_paths:
                    user_settings_data[user_id] = list(config_paths)
            
            # Now build pipeline with all collected data (single round trip)
            pipe = self.redis.pipeline()
            count = 0
            
            for user_id in members:
                # Build all keys to delete for this user
                user_role_key = f"{CACHE_PREFIX_USER_ROLE}:{user_id}"
                user_permissions_key = f"{CACHE_PREFIX_USER_PERMISSIONS}:{user_id}"
                user_groups_key = f"{CACHE_PREFIX_USER_GROUPS}:{user_id}"
                auth_user_key = f"{CACHE_PREFIX_AUTH_USER}:{user_id}"
                
                # Delete individual keys
                pipe.delete(user_role_key)
                pipe.delete(user_permissions_key)
                pipe.delete(user_groups_key)
                pipe.delete(auth_user_key)
                count += 4
                
                # Delete user settings (all config_paths) - use pre-collected data
                if user_id in user_settings_data:
                    for config_path in user_settings_data[user_id]:
                        settings_key = f"{CACHE_PREFIX_USER_SETTINGS}:{user_id}:{config_path}"
                        pipe.delete(settings_key)
                        count += 1
                    settings_keys_set = f"{CACHE_PREFIX_USER_SETTINGS_KEYS}:{user_id}"
                    pipe.delete(settings_keys_set)
                    count += 1
            
            # Execute all deletions in one atomic operation
            pipe.execute()
            
            return count
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping group member cache invalidation. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return 0
        except Exception as e:
            log.error(f"Unexpected error invalidating group member users: {e}", exc_info=True)
            return 0
    
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
        """Cache API key to user_id mapping. Default TTL: 30 minutes.
        
        Also maintains reverse mapping (user_id -> Set of API key hashes) for fast invalidation.
        Cleans up old reverse mapping if API key was previously associated with different user.
        """
        if not self._check_redis_available():
            return False
        
        try:
            # Check if API key already exists and belongs to different user
            key = f"{CACHE_PREFIX_AUTH_API_KEY}:{api_key_hash}"
            existing_user_id_json = self.redis.get(key)
            
            if existing_user_id_json:
                try:
                    existing_user_id = json.loads(existing_user_id_json)
                    if existing_user_id != user_id:
                        # API key was associated with different user - clean up old reverse mapping
                        old_reverse_key = f"{CACHE_PREFIX_USER_API_KEYS}:{existing_user_id}"
                        self.redis.srem(old_reverse_key, api_key_hash)
                        # Clean up reverse mapping if empty
                        if self.redis.scard(old_reverse_key) == 0:
                            self.redis.delete(old_reverse_key)
                except (json.JSONDecodeError, Exception) as e:
                    log.debug(f"Error cleaning up old reverse mapping for API key: {e}")
            
            # Forward mapping: api_key_hash -> user_id
            serialized = json.dumps(user_id)
            self.redis.setex(key, ttl, serialized)
            
            # Reverse mapping: user_id -> Set of API key hashes (for fast invalidation)
            # Use Redis Set to track all API keys for this user
            reverse_key = f"{CACHE_PREFIX_USER_API_KEYS}:{user_id}"
            self.redis.sadd(reverse_key, api_key_hash)
            # Refresh TTL on reverse mapping (slightly longer than forward mapping to ensure cleanup)
            self.redis.expire(reverse_key, ttl + 60)
            
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping API key cache write. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return False
        except Exception as e:
            log.error(f"Unexpected error setting API key cache: {e}", exc_info=True)
            return False
    
    def invalidate_api_key(self, api_key_hash: str) -> bool:
        """Invalidate cached API key mapping.
        
        Also removes from reverse mapping if user_id is known.
        """
        if not self._check_redis_available():
            return False
        
        try:
            # Get user_id before deleting (for reverse mapping cleanup)
            key = f"{CACHE_PREFIX_AUTH_API_KEY}:{api_key_hash}"
            user_id_json = self.redis.get(key)
            
            # Delete forward mapping
            deleted = self.redis.delete(key) > 0
            
            # Remove from reverse mapping if user_id was found
            if user_id_json:
                try:
                    user_id = json.loads(user_id_json)
                    reverse_key = f"{CACHE_PREFIX_USER_API_KEYS}:{user_id}"
                    self.redis.srem(reverse_key, api_key_hash)
                    # Clean up reverse mapping if empty
                    if self.redis.scard(reverse_key) == 0:
                        self.redis.delete(reverse_key)
                except (json.JSONDecodeError, Exception) as e:
                    log.debug(f"Error cleaning up reverse mapping for API key: {e}")
            
            return deleted
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping API key invalidation. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return False
        except Exception as e:
            log.error(f"Unexpected error invalidating API key: {e}", exc_info=True)
            return False
    
    def get_or_set_with_lock(
        self,
        cache_key: str,
        fetch_func: Callable[[], Any],
        ttl: int = DEFAULT_CACHE_TTL,
        lock_timeout: int = 5,
        retry_wait_ms: int = 50,  # Deprecated: no longer used (non-blocking fallback)
        max_retries: int = 3  # Deprecated: no longer used (non-blocking fallback)
    ) -> Optional[Any]:
        """Get value from cache, or fetch and set with distributed locking to prevent cache stampede.
        
        This implements cache-aside pattern with distributed locking:
        1. Try to get from cache (fast path)
        2. If miss, try to acquire lock
        3. If lock acquired, fetch from DB, set cache, release lock
        4. If lock not acquired, immediately fall back to direct fetch (non-blocking)
        
        IMPORTANT: This function is non-blocking. If the lock isn't acquired, it immediately
        falls back to direct fetch instead of sleeping. This prevents blocking the event loop
        when called from async contexts.
        
        Args:
            cache_key: Redis cache key
            fetch_func: Function to fetch value from database if cache miss
            ttl: Cache TTL in seconds
            lock_timeout: Lock timeout in seconds (prevents deadlock)
            retry_wait_ms: Deprecated - no longer used
            max_retries: Deprecated - no longer used
            
        Returns:
            Cached or fetched value, or None if fetch fails
        """
        # Fast path: Try cache first
        cached_value = self._get(cache_key)
        if cached_value is not None:
            return cached_value
        
        # Cache miss: Try to acquire lock to fetch from DB
        # Check Redis availability first to avoid creating lock if Redis is down
        if not self._check_redis_available():
            # Redis unavailable - fall back to direct fetch
            log.debug(f"Redis unavailable for {cache_key}, falling back to direct fetch")
            try:
                value = fetch_func()
                if value is not None:
                    # Try to cache (will fail silently if Redis still down)
                    self._set(cache_key, value, ttl)
                return value
            except Exception as e:
                log.error(f"Error in fetch_func for {cache_key}: {e}", exc_info=True)
                return None
        
        lock_name = f"cache_lock:{cache_key}"
        lock = RedisLock(self.redis_url, lock_name, lock_timeout)
        
        if lock.aquire_lock():
            # We got the lock - fetch from DB and set cache
            try:
                # Double-check cache (another replica might have set it while we waited)
                cached_value = self._get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Fetch from database
                value = fetch_func()
                
                # Set cache
                if value is not None:
                    self._set(cache_key, value, ttl)
                
                return value
            finally:
                lock.release_lock()
        else:
            # Lock not acquired - another replica is fetching
            # OPTIMIZATION: Instead of blocking with time.sleep(), immediately fall back to direct fetch
            # This avoids blocking the event loop in async contexts while still being efficient
            # The cache will be populated by the lock holder, benefiting future requests
            log.debug(f"Cache lock not acquired for {cache_key}, falling back to direct fetch (non-blocking)")
            try:
                value = fetch_func()
                # Don't set cache here - the lock holder will do it
                # This prevents race conditions and redundant writes
                return value
            except Exception as e:
                log.error(f"Error in fetch_func for {cache_key}: {e}", exc_info=True)
                return None
    
    def invalidate_all_api_keys_for_user(self, user_id: str) -> int:
        """Invalidate all API keys for a user.
        
        Uses reverse mapping (Redis Set) for O(N) performance where N is number of keys
        for this user, not all keys in Redis. Fast and efficient even for users with many keys.
        """
        if not self._check_redis_available():
            return 0
        
        try:
            # Get all API key hashes for this user from reverse mapping
            reverse_key = f"{CACHE_PREFIX_USER_API_KEYS}:{user_id}"
            api_key_hashes = self.redis.smembers(reverse_key)
            
            if not api_key_hashes:
                return 0
            
            # Use pipeline for atomic batch deletion (fast, single round trip)
            pipe = self.redis.pipeline()
            count = 0
            
            for api_key_hash in api_key_hashes:
                # Delete forward mapping
                key = f"{CACHE_PREFIX_AUTH_API_KEY}:{api_key_hash}"
                pipe.delete(key)
                count += 1
            
            # Delete reverse mapping set
            pipe.delete(reverse_key)
            
            # Execute all deletions in one atomic operation
            pipe.execute()
            
            return count
        except (ConnectionError, TimeoutError, RedisError) as e:
            error_msg = str(e)
            if self._last_connection_error != error_msg:
                log.debug(f"Redis unavailable, skipping API key invalidation. Error: {e}")
                self._last_connection_error = error_msg
                self._redis_available = False
            return 0
        except Exception as e:
            log.warning(f"Error invalidating API keys for user {user_id}: {e}", exc_info=True)
            return 0


# Global cache manager instance
_cache_manager = None
_cache_manager_lock = threading.Lock()  # Thread-safe singleton creation

def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance.
    
    Thread-safe singleton pattern to prevent multiple instances.
    """
    global _cache_manager
    if _cache_manager is None:
        with _cache_manager_lock:
            # Double-check locking pattern
            if _cache_manager is None:
                _cache_manager = CacheManager()
    return _cache_manager

