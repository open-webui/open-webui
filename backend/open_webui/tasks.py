# tasks.py
import asyncio
from typing import Dict
from uuid import uuid4
import json
import logging
from redis.asyncio import Redis
from fastapi import Request
from typing import Dict, List, Optional

from open_webui.env import REDIS_KEY_PREFIX


log = logging.getLogger(__name__)

# A dictionary to keep track of active tasks
tasks: Dict[str, asyncio.Task] = {}
item_tasks = {}


REDIS_TASKS_KEY = f"{REDIS_KEY_PREFIX}:tasks"
REDIS_ITEM_TASKS_KEY = f"{REDIS_KEY_PREFIX}:tasks:item"
REDIS_TASK_STOP_KEY = f"{REDIS_KEY_PREFIX}:task:stop"

# Task stop check interval in seconds
TASK_STOP_CHECK_INTERVAL = 1.0


### ------------------------------
### REDIS-ENABLED HANDLERS
### ------------------------------


async def redis_save_task(redis: Redis, task_id: str, item_id: Optional[str]):
    pipe = redis.pipeline()
    pipe.hset(REDIS_TASKS_KEY, task_id, item_id or "")
    if item_id:
        pipe.sadd(f"{REDIS_ITEM_TASKS_KEY}:{item_id}", task_id)
    await pipe.execute()


async def redis_cleanup_task(redis: Redis, task_id: str, item_id: Optional[str]):
    """Clean up task tracking in Redis."""
    try:
        pipe = redis.pipeline()
        pipe.hdel(REDIS_TASKS_KEY, task_id)
        
        if item_id:
            pipe.srem(f"{REDIS_ITEM_TASKS_KEY}:{item_id}", task_id)
        
        # Clean up stop signal if exists
        pipe.delete(f"{REDIS_TASK_STOP_KEY}:{task_id}")
        
        await pipe.execute()
        
        # Check and delete empty item set
        if item_id:
            remaining_count = await redis.scard(f"{REDIS_ITEM_TASKS_KEY}:{item_id}")
            if remaining_count == 0:
                await redis.delete(f"{REDIS_ITEM_TASKS_KEY}:{item_id}")
    except Exception as e:
        log.warning(f"Error cleaning up task {task_id} from Redis: {e}")


async def redis_list_tasks(redis: Redis) -> List[str]:
    return list(await redis.hkeys(REDIS_TASKS_KEY))


async def redis_list_item_tasks(redis: Redis, item_id: str) -> List[str]:
    return list(await redis.smembers(f"{REDIS_ITEM_TASKS_KEY}:{item_id}"))


async def should_stop_task(redis: Redis, task_id: str) -> bool:
    """Check if a task should be stopped based on Redis state."""
    if not redis:
        return False
    try:
        stop_key = f"{REDIS_TASK_STOP_KEY}:{task_id}"
        return await redis.exists(stop_key) > 0
    except Exception:
        return False


async def cleanup_task(redis, task_id: str, id=None):
    """
    Remove a completed or canceled task from the global `tasks` dictionary.
    """
    if redis:
        await redis_cleanup_task(redis, task_id, id)

    tasks.pop(task_id, None)  # Remove the task if it exists

    # If an ID is provided, remove the task from the item_tasks dictionary
    if id and task_id in item_tasks.get(id, []):
        item_tasks[id].remove(task_id)
        if not item_tasks[id]:  # If no tasks left for this ID, remove the entry
            item_tasks.pop(id, None)


async def create_task(redis, coroutine, id=None):
    """
    Create a new asyncio task and add it to the global task dictionary.
    Wraps the coroutine to check for stop signals from Redis.
    """
    task_id = str(uuid4())  # Generate a unique ID for the task

    # Wrapper that checks for stop signal periodically
    async def task_with_stop_check():
        """Wrapper that periodically checks for stop signal from Redis."""
        # Create the actual task
        main_task = asyncio.create_task(coroutine)
        
        try:
            # Run monitoring loop
            while not main_task.done():
                # Check if stop signal has been set
                if redis and await should_stop_task(redis, task_id):
                    log.debug(f"Stop signal detected for task {task_id}")
                    main_task.cancel()
                    break
                
                # Wait before next check, but wake up if main_task completes
                done, pending = await asyncio.wait(
                    [main_task],
                    timeout=TASK_STOP_CHECK_INTERVAL,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if main_task in done:
                    # Task completed normally or with exception
                    break
            
            # Return result or raise exception from main_task
            return await main_task
            
        except asyncio.CancelledError:
            # Wrapper was cancelled, cancel main task too
            if not main_task.done():
                main_task.cancel()
                try:
                    await main_task
                except asyncio.CancelledError:
                    pass
            raise

    task = asyncio.create_task(task_with_stop_check())

    # Add a done callback for cleanup
    task.add_done_callback(
        lambda t: asyncio.create_task(cleanup_task(redis, task_id, id))
    )
    tasks[task_id] = task

    # If an ID is provided, associate the task with that ID
    if item_tasks.get(id):
        item_tasks[id].append(task_id)
    else:
        item_tasks[id] = [task_id]

    if redis:
        await redis_save_task(redis, task_id, id)

    return task_id, task


async def list_tasks(redis):
    """
    List all currently active task IDs.
    """
    if redis:
        return await redis_list_tasks(redis)
    return list(tasks.keys())


async def list_task_ids_by_item_id(redis, id):
    """
    List all tasks associated with a specific ID.
    """
    if redis:
        return await redis_list_item_tasks(redis, id)
    return item_tasks.get(id, [])


async def stop_task(redis, task_id: str):
    """
    Stop a task by setting a state flag in Redis or canceling it locally.
    Uses STATE-based approach instead of PUBLISH.
    """
    if redis:
        try:
            # Set stop signal with TTL to prevent orphaned keys
            stop_key = f"{REDIS_TASK_STOP_KEY}:{task_id}"
            await redis.set(stop_key, "1", ex=300)  # 5 minute TTL
        except Exception as e:
            log.warning(f"Error setting stop signal for task {task_id}: {e}")
        
        # Also try to cancel local task immediately if it exists
        local_task = tasks.get(task_id)
        if local_task and not local_task.done():
            local_task.cancel()
        
        return {"status": True, "message": f"Stop signal set for {task_id}"}

    # Local-only fallback (no Redis)
    task = tasks.pop(task_id, None)
    if not task:
        return {"status": False, "message": f"Task with ID {task_id} not found."}

    task.cancel()  # Request task cancellation
    try:
        await task  # Wait for the task to handle the cancellation
    except asyncio.CancelledError:
        # Task successfully canceled
        return {"status": True, "message": f"Task {task_id} successfully stopped."}

    return {"status": False, "message": f"Failed to stop task {task_id}."}


async def stop_item_tasks(redis: Redis, item_id: str):
    """
    Stop all tasks associated with a specific item ID.
    """
    task_ids = await list_task_ids_by_item_id(redis, item_id)
    if not task_ids:
        return {"status": True, "message": f"No tasks found for item {item_id}."}

    for task_id in task_ids:
        result = await stop_task(redis, task_id)
        if not result["status"]:
            return result  # Return the first failure

    return {"status": True, "message": f"All tasks for item {item_id} stopped."}
