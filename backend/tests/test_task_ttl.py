"""Run with TEST_REDIS_URL=redis://localhost:6379 PYTHONPATH=backend python backend/tests/test_task_ttl.py."""

import asyncio
import os
import sys
from contextlib import suppress
from types import SimpleNamespace
from uuid import uuid4

from open_webui import tasks
from redis.asyncio import Redis


async def check():
    prefix = sys.argv[1] if len(sys.argv) > 1 else f'task-ttl-test:{uuid4()}'
    tasks.REDIS_TASKS_KEY = f'{prefix}:tasks'
    tasks.REDIS_ITEM_TASKS_KEY = f'{prefix}:items'
    tasks.REDIS_RESPONSE_STREAMS_KEY = f'{prefix}:responses'
    tasks.REDIS_PUBSUB_CHANNEL = f'{prefix}:commands'
    tasks.REDIS_TASK_TTL = 2
    async with Redis.from_url(os.environ['TEST_REDIS_URL'], decode_responses=True) as redis:
        app = SimpleNamespace(state=SimpleNamespace(redis=redis))
        heartbeat = asyncio.create_task(tasks.redis_task_heartbeat(app))
        worker = None
        try:
            if len(sys.argv) > 1:
                await tasks.create_task(redis, asyncio.Event().wait(), 'chat', task_id='worker-task')
                print('ready', flush=True)
                await asyncio.Event().wait()

            worker = await asyncio.create_subprocess_exec(
                sys.executable, __file__, prefix, stdout=asyncio.subprocess.PIPE
            )
            assert await asyncio.wait_for(worker.stdout.readline(), 10) == b'ready\n'
            await tasks.create_task(redis, asyncio.Event().wait(), 'chat', task_id='live-task')
            await tasks.create_task(redis, asyncio.Event().wait(), task_id='unscoped-task')
            await asyncio.sleep(2.2)
            assert set(await tasks.list_tasks(redis)) == {'worker-task', 'live-task', 'unscoped-task'}
            print('PASS: both workers retain running tasks beyond the TTL, including tasks without an item ID')

            worker.kill()
            await worker.wait()
            await tasks.redis_save_task(redis, 'abandoned-task', None)
            await tasks.redis_save_task(redis, 'only-task', 'empty-chat')
            await redis.hset(tasks.REDIS_RESPONSE_STREAMS_KEY, 'worker-task', 'stale response')
            await asyncio.sleep(2.2)
            assert await tasks.list_task_ids_by_item_id(redis, 'chat') == ['live-task']
            assert await redis.smembers(f'{tasks.REDIS_ITEM_TASKS_KEY}:chat') == {'live-task'}
            assert not await redis.hexists(tasks.REDIS_RESPONSE_STREAMS_KEY, 'worker-task')
            assert await tasks.list_task_ids_by_item_id(redis, 'empty-chat') == []
            assert not await redis.exists(f'{tasks.REDIS_ITEM_TASKS_KEY}:empty-chat')
            assert set(await tasks.list_tasks(redis)) == {'live-task', 'unscoped-task'}
            assert not await redis.hexists(tasks.REDIS_TASKS_KEY, 'abandoned-task')
            print('PASS: killed-worker tasks expire independently; chat/global reads prune stale IDs and responses')

            await tasks.stop_task(redis, 'live-task')
            await asyncio.sleep(0.6)
            assert not await redis.exists(f'{tasks.REDIS_TASKS_KEY}:live-task')
            assert not await tasks.has_active_tasks(redis, 'chat')
            print('PASS: heartbeat does not recreate a removed task')

            await redis.hset(tasks.REDIS_TASKS_KEY, 'legacy-task', 'legacy-chat')
            await redis.sadd(f'{tasks.REDIS_ITEM_TASKS_KEY}:legacy-chat', 'legacy-task')
            assert not await tasks.has_active_tasks(redis, 'legacy-chat')
            print('PASS: legacy entries without expiry keys are pruned')

            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
            tasks.REDIS_TASK_TTL = 0
            await tasks.redis_save_task(redis, 'persistent-task', 'persistent-chat')
            assert await redis.ttl(f'{tasks.REDIS_TASKS_KEY}:persistent-task') == -1
            assert await tasks.list_task_ids_by_item_id(redis, 'persistent-chat') == ['persistent-task']
            print('PASS: TTL=0 disables expiry')
        finally:
            if worker and worker.returncode is None:
                worker.kill()
                await worker.wait()
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
            pending = list(tasks.tasks.values())
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            # Let task done callbacks finish their Redis cleanup before closing the connection.
            while tasks.tasks:
                await asyncio.sleep(0.01)
            async for key in redis.scan_iter(match=f'{prefix}:*'):
                await redis.delete(key)


if __name__ == '__main__':
    asyncio.run(asyncio.wait_for(check(), 30))
