"""Per-room redis channels let instances skip the decode and packet encode for rooms with no local members."""

import asyncio

from redis.asyncio.client import PubSub
from redis.exceptions import NoPermissionError
from socketio import AsyncRedisManager


class AsyncRedisRoomChannelManager(AsyncRedisManager):
    name = 'aioredisroomchannel'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._local_room_channels = set()
        self._local_room_channels_changed: asyncio.Event = asyncio.Event()

    # collision-free while namespaces contain no '#' (socket.io default '/'); rooms may contain '#'
    def _room_channel(self, namespace, room):
        return f'{self.channel}#{namespace}#{room}'.encode()

    def basic_enter_room(self, sid, namespace, room, eio_sid=None):
        super().basic_enter_room(sid, namespace, room, eio_sid=eio_sid)
        if room is not None:
            self._local_room_channels.add(self._room_channel(namespace, room))
            self._local_room_channels_changed.set()

    def basic_leave_room(self, sid, namespace, room):
        super().basic_leave_room(sid, namespace, room)
        if room is not None and room not in self.rooms.get(namespace, {}):
            self._local_room_channels.discard(self._room_channel(namespace, room))
            self._local_room_channels_changed.set()

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

    async def _subscribe_local_room_channels(self, pubsub: PubSub):
        """Keep a pubsub connection subscribed to exactly the local room channels."""
        _, error = self._get_redis_module_and_error()
        subscribed_room_channels = set()
        while True:
            self._local_room_channels_changed.clear()
            local_room_channels = set(self._local_room_channels)
            try:
                if new_room_channels := local_room_channels - subscribed_room_channels:
                    await pubsub.subscribe(*new_room_channels)
                if removed_room_channels := subscribed_room_channels - local_room_channels:
                    await pubsub.unsubscribe(*removed_room_channels)
            except (error, RuntimeError):
                # RuntimeError: redis-py reconnected this connection from here and from the listener at once
                await asyncio.sleep(1)
                continue
            subscribed_room_channels = local_room_channels
            await self._local_room_channels_changed.wait()

    async def _redis_listen_with_retries(self):
        _, error = self._get_redis_module_and_error()
        retry_sleep = 1
        subscribed = False
        while True:
            try:
                if not subscribed:
                    self._redis_connect()
                    await self.pubsub.subscribe(self.channel)
                    retry_sleep = 1
                subscription_task = asyncio.create_task(self._subscribe_local_room_channels(self.pubsub))
                try:
                    async for message in self.pubsub.listen():
                        yield message
                finally:
                    subscription_task.cancel()
            except error as exc:
                if isinstance(exc, NoPermissionError):
                    self._get_logger().error(
                        'Redis denied subscribing: %s. Check SUBSCRIBE/UNSUBSCRIBE permissions and channel ACLs '
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
                subscribed = False
                await asyncio.sleep(retry_sleep)
                retry_sleep *= 2
                if retry_sleep > 60:
                    retry_sleep = 60

    async def _listen(self):
        main_channel = self.channel.encode()
        async for message in self._redis_listen_with_retries():
            if 'data' not in message:
                continue
            if message['type'] == 'message' and (
                message['channel'] == main_channel or message['channel'] in self._local_room_channels
            ):
                yield message['data']
