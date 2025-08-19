# tasks.py
import asyncio
from typing import Dict
from uuid import uuid4
import json
import logging
from redis.asyncio import Redis
from fastapi import Request
from typing import Dict, List, Optional
from builtins import ExceptionGroup

from open_webui.env import SRC_LOG_LEVELS, REDIS_KEY_PREFIX


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

# A dictionary to keep track of active tasks
tasks: Dict[str, asyncio.Task] = {}
item_tasks = {}


REDIS_TASKS_KEY = f"{REDIS_KEY_PREFIX}:tasks"
REDIS_ITEM_TASKS_KEY = f"{REDIS_KEY_PREFIX}:tasks:item"
REDIS_PUBSUB_CHANNEL = f"{REDIS_KEY_PREFIX}:tasks:commands"


async def redis_task_command_listener(app):
    redis: Redis = app.state.redis
    pubsub = redis.pubsub()
    await pubsub.subscribe(REDIS_PUBSUB_CHANNEL)

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            # Check if message data is empty or None
            if not message["data"]:
                log.warning("Received empty message data from Redis pub/sub")
                continue

            # Attempt to parse JSON
            try:
                command = json.loads(message["data"])
            except json.JSONDecodeError as json_error:
                log.warning(f"Invalid JSON in Redis message: {message['data'][:100]}... Error: {json_error}")
                continue

            if command.get("action") == "stop":
                task_id = command.get("task_id")
                local_task = tasks.get(task_id)
                if local_task:
                    try:
                        local_task.cancel()
                        # Wait briefly for cancellation to complete
                        await asyncio.sleep(0.1)
                    except Exception as cancel_error:
                        log.error(f"Error cancelling task {task_id}: {cancel_error}")
        except ExceptionGroup as eg:
            # Handle multiple concurrent exceptions
            log.error(f"Multiple errors in task command processing: {len(eg.exceptions)} exceptions")
            for i, exc in enumerate(eg.exceptions):
                log.error(f"  Exception {i+1}: {type(exc).__name__}: {exc}")
        except Exception as e:
            log.exception(f"Error handling distributed task command: {e}")


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
    pipe = redis.pipeline()
    pipe.hdel(REDIS_TASKS_KEY, task_id)
    if item_id:
        pipe.srem(f"{REDIS_ITEM_TASKS_KEY}:{item_id}", task_id)
        if (await pipe.scard(f"{REDIS_ITEM_TASKS_KEY}:{item_id}").execute())[-1] == 0:
            pipe.delete(f"{REDIS_ITEM_TASKS_KEY}:{item_id}")  # Remove if empty set
    await pipe.execute()


async def redis_list_tasks(redis: Redis) -> List[str]:
    return list(await redis.hkeys(REDIS_TASKS_KEY))


async def redis_list_item_tasks(redis: Redis, item_id: str) -> List[str]:
    return list(await redis.smembers(f"{REDIS_ITEM_TASKS_KEY}:{item_id}"))


async def redis_send_command(redis: Redis, command: dict):
    await redis.publish(REDIS_PUBSUB_CHANNEL, json.dumps(command))


async def cleanup_task(redis, task_id: str, id=None):
    """
    Remove a completed or canceled task with proper exception handling.
    """
    cleanup_errors = []

    # Redis cleanup
    if redis:
        try:
            await redis_cleanup_task(redis, task_id, id)
        except Exception as e:
            cleanup_errors.append(e)
            log.error(f"Redis cleanup failed for task {task_id}: {e}")

    # Local cleanup
    try:
        tasks.pop(task_id, None)
        if id and task_id in item_tasks.get(id, []):
            item_tasks[id].remove(task_id)
            if not item_tasks[id]:
                item_tasks.pop(id, None)
    except Exception as e:
        cleanup_errors.append(e)
        log.error(f"Local cleanup failed for task {task_id}: {e}")

    # If multiple errors occurred, group them
    if len(cleanup_errors) > 1 and ExceptionGroup:
        raise ExceptionGroup(f"Multiple cleanup errors for task {task_id}", cleanup_errors)
    elif cleanup_errors:
        raise cleanup_errors[0]


async def create_task(redis, coroutine, id=None):
    """
    Create a new asyncio task and add it to the global task dictionary.
    """
    task_id = str(uuid4())  # Generate a unique ID for the task
    task = asyncio.create_task(coroutine)  # Create the task

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
    Cancel a running task and remove it from the global task list.
    """
    if redis:
        # PUBSUB: All instances check if they have this task, and stop if so.
        await redis_send_command(
            redis,
            {
                "action": "stop",
                "task_id": task_id,
            },
        )
        # Optionally check if task_id still in Redis a few moments later for feedback?
        return {"status": True, "message": f"Stop signal sent for {task_id}"}

    task = tasks.pop(task_id)
    if not task:
        raise ValueError(f"Task with ID {task_id} not found.")

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
