from __future__ import annotations

import asyncio
import logging
import random
import sys
import time
from typing import Dict

import pycrdt as Y
import aiortc
import json
import socketio
from open_webui.config import (
    CORS_ALLOW_ORIGIN,
)
from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
    GLOBAL_LOG_LEVEL,
    REDIS_KEY_PREFIX,
    VERSION,
    WEBSOCKET_EVENT_CALLER_TIMEOUT,
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
    INSTANCE_ID
)
from open_webui.models.access_grants import AccessGrants
from open_webui.models.channels import Channels
from open_webui.models.chats import Chats
from open_webui.models.notes import Notes, NoteUpdateForm
from open_webui.models.users import UserNameResponse, Users
from open_webui.socket.utils import RedisDict, RedisLock, YdocManager, SelectiveForwardingUnit
from open_webui.tasks import create_task, stop_item_tasks
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import decode_token
from open_webui.utils.redis import (
    get_redis_connection,
    get_sentinel_url_from_env,
    get_sentinels_from_env,
)
from redis import asyncio as aioredis

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


# Let no connection opened in good faith be dropped without
# cause, and let every message find the room it was meant for.
REDIS = None

# Configure CORS for Socket.IO
SOCKETIO_CORS_ORIGINS = '*' if CORS_ALLOW_ORIGIN == ['*'] else CORS_ALLOW_ORIGIN

if WEBSOCKET_MANAGER == 'redis':
    if WEBSOCKET_SENTINEL_HOSTS:
        mgr = socketio.AsyncRedisManager(
            get_sentinel_url_from_env(WEBSOCKET_REDIS_URL, WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT),
            redis_options=WEBSOCKET_REDIS_OPTIONS,
        )
    else:
        mgr = socketio.AsyncRedisManager(WEBSOCKET_REDIS_URL, redis_options=WEBSOCKET_REDIS_OPTIONS)
    sio = socketio.AsyncServer(
        cors_allowed_origins=SOCKETIO_CORS_ORIGINS,
        async_mode='asgi',
        transports=(['websocket'] if ENABLE_WEBSOCKET_SUPPORT else ['polling']),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        client_manager=mgr,
        logger=WEBSOCKET_SERVER_LOGGING,
        ping_interval=WEBSOCKET_SERVER_PING_INTERVAL,
        ping_timeout=WEBSOCKET_SERVER_PING_TIMEOUT,
        engineio_logger=WEBSOCKET_SERVER_ENGINEIO_LOGGING,
    )
else:
    sio = socketio.AsyncServer(
        cors_allowed_origins=SOCKETIO_CORS_ORIGINS,
        async_mode='asgi',
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
SESSION_POOL_TIMEOUT = 120  # seconds without heartbeat before session is reaped

# Dictionary to maintain the user pool

if WEBSOCKET_MANAGER == 'redis':
    log.debug('Using Redis to manage websockets.')
    REDIS = get_redis_connection(
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=get_sentinels_from_env(WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT),
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
        async_mode=True,
    )

    redis_sentinels = get_sentinels_from_env(WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT)

    MODELS = RedisDict(
        f'{REDIS_KEY_PREFIX}:models',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )

    SESSION_POOL = RedisDict(
        f'{REDIS_KEY_PREFIX}:session_pool',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
    USAGE_POOL = RedisDict(
        f'{REDIS_KEY_PREFIX}:usage_pool',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )

    clean_up_lock = RedisLock(
        redis_url=WEBSOCKET_REDIS_URL,
        lock_name=f'{REDIS_KEY_PREFIX}:usage_cleanup_lock',
        timeout_secs=WEBSOCKET_REDIS_LOCK_TIMEOUT,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
    aquire_func = clean_up_lock.aquire_lock
    renew_func = clean_up_lock.renew_lock
    release_func = clean_up_lock.release_lock

    session_cleanup_lock = RedisLock(
        redis_url=WEBSOCKET_REDIS_URL,
        lock_name=f'{REDIS_KEY_PREFIX}:session_cleanup_lock',
        timeout_secs=WEBSOCKET_REDIS_LOCK_TIMEOUT,
        redis_sentinels=redis_sentinels,
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


# Local SFU (Selective Forwarding Unit) instances for active calls on this node
SFU_POOL = {}

if WEBSOCKET_MANAGER == 'redis':
    # Shared across nodes: maps channel_id -> {instance_id, created_at} so signaling
    # events arriving at a non-hosting node are relayed via pub/sub to the correct one
    SFU_REGISTRY = RedisDict(
        f'{REDIS_KEY_PREFIX}:sfu:registry',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )

    # Shared across nodes: maps sid -> channel_id for cleanup on disconnect
    SFU_SESSIONS = RedisDict(
        f'{REDIS_KEY_PREFIX}:sfu:sessions',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )

    # Shared across nodes: maps channel_id -> {active, participantCount} so users
    # connected to a non-hosting node can read initial call status on join-channels
    SFU_STATUS = RedisDict(
        f'{REDIS_KEY_PREFIX}:sfu:status',
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
else:
    SFU_REGISTRY = {}  # unused in single-instance mode
    SFU_SESSIONS = {}  # local dict: maps sid -> channel_id for cleanup on disconnect
    SFU_STATUS = {}  # local dict: maps channel_id -> {active, participantCount}


YDOC_MANAGER = YdocManager(
    redis=REDIS,
    redis_key_prefix=f'{REDIS_KEY_PREFIX}:ydoc:documents',
)


async def periodic_session_pool_cleanup():
    """Reap orphaned SESSION_POOL entries that missed heartbeats (e.g. crashed instance)."""
    if not session_aquire_func():
        log.debug('Session cleanup lock held by another node. Skipping.')
        return

    try:
        while True:
            if not session_renew_func():
                log.error('Unable to renew session cleanup lock. Exiting.')
                return

            now = int(time.time())
            for sid in list(SESSION_POOL.keys()):
                entry = SESSION_POOL.get(sid)
                if entry and now - entry.get('last_seen_at', 0) > SESSION_POOL_TIMEOUT:
                    log.warning(f'Reaping orphaned session {sid} (user {entry.get("id")})')
                    del SESSION_POOL[sid]
            await asyncio.sleep(SESSION_POOL_TIMEOUT)
    finally:
        session_release_func()


async def periodic_usage_pool_cleanup():
    max_retries = 2
    retry_delay = random.uniform(WEBSOCKET_REDIS_LOCK_TIMEOUT / 2, WEBSOCKET_REDIS_LOCK_TIMEOUT)
    for attempt in range(max_retries + 1):
        if aquire_func():
            break
        else:
            if attempt < max_retries:
                log.debug(f'Cleanup lock already exists. Retry {attempt + 1} after {retry_delay}s...')
                await asyncio.sleep(retry_delay)
            else:
                log.warning('Failed to acquire cleanup lock after retries. Skipping cleanup.')
                return

    log.debug('Running periodic_cleanup')
    try:
        while True:
            if not renew_func():
                log.error(f'Unable to renew cleanup lock. Exiting usage pool cleanup.')
                raise Exception('Unable to renew usage pool cleanup lock.')

            now = int(time.time())
            send_usage = False
            for model_id, connections in list(USAGE_POOL.items()):
                # Creating a list of sids to remove if they have timed out
                expired_sids = [
                    sid for sid, details in connections.items() if now - details['updated_at'] > TIMEOUT_DURATION
                ]

                for sid in expired_sids:
                    del connections[sid]

                if not connections:
                    log.debug(f'Cleaning up model {model_id} from usage pool')
                    del USAGE_POOL[model_id]
                else:
                    USAGE_POOL[model_id] = connections

                send_usage = True
            await asyncio.sleep(TIMEOUT_DURATION)
    finally:
        release_func()


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


def get_session_ids_from_room(room):
    """Get all session IDs from a specific room."""
    active_session_ids = sio.manager.get_participants(
        namespace='/',
        room=room,
    )
    return [session_id[0] for session_id in active_session_ids]


def get_user_ids_from_room(room):
    active_session_ids = get_session_ids_from_room(room)

    active_user_ids = list(
        set(
            [
                SESSION_POOL.get(session_id)['id']
                for session_id in active_session_ids
                if SESSION_POOL.get(session_id) is not None
            ]
        )
    )
    return active_user_ids


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
        log.debug(f'Failed to emit event {event} to users {user_ids}: {e}')


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
        log.debug(f'Failed to make users {user_ids} join room {room}: {e}')


async def disconnect_user_sessions(user_id: str):
    """Disconnect all Socket.IO sessions belonging to a user.

    Call this when a user's role is changed or the user is deleted so that
    stale role/permission data cached in SESSION_POOL is invalidated.
    The client will automatically reconnect and re-authenticate with
    fresh data from the database.
    """
    try:
        session_ids = get_session_ids_from_room(f'user:{user_id}')
        for sid in session_ids:
            await sio.disconnect(sid)
        if session_ids:
            log.info(f'Disconnected {len(session_ids)} session(s) for user {user_id}')
    except Exception as e:
        log.warning(f'Failed to disconnect sessions for user {user_id}: {e}')


@sio.on('usage')
async def usage(sid, data):
    if sid in SESSION_POOL:
        model_id = data['model']
        # Record the timestamp for the last update
        current_time = int(time.time())

        # Store the new usage data and task
        USAGE_POOL[model_id] = {
            **(USAGE_POOL[model_id] if model_id in USAGE_POOL else {}),
            sid: {'updated_at': current_time},
        }


@sio.event
async def connect(sid, environ, auth):
    user = None
    if auth and 'token' in auth:
        data = decode_token(auth['token'])

        if data is not None and 'id' in data:
            user = await Users.get_user_by_id(data['id'])

        if user:
            SESSION_POOL[sid] = {
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
            await sio.enter_room(sid, f'user:{user.id}')


@sio.on('user-join')
async def user_join(sid, data):
    auth = data.get('auth')
    if not auth or 'token' not in auth:
        return

    token_data = decode_token(auth['token'])
    if token_data is None or 'id' not in token_data:
        return

    user = await Users.get_user_by_id(token_data['id'])
    if not user:
        return

    SESSION_POOL[sid] = {
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

    await sio.enter_room(sid, f'user:{user.id}')

    # Join all the channels only if user has channels permission
    if user.role == 'admin' or await has_permission(user.id, 'features.channels'):
        channels = await Channels.get_channels_by_user_id(user.id)
        log.debug(f'{channels=}')
        for channel in channels:
            await sio.enter_room(sid, f'channel:{channel.id}')

    return {'id': user.id, 'name': user.name}


@sio.on('heartbeat')
async def heartbeat(sid, data):
    user = SESSION_POOL.get(sid)
    if user:
        SESSION_POOL[sid] = {**user, 'last_seen_at': int(time.time())}
        await Users.update_last_active_by_id(user['id'])


@sio.on('join-channels')
async def join_channel(sid, data):
    auth = data['auth'] if 'auth' in data else None
    if not auth or 'token' not in auth:
        return

    data = decode_token(auth['token'])
    if data is None or 'id' not in data:
        return

    user = await Users.get_user_by_id(data['id'])
    if not user:
        return

    # Join all the channels only if user has channels permission
    if user.role == 'admin' or await has_permission(user.id, 'features.channels'):
        channels = await Channels.get_channels_by_user_id(user.id)
        log.debug(f'{channels=}')
        for channel in channels:
            await sio.enter_room(sid, f'channel:{channel.id}')


@sio.on('join-note')
async def join_note(sid, data):
    auth = data['auth'] if 'auth' in data else None
    if not auth or 'token' not in auth:
        return

    token_data = decode_token(auth['token'])
    if token_data is None or 'id' not in token_data:
        return

    user = await Users.get_user_by_id(token_data['id'])
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

    log.debug(f'Joining note {note.id} for user {user.id}')
    await sio.enter_room(sid, f'note:{note.id}')


@sio.on('events:channel')
async def channel_events(sid, data):
    room = f'channel:{data["channel_id"]}'
    participants = sio.manager.get_participants(
        namespace='/',
        room=room,
    )

    sids = [sid for sid, _ in participants]
    if sid not in sids:
        return

    event_data = data['data']
    event_type = event_data['type']

    user = SESSION_POOL.get(sid)

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


@sio.on('events:chat')
async def chat_events(sid, data):
    user = SESSION_POOL.get(sid)
    if not user:
        return

    event_data = data.get('data', {})
    event_type = event_data.get('type')

    if event_type == 'last_read_at':
        await Chats.update_chat_last_read_at_by_id(data['chat_id'], user['id'])


def get_sfu_for_channel(channel_id):
    sfu = SFU_POOL.get(channel_id)
    if sfu is None:
        # deferred: open_webui.main imports socket.main at top level (circular)
        from open_webui.main import app

        ice_servers = app.state.config.ICE_SERVERS

        log.info(f'call:sfu creating new SFU for channel {channel_id}')
        sfu = SelectiveForwardingUnit(channel_id, ice_servers=ice_servers)

        @sfu.on('status-changed')
        async def handle_status_changed():
            active = not sfu.is_empty()
            participant_count = len(sfu.peers)
            if active:
                SFU_STATUS[channel_id] = {'active': True, 'participantCount': participant_count}
            elif channel_id in SFU_STATUS:
                del SFU_STATUS[channel_id]
            await sio.emit(
                'channel:call:status',
                {'channel_id': channel_id, 'active': active, 'participantCount': participant_count},
                room=f'channel:{channel_id}',
            )

        @sfu.on('renegotiate')
        async def handle_renegotiation_request(to_sid, renegotiation_entries):
            enriched_track_data = []
            for renegotiation_entry in renegotiation_entries:
                peer_sid = renegotiation_entry.peer_id
                peer_user = SESSION_POOL.get(peer_sid)
                user_info = (
                    UserNameResponse(**peer_user).model_dump()
                    if peer_user
                    else {'id': peer_sid, 'name': 'Unknown', 'role': ''}
                )
                enriched_track_data.append(
                    {
                        'peer_id': peer_sid,
                        'user': user_info,
                        'kind': renegotiation_entry.kind,
                        'track_id': renegotiation_entry.track_id,
                    }
                )

            await sio.emit(
                'channel:call:renegotiate', {'channel_id': channel_id, 'data': enriched_track_data}, to=to_sid
            )

        SFU_POOL[channel_id] = sfu

    return sfu


async def relay_to_sfu_host(channel_id, event, sid, data):
    if WEBSOCKET_MANAGER != 'redis':
        return False

    registry_entry = SFU_REGISTRY.get(channel_id)
    if not registry_entry or registry_entry['instance_id'] == INSTANCE_ID:
        return False

    relay_channel = f'{REDIS_KEY_PREFIX}:sfu:relay:{registry_entry["instance_id"]}'
    await REDIS.publish(relay_channel, json.dumps({'event': event, 'sid': sid, 'data': data}))
    return True


async def channel_call_sfu_handle_offer(sid, data):
    channel_id = data['channel_id']
    signal_data = data['data']

    sfu = get_sfu_for_channel(channel_id)
    offer_result = await sfu.handle_offer(sid, signal_data.get('sdp'), signal_data.get('type'))
    if offer_result is None:
        return

    await sio.emit(
        'channel:call:answer',
        {
            'channel_id': channel_id,
            'data': {
                'sdp': offer_result.description.sdp,
                'type': offer_result.description.type,
                'track_ids': [
                    {'track_id': track_info.track_id, 'kind': track_info.kind} for track_info in offer_result.new_tracks
                ],
            },
        },
        to=sid,
    )


async def channel_call_sfu_handle_ice_candidate(sid, data):
    channel_id = data['channel_id']
    sfu = SFU_POOL.get(channel_id)
    if not sfu:
        return

    candidate_data = data.get('data')
    await sfu.handle_ice_candidate(sid, candidate_data)


async def channel_call_sfu_handle_leave(sid, data):
    channel_id = data['channel_id']
    sfu = SFU_POOL.get(channel_id)
    if not sfu:
        return

    await sfu.remove_peer(sid)

    for peer_sid in list(sfu.peers.keys()):
        await sio.emit(
            'channel:call:peer-left',
            {'channel_id': channel_id, 'data': {'peer_id': sid}},
            to=peer_sid,
        )

    if sfu.is_empty():
        log.info(f'call: removing empty SFU for channel {channel_id}')
        sfu.destroy()
        del SFU_POOL[channel_id]
        if WEBSOCKET_MANAGER == 'redis' and channel_id in SFU_REGISTRY:
            del SFU_REGISTRY[channel_id]


async def channel_call_sfu_handle_track_event(sid, data):
    channel_id = data['channel_id']
    event_data = data['data']
    track_id = event_data['track_id']
    action = event_data['action']

    sfu = SFU_POOL.get(channel_id)
    if not sfu:
        return

    track_owner = sfu.track_metadata.get(track_id)
    if not track_owner or track_owner.sid != sid:
        return

    if action == 'kill':
        sfu.handle_track_kill(track_id)

    for peer_sid in list(sfu.peers.keys()):
        if peer_sid == sid:
            continue
        await sio.emit(
            'channel:call:track-event',
            {'channel_id': channel_id, 'data': event_data},
            to=peer_sid,
        )


async def channel_call_message_relayer():
    if WEBSOCKET_MANAGER != 'redis' or REDIS is None:
        return

    channel_name = f'{REDIS_KEY_PREFIX}:sfu:relay:{INSTANCE_ID}'
    pubsub = REDIS.pubsub()
    await pubsub.subscribe(channel_name)

    try:
        async for message in pubsub.listen():
            if message['type'] != 'message':
                continue

            try:
                payload = json.loads(message['data'])
                event = payload['event']
                sid = payload['sid']
                data = payload['data']

                if event == 'offer':
                    await channel_call_sfu_handle_offer(sid, data)
                elif event == 'ice-candidate':
                    await channel_call_sfu_handle_ice_candidate(sid, data)
                elif event == 'leave':
                    await channel_call_sfu_handle_leave(sid, data)
                elif event == 'track-event':
                    await channel_call_sfu_handle_track_event(sid, data)
            except Exception as e:
                log.error(f'call: error processing relayed message: {e}', exc_info=True)
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()


@sio.on('channel:call:status:get')
async def channel_call_status_get(sid, data):
    channel_id = data.get('channel_id')
    if not channel_id:
        return
    status = SFU_STATUS.get(channel_id)
    if not status:
        return
    await sio.emit(
        'channel:call:status',
        {'channel_id': channel_id, **status},
        to=sid,
    )


@sio.on('channel:call:offer')
async def channel_call_peer_offer(sid, data):
    try:
        user = SESSION_POOL.get(sid)
        if not user:
            return

        if user.get('role') != 'admin' and not has_permission(user['id'], 'features.channels'):
            return

        channel_id = data['channel_id']

        # verify user is a member of this channel's room
        room = f'channel:{channel_id}'
        participants = sio.manager.get_participants(namespace='/', room=room)
        if sid not in [s for s, _ in participants]:
            return

        # check if user is in a different call
        existing_channel_id = SFU_SESSIONS.get(sid)
        if existing_channel_id and existing_channel_id != channel_id:
            return

        SFU_SESSIONS[sid] = channel_id

        if WEBSOCKET_MANAGER == 'redis':
            if await relay_to_sfu_host(channel_id, 'offer', sid, data):
                return

            # no SFU exists yet; atomically claim this call for our instance
            registry_entry = SFU_REGISTRY.get(channel_id)
            if not registry_entry:
                claimed = SFU_REGISTRY.setnx(channel_id, {'instance_id': INSTANCE_ID, 'created_at': int(time.time())})
                if not claimed:
                    # another instance won the race — relay to them
                    await relay_to_sfu_host(channel_id, 'offer', sid, data)
                    return

        await channel_call_sfu_handle_offer(sid, data)
    except Exception as e:
        log.error(f'call: error handling offer from {sid}: {e}', exc_info=True)


@sio.on('channel:call:ice-candidate')
async def channel_call_peer_ice_candidate(sid, data):
    try:
        user = SESSION_POOL.get(sid)
        if not user:
            return

        channel_id = data['channel_id']

        if SFU_SESSIONS.get(sid) != channel_id:
            return

        if await relay_to_sfu_host(channel_id, 'ice-candidate', sid, data):
            return

        await channel_call_sfu_handle_ice_candidate(sid, data)
    except Exception as e:
        log.error(f'call: error handling ice-candidate from {sid}: {e}', exc_info=True)


@sio.on('channel:call:track-event')
async def channel_call_peer_track_event(sid, data):
    try:
        user = SESSION_POOL.get(sid)
        if not user:
            return

        channel_id = data['channel_id']

        if SFU_SESSIONS.get(sid) != channel_id:
            return

        if await relay_to_sfu_host(channel_id, 'track-event', sid, data):
            return

        await channel_call_sfu_handle_track_event(sid, data)
    except Exception as e:
        log.error(f'call: error handling track-event from {sid}: {e}', exc_info=True)


@sio.on('channel:call:leave')
async def channel_call_peer_leave(sid, data):
    try:
        user = SESSION_POOL.get(sid)
        if not user:
            return

        channel_id = data['channel_id']

        if SFU_SESSIONS.get(sid) not in (channel_id, None):
            return

        del SFU_SESSIONS[sid]

        if await relay_to_sfu_host(channel_id, 'leave', sid, data):
            return

        await channel_call_sfu_handle_leave(sid, data)
    except Exception as e:
        log.error(f'call: error on leave from {sid}: {e}', exc_info=True)


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
    user = SESSION_POOL.get(sid)
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

        log.info(f'User {user_id} joining document {document_id}')
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

        log.info(f'User {user_id} successfully joined document {document_id}')

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
        user = SESSION_POOL.get(sid)
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

        try:
            await stop_item_tasks(REDIS, document_id)
        except Exception:
            pass

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
            await create_task(REDIS, debounced_save(), document_id)

    except Exception as e:
        log.error(f'Error in yjs_document_update: {e}')


@sio.on('ydoc:document:leave')
async def yjs_document_leave(sid, data):
    """Handle user leaving a document"""
    try:
        document_id = normalize_document_id(data['document_id'])
        user_id = data.get('user_id', sid)

        log.info(f'User {user_id} leaving document {document_id}')

        # Remove user from the document
        await YDOC_MANAGER.remove_user(document_id=document_id, user_id=sid)

        # Leave Socket.IO room
        await sio.leave_room(sid, f'doc_{document_id}')

        # Notify other users
        await sio.emit(
            'ydoc:user:left',
            {'document_id': document_id, 'user_id': user_id},
            room=f'doc_{document_id}',
        )

        if await YDOC_MANAGER.document_exists(document_id) and len(await YDOC_MANAGER.get_users(document_id)) == 0:
            log.info(f'Cleaning up document {document_id} as no users are left')
            await YDOC_MANAGER.clear_document(document_id)

    except Exception as e:
        log.error(f'Error in yjs_document_leave: {e}')


@sio.on('ydoc:awareness:update')
async def yjs_awareness_update(sid, data):
    """Handle awareness updates (cursors, selections, etc.)"""
    try:
        document_id = data['document_id']
        user_id = data.get('user_id', sid)
        update = data['update']

        # Broadcast awareness update to all other users in the document
        await sio.emit(
            'ydoc:awareness:update',
            {'document_id': document_id, 'user_id': user_id, 'update': update},
            room=f'doc_{document_id}',
            skip_sid=sid,
        )

    except Exception as e:
        log.error(f'Error in yjs_awareness_update: {e}')


@sio.event
async def disconnect(sid):
    if sid in SESSION_POOL:
        user = SESSION_POOL[sid]
        del SESSION_POOL[sid]

        # Clean up USAGE_POOL entries for this session
        for model_id in list(USAGE_POOL.keys()):
            connections = USAGE_POOL.get(model_id)
            if connections and sid in connections:
                del connections[sid]
                if not connections:
                    del USAGE_POOL[model_id]
                else:
                    USAGE_POOL[model_id] = connections

        await YDOC_MANAGER.remove_user_from_all_documents(sid)
    else:
        pass
        # print(f"Unknown session ID {sid} disconnected")

    # clean up any SFU connections for this session
    channel_id = SFU_SESSIONS.get(sid)
    if channel_id:
        del SFU_SESSIONS[sid]
        data = {'channel_id': channel_id}

        if WEBSOCKET_MANAGER == 'redis':
            registry_entry = SFU_REGISTRY.get(channel_id)

            # forward leave event to hosting instance
            if registry_entry and registry_entry['instance_id'] != INSTANCE_ID:
                sfu_instance_id = registry_entry['instance_id']
                relay_channel = f'{REDIS_KEY_PREFIX}:sfu:relay:{sfu_instance_id}'
                await REDIS.publish(relay_channel, json.dumps({'event': 'leave', 'sid': sid, 'data': data}))

                return

        await channel_call_sfu_handle_leave(sid, data)


async def _make_channel_emitter(request_info):
    """Event emitter that routes pipeline output to a channel message.

    Translates chat:completion events into channel message:update socket
    emissions, throttled to avoid flooding with per-token updates.
    """
    channel_id = request_info['chat_id'].removeprefix('channel:')
    message_id = request_info['message_id']

    state = {'last_emit_at': 0.0}
    THROTTLE_INTERVAL = 0.15  # ~6 updates/sec

    async def _emit_channel_update(content: str, done: bool = False):
        from open_webui.models.messages import MessageForm, Messages

        update_form = MessageForm(content=content)
        if done:
            # Merge done flag into existing meta (preserve model_id etc.)
            msg = await Messages.get_message_by_id(message_id)
            existing_meta = (msg.meta or {}) if msg else {}
            update_form = MessageForm(
                content=content,
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
            content = data.get('content', '')
            done = data.get('done', False)

            if not content and not done:
                return

            now = __import__('time').time()
            if done or (now - state['last_emit_at']) >= THROTTLE_INTERVAL:
                state['last_emit_at'] = now
                await _emit_channel_update(content, done)

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

        await sio.emit(
            'events',
            {
                'chat_id': chat_id,
                'message_id': message_id,
                'data': event_data,
            },
            room=f'user:{user_id}',
        )

        if update_db and message_id and not (request_info.get('chat_id') or '').startswith('local:'):
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
                    message = await Chats.get_message_by_id_and_message_id(
                        request_info['chat_id'],
                        request_info['message_id'],
                    )
                    embeds.extend(message.get('embeds', []))

                await Chats.upsert_message_to_chat_by_id_and_message_id(
                    request_info['chat_id'],
                    request_info['message_id'],
                    {
                        'embeds': embeds,
                    },
                )

            elif event_type == 'files':
                message = await Chats.get_message_by_id_and_message_id(
                    request_info['chat_id'],
                    request_info['message_id'],
                )

                files = event_data.get('data', {}).get('files', [])
                files.extend(message.get('files', []))

                await Chats.upsert_message_to_chat_by_id_and_message_id(
                    request_info['chat_id'],
                    request_info['message_id'],
                    {
                        'files': files,
                    },
                )

            elif event_type in ('source', 'citation'):
                data = event_data.get('data', {})
                if data.get('type') is None:
                    message = await Chats.get_message_by_id_and_message_id(
                        request_info['chat_id'],
                        request_info['message_id'],
                    )

                    sources = message.get('sources', [])
                    sources.append(data)

                    await Chats.upsert_message_to_chat_by_id_and_message_id(
                        request_info['chat_id'],
                        request_info['message_id'],
                        {
                            'sources': sources,
                        },
                    )

    if 'user_id' in request_info and 'chat_id' in request_info and 'message_id' in request_info:
        return __event_emitter__
    else:
        return None


async def get_event_call(request_info):
    async def __event_caller__(event_data):
        session_id = request_info['session_id']

        # Fast-fail if the client has disconnected.
        if session_id not in SESSION_POOL:
            log.warning(f'Event caller: session {session_id} no longer connected')
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
        except TimeoutError:
            log.warning(f'Event caller timed out for session {session_id}')
            return {'error': 'Event call timed out. The browser tab may be inactive or closed.'}

    if 'session_id' in request_info and 'chat_id' in request_info and 'message_id' in request_info:
        return __event_caller__
    else:
        return None


get_event_caller = get_event_call
