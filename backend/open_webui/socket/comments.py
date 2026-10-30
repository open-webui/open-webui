"""Small, authorized subscriptions on the existing Socket.IO server."""

import hashlib

from fastapi import HTTPException
from open_webui.internal.db import get_async_db_context
from open_webui.models.users import Users
from open_webui.utils.comments import comment_resource
from starlette.requests import HTTPConnection


def comment_room(resource_type, resource_id):
    return 'comments:' + hashlib.sha256(f'{resource_type}:{resource_id}'.encode()).hexdigest()


def comment_connection(sio, sid):
    scope = (sio.get_environ(sid) or {}).get('asgi.scope') or {}
    return HTTPConnection(scope) if scope.get('app') else None


def register_comment_events(sio, get_socket_session_user):
    @sio.on('comments:join')
    async def join(sid, data):
        session_user = await get_socket_session_user(sid)
        if not session_user or not isinstance(data, dict):
            return {'error': 'Unauthorized'}
        kind, id = data.get('resource_type'), data.get('resource_id')
        if not isinstance(kind, str) or not isinstance(id, str) or len(id) > 512:
            return {'error': 'Invalid resource'}
        user = await Users.get_user_by_id(session_user['id'])
        if not user:
            return {'error': 'Unauthorized'}
        try:
            async with get_async_db_context() as db:
                await comment_resource(kind, id, user, db, request=comment_connection(sio, sid))
        except HTTPException:
            return {'error': 'Resource unavailable'}
        session = await sio.get_session(sid)
        previous = session.get('comments_resource')
        if previous:
            await sio.leave_room(sid, comment_room(*previous))
        session['comments_resource'] = [kind, id]
        await sio.save_session(sid, session)
        await sio.enter_room(sid, comment_room(kind, id))
        return {'ok': True}

    @sio.on('comments:leave')
    async def leave(sid, data=None):
        session = await sio.get_session(sid)
        resource = session.pop('comments_resource', None)
        if resource:
            await sio.leave_room(sid, comment_room(*resource))
            await sio.save_session(sid, session)


async def revalidate_comment_subscription(sio, sid, session_user):
    session = await sio.get_session(sid)
    resource = session.get('comments_resource')
    if not resource:
        return
    user = await Users.get_user_by_id(session_user['id'])
    try:
        if not user:
            raise HTTPException(403)
        async with get_async_db_context() as db:
            await comment_resource(*resource, user, db, request=comment_connection(sio, sid))
    except HTTPException:
        await sio.leave_room(sid, comment_room(*resource))
        session.pop('comments_resource', None)
        await sio.save_session(sid, session)
        await sio.emit('comments:unavailable', {}, to=sid)
