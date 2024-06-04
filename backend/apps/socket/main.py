import socketio
import asyncio


from apps.webui.models.users import Users
from utils.utils import decode_token

sio = socketio.AsyncServer(cors_allowed_origins=[], async_mode="asgi")
app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")

# Dictionary to maintain the user pool


USER_POOL = {}
USAGE_POOL = {}
# Timeout duration in seconds
TIMEOUT_DURATION = 3


@sio.event
async def connect(sid, environ, auth):
    print("connect ", sid)

    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

        if user:
            USER_POOL[sid] = user.id
            print(f"user {user.name}({user.id}) connected with session ID {sid}")

            print(len(set(USER_POOL)))
            await sio.emit("user-count", {"count": len(set(USER_POOL))})


@sio.on("user-join")
async def user_join(sid, data):
    print("user-join", sid, data)

    auth = data["auth"] if "auth" in data else None

    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

        if user:
            USER_POOL[sid] = user.id
            print(f"user {user.name}({user.id}) connected with session ID {sid}")

            print(len(set(USER_POOL)))
            await sio.emit("user-count", {"count": len(set(USER_POOL))})


@sio.on("user-count")
async def user_count(sid):
    print("user-count", sid)
    await sio.emit("user-count", {"count": len(set(USER_POOL))})


def get_models_in_use():
    # Aggregate all models in use

    models_in_use = []
    for sid, data in USAGE_POOL.items():
        models_in_use.extend(data["models"])
    print(f"Models in use: {models_in_use}")

    return models_in_use


@sio.on("usage")
async def usage(sid, data):
    print(f'Received "usage" event from {sid}: {data}')

    # Cancel previous task if there is one
    if sid in USAGE_POOL:
        USAGE_POOL[sid]["task"].cancel()

    # Store the new usage data and task
    model_id = data["model"]

    if sid in USAGE_POOL and "models" in USAGE_POOL[sid]:

        print(USAGE_POOL[sid])

        models = USAGE_POOL[sid]["models"]
        if model_id not in models:
            models.append(model_id)
            USAGE_POOL[sid] = {"models": models}

    else:
        USAGE_POOL[sid] = {"models": [model_id]}

    # Schedule a task to remove the usage data after TIMEOUT_DURATION
    USAGE_POOL[sid]["task"] = asyncio.create_task(remove_after_timeout(sid, model_id))

    models_in_use = get_models_in_use()
    # Broadcast the usage data to all clients
    await sio.emit("usage", {"models": models_in_use})


async def remove_after_timeout(sid, model_id):
    try:
        await asyncio.sleep(TIMEOUT_DURATION)
        if sid in USAGE_POOL:
            if model_id in USAGE_POOL[sid]["models"]:
                USAGE_POOL[sid]["models"].remove(model_id)
            if len(USAGE_POOL[sid]["models"]) == 0:
                del USAGE_POOL[sid]
            print(f"Removed usage data for {sid} due to timeout")

            models_in_use = get_models_in_use()
            # Broadcast the usage data to all clients
            await sio.emit("usage", {"models": models_in_use})
    except asyncio.CancelledError:
        # Task was cancelled due to new 'usage' event
        pass


@sio.event
async def disconnect(sid):
    if sid in USER_POOL:
        disconnected_user = USER_POOL.pop(sid)
        print(f"user {disconnected_user} disconnected with session ID {sid}")

        await sio.emit("user-count", {"count": len(USER_POOL)})
    else:
        print(f"Unknown session ID {sid} disconnected")
