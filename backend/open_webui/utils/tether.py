"""Ephemeral reverse connections and streaming service transport."""

import asyncio
import json
import re
import struct
import time
from contextlib import suppress
from types import SimpleNamespace
from urllib.parse import urlsplit, urlencode
from uuid import uuid4

import aiohttp
from multidict import CIMultiDict
from fastapi import HTTPException
from open_webui.env import REDIS_KEY_PREFIX, UVICORN_WORKERS
from open_webui.models.auth_sessions import AuthSessions
from open_webui.models.config import Config

CHUNK = 65536
WINDOW = 2 * 1024 * 1024
MAX_MESSAGE = 16 * 1024 * 1024


class RelayInterrupted(ConnectionError):
    def __init__(self, reason='Connection lost'):
        super().__init__(
            f'Tether connection interrupted: {reason}. '
            'The operation may have completed. Check its result before trying again; do not automatically repeat it.'
        )

    def result(self):
        return {'error': str(self), 'code': 'tether_interrupted', 'outcome': 'unknown', 'retryable': False}


def get_services(value):
    if (
        not isinstance(value, list)
        or len(value) > 16
        or any(not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,31}', name) for name in value)
    ):
        raise ValueError('Invalid Tether services')
    return list(dict.fromkeys(value))


def encode(header, data=b''):
    raw = json.dumps(header, separators=(',', ':')).encode()
    if len(raw) > 4096 or len(data) > CHUNK:
        raise ValueError('Relay packet too large')
    return struct.pack('!I', len(raw)) + raw + data


def decode(raw):
    if len(raw) < 4 or len(raw) > CHUNK + 4100:
        raise ValueError('Invalid relay packet')
    length = struct.unpack('!I', raw[:4])[0]
    if length > 4096 or length > len(raw) - 4:
        raise ValueError('Invalid relay header')
    header = json.loads(raw[4 : 4 + length])
    if (
        not isinstance(header, dict)
        or not isinstance(header.get('stream'), str)
        or len(header['stream']) != 36
        or type(header.get('sequence')) is not int
        or header['sequence'] < 0
    ):
        raise ValueError('Invalid relay header')
    return header, raw[4 + length :]


class Stream:
    def __init__(self, owner, presence):
        self.id = str(uuid4())
        self.owner, self.presence = owner, presence
        self.sequence = self.incoming = 0
        self.window = presence.get('window', 256 * 1024)
        self.credit = self.receive_credit = self.window
        self.wake = asyncio.Event()
        self.queue = asyncio.Queue(maxsize=64)
        self.closed = False
        self.lock = asyncio.Lock()
        self.error = None
        self.cleanup = None
        self.timeout_handle = None
        self.read_timeout = None

    def set_timeout(self, timeout):
        self.read_timeout = timeout.sock_read if timeout.sock_read and timeout.sock_read > 0 else None
        if timeout.total and timeout.total > 0:
            self.timeout_handle = asyncio.get_running_loop().call_later(timeout.total, self.fail, 'Request timed out')

    async def send(self, operation, data=b'', **fields):
        while len(data) > self.credit and not self.closed:
            self.wake.clear()
            try:
                await asyncio.wait_for(self.wake.wait(), 300)
            except TimeoutError as error:
                self.fail('Send timed out')
                raise self.error from error
        if self.closed:
            raise self.error or RelayInterrupted('Stream closed')
        self.credit -= len(data)
        async with self.lock:
            if self.closed:
                raise self.error or RelayInterrupted('Stream closed')
            header = dict(fields, type=operation, stream=self.id, sequence=self.sequence)
            self.sequence += 1
            try:
                await self.owner.send(self.presence, header, data)
            except (OSError, TimeoutError) as error:
                self.fail(str(error) or 'Send failed')
                raise self.error from error

    def feed(self, header, data):
        if self.closed:
            return
        if header['sequence'] != self.incoming:
            self.fail('Missing relay packet')
            return
        self.incoming += 1
        if header['type'] == 'window':
            count = header.get('bytes')
            if type(count) is not int or count <= 0 or self.credit + count > self.window:
                self.fail('Invalid relay window')
            else:
                self.credit += count
                self.wake.set()
            return
        if len(data) > self.receive_credit:
            self.fail('Receive window exceeded')
            return
        self.receive_credit -= len(data)
        try:
            self.queue.put_nowait((header, data))
        except asyncio.QueueFull:
            self.fail('Relay consumer too slow')

    def fail(self, message):
        self.error = RelayInterrupted(message)
        self.closed = True
        self.wake.set()
        while not self.queue.empty():
            self.queue.get_nowait()
        self.queue.put_nowait(({'type': 'error', 'message': message}, b''))

    async def receive(self):
        if self.error:
            raise self.error
        try:
            header, data = await asyncio.wait_for(self.queue.get(), self.read_timeout)
        except TimeoutError as error:
            self.fail('Response timed out')
            raise self.error from error
        if header['type'] == 'error':
            self.fail(header.get('message', 'Response interrupted'))
            raise self.error
        return header, data

    async def consumed(self, count):
        if count and not self.closed:
            self.receive_credit += count
            await self.send('window', bytes=count)

    async def close(self):
        if self.cleanup is None:
            self.closed = True
            self.wake.set()
            if self.timeout_handle:
                self.timeout_handle.cancel()
            self.cleanup = asyncio.create_task(self._cleanup())
        # A cancelled consumer must not interrupt remote cleanup or send it twice.
        await asyncio.shield(self.cleanup)

    async def _cleanup(self):
        try:
            with suppress(Exception):
                async with asyncio.timeout(10):
                    async with self.lock:
                        header = dict(type='cancel', stream=self.id, sequence=self.sequence)
                        self.sequence += 1
                        # send() deliberately rejects failed streams; cancellation must still reach Tether.
                        await self.owner.send(self.presence, header, b'')
        finally:
            self.owner.streams.pop(self.id, None)


class Hub:
    def __init__(self):
        self.worker = str(uuid4())
        self.connections = {}
        self.streams = {}
        self.redis = None
        self.listener = None
        self.lock = asyncio.Lock()

    def channel(self, worker):
        return f'{REDIS_KEY_PREFIX}:tether:worker:{worker}'

    def key(self, user, connection_id):
        return f'{REDIS_KEY_PREFIX}:tether:presence:{user}:{connection_id}'

    async def start(self):
        async with self.lock:
            if self.listener and not self.listener.done():
                return
            from open_webui.env import REDIS_URL, REDIS_SENTINEL_HOSTS, REDIS_SENTINEL_PORT, REDIS_CLUSTER
            from open_webui.utils.redis import get_redis_connection, get_sentinels_from_env

            sentinels = get_sentinels_from_env(REDIS_SENTINEL_HOSTS, REDIS_SENTINEL_PORT)
            if not REDIS_URL and not sentinels:
                if UVICORN_WORKERS > 1:
                    raise HTTPException(503, 'Tether requires Redis with multiple WebUI workers.')
                return
            self.redis = get_redis_connection(
                REDIS_URL,
                redis_sentinels=sentinels,
                redis_cluster=REDIS_CLUSTER,
                async_mode=True,
                decode_responses=False,
            )
            # RedisCluster can't route a pubsub subscribe until initialize() fills its slot cache.
            await self.redis.initialize()
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(self.channel(self.worker))
            self.listener = asyncio.create_task(self.listen(pubsub))

    async def listen(self, pubsub):
        try:
            async for message in pubsub.listen():
                if message['type'] != 'message':
                    continue
                header, data = decode(message['data'])
                if header.pop('route', None) == 'connection':
                    connection = self.connections.get(header.pop('connection', ''))
                    if not connection:
                        continue
                    if header['type'] == 'notification':
                        await connection.send(header, data)
                        continue
                    reply = header.pop('reply', '')
                    if header['type'] in ('http-open', 'ws-open'):
                        if len(connection.routes) >= 16:
                            continue
                        connection.routes[header['stream']] = reply
                    elif connection.routes.get(header['stream']) != reply:
                        continue
                    try:
                        await connection.send(header, data)
                    finally:
                        if header['type'] == 'cancel':
                            connection.routes.pop(header['stream'], None)
                else:
                    stream = self.streams.get(header['stream'])
                    if stream and header.pop('connection', None) == stream.presence['connection']:
                        stream.feed(header, data)
        except Exception:
            for stream in list(self.streams.values()):
                stream.fail('Tether coordination disconnected')
            for connection in list(self.connections.values()):
                with suppress(Exception):
                    await connection.ws.close(code=1011)
        finally:
            await pubsub.aclose()

    async def presence(self, user_id, connection_id):
        await self.start()
        if self.redis:
            raw = await self.redis.get(self.key(user_id, connection_id))
            return json.loads(raw) if raw else None
        return next(
            (
                c.presence
                for c in self.connections.values()
                if c.presence['user'] == user_id and c.presence['connection_id'] == connection_id
            ),
            None,
        )

    async def presences(self, user_id):
        await self.start()
        if self.redis:
            records = []
            async for key in self.redis.scan_iter(match=self.key(user_id, '*'), count=100):
                raw = await self.redis.get(key)
                if raw:
                    records.append(json.loads(raw))
        else:
            records = [connection.presence for connection in self.connections.values()]
        # SCAN may return a key more than once while connections are changing.
        return list({record['connection_id']: record for record in records if record['user'] == user_id}.values())

    async def open(self, user_id, connection_id, service):
        presence = await self.presence(user_id, connection_id)
        if not presence or presence['user'] != user_id or presence['connection_id'] != connection_id:
            raise HTTPException(503, 'Tether is offline.')
        row = await AuthSessions.get(presence['session'])
        if not row or row.user_id != user_id or row.refresh_token_id is None or row.expires_at <= time.time():
            raise HTTPException(403, 'Tether session is no longer available.')
        if service not in presence.get('services', []):
            raise HTTPException(503, 'Tether service is unavailable.')
        if sum(s.presence['connection'] == presence['connection'] for s in self.streams.values()) >= 16:
            raise HTTPException(429, 'Tether has too many active operations.')
        stream = Stream(self, presence)
        self.streams[stream.id] = stream
        return stream

    async def send(self, presence, header, data):
        connection = self.connections.get(presence['connection'])
        if presence['worker'] == self.worker:
            if not connection:
                raise ConnectionError('Tether disconnected')
            if header['type'] in ('http-open', 'ws-open'):
                if len(connection.routes) >= 16:
                    raise HTTPException(429, 'Tether has too many active operations.')
                connection.routes[header['stream']] = self.worker
            try:
                await connection.send(header, data)
            finally:
                if header['type'] == 'cancel':
                    connection.routes.pop(header['stream'], None)
        else:
            packet = encode(
                dict(header, route='connection', connection=presence['connection'], reply=self.worker), data
            )
            if not await self.redis.publish(self.channel(presence['worker']), packet):
                raise ConnectionError('Tether worker is unavailable')

    async def returned(self, connection, header, data):
        worker = connection.routes.get(header['stream'])
        if worker == self.worker:
            stream = self.streams.get(header['stream'])
            if stream:
                stream.feed(header, data)
        elif worker:
            await self.redis.publish(
                self.channel(worker),
                encode(dict(header, route='stream', connection=connection.presence['connection']), data),
            )
        if header['type'] in ('end', 'error'):
            connection.routes.pop(header['stream'], None)


hub = Hub()


async def notify(user_id, notification_id, title, body, path):
    """Deliver only to authenticated background clients that opted into notifications."""
    from open_webui.models.users import Users

    if not user_id:
        return
    presences = [p for p in await hub.presences(user_id) if p.get('notifications')]
    if not presences:
        return
    user = await Users.get_user_by_id(user_id)
    if (
        not user
        or user.role == 'pending'
        or not user.settings
        or not (user.settings.ui or {}).get('notificationEnabled', False)
    ):
        return
    payload = json.dumps(
        {
            'id': str(notification_id)[:200],
            'user_id': user_id,
            'title': str(title)[:256],
            'body': str(body)[:4096],
            'path': path,
        }
    ).encode()
    for presence in presences:
        row = await AuthSessions.get(presence['session'])
        if not row or row.user_id != user_id or row.refresh_token_id is None or row.expires_at <= time.time():
            continue
        with suppress(Exception):
            await asyncio.wait_for(
                hub.send(
                    presence,
                    {
                        'type': 'notification',
                        'stream': str(uuid4()),
                        'sequence': 0,
                    },
                    payload,
                ),
                10,
            )


async def get_terminal_connections(user):
    """Resolve personal targets alongside existing configured servers."""
    user_id = user['id'] if isinstance(user, dict) else user.id
    connections = list(await Config.get('terminal_server.connections', []) or [])
    for presence in await hub.presences(user_id):
        if 'open_terminal' not in presence.get('services', []):
            continue
        row = await AuthSessions.get(presence['session'])
        if not row or row.user_id != user_id or row.refresh_token_id is None or row.expires_at <= time.time():
            continue
        connection_id = presence['connection_id']
        connections.append(
            {
                'id': 'tether:' + connection_id,
                'name': presence['name'],
                'url': 'tether://' + connection_id,
                'auth_type': 'none',
                'enabled': True,
                'owner_id': user_id,
                'config': {
                    'access_grants': [{'principal_type': 'user', 'principal_id': user_id, 'permission': 'read'}]
                },
            }
        )
    return connections


class Operation:
    def __init__(self, coroutine):
        self.coroutine, self.value = coroutine, None

    def __await__(self):
        return self.coroutine.__await__()

    async def __aenter__(self):
        self.value = await self.coroutine
        return self.value

    async def __aexit__(self, *_):
        if self.value:
            await self.value.close()


class RelayResponse:
    def __init__(self, stream, header, upload):
        self.stream, self.upload = stream, upload
        self.status = header['status']
        self.headers = CIMultiDict({k: str(v) for k, v in header.get('headers', {}).items()})
        self.content_type = self.headers.get('Content-Type', '').split(';')[0]
        self.content = self
        self.cached = None

    async def iter_any(self):
        while True:
            header, data = await self.stream.receive()
            if header['type'] == 'end':
                return
            if header['type'] != 'data':
                raise RelayInterrupted('Unexpected response')
            yield data
            await self.stream.consumed(len(data))

    def iter_chunked(self, size):
        return self.iter_any()

    async def read(self):
        if self.cached is None:
            parts, size = [], 0
            async for data in self.iter_any():
                size += len(data)
                if size > MAX_MESSAGE:
                    await self.close()
                    raise HTTPException(413, 'Response too large to buffer; use streaming.')
                parts.append(data)
            self.cached = b''.join(parts)
        return self.cached

    async def text(self):
        return (await self.read()).decode('utf-8', errors='replace')

    async def json(self):
        return json.loads(await self.read())

    async def close(self):
        self.upload.cancel()
        await asyncio.gather(self.upload, return_exceptions=True)
        await self.stream.close()

    release = close


class RelaySocket:
    close_code = 1000

    def __init__(self, stream):
        self.stream = stream

    async def send_bytes(self, value):
        await self.send(value, 'binary')

    async def send_str(self, value):
        await self.send(value.encode(), 'text')

    async def send(self, value, kind):
        if len(value) > MAX_MESSAGE:
            raise ValueError('WebSocket message too large')
        for offset in range(0, max(1, len(value)), CHUNK):
            await self.stream.send(
                'data', value[offset : offset + CHUNK], kind=kind, final=offset + CHUNK >= len(value)
            )

    def __aiter__(self):
        return self

    async def __anext__(self):
        parts, size = [], 0
        while True:
            header, data = await self.stream.receive()
            if header['type'] == 'end':
                self.close_code = header.get('code', 1000)
                raise StopAsyncIteration
            if header['type'] != 'data':
                raise ConnectionError('Invalid WebSocket relay message')
            size += len(data)
            if size > MAX_MESSAGE:
                raise ValueError('WebSocket message too large')
            parts.append(data)
            await self.stream.consumed(len(data))
            if header.get('final'):
                value = b''.join(parts)
                binary = header.get('kind') != 'text'
                return SimpleNamespace(
                    type=aiohttp.WSMsgType.BINARY if binary else aiohttp.WSMsgType.TEXT,
                    data=value if binary else value.decode(),
                )

    async def close(self, **kwargs):
        await self.stream.close()


class RelayClient:
    def __init__(self, user_id, service, timeout=None):
        if not user_id:
            raise HTTPException(403, 'A user is required for Tether.')
        self.user_id = user_id
        self.service = get_services([service])[0]
        self.operations = []
        self.timeout = timeout if timeout is not None else aiohttp.ClientTimeout(total=300)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        await asyncio.gather(*(operation.close() for operation in self.operations), return_exceptions=True)

    def request(self, method, url, **kwargs):
        return Operation(self._request(method, url, **kwargs))

    def ws_connect(self, url, **kwargs):
        return Operation(self._request(None, url, **kwargs))

    def __getattr__(self, name):
        if name in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
            return lambda url, **kwargs: self.request(name.upper(), url, **kwargs)
        raise AttributeError(name)

    async def _request(self, method, url, **kwargs):
        parsed = urlsplit(str(url))
        if parsed.scheme != 'tether' or not parsed.hostname:
            raise ValueError('Invalid Tether URL')
        headers = dict(kwargs.get('headers') or {})
        headers['X-User-Id'] = self.user_id
        query = parsed.query
        if kwargs.get('params'):
            query += ('&' if query else '') + urlencode(kwargs['params'], doseq=True)
        stream = await hub.open(self.user_id, parsed.hostname, self.service)
        body = kwargs.get('data')
        if kwargs.get('json') is not None:
            body = json.dumps(kwargs['json']).encode()
            headers['Content-Type'] = 'application/json'
        if isinstance(body, aiohttp.FormData):
            body = body()
            headers['Content-Type'] = body.headers['Content-Type']
        upload = None
        try:
            if method:
                timeout = kwargs.get('timeout', self.timeout)
                if not isinstance(timeout, aiohttp.ClientTimeout):
                    timeout = aiohttp.ClientTimeout(total=timeout)
                stream.set_timeout(timeout)
            await stream.send(
                'http-open' if method else 'ws-open',
                service=self.service,
                method=method,
                path=parsed.path or '/',
                query=query,
                headers=headers,
            )
            if method:

                async def write(data):
                    for offset in range(0, len(data), CHUNK):
                        await stream.send('data', data[offset : offset + CHUNK])

                async def upload_body():
                    try:
                        if isinstance(body, str):
                            await write(body.encode())
                        elif isinstance(body, (bytes, bytearray)):
                            await write(body)
                        elif isinstance(body, aiohttp.payload.Payload):
                            await body.write(SimpleNamespace(write=write))
                        elif body is not None:
                            async for data in body:
                                await write(data)
                        await stream.send('end')
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        stream.fail('Upload interrupted; completion may be unknown')

                upload = asyncio.create_task(upload_body())
            # HTTP headers may wait for an upload or command to finish. Only the
            # WebSocket upgrade has a separate establishment deadline.
            header, _ = await stream.receive() if method else await asyncio.wait_for(stream.receive(), 30)
            if method and header['type'] == 'http-response':
                result = RelayResponse(stream, header, upload)
            elif not method and header['type'] == 'ws-ready':
                result = RelaySocket(stream)
            else:
                raise ConnectionError('Unexpected relay handshake')
            self.operations.append(result)
            return result
        except BaseException as error:
            if upload:
                upload.cancel()
                await asyncio.gather(upload, return_exceptions=True)
            await stream.close()
            if isinstance(error, (OSError, TimeoutError)) and not isinstance(error, RelayInterrupted):
                raise RelayInterrupted(str(error) or 'Response timed out') from error
            raise


def get_terminal_client(url, user_id=None, **kwargs):
    if str(url).startswith('tether://'):
        return RelayClient(user_id, service='open_terminal', timeout=kwargs.get('timeout'))
    return aiohttp.ClientSession(**kwargs)
