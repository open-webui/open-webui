import socketio

from apps.webui.models.users import Users
from utils.utils import decode_token

sio = socketio.AsyncServer(cors_allowed_origins=[], async_mode="asgi")
app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")

# Dictionary to maintain the user pool
USER_POOL = {}


@sio.event
async def connect(sid, environ, auth):
    print("connect ", sid)

    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

        if user:
            USER_POOL[sid] = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            }
            print(f"user {user.name}({user.id}) connected with session ID {sid}")


@sio.event
def disconnect(sid):
    if sid in USER_POOL:
        disconnected_user = USER_POOL.pop(sid)
        print(f"user {disconnected_user} disconnected with session ID {sid}")
    else:
        print(f"Unknown session ID {sid} disconnected")


@sio.event
def disconnect(sid):
    print("disconnect", sid)
