import asyncio

import socketio
from open_webui.apps.webui.models.users import Users
from open_webui.utils.utils import decode_token

sio = socketio.AsyncServer(cors_allowed_origins=[], async_mode="asgi")
app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")

# Dictionary to maintain the user pool

SESSION_POOL = {}
USER_POOL = {}
USAGE_POOL = {}
# Timeout duration in seconds
TIMEOUT_DURATION = 3


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

            print(f"user {user.name}({user.id}) connected with session ID {sid}")

            await sio.emit("user-count", {"count": len(set(USER_POOL))})
            await sio.emit("usage", {"models": get_models_in_use()})


@sio.on("user-join")
async def user_join(sid, data):
    print("user-join", sid, data)

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

    print(f"user {user.name}({user.id}) connected with session ID {sid}")

    await sio.emit("user-count", {"count": len(set(USER_POOL))})


@sio.on("user-count")
async def user_count(sid):
    await sio.emit("user-count", {"count": len(set(USER_POOL))})


def get_models_in_use():
    # Aggregate all models in use
    models_in_use = []
    for model_id, data in USAGE_POOL.items():
        models_in_use.append(model_id)

    return models_in_use


@sio.on("usage")
async def usage(sid, data):
    model_id = data["model"]

    # Cancel previous callback if there is one
    if model_id in USAGE_POOL:
        USAGE_POOL[model_id]["callback"].cancel()

    # Store the new usage data and task

    if model_id in USAGE_POOL:
        USAGE_POOL[model_id]["sids"].append(sid)
        USAGE_POOL[model_id]["sids"] = list(set(USAGE_POOL[model_id]["sids"]))

    else:
        USAGE_POOL[model_id] = {"sids": [sid]}

    # Schedule a task to remove the usage data after TIMEOUT_DURATION
    USAGE_POOL[model_id]["callback"] = asyncio.create_task(
        remove_after_timeout(sid, model_id)
    )

    # Broadcast the usage data to all clients
    await sio.emit("usage", {"models": get_models_in_use()})


async def remove_after_timeout(sid, model_id):
    try:
        await asyncio.sleep(TIMEOUT_DURATION)
        if model_id in USAGE_POOL:
            print(USAGE_POOL[model_id]["sids"])
            USAGE_POOL[model_id]["sids"].remove(sid)
            USAGE_POOL[model_id]["sids"] = list(set(USAGE_POOL[model_id]["sids"]))

            if len(USAGE_POOL[model_id]["sids"]) == 0:
                del USAGE_POOL[model_id]

            # Broadcast the usage data to all clients
            await sio.emit("usage", {"models": get_models_in_use()})
    except asyncio.CancelledError:
        # Task was cancelled due to new 'usage' event
        pass


@sio.event
async def disconnect(sid):
    if sid in SESSION_POOL:
        user_id = SESSION_POOL[sid]
        del SESSION_POOL[sid]

        USER_POOL[user_id].remove(sid)

        if len(USER_POOL[user_id]) == 0:
            del USER_POOL[user_id]

        await sio.emit("user-count", {"count": len(USER_POOL)})
    else:
        print(f"Unknown session ID {sid} disconnected")


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
