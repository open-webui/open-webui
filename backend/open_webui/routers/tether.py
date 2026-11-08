"""Authenticated outbound connections from Tether."""

import asyncio
import json
from contextlib import suppress
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket
from open_webui.models.auth_sessions import AuthSessions
from open_webui.utils.auth import decode_token, get_verified_user_by_token
from open_webui.utils.tether import CHUNK, WINDOW, hub, encode, decode, get_services

router = APIRouter()


@router.websocket('/connect')
async def connect(ws: WebSocket):
    await ws.accept()
    connection = None
    watcher = None
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), 10))
        if hello.get('type') != 'hello' or hello.get('version') not in (1, 2):
            raise ValueError('Unsupported Tether handshake')
        window = hello.get('window', 256 * 1024)
        if type(window) is not int or window < CHUNK:
            raise ValueError('Invalid relay window')
        window = min(window, WINDOW)
        token = hello.get('token', '')
        user = await get_verified_user_by_token(token, getattr(ws.app.state, 'redis', None))
        claims = decode_token(token)
        if not user or not claims or not claims.get('sid') or claims.get('typ') != 'session':
            raise ValueError('A renewable human session is required')
        row = await AuthSessions.get(claims['sid'])
        if not row or row.user_id != user.id or row.refresh_token_id is None:
            raise ValueError('Invalid session')
        connection_id = str(UUID(hello['connection_id']))
        name = hello.get('name')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ValueError('A connection name of 1–100 characters is required')
        await hub.start()
        presence = {
            'connection': str(uuid4()),
            'worker': hub.worker,
            'session': row.id,
            'user': user.id,
            'connection_id': connection_id,
            'name': name.strip(),
            'notifications': hello.get('notifications') is True,
            'window': window,
            'services': get_services(hello.get('services', ['open_terminal'] if hello['version'] == 1 else None)),
        }
        connection = SimpleNamespace(ws=ws, presence=presence, routes={}, lock=asyncio.Lock(), pending=0)

        async def send(header, data):
            if connection.pending >= 64:
                raise ConnectionError('Relay send queue full')
            connection.pending += 1
            try:
                # Lock waiters are FIFO; each stream yields after one chunk.
                async with connection.lock:
                    await asyncio.wait_for(ws.send_bytes(encode(header, data)), 10)
            finally:
                connection.pending -= 1

        connection.send = send
        key = hub.key(user.id, connection_id)
        record = json.dumps(presence)
        # A reconnect replaces the previous connection, including on another worker.
        for old in list(hub.connections.values()):
            if old.presence['user'] == user.id and old.presence['connection_id'] == connection_id:
                await old.ws.close(code=1000)
        await ws.send_json({'type': 'ready', 'notifications': True, 'window': window})
        hub.connections[presence['connection']] = connection
        presence_lock = asyncio.Lock()
        if hub.redis:
            await hub.redis.set(key, record, ex=60)

        async def watch():
            while True:
                await asyncio.sleep(15)
                current = await get_verified_user_by_token(token, getattr(ws.app.state, 'redis', None))
                if not current or current.id != user.id:
                    await ws.close(code=4001)
                    return
                async with presence_lock:
                    if hub.redis:
                        refreshed = await hub.redis.eval(
                            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], 60) else return 0 end",
                            1,
                            key,
                            record,
                        )
                        if not refreshed:
                            await ws.close(code=1000)
                            return

        async def guarded_watch():
            try:
                await watch()
            except Exception:
                with suppress(Exception):
                    await ws.close(code=4001)

        watcher = asyncio.create_task(guarded_watch())
        while True:
            message = await ws.receive()
            if message['type'] == 'websocket.disconnect':
                break
            if message.get('bytes') is not None:
                header, data = decode(message['bytes'])
                await hub.returned(connection, header, data)
            elif message.get('text') is not None:
                update = json.loads(message['text'])
                if update.get('type') == 'services':
                    services = get_services(update.get('services'))
                    name = update.get('name', presence['name'])
                    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
                        raise ValueError('A device name of 1–100 characters is required')
                    async with presence_lock:
                        updated_record = json.dumps({**presence, 'services': services, 'name': name.strip()})
                        if hub.redis:
                            replaced = await hub.redis.eval(
                                "if redis.call('get', KEYS[1]) == ARGV[1] then redis.call('set', KEYS[1], ARGV[2], 'EX', 60); return 1 else return 0 end",
                                1,
                                key,
                                record,
                                updated_record,
                            )
                            if not replaced:
                                raise ValueError('Tether connection was replaced')
                        presence['services'] = services
                        presence['name'] = name.strip()
                        record = updated_record
                    continue
                updated = decode_token(update.get('token', ''))
                current = await get_verified_user_by_token(
                    update.get('token', ''), getattr(ws.app.state, 'redis', None)
                )
                if (
                    update.get('type') != 'auth'
                    or not current
                    or current.id != user.id
                    or not updated
                    or updated.get('sid') != row.id
                    or updated.get('typ') != 'session'
                ):
                    raise ValueError('Cannot change relay identity')
                token = update['token']
    except Exception:
        with suppress(Exception):
            await ws.close(code=4001)
    finally:
        if watcher:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
        if connection:
            hub.connections.pop(connection.presence['connection'], None)
            if hub.redis:
                with suppress(Exception):
                    await hub.redis.eval(
                        "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
                        1,
                        key,
                        record,
                    )
            for stream_id in list(connection.routes):
                stream = hub.streams.get(stream_id)
                if stream:
                    stream.fail('Tether disconnected; operation completion may be unknown')
                else:
                    worker = connection.routes[stream_id]
                    if hub.redis:
                        # An explicit failure is terminal even if a preceding frame was lost.
                        with suppress(Exception):
                            await hub.redis.publish(
                                hub.channel(worker),
                                encode(
                                    {
                                        'type': 'error',
                                        'stream': stream_id,
                                        'sequence': 0,
                                        'route': 'stream',
                                        'connection': connection.presence['connection'],
                                        'message': 'Tether disconnected',
                                    },
                                    b'',
                                ),
                            )
