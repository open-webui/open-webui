"""Native external apps: administration, channel participation and authenticated interactions."""

import time
import uuid
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrant, AccessGrants
from open_webui.models.apps import (
    App,
    AppAccessResponse,
    AppChannelMessage,
    AppConnectionForm,
    AppForm,
    AppInteractionForm,
    AppManifestForm,
    AppResponse,
    Apps,
    AppTokenForm,
    AppUpdateForm,
    Manifest,
)
from open_webui.models.channels import Channel, ChannelMember, Channels
from open_webui.models.config import Config
from open_webui.models.messages import Message
from open_webui.models.users import Users
from open_webui.utils.apps import (
    check_app_channel_membership,
    check_app_invocation_access,
    create_app_message,
    decode_app_context_token,
    generate_app_channel_reply,
    get_app_by_id,
    get_app_encryption_cipher,
    get_app_message_data,
    get_app_response,
    get_verified_app,
    has_app_access,
    require_scope,
    send_app_event,
    send_app_request,
    update_app_message,
    validate_app_url,
    verify_app_token,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


############################
# GetApps
############################


@router.get('', response_model=list[AppResponse])
async def get_apps(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    if not await Config.get('apps.enable'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Apps are disabled')
    apps = (await db.scalars(select(App).order_by(App.name))).all()
    return [
        get_app_response(app)
        for app in apps
        if user.role == 'admin' or (app.is_active and await has_app_access(app, user, db=db))
    ]


############################
# PreviewAppManifest
############################


@router.post('/manifest/preview', response_model=Manifest)
async def preview_app_manifest(form_data: AppManifestForm, user=Depends(get_admin_user)):
    if not await Config.get('apps.enable'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Apps are disabled')
    try:
        status_code, raw = await send_app_request(form_data.url)
        if status_code != 200:
            raise ValueError()
        manifest = Manifest.model_validate(raw)
        return manifest.model_dump()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid or unreachable app manifest'
        ) from None


############################
# CreateNewApp
############################


@router.post('', response_model=AppResponse)
async def create_new_app(
    form_data: AppForm, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    if not await Config.get('apps.enable'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Apps are disabled')
    try:
        validate_app_url(form_data.url)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid app URL') from None
    if not set(form_data.granted_scopes) <= set(form_data.manifest.requested_scopes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unrequested scope')
    now = time.time_ns()
    app = App(
        id=str(uuid.uuid4()),
        slug=form_data.slug,
        name=form_data.manifest.name,
        user_id=user.id,
        is_active=False,
        data={
            'url': form_data.url,
            'manifest': form_data.manifest.model_dump(),
            'granted_scopes': form_data.granted_scopes,
            'settings': {},
        },
        api_key=get_app_encryption_cipher().encrypt(form_data.api_key.get_secret_value().encode()).decode(),
        created_at=now,
        updated_at=now,
    )
    db.add(app)
    try:
        await AccessGrants.replace_access_grants(db, 'app', app.id, form_data.access_grants)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='App slug is already registered') from None
    return get_app_response(app)


# Fixed runtime routes must precede /{app_id}.
############################
# GetCurrentApp
############################


@router.get('/runtime/me', response_model=AppResponse)
async def get_current_app(app=Depends(get_verified_app)):
    return get_app_response(app)


############################
# GetAppChannels
############################


@router.get('/runtime/channels')
async def get_app_channels(app=Depends(get_verified_app), db: AsyncSession = Depends(get_async_session)):
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


############################
# AuthorizeAppExecution
############################


@router.post('/runtime/authorize')
async def authorize_app_execution(
    form_data: AppTokenForm, app=Depends(get_verified_app), db: AsyncSession = Depends(get_async_session)
):
    value = decode_app_context_token(app, 'execution', form_data.token)
    user = await Users.get_user_by_id(value['actor_id'], db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Actor is unavailable')
    await check_app_invocation_access(app, value['channel_id'], user, db=db)
    require_scope(app, value['scope'])
    return {
        'authorized': True,
        'operation_id': value['operation_id'],
        'actor': {'id': user.id, 'is_admin': user.role == 'admin'},
        'channel_id': value['channel_id'],
        'type': value.get('type'),
        'data': value.get('data'),
    }


############################
# VerifyAppEvent
############################


@router.post('/runtime/events/verify')
async def verify_app_event(
    form_data: AppTokenForm, app=Depends(get_verified_app), db: AsyncSession = Depends(get_async_session)
):
    value = decode_app_context_token(app, 'event', form_data.token)
    await check_app_channel_membership(app, value['channel']['id'], db=db)
    require_scope(app, 'messages:read')
    return {k: v for k, v in value.items() if k not in ('purpose', 'exp', 'nonce')}


############################
# GetAppChannelMessages
############################


@router.get('/runtime/channels/{channel_id}/messages')
async def get_app_channel_messages(
    channel_id: str,
    before: str | None = None,
    parent_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    app=Depends(get_verified_app),
    db: AsyncSession = Depends(get_async_session),
):
    await check_app_channel_membership(app, channel_id, db=db)
    require_scope(app, 'messages:read')
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


############################
# PostAppMessage
############################


@router.post('/runtime/channels/{channel_id}/messages', status_code=status.HTTP_201_CREATED)
async def post_app_message(
    channel_id: str,
    form_data: AppChannelMessage,
    app=Depends(get_verified_app),
    db: AsyncSession = Depends(get_async_session),
):
    return await create_app_message(db, app, channel_id, form_data)


############################
# UpdateAppMessageById
############################


@router.patch('/runtime/messages/{message_id}')
async def update_app_message_by_id(
    message_id: str,
    form_data: AppChannelMessage,
    if_match: str | None = Header(default=None),
    app=Depends(get_verified_app),
    db: AsyncSession = Depends(get_async_session),
):
    return await update_app_message(db, app, message_id, form_data, if_match)


############################
# GetAppDetailsById
############################


@router.get('/{app_id}', response_model=AppAccessResponse)
async def get_app_details_by_id(
    app_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    result = get_app_response(await get_app_by_id(app_id, db=db))
    result['access_grants'] = [
        {'principal_type': g.principal_type, 'principal_id': g.principal_id, 'permission': g.permission}
        for g in (
            await db.scalars(
                select(AccessGrant).where(AccessGrant.resource_type == 'app', AccessGrant.resource_id == app_id)
            )
        ).all()
    ]
    return result


############################
# UpdateAppById
############################


@router.patch('/{app_id}', response_model=AppResponse)
async def update_app_by_id(
    app_id: str, form_data: AppUpdateForm, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    app = await get_app_by_id(app_id, db=db)
    if form_data.is_active is True:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Connect the app to enable it')
    data = {'updated_at': max(time.time_ns(), app.updated_at + 1)}
    if form_data.is_active is False:
        data['is_active'] = False
    if form_data.name is not None:
        data['name'] = form_data.name
    if form_data.settings is not None:
        data['data'] = {**app.data, 'settings': form_data.settings}
    if form_data.manifest is not None:
        if form_data.manifest.id != app.data['manifest']['id']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='App identity cannot change')
        if form_data.granted_scopes is None or not set(form_data.granted_scopes) <= set(
            form_data.manifest.requested_scopes
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Review the updated scopes')
        data['data'] = {
            **data.get('data', app.data),
            'manifest': form_data.manifest.model_dump(),
            'granted_scopes': form_data.granted_scopes,
        }
        data['is_active'] = False
    elif form_data.granted_scopes is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='An updated manifest is required')
    app = await Apps.update_app_by_id(app_id, data, access_grants=form_data.access_grants, db=db)
    return get_app_response(app)


############################
# ConnectAppById
############################


@router.post('/{app_id}/connect', response_model=AppResponse)
async def connect_app_by_id(
    app_id: str,
    form_data: AppConnectionForm,
    request: Request,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    app = await get_app_by_id(app_id, db=db)
    webui_url = str(request.base_url).rstrip('/')
    try:
        validate_app_url(webui_url)
        origin = urlsplit(webui_url)
        if origin.path or origin.query or origin.fragment:
            raise ValueError()
        host = f'[{origin.hostname}]' if ':' in origin.hostname else origin.hostname.lower()
        port = origin.port or (443 if origin.scheme == 'https' else 80)
        suffix = f':{port}' if port != (443 if origin.scheme == 'https' else 80) else ''
        webui_url = f'{origin.scheme}://{host}{suffix}'
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Connect through your public HTTPS WebUI URL'
        ) from None
    if form_data.api_key is not None:
        app.api_key = get_app_encryption_cipher().encrypt(form_data.api_key.get_secret_value().encode()).decode()
    if not app.api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='An app API key is required')
    app.data = {**app.data, 'webui_url': webui_url}
    app.is_active = False
    app.updated_at = max(time.time_ns(), app.updated_at + 1)
    checked_at, api_key = app.updated_at, app.api_key
    app = await Apps.update_app_by_id(
        app_id, {'api_key': api_key, 'data': app.data, 'is_active': False, 'updated_at': checked_at}, db=db
    )
    await db.commit()
    challenge = str(uuid.uuid4())
    try:
        status_code, value = await send_app_event(
            app,
            {'id': str(uuid.uuid4()), 'type': 'connect', 'data': {'challenge': challenge}},
            timeout=20,
        )
        if status_code != 200 or not isinstance(value, dict):
            raise ValueError()
        claims = verify_app_token(app, value['proof'], 'webui-app-connect+jwt')
        if claims.get('challenge') != challenge:
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Could not connect. Check the app API key and installed public key.',
        ) from None
    result = await db.execute(
        update(App)
        .where(App.id == app_id, App.updated_at == checked_at, App.api_key == api_key)
        .values(is_active=True, updated_at=max(time.time_ns(), checked_at + 1))
    )
    if result.rowcount != 1:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='App changed while connecting; connect again')
    await db.commit()
    return get_app_response(await get_app_by_id(app_id, db=db))


############################
# UninstallAppById
############################


@router.delete('/{app_id}', response_model=AppResponse)
async def uninstall_app_by_id(app_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    app = await get_app_by_id(app_id, db=db)
    app = await Apps.uninstall_app_by_id(app_id, db=db)
    return get_app_response(app)


############################
# CreateAppInteraction
############################


@router.post('/{app_id}/interactions')
async def create_app_interaction(
    app_id: str,
    form_data: AppInteractionForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    app = await get_app_by_id(app_id, require_active=True, db=db)
    message = await db.get(Message, form_data.message_id)
    if not message or message.app_id != app.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='App message not found')
    await check_app_invocation_access(app, message.channel_id, user, db=db)
    actions = (message.data or {}).get('app', {}).get('actions', [])
    action = next((item for item in actions if item['action_id'] == form_data.action_id), None)
    if not action:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unknown action')
    return await generate_app_channel_reply(
        app,
        user,
        message.channel_id,
        'channel.action',
        {'message_id': message.id, 'action_id': form_data.action_id, 'context': action['context']},
        source={'id': message.id, 'updated_at': message.updated_at},
        db=db,
    )


############################
# GetAppOperation
############################


@router.get('/{app_id}/operations/{operation_id}')
async def get_app_operation(
    app_id: str,
    operation_id: str,
    x_openwebui_operation_receipt: str = Header(),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    app = await get_app_by_id(app_id, require_active=True, db=db)
    value = decode_app_context_token(app, 'operation', x_openwebui_operation_receipt)
    if value['actor_id'] != user.id or value['operation_id'] != operation_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid operation receipt')
    await check_app_invocation_access(app, value['channel_id'], user, db=db)
    return await generate_app_channel_reply(
        app,
        user,
        value['channel_id'],
        'channel.operation.status',
        {'operation_id': operation_id},
        operation_id=operation_id,
        db=db,
    )
