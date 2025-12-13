import asyncio
import socketio
import logging
import sys
import time

from open_webui.models.users import Users, UserNameResponse
from open_webui.models.channels import Channels
from open_webui.models.chats import Chats

from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_URL,
)
from open_webui.utils.auth import decode_token
from open_webui.socket.utils import RedisDict, RedisLock

from open_webui.env import (
    GLOBAL_LOG_LEVEL,
    SRC_LOG_LEVELS,
)


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SOCKET"])


if WEBSOCKET_MANAGER == "redis":
    mgr = socketio.AsyncRedisManager(WEBSOCKET_REDIS_URL)
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        client_manager=mgr,
    )
else:
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
    )


# Timeout duration in seconds
TIMEOUT_DURATION = 3

# Dictionary to maintain the user pool

if WEBSOCKET_MANAGER == "redis":
    log.debug("Using Redis to manage websockets.")
    # Set TTL for session/usage pools to prevent memory growth (1 hour default)
    # TTL is set per hash, not per field (faster, less granular)
    # Use master for writes (SESSION_POOL, USER_POOL, USAGE_POOL all need writes)
    SESSION_POOL = RedisDict("open-webui:session_pool", redis_url=WEBSOCKET_REDIS_URL, default_ttl=3600, use_master=True)
    USER_POOL = RedisDict("open-webui:user_pool", redis_url=WEBSOCKET_REDIS_URL, default_ttl=3600, use_master=True)
    USAGE_POOL = RedisDict("open-webui:usage_pool", redis_url=WEBSOCKET_REDIS_URL, default_ttl=1800, use_master=True)  # 30 min for usage

    clean_up_lock = RedisLock(
        redis_url=WEBSOCKET_REDIS_URL,
        lock_name="usage_cleanup_lock",
        timeout_secs=TIMEOUT_DURATION * 2,
    )
    aquire_func = clean_up_lock.aquire_lock
    renew_func = clean_up_lock.renew_lock
    release_func = clean_up_lock.release_lock
else:
    SESSION_POOL = {}
    USER_POOL = {}
    USAGE_POOL = {}
    aquire_func = release_func = renew_func = lambda: True


async def periodic_usage_pool_cleanup():
    if not aquire_func():
        log.debug("Usage pool cleanup lock already exists. Not running it.")
        return
    log.debug("Running periodic_usage_pool_cleanup")
    
    consecutive_renewal_failures = 0
    max_renewal_failures = 3  # Allow some transient failures before giving up
    
    try:
        while True:
            if not renew_func():
                consecutive_renewal_failures += 1
                log.warning(
                    f"Unable to renew cleanup lock (failure #{consecutive_renewal_failures}). "
                    f"Lock may have expired or Redis is unavailable."
                )
                
                # If we've had multiple consecutive failures, exit gracefully
                if consecutive_renewal_failures >= max_renewal_failures:
                    log.error(
                        f"Too many consecutive lock renewal failures ({consecutive_renewal_failures}). "
                        "Exiting usage pool cleanup. Another instance may take over."
                    )
                    break  # Exit gracefully instead of raising exception
                
                # For transient failures, wait a bit and try again before next iteration
                await asyncio.sleep(1)
                continue
            
            # Reset failure counter on successful renewal
            consecutive_renewal_failures = 0

            now = int(time.time())
            send_usage = False
            try:
                for model_id, connections in list(USAGE_POOL.items()):
                    # Ensure connections is a dict
                    if not isinstance(connections, dict):
                        log.warning(f"USAGE_POOL[{model_id}] is not a dict, resetting. Value: {connections}")
                        try:
                            del USAGE_POOL[model_id]
                        except KeyError:
                            pass  # Already deleted by another replica
                        continue
                    
                    # Creating a list of sids to remove if they have timed out
                    expired_sids = [
                        sid
                        for sid, details in connections.items()
                        if isinstance(details, dict) and now - details.get("updated_at", 0) > TIMEOUT_DURATION
                    ]

                    if expired_sids:
                        # Use truly atomic Lua script for batch field removal (single round trip)
                        if isinstance(USAGE_POOL, RedisDict):
                            result = USAGE_POOL.atomic_remove_dict_fields(model_id, expired_sids)
                            if result is None:
                                log.debug(f"Cleaning up model {model_id} from usage pool (now empty)")
                        else:
                            # Fallback for regular dict (single-pod mode, no Redis)
                            for expired_sid in expired_sids:
                                if expired_sid in connections:
                                    del connections[expired_sid]
                            if not connections:
                                log.debug(f"Cleaning up model {model_id} from usage pool")
                                del USAGE_POOL[model_id]
                            else:
                                USAGE_POOL[model_id] = connections
                        send_usage = True

                if send_usage:
                    # Emit updated usage information after cleaning
                    await sio.emit("usage", {"models": get_models_in_use()})
            except Exception as e:
                log.error(f"Error in usage pool cleanup iteration: {e}", exc_info=True)

            await asyncio.sleep(TIMEOUT_DURATION)
    except Exception as e:
        log.error(f"Fatal error in periodic_usage_pool_cleanup: {e}", exc_info=True)
    finally:
        release_func()
        log.debug("periodic_usage_pool_cleanup exited and released lock")


app = socketio.ASGIApp(
    sio,
    socketio_path="/ws/socket.io",
)


def get_models_in_use():
    # List models that are currently in use
    models_in_use = list(USAGE_POOL.keys())
    return models_in_use


@sio.on("usage")
async def usage(sid, data):
    try:
        model_id = data["model"]
        # Record the timestamp for the last update
        current_time = int(time.time())

        # Use truly atomic Lua script for single-round-trip update (prevents race conditions)
        if isinstance(USAGE_POOL, RedisDict):
            USAGE_POOL.atomic_set_dict_field(model_id, sid, {"updated_at": current_time})
        else:
            # Fallback for regular dict (single-pod mode, no Redis)
            existing_usage = USAGE_POOL.get(model_id, {})
            if not isinstance(existing_usage, dict):
                existing_usage = {}
            existing_usage[sid] = {"updated_at": current_time}
            USAGE_POOL[model_id] = existing_usage

        # Broadcast the usage data to all clients
        await sio.emit("usage", {"models": get_models_in_use()})
    except Exception as e:
        log.error(f"Error in usage handler for session {sid}: {e}", exc_info=True)


@sio.event
async def connect(sid, environ, auth):
    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

        if user:
            try:
                SESSION_POOL[sid] = user.model_dump()
                # Atomic append to prevent race conditions (fast single round trip)
                # Fallback to regular dict operations if RedisDict not available
                if isinstance(USER_POOL, RedisDict):
                    USER_POOL.atomic_append_to_list(user.id, sid)
                else:
                    # Fallback for regular dict (single-pod mode, no Redis)
                    existing_sessions = USER_POOL.get(user.id, [])
                    if not isinstance(existing_sessions, list):
                        existing_sessions = []
                    USER_POOL[user.id] = existing_sessions + [sid]

                # print(f"user {user.name}({user.id}) connected with session ID {sid}")
                await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})
                await sio.emit("usage", {"models": get_models_in_use()})
            except Exception as e:
                log.error(f"Error in connect handler for user {user.id}: {e}", exc_info=True)


@sio.on("user-join")
async def user_join(sid, data):

    auth = data["auth"] if "auth" in data else None
    if not auth or "token" not in auth:
        return

    data = decode_token(auth["token"])
    if data is None or "id" not in data:
        return

    user = Users.get_user_by_id(data["id"])
    if not user:
        return

    try:
        SESSION_POOL[sid] = user.model_dump()
        # Atomic append to prevent race conditions (fast single round trip)
        # Fallback to regular dict operations if RedisDict not available
        if isinstance(USER_POOL, RedisDict):
            USER_POOL.atomic_append_to_list(user.id, sid)
        else:
            # Fallback for regular dict (single-pod mode, no Redis)
            existing_sessions = USER_POOL.get(user.id, [])
            if not isinstance(existing_sessions, list):
                existing_sessions = []
            USER_POOL[user.id] = existing_sessions + [sid]

        # Join all the channels
        channels = Channels.get_channels_by_user_id(user.id)
        log.debug(f"{channels=}")
        for channel in channels:
            await sio.enter_room(sid, f"channel:{channel.id}")

        # print(f"user {user.name}({user.id}) connected with session ID {sid}")

        await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})
        return {"id": user.id, "name": user.name}
    except Exception as e:
        log.error(f"Error in user_join handler for user {user.id}: {e}", exc_info=True)
        return None


@sio.on("join-channels")
async def join_channel(sid, data):
    auth = data["auth"] if "auth" in data else None
    if not auth or "token" not in auth:
        return

    data = decode_token(auth["token"])
    if data is None or "id" not in data:
        return

    user = Users.get_user_by_id(data["id"])
    if not user:
        return

    # Join all the channels
    channels = Channels.get_channels_by_user_id(user.id)
    log.debug(f"{channels=}")
    for channel in channels:
        await sio.enter_room(sid, f"channel:{channel.id}")


@sio.on("channel-events")
async def channel_events(sid, data):
    room = f"channel:{data['channel_id']}"
    participants = sio.manager.get_participants(
        namespace="/",
        room=room,
    )

    sids = [sid for sid, _ in participants]
    if sid not in sids:
        return

    event_data = data["data"]
    event_type = event_data["type"]

    if event_type == "typing":
        # Safely get user from session pool
        user_data = SESSION_POOL.get(sid)
        if not user_data:
            log.warning(f"Session {sid} not found in SESSION_POOL for channel-events")
            return
        
        await sio.emit(
            "channel-events",
            {
                "channel_id": data["channel_id"],
                "message_id": data.get("message_id", None),
                "data": event_data,
                "user": UserNameResponse(**user_data).model_dump(),
            },
            room=room,
        )


@sio.on("user-list")
async def user_list(sid):
    await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})


@sio.event
async def disconnect(sid):
    try:
        if sid in SESSION_POOL:
            user = SESSION_POOL[sid]
            del SESSION_POOL[sid]

            user_id = user["id"]
            # Use truly atomic Lua script for list item removal (single round trip)
            if isinstance(USER_POOL, RedisDict):
                USER_POOL.atomic_remove_from_list(user_id, sid)
                # Note: atomic_remove_from_list handles key deletion if list becomes empty
            else:
                # Fallback for regular dict (single-pod mode, no Redis)
                existing_sessions = USER_POOL.get(user_id, [])
                if not isinstance(existing_sessions, list):
                    existing_sessions = []
                filtered_sessions = [_sid for _sid in existing_sessions if _sid != sid]
                if len(filtered_sessions) == 0:
                    if user_id in USER_POOL:
                        del USER_POOL[user_id]
                else:
                    USER_POOL[user_id] = filtered_sessions

            await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})
        else:
            pass
            # print(f"Unknown session ID {sid} disconnected")
    except Exception as e:
        log.error(f"Error in disconnect handler for session {sid}: {e}", exc_info=True)


def get_event_emitter(request_info):
    async def __event_emitter__(event_data):
        user_id = request_info["user_id"]
        session_ids = list(
            set(USER_POOL.get(user_id, []) + [request_info["session_id"]])
        )

        for session_id in session_ids:
            await sio.emit(
                "chat-events",
                {
                    "chat_id": request_info.get("chat_id", None),
                    "message_id": request_info.get("message_id", None),
                    "data": event_data,
                },
                to=session_id,
            )

        if "type" in event_data and event_data["type"] == "status":
            Chats.add_message_status_to_chat_by_id_and_message_id(
                request_info["chat_id"],
                request_info["message_id"],
                event_data.get("data", {}),
            )

        if "type" in event_data and event_data["type"] == "message":
            message = Chats.get_message_by_id_and_message_id(
                request_info["chat_id"],
                request_info["message_id"],
            )

            content = message.get("content", "")
            content += event_data.get("data", {}).get("content", "")

            Chats.upsert_message_to_chat_by_id_and_message_id(
                request_info["chat_id"],
                request_info["message_id"],
                {
                    "content": content,
                },
            )

        if "type" in event_data and event_data["type"] == "replace":
            content = event_data.get("data", {}).get("content", "")

            Chats.upsert_message_to_chat_by_id_and_message_id(
                request_info["chat_id"],
                request_info["message_id"],
                {
                    "content": content,
                },
            )

    return __event_emitter__


def get_event_call(request_info):
    async def __event_caller__(event_data):
        response = await sio.call(
            "chat-events",
            {
                "chat_id": request_info.get("chat_id", None),
                "message_id": request_info.get("message_id", None),
                "data": event_data,
            },
            to=request_info["session_id"],
        )
        return response

    return __event_caller__


get_event_caller = get_event_call


def get_user_id_from_session_pool(sid):
    user = SESSION_POOL.get(sid)
    if user:
        return user["id"]
    return None


def get_user_ids_from_room(room):
    active_session_ids = sio.manager.get_participants(
        namespace="/",
        room=room,
    )

    active_user_ids = list(
        set(
            [
                user_data["id"]
                for session_id in active_session_ids
                if (user_data := SESSION_POOL.get(session_id[0])) is not None
            ]
        )
    )
    return active_user_ids


def get_active_status_by_user_id(user_id):
    if user_id in USER_POOL:
        return True
    return False
