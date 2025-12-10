import json
import redis
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError
import uuid
import threading
import logging

log = logging.getLogger(__name__)

# Shared connection pool for all Redis operations (one per pod)
_redis_pools = {}
_pool_lock = threading.Lock()  # Thread-safe pool creation


def get_redis_pool(redis_url):
    """Get or create a shared Redis connection pool for the given URL.
    
    This ensures all Redis operations share connections efficiently,
    improving performance under concurrent load.
    
    Thread-safe: Uses a lock to prevent race conditions when creating pools.
    
    Args:
        redis_url: Redis connection URL. Must be a non-empty string.
        
    Returns:
        ConnectionPool: Redis connection pool
        
    Raises:
        ValueError: If redis_url is None, empty, or invalid
    """
    # BUG #1 fix: Validate redis_url before using it
    if not redis_url or not isinstance(redis_url, str) or not redis_url.strip():
        raise ValueError(
            f"Invalid redis_url: {redis_url}. "
            "redis_url must be a non-empty string (e.g., 'redis://localhost:6379/0')"
        )
    
    global _redis_pools
    # Double-check locking pattern for thread safety
    if redis_url not in _redis_pools:
        with _pool_lock:
            # Check again after acquiring lock (double-check pattern)
            if redis_url not in _redis_pools:
                try:
                    _redis_pools[redis_url] = ConnectionPool.from_url(
                        redis_url,
                        decode_responses=True,
                        max_connections=50,  # Maximum connections in pool (adjust based on load)
                        retry_on_timeout=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                        health_check_interval=30,  # Health check every 30 seconds
                    )
                except Exception as e:
                    log.error(f"Failed to create Redis connection pool for URL: {redis_url}. Error: {e}")
                    raise ValueError(f"Invalid Redis URL: {redis_url}. Error: {e}") from e
    return _redis_pools[redis_url]


class RedisLock:
    def __init__(self, redis_url, lock_name, timeout_secs):
        self.lock_name = lock_name
        self.lock_id = str(uuid.uuid4())
        self.timeout_secs = timeout_secs
        self.lock_obtained = False
        self._release_script = None  # BUG #2 fix: Cache Lua script for lock release
        # BUG #2 fix: Handle errors when creating connection pool
        try:
            # Use connection pool instead of direct connection for better performance
            pool = get_redis_pool(redis_url)
            self.redis = redis.Redis(connection_pool=pool)
        except (ValueError, Exception) as e:
            # If pool creation fails, set redis to None and log error
            log.error(
                f"Failed to initialize Redis lock '{lock_name}': {e}. "
                "Lock operations will fail gracefully."
            )
            self.redis = None

    def aquire_lock(self):
        # nx=True will only set this key if it _hasn't_ already been set
        # BUG #2 fix: Check if redis is available
        if self.redis is None:
            log.warning(f"Cannot acquire lock {self.lock_name}: Redis connection not available")
            return False
        
        try:
            self.lock_obtained = self.redis.set(
                self.lock_name, self.lock_id, nx=True, ex=self.timeout_secs
            )
            return self.lock_obtained
        except (ConnectionError, TimeoutError, RedisError) as e:
            # Log error but don't use exc_info=True to avoid printing full traceback during normal operation
            log.warning(f"Redis error acquiring lock {self.lock_name}: {e}. Redis may be unavailable.")
            self.lock_obtained = False
            return False
        except Exception as e:
            # Catch all other exceptions to prevent crashes
            log.warning(f"Unexpected error acquiring lock {self.lock_name}: {e}. Redis may be unavailable.")
            self.lock_obtained = False
            return False

    def renew_lock(self):
        # xx=True will only set this key if it _has_ already been set
        # BUG #2 fix: Check if redis is available
        if self.redis is None:
            log.warning(f"Cannot renew lock {self.lock_name}: Redis connection not available")
            return False
        
        try:
            return self.redis.set(
                self.lock_name, self.lock_id, xx=True, ex=self.timeout_secs
            )
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error renewing lock {self.lock_name}: {e}", exc_info=True)
            return False
        except Exception as e:
            log.error(f"Unexpected error renewing lock {self.lock_name}: {e}", exc_info=True)
            return False

    def release_lock(self):
        # BUG #2 fix: Check if redis is available
        if self.redis is None:
            log.warning(f"Cannot release lock {self.lock_name}: Redis connection not available")
            self.lock_obtained = False
            return
        
        # BUG #8 fix: Use Lua script for atomic check-and-delete to prevent race condition
        # BUG #2 fix: Cache script to avoid re-registering on every call
        try:
            # Register script if not already cached
            if self._release_script is None:
                # Lua script for atomic lock release (check lock_id matches before deleting)
                self._release_script = self.redis.register_script("""
                    local lock_name = KEYS[1]
                    local lock_id = ARGV[1]
                    local current_id = redis.call('GET', lock_name)
                    if current_id == lock_id then
                        redis.call('DEL', lock_name)
                        return 1
                    else
                        return 0
                    end
                """)
            result = self._release_script(keys=[self.lock_name], args=[self.lock_id])
            if result == 1:
                self.lock_obtained = False
                log.debug(f"Successfully released lock {self.lock_name}")
            else:
                log.warning(
                    f"Lock {self.lock_name} was not released: lock_id mismatch or lock already released"
                )
                self.lock_obtained = False
        except Exception as script_error:
            # Fallback to non-atomic method if Lua script fails
            # BUG #5 fix: Clear cached script so it will be re-registered on next attempt
            self._release_script = None
            log.warning(f"Lua script for lock release failed, using fallback method: {script_error}")
            try:
                lock_value = self.redis.get(self.lock_name)
                if lock_value and lock_value == self.lock_id:
                    self.redis.delete(self.lock_name)
                    self.lock_obtained = False
                    log.debug(f"Successfully released lock {self.lock_name} (fallback method)")
                else:
                    log.warning(
                        f"Lock {self.lock_name} was not released: lock_id mismatch or lock already released"
                    )
                    self.lock_obtained = False
            except (ConnectionError, TimeoutError, RedisError) as e:
                log.error(f"Redis error releasing lock {self.lock_name}: {e}", exc_info=True)
                self.lock_obtained = False
            except Exception as e:
                log.error(f"Unexpected error releasing lock {self.lock_name}: {e}", exc_info=True)
                self.lock_obtained = False


class RedisDict:
    def __init__(self, name, redis_url):
        self.name = name
        # BUG #3 fix: Handle errors when creating connection pool
        try:
            # Use connection pool instead of direct connection for better performance
            pool = get_redis_pool(redis_url)
            self.redis = redis.Redis(connection_pool=pool)
        except (ValueError, Exception) as e:
            # If pool creation fails, set redis to None and log error
            log.error(
                f"Failed to initialize RedisDict '{name}': {e}. "
                "Dict operations will fail gracefully."
            )
            self.redis = None

    def __setitem__(self, key, value):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        try:
            serialized_value = json.dumps(value)
            self.redis.hset(self.name, key, serialized_value)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error setting {self.name}[{key}]: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error setting {self.name}[{key}]: {e}", exc_info=True)
            raise

    def __getitem__(self, key):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        try:
            value = self.redis.hget(self.name, key)
            if value is None:
                raise KeyError(key)
            return json.loads(value)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting {self.name}[{key}]: {e}")
            raise KeyError(key)  # Convert to KeyError for consistency
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error for {self.name}[{key}]: {e}")
            raise KeyError(key)

    def __delitem__(self, key):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        try:
            result = self.redis.hdel(self.name, key)
            if result == 0:
                raise KeyError(key)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error deleting {self.name}[{key}]: {e}")
            raise KeyError(key)  # Convert to KeyError for consistency

    def __contains__(self, key):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            return False  # Return False on error rather than raising
        try:
            return self.redis.hexists(self.name, key)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error checking {self.name}[{key}]: {e}")
            return False  # Return False on error rather than raising

    def __len__(self):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            return 0  # Return 0 on error rather than raising
        try:
            return self.redis.hlen(self.name)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting length of {self.name}: {e}")
            return 0  # Return 0 on error rather than raising

    def keys(self):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            return []  # Return empty list on error
        try:
            return self.redis.hkeys(self.name)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting keys of {self.name}: {e}")
            return []  # Return empty list on error

    def values(self):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            return []  # Return empty list on error
        try:
            return [json.loads(v) for v in self.redis.hvals(self.name)]
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting values of {self.name}: {e}")
            return []  # Return empty list on error
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error in values() for {self.name}: {e}")
            return []  # Return empty list on decode error

    def items(self):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            return []  # Return empty list on error
        try:
            return [(k, json.loads(v)) for k, v in self.redis.hgetall(self.name).items()]
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting items of {self.name}: {e}")
            return []  # Return empty list on error
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error in items() for {self.name}: {e}")
            return []  # Return empty list on decode error

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            return  # Don't raise - clearing is best-effort
        try:
            self.redis.delete(self.name)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error clearing {self.name}: {e}")
            # Don't raise - clearing is best-effort

    def update(self, other=None, **kwargs):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        try:
            if other is not None:
                for k, v in other.items() if hasattr(other, "items") else other:
                    self[k] = v
            for k, v in kwargs.items():
                self[k] = v
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error updating {self.name}: {e}")
            raise

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]
