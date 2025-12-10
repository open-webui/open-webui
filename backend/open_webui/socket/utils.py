import json
import redis
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError
import uuid
import threading
import logging

# Default Redis max connections (used if env import fails or not set)
DEFAULT_REDIS_MAX_CONNECTIONS = 100

try:
    from open_webui.env import REDIS_MAX_CONNECTIONS
except ImportError:
    REDIS_MAX_CONNECTIONS = DEFAULT_REDIS_MAX_CONNECTIONS

# Ensure we have a valid value
if REDIS_MAX_CONNECTIONS is None or not isinstance(REDIS_MAX_CONNECTIONS, int):
    REDIS_MAX_CONNECTIONS = DEFAULT_REDIS_MAX_CONNECTIONS

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
                        max_connections=REDIS_MAX_CONNECTIONS,  # Configurable via REDIS_MAX_CONNECTIONS env var
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
        
        # Make release idempotent: if lock is already marked as released, don't try again
        if not self.lock_obtained:
            log.debug(f"Lock {self.lock_name} already released, skipping release (idempotent)")
            return
        
        # BUG #8 fix: Use Lua script for atomic check-and-delete to prevent race condition
        # BUG #2 fix: Cache script to avoid re-registering on every call
        try:
            # Register script if not already cached
            if self._release_script is None:
                # Lua script for atomic lock release (check lock_id matches before deleting)
                # Returns: 1 = success, 2 = lock already expired/deleted, 0 = lock ID mismatch
                self._release_script = self.redis.register_script("""
                    local lock_name = KEYS[1]
                    local lock_id = ARGV[1]
                    local current_id = redis.call('GET', lock_name)
                    if current_id == lock_id then
                        redis.call('DEL', lock_name)
                        return 1
                    elseif current_id == false then
                        return 2
                    else
                        return 0
                    end
                """)
            result = self._release_script(keys=[self.lock_name], args=[self.lock_id])
            
            # Always mark as released to make subsequent calls idempotent
            self.lock_obtained = False
            
            if result == 1:
                log.debug(f"Successfully released lock {self.lock_name}")
            elif result == 2:
                # Lock already expired/deleted - this is fine, just mark as released
                log.debug(
                    f"Lock {self.lock_name} already expired/deleted when attempting release. "
                    "This is normal if lock expired naturally."
                )
            else:
                # result == 0: Lock ID mismatch
                # This can happen legitimately if:
                # 1. Lock expired and was re-acquired by another process
                # 2. Process took too long and lock was taken over
                log.info(
                    f"Lock {self.lock_name} not released: lock_id mismatch. "
                    "This is expected if the lock expired and was re-acquired by another process."
                )
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
                elif lock_value is None:
                    # Lock already expired/deleted
                    self.lock_obtained = False
                    log.debug(
                        f"Lock {self.lock_name} already expired/deleted when attempting release (fallback). "
                        "This is normal if lock expired naturally."
                    )
                else:
                    # Lock ID mismatch
                    self.lock_obtained = False
                    log.info(
                        f"Lock {self.lock_name} not released: lock_id mismatch (fallback). "
                        "This is expected if the lock expired and was re-acquired by another process."
                    )
            except (ConnectionError, TimeoutError, RedisError) as e:
                log.error(f"Redis error releasing lock {self.lock_name}: {e}", exc_info=True)
                self.lock_obtained = False
            except Exception as e:
                log.error(f"Unexpected error releasing lock {self.lock_name}: {e}", exc_info=True)
                self.lock_obtained = False


class RedisDict:
    def __init__(self, name, redis_url, default_ttl=None):
        self.name = name
        self.default_ttl = default_ttl  # Optional TTL for all keys in this dict
        # BUG #3 fix: Handle errors when creating connection pool
        try:
            # Use connection pool instead of direct connection for better performance
            pool = get_redis_pool(redis_url)
            self.redis = redis.Redis(connection_pool=pool)
            # Cache Lua scripts for atomic operations (faster than re-registering)
            self._atomic_update_script = None
            self._atomic_append_script = None
        except (ValueError, Exception) as e:
            # If pool creation fails, set redis to None and log error
            log.error(
                f"Failed to initialize RedisDict '{name}': {e}. "
                "Dict operations will fail gracefully."
            )
            self.redis = None

    def __setitem__(self, key, value, ttl=None):
        # BUG #3 fix: Check if redis is available
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        try:
            serialized_value = json.dumps(value)
            # Use HSET for fast operation (single round trip)
            self.redis.hset(self.name, key, serialized_value)
            # Set TTL if specified (use default_ttl if ttl not provided)
            expire_ttl = ttl if ttl is not None else self.default_ttl
            if expire_ttl:
                # Expire the entire hash, not individual fields (faster, but less granular)
                # For per-field TTL, would need Redis 7.0+ with HSET ... EX option
                self.redis.expire(self.name, expire_ttl)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error setting {self.name}[{key}]: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error setting {self.name}[{key}]: {e}", exc_info=True)
            raise
    
    def atomic_update_dict(self, key, update_func, default_value=None):
        """
        Atomically update a dictionary value in Redis using optimistic locking.
        Uses WATCH/MULTI/EXEC for true atomicity with retry on conflict.
        
        NOTE: For high-concurrency scenarios, prefer specialized methods like
        atomic_set_dict_field() or atomic_remove_dict_field() which use Lua
        scripts and are faster.
        
        Args:
            key: The hash key to update
            update_func: Function that takes current dict and returns new dict
            default_value: Default value if key doesn't exist (default: {})
        
        Returns:
            The updated dictionary value
        """
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        
        if default_value is None:
            default_value = {}
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use pipeline with WATCH for optimistic locking
                pipe = self.redis.pipeline(True)  # True = transaction mode
                
                # Watch the hash for changes
                pipe.watch(self.name)
                
                # Get current value
                current_json = self.redis.hget(self.name, key)
                if current_json:
                    current = json.loads(current_json)
                else:
                    current = default_value.copy() if isinstance(default_value, dict) else default_value
                
                # Apply update function
                updated = update_func(current)
                
                # Start transaction
                pipe.multi()
                
                # Write updated value
                serialized = json.dumps(updated)
                pipe.hset(self.name, key, serialized)
                
                # Execute - will raise WatchError if key was modified
                pipe.execute()
                
                return updated
            except redis.WatchError:
                # Another client modified the key - retry
                if attempt < max_retries - 1:
                    continue
                log.warning(f"atomic_update_dict failed after {max_retries} retries for {self.name}[{key}]")
                raise
            except Exception as e:
                log.error(f"Error in atomic_update_dict for {self.name}[{key}]: {e}", exc_info=True)
                raise
            finally:
                pipe.reset()
    
    def atomic_set_dict_field(self, key, field, value):
        """
        Atomically set a field in a dictionary stored in Redis hash.
        Single Lua script = single round trip, truly atomic.
        
        Use this for operations like: USAGE_POOL[model_id][sid] = {"updated_at": time}
        
        Args:
            key: The hash key (e.g., model_id)
            field: The field within the dict (e.g., sid)
            value: The value to set (will be JSON serialized)
        
        Returns:
            The updated dictionary
        """
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        
        # Register script if not cached
        if not hasattr(self, '_atomic_set_field_script') or self._atomic_set_field_script is None:
            self._atomic_set_field_script = self.redis.register_script("""
                local hash_name = KEYS[1]
                local key = ARGV[1]
                local field = ARGV[2]
                local value_json = ARGV[3]
                
                local current_json = redis.call('HGET', hash_name, key)
                local current = {}
                if current_json then
                    local success, decoded = pcall(cjson.decode, current_json)
                    if success and type(decoded) == 'table' then
                        current = decoded
                    end
                end
                
                -- Decode value and set field
                local value = cjson.decode(value_json)
                current[field] = value
                
                -- Write back
                redis.call('HSET', hash_name, key, cjson.encode(current))
                return cjson.encode(current)
            """)
        
        try:
            result_json = self._atomic_set_field_script(
                keys=[self.name],
                args=[key, field, json.dumps(value)]
            )
            return json.loads(result_json)
        except Exception as e:
            log.error(f"Error in atomic_set_dict_field for {self.name}[{key}][{field}]: {e}", exc_info=True)
            raise
    
    def atomic_remove_dict_fields(self, key, fields_to_remove):
        """
        Atomically remove multiple fields from a dictionary stored in Redis hash.
        Single Lua script = single round trip, truly atomic.
        
        Use this for operations like: removing expired sids from USAGE_POOL[model_id]
        
        Args:
            key: The hash key (e.g., model_id)
            fields_to_remove: List of fields to remove (e.g., [sid1, sid2])
        
        Returns:
            The updated dictionary, or None if dictionary became empty
        """
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        
        if not fields_to_remove:
            return self.get(key, {})
        
        # Register script if not cached
        if not hasattr(self, '_atomic_remove_fields_script') or self._atomic_remove_fields_script is None:
            self._atomic_remove_fields_script = self.redis.register_script("""
                local hash_name = KEYS[1]
                local key = ARGV[1]
                local fields_json = ARGV[2]
                
                local current_json = redis.call('HGET', hash_name, key)
                if not current_json then
                    return nil
                end
                
                local success, current = pcall(cjson.decode, current_json)
                if not success or type(current) ~= 'table' then
                    return nil
                end
                
                -- Decode fields to remove
                local fields = cjson.decode(fields_json)
                for _, field in ipairs(fields) do
                    current[field] = nil
                end
                
                -- Check if empty
                local is_empty = true
                for _ in pairs(current) do
                    is_empty = false
                    break
                end
                
                if is_empty then
                    redis.call('HDEL', hash_name, key)
                    return nil
                else
                    redis.call('HSET', hash_name, key, cjson.encode(current))
                    return cjson.encode(current)
                end
            """)
        
        try:
            result_json = self._atomic_remove_fields_script(
                keys=[self.name],
                args=[key, json.dumps(fields_to_remove)]
            )
            if result_json is None:
                return None
            return json.loads(result_json)
        except Exception as e:
            log.error(f"Error in atomic_remove_dict_fields for {self.name}[{key}]: {e}", exc_info=True)
            raise
    
    def atomic_remove_from_list(self, key, item_to_remove):
        """
        Atomically remove an item from a list stored in Redis hash.
        Single Lua script = single round trip, truly atomic.
        
        Use this for operations like: removing a sid from USER_POOL[user_id]
        
        Args:
            key: The hash key (e.g., user_id)
            item_to_remove: Item to remove from the list
        
        Returns:
            The updated list, or None if list became empty (key will be deleted)
        """
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        
        # Register script if not cached
        if not hasattr(self, '_atomic_remove_item_script') or self._atomic_remove_item_script is None:
            self._atomic_remove_item_script = self.redis.register_script("""
                local hash_name = KEYS[1]
                local key = ARGV[1]
                local item_to_remove = ARGV[2]
                
                local current_json = redis.call('HGET', hash_name, key)
                if not current_json then
                    return nil
                end
                
                local success, current = pcall(cjson.decode, current_json)
                if not success or type(current) ~= 'table' then
                    return nil
                end
                
                -- Remove item from list
                local new_list = {}
                for _, item in ipairs(current) do
                    if item ~= item_to_remove then
                        table.insert(new_list, item)
                    end
                end
                
                -- Check if empty
                if #new_list == 0 then
                    redis.call('HDEL', hash_name, key)
                    return nil
                else
                    redis.call('HSET', hash_name, key, cjson.encode(new_list))
                    return cjson.encode(new_list)
                end
            """)
        
        try:
            result_json = self._atomic_remove_item_script(
                keys=[self.name],
                args=[key, item_to_remove]
            )
            if result_json is None:
                return None
            return json.loads(result_json)
        except Exception as e:
            log.error(f"Error in atomic_remove_from_list for {self.name}[{key}]: {e}", exc_info=True)
            raise
    
    def atomic_append_to_list(self, key, item, max_length=None):
        """
        Atomically append an item to a list stored in Redis.
        Fast single-round-trip operation using Lua script (optimized for speed).
        
        Args:
            key: The hash key containing the list
            item: Item to append (will be JSON serialized and stored in list)
            max_length: Optional max list length (removes oldest if exceeded)
        
        Returns:
            The updated list (parsed from JSON)
        """
        if self.redis is None:
            raise ConnectionError(f"Redis connection not available for {self.name}")
        
        # Register script if not cached (cached for performance - no re-registration overhead)
        if self._atomic_append_script is None:
            self._atomic_append_script = self.redis.register_script("""
                local hash_name = KEYS[1]
                local key = ARGV[1]
                local item_json = ARGV[2]
                local max_len = tonumber(ARGV[3]) or 0
                
                local current_json = redis.call('HGET', hash_name, key)
                local current = {}
                if current_json then
                    current = cjson.decode(current_json)
                end
                
                -- Ensure it's a list/array (Lua tables can be arrays or objects)
                -- Check if it's an array (has numeric indices starting from 1)
                if type(current) ~= 'table' or (current[1] == nil and next(current) ~= nil) then
                    current = {}
                end
                
                -- Parse item_json to get actual value, then append
                local item_value = cjson.decode(item_json)
                table.insert(current, item_value)
                
                -- Trim if max_length specified (remove oldest first)
                if max_len > 0 and #current > max_len then
                    local remove_count = #current - max_len
                    for i = 1, remove_count do
                        table.remove(current, 1)
                    end
                end
                
                -- Write back atomically (single operation)
                redis.call('HSET', hash_name, key, cjson.encode(current))
                return cjson.encode(current)
            """)
        
        try:
            # Fast single round trip - script is cached, no re-registration overhead
            result_json = self._atomic_append_script(
                keys=[self.name],
                args=[key, json.dumps(item), str(max_length) if max_length else "0"]
            )
            # Parse result - items are already decoded in Lua, so just parse the array
            return json.loads(result_json)
        except Exception as e:
            log.error(f"Error in atomic_append_to_list for {self.name}[{key}]: {e}", exc_info=True)
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
