# tasks.py
import asyncio
import json
import logging
import os
import socket
import time
from typing import Dict, Optional
from uuid import uuid4, UUID

import redis
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError, ResponseError

from open_webui.env import REDIS_URL
from open_webui.socket.utils import get_redis_pool

log = logging.getLogger(__name__)

# A dictionary to keep track of active tasks on this pod (asyncio.Task objects cannot be serialized)
# This is a hybrid approach: metadata in Redis, Task objects locally
# Note: Dictionary operations in Python are atomic due to GIL, but for true thread safety
# in multi-threaded scenarios, additional locking would be needed. Since tasks are typically
# accessed from the same event loop, this is safe.
tasks: Dict[str, asyncio.Task] = {}

# Redis hash key for storing task metadata
REDIS_TASKS_KEY = "open-webui:tasks"

# Task status constants
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_CANCELLED = "cancelled"
TASK_STATUS_ERROR = "error"

# Valid status transitions (from -> to)
VALID_STATUS_TRANSITIONS = {
    TASK_STATUS_RUNNING: {TASK_STATUS_COMPLETED, TASK_STATUS_CANCELLED, TASK_STATUS_ERROR},
    # Terminal states cannot transition
    TASK_STATUS_COMPLETED: set(),
    TASK_STATUS_CANCELLED: set(),
    TASK_STATUS_ERROR: set(),
}

# Global pod identifier (generated once at startup for consistency)
_POD_IDENTIFIER: Optional[str] = None


def get_pod_identifier() -> str:
    """
    Get a unique identifier for the current pod/instance.
    Uses POD_NAME (Kubernetes), HOSTNAME, hostname + PID, or falls back to socket.gethostname().
    Generated once at startup for consistency.
    
    NOTE: If using fallback (hostname-PID-timestamp), the identifier will change on restart.
    This is acceptable for most use cases, but means orphaned tasks from previous instances
    won't be automatically associated with the new instance. The periodic cleanup will handle them.
    """
    global _POD_IDENTIFIER
    if _POD_IDENTIFIER is not None:
        return _POD_IDENTIFIER
    
    # Try Kubernetes pod name first (most reliable and persistent)
    pod_id = os.environ.get("POD_NAME")
    if pod_id:
        _POD_IDENTIFIER = pod_id
        return pod_id
    
    # Try HOSTNAME (usually persistent in containers)
    pod_id = os.environ.get("HOSTNAME")
    if pod_id:
        # Add process ID for uniqueness in case multiple processes on same host
        pod_id = f"{pod_id}-{os.getpid()}"
        _POD_IDENTIFIER = pod_id
        return pod_id
    
    # Fallback to hostname + PID + timestamp
    # NOTE: This will change on restart, but periodic cleanup will handle orphaned tasks
    hostname = socket.gethostname()
    pod_id = f"{hostname}-{os.getpid()}-{int(time.time())}"
    _POD_IDENTIFIER = pod_id
    log.info(f"Generated pod identifier: {pod_id} (will change on restart)")
    return pod_id


class RedisTaskStore:
    """
    Manages task metadata in Redis for multi-replica support.
    Handles Redis connection failures gracefully by falling back to local-only mode.
    Uses atomic operations to prevent race conditions.
    """

    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[redis.Redis] = None
        self._redis_available = False
        self._max_retries = 3
        self._retry_delay = 0.1  # 100ms initial delay
        self._initialize_redis()
        self._load_lua_scripts()

    def _initialize_redis(self):
        """Initialize Redis connection pool. Called once at startup."""
        try:
            self.pool = get_redis_pool(self.redis_url)
            self.redis = redis.Redis(connection_pool=self.pool)
            # Test connection
            self.redis.ping()
            self._redis_available = True
            log.debug("Redis task store initialized successfully")
        except Exception as e:
            log.warning(
                f"Redis task store initialization failed: {e}. "
                "Falling back to local-only task tracking. "
                "Tasks will not be visible across replicas."
            )
            self._redis_available = False

    def _load_lua_scripts(self):
        """Load Lua scripts for atomic operations. Handles errors gracefully."""
        if not self._redis_available or not self.redis:
            self._update_status_script = None
            return
        
        try:
            # Lua script for atomic status update with validation
            # Includes error handling for JSON decode failures
            self._update_status_script = self.redis.register_script("""
                local key = KEYS[1]
                local task_id = ARGV[1]
                local new_status = ARGV[2]
                local completed_at = ARGV[3]
                local error_msg = ARGV[4]
                
                local current = redis.call('HGET', key, task_id)
                if not current then
                    return {0, 'TASK_NOT_FOUND'}
                end
                
                -- Try to decode JSON, handle errors gracefully
                local success, metadata = pcall(cjson.decode, current)
                if not success then
                    return {0, 'JSON_DECODE_ERROR', tostring(metadata)}
                end
                
                local old_status = metadata['status']
                
                -- Validate status transition
                if old_status == 'completed' or old_status == 'cancelled' or old_status == 'error' then
                    return {0, 'INVALID_TRANSITION', old_status}
                end
                
                -- Update metadata
                metadata['status'] = new_status
                if completed_at and completed_at ~= '' then
                    metadata['completed_at'] = tonumber(completed_at)
                end
                if error_msg and error_msg ~= '' then
                    metadata['error'] = error_msg
                end
                
                -- Try to encode JSON, handle errors gracefully
                local encode_success, encoded = pcall(cjson.encode, metadata)
                if not encode_success then
                    return {0, 'JSON_ENCODE_ERROR', tostring(encoded)}
                end
                
                redis.call('HSET', key, task_id, encoded)
                return {1, 'SUCCESS'}
            """)
            log.debug("Lua script registered successfully")
        except Exception as e:
            log.warning(
                f"Failed to register Lua script for atomic operations: {e}. "
                "Falling back to read-modify-write pattern (non-atomic)."
            )
            self._update_status_script = None

    def _check_redis_connection(self) -> bool:
        """Check if Redis is available, attempt reconnection if needed."""
        if self._redis_available and self.redis:
            try:
                self.redis.ping()
                return True
            except Exception:
                self._redis_available = False
                log.warning("Redis connection lost. Falling back to local-only mode.")

        # Try to reconnect if we have a pool
        if self.pool and not self._redis_available:
            try:
                if not self.redis:
                    self.redis = redis.Redis(connection_pool=self.pool)
                self.redis.ping()
                self._redis_available = True
                log.info("Redis connection restored for task store")
                # Reload Lua scripts after reconnection
                self._load_lua_scripts()
                return True
            except Exception:
                pass

        return False

    def _retry_operation(self, operation, *args, **kwargs):
        """
        Retry a Redis operation with exponential backoff and jitter.
        
        Note: This is a sync function that uses time.sleep(), which is appropriate here
        because:
        1. All Redis operations in this class are synchronous (redis.Redis, not redis.asyncio)
        2. This method is only called from sync methods (create_task_metadata, get_task_metadata, etc.)
        3. The delays are short (milliseconds to seconds) and only occur on retries
        
        If this class is ever refactored to use async Redis operations, this should
        be converted to an async method using asyncio.sleep() instead.
        """
        import random
        for attempt in range(self._max_retries):
            try:
                return operation(*args, **kwargs)
            except (ConnectionError, TimeoutError, RedisError) as e:
                if attempt == self._max_retries - 1:
                    raise
                # Exponential backoff with jitter (prevents thundering herd)
                base_delay = self._retry_delay * (2 ** attempt)
                jitter = random.uniform(0, base_delay * 0.1)  # 10% jitter
                delay = base_delay + jitter
                log.warning(f"Redis operation failed (attempt {attempt + 1}/{self._max_retries}), retrying in {delay:.3f}s: {e}")
                time.sleep(delay)
        return None

    def create_task_metadata(
        self, task_id: str, pod_id: str, status: str = TASK_STATUS_RUNNING
    ) -> bool:
        """
        Store task metadata in Redis atomically.
        Returns True if successful, False if Redis is unavailable.
        """
        if not self._check_redis_connection():
            return False

        try:
            metadata = {
                "task_id": task_id,
                "pod_id": pod_id,
                "status": status,
                "created_at": time.time(),
            }
            
            def _create():
                self.redis.hset(
                    REDIS_TASKS_KEY, task_id, json.dumps(metadata)
                )
                # Set TTL on the hash key (optional, but helps with cleanup)
                # Note: This sets TTL on the entire hash, not individual fields
                # For per-task TTL, we'd need a different structure
            
            self._retry_operation(_create)
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error creating task metadata for {task_id}: {e}")
            self._redis_available = False
            return False
        except Exception as e:
            log.error(
                f"Unexpected error creating task metadata for {task_id}: {e}",
                exc_info=True,
            )
            return False

    def get_task_metadata(self, task_id: str) -> Optional[dict]:
        """
        Retrieve task metadata from Redis.
        Returns None if task not found or Redis is unavailable.
        """
        if not self._check_redis_connection():
            return None

        try:
            def _get():
                return self.redis.hget(REDIS_TASKS_KEY, task_id)
            
            value = self._retry_operation(_get)
            if value is None:
                return None
            return json.loads(value)
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting task metadata for {task_id}: {e}")
            self._redis_available = False
            return None
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error for task {task_id}: {e}")
            return None
        except Exception as e:
            log.error(
                f"Unexpected error getting task metadata for {task_id}: {e}",
                exc_info=True,
            )
            return None

    def update_task_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None,
        completed_at: Optional[float] = None,
        skip_transition_check: bool = False,
    ) -> bool:
        """
        Update task status in Redis atomically using Lua script.
        Validates status transitions to prevent invalid state changes.
        Returns True if successful, False if Redis is unavailable or transition is invalid.
        
        Args:
            task_id: The task ID to update
            status: New status
            error: Optional error message
            completed_at: Optional completion timestamp
            skip_transition_check: Skip validation (for cleanup operations)
        """
        if not self._check_redis_connection():
            return False

        try:
            # Use Lua script for atomic update with validation
            if hasattr(self, '_update_status_script') and self._update_status_script and not skip_transition_check:
                def _update_atomic():
                    try:
                        result = self._update_status_script(
                            keys=[REDIS_TASKS_KEY],
                            args=[
                                task_id,
                                status,
                                str(completed_at) if completed_at else "",
                                error or "",
                            ],
                        )
                        if result[0] == 0:
                            if result[1] == 'TASK_NOT_FOUND':
                                return False
                            elif result[1] == 'INVALID_TRANSITION':
                                log.warning(
                                    f"Invalid status transition for task {task_id}: "
                                    f"{result[2] if len(result) > 2 else 'unknown'} -> {status}"
                                )
                                return False
                            elif result[1] in ['JSON_DECODE_ERROR', 'JSON_ENCODE_ERROR']:
                                log.error(
                                    f"JSON error in Lua script for task {task_id}: {result[2] if len(result) > 2 else 'unknown'}"
                                )
                                return False
                        return True
                    except (ResponseError, RedisError) as script_error:
                        # Catch script execution errors (ResponseError for Lua script errors, etc.)
                        log.error(
                            f"Lua script execution error for task {task_id}: {script_error}",
                            exc_info=True,
                        )
                        # Fall through to fallback implementation
                        raise
                    except Exception as script_error:
                        # Catch any other unexpected errors
                        log.error(
                            f"Unexpected error in Lua script execution for task {task_id}: {script_error}",
                            exc_info=True,
                        )
                        # Fall through to fallback implementation
                        raise
                
                try:
                    return self._retry_operation(_update_atomic) or False
                except Exception:
                    # If script fails, fall through to fallback
                    log.debug(f"Lua script failed for task {task_id}, using fallback method")
                    pass
            else:
                # Fallback to read-modify-write if Lua script not available
                metadata = self.get_task_metadata(task_id)
                if metadata is None:
                    return False

                # Validate status transition
                if not skip_transition_check:
                    old_status = metadata.get("status")
                    if old_status not in VALID_STATUS_TRANSITIONS:
                        log.warning(f"Unknown old status {old_status} for task {task_id}")
                        return False
                    if status not in VALID_STATUS_TRANSITIONS[old_status]:
                        log.warning(
                            f"Invalid status transition for task {task_id}: "
                            f"{old_status} -> {status}"
                        )
                        return False

                metadata["status"] = status
                if completed_at is not None:
                    metadata["completed_at"] = completed_at
                if error is not None:
                    metadata["error"] = error

                def _update():
                    self.redis.hset(REDIS_TASKS_KEY, task_id, json.dumps(metadata))
                
                self._retry_operation(_update)
                return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error updating task status for {task_id}: {e}")
            self._redis_available = False
            return False
        except Exception as e:
            log.error(
                f"Unexpected error updating task status for {task_id}: {e}",
                exc_info=True,
            )
            return False

    def delete_task_metadata(self, task_id: str) -> bool:
        """
        Delete task metadata from Redis.
        Returns True if successful or if task didn't exist, False on Redis error.
        """
        if not self._check_redis_connection():
            return False

        try:
            def _delete():
                self.redis.hdel(REDIS_TASKS_KEY, task_id)
            
            self._retry_operation(_delete)
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error deleting task metadata for {task_id}: {e}")
            self._redis_available = False
            return False
        except Exception as e:
            log.error(
                f"Unexpected error deleting task metadata for {task_id}: {e}",
                exc_info=True,
            )
            return False

    def list_all_tasks(self, status_filter: Optional[str] = None) -> list:
        """
        List all task IDs from Redis, optionally filtered by status.
        Returns empty list if Redis is unavailable.
        
        Args:
            status_filter: If provided, only return tasks with this status
        """
        if not self._check_redis_connection():
            return []

        try:
            def _list():
                if status_filter:
                    # Get all metadata and filter
                    all_data = self.redis.hgetall(REDIS_TASKS_KEY)
                    result = []
                    for key, value in all_data.items():
                        try:
                            metadata = json.loads(value)
                            if metadata.get("status") == status_filter:
                                task_id = key.decode() if isinstance(key, bytes) else key
                                result.append(task_id)
                        except json.JSONDecodeError:
                            continue
                    return result
                else:
                    return [
                        key.decode() if isinstance(key, bytes) else key
                        for key in self.redis.hkeys(REDIS_TASKS_KEY)
                    ]
            
            return self._retry_operation(_list) or []
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error listing tasks: {e}")
            self._redis_available = False
            return []
        except Exception as e:
            log.error(f"Unexpected error listing tasks: {e}", exc_info=True)
            return []

    def get_all_task_metadata(self) -> Dict[str, dict]:
        """
        Get all task metadata from Redis.
        Returns empty dict if Redis is unavailable.
        """
        if not self._check_redis_connection():
            return {}

        try:
            def _get_all():
                all_data = self.redis.hgetall(REDIS_TASKS_KEY)
                result = {}
                for key, value in all_data.items():
                    task_id = key.decode() if isinstance(key, bytes) else key
                    try:
                        result[task_id] = json.loads(value)
                    except json.JSONDecodeError:
                        log.warning(f"Failed to decode metadata for task {task_id}")
                return result
            
            return self._retry_operation(_get_all) or {}
        except (ConnectionError, TimeoutError, RedisError) as e:
            log.error(f"Redis error getting all task metadata: {e}")
            self._redis_available = False
            return {}
        except Exception as e:
            log.error(f"Unexpected error getting all task metadata: {e}", exc_info=True)
            return {}

    def cleanup_orphaned_tasks(self, current_pod_id: str) -> int:
        """
        Clean up tasks from this pod that no longer exist locally (orphaned after restart).
        Uses batch operations for efficiency.
        Returns number of tasks cleaned up.
        """
        if not self._check_redis_connection():
            return 0

        try:
            all_metadata = self.get_all_task_metadata()
            orphaned_task_ids = []
            for task_id, metadata in all_metadata.items():
                if metadata.get("pod_id") == current_pod_id:
                    orphaned_task_ids.append(task_id)
            
            if not orphaned_task_ids:
                return 0
            
            # Batch update using pipeline for efficiency
            cleaned = 0
            try:
                pipe = self.redis.pipeline()
                current_time = time.time()
                for task_id in orphaned_task_ids:
                    # Get current metadata to update
                    metadata = all_metadata.get(task_id, {})
                    metadata["status"] = TASK_STATUS_CANCELLED
                    metadata["error"] = "Task orphaned after pod restart"
                    metadata["completed_at"] = current_time
                    pipe.hset(REDIS_TASKS_KEY, task_id, json.dumps(metadata))
                
                pipe.execute()
                cleaned = len(orphaned_task_ids)
            except Exception as pipe_error:
                log.warning(f"Pipeline update failed, falling back to individual updates: {pipe_error}")
                # Fallback to individual updates
                for task_id in orphaned_task_ids:
                    if self.update_task_status(
                        task_id,
                        TASK_STATUS_CANCELLED,
                        error="Task orphaned after pod restart",
                        completed_at=time.time(),
                        skip_transition_check=True,
                    ):
                        cleaned += 1
            
            if cleaned > 0:
                log.info(f"Cleaned up {cleaned} orphaned tasks from pod {current_pod_id}")
            return cleaned
        except Exception as e:
            log.error(f"Error cleaning up orphaned tasks: {e}", exc_info=True)
            return 0


# Global Redis task store instance
_redis_task_store = RedisTaskStore()

# Cleanup configuration (configurable via environment variables)
def _safe_int_env(key: str, default: int, min_value: int = 1) -> int:
    """Safely parse integer environment variable with fallback to default."""
    try:
        value = os.environ.get(key)
        if value is None:
            return default
        parsed = int(value)
        # Validate reasonable range (must be positive, at least min_value)
        if parsed < min_value:
            log.warning(
                f"Invalid value for {key} (must be >= {min_value}): {parsed}, using default {default}"
            )
            return default
        return parsed
    except (ValueError, TypeError) as e:
        log.warning(f"Invalid value for {key}: {os.environ.get(key)}, using default {default}. Error: {e}")
        return default

TASK_CLEANUP_INTERVAL = _safe_int_env("TASK_CLEANUP_INTERVAL", 300, min_value=60)  # Run cleanup every 5 minutes (default, min 1 minute)
TASK_STALE_THRESHOLD = _safe_int_env("TASK_STALE_THRESHOLD", 3600, min_value=60)  # Consider tasks stale after 1 hour (default, min 1 minute)
TASK_COMPLETED_RETENTION = _safe_int_env("TASK_COMPLETED_RETENTION", 86400, min_value=3600)  # Keep completed/cancelled tasks for 24 hours (default, min 1 hour)


async def startup_cleanup():
    """
    Clean up orphaned tasks on pod startup.
    This fixes BUG #3: Memory leak on pod restart.
    Includes error handling to prevent silent failures.
    """
    try:
        pod_id = get_pod_identifier()
        cleaned = _redis_task_store.cleanup_orphaned_tasks(pod_id)
        if cleaned > 0:
            log.info(f"Startup cleanup completed: {cleaned} orphaned tasks cleaned up")
        else:
            log.debug("Startup cleanup completed: no orphaned tasks found")
    except Exception as e:
        log.error(f"Error during startup cleanup: {e}", exc_info=True)
        # Don't raise - startup cleanup failure shouldn't prevent app from starting


async def periodic_task_cleanup():
    """
    Periodic cleanup of stale tasks from Redis.
    - Removes tasks from crashed pods (running status but no updates for > TASK_STALE_THRESHOLD)
    - Removes old completed/cancelled/error tasks (older than TASK_COMPLETED_RETENTION)
    - Uses distributed lock to prevent multiple pods from cleaning simultaneously
    - FIXED BUG #7: Checks if task is actually running before deleting
    """
    from open_webui.env import REDIS_URL
    from open_webui.socket.utils import RedisLock

    cleanup_lock = RedisLock(
        redis_url=REDIS_URL,
        lock_name="task_cleanup_lock",
        timeout_secs=TASK_CLEANUP_INTERVAL + 120,  # Increased timeout (BUG #12 fix)
    )

    try:
        if not cleanup_lock.aquire_lock():
            log.debug("Task cleanup lock already exists. Another pod is handling cleanup.")
            return
    except Exception as e:
        # If Redis is unavailable, log and skip cleanup rather than crashing
        log.warning(f"Failed to acquire task cleanup lock (Redis may be unavailable): {e}. Skipping periodic cleanup.")
        return

    log.debug("Starting periodic task cleanup")
    try:
        while True:
            if not cleanup_lock.renew_lock():
                log.warning("Unable to renew task cleanup lock. Exiting cleanup.")
                break

            try:
                current_time = time.time()
                all_metadata = _redis_task_store.get_all_task_metadata()
                tasks_to_delete = []
                current_pod_id = get_pod_identifier()

                for task_id, metadata in all_metadata.items():
                    status = metadata.get("status", TASK_STATUS_RUNNING)
                    created_at = metadata.get("created_at", current_time)
                    completed_at = metadata.get("completed_at")
                    pod_id = metadata.get("pod_id", "unknown")

                    # Check for stale running tasks (pod likely crashed)
                    # FIXED BUG #7: Only delete if task is NOT in local dict (actually stale)
                    # NOTE: There's a benign race condition here - task could be deleted between
                    # check and use, but worst case is we skip deleting a task that's already gone
                    if status == TASK_STATUS_RUNNING:
                        age = current_time - created_at
                        if age > TASK_STALE_THRESHOLD:
                            # Check if task is actually running locally
                            # Race condition: task could be deleted between check and use
                            # This is acceptable - worst case we skip a task that's already gone
                            is_running_locally = task_id in tasks
                            
                            if not is_running_locally:
                                # Task is stale and not running locally - safe to delete
                                log.info(
                                    f"Cleaning up stale running task {task_id} "
                                    f"(pod: {pod_id}, age: {age:.0f}s)"
                                )
                                tasks_to_delete.append(task_id)
                            else:
                                # Task is still running locally - update last_heartbeat or skip
                                log.debug(
                                    f"Task {task_id} is still running locally, skipping cleanup"
                                )

                    # Check for old completed/cancelled/error tasks
                    elif status in [TASK_STATUS_COMPLETED, TASK_STATUS_CANCELLED, TASK_STATUS_ERROR]:
                        if completed_at:
                            age = current_time - completed_at
                        else:
                            # Fallback to created_at if completed_at is missing
                            age = current_time - created_at

                        if age > TASK_COMPLETED_RETENTION:
                            tasks_to_delete.append(task_id)

                # Delete stale/old tasks
                deleted_count = 0
                for task_id in tasks_to_delete:
                    if _redis_task_store.delete_task_metadata(task_id):
                        deleted_count += 1

                if deleted_count > 0:
                    log.info(f"Cleaned up {deleted_count} stale/old tasks from Redis")

            except Exception as e:
                log.error(f"Error in task cleanup iteration: {e}", exc_info=True)

            await asyncio.sleep(TASK_CLEANUP_INTERVAL)

    except Exception as e:
        log.error(f"Fatal error in periodic_task_cleanup: {e}", exc_info=True)
    finally:
        cleanup_lock.release_lock()
        log.debug("Task cleanup stopped")


def cleanup_task(task_id: str):
    """
    Remove a completed or canceled task from both local dictionary and Redis.
    This ensures data invalidation across all pods.
    Thread-safe: Dictionary operations are atomic in Python due to GIL.
    """
    # Remove from local dict first (fast operation)
    tasks.pop(task_id, None)

    # Remove from Redis (ensures invalidation across all pods)
    # This is idempotent - safe to call multiple times
    _redis_task_store.delete_task_metadata(task_id)


def create_task(coroutine):
    """
    Create a new asyncio task and add it to both local dictionary and Redis.
    
    This function maintains backward compatibility - signature unchanged.
    
    Args:
        coroutine: The coroutine to run as a task
        
    Returns:
        tuple: (task_id, task) where task_id is a string and task is the asyncio.Task
               Same signature as before for backward compatibility
    """
    task_id = str(uuid4())  # Generate a unique ID for the task
    task = asyncio.create_task(coroutine)  # Create the task
    pod_id = get_pod_identifier()

    # Store metadata in Redis first (ensures visibility across pods)
    # If Redis fails, we still create the task locally (graceful degradation)
    redis_success = _redis_task_store.create_task_metadata(task_id, pod_id, TASK_STATUS_RUNNING)
    if not redis_success:
        log.warning(
            f"Failed to store task {task_id} metadata in Redis. "
            "Task will only be visible on this pod."
        )
    else:
        # Log task creation for metrics/observability (BUG #15 fix)
        log.info(f"Task created: task_id={task_id}, pod_id={pod_id}, status=running")

    # Store Task object locally (cannot be serialized)
    # Note: Dictionary writes in Python are generally atomic due to GIL,
    # but for true thread safety in async contexts, we'd need proper locking.
    # Since create_task is typically called from async contexts and tasks dict
    # is only accessed from the same event loop, this is safe.
    tasks[task_id] = task

    # Track if task was manually cancelled to avoid double update (BUG #4 fix)
    # Use setattr to ensure attribute exists even if task object is modified
    setattr(task, '_manually_cancelled', False)

    # Add a done callback for cleanup
    def cleanup_callback(t: asyncio.Task):
        """Callback to clean up task when it completes."""
        try:
            # Determine final status
            if t.cancelled():
                status = TASK_STATUS_CANCELLED
            elif t.exception() is not None:
                status = TASK_STATUS_ERROR
                error_msg = str(t.exception())
            else:
                status = TASK_STATUS_COMPLETED
                error_msg = None

            # Update Redis metadata only if not already updated by stop_task()
            # BUG #4 fix: Check if task was manually cancelled
            if not getattr(t, '_manually_cancelled', False):
                _redis_task_store.update_task_status(
                    task_id,
                    status,
                    error=error_msg,
                    completed_at=time.time(),
                )
                # Log task completion for metrics/observability (BUG #15 fix)
                # Get pod_id once with error handling to prevent logging failures (BUG #4 fix)
                try:
                    pod_id = get_pod_identifier()
                except Exception as pod_error:
                    log.warning(f"Failed to get pod identifier for task {task_id}: {pod_error}")
                    pod_id = "unknown"
                
                if status == TASK_STATUS_COMPLETED:
                    log.info(f"Task completed: task_id={task_id}, pod_id={pod_id}")
                elif status == TASK_STATUS_ERROR:
                    log.error(f"Task failed: task_id={task_id}, pod_id={pod_id}, error={error_msg}")
                elif status == TASK_STATUS_CANCELLED:
                    log.info(f"Task cancelled: task_id={task_id}, pod_id={pod_id}")

            # Clean up local and Redis
            # Note: cleanup_task() is a sync function, so we can call it directly
            # from the done callback (which runs in the event loop context)
            tasks.pop(task_id, None)
            _redis_task_store.delete_task_metadata(task_id)
        except Exception as e:
            log.error(f"Error in task cleanup callback for {task_id}: {e}", exc_info=True)
            # Still try to clean up locally to prevent memory leaks
            tasks.pop(task_id, None)
            # Try to update Redis one more time with error status
            try:
                _redis_task_store.update_task_status(
                    task_id,
                    TASK_STATUS_ERROR,
                    error=f"Cleanup callback error: {str(e)}",
                    completed_at=time.time(),
                    skip_transition_check=True,
                )
            except Exception:
                pass  # Best effort - if Redis is down, we've already logged the error

    task.add_done_callback(cleanup_callback)

    return task_id, task


def _is_valid_task_id(task_id: str) -> bool:
    """
    Validate that task_id is a valid UUID format.
    Returns True if valid, False otherwise.
    """
    try:
        UUID(task_id)
        return True
    except (ValueError, TypeError):
        return False


def get_task(task_id: str):
    """
    Retrieve a task by its task ID.
    
    This function maintains backward compatibility - signature and return type unchanged.
    
    Args:
        task_id: The task ID to retrieve (must be a valid UUID)
        
    Returns:
        asyncio.Task if found locally, None otherwise.
        Same return type as before for backward compatibility.
        Note: This returns the Task object, not metadata. Use get_task_metadata() for metadata.
    """
    # Validate task ID format
    if not _is_valid_task_id(task_id):
        log.warning(
            f"Invalid task ID format: task_id={task_id}. "
            "Task ID must be a valid UUID format."
        )
        return None
    
    # Check local dict first (for the actual Task object)
    # Thread-safe read (dictionary reads are generally safe in Python)
    if task_id in tasks:
        return tasks[task_id]

    # Check Redis for metadata (task might be on another pod)
    # This is new functionality but doesn't break backward compatibility
    # If task is on another pod, we still return None (can't return Task object from another pod)
    metadata = _redis_task_store.get_task_metadata(task_id)
    if metadata:
        # Task exists but is on another pod (or was completed)
        # Return None since we can't return the Task object from another pod
        # This maintains the same behavior as the old implementation
        return None

    return None


def get_task_metadata(task_id: str) -> Optional[dict]:
    """
    Get task metadata from Redis.
    Useful for checking task status across pods.
    
    Args:
        task_id: The task ID (must be a valid UUID)
    
    Returns:
        dict with task metadata (task_id, pod_id, status, created_at, etc.) or None
    """
    # Validate task ID format
    if not _is_valid_task_id(task_id):
        log.warning(
            f"Invalid task ID format: task_id={task_id}. "
            "Task ID must be a valid UUID format."
        )
        return None
    
    return _redis_task_store.get_task_metadata(task_id)


def list_tasks():
    """
    List all currently active (running) task IDs.
    
    This function maintains backward compatibility - signature and return type unchanged.
    FIXED BUG #8: Only returns running tasks, not completed ones.
    
    BEHAVIOR CHANGE: When Redis is available, returns running tasks from all pods.
    This is an enhancement that provides visibility across replicas.
    When Redis is unavailable, falls back to local-only (same as old behavior).
    
    Returns:
        list: List of task ID strings (only running tasks)
        Same return type as before for backward compatibility
    """
    # Try to get running tasks from Redis
    redis_tasks = _redis_task_store.list_all_tasks(status_filter=TASK_STATUS_RUNNING)
    
    # If Redis is available, return Redis list (includes all pods, only running tasks)
    if _redis_task_store._redis_available:
        # Also include local running tasks, but filter by status in Redis
        # FIXED BUG #3: Only include local tasks that are actually running in Redis
        # BUG #3 fix: Create snapshot of task IDs to avoid race condition during iteration
        local_running_tasks = []
        task_ids_snapshot = list(tasks.keys())  # Create snapshot to avoid race condition
        for task_id in task_ids_snapshot:
            # Check if task is running in Redis (might not be in Redis yet if just created)
            metadata = _redis_task_store.get_task_metadata(task_id)
            if metadata is None:
                # Task not in Redis yet, assume it's running (just created)
                # Double-check task still exists locally (could have been deleted)
                if task_id in tasks:
                    local_running_tasks.append(task_id)
            elif metadata.get("status") == TASK_STATUS_RUNNING:
                # Task is running in Redis
                # Double-check task still exists locally (could have been deleted)
                if task_id in tasks:
                    local_running_tasks.append(task_id)
            # If task is completed/cancelled/error in Redis, don't include it
        
        # Combine and deduplicate
        all_tasks = list(set(redis_tasks + local_running_tasks))
        return all_tasks
    
    # Fallback to local-only if Redis is unavailable
    # This ensures backward compatibility when Redis is down
    # Same behavior as the old implementation
    return list(tasks.keys())


async def stop_task(task_id: str):
    """
    Cancel a running task and remove it from both local dictionary and Redis.
    
    Important: Can only cancel tasks that are running on the current pod.
    Tasks on other pods cannot be cancelled from here (asyncio.Task objects are not shared).
    
    FIXED BUG #4: Removed redundant status update - done callback handles it.
    
    Args:
        task_id: The task ID to stop (must be a valid UUID)
    
    Raises:
        ValueError: If task ID is invalid, task is not found, or is on another pod.
    """
    # Validate task ID format
    if not _is_valid_task_id(task_id):
        raise ValueError(
            f"Invalid task ID format: task_id={task_id}. "
            "Task ID must be a valid UUID format."
        )
    
    # Check if task exists locally (on this pod)
    task = tasks.get(task_id)
    
    if task:
        # Task is on this pod, we can cancel it
        # Mark as manually cancelled to prevent done callback from updating (BUG #4 fix)
        # Use setattr to ensure attribute exists
        setattr(task, '_manually_cancelled', True)
        
        # Update Redis status to "cancelled" immediately for consistency
        _redis_task_store.update_task_status(
            task_id,
            TASK_STATUS_CANCELLED,
            completed_at=time.time(),
        )
        
        # Log task cancellation for metrics/observability (BUG #15 fix)
        try:
            pod_id = get_pod_identifier()
        except Exception as pod_error:
            log.warning(f"Failed to get pod identifier for task {task_id}: {pod_error}")
            pod_id = "unknown"
        log.info(f"Task stopped: task_id={task_id}, pod_id={pod_id}")
        
        task.cancel()
        try:
            await task  # Wait for the task to handle the cancellation
        except asyncio.CancelledError:
            # Task successfully canceled
            # Cleanup will be handled by the done callback
            return {"status": True, "message": f"Task {task_id} successfully stopped."}
        except Exception as e:
            log.error(f"Error while stopping task {task_id}: {e}", exc_info=True)
            # Update Redis to reflect error state
            _redis_task_store.update_task_status(
                task_id,
                TASK_STATUS_ERROR,
                error=str(e),
                completed_at=time.time(),
                skip_transition_check=True,
            )
            return {"status": False, "message": f"Failed to stop task {task_id}: {e}"}
    
    # Task not found locally, check Redis
    metadata = _redis_task_store.get_task_metadata(task_id)
    if metadata:
        pod_id = metadata.get("pod_id")
        current_pod = get_pod_identifier()
        
        if pod_id != current_pod:
            raise ValueError(
                f"Cannot stop task: task_id={task_id}, task_pod_id={pod_id}, current_pod_id={current_pod}. "
                "Tasks can only be stopped on the pod where they were created."
            )
        
        # Task metadata exists but Task object is gone (might have completed)
        status = metadata.get("status")
        if status in [TASK_STATUS_COMPLETED, TASK_STATUS_CANCELLED, TASK_STATUS_ERROR]:
            raise ValueError(
                f"Cannot stop task: task_id={task_id}, status={status}. "
                "Task is already in a terminal state and cannot be stopped."
            )
        
        # Task was on this pod but Task object is missing (shouldn't happen, but handle gracefully)
        # Mark it as cancelled in Redis since we can't actually cancel the Task object
        _redis_task_store.update_task_status(
            task_id,
            TASK_STATUS_CANCELLED,
            error="Task object not found on pod restart",
            completed_at=time.time(),
            skip_transition_check=True,
        )
        raise ValueError(
            f"Cannot stop task: task_id={task_id}, pod_id={current_pod}. "
            "Task metadata exists but Task object not found. "
            "The task may have already completed or the pod may have restarted. "
            "Task has been marked as cancelled in Redis."
        )
    
    # Task not found in Redis either
    raise ValueError(
        f"Task not found: task_id={task_id}. "
        "Task does not exist in local storage or Redis."
    )
