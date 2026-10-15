# tasks.py
import asyncio
import logging
from contextlib import suppress
from itertools import groupby
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from open_webui.env import REDIS_KEY_PREFIX, REDIS_RESPONSE_STREAM_TTL, REDIS_TASK_TTL
from open_webui.utils.json_codec import JSONCodec, dumps_bytes
from open_webui.utils.misc import get_output_text

log = logging.getLogger(__name__)

# A dictionary to keep track of active tasks
tasks: dict[str, asyncio.Task] = {}
item_tasks = {}
response_streams: dict[str, list[str]] = {}


REDIS_TASKS_KEY = f'{REDIS_KEY_PREFIX}:tasks'
REDIS_ITEM_TASKS_KEY = f'{REDIS_KEY_PREFIX}:tasks:item'
REDIS_RESPONSE_STREAMS_KEY = f'{REDIS_KEY_PREFIX}:tasks:response_streams'
REDIS_PUBSUB_CHANNEL = f'{REDIS_KEY_PREFIX}:tasks:commands'
REDIS_PUBSUB_RECONNECT_INTERVAL = 1.0
REDIS_PUBSUB_MAX_RECONNECT_INTERVAL = 30.0


async def redis_task_command_listener(app):
    redis: Redis = app.state.redis
    reconnect_interval = REDIS_PUBSUB_RECONNECT_INTERVAL

    while True:
        pubsub = None
        try:
            # RedisCluster can't route a pubsub subscribe until initialize() fills its slot cache.
            await redis.initialize()

            pubsub = redis.pubsub()
            await pubsub.subscribe(REDIS_PUBSUB_CHANNEL)
            reconnect_interval = REDIS_PUBSUB_RECONNECT_INTERVAL

            async for message in pubsub.listen():
                if message['type'] != 'message':
                    continue
                try:
                    command = JSONCodec.loads(message['data'])
                    if command.get('action') != 'stop':
                        continue

                    local_task = tasks.get(command.get('task_id'))
                    if local_task:
                        local_task.cancel()
                except Exception as e:
                    log.exception(f'Error handling distributed task command: {e}')
            log.warning('Redis task command listener stopped. Retrying.')
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception(f'Redis task command listener failed. Retrying: {e}')
        finally:
            if pubsub:
                with suppress(Exception):
                    await pubsub.aclose()

        await asyncio.sleep(reconnect_interval)
        reconnect_interval = min(reconnect_interval * 2, REDIS_PUBSUB_MAX_RECONNECT_INTERVAL)


async def redis_task_heartbeat(app):
    redis: Redis = app.state.redis
    while True:
        await asyncio.sleep(REDIS_TASK_TTL / 4)
        try:
            pipe = redis.pipeline(transaction=False)
            for task_id in list(tasks):
                # EXPIRE cannot recreate a task already removed by cleanup.
                pipe.expire(f'{REDIS_TASKS_KEY}:{task_id}', REDIS_TASK_TTL)
            await pipe.execute()
        except Exception:
            log.exception('Redis task heartbeat failed')


### ------------------------------
### REDIS-ENABLED HANDLERS
### ------------------------------


async def redis_save_task(redis: Redis, task_id: str, item_id: str | None):
    pipe = redis.pipeline(transaction=False)
    pipe.set(f'{REDIS_TASKS_KEY}:{task_id}', '1', ex=REDIS_TASK_TTL or None)
    pipe.hset(REDIS_TASKS_KEY, task_id, item_id or '')
    if item_id:
        pipe.sadd(f'{REDIS_ITEM_TASKS_KEY}:{item_id}', task_id)
    await pipe.execute()


async def redis_cleanup_task(redis: Redis, task_id: str, item_id: str | None):
    pipe = redis.pipeline(transaction=False)
    pipe.delete(f'{REDIS_TASKS_KEY}:{task_id}')
    pipe.hdel(REDIS_TASKS_KEY, task_id)
    pipe.delete(f'{REDIS_RESPONSE_STREAMS_KEY}:{task_id}')
    if item_id:
        pipe.srem(f'{REDIS_ITEM_TASKS_KEY}:{item_id}', task_id)
    await pipe.execute()


async def redis_list_tasks(redis: Redis, item_id: str | None = None) -> list[str]:
    task_ids = list(
        await redis.smembers(f'{REDIS_ITEM_TASKS_KEY}:{item_id}')
        if item_id is not None
        else await redis.hkeys(REDIS_TASKS_KEY)
    )
    if not task_ids or REDIS_TASK_TTL == 0:
        return task_ids

    pipe = redis.pipeline(transaction=False)
    for task_id in task_ids:
        pipe.exists(f'{REDIS_TASKS_KEY}:{task_id}')

    active = []
    for task_id, exists in zip(task_ids, await pipe.execute()):
        if exists:
            active.append(task_id)
        else:
            task_item_id = item_id if item_id is not None else await redis.hget(REDIS_TASKS_KEY, task_id)
            await redis_cleanup_task(redis, task_id, task_item_id or None)
    return active


async def redis_send_command(redis: Redis, command: dict):
    command_json = dumps_bytes(command)
    # RedisCluster doesn't expose publish() directly, but the
    # PUBLISH command broadcasts across all cluster nodes server-side.
    if hasattr(redis, 'nodes_manager'):
        await redis.execute_command('PUBLISH', REDIS_PUBSUB_CHANNEL, command_json)
    else:
        await redis.publish(REDIS_PUBSUB_CHANNEL, command_json)


async def cleanup_task(redis, task_id: str, id=None):
    """
    Remove a completed or canceled task from the global `tasks` dictionary.
    """
    if redis:
        await redis_cleanup_task(redis, task_id, id)

    tasks.pop(task_id, None)  # Remove the task if it exists
    response_streams.pop(task_id, None)

    # If an ID is provided, remove the task from the item_tasks dictionary
    if id and task_id in item_tasks.get(id, []):
        item_tasks[id].remove(task_id)
        if not item_tasks[id]:  # If no tasks left for this ID, remove the entry
            item_tasks.pop(id, None)


async def create_task(redis, coroutine, id=None, task_id=None):
    """
    Create a new asyncio task and add it to the global task dictionary.
    """
    task_id = task_id or str(uuid4())  # Generate a unique ID for the task
    task = asyncio.create_task(coroutine)  # Create the task

    # Add a done callback for cleanup
    task.add_done_callback(lambda t: asyncio.create_task(cleanup_task(redis, task_id, id)))
    tasks[task_id] = task

    # If an ID is provided, associate the task with that ID
    if id:
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
        return await redis_list_tasks(redis, id)
    return list(item_tasks.get(id, []))


async def save_response_stream(redis: Redis | None, task_id: str, stream_data: str) -> bool:
    """Replace a stream's live log; False when Redis did not take it."""
    if redis:
        try:
            await redis.set(
                f'{REDIS_RESPONSE_STREAMS_KEY}:{task_id}',
                stream_data,
                ex=REDIS_RESPONSE_STREAM_TTL if REDIS_RESPONSE_STREAM_TTL > 0 else None,
            )
        except RedisError:
            return False
    else:
        response_streams[task_id] = [stream_data]
    return True


async def append_response_stream(redis: Redis | None, task_id: str, line: str) -> bool:
    """Append an event line; False when Redis did not take it or had lost the log."""
    if redis:
        key = f'{REDIS_RESPONSE_STREAMS_KEY}:{task_id}'
        pipe = redis.pipeline(transaction=False)
        pipe.append(key, line)
        if REDIS_RESPONSE_STREAM_TTL > 0:
            pipe.expire(key, REDIS_RESPONSE_STREAM_TTL)
        try:
            log_size, *_ = await pipe.execute()
        except RedisError:
            return False
        return log_size > len(line.encode())
    else:
        response_streams[task_id].append(line)
        return True


def replay_response_stream(stream_data: str) -> dict:
    """Apply the logged events to the base line's output."""
    from open_webui.utils.middleware import get_response_delta_key, handle_responses_streaming_event

    def get_text_delta_key(event: dict) -> tuple | None:
        return get_response_delta_key(event) if isinstance(event.get('delta'), str) else None

    base, *events = (JSONCodec.loads(line) for line in stream_data.split('\n') if line)
    output = base['output']
    # Merge text deltas first so the replay copies the text once, not once per token
    for delta_key, run in groupby(events, key=get_text_delta_key):
        if delta_key:
            first, *rest = run
            merged = {**first, 'delta': first['delta'] + ''.join(event['delta'] for event in rest)}
            output, _ = handle_responses_streaming_event(merged, output)
        else:
            for event in run:
                output, _ = handle_responses_streaming_event(event, output)
    return {**base, 'output': output}


async def get_response_streams_by_chat_id(redis, chat_id: str) -> list[dict]:
    task_ids = await list_task_ids_by_item_id(redis, chat_id)
    if not task_ids:
        return []

    if redis:
        pipe = redis.pipeline(transaction=False)
        for task_id in task_ids:
            pipe.get(f'{REDIS_RESPONSE_STREAMS_KEY}:{task_id}')
        values = await pipe.execute()
    else:
        values = [''.join(response_streams.get(task_id, [])) for task_id in task_ids]

    streams = []
    for value in values:
        if not value:
            continue
        try:
            stream = replay_response_stream(value)
        except Exception:
            continue
        if stream.get('chat_id') == chat_id:
            stream['content'] = get_output_text(stream['output'])
            streams.append(stream)
    return streams


async def clear_response_stream(redis, task_id: str | None):
    if not task_id:
        return
    if redis:
        await redis.delete(f'{REDIS_RESPONSE_STREAMS_KEY}:{task_id}')
    else:
        response_streams.pop(task_id, None)


async def stop_task(redis, task_id: str):
    """
    Cancel a running task and remove it from the global task list.
    """
    if redis:
        # Look up the item_id before cleanup so we can remove the set entry too
        item_id = await redis.hget(REDIS_TASKS_KEY, task_id)
        # PUBSUB: All instances check if they have this task, and stop if so.
        await redis_send_command(
            redis,
            {
                'action': 'stop',
                'task_id': task_id,
            },
        )
        # Always clean Redis directly — hdel/srem are idempotent, safe even
        # if the done_callback on the owning process also fires cleanup.
        await redis_cleanup_task(redis, task_id, item_id or None)
        return {'status': True, 'message': f'Task {task_id} stopped.'}

    task = tasks.pop(task_id, None)
    if not task:
        return {'status': False, 'message': f'Task with ID {task_id} not found.'}

    task.cancel()  # Request task cancellation
    try:
        await task  # Wait for the task to handle the cancellation
    except asyncio.CancelledError:
        # Task successfully canceled
        return {'status': True, 'message': f'Task {task_id} successfully stopped.'}

    if task.cancelled() or task.done():
        return {'status': True, 'message': f'Task {task_id} successfully cancelled.'}

    return {'status': True, 'message': f'Cancellation requested for {task_id}.'}


async def stop_item_tasks(redis: Redis, item_id: str):
    """
    Stop all tasks associated with a specific item ID.
    """
    task_ids = await list_task_ids_by_item_id(redis, item_id)
    if not task_ids:
        return {'status': True, 'message': f'No tasks found for item {item_id}.'}

    # Cleanup mutates the local task list while cancellation is awaited.
    for task_id in list(task_ids):
        # A task that already finished needs no stopping; continue with the rest.
        await stop_task(redis, task_id)

    return {'status': True, 'message': f'All tasks for item {item_id} stopped.'}


async def has_active_tasks(redis, chat_id: str) -> bool:
    """Check if a chat has any active tasks."""
    task_ids = await list_task_ids_by_item_id(redis, chat_id)
    return len(task_ids) > 0
