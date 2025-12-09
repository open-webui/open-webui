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
    """
    global _redis_pools
    # Double-check locking pattern for thread safety
    if redis_url not in _redis_pools:
        with _pool_lock:
            # Check again after acquiring lock (double-check pattern)
            if redis_url not in _redis_pools:
                _redis_pools[redis_url] = ConnectionPool.from_url(
                    redis_url,
                    decode_responses=True,
                    max_connections=50,  # Maximum connections in pool (adjust based on load)
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    health_check_interval=30,  # Health check every 30 seconds
                )
    return _redis_pools[redis_url]


class RedisLock:
    def __init__(self, redis_url, lock_name, timeout_secs):
        self.lock_name = lock_name
        self.lock_id = str(uuid.uuid4())
        self.timeout_secs = timeout_secs
        self.lock_obtained = False
        # Use connection pool instead of direct connection for better performance
        pool = get_redis_pool(redis_url)
        self.redis = redis.Redis(connection_pool=pool)

    def aquire_lock(self):
        # nx=True will only set this key if it _hasn't_ already been set
        try:
            self.lock_obtained = self.redis.set(
                self.lock_name, self.lock_id, nx=True, ex=self.timeout_secs
            )
            return self.lock_obtained
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error acquiring lock {self.lock_name}: {e}")
            return False
        except Exception as e:
            log.error(f"Unexpected error acquiring lock {self.lock_name}: {e}", exc_info=True)
            return False

    def renew_lock(self):
        # xx=True will only set this key if it _has_ already been set
        try:
            return self.redis.set(
                self.lock_name, self.lock_id, xx=True, ex=self.timeout_secs
            )
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error renewing lock {self.lock_name}: {e}")
            return False
        except Exception as e:
            log.error(f"Unexpected error renewing lock {self.lock_name}: {e}", exc_info=True)
            return False

    def release_lock(self):
        try:
            lock_value = self.redis.get(self.lock_name)
            if lock_value and lock_value == self.lock_id:
                self.redis.delete(self.lock_name)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error releasing lock {self.lock_name}: {e}")
        except Exception as e:
            log.error(f"Unexpected error releasing lock {self.lock_name}: {e}", exc_info=True)


class RedisDict:
    def __init__(self, name, redis_url):
        self.name = name
        # Use connection pool instead of direct connection for better performance
        pool = get_redis_pool(redis_url)
        self.redis = redis.Redis(connection_pool=pool)

    def __setitem__(self, key, value):
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
        try:
            result = self.redis.hdel(self.name, key)
            if result == 0:
                raise KeyError(key)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error deleting {self.name}[{key}]: {e}")
            raise KeyError(key)  # Convert to KeyError for consistency

    def __contains__(self, key):
        try:
            return self.redis.hexists(self.name, key)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error checking {self.name}[{key}]: {e}")
            return False  # Return False on error rather than raising

    def __len__(self):
        try:
            return self.redis.hlen(self.name)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting length of {self.name}: {e}")
            return 0  # Return 0 on error rather than raising

    def keys(self):
        try:
            return self.redis.hkeys(self.name)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting keys of {self.name}: {e}")
            return []  # Return empty list on error

    def values(self):
        try:
            return [json.loads(v) for v in self.redis.hvals(self.name)]
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting values of {self.name}: {e}")
            return []  # Return empty list on error
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error in values() for {self.name}: {e}")
            return []  # Return empty list on decode error

    def items(self):
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
        try:
            self.redis.delete(self.name)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error clearing {self.name}: {e}")
            # Don't raise - clearing is best-effort

    def update(self, other=None, **kwargs):
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
