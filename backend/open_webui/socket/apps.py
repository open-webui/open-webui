"""Outbound app sockets. Each WebUI worker owns its own authenticated connections."""

import asyncio
import hashlib
import json
import logging
import random
import re
import time
import uuid
from urllib.parse import urlsplit

import aiohttp
import jwt
import socketio
from fastapi import HTTPException
from open_webui.env import REDIS_KEY_PREFIX
from open_webui.internal.db import get_async_db
from open_webui.models.apps import App, AppChannelMessage, Apps, AppTokenForm
from open_webui.models.config import Config
from open_webui.utils.apps import (
    AppTCPConnector,
    get_app_by_id,
    get_app_encryption_cipher,
    get_app_response,
    validate_app_url,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from socketio.packet import Packet
from sqlalchemy import select, update

log = logging.getLogger(__name__)
NAMESPACE = '/apps'
MAX_PACKET = 16 * 1024 * 1024


class JSON:
    @staticmethod
    def dumps(value, **kwargs):
        return json.dumps(value, **{**kwargs, 'ensure_ascii': False, 'separators': (',', ':')})

    loads = staticmethod(json.loads)


class JSONPacket(Packet):
    def decode(self, encoded_packet):
        if not isinstance(encoded_packet, str) or len(encoded_packet.encode()) > MAX_PACKET:
            raise ValueError('Socket packet exceeds 16 MiB or is not JSON')
        if encoded_packet[:1] in ('5', '6'):
            raise ValueError('Binary app packets are not supported')
        return super().decode(encoded_packet)


class AppHistoryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    channel_id: str
    parent_id: str | None = None
    before: str | None = None
    limit: int = Field(default=50, ge=1, le=100)


def connection_config(app):
    return (app.api_key, app.data.get('connection_token'), app.data['manifest']['public_key'], app.data['url'])


class AppConnection:
    def __init__(self, app):
        self.app = app
        self.session = None
        self.sio = None
        self.ready = False
        self.verified = False
        self.requests = set()
        self.connected = asyncio.Event()

    async def open(self, *, enroll=False):
        allow_private = validate_app_url(self.app.data['url'])
        trace = aiohttp.TraceConfig()

        async def reject_redirect(*args):
            raise ValueError('App endpoint must not redirect')

        trace.on_request_redirect.append(reject_redirect)
        self.session = aiohttp.ClientSession(
            connector=AppTCPConnector(allow_private=allow_private),
            trust_env=False,
            trace_configs=[trace],
            timeout=aiohttp.ClientTimeout(total=20),
        )
        self.sio = socketio.AsyncClient(
            http_session=self.session,
            reconnection=False,
            json=JSON,
            serializer=JSONPacket,
            websocket_extra_options={'max_msg_size': MAX_PACKET},
        )
        self.sio.on('app:request', self.request, namespace=NAMESPACE)

        async def disconnected(*args):
            self.ready = False
            self.connected.clear()

        self.sio.on('disconnect', disconnected, namespace=NAMESPACE)
        cipher = get_app_encryption_cipher()
        key = cipher.decrypt(self.app.api_key.encode()).decode()
        saved = self.app.data.get('connection_token')
        if not saved and not enroll:
            raise HTTPException(409, 'Reconnect this app to upgrade its transport')
        token = cipher.decrypt(saved.encode()).decode() if saved else None
        challenge = str(uuid.uuid4())
        url = urlsplit(self.app.data['url'])
        await self.sio.connect(
            f'{url.scheme}://{url.netloc}',
            socketio_path=url.path.rstrip('/') + '/socket.io',
            headers={'Authorization': 'Bearer ' + key},
            namespaces=[NAMESPACE],
            transports=['websocket'],
            wait_timeout=20,
        )
        result = await self.sio.call(
            'app:connect',
            {
                'app_id': self.app.id,
                'challenge': challenge,
                'connection_token': token,
            },
            namespace=NAMESPACE,
            timeout=10,
        )
        if not isinstance(result, dict) or result.get('status') != 200:
            raise HTTPException(403, 'App rejected its connection credential. Review credentials before reconnecting.')
        token, installation_id = self.verify_connection(result['data'], challenge, saved)
        self.verified = True
        if enroll:
            async with get_async_db() as db:
                values = {k: v for k, v in self.app.data.items() if k != 'webui_url'}
                values.update(installation_id=installation_id, connection_token=cipher.encrypt(token.encode()).decode())
                result = await db.execute(
                    update(App)
                    .where(
                        App.id == self.app.id,
                        App.updated_at == self.app.updated_at,
                    )
                    .values(data=values, is_active=False, updated_at=max(time.time_ns(), self.app.updated_at + 1))
                )
                if result.rowcount != 1:
                    raise HTTPException(409, 'App changed while connecting; connect again')
                await db.commit()
                self.app = await Apps.get_app_by_id(self.app.id, db=db)
        result = await self.sio.call('app:ready', {}, namespace=NAMESPACE, timeout=10)
        if result != {'status': 200, 'data': {'received': True}}:
            raise HTTPException(502, 'App could not complete its bidirectional connection check')
        if enroll:
            async with get_async_db() as db:
                result = await db.execute(
                    update(App)
                    .where(
                        App.id == self.app.id,
                        App.updated_at == self.app.updated_at,
                    )
                    .values(is_active=True, updated_at=max(time.time_ns(), self.app.updated_at + 1))
                )
                if result.rowcount != 1:
                    raise HTTPException(409, 'App changed while connecting; connect again')
                await db.commit()
                self.app = await Apps.get_app_by_id(self.app.id, db=db)
        self.ready = True
        self.connected.set()

    def verify_connection(self, data, challenge, saved):
        token = data['connection_token']
        if not isinstance(token, str) or len(token) > 8192:
            raise ValueError('Invalid app connection token')
        proof = data['proof']
        if jwt.get_unverified_header(proof).get('typ') != 'oix-connect+jwt':
            raise ValueError('Invalid app identity proof')
        claims = jwt.decode(
            proof,
            self.app.data['manifest']['public_key'],
            algorithms=['EdDSA'],
            audience='oix:connect',
            options={'require': ['sub', 'app_id', 'manifest_id', 'iat', 'exp', 'challenge', 'token_hash']},
        )
        installation_id = str(uuid.UUID(data['installation_id']))
        if (
            claims['sub'] != installation_id
            or claims['app_id'] != self.app.id
            or claims['manifest_id'] != self.app.data['manifest']['id']
            or claims['challenge'] != challenge
            or claims['token_hash'] != hashlib.sha256(token.encode()).hexdigest()
            or type(claims['iat']) is not int
            or type(claims['exp']) is not int
            or not 0 < claims['exp'] - claims['iat'] <= 60
        ):
            raise ValueError('Invalid app identity proof')
        if saved and installation_id != self.app.data.get('installation_id'):
            raise ValueError('App installation identity changed')
        return token, installation_id

    async def request(self, packet):
        task = asyncio.current_task()
        self.requests.add(task)
        try:
            if not isinstance(packet, dict) or len(JSON.dumps(packet).encode()) > MAX_PACKET - 128:
                raise HTTPException(413, 'App request exceeds 16 MiB')
            operation = packet.get('operation')
            arguments = packet.get('arguments', {})
            if not self.verified or (not self.ready and operation != 'ping'):
                raise HTTPException(503 if self.verified else 403, 'App connection is not ready')
            if operation == 'ping' and arguments == {}:
                return {'status': 200, 'data': {'received': True}}
            async with asyncio.timeout(10):
                async with get_async_db() as db:
                    app = await get_app_by_id(self.app.id, db=db, require_active=True)
                    if connection_config(app) != connection_config(self.app):
                        raise HTTPException(403, 'App credentials changed')
                    value = await execute_request(app, operation, arguments, db)
            result = {'status': 200, 'data': value}
            if len(JSON.dumps(result).encode()) > MAX_PACKET - 128:
                raise HTTPException(413, 'App response exceeds 16 MiB')
            return result
        except HTTPException as exc:
            return {'status': exc.status_code, 'error': exc.detail}
        except ValidationError:
            return {'status': 400, 'error': 'Invalid app operation arguments'}
        except TimeoutError:
            return {'status': 504, 'error': 'App operation timed out; outcome may be unknown'}
        except Exception:
            log.exception('App operation failed for %s', self.app.id)
            return {'status': 500, 'error': 'App operation failed'}
        finally:
            self.requests.discard(task)

    async def close(self):
        self.ready = False
        self.connected.clear()
        if self.sio:
            await self.sio.disconnect()
        if self.session:
            await self.session.close()


async def execute_request(app, operation, arguments, db):
    from open_webui.utils import apps as runtime
    from open_webui.utils.apps import create_app_message, update_app_message

    if not isinstance(arguments, dict):
        raise HTTPException(400, 'Invalid app operation arguments')
    if operation in ('get_me', 'list_channels') and not arguments:
        if operation == 'get_me':
            return get_app_response(app)
        return await runtime.get_app_channels(app=app, db=db)
    if operation in ('authorize', 'verify_event'):
        form = AppTokenForm.model_validate(arguments)
        handler = runtime.authorize_app_execution if operation == 'authorize' else runtime.verify_app_event
        return await handler(form_data=form, app=app, db=db)
    if operation == 'list_messages':
        form = AppHistoryRequest.model_validate(arguments)
        return await runtime.get_app_channel_messages(**form.model_dump(), app=app, db=db)
    if operation in ('create_message', 'update_message'):
        arguments = dict(arguments)
        identifier = arguments.pop('channel_id' if operation == 'create_message' else 'message_id', None)
        if not isinstance(identifier, str) or not 1 <= len(identifier) <= 100:
            raise HTTPException(400, 'Invalid resource ID')
        etag = arguments.pop('etag', None) if operation == 'update_message' else None
        form = AppChannelMessage.model_validate(arguments)
        if operation == 'create_message':
            return await create_app_message(db, app, identifier, form)
        if not isinstance(etag, str) or not re.fullmatch(r'[0-9]+', etag):
            raise HTTPException(400, 'If-Match is required')
        return await update_app_message(db, app, identifier, form, f'"{etag}"')
    raise HTTPException(400, 'Unknown app operation')


class AppConnections:
    def __init__(self):
        self.peers = {}
        self.tasks = {}
        self.locks = {}
        self.worker_id = str(uuid.uuid4())
        self.redis = None
        self.loop = None
        self.closing = False

    async def start(self, redis=None):
        self.redis = redis
        self.closing = False
        self.loop = asyncio.create_task(self.reconcile())

    async def maintain(self, app):
        delay = 1
        while not self.closing:
            peer = AppConnection(app)
            self.peers[app.id] = peer
            try:
                async with asyncio.timeout(20):
                    await peer.open()
                delay = 1
                await peer.sio.wait()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning('App %s socket unavailable: %s', app.id, type(exc).__name__)
            finally:
                await peer.close()
            await asyncio.sleep(random.uniform(delay / 2, delay))
            delay = min(delay * 2, 30)

    async def reconcile(self):
        while not self.closing:
            try:
                async with get_async_db() as db:
                    apps = (
                        list((await db.scalars(select(App).where(App.is_active.is_(True)))).all())
                        if await Config.get('apps.enable')
                        else []
                    )
                    snapshots = [await Apps.get_app_by_id(app.id, db=db) for app in apps]
                active = {app.id: app for app in snapshots if app.data.get('connection_token')}
                for app_id in set(self.tasks) | set(active):
                    await self.refresh(app_id)
                if self.redis:
                    for app_id, peer in list(self.peers.items()):
                        key = f'{REDIS_KEY_PREFIX}:apps:connections:{app_id}'
                        if peer.ready:
                            await self.redis.zadd(key, {self.worker_id: time.time() + 15})
                            await self.redis.expire(key, 30)
                        else:
                            await self.redis.zrem(key, self.worker_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.warning('App connection reconciliation failed')
            await asyncio.sleep(5)

    async def refresh(self, app_id):
        async with self.locks.setdefault(app_id, asyncio.Lock()):
            # Refresh after taking the lock: an admin may have just connected this app.
            app = await Apps.get_app_by_id(app_id)
            enabled = await Config.get('apps.enable')
            peer = self.peers.get(app_id)
            if not enabled or not app or not app.is_active or not app.data.get('connection_token'):
                await self.remove(app_id)
            else:
                if peer and connection_config(app) != connection_config(peer.app):
                    await self.remove(app_id)
                if app_id not in self.tasks:
                    self.tasks[app_id] = asyncio.create_task(self.maintain(app))

    async def remove(self, app_id):
        task = self.tasks.pop(app_id, None)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        peer = self.peers.pop(app_id, None)
        if peer:
            await peer.close()
        if self.redis:
            try:
                await self.redis.zrem(f'{REDIS_KEY_PREFIX}:apps:connections:{app_id}', self.worker_id)
            except Exception:
                pass  # Liveness expires after a crashed worker or Redis outage.

    async def connect(self, app):
        async with self.locks.setdefault(app.id, asyncio.Lock()):
            await self.remove(app.id)
            peer = AppConnection(app)
            try:
                async with asyncio.timeout(20):
                    await peer.open(enroll=True)
            except HTTPException:
                await peer.close()
                raise
            except Exception as exc:
                await peer.close()
                log.warning('App %s connection failed: %s', app.id, type(exc).__name__)
                raise HTTPException(
                    502, 'App connection failed. Check the API key, pinned public key and Socket.IO endpoint.'
                ) from None
            self.peers[app.id] = peer

            async def resume():
                try:
                    await peer.sio.wait()
                finally:
                    await peer.close()
                await self.maintain(peer.app)

            self.tasks[app.id] = asyncio.create_task(resume())
            return peer.app

    async def send(self, app, payload, timeout):
        if self.closing:
            raise HTTPException(503, 'App connections are shutting down')
        async with self.locks.setdefault(app.id, asyncio.Lock()):
            peer = self.peers.get(app.id)
            if peer is None or connection_config(peer.app) != connection_config(app):
                await self.remove(app.id)
                if not app.data.get('connection_token'):
                    raise HTTPException(409, 'Reconnect this app to upgrade its transport')
                self.tasks[app.id] = asyncio.create_task(self.maintain(app))
                await asyncio.sleep(0)
                peer = self.peers[app.id]
        if not peer.ready:
            raise HTTPException(503, 'App is disconnected; event was not sent')
        try:
            result = await peer.sio.call('app:event', payload, namespace=NAMESPACE, timeout=timeout)
        except Exception:
            raise HTTPException(504, 'App connection lost or timed out; execution outcome may be unknown') from None
        if not isinstance(result, dict) or len(JSON.dumps(result).encode()) > 262144 + 128:
            raise HTTPException(502, 'App returned an invalid or oversized response')
        status = result.get('status')
        if type(status) is not int:
            raise HTTPException(502, 'App returned an invalid status')
        return status, result.get('data') if status == 200 else result.get('error')

    async def status(self, app):
        if not app.is_active:
            return 'disconnected'
        if self.redis:
            try:
                if await self.redis.zcount(f'{REDIS_KEY_PREFIX}:apps:connections:{app.id}', time.time(), '+inf'):
                    return 'connected'
            except Exception:
                return 'disconnected'
        peer = self.peers.get(app.id)
        return 'connected' if peer and peer.ready else 'connecting' if peer else 'disconnected'

    async def close(self):
        self.closing = True
        if self.loop:
            self.loop.cancel()
            await asyncio.gather(self.loop, return_exceptions=True)
        for peer in self.peers.values():
            peer.ready = False
        pending = set().union(*(peer.requests for peer in self.peers.values())) if self.peers else set()
        if pending:
            _, unfinished = await asyncio.wait(pending, timeout=30)
            for task in unfinished:
                task.cancel()
            await asyncio.gather(*unfinished, return_exceptions=True)
        for app_id in list(self.peers):
            await self.remove(app_id)


connections = AppConnections()
