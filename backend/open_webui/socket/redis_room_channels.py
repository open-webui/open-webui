"""Per-room redis channels let instances skip the decode and packet encode for rooms with no local members."""

import asyncio

from redis.exceptions import NoPermissionError
from socketio import AsyncRedisManager


class AsyncRedisRoomChannelManager(AsyncRedisManager):
    name = 'aioredisroomchannel'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscription_queue = asyncio.Queue()

    # collision-free while namespaces contain no '#' (socket.io default '/'); rooms may contain '#'
    def _room_channel(self, namespace, room):
        return f'{self.channel}#{namespace}#{room}'.encode()

    def basic_enter_room(self, sid, namespace, room, eio_sid=None):
        super().basic_enter_room(sid, namespace, room, eio_sid=eio_sid)
        if room is not None:
            self._subscription_queue.put_nowait(asyncio.Event())

    def basic_leave_room(self, sid, namespace, room):
        super().basic_leave_room(sid, namespace, room)
        if room is not None and room not in self.rooms.get(namespace, {}):
            self._subscription_queue.put_nowait(asyncio.Event())

    async def _wait_for_rooms(self):
        ready = asyncio.Event()
        self._subscription_queue.put_nowait(ready)
        await ready.wait()

    async def connect(self, eio_sid, namespace):
        sid = await super().connect(eio_sid, namespace)
        if sid is not None:
            await self._wait_for_rooms()
        return sid

    async def enter_room(self, sid, namespace, room, eio_sid=None):
        local = self.is_connected(sid, namespace)
        await super().enter_room(sid, namespace, room, eio_sid=eio_sid)
        if local and room is not None:
            await self._wait_for_rooms()

    async def _publish(self, data):
        if data.get('method') == 'emit' and isinstance(data.get('room'), str):
            channel = self._room_channel(data['namespace'], data['room'])
        else:
            channel = self.channel
        _, error = self._get_redis_module_and_error()
        for retries_left in range(1, -1, -1):  # 2 attempts
            try:
                if not self.connected:
                    self._redis_connect()
                return await self.redis.publish(channel, self.json.dumps(data))
            except error as exc:
                if isinstance(exc, NoPermissionError):
                    self._get_logger().error(
                        'Redis denied publishing: %s. Check PUBLISH permission and channel ACLs '
                        '(&%s and &%s#*). To disable room channels, set '
                        'WEBSOCKET_REDIS_ROOM_CHANNELS=False on every instance and fully restart the fleet.',
                        exc,
                        self.channel,
                        self.channel,
                    )
                if retries_left > 0:
                    self._get_logger().error('Cannot publish to redis... retrying', extra={'redis_exception': str(exc)})
                    self.connected = False
                else:
                    self._get_logger().error(
                        'Cannot publish to redis... giving up', extra={'redis_exception': str(exc)}
                    )
                    break

    async def _sync_rooms(self, pubsub):
        wanted = {self.channel.encode()} | {
            self._room_channel(namespace, room)
            for namespace, rooms in self.rooms.items()
            for room in rooms
            if room is not None
        }
        if added := wanted - (pubsub.channels.keys() - pubsub.pending_unsubscribe_channels):
            await pubsub.subscribe(*added)
        if removed := pubsub.channels.keys() - wanted - pubsub.pending_unsubscribe_channels:
            await pubsub.unsubscribe(*removed)

    async def _listen_to_rooms(self, pubsub):
        pubsub.ignore_subscribe_messages = False
        self._subscription_queue.put_nowait(asyncio.Event())
        changed = asyncio.create_task(self._subscription_queue.get())
        message = asyncio.create_task(pubsub.get_message(timeout=None))
        waiters = []
        serial = 0
        try:
            while True:
                await asyncio.wait([message] if waiters else [message, changed], return_when=asyncio.FIRST_COMPLETED)
                if not waiters and changed.done():
                    waiters.append(changed.result())
                    while not self._subscription_queue.empty():
                        waiters.append(self._subscription_queue.get_nowait())
                    changed = asyncio.create_task(self._subscription_queue.get())
                    await self._sync_rooms(pubsub)
                    # PONG confirms Redis processed the subscriptions before a join returns.
                    serial += 1
                    await pubsub.ping(str(serial).encode())
                if message.done():
                    data = message.result() or {}
                    message = asyncio.create_task(pubsub.get_message(timeout=None))
                    if data.get('type') == 'subscribe':
                        # redis-py can reconnect internally and restore a pending removal.
                        self._subscription_queue.put_nowait(asyncio.Event())
                    elif data.get('type') == 'pong' and data['data'] == str(serial).encode():
                        for ready in waiters:
                            ready.set()
                        waiters.clear()
                    else:
                        yield data
        finally:
            if changed.done() and not changed.cancelled():
                waiters.append(changed.result())
            for ready in waiters:
                self._subscription_queue.put_nowait(ready)
            message.cancel()
            changed.cancel()
            await asyncio.gather(message, changed, return_exceptions=True)
            await pubsub.aclose()

    async def _redis_listen_with_retries(self):
        _, error = self._get_redis_module_and_error()
        retry_sleep = 1
        while True:
            try:
                self._redis_connect()
                await self.pubsub.subscribe(self.channel)
                retry_sleep = 1
                async for message in self._listen_to_rooms(self.pubsub):
                    yield message
            except error as exc:
                if isinstance(exc, NoPermissionError):
                    self._get_logger().error(
                        'Redis denied subscribing: %s. Check SUBSCRIBE/UNSUBSCRIBE/PING permissions and channel ACLs '
                        '(&%s and &%s#*). To disable room channels, set '
                        'WEBSOCKET_REDIS_ROOM_CHANNELS=False on every instance and fully restart the fleet.',
                        exc,
                        self.channel,
                        self.channel,
                    )
                self._get_logger().error(
                    f'Cannot receive from redis... retrying in {retry_sleep} secs',
                    extra={'redis_exception': str(exc)},
                )
                await asyncio.sleep(retry_sleep)
                retry_sleep *= 2
                if retry_sleep > 60:
                    retry_sleep = 60

    async def _listen(self):
        async for message in self._redis_listen_with_retries():
            if message.get('type') == 'message':
                yield message['data']
