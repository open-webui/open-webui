"""Routed delivery for the socket.io Redis manager, enabled with WEBSOCKET_REDIS_ROUTING=true.

Instead of broadcasting every emit on one shared channel for every instance to decode,
each instance registers its room membership in Redis and emits are published only to the
per-instance channels of the instances holding members of the target room. Emits to
rooms with no members anywhere in the fleet are dropped before serialization and
local-only delivery costs at most a cached registry read. All instances sharing a
channel must run the same mode, since hub instances neither subscribe to per-instance
channels nor register their rooms. Registration is asynchronous (a writer pass plus a
Redis round trip behind the membership change), so emits targeting state newer than
the registry, like a sid learned out of band, can briefly read as empty; every current
caller emits from live socket state. Rooms spanning most of the fleet cost one publish
per member instance, so very wide rooms approach hub cost instead of beating it.
"""

import asyncio
import random
import time

from socketio import AsyncRedisManager


def to_str(value):
    return value.decode() if isinstance(value, bytes) else value


class AsyncRedisRouterManager(AsyncRedisManager):
    name = 'aioredisrouter'

    HEARTBEAT_INTERVAL = 15
    INSTANCE_TTL = 60
    ROUTE_CACHE_TTL = 5
    SYNC_CHUNK_SIZE = 500  # rooms per registry pipeline, bounds event-loop blocking

    def __init__(
        self,
        url='redis://localhost:6379/0',
        channel='socketio',
        write_only=False,
        logger=None,
        json=None,
        redis_options=None,
    ):
        super().__init__(
            url, channel=channel, write_only=write_only, logger=logger, json=json, redis_options=redis_options
        )
        self._ctl_channel = f'{channel}:ctl'
        self._instances_key = f'{channel}:instances'
        self._own_node_channel = self._node_channel(self.host_id)
        self._own_rooms_key = self._instance_rooms_key(self.host_id)
        self._route_cache = {}  # (namespace, room) -> (instance ids, expiry)
        self._route_epoch = 0  # bumped per invalidation, guards reads racing a route change
        self._written_rooms = set()  # (namespace, room) entries we hold in Redis
        self._dirty_rooms = {}  # (namespace, room) -> is it the sid's personal room
        self._dirty_event = asyncio.Event()
        self._syncing = False
        self._writes_failing = False
        self._registry_read_down = False
        self._distrust_until = float('inf')  # peers may not have re-registered yet
        self._last_ctl_seen = time.monotonic()  # our own heartbeat ping must echo back
        self._pruned_peers = None  # (ids, until): prune notices are repeated for stragglers
        self._rebuild_until = 0.0  # set only when the registry itself was rebuilt
        self._registry_tasks = []  # references keep the tasks from being garbage collected

    # key layout assumes namespaces without ':' (true for socket.io defaults), rooms may contain it
    def _node_channel(self, instance_id):
        return f'{self.channel}:node:{instance_id}'

    def _instance_rooms_key(self, instance_id):
        return f'{self.channel}:rooms:{instance_id}'

    def _room_key(self, namespace, room):
        return f'{self.channel}:room:{namespace}:{room}'

    def _alive_key(self, instance_id):
        return f'{self.channel}:alive:{instance_id}'

    def _ensure_redis(self):
        if not self.connected:
            self._redis_connect()
            # a fresh connection may see a different dataset (restart, failover)
            self._arm_distrust(True)
            self._reconcile_own_rooms()

    def initialize(self):
        super().initialize()
        if not self.write_only:
            self._registry_tasks = [
                self.server.start_background_task(self._registry_writer),
                self.server.start_background_task(self._registry_heartbeat),
            ]

    async def emit(self, event, data, namespace=None, room=None, skip_sid=None, callback=None, to=None, **kwargs):
        room = to or room
        namespace = namespace or '/'
        # callback emits are never dropped: a lost ack blocks the caller, not just a UI update
        if (
            isinstance(room, str)
            and callback is None
            and not kwargs.get('ignore_queue')
            and room not in self.rooms.get(namespace, {})
        ):
            remote_instances = await self._remote_instances(namespace, room)
            if remote_instances is not None and not remote_instances:
                # no members anywhere in the fleet: skip serialization entirely
                return
        return await super().emit(
            event, data, namespace=namespace, room=room, skip_sid=skip_sid, callback=callback, **kwargs
        )

    async def _publish(self, data):
        method = data.get('method')
        if method == 'callback':
            # acks go straight back to the originating instance
            return await self._publish_to_channels([self._node_channel(data['host_id'])], data)
        room = data.get('room')
        if method != 'emit' or not isinstance(room, str):
            return await super()._publish(data)
        if self.is_connected(room, data['namespace']):
            # the parent emit already delivered locally and an ack resolves locally too
            return
        remote_instances = await self._remote_instances(data['namespace'], room)
        if remote_instances is None or (data.get('callback') and not remote_instances):
            # registry unavailable, or an ack is expected and no route is known:
            # deliver like the stock hub manager
            return await super()._publish(data)
        if remote_instances:
            return await self._publish_to_channels(
                [self._node_channel(instance_id) for instance_id in remote_instances], data
            )
        # members are local only and the parent emit already delivered to them

    async def _remote_instances(self, namespace, room):
        """Instance ids holding members of the room, or None when unknown."""
        cache_key = (namespace, room)
        cached = self._route_cache.get(cache_key)
        now = time.monotonic()
        if cached and cached[1] > now:
            instances = cached[0]
            if instances is None:
                return None
        else:
            if now < self._distrust_until:
                # the registry may be missing entries of live peers (rebuild after a
                # wipe or prune, a peer whose writes fail): suspend routing entirely
                self._route_cache[cache_key] = (None, now + 1)
                return None
            epoch = self._route_epoch
            _, redis_error = self._get_redis_module_and_error()
            try:
                self._ensure_redis()
                pipe = self.redis.pipeline(transaction=False)
                pipe.hkeys(self._room_key(namespace, room))
                pipe.exists(self._alive_key(self.host_id))
                members, own_alive = await pipe.execute()
            except Exception as exc:
                if isinstance(exc, redis_error):
                    self.connected = False
                if not self._registry_read_down:
                    self._registry_read_down = True
                    self._get_logger().error(
                        'Cannot read the socket.io room registry, falling back to broadcast',
                        extra={'redis_exception': str(exc)},
                    )
                # remember the failure briefly so an outage costs one read per room per second
                self._route_cache[cache_key] = (None, now + 1)
                return None
            self._registry_read_down = False
            if not members and not own_alive:
                # empty read while our own liveness key is missing: the registry may
                # have been wiped (restart, failover, eviction), so do not trust it
                self._route_cache[cache_key] = (None, now + 1)
                return None
            if epoch != self._route_epoch:
                # an invalidation landed mid-read, the result may already be stale
                return None
            instances = frozenset(to_str(instance_id) for instance_id in members)
            self._route_cache[cache_key] = (instances, now + self.ROUTE_CACHE_TTL)
        return instances - {self.host_id}

    async def _publish_to_channels(self, channels, message):
        _, error = self._get_redis_module_and_error()
        payload = self.json.dumps(message)
        for retries_left in (1, 0):
            try:
                self._ensure_redis()
                pipe = self.redis.pipeline(transaction=False)
                for channel in channels:
                    pipe.publish(channel, payload)
                return await pipe.execute()
            except error as exc:
                self.connected = False
                self._get_logger().error(
                    'Cannot publish routed message to redis... ' + ('retrying' if retries_left else 'giving up'),
                    extra={'redis_exception': str(exc)},
                )

    async def _redis_listen_with_retries(self):
        # copied from AsyncRedisManager (5.16) with the routing subscribe list and
        # missed-ctl compensation added; re-check on upgrades
        _, error = self._get_redis_module_and_error()
        retry_sleep = 1
        subscribed = False
        while True:
            try:
                if not subscribed:
                    self._redis_connect()
                    await self.pubsub.subscribe(self.channel, self._own_node_channel, self._ctl_channel)
                    # ctl messages may have been missed while unsubscribed
                    self._arm_distrust()
                    self._reconcile_own_rooms()
                    retry_sleep = 1
                async for message in self.pubsub.listen():
                    yield message
            except error as exc:
                self._get_logger().error(
                    f'Cannot receive from redis... retrying in {retry_sleep} secs', extra={'redis_exception': str(exc)}
                )
                subscribed = False
                await asyncio.sleep(retry_sleep)
                retry_sleep *= 2
                if retry_sleep > 60:
                    retry_sleep = 60

    async def _listen(self):
        ctl_channel = self._ctl_channel.encode()
        message_channels = {self.channel.encode(), self._own_node_channel.encode()}
        async for message in self._redis_listen_with_retries():
            if message['type'] != 'message' or 'data' not in message:
                continue
            channel = message['channel']
            channel = channel.encode() if isinstance(channel, str) else channel
            if channel == ctl_channel:
                self._handle_route_change(message['data'])
            elif channel in message_channels:
                yield message['data']

    def _handle_route_change(self, payload):
        self._last_ctl_seen = time.monotonic()
        try:
            data = self.json.loads(payload)
        except Exception:
            return
        if not isinstance(data, dict) or data.get('host_id') == self.host_id:
            return
        if data.get('method') == 'ctl_ping':
            return
        self._route_epoch += 1
        if data.get('method') == 'registry_distrust':
            # a live peer may be missing registry entries (pruned while stalled or its
            # writes are failing), distrust empty reads until the fleet re-registered.
            # a prune arms long: a pruned-but-alive peer is at least a TTL behind, so
            # the window must outlast its recovery or its users lose messages
            self._arm_distrust(True, seconds=2 * self.INSTANCE_TTL if data.get('pruned') else None, rebuilt=True)
            self._route_cache.clear()
            if self.host_id in (data.get('pruned') or ()):
                # that peer is us: re-register everything now, not at the next heartbeat
                self._reconcile_own_rooms()
            return
        self._route_cache.pop((data.get('namespace'), data.get('room')), None)

    # every local membership change funnels through these two hooks
    def basic_enter_room(self, sid, namespace, room, eio_sid=None):
        super().basic_enter_room(sid, namespace, room, eio_sid=eio_sid)
        if room is not None:
            self._dirty_rooms[(namespace, room)] = room == sid
            self._dirty_event.set()

    def basic_leave_room(self, sid, namespace, room):
        super().basic_leave_room(sid, namespace, room)
        if room is not None:
            self._dirty_rooms[(namespace, room)] = room == sid
            self._dirty_event.set()

    async def _registry_writer(self):
        retry_sleep = 1
        while True:
            await self._dirty_event.wait()
            self._dirty_event.clear()
            dirty = self._dirty_rooms
            self._dirty_rooms = {}
            try:
                self._syncing = True
                await self._sync_rooms(dirty)
                retry_sleep = 1
                self._writes_failing = False
            except Exception:
                self._writes_failing = True
                if retry_sleep == 1:
                    self._get_logger().exception('socket.io room registry sync failed, retrying')
                    # tell the fleet right away instead of waiting for the next
                    # heartbeat, memberships written during the gap would be invisible
                    try:
                        await self.redis.publish(
                            self._ctl_channel,
                            self.json.dumps({'method': 'registry_distrust', 'host_id': self.host_id}),
                        )
                    except Exception:
                        pass
                else:
                    self._get_logger().error('socket.io room registry sync still failing')
                self._dirty_rooms = dirty | self._dirty_rooms
                await asyncio.sleep(retry_sleep)
                retry_sleep = min(retry_sleep * 2, 30)
                self._dirty_event.set()
            finally:
                self._syncing = False

    async def _sync_rooms(self, rooms):
        """Write local membership for the given rooms to Redis, unconditionally.

        Writing without comparing against previous state keeps the registry self-healing:
        lost or partially applied updates are repaired by the next write or reconcile pass.
        """
        self._ensure_redis()
        # registration first so even partially written state is always prunable; the
        # liveness key is deliberately left to the heartbeat, which stops refreshing
        # it while writes fail so a degraded instance lapses instead of lingering
        self._arm_distrust(await self.redis.sadd(self._instances_key, self.host_id), rebuilt=True)
        route_changes = []
        mirror_adds = []
        mirror_removes = []
        entries = [
            (namespace, room, is_sid_room, len(self.rooms.get(namespace, {}).get(room, ())))
            for (namespace, room), is_sid_room in rooms.items()
        ]
        for chunk_start in range(0, len(entries), self.SYNC_CHUNK_SIZE):
            chunk = entries[chunk_start : chunk_start + self.SYNC_CHUNK_SIZE]
            pipe = self.redis.pipeline(transaction=False)
            for namespace, room, _, count in chunk:
                field = f'{namespace}:{room}'
                if count:
                    pipe.hset(self._room_key(namespace, room), self.host_id, count)
                    pipe.hset(self._own_rooms_key, field, count)
                else:
                    pipe.hdel(self._room_key(namespace, room), self.host_id)
                    pipe.hdel(self._own_rooms_key, field)
            results = await pipe.execute()
            for index, (namespace, room, is_sid_room, count) in enumerate(chunk):
                was_written = (namespace, room) in self._written_rooms
                if count:
                    mirror_adds.append((namespace, room))
                    # hset created the field although we wrote it before: Redis lost the
                    # entry (wipe or wrongful prune), invalidate peer caches right away,
                    # for sid rooms too since peers cache those routes as well
                    repaired = was_written and results[2 * index] == 1
                    if (not is_sid_room and not was_written) or repaired:
                        route_changes.append((namespace, room))
                elif was_written:
                    mirror_removes.append((namespace, room))
                    if not is_sid_room:
                        route_changes.append((namespace, room))
        if route_changes and time.monotonic() < self._rebuild_until:
            # after a registry rebuild per-room invalidations would only add to the
            # storm they ride on; one blanket distrust replaces them and also covers
            # a lone wrongfully wiped instance whose peers are not armed after all
            route_changes = []
            await self.redis.publish(
                self._ctl_channel, self.json.dumps({'method': 'registry_distrust', 'host_id': self.host_id})
            )
        for chunk_start in range(0, len(route_changes), self.SYNC_CHUNK_SIZE):
            pipe = self.redis.pipeline(transaction=False)
            for namespace, room in route_changes[chunk_start : chunk_start + self.SYNC_CHUNK_SIZE]:
                pipe.publish(
                    self._ctl_channel,
                    self.json.dumps(
                        {'method': 'route_change', 'namespace': namespace, 'room': room, 'host_id': self.host_id}
                    ),
                )
            await pipe.execute()
        # mirror updated last so a failed ctl publish retries its transitions too
        self._written_rooms.update(mirror_adds)
        self._written_rooms.difference_update(mirror_removes)

    def _arm_distrust(self, needed=True, seconds=None, rebuilt=False):
        # the registry may be missing entries of live peers (rebuild, prune, failing
        # writer): routing is suspended until the fleet had time to re-register
        if not self._registry_tasks:
            # no heartbeat and no ctl listener yet (socketio initializes the manager
            # on the first socket connect, and write_only managers never do): this
            # process is deaf to the distrust protocol, keep routing suspended
            return
        if not needed:
            return
        until = time.monotonic() + (seconds or 2 * self.HEARTBEAT_INTERVAL)
        # a shorter arm never truncates an active longer window; the first finite
        # arm deliberately replaces the boot-time infinity
        if self._distrust_until == float('inf') or until > self._distrust_until:
            self._distrust_until = until
        if rebuilt and until > self._rebuild_until:
            self._rebuild_until = until

    async def _registry_heartbeat(self):
        failures = 0
        beats = 0
        last_wall = time.time()
        while True:
            beats += 1
            now = time.monotonic()
            wall = time.time()
            if wall - last_wall > 3 * self.HEARTBEAT_INTERVAL:
                # wall time jumped several beats ahead: the process was suspended and
                # every monotonic-frozen deadline and cache entry is stale in real time
                self._route_cache.clear()
                self._arm_distrust(True, rebuilt=True)
                self._reconcile_own_rooms()
            last_wall = wall
            # swept unconditionally, the cache keeps filling during Redis degradations
            self._route_cache = {key: route for key, route in self._route_cache.items() if route[1] > now}
            try:
                if self._writes_failing:
                    # registry writes are failing while our rooms drift: let the liveness
                    # key lapse and keep the fleet distrusting empty reads meanwhile
                    # (PUBLISH tends to still work when write commands are rejected)
                    try:
                        await self.redis.publish(
                            self._ctl_channel,
                            self.json.dumps({'method': 'registry_distrust', 'host_id': self.host_id}),
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                    continue
                self._ensure_redis()
                syncing = self._syncing
                pipe = self.redis.pipeline(transaction=False)
                pipe.sadd(self._instances_key, self.host_id)
                pipe.set(self._alive_key(self.host_id), '1', ex=self.INSTANCE_TTL)
                pipe.hlen(self._own_rooms_key)
                pipe.publish(self._ctl_channel, self.json.dumps({'method': 'ctl_ping', 'host_id': self.host_id}))
                newly_added, _, stored_count, _ = await pipe.execute()
                self._arm_distrust(newly_added, rebuilt=True)
                if time.monotonic() - self._last_ctl_seen > 3 * self.HEARTBEAT_INTERVAL:
                    # our own pings are not echoing back: the subscriber connection is
                    # dead even though commands work, stop routing and force a rebuild
                    self._arm_distrust(True)
                    try:
                        if self.pubsub is not None and self.pubsub.connection is not None:
                            await self.pubsub.connection.disconnect()
                    except Exception:
                        pass
                    self._get_logger().error('socket.io ctl subscription is silent, forcing a resubscribe')
                if self._pruned_peers:
                    pruned_ids, repeat_until = self._pruned_peers
                    if time.monotonic() < repeat_until:
                        # repeated so peers whose subscription silently cycled
                        # (client-level reconnects never surface here) still learn of it
                        await self.redis.publish(
                            self._ctl_channel,
                            self.json.dumps(
                                {'method': 'registry_distrust', 'host_id': self.host_id, 'pruned': pruned_ids}
                            ),
                        )
                    else:
                        self._pruned_peers = None
                # Redis visibly lost entries: rewrite everything (the mirror is only
                # comparable while no sync was mid-flight around the HLEN) and assume
                # peers' entries went missing too, e.g. a failover losing recent writes
                if not syncing and not self._syncing and stored_count != len(self._written_rooms):
                    self._arm_distrust(True, rebuilt=True)
                    self._reconcile_own_rooms()
                elif beats % 20 == 0:
                    # low frequency full pass: catches count-balanced losses the HLEN
                    # comparison cannot see, e.g. a failover losing one add and one remove
                    self._reconcile_own_rooms()
                await self._prune_dead_instances()
                failures = 0
            except Exception:
                failures += 1
                if failures == 1:
                    self._get_logger().exception('socket.io registry heartbeat failed')
                else:
                    self._get_logger().error('socket.io registry heartbeat still failing')
            await asyncio.sleep(self.HEARTBEAT_INTERVAL * (1 + random.random() / 4))

    def _reconcile_own_rooms(self):
        # remark everything dirty so the writer repairs drift, including a wrongful prune
        for namespace, namespace_rooms in self.rooms.items():
            connected_sids = namespace_rooms.get(None) or ()
            for room in namespace_rooms:
                if room is not None:
                    self._dirty_rooms.setdefault((namespace, room), room in connected_sids)
        if self._dirty_rooms:
            self._dirty_event.set()

    async def _prune_dead_instances(self):
        # one pruner per interval; overlapping prunes would be idempotent anyway
        if not await self.redis.set(
            f'{self.channel}:prune_lock', self.host_id, nx=True, px=int(self.HEARTBEAT_INTERVAL * 1000)
        ):
            return
        peer_ids = [to_str(raw_id) for raw_id in await self.redis.smembers(self._instances_key)]
        peer_ids = [peer_id for peer_id in peer_ids if peer_id != self.host_id]
        if not peer_ids:
            return
        pipe = self.redis.pipeline(transaction=False)
        for peer_id in peer_ids:
            pipe.exists(self._alive_key(peer_id))
        alive_flags = await pipe.execute()
        pruned_ids = []
        for peer_id, alive in zip(peer_ids, alive_flags):
            if alive:
                continue
            # distrust ctl BEFORE deleting anything: the peer might be alive but
            # stalled, and if this prune is interrupted midway the named peer still
            # reconciles itself instead of staying silently unroutable
            await self.redis.publish(
                self._ctl_channel,
                self.json.dumps({'method': 'registry_distrust', 'host_id': self.host_id, 'pruned': [peer_id]}),
            )
            self._arm_distrust(True, seconds=2 * self.INSTANCE_TTL, rebuilt=True)
            self._route_epoch += 1
            self._route_cache.clear()
            rooms_key = self._instance_rooms_key(peer_id)
            fields = await self.redis.hkeys(rooms_key)
            revived = False
            for chunk_start in range(0, len(fields), self.SYNC_CHUNK_SIZE):
                # re-checked before every destructive step: the peer may have come
                # back, or this coroutine may resume from a long pause into a world
                # where every guard window already expired in real time
                if await self.redis.exists(self._alive_key(peer_id)):
                    revived = True
                    break
                pipe = self.redis.pipeline(transaction=False)
                for field in fields[chunk_start : chunk_start + self.SYNC_CHUNK_SIZE]:
                    namespace, _, room = to_str(field).partition(':')
                    pipe.hdel(self._room_key(namespace, room), peer_id)
                await pipe.execute()
            if revived or await self.redis.exists(self._alive_key(peer_id)):
                continue
            # deleted last so an interrupted prune leaves the peer in the instances
            # set and a later prune cycle finishes the cleanup
            pipe = self.redis.pipeline(transaction=False)
            pipe.delete(rooms_key)
            pipe.srem(self._instances_key, peer_id)
            await pipe.execute()
            pruned_ids.append(peer_id)
            self._get_logger().info(f'Pruned dead socket.io instance {peer_id}')
        if pruned_ids:
            self._pruned_peers = (pruned_ids, time.monotonic() + 2 * self.INSTANCE_TTL)
