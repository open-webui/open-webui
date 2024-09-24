import asyncio
import socketio
import logging
import sys
import time

from open_webui.apps.webui.models.users import Users
from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_URL,
)
from open_webui.utils.utils import decode_token
from open_webui.apps.socket.utils import RedisDict

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
        transports=(
            ["polling", "websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]
        ),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        client_manager=mgr,
    )
else:
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(
            ["polling", "websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]
        ),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
    )


# Dictionary to maintain the user pool

if WEBSOCKET_MANAGER == "redis":
    SESSION_POOL = RedisDict("open-webui:session_pool", redis_url=WEBSOCKET_REDIS_URL)
    USER_POOL = RedisDict("open-webui:user_pool", redis_url=WEBSOCKET_REDIS_URL)
    USAGE_POOL = RedisDict("open-webui:usage_pool", redis_url=WEBSOCKET_REDIS_URL)
else:
    SESSION_POOL = {}
    USER_POOL = {}
    USAGE_POOL = {}


# Timeout duration in seconds
TIMEOUT_DURATION = 3


async def periodic_usage_pool_cleanup():
    while True:
        now = int(time.time())
        for model_id, connections in list(USAGE_POOL.items()):
            # Creating a list of sids to remove if they have timed out
            expired_sids = [
                sid
                for sid, details in connections.items()
                if now - details["updated_at"] > TIMEOUT_DURATION
            ]

            for sid in expired_sids:
                del connections[sid]

            if not connections:
                log.debug(f"Cleaning up model {model_id} from usage pool")
                del USAGE_POOL[model_id]
            else:
                USAGE_POOL[model_id] = connections

            # Emit updated usage information after cleaning
            await sio.emit("usage", {"models": get_models_in_use()})

        await asyncio.sleep(TIMEOUT_DURATION)


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
    model_id = data["model"]
    # Record the timestamp for the last update
    current_time = int(time.time())

    # Store the new usage data and task
    USAGE_POOL[model_id] = {
        **(USAGE_POOL[model_id] if model_id in USAGE_POOL else {}),
        sid: {"updated_at": current_time},
    }

    # Broadcast the usage data to all clients
    await sio.emit("usage", {"models": get_models_in_use()})


@sio.event
async def connect(sid, environ, auth):
    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

        if user:
            SESSION_POOL[sid] = user.id
            if user.id in USER_POOL:
                USER_POOL[user.id].append(sid)
            else:
                USER_POOL[user.id] = [sid]

            # print(f"user {user.name}({user.id}) connected with session ID {sid}")
            await sio.emit("user-count", {"count": len(USER_POOL.items())})
            await sio.emit("usage", {"models": get_models_in_use()})


@sio.on("user-join")
async def user_join(sid, data):
    # print("user-join", sid, data)

    auth = data["auth"] if "auth" in data else None
    if not auth or "token" not in auth:
        return

    data = decode_token(auth["token"])
    if data is None or "id" not in data:
        return

    user = Users.get_user_by_id(data["id"])
    if not user:
        return

    SESSION_POOL[sid] = user.id
    if user.id in USER_POOL:
        USER_POOL[user.id].append(sid)
    else:
        USER_POOL[user.id] = [sid]

    # print(f"user {user.name}({user.id}) connected with session ID {sid}")

    await sio.emit("user-count", {"count": len(USER_POOL.items())})


@sio.on("user-count")
async def user_count(sid):
    await sio.emit("user-count", {"count": len(USER_POOL.items())})


@sio.event
async def disconnect(sid):
    if sid in SESSION_POOL:
        user_id = SESSION_POOL[sid]
        del SESSION_POOL[sid]

        USER_POOL[user_id] = [_sid for _sid in USER_POOL[user_id] if _sid != sid]

        if len(USER_POOL[user_id]) == 0:
            del USER_POOL[user_id]

        await sio.emit("user-count", {"count": len(USER_POOL)})
    else:
        pass
        # print(f"Unknown session ID {sid} disconnected")


def get_event_emitter(request_info):
    async def __event_emitter__(event_data):
        await sio.emit(
            "chat-events",
            {
                "chat_id": request_info["chat_id"],
                "message_id": request_info["message_id"],
                "data": event_data,
            },
            to=request_info["session_id"],
        )

    return __event_emitter__


def get_event_call(request_info):
    async def __event_call__(event_data):
        response = await sio.call(
            "chat-events",
            {
                "chat_id": request_info["chat_id"],
                "message_id": request_info["message_id"],
                "data": event_data,
            },
            to=request_info["session_id"],
        )
        return response

    return __event_call__
