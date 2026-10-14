"""App credentials, authenticated events, and access checks."""

import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import time
import uuid
from copy import deepcopy
from typing import Any
from urllib.parse import urlsplit

import aiohttp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException, status
from open_webui.env import WEBUI_SECRET_KEY
from open_webui.internal.db import get_async_db
from open_webui.models.access_grants import AccessGrants
from open_webui.models.apps import AppChannelMessage, AppChannelReply, AppModel, Apps, AppTokenForm
from open_webui.models.channels import Channel, ChannelMember, ChannelModel, Channels
from open_webui.models.config import Config
from open_webui.models.messages import Message, MessageForm, Messages
from open_webui.models.users import UserModel, Users
from open_webui.tasks import create_task
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


def get_app_url_origin(url: str) -> str:
    if any(c in url for c in ('\\', '\r', '\n', '\t')):
        raise ValueError('Invalid service URL')
    try:
        parsed_url = urlsplit(url)
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    except ValueError:
        raise ValueError('Invalid service URL') from None
    if not parsed_url.hostname or parsed_url.username or parsed_url.password or parsed_url.fragment:
        raise ValueError('Invalid service URL')
    host = f'[{parsed_url.hostname}]' if ':' in parsed_url.hostname else parsed_url.hostname.lower()
    return f'{parsed_url.scheme}://{host}:{port}'


def validate_app_url(url: str) -> bool:
    """Validate the endpoint and return whether its private origin is explicitly allowed."""
    origin = get_app_url_origin(url)
    if urlsplit(url).query:
        raise ValueError('App URL must not contain a query')
    private_origins = {
        get_app_url_origin(x.strip()) for x in os.getenv('APP_ALLOWED_PRIVATE_ORIGINS', '').split(',') if x.strip()
    }
    is_private_origin_allowed = origin in private_origins
    scheme = urlsplit(url).scheme
    if scheme != 'https' and not (is_private_origin_allowed and scheme == 'http'):
        raise ValueError('App endpoints require HTTPS')
    return is_private_origin_allowed


def _is_public_ip_address(ip_address: str) -> bool:
    address = ipaddress.ip_address(ip_address)
    if not address.is_global or address.is_multicast:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        embedded = [address.ipv4_mapped, address.sixtofour]
        if address.teredo:
            embedded.extend(address.teredo)
        # NAT64 carries an IPv4 destination; reject translation prefixes instead of trusting it.
        if address in ipaddress.ip_network('64:ff9b::/96') or address in ipaddress.ip_network('64:ff9b:1::/48'):
            return False
        return all(x is None or (x.is_global and not x.is_multicast) for x in embedded)
    return True


class AppTCPConnector(aiohttp.TCPConnector):
    def __init__(self, *, allow_private: bool = False):
        super().__init__(use_dns_cache=False)
        self.allow_private = allow_private

    async def _resolve_host(self, host, port, traces=None):
        addresses = await super()._resolve_host(host, port, traces)
        if not self.allow_private and any(not _is_public_ip_address(x['host']) for x in addresses):
            raise ValueError('App endpoint resolves to a prohibited address')
        return addresses


async def send_app_request(
    url: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10,
    max_response_size: int = 262144,
) -> tuple[int, Any]:
    try:
        allow_private = validate_app_url(url)
        async with aiohttp.ClientSession(
            connector=AppTCPConnector(allow_private=allow_private),
            timeout=aiohttp.ClientTimeout(total=timeout),
            trust_env=False,
        ) as session:
            async with session.request(
                'POST' if body is not None else 'GET',
                url,
                data=body,
                headers=headers,
                allow_redirects=False,
            ) as response:
                response_body = bytearray()
                async for chunk in response.content.iter_chunked(16384):
                    response_body.extend(chunk)
                    if len(response_body) > max_response_size:
                        raise ValueError('App response is too large')
                if response.status != 200:
                    return response.status, None
                return response.status, json.loads(response_body) if response_body else None
    except TimeoutError:
        raise HTTPException(504, 'App request timed out. Check that the app server is running and reachable.') from None
    except aiohttp.ClientSSLError:
        raise HTTPException(502, 'App TLS verification failed. Check its certificate and hostname.') from None
    except aiohttp.ClientConnectorDNSError:
        raise HTTPException(502, 'App hostname could not be resolved. Check DNS from the WebUI server.') from None
    except aiohttp.ClientConnectorError:
        raise HTTPException(
            502, 'Could not reach the app server. Check its address, port and network access.'
        ) from None
    except aiohttp.ClientError:
        raise HTTPException(502, 'The app connection failed before a complete response was received.') from None
    except ValueError as exc:
        # Only local, fixed diagnostics may be shown; never echo arbitrary app responses.
        details = {
            'Invalid service URL': 'Invalid app URL. Use an HTTP(S) URL without credentials or a fragment.',
            'App endpoints require HTTPS': (
                'App endpoints require HTTPS. For local HTTP, configure APP_ALLOWED_PRIVATE_ORIGINS.'
            ),
            'App endpoint resolves to a prohibited address': (
                'App resolves to a private or reserved address. '
                'For local development, configure APP_ALLOWED_PRIVATE_ORIGINS.'
            ),
            'App response is too large': 'App response exceeds the allowed size.',
        }
        raise HTTPException(502, details.get(str(exc), 'App returned an invalid response. Expected JSON.')) from None


def get_app_encryption_cipher() -> Fernet:
    if not WEBUI_SECRET_KEY:
        raise RuntimeError('A stable WEBUI_SECRET_KEY is required for apps')
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'open-webui-app-keys-v1').derive(
        WEBUI_SECRET_KEY.encode()
    )
    return Fernet(base64.urlsafe_b64encode(key))


def _sign_app_context(app: AppModel, payload: str) -> bytes:
    # Key or service-credential replacement invalidates execution contexts.
    return hmac.digest(
        WEBUI_SECRET_KEY.encode(),
        b'open-webui-context-v1\n'
        + app.id.encode()
        + b'\n'
        + hashlib.sha256((app.data['manifest']['public_key'] + (app.api_key or '')).encode()).digest()
        + b'\n'
        + payload.encode(),
        'sha256',
    )


def _serialize_json(value: Any) -> bytes:
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode()


def create_app_context_token(app: AppModel, purpose: str, data: dict, expires_in: int = 900) -> str:
    payload = base64.urlsafe_b64encode(
        _serialize_json(
            {
                **data,
                'app_id': app.id,
                'purpose': purpose,
                'exp': int(time.time()) + expires_in,
                'nonce': str(uuid.uuid4()),
            }
        )
    ).decode()
    signature = _sign_app_context(app, payload)
    return payload + '.' + base64.urlsafe_b64encode(signature).decode()


def decode_app_context_token(app: AppModel, purpose: str, token: str) -> dict:
    try:
        payload, signature = token.split('.')
        decoded_signature = base64.b64decode(signature, altchars=b'-_', validate=True)
        decoded_payload = base64.b64decode(payload, altchars=b'-_', validate=True)
        if (
            base64.urlsafe_b64encode(decoded_signature).decode() != signature
            or base64.urlsafe_b64encode(decoded_payload).decode() != payload
        ):
            raise ValueError('Non-canonical context')
        if not hmac.compare_digest(decoded_signature, _sign_app_context(app, payload)):
            raise ValueError('Invalid context signature')
        data = json.loads(decoded_payload)
        if data['app_id'] != app.id or data['purpose'] != purpose or data['exp'] <= time.time():
            raise ValueError('Expired context')
        return data
    except Exception:
        raise HTTPException(403, 'Invalid or expired app context') from None


async def send_app_event(app: AppModel, event_data: dict, *, timeout: float = 3) -> tuple[int, Any]:
    from open_webui.socket.apps import connections

    payload = {**event_data, 'app_id': app.id, 'installation_id': app.data.get('installation_id')}
    if len(_serialize_json(payload)) > 1048576 - 128:
        log.warning('App %s event exceeds the 1 MiB delivery limit', app.id)
        raise ValueError('App event exceeds 1 MiB')
    return await connections.send(app, payload, timeout)


def get_app_response(app: AppModel) -> dict:
    return {
        'id': app.id,
        'slug': app.slug,
        'name': app.name,
        'is_active': app.is_active,
        'configured': bool(app.api_key),
        'data': {k: v for k, v in app.data.items() if k not in ('connection_token', 'webui_url')},
        'created_at': app.created_at,
        'updated_at': app.updated_at,
    }


async def get_app_by_id(app_id: str, db: AsyncSession, require_active: bool = False) -> AppModel:
    if not await Config.get('apps.enable'):
        raise HTTPException(404, 'Apps are disabled')
    app = await Apps.get_app_by_id(app_id, db=db)
    if not app:
        raise HTTPException(404, 'App not found')
    if require_active and (not app.is_active or not app.data['manifest'].get('public_key') or not app.api_key):
        raise HTTPException(403, 'App is inactive')
    return app


async def has_app_access(app: AppModel, user: UserModel, db: AsyncSession) -> bool:
    return user.role == 'admin' or await AccessGrants.has_access(user.id, 'app', app.id, 'read', db=db)


async def check_app_channel_access(
    channel_id: str,
    db: AsyncSession,
    user: UserModel | None = None,
    require_manager: bool = False,
    require_write: bool = False,
) -> ChannelModel:
    if not await Config.get('apps.enable'):
        raise HTTPException(404, 'Apps are disabled')
    if not await Config.get('channels.enable'):
        raise HTTPException(403, 'Channels are disabled')
    channel = await Channels.get_channel_by_id(channel_id, db=db)
    if not channel or channel.type == 'dm' or channel.deleted_at or channel.archived_at:
        raise HTTPException(404, 'Channel unavailable')
    if user:
        if user.role not in ('user', 'admin'):
            raise HTTPException(403, 'User is inactive')
        if user.role == 'admin':
            return channel
        if require_manager:
            allowed = await Channels.is_user_channel_manager(channel_id, user.id, db=db)
        elif channel.type == 'group':
            allowed = await Channels.is_user_channel_member(channel_id, user.id, db=db)
        else:
            allowed = await AccessGrants.has_access(
                user.id, 'channel', channel_id, 'write' if require_write else 'read', db=db
            )
        if not allowed:
            raise HTTPException(403, 'Channel access denied')
    return channel


async def check_app_channel_membership(app: AppModel, channel_id: str, db: AsyncSession) -> ChannelModel:
    await get_app_by_id(app.id, db=db, require_active=True)
    channel = await check_app_channel_access(channel_id, db=db)
    if not await Channels.is_app_channel_member(channel_id, app.id, db=db):
        raise HTTPException(403, 'Invite the app into this channel first')
    return channel


async def check_app_invocation_access(
    app: AppModel, channel_id: str, user: UserModel, db: AsyncSession
) -> ChannelModel:
    if not await has_app_access(app, user, db=db):
        raise HTTPException(403, 'App invocation denied')
    await check_app_channel_access(channel_id, user=user, db=db)
    return await check_app_channel_membership(app, channel_id, db=db)


def require_scope(app, scope):
    if scope and scope not in app.data.get('granted_scopes', []):
        raise HTTPException(403, 'App scope was not granted')


def get_app_message_data(message):
    # Send channel content, not arbitrary internal message metadata.
    meta = message.meta or {}
    if message.app_id:
        author = {'type': 'app', 'id': message.app_id}
    elif meta.get('webhook', {}).get('id'):
        author = {'type': 'webhook', 'id': meta['webhook']['id']}
    elif meta.get('model_id'):
        author = {'type': 'model', 'id': meta['model_id']}
    else:
        author = {'type': 'user', 'id': message.user_id}
    return {
        'id': message.id,
        'channel_id': message.channel_id,
        'author': author,
        'content': message.content,
        'parent_id': message.parent_id,
        'reply_to_id': message.reply_to_id,
        'files': (message.data or {}).get('files', []),
        'actions': (message.data or {}).get('app', {}).get('actions', []),
        'embeds': (message.data or {}).get('app', {}).get('embeds', []),
        'created_at': str(message.created_at),
        'updated_at': str(message.updated_at),
        'etag': str(message.updated_at),
    }


async def publish_app_message_event(message, kind):
    # Model output is streamed into this row; only publish its completed update.
    if (
        kind == 'channel.message.updated'
        and (message.meta or {}).get('model_id')
        and not (message.meta or {}).get('done')
    ):
        return
    value = deepcopy(get_app_message_data(message))
    if kind == 'channel.message.deleted':
        value = {k: value[k] for k in ('id', 'channel_id', 'parent_id', 'author', 'updated_at')}
    # shortcut: events are lost on failure/restart; add durable delivery only if replay becomes required.
    await create_task(None, send_app_message_event(value, kind, time.time_ns()))


async def send_app_message_event(message, kind, created_at):
    try:
        if not await Config.get('apps.enable') or not await Config.get('channels.enable'):
            return
        async with get_async_db() as db:
            app_ids = await Apps.get_app_ids_by_channel_id(message['channel_id'], created_at, db=db)
        for app_id in app_ids:
            try:
                async with get_async_db() as db:
                    app = await Apps.get_app_by_id(app_id, db=db)
                    if not app or 'channels:messages:read' not in app.data.get('granted_scopes', []):
                        continue
                    if not app.data.get('installation_id'):
                        continue
                    try:
                        await check_app_channel_membership(app, message['channel_id'], db=db)
                    except HTTPException:
                        continue  # App or channel access was revoked before sending.
                    envelope = {
                        'id': str(uuid.uuid4()),
                        'type': kind,
                        'message': message,
                        'app_id': app.id,
                        'installation_id': app.data['installation_id'],
                        'channel': {'id': message['channel_id']},
                    }
                    envelope['event_token'] = create_app_context_token(app, 'event', envelope, expires_in=300)
                status, _ = await send_app_event(app, envelope, timeout=10)
                if not 200 <= status < 300:
                    log.warning('App %s did not acknowledge %s: HTTP %s', app_id, kind, status)
            except Exception:
                log.exception('Failed to send %s to app %s', kind, app_id)
    except Exception:
        log.exception('Failed to publish %s for message %s', kind, message['id'])


async def emit_app_message(message, channel, kind='message'):
    from open_webui.socket.main import sio

    try:
        await sio.emit(
            'events:channel',
            {
                'channel_id': channel.id,
                'message_id': message['id'],
                'data': {'type': kind, 'data': message},
                'channel': channel.model_dump(),
            },
            to=f'channel:{channel.id}',
        )
    except Exception:
        # The insert is committed; socket delivery must never turn this into a failed POST.
        log.warning('App message committed but channel notification failed')


async def create_app_message(db, app, channel_id, form):
    channel = await check_app_channel_membership(app, channel_id, db=db)
    require_scope(app, 'channels:messages:write')
    for target in (form.parent_id, form.reply_to_id):
        if target:
            reference = await Messages.get_message_by_id(target, include_thread_replies=False, db=db)
            if not reference or reference.channel_id != channel_id:
                raise HTTPException(400, 'Invalid message reference')
    message = await Messages.insert_new_app_message(
        app.id,
        channel_id,
        MessageForm(
            content=form.content,
            data={
                'app': {
                    'actions': [x.model_dump() for x in form.actions],
                    'embeds': [x.model_dump() for x in form.embeds],
                }
            },
            parent_id=form.parent_id,
            reply_to_id=form.reply_to_id,
        ),
        db=db,
    )
    result = message.model_dump()
    await emit_app_message(result, channel)
    return result


async def update_app_message(db, app, message_id, form, if_match):
    if if_match is None:
        raise HTTPException(428, 'If-Match is required')
    message = await Messages.get_message_by_id(message_id, include_thread_replies=False, db=db)
    if not message or message.app_id != app.id:
        raise HTTPException(404, 'App message not found')
    channel = await check_app_channel_membership(app, message.channel_id, db=db)
    require_scope(app, 'channels:messages:write')
    if if_match != f'"{message.updated_at}"':
        raise HTTPException(412, 'Message changed')
    updated = await Messages.update_app_message_by_id(
        message_id,
        app.id,
        message.updated_at,
        MessageForm(
            content=form.content,
            data={
                'app': {
                    'actions': [x.model_dump() for x in form.actions],
                    'embeds': [x.model_dump() for x in form.embeds],
                }
            },
        ),
        db=db,
    )
    if not updated:
        raise HTTPException(412, 'Message changed')
    value = updated.model_dump()
    await emit_app_message(value, channel, 'message:update')
    return value


async def send_app_invocation(
    app, user, channel_id, event_type, data, *, db: AsyncSession, source=None, operation_id=None, scope=None, timeout=3
):
    await check_app_invocation_access(app, channel_id, user, db=db)
    require_scope(app, scope)
    operation_id = operation_id or str(uuid.uuid4())
    token = create_app_context_token(
        app,
        'execution',
        {
            'actor_id': user.id,
            'channel_id': channel_id,
            'operation_id': operation_id,
            'scope': scope,
            'type': event_type,
            'data': data,
        },
        expires_in=86400,
    )
    envelope = {
        'id': operation_id,
        'type': event_type,
        'actor': {'id': user.id, 'name': user.name, 'is_admin': user.role == 'admin'},
        'channel': {'id': channel_id},
        'data': data,
        'execution_token': token,
        'source': source,
    }
    # Release the read transaction before socket delivery.
    await db.commit()
    try:
        status, raw = await send_app_event(app, envelope, timeout=timeout)
    except HTTPException as exc:
        if exc.status_code == 504:
            raise HTTPException(504, 'App response timed out; execution outcome may be unknown') from None
        raise
    except ValueError:
        raise HTTPException(502, 'App event could not be delivered. Check the WebUI server logs.') from None
    if status != 200:
        detail = {
            401: 'App rejected the API key. Update the key in app settings.',
            403: 'App rejected event authorization. Check the app server logs for the verification failure.',
            404: 'App event endpoint was not found. Check its URL in app settings.',
            405: 'App endpoint does not accept POST requests. Check its event URL.',
            413: 'App rejected the event because it is too large.',
            503: 'App is busy or shutting down. The event was not accepted.',
            504: 'App processing timed out; execution outcome may be unknown.',
        }.get(status, f'App returned HTTP {status}. Check the app server logs.')
        if isinstance(raw, str) and raw.strip():
            try:
                cipher = get_app_encryption_cipher()
                secrets = [token]
                for stored in filter(None, (app.api_key, app.data.get('connection_token'))):
                    secrets.extend((stored, cipher.decrypt(stored.encode()).decode()))
                sanitized = raw.strip()
                for secret in sorted(filter(None, secrets), key=len, reverse=True):
                    sanitized = sanitized.replace(secret, '[redacted]')
            except Exception:
                # Keep the generic error if credentials cannot be safely scrubbed.
                log.warning('Could not redact app error credentials')
            else:
                detail = sanitized[:2000]
        raise HTTPException(status if 400 <= status < 600 else 502, detail)
    return raw


async def send_app_mention(app, user, channel_id, data, *, operation_id, scope, db):
    receipt = await send_app_invocation(
        app,
        user,
        channel_id,
        'channel.mention',
        data,
        operation_id=operation_id,
        scope=scope,
        db=db,
        timeout=10,
    )
    if receipt != {'received': True}:
        raise HTTPException(502, 'App returned an invalid delivery receipt')


async def generate_app_channel_reply(
    app, user, channel_id, event_type, data, *, db: AsyncSession, source=None, operation_id=None, scope=None
):
    checked_key = (app.api_key, app.data['manifest']['public_key'])
    raw = await send_app_invocation(
        app,
        user,
        channel_id,
        event_type,
        data,
        db=db,
        source=source,
        operation_id=operation_id,
        scope=scope,
    )
    app = await get_app_by_id(app.id, require_active=True, db=db)
    if (app.api_key, app.data['manifest']['public_key']) != checked_key:
        raise HTTPException(403, 'App credentials changed')
    user = await Users.get_user_by_id(user.id, db=db)
    if not user:
        raise HTTPException(403, 'Actor is unavailable')
    try:
        reply = AppChannelReply.model_validate(raw)
    except Exception:
        raise HTTPException(502, 'App returned an invalid response') from None
    await check_app_invocation_access(app, channel_id, user, db=db)
    if reply.type == 'ack':
        return {'type': 'ack'}
    if reply.actions and (reply.visibility != 'channel' or reply.type not in ('message', 'update')):
        raise HTTPException(502, 'Buttons require a channel message')
    value = reply.model_dump()
    if reply.type == 'message' and reply.visibility == 'channel':
        value['message'] = await create_app_message(db, app, channel_id, reply)
    elif reply.type == 'update':
        if not source:
            raise HTTPException(400, 'Message update requires a source message')
        message = AppChannelMessage(**{k: getattr(reply, k) for k in AppChannelMessage.model_fields})
        value['message'] = await update_app_message(db, app, source['id'], message, f'"{source["updated_at"]}"')
    return value


async def get_app_channels(app: AppModel, db: AsyncSession):
    if not await Config.get('channels.enable'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Channels are disabled')
    await get_app_by_id(app.id, require_active=True, db=db)
    require_scope(app, 'channels:read')
    channels = (
        await db.scalars(
            select(Channel)
            .join(ChannelMember, Channel.id == ChannelMember.channel_id)
            .where(
                ChannelMember.app_id == app.id,
                ChannelMember.is_active.is_(True),
                Channel.deleted_at.is_(None),
                Channel.archived_at.is_(None),
            )
        )
    ).all()
    result = []
    for channel in channels:
        channel_data = await Channels.get_channel_by_id(channel.id, db=db)
        is_private = (
            channel_data.is_private is True
            if channel_data.type == 'group'
            else not any(grant.principal_id == '*' for grant in channel_data.access_grants)
        )
        result.append({'id': channel.id, 'name': channel.name, 'type': channel.type, 'is_private': is_private})
    return result


async def authorize_app_execution(form_data: AppTokenForm, app: AppModel, db: AsyncSession):
    value = decode_app_context_token(app, 'execution', form_data.token)
    user = await Users.get_user_by_id(value['actor_id'], db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Actor is unavailable')
    await check_app_invocation_access(app, value['channel_id'], user, db=db)
    require_scope(app, value['scope'])
    return {
        'authorized': True,
        'operation_id': value['operation_id'],
        'actor': {'id': user.id, 'name': user.name, 'is_admin': user.role == 'admin'},
        'channel_id': value['channel_id'],
        'type': value.get('type'),
        'data': value.get('data'),
    }


async def verify_app_event(form_data: AppTokenForm, app: AppModel, db: AsyncSession):
    value = decode_app_context_token(app, 'event', form_data.token)
    await check_app_channel_membership(app, value['channel']['id'], db=db)
    require_scope(app, 'channels:messages:read')
    return {k: v for k, v in value.items() if k not in ('purpose', 'exp', 'nonce')}


async def get_app_channel_messages(
    app: AppModel,
    db: AsyncSession,
    channel_id: str,
    before: str | None = None,
    parent_id: str | None = None,
    limit: int = 50,
):
    await check_app_channel_membership(app, channel_id, db=db)
    require_scope(app, 'channels:messages:read')
    query = select(Message).where(Message.channel_id == channel_id, Message.parent_id == parent_id)
    if parent_id:
        parent = await db.get(Message, parent_id)
        if not parent or parent.channel_id != channel_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Thread not found')
    if before:
        cursor = await db.get(Message, before)
        if not cursor or cursor.channel_id != channel_id or cursor.parent_id != parent_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid message cursor')
        query = query.where(
            or_(
                Message.created_at < cursor.created_at,
                and_(Message.created_at == cursor.created_at, Message.id < cursor.id),
            )
        )
    rows = (await db.scalars(query.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit + 1))).all()
    return {
        'messages': [get_app_message_data(row) for row in rows[:limit]],
        'next_cursor': rows[limit - 1].id if len(rows) > limit else None,
    }
