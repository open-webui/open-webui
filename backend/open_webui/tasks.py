# tasks.py
import asyncio
from typing import Dict
from uuid import uuid4
import json
from redis.asyncio import Redis
from fastapi import Request
from typing import Dict, List, Optional

# A dictionary to keep track of active tasks
tasks: Dict[str, asyncio.Task] = {}
chat_tasks = {}


REDIS_TASKS_KEY = "open-webui:tasks"
REDIS_CHAT_TASKS_KEY = "open-webui:tasks:chat"
REDIS_PUBSUB_CHANNEL = "open-webui:tasks:commands"


def is_redis(request: Request) -> bool:
    # Called everywhere a request is available to check Redis
    return hasattr(request.app.state, "redis") and (request.app.state.redis is not None)


async def redis_task_command_listener(app):
    redis: Redis = app.state.redis
    pubsub = redis.pubsub()
    await pubsub.subscribe(REDIS_PUBSUB_CHANNEL)

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            command = json.loads(message["data"])
            if command.get("action") == "stop":
                task_id = command.get("task_id")
                local_task = tasks.get(task_id)
                if local_task:
                    local_task.cancel()
        except Exception as e:
            print(f"Error handling distributed task command: {e}")


### ------------------------------
### REDIS-ENABLED HANDLERS
### ------------------------------


async def redis_save_task(redis: Redis, task_id: str, chat_id: Optional[str]):
    pipe = redis.pipeline()
    pipe.hset(REDIS_TASKS_KEY, task_id, chat_id or "")
    if chat_id:
        pipe.sadd(f"{REDIS_CHAT_TASKS_KEY}:{chat_id}", task_id)
    await pipe.execute()


async def redis_cleanup_task(redis: Redis, task_id: str, chat_id: Optional[str]):
    pipe = redis.pipeline()
    pipe.hdel(REDIS_TASKS_KEY, task_id)
    if chat_id:
        pipe.srem(f"{REDIS_CHAT_TASKS_KEY}:{chat_id}", task_id)
        if (await pipe.scard(f"{REDIS_CHAT_TASKS_KEY}:{chat_id}").execute())[-1] == 0:
            pipe.delete(f"{REDIS_CHAT_TASKS_KEY}:{chat_id}")  # Remove if empty set
    await pipe.execute()


async def redis_list_tasks(redis: Redis) -> List[str]:
    return list(await redis.hkeys(REDIS_TASKS_KEY))


async def redis_list_chat_tasks(redis: Redis, chat_id: str) -> List[str]:
    return list(await redis.smembers(f"{REDIS_CHAT_TASKS_KEY}:{chat_id}"))


async def redis_send_command(redis: Redis, command: dict):
    await redis.publish(REDIS_PUBSUB_CHANNEL, json.dumps(command))


async def cleanup_task(request, task_id: str, id=None):
    """
    Remove a completed or canceled task from the global `tasks` dictionary.
    """
    if is_redis(request):
        await redis_cleanup_task(request.app.state.redis, task_id, id)

    tasks.pop(task_id, None)  # Remove the task if it exists

    # If an ID is provided, remove the task from the chat_tasks dictionary
    if id and task_id in chat_tasks.get(id, []):
        chat_tasks[id].remove(task_id)
        if not chat_tasks[id]:  # If no tasks left for this ID, remove the entry
            chat_tasks.pop(id, None)


async def create_task(request, coroutine, id=None):
    """
    Create a new asyncio task and add it to the global task dictionary.
    """
    task_id = str(uuid4())  # Generate a unique ID for the task
    task = asyncio.create_task(coroutine)  # Create the task

    # Add a done callback for cleanup
    task.add_done_callback(
        lambda t: asyncio.create_task(cleanup_task(request, task_id, id))
    )
    tasks[task_id] = task

    # If an ID is provided, associate the task with that ID
    if chat_tasks.get(id):
        chat_tasks[id].append(task_id)
    else:
        chat_tasks[id] = [task_id]

    if is_redis(request):
        await redis_save_task(request.app.state.redis, task_id, id)

    return task_id, task


async def list_tasks(request):
    """
    List all currently active task IDs.
    """
    if is_redis(request):
        return await redis_list_tasks(request.app.state.redis)
    return list(tasks.keys())


async def list_task_ids_by_chat_id(request, id):
    """
    List all tasks associated with a specific ID.
    """
    if is_redis(request):
        return await redis_list_chat_tasks(request.app.state.redis, id)
    return chat_tasks.get(id, [])


async def stop_task(request, task_id: str):
    """
    Cancel a running task and remove it from the global task list.
    """
    if is_redis(request):
        # PUBSUB: All instances check if they have this task, and stop if so.
        await redis_send_command(
            request.app.state.redis,
            {
                "action": "stop",
                "task_id": task_id,
            },
        )
        # Optionally check if task_id still in Redis a few moments later for feedback?
        return {"status": True, "message": f"Stop signal sent for {task_id}"}

    task = tasks.get(task_id)
    if not task:
        raise ValueError(f"Task with ID {task_id} not found.")

    task.cancel()  # Request task cancellation
    try:
        await task  # Wait for the task to handle the cancellation
    except asyncio.CancelledError:
        # Task successfully canceled
        tasks.pop(task_id, None)  # Remove it from the dictionary
        return {"status": True, "message": f"Task {task_id} successfully stopped."}

    return {"status": False, "message": f"Failed to stop task {task_id}."}
