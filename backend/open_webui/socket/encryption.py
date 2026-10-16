"""Volatile packet relay. Only account bindings and liveness enter coordination storage."""

import asyncio
import base64
import hashlib
import json
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from copy import deepcopy
from uuid import uuid4

from open_webui.config import DEFAULT_USER_PERMISSIONS
from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
    ENV,
    REDIS_KEY_PREFIX,
    WEBSOCKET_SERVER_ENGINEIO_LOGGING,
    WEBSOCKET_SERVER_LOGGING,
)
from open_webui.models.channels import Channels
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.users import Users
from open_webui.utils.access_control import combine_permissions, fill_missing_permissions

MAX_PACKET = 1024 * 1024
TTL = 90


class Rejected(Exception):
    pass


def require(condition):
    if not condition:
        raise Rejected()


def packet(value):
    require(isinstance(value, str) and 0 < len(value) <= (MAX_PACKET + 2) // 3 * 4)
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise Rejected() from None
    require(0 < len(decoded) <= MAX_PACKET)
    return value


class Registry:
    def __init__(self, redis=None):
        self.redis = redis
        self.values = {}
        self.lock = asyncio.Lock()
        self.lease = ContextVar('encryption_lease', default=None)

    def key(self, channel):
        digest = hashlib.sha256(channel.encode()).hexdigest()
        return f'{REDIS_KEY_PREFIX}:encryption:{{{digest}}}'

    @asynccontextmanager
    async def transaction(self, channel):
        key = self.key(channel)
        lock = self.redis.lock(key + ':lock', timeout=10, blocking_timeout=2) if self.redis else self.lock
        async with lock:
            raw = await self.redis.get(key) if self.redis else self.values.get(key)
            state = json.loads(raw) if raw else None
            if state and state['expires'] <= time.time():
                state = None
            token = self.lease.set(lock if self.redis else None)
            try:
                yield state
            finally:
                self.lease.reset(token)

    async def save(self, channel, state):
        key = self.key(channel)
        if state is not None:
            state['expires'] = time.time() + TTL
        raw = json.dumps(state, separators=(',', ':')) if state is not None else ''
        if self.redis:
            lease = self.lease.get()
            require(lease is not None)
            # A stalled worker must never overwrite a newer owner's metadata.
            changed = await self.redis.eval(
                "if redis.call('get', KEYS[2]) ~= ARGV[1] then return 0 end "
                "if ARGV[2] == '' then redis.call('del', KEYS[1]) "
                "else redis.call('set', KEYS[1], ARGV[2], 'EX', ARGV[3]) end return 1",
                2,
                key,
                key + ':lock',
                lease.local.token,
                raw,
                TTL,
            )
            if not changed:
                raise RuntimeError('Coordination lease expired')
        elif state is None:
            self.values.pop(key, None)
        else:
            self.values[key] = raw


class Relay:
    def __init__(self, sio, authenticate, redis=None):
        self.sio, self.authenticate = sio, authenticate
        self.registry = Registry(redis)
        self.local = {}  # sid -> channel, never payloads
        self.rates = {}
        for action in ('start', 'status', 'join', 'bind', 'packet', 'leave', 'ping'):

            async def handler(sid, data=None, action=action):
                return await self.handle(action, sid, data)

            sio.on(f'encryption:{action}', handler)

    async def authorize(self, sid, channel):
        require(ENABLE_WEBSOCKET_SUPPORT and self.sio.transport(sid) == 'websocket')
        require(not WEBSOCKET_SERVER_LOGGING and not WEBSOCKET_SERVER_ENGINEIO_LOGGING)
        scope = (self.sio.get_environ(sid) or {}).get('asgi.scope', {})
        require(ENV != 'prod' or scope.get('scheme') in ('https', 'wss'))
        auth = await self.authenticate(sid, wait_for_disconnect=False)
        require(auth and auth.get('id'))
        user = await Users.get_user_by_id(auth['id'])
        require(user and user.role in ('user', 'admin'))
        record = await Channels.get_channel_by_id(channel)
        require(record and (record.type == 'dm' or (record.type == 'group' and record.is_private is True)))
        require(await Channels.is_user_channel_member(channel, user.id))
        return user

    @staticmethod
    def view(state):
        if not state:
            return None
        return {
            'channel': state['channel'],
            'session': state['session'],
            'host': state['host'],
            'bindings': [
                {
                    'identity': {
                        'channel': state['channel'],
                        'session': state['session'],
                        'user': p['user'],
                        'participation': pid,
                    },
                    'key': p['key'],
                }
                for pid, p in state['members'].items()
                if p.get('key')
            ],
            'participants': [
                {'participation': pid, 'user': p['user'], 'name': p['name']} for pid, p in state['members'].items()
            ],
        }

    async def invite(self, state, channel):
        await self.sio.emit(
            'encryption:available',
            {'channel': channel, 'session': state['session'] if state else None},
            room=f'channel:{channel}',
        )

    async def deliver(self, state, recipients, event):
        # Per-recipient sequence detects missing Pub/Sub deliveries without storing packets.
        targets = []
        for pid in recipients:
            member = state['members'][pid]
            member['out'] += 1
            targets.append((member['sid'], member['out']))
        await self.registry.save(state['channel'], state)
        for sid, sequence in targets:
            await self.sio.emit('encryption:event', {**event, **self.view(state), 'sequence': sequence}, to=sid)

    async def close(self, channel, state):
        await self.registry.save(channel, None)
        if state:
            for p in state['members'].values():
                self.local.pop(p['sid'], None)
                await self.sio.emit(
                    'encryption:event', {'kind': 'ended', 'channel': channel, 'session': state['session']}, to=p['sid']
                )
        await self.invite(None, channel)

    async def eligible_users(self, user_ids):
        config = await Config.get_many('channels.enable', 'channels.encryption.enable', 'user.permissions')
        if not config['channels.enable'] or not config['channels.encryption.enable']:
            return {}
        defaults = fill_missing_permissions(deepcopy(config['user.permissions'] or {}), DEFAULT_USER_PERMISSIONS)
        users = await Users.get_users_by_user_ids(list(set(user_ids)))
        groups = await Groups.get_groups_by_member_ids(
            [u.id for u in users if u.role == 'user'], include_inherited=True
        )
        eligible = {}
        for user in users:
            if user.role == 'admin':
                eligible[user.id] = user
            elif user.role == 'user':
                permissions = deepcopy(defaults)
                for group in groups[user.id]:
                    combine_permissions(permissions, group.permissions or {})
                features = permissions.get('features', {})
                if features.get('channels') and features.get('encrypted_channels'):
                    eligible[user.id] = user
        return eligible

    async def prune(self, state, eligible=None):
        if not state:
            return None
        if eligible is None:
            eligible = await self.eligible_users([p['user'] for p in state['members'].values()])
        members = await Channels.get_members_by_channel_id(state['channel'])
        active = {m.user_id for m in members if m.is_active}
        stale = [
            pid
            for pid, p in state['members'].items()
            if p['seen'] < time.time() - 45 or p['user'] not in active or p['user'] not in eligible
        ]
        if state['host'] in stale:
            await self.close(state['channel'], state)
            return None
        if stale:
            await self.remove(state, *stale)
        return state

    async def remove(self, state, *pids):
        if state['host'] in pids:
            await self.close(state['channel'], state)
            return
        # Exclude every revoked recipient before any departure event is forwarded.
        removed = [(pid, state['members'].pop(pid)) for pid in pids]
        for pid, p in removed:
            self.local.pop(p['sid'], None)
            await self.sio.emit(
                'encryption:event',
                {'kind': 'ended', 'channel': state['channel'], 'session': state['session']},
                to=p['sid'],
            )
            await self.deliver(
                state,
                [i for i, m in state['members'].items() if m['admitted']],
                {'kind': 'departed', 'participation': pid, 'admitted': p['admitted']},
            )

    async def limit(self, user, action, size):
        now = time.monotonic()
        if len(self.rates) > 10000:
            self.rates = {k: v for k, v in self.rates.items() if now - v[0] < 60}
        if self.registry.redis:
            bucket = 'admission' if action in ('start', 'join') else 'traffic'
            period, maximum = (60, 10) if bucket == 'admission' else (1, 100)
            key = self.registry.key('rate:' + user + ':' + bucket)
            allowed = await self.registry.redis.eval(
                "local n = redis.call('hincrby', KEYS[1], 'count', 1) "
                "local b = redis.call('hincrby', KEYS[1], 'bytes', ARGV[1]) "
                "if n == 1 then redis.call('expire', KEYS[1], ARGV[2]) end "
                'if n > tonumber(ARGV[3]) or b > tonumber(ARGV[4]) then return 0 end return 1',
                1,
                key,
                size,
                period,
                maximum,
                4 * MAX_PACKET,
            )
            require(allowed)
            return
        # Account-wide admission bound also applies across tabs on this worker.
        key = (user, 'admission' if action in ('start', 'join') else 'traffic')
        period, maximum = (60, 10) if key[1] == 'admission' else (1, 100)
        start, count, total = self.rates.get(key, (now, 0, 0))
        if now - start >= period:
            start, count, total = now, 0, 0
        require(count < maximum and total + size <= 4 * MAX_PACKET)
        self.rates[key] = (start, count + 1, total + size)

    async def reserve(self, action, sid, user, channel, data, state):
        # Another worker may have closed the session; its metadata is authoritative.
        if self.local.get(sid) == channel and (
            not state or not any(p['sid'] == sid for p in state['members'].values())
        ):
            self.local.pop(sid, None)
        require(sid not in self.local)
        if action == 'start':
            require(state is None)
            pid = str(uuid4())
            state = {'channel': channel, 'session': str(uuid4()), 'host': pid, 'members': {}}
        else:
            require(state and data.get('session') == state['session'])
            require(len(state['members']) < 128 and not any(p['user'] == user.id for p in state['members'].values()))
            require(state['members'][state['host']].get('key'))
            pid = str(uuid4())
        state['members'][pid] = {
            'sid': sid,
            'user': user.id,
            'name': user.name,
            'key': None,
            'seen': time.time(),
            'out': 0,
            'admitted': action == 'start',
        }
        self.local[sid] = channel
        await self.registry.save(channel, state)
        return {'ok': True, **self.view(state), 'participation': pid}

    async def bind(self, state, pid, member, data):
        require(member['key'] is None)
        key = packet(data.get('key'))
        require(len(base64.b64decode(key)) == 32)
        member['key'] = key
        if pid != state['host']:
            kp = packet(data.get('packet'))
            await self.deliver(state, [state['host']], {'kind': 'candidate', 'sender': pid, 'packet': kp})
        else:
            await self.registry.save(state['channel'], state)
            await self.invite(state, state['channel'])

    async def forward(self, state, pid, member, data):
        require(member['key'] and member['admitted'])
        body = packet(data.get('packet'))
        if data.get('kind') == 'admit':
            require(pid == state['host'])
            target = data.get('target')
            joining = state['members'].get(target)
            require(joining and joining.get('key') and not joining['admitted'])
            welcome = packet(data.get('welcome'))
            existing = [i for i, p in state['members'].items() if i != pid and p['admitted']]
            joining['admitted'] = True
            await self.deliver(state, existing, {'kind': 'mls', 'sender': pid, 'packet': body})
            await self.deliver(state, [target], {'kind': 'welcome', 'sender': pid, 'packet': welcome})
        else:
            require(data.get('kind') == 'mls')
            recipients = [i for i, p in state['members'].items() if i != pid and p['admitted']]
            await self.deliver(state, recipients, {'kind': 'mls', 'sender': pid, 'packet': body})

    async def handle(self, action, sid, data):
        channel = None
        authorized = False
        try:
            require(isinstance(data, dict))
            channel = data.get('channel')
            require(isinstance(channel, str) and 0 < len(channel) <= 128)
            size = len(json.dumps(data))
            require(size <= 3 * MAX_PACKET)
            user = await self.authorize(sid, channel)
            authorized = True
            await self.limit(user.id, action, size)
            async with self.registry.transaction(channel) as state:
                # Read current policy after waiting for the channel's coordination lock.
                eligible = await self.eligible_users(
                    [user.id, *([p['user'] for p in state['members'].values()] if state else [])]
                )
                state = await self.prune(state, eligible)
                require(user.id in eligible)
                user = eligible[user.id]
                require(await Channels.is_user_channel_member(channel, user.id))
                if action == 'status':
                    return {
                        'ok': True,
                        'available': bool(state and state['members'][state['host']].get('key')),
                        'session': state['session'] if state else None,
                    }
                if action in ('start', 'join'):
                    return await self.reserve(action, sid, user, channel, data, state)
                require(state and data.get('session') == state['session'] and self.local.get(sid) == channel)
                pid = data.get('participation')
                member = state['members'].get(pid)
                require(member and member['sid'] == sid and member['user'] == user.id)
                member['seen'] = time.time()
                if action == 'leave':
                    await self.remove(state, pid)
                    return {'ok': True}
                if action == 'bind':
                    await self.bind(state, pid, member, data)
                elif action == 'ping':
                    await self.registry.save(channel, state)
                elif action == 'packet':
                    await self.forward(state, pid, member, data)
                else:
                    raise Rejected()
                return {'ok': True, **self.view(state)}
        except Rejected:
            return {'ok': False, 'error': 'Private chat is unavailable or the session changed.'}
        except Exception:
            # Never log exceptions carrying packet input. Fail closed on coordinator failure.
            if authorized:
                await self.fail_local(channel)
            return {'ok': False, 'error': 'Private chat ended.'}

    async def fail_local(self, channel):
        for sid, local_channel in list(self.local.items()):
            if channel is None or local_channel == channel:
                self.local.pop(sid, None)
                await self.sio.emit(
                    'encryption:event', {'kind': 'ended', 'channel': local_channel}, to=sid, ignore_queue=True
                )

    async def disconnect(self, sid):
        channel = self.local.pop(sid, None)
        if not channel:
            return
        try:
            async with self.registry.transaction(channel) as state:
                if state:
                    for pid, p in list(state['members'].items()):
                        if p['sid'] == sid:
                            await self.remove(state, pid)
                            break
        except Exception:
            await self.fail_local(channel)

    async def invalidate(self, channel):
        # Channel access mutations end the session before any further private sends.
        try:
            async with self.registry.transaction(channel) as state:
                await self.close(channel, state)
        except Exception:
            await self.fail_local(channel)

    async def sweep(self):
        for channel in set(self.local.values()):
            try:
                async with self.registry.transaction(channel) as state:
                    if not state:
                        await self.fail_local(channel)
                    else:
                        await self.prune(state)
            except Exception:
                await self.fail_local(channel)
        if not self.registry.redis:
            for key, raw in list(self.registry.values.items()):
                if json.loads(raw)['expires'] <= time.time():
                    self.registry.values.pop(key, None)
