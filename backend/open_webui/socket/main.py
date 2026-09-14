from __future__ import annotations

import asyncio
import logging
import random
import sys
import time
from typing import Any

import pycrdt as Y
import socketio
from open_webui.config import (
    CORS_ALLOW_ORIGIN,
)
from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
    GLOBAL_LOG_LEVEL,
    REDIS_KEY_PREFIX,
    WEBSOCKET_EVENT_CALLER_TIMEOUT,
    WEBSOCKET_HEARTBEAT_INTERVAL,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_CLUSTER,
    WEBSOCKET_REDIS_LOCK_TIMEOUT,
    WEBSOCKET_REDIS_OPTIONS,
    WEBSOCKET_REDIS_URL,
    WEBSOCKET_SENTINEL_HOSTS,
    WEBSOCKET_SENTINEL_PORT,
    WEBSOCKET_SERVER_ENGINEIO_LOGGING,
    WEBSOCKET_SERVER_LOGGING,
    WEBSOCKET_SERVER_PING_INTERVAL,
    WEBSOCKET_SERVER_PING_TIMEOUT,
)
from open_webui.models.access_grants import AccessGrants
from open_webui.models.channels import Channels
from open_webui.models.chats import Chats
from open_webui.models.folders import Folders
from open_webui.models.notes import Notes, NoteUpdateForm
from open_webui.models.users import UserNameResponse, Users
from open_webui.socket.utils import RedisDict, RedisLock, YdocManager
from open_webui.tasks import create_task, stop_item_tasks
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_verified_user_by_token
from open_webui.utils.chat_id import is_saved_chat_id
from open_webui.utils.json_codec import SOCKETIO_JSON
from open_webui.utils.misc import get_output_text
from open_webui.utils.redis import (
    build_sentinel_url,
    get_redis_connection,
    get_sentinels_from_env,
)
from socketio.packet import Packet

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


# Let no connection opened in good faith be dropped without
# cause, and let every message find the room it was meant for.
REDIS = None

# Configure CORS for Socket.IO
SOCKETIO_CORS_ORIGINS = '*' if CORS_ALLOW_ORIGIN == ['*'] else CORS_ALLOW_ORIGIN


def get_room_sid_map(manager, namespace: str, room: str):
    """Return this process's Socket.IO sid map for a room, without copying it."""
    return manager.rooms.get(namespace, {}).get(room)


class JSONOnlyPacket(Packet):
    """Packet class for JSON-serializable payloads only, skipping python-socketio's per-emit binary scan."""

    uses_binary_events = False

    @classmethod
    def reconstruct_binary(cls, data: Any, attachments: list[bytes]):
        """Normalize client attachments to int lists, the form the Yjs handlers store and apply."""
        return super().reconstruct_binary(data, [list(attachment) for attachment in attachments])


if WEBSOCKET_MANAGER == 'redis':
    sentinel_hosts = WEBSOCKET_SENTINEL_HOSTS or ''
    ws_redis_url = (
        build_sentinel_url(WEBSOCKET_REDIS_URL, sentinel_hosts, WEBSOCKET_SENTINEL_PORT)
        if sentinel_hosts
        else WEBSOCKET_REDIS_URL
    )
    redis_manager = socketio.AsyncRedisManager(ws_redis_url, redis_options=WEBSOCKET_REDIS_OPTIONS, json=SOCKETIO_JSON)
    sio = socketio.AsyncServer(
        cors_allowed_origins=SOCKETIO_CORS_ORIGINS,
        async_mode='asgi',
        json=SOCKETIO_JSON,
        serializer=JSONOnlyPacket,
        transports=(['websocket'] if ENABLE_WEBSOCKET_SUPPORT else ['polling']),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        client_manager=redis_manager,
        logger=WEBSOCKET_SERVER_LOGGING,
        ping_interval=WEBSOCKET_SERVER_PING_INTERVAL,
        ping_timeout=WEBSOCKET_SERVER_PING_TIMEOUT,
        engineio_logger=WEBSOCKET_SERVER_ENGINEIO_LOGGING,
    )
else:
    sio = socketio.AsyncServer(
        cors_allowed_origins=SOCKETIO_CORS_ORIGINS,
        async_mode='asgi',
        json=SOCKETIO_JSON,
        serializer=JSONOnlyPacket,
        transports=(['websocket'] if ENABLE_WEBSOCKET_SUPPORT else ['polling']),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        logger=WEBSOCKET_SERVER_LOGGING,
        ping_interval=WEBSOCKET_SERVER_PING_INTERVAL,
        ping_timeout=WEBSOCKET_SERVER_PING_TIMEOUT,
        engineio_logger=WEBSOCKET_SERVER_ENGINEIO_LOGGING,
    )


# Timeout duration in seconds
TIMEOUT_DURATION = 3
SESSION_POOL_TIMEOUT = max(WEBSOCKET_HEARTBEAT_INTERVAL * 4, 120) if WEBSOCKET_HEARTBEAT_INTERVAL is not None else 120

# Dictionary to maintain the user pool

if WEBSOCKET_MANAGER == 'redis':
    log.debug('Using Redis to manage websockets.')
    ws_sentinels = get_sentinels_from_env(WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT)
    REDIS = get_redis_connection(
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=ws_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
        async_mode=True,
    )

    MODELS = RedisDict(
        f'{REDIS_KEY_PREFIX}:models',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=ws_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
        cache_set_signature=True,
    )

    SESSION_POOL = RedisDict(
        f'{REDIS_KEY_PREFIX}:session_pool',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=ws_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
    USAGE_POOL = RedisDict(
        f'{REDIS_KEY_PREFIX}:usage_pool',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=ws_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )

    clean_up_lock = RedisLock(
        redis_url=WEBSOCKET_REDIS_URL,
        lock_name=f'{REDIS_KEY_PREFIX}:usage_cleanup_lock',
        timeout_secs=WEBSOCKET_REDIS_LOCK_TIMEOUT,
        redis_sentinels=ws_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
    aquire_func = clean_up_lock.aquire_lock
    renew_func = clean_up_lock.renew_lock
    release_func = clean_up_lock.release_lock

    session_cleanup_lock = RedisLock(
        redis_url=WEBSOCKET_REDIS_URL,
        lock_name=f'{REDIS_KEY_PREFIX}:session_cleanup_lock',
        timeout_secs=WEBSOCKET_REDIS_LOCK_TIMEOUT,
        redis_sentinels=ws_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
    session_aquire_func = session_cleanup_lock.aquire_lock
    session_renew_func = session_cleanup_lock.renew_lock
    session_release_func = session_cleanup_lock.release_lock
else:
    MODELS = {}

    SESSION_POOL = {}
    USAGE_POOL = {}

    aquire_func = release_func = renew_func = lambda: True
    session_aquire_func = session_release_func = session_renew_func = lambda: True


YDOC_MANAGER = YdocManager(
    redis=REDIS,
    redis_key_prefix=f'{REDIS_KEY_PREFIX}:ydoc:documents',
)


def get_session_pool_batches():
    """All session pool entries, in bounded batches for the Redis backing."""
    if WEBSOCKET_MANAGER == 'redis':
        return SESSION_POOL.scan_batches()
    return [list(SESSION_POOL.items())]


async def periodic_session_pool_cleanup():
    """Reap orphaned SESSION_POOL entries that missed heartbeats (e.g. crashed instance)."""
    retry_delay = random.uniform(WEBSOCKET_REDIS_LOCK_TIMEOUT / 2, WEBSOCKET_REDIS_LOCK_TIMEOUT)
    renew_interval = max(WEBSOCKET_REDIS_LOCK_TIMEOUT / 2, 0.5)
    while True:
        if not session_aquire_func():
            log.debug('Session cleanup lock held by another node. Retrying.')
            await asyncio.sleep(retry_delay)
            continue

        try:
            while True:
                if not session_renew_func():
                    log.warning('Unable to renew session cleanup lock. Retrying cleanup ownership.')
                    break

                now = int(time.time())
                for batch in get_session_pool_batches():
                    expired = [
                        sid
                        for sid, entry in batch
                        if entry and now - entry.get('last_seen_at', 0) > SESSION_POOL_TIMEOUT
                    ]
                    if expired:
                        log.warning('Reaping %d orphaned session(s) from the session pool', len(expired))
                        if WEBSOCKET_MANAGER == 'redis':
                            SESSION_POOL.delete_many(*expired)
                        else:
                            for sid in expired:
                                SESSION_POOL.pop(sid, None)
                    await asyncio.sleep(0)  # don't hold the loop for the whole sweep

                next_cleanup_at = time.monotonic() + SESSION_POOL_TIMEOUT
                lock_lost = False
                while True:
                    sleep_for = min(renew_interval, next_cleanup_at - time.monotonic())
                    if sleep_for <= 0:
                        break
                    await asyncio.sleep(sleep_for)
                    if not session_renew_func():
                        log.warning('Unable to renew session cleanup lock. Retrying cleanup ownership.')
                        lock_lost = True
                        break

                if lock_lost:
                    break
        finally:
            session_release_func()


async def periodic_usage_pool_cleanup():
    retry_delay = random.uniform(WEBSOCKET_REDIS_LOCK_TIMEOUT / 2, WEBSOCKET_REDIS_LOCK_TIMEOUT)
    while True:
        try:
            if not aquire_func():
                log.debug('Usage cleanup lock held by another node. Retrying.')
                await asyncio.sleep(retry_delay)
                continue

            try:
                while True:
                    if not renew_func():
                        log.warning('Unable to renew usage cleanup lock. Retrying cleanup ownership.')
                        break

                    now = int(time.time())
                    for model_id, connections in list(USAGE_POOL.items()):
                        expired_sids = [
                            sid
                            for sid, details in connections.items()
                            if now - details['updated_at'] > TIMEOUT_DURATION
                        ]

                        if connections and not expired_sids:
                            continue

                        for sid in expired_sids:
                            del connections[sid]

                        if not connections:
                            log.debug('Cleaning up model %s from usage pool', model_id)
                            try:
                                del USAGE_POOL[model_id]
                            except KeyError:
                                pass
                        else:
                            USAGE_POOL[model_id] = connections
                    await asyncio.sleep(TIMEOUT_DURATION)
            finally:
                release_func()
        except Exception:
            log.exception('Usage pool cleanup failed. Retrying.')
            await asyncio.sleep(retry_delay)


app = socketio.ASGIApp(
    sio,
    socketio_path='/ws/socket.io',
)


def get_models_in_use():
    # List models that are currently in use
    models_in_use = list(USAGE_POOL.keys())
    return models_in_use


def get_user_id_from_session_pool(sid):
    user = SESSION_POOL.get(sid)
    if user:
        return user['id']
    return None


async def get_socket_session_user(sid: str) -> dict | None:
    """Session user from this worker's local Socket.IO store; only locally connected sids are ever looked up."""
    try:
        return (await sio.get_session(sid)).get('user')
    except KeyError:
        return None


def get_session_ids_from_room(room):
    """Get all session IDs from a specific room."""
    members = get_room_sid_map(sio.manager, '/', room)
    return list(members) if members else []


def get_session_ids_by_user_id(user_id: str) -> list[str]:
    """Get known session IDs for a user across the local rooms and shared session pool."""
    session_ids = set(get_session_ids_from_room(f'user:{user_id}'))
    session_ids.update(sid for sid, entry in SESSION_POOL.items() if entry and entry.get('id') == user_id)
    return list(session_ids)


async def get_user_ids_from_room(room) -> set[str]:
    users = [await get_socket_session_user(session_id) for session_id in get_session_ids_from_room(room)]
    return {user['id'] for user in users if user}


async def emit_to_users(event: str, data: dict, user_ids: list[str]):
    """
    Send a message to specific users using their user:{id} rooms.

    Args:
        event (str): The event name to emit.
        data (dict): The payload/data to send.
        user_ids (list[str]): The target users' IDs.
    """
    try:
        for user_id in user_ids:
            await sio.emit(event, data, room=f'user:{user_id}')
    except Exception as e:
        log.debug('Failed to emit event %s to users %s: %s', event, user_ids, e)


async def enter_room_for_users(room: str, user_ids: list[str]):
    """
    Make all sessions of a user join a specific room.
    Args:
        room (str): The room to join.
        user_ids (list[str]): The target user's IDs.
    """
    try:
        for user_id in user_ids:
            session_ids = get_session_ids_from_room(f'user:{user_id}')
            for sid in session_ids:
                await sio.enter_room(sid, room)
    except Exception as e:
        log.debug('Failed to make users %s join room %s: %s', user_ids, room, e)


async def disconnect_user_sessions(user_id: str):
    """Disconnect all Socket.IO sessions belonging to a user.

    Call this when a user's role is changed or the user is deleted so that
    stale role/permission data cached in SESSION_POOL is invalidated.
    The client will automatically reconnect and re-authenticate with
    fresh data from the database.
    """
    session_ids = get_session_ids_by_user_id(user_id)
    for sid in session_ids:
        try:
            await sio.disconnect(sid)
        except Exception:
            log.exception('Failed to disconnect session %s for user %s', sid, user_id)

    if session_ids:
        log.info('Requested disconnect of %s session(s) for user %s', len(session_ids), user_id)


@sio.on('usage')
async def usage(sid, data):
    if await get_socket_session_user(sid):
        model_id = data['model']
        # Record the timestamp for the last update
        current_time = int(time.time())

        # Store the new usage data and task
        USAGE_POOL[model_id] = {
            **(USAGE_POOL.get(model_id) or {}),
            sid: {'updated_at': current_time},
        }


@sio.event
async def connect(sid, environ, auth):
    user = None
    if auth and 'token' in auth:
        scope = (environ or {}).get('asgi.scope') or {}
        fastapi_app = scope.get('app')
        redis = getattr(getattr(fastapi_app, 'state', None), 'redis', None) or REDIS
        user = await get_verified_user_by_token(auth['token'], redis)

        if user:
            socket_user = {
                **user.model_dump(
                    exclude=[
                        'profile_image_url',
                        'profile_banner_image_url',
                        'date_of_birth',
                        'bio',
                        'gender',
                    ]
                ),
                'last_seen_at': int(time.time()),
            }
            SESSION_POOL[sid] = socket_user
            await sio.save_session(sid, {'user': socket_user})
            await sio.enter_room(sid, f'user:{user.id}')


@sio.on('user-join')
async def user_join(sid, data):
    auth = data.get('auth')
    if not auth or 'token' not in auth:
        return

    environ = sio.get_environ(sid) or {}
    scope = environ.get('asgi.scope') or {}
    fastapi_app = scope.get('app')
    redis = getattr(getattr(fastapi_app, 'state', None), 'redis', None) or REDIS
    user = await get_verified_user_by_token(auth['token'], redis)
    if not user:
        return

    socket_user = {
        **user.model_dump(
            exclude=[
                'profile_image_url',
                'profile_banner_image_url',
                'date_of_birth',
                'bio',
                'gender',
            ]
        ),
        'last_seen_at': int(time.time()),
    }

    SESSION_POOL[sid] = socket_user
    await sio.save_session(sid, {'user': socket_user})
    await sio.enter_room(sid, f'user:{user.id}')

    # Join all the channels only if user has channels permission
    if user.role == 'admin' or await has_permission(user.id, 'features.channels'):
        channels = await Channels.get_channels_by_user_id(user.id)
        log.debug('channels=%r', channels)
        for channel in channels:
            await sio.enter_room(sid, f'channel:{channel.id}')

    return {'id': user.id, 'name': user.name}


@sio.on('heartbeat')
async def heartbeat(sid, data):
    user = await get_socket_session_user(sid)
    if user:
        SESSION_POOL[sid] = {**user, 'last_seen_at': int(time.time())}
        await Users.update_last_active_by_id(user['id'])


@sio.on('join-channels')
async def join_channel(sid, data):
    auth = data['auth'] if 'auth' in data else None
    if not auth or 'token' not in auth:
        return

    environ = sio.get_environ(sid) or {}
    scope = environ.get('asgi.scope') or {}
    fastapi_app = scope.get('app')
    redis = getattr(getattr(fastapi_app, 'state', None), 'redis', None) or REDIS
    user = await get_verified_user_by_token(auth['token'], redis)
    if not user:
        return

    # Join all the channels only if user has channels permission
    if user.role == 'admin' or await has_permission(user.id, 'features.channels'):
        channels = await Channels.get_channels_by_user_id(user.id)
        log.debug('channels=%r', channels)
        for channel in channels:
            await sio.enter_room(sid, f'channel:{channel.id}')


@sio.on('join-note')
async def join_note(sid, data):
    auth = data['auth'] if 'auth' in data else None
    if not auth or 'token' not in auth:
        return

    environ = sio.get_environ(sid) or {}
    scope = environ.get('asgi.scope') or {}
    fastapi_app = scope.get('app')
    redis = getattr(getattr(fastapi_app, 'state', None), 'redis', None) or REDIS
    user = await get_verified_user_by_token(auth['token'], redis)
    if not user:
        return

    note = await Notes.get_note_by_id(data['note_id'])
    if not note:
        log.error(f'Note {data["note_id"]} not found for user {user.id}')
        return

    if (
        user.role != 'admin'
        and user.id != note.user_id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='read',
        )
    ):
        log.error(f'User {user.id} does not have access to note {data["note_id"]}')
        return

    log.debug('Joining note %s for user %s', note.id, user.id)
    await sio.enter_room(sid, f'note:{note.id}')


@sio.on('events:channel')
async def channel_events(sid, data):
    room = f'channel:{data["channel_id"]}'
    if sid not in (get_room_sid_map(sio.manager, '/', room) or {}):
        return

    event_data = data['data']
    event_type = event_data['type']

    user = await get_socket_session_user(sid)

    if not user:
        return

    if event_type == 'typing':
        await sio.emit(
            'events:channel',
            {
                'channel_id': data['channel_id'],
                'message_id': data.get('message_id', None),
                'data': event_data,
                'user': UserNameResponse(**user).model_dump(),
            },
            room=room,
        )
    elif event_type == 'last_read_at':
        await Channels.update_member_last_read_at(data['channel_id'], user['id'])


async def get_folder_unread_counts(user_id: str) -> dict[str, int]:
    folder_list = await Folders.get_folders_by_user_id(user_id)
    parent_by_id = {folder.id: folder.parent_id for folder in folder_list}
    unread_counts = dict.fromkeys(parent_by_id.keys(), 0)

    direct_unread_counts = await Chats.count_unread_by_folder_ids(user_id, list(parent_by_id.keys()))
    for unread_folder_id, unread_count in direct_unread_counts.items():
        current_id = unread_folder_id
        seen = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            if current_id in unread_counts:
                unread_counts[current_id] += unread_count
            current_id = parent_by_id.get(current_id)

    return unread_counts


@sio.on('events:chat')
async def chat_events(sid, data):
    user = await get_socket_session_user(sid)
    if not user:
        return

    event_data = data.get('data', {})
    event_type = event_data.get('type')

    if event_type == 'last_read_at':
        read_update = await Chats.update_chat_last_read_at_by_id(data['chat_id'], user['id'])
        if not read_update:
            return
        last_read_at, was_unread = read_update
        response_data = {
            'chat_id': data['chat_id'],
            'last_read_at': last_read_at,
        }
        if was_unread:
            response_data['folder_unread_counts'] = await get_folder_unread_counts(user['id'])

        await sio.emit(
            'events',
            {
                'chat_id': data['chat_id'],
                'data': {
                    'type': 'chat:list',
                    'data': response_data,
                },
            },
            room=f'user:{user["id"]}',
        )
        try:
            from open_webui.utils.timers import cancel_timers_for_chat

            await cancel_timers_for_chat(data['chat_id'], 'chat.read', user['id'])
        except Exception:
            log.exception('Failed to cancel chat.read timers for chat %s', data.get('chat_id'))


def normalize_document_id(document_id: str) -> str:
    """Canonicalize document IDs to prevent auth bypass via prefix variants.

    YdocManager normalizes storage keys by replacing ":" with "_", so
    "note_abc" and "note:abc" resolve to the same underlying document.
    We must rewrite underscore-prefixed IDs back to the colon form so
    that authorization checks (which key on "note:") always fire.
    """
    if document_id.startswith('note_'):
        document_id = 'note:' + document_id[5:]
    return document_id


@sio.on('ydoc:document:join')
async def ydoc_document_join(sid, data):
    """Handle user joining a document"""
    user = await get_socket_session_user(sid)
    if not user:
        return

    try:
        document_id = normalize_document_id(data['document_id'])

        if document_id.startswith('note:'):
            note_id = document_id.split(':')[1]
            note = await Notes.get_note_by_id(note_id)
            if not note:
                log.error(f'Note {note_id} not found')
                return

            if (
                user.get('role') != 'admin'
                and user.get('id') != note.user_id
                and not await AccessGrants.has_access(
                    user_id=user.get('id'),
                    resource_type='note',
                    resource_id=note.id,
                    permission='read',
                )
            ):
                log.error(f'User {user.get("id")} does not have access to note {note_id}')
                return

        user_id = data.get('user_id', sid)
        user_name = data.get('user_name', 'Anonymous')
        user_color = data.get('user_color', '#000000')

        log.info('User %s joining document %s', user_id, document_id)
        await YDOC_MANAGER.add_user(document_id=document_id, user_id=sid)

        # Join Socket.IO room
        await sio.enter_room(sid, f'doc_{document_id}')

        active_session_ids = get_session_ids_from_room(f'doc_{document_id}')

        # Get the Yjs document state
        ydoc = Y.Doc()
        updates = await YDOC_MANAGER.get_updates(document_id)
        for update in updates:
            ydoc.apply_update(bytes(update))

        # Encode the entire document state as an update
        state_update = ydoc.get_update()
        await sio.emit(
            'ydoc:document:state',
            {
                'document_id': document_id,
                'state': list(state_update),  # Convert bytes to list for JSON
                'sessions': active_session_ids,
            },
            room=sid,
        )

        # Notify other users about the new user
        await sio.emit(
            'ydoc:user:joined',
            {
                'document_id': document_id,
                'user_id': user_id,
                'user_name': user_name,
                'user_color': user_color,
            },
            room=f'doc_{document_id}',
            skip_sid=sid,
        )

        log.info('User %s successfully joined document %s', user_id, document_id)

    except Exception as e:
        log.error(f'Error in yjs_document_join: {e}')
        await sio.emit('error', {'message': 'Failed to join document'}, room=sid)


async def document_save_handler(document_id, data, user):
    document_id = normalize_document_id(document_id)

    if document_id.startswith('note:'):
        note_id = document_id.split(':')[1]
        note = await Notes.get_note_by_id(note_id)
        if not note:
            log.error(f'Note {note_id} not found')
            return

        if (
            user.get('role') != 'admin'
            and user.get('id') != note.user_id
            and not await AccessGrants.has_access(
                user_id=user.get('id'),
                resource_type='note',
                resource_id=note.id,
                permission='write',
            )
        ):
            log.error(f'User {user.get("id")} does not have write access to note {note_id}')
            return

        await Notes.update_note_by_id(note_id, NoteUpdateForm(data=data))


@sio.on('ydoc:document:state')
async def yjs_document_state(sid, data):
    """Send the current state of the Yjs document to the user"""
    try:
        document_id = data['document_id']

        document_id = normalize_document_id(document_id)
        room = f'doc_{document_id}'

        active_session_ids = get_session_ids_from_room(room)

        if sid not in active_session_ids:
            log.warning(f'Session {sid} not in room {room}. Cannot send state.')
            return

        if not await YDOC_MANAGER.document_exists(document_id):
            log.warning(f'Document {document_id} not found')
            return

        # Get the Yjs document state
        ydoc = Y.Doc()
        updates = await YDOC_MANAGER.get_updates(document_id)
        for update in updates:
            ydoc.apply_update(bytes(update))

        # Encode the entire document state as an update
        state_update = ydoc.get_update()

        await sio.emit(
            'ydoc:document:state',
            {
                'document_id': document_id,
                'state': list(state_update),  # Convert bytes to list for JSON
                'sessions': active_session_ids,
            },
            room=sid,
        )
    except Exception as e:
        log.error(f'Error in yjs_document_state: {e}')


@sio.on('ydoc:document:update')
async def yjs_document_update(sid, data):
    """Handle Yjs document updates"""
    try:
        document_id = data['document_id']

        document_id = normalize_document_id(document_id)

        # Verify the sender actually joined this document room
        room = f'doc_{document_id}'
        active_session_ids = get_session_ids_from_room(room)
        if sid not in active_session_ids:
            log.warning(f'Session {sid} not in room {room}. Rejecting update.')
            return

        # Verify write permission — room membership only proves read access
        user = await get_socket_session_user(sid)
        if not user:
            return

        if document_id.startswith('note:'):
            note_id = document_id.split(':')[1]
            note = await Notes.get_note_by_id(note_id)
            if not note:
                log.error(f'Note {note_id} not found')
                return

            if (
                user.get('role') != 'admin'
                and user.get('id') != note.user_id
                and not await AccessGrants.has_access(
                    user_id=user.get('id'),
                    resource_type='note',
                    resource_id=note.id,
                    permission='write',
                )
            ):
                log.warning(f'User {user.get("id")} does not have write access to note {note_id}. Rejecting update.')
                return

        user_id = data.get('user_id', sid)

        update = data['update']  # List of bytes from frontend

        await YDOC_MANAGER.append_to_updates(
            document_id=document_id,
            update=update,  # Convert list of bytes to bytes
        )

        # Broadcast update to all other users in the document
        await sio.emit(
            'ydoc:document:update',
            {
                'document_id': document_id,
                'user_id': user_id,
                'update': update,
                'socket_id': sid,  # Add socket_id to match frontend filtering
            },
            room=f'doc_{document_id}',
            skip_sid=sid,
        )

        async def debounced_save():
            await asyncio.sleep(0.5)
            await document_save_handler(document_id, data.get('data', {}), user)

        if data.get('data'):
            # Only drop the pending save when a new one takes its place.
            # Updates without a content snapshot (the resync a client sends
            # after rejoining a document) would otherwise cancel the pending
            # save without scheduling a replacement, so the edits made just
            # before the resync never reach the database.
            try:
                await stop_item_tasks(REDIS, document_id)
            except Exception:
                pass

            await create_task(REDIS, debounced_save(), document_id)

    except Exception as e:
        log.error(f'Error in yjs_document_update: {e}')


@sio.on('ydoc:document:leave')
async def yjs_document_leave(sid, data):
    """Handle user leaving a document"""
    user = await get_socket_session_user(sid)
    if not user:  # authenticated session required (parity with sibling handlers)
        return
    try:
        document_id = normalize_document_id(data['document_id'])

        log.info('User %s leaving document %s', user['id'], document_id)

        # Remove user from the document
        await YDOC_MANAGER.remove_user(document_id=document_id, user_id=sid)

        # Leave Socket.IO room
        await sio.leave_room(sid, f'doc_{document_id}')

        # Notify other users; user_id is the authenticated identity, not client-supplied
        await sio.emit(
            'ydoc:user:left',
            {'document_id': document_id, 'user_id': user['id']},
            room=f'doc_{document_id}',
        )

        if await YDOC_MANAGER.document_exists(document_id) and len(await YDOC_MANAGER.get_users(document_id)) == 0:
            log.info('Cleaning up document %s as no users are left', document_id)
            await YDOC_MANAGER.clear_document(document_id)

    except Exception as e:
        log.error(f'Error in yjs_document_leave: {e}')


@sio.on('ydoc:awareness:update')
async def yjs_awareness_update(sid, data):
    """Handle awareness updates (cursors, selections, etc.)"""
    user = await get_socket_session_user(sid)
    if not user:  # authenticated session required (parity with sibling handlers)
        return
    try:
        document_id = normalize_document_id(data['document_id'])
        room = f'doc_{document_id}'
        if room not in sio.rooms(sid):  # must have joined the document first
            return
        update = data['update']

        # Broadcast to the room; user_id is the authenticated identity, not client-supplied
        await sio.emit(
            'ydoc:awareness:update',
            {'document_id': document_id, 'user_id': user['id'], 'update': update},
            room=room,
            skip_sid=sid,
        )

    except Exception as e:
        log.error(f'Error in yjs_awareness_update: {e}')


@sio.event
async def disconnect(sid, reason=None):
    if sid in SESSION_POOL:
        del SESSION_POOL[sid]

        # Clean up USAGE_POOL entries for this session
        for model_id, connections in list(USAGE_POOL.items()):
            if sid in connections:
                del connections[sid]
                if not connections:
                    del USAGE_POOL[model_id]
                else:
                    USAGE_POOL[model_id] = connections

        await YDOC_MANAGER.remove_user_from_all_documents(sid)
    else:
        pass
        # print(f"Unknown session ID {sid} disconnected")


async def _make_channel_emitter(request_info):
    """Event emitter that routes pipeline output to a channel message.

    Translates chat:completion events into channel message:update socket
    emissions, throttled to avoid flooding with per-token updates.
    """
    channel_id = request_info['chat_id'].removeprefix('channel:')
    message_id = request_info['message_id']

    state = {'last_emit_at': 0.0, 'output': []}
    THROTTLE_INTERVAL = 0.15  # ~6 updates/sec

    async def _emit_channel_update(
        content: str,
        done: bool = False,
        output: list | None = None,
        data: dict | None = None,
    ):
        from open_webui.models.messages import MessageForm, Messages

        msg = await Messages.get_message_by_id(message_id)
        if not msg or msg.channel_id != channel_id:
            return

        update_data = data or ({'output': output} if output else None)
        update_form = MessageForm(content=content, data=update_data)
        if done:
            # Merge done flag into existing meta (preserve model_id etc.)
            existing_meta = msg.meta or {}
            update_form = MessageForm(
                content=content,
                data=update_data,
                meta={**existing_meta, 'done': True},
            )

        await Messages.update_message_by_id(message_id, update_form)
        message = await Messages.get_message_by_id(message_id)
        if message:
            await sio.emit(
                'events:channel',
                {
                    'channel_id': channel_id,
                    'message_id': message_id,
                    'data': {
                        'type': 'message:update',
                        'data': message.model_dump(),
                    },
                },
                to=f'channel:{channel_id}',
            )

    async def __channel_emitter__(event_data):
        event_type = event_data.get('type')

        if event_type == 'chat:completion':
            data = event_data.get('data', {})
            output = data.get('output')
            content = data.get('content') or get_output_text(output)
            done = data.get('done', False)

            if not content and not output and not done:
                return

            now = time.time()
            if done or (now - state['last_emit_at']) >= THROTTLE_INTERVAL:
                state['last_emit_at'] = now
                await _emit_channel_update(content, done, output if isinstance(output, list) else None)

        elif event_type == 'response:completion':
            from open_webui.utils.middleware import handle_responses_streaming_event

            data = event_data.get('data', {})
            state['output'], _ = handle_responses_streaming_event(data, state['output'])
            content = get_output_text(state['output'])

            now = time.time()
            if content and (now - state['last_emit_at']) >= THROTTLE_INTERVAL:
                state['last_emit_at'] = now
                await _emit_channel_update(content, False, state['output'])

        elif event_type in ('files', 'chat:message:files'):
            from open_webui.models.messages import Messages

            files = event_data.get('data', {}).get('files', [])
            if not files:
                return

            msg = await Messages.get_message_by_id(message_id)
            if not msg or msg.channel_id != channel_id:
                return

            existing_files = (msg.data or {}).get('files')
            for file in files:
                if isinstance(file, dict) and file.get('id'):
                    file['url'] = file['id']
                    await Channels.add_file_to_channel_by_id(channel_id, file['id'], msg.user_id)
                    await Channels.set_file_message_id_in_channel_by_id(channel_id, file['id'], message_id)

            if isinstance(existing_files, list):
                files.extend(existing_files)

            await _emit_channel_update(msg.content, data={'files': files})

        elif event_type == 'chat:message:error':
            error = event_data.get('data', {}).get('error', {})
            error_content = error.get('content', 'An error occurred') if isinstance(error, dict) else str(error)
            await _emit_channel_update(f'Error: {error_content}', done=True)

    return __channel_emitter__


async def get_event_emitter(request_info, update_db=True):
    # Channel mode: route pipeline output to channel message updates
    if (request_info.get('chat_id') or '').startswith('channel:'):
        return await _make_channel_emitter(request_info)

    async def __event_emitter__(event_data):
        user_id = request_info['user_id']
        chat_id = request_info['chat_id']
        message_id = request_info['message_id']
        internal = request_info.get('internal') is True
        save_to_chat = update_db and message_id and is_saved_chat_id(chat_id)

        if internal and event_data.get('type') == 'notification':
            return

        room = f'user:{user_id}'
        # Local rooms are authoritative; Redis may have listeners on another instance.
        if WEBSOCKET_MANAGER == 'redis' or room in sio.manager.rooms.get('/', {}):
            await sio.emit(
                'events',
                {
                    'chat_id': chat_id,
                    'message_id': message_id,
                    **({'internal': True} if internal else {}),
                    'data': event_data,
                },
                room=room,
            )

        if save_to_chat:
            event_type = event_data.get('type')

            if event_type == 'status':
                await Chats.add_message_status_to_chat_by_id_and_message_id(
                    request_info['chat_id'],
                    request_info['message_id'],
                    event_data.get('data', {}),
                )

            elif event_type == 'message':
                message = await Chats.get_message_by_id_and_message_id(
                    request_info['chat_id'],
                    request_info['message_id'],
                )

                if message:
                    content = message.get('content', '')
                    content += event_data.get('data', {}).get('content', '')

                    await Chats.upsert_message_to_chat_by_id_and_message_id(
                        request_info['chat_id'],
                        request_info['message_id'],
                        {
                            'content': content,
                        },
                    )

            elif event_type == 'replace':
                content = event_data.get('data', {}).get('content', '')

                await Chats.upsert_message_to_chat_by_id_and_message_id(
                    request_info['chat_id'],
                    request_info['message_id'],
                    {
                        'content': content,
                    },
                )

            elif event_type == 'embeds':
                event_payload = event_data.get('data', {})
                embeds = event_payload.get('embeds', [])

                if not event_payload.get('replace', False):
                    existing_embeds = await Chats.get_message_metadata(chat_id, message_id, 'embeds')
                    if isinstance(existing_embeds, list):
                        embeds.extend(existing_embeds)

                await Chats.upsert_message_to_chat_by_id_and_message_id(
                    chat_id,
                    message_id,
                    {
                        'embeds': embeds,
                    },
                    touch=False,
                )

            elif event_type == 'files':
                files = event_data.get('data', {}).get('files', [])
                existing_files = await Chats.get_message_metadata(chat_id, message_id, 'files')
                if isinstance(existing_files, list):
                    files.extend(existing_files)

                await Chats.upsert_message_to_chat_by_id_and_message_id(
                    chat_id,
                    message_id,
                    {
                        'files': files,
                    },
                    touch=False,
                )

            elif event_type in ('source', 'citation'):
                data = event_data.get('data', {})
                if data.get('type') is None:
                    sources = await Chats.get_message_metadata(chat_id, message_id, 'sources')
                    if not isinstance(sources, list):
                        sources = []
                    sources.append(data)

                    await Chats.upsert_message_to_chat_by_id_and_message_id(
                        chat_id,
                        message_id,
                        {
                            'sources': sources,
                        },
                        touch=False,
                    )

    if 'user_id' in request_info and 'chat_id' in request_info and 'message_id' in request_info:
        return __event_emitter__
    else:
        return None


async def get_event_call(request_info):
    async def __event_caller__(event_data):
        session_id = request_info['session_id']

        # session_id is client-supplied; only the requesting user's own live session may be targeted.
        session = SESSION_POOL.get(session_id)
        if session is None or session.get('id') != request_info.get('user_id'):
            log.warning(f'Event caller: session {session_id} not owned by requesting user or disconnected')
            return {'error': 'Client session disconnected.'}

        try:
            return await sio.call(
                'events',
                {
                    'chat_id': request_info.get('chat_id', None),
                    'message_id': request_info.get('message_id', None),
                    'data': event_data,
                },
                to=session_id,
                timeout=WEBSOCKET_EVENT_CALLER_TIMEOUT,
            )
        except (TimeoutError, socketio.exceptions.TimeoutError):
            log.warning(f'Event caller timed out for session {session_id}')
            return {'error': 'Event call timed out. The browser tab may be inactive or closed.'}

    if 'session_id' in request_info and 'chat_id' in request_info and 'message_id' in request_info:
        return __event_caller__
    else:
        return None


get_event_caller = get_event_call
