"""Native external apps: administration, channel participation and authenticated interactions."""

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrant, AccessGrants
from open_webui.models.apps import (
    App,
    AppAccessResponse,
    AppConnectionForm,
    AppForm,
    AppInteractionForm,
    AppManifestForm,
    AppResponse,
    Apps,
    AppUpdateForm,
    Manifest,
)
from open_webui.models.config import Config
from open_webui.models.messages import Message
from open_webui.utils.apps import (
    check_app_invocation_access,
    generate_app_channel_reply,
    get_app_by_id,
    get_app_encryption_cipher,
    get_app_response,
    has_app_access,
    send_app_request,
    validate_app_url,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from sqlalchemy import select
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
    from open_webui.socket.apps import connections

    return [
        {**get_app_response(app), 'connection_status': await connections.status(app)}
        for app in apps
        if user.role == 'admin' or (app.is_active and await has_app_access(app, user, db=db))
    ]


############################
# PreviewAppManifest
############################


@router.post('/manifest/preview', response_model=Manifest)
async def preview_app_manifest(
    form_data: AppManifestForm, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    if not await Config.get('apps.enable'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Apps are disabled')
    api_key = form_data.api_key.get_secret_value() if form_data.api_key is not None else None
    if form_data.app_id:
        app = await get_app_by_id(form_data.app_id, db=db)
        if form_data.url != app.data['url']:
            raise HTTPException(400, 'App URL does not match the installed app')
        if api_key is None and app.api_key:
            api_key = get_app_encryption_cipher().decrypt(app.api_key.encode()).decode()
    if not api_key:
        raise HTTPException(400, 'An app API key is required')
    try:
        status_code, raw = await send_app_request(form_data.url, headers={'Authorization': f'Bearer {api_key}'})
        if status_code in (401, 403):
            raise HTTPException(400, 'App rejected the API key. Check the API key configured on the app server.')
        if status_code != 200:
            raise HTTPException(
                502, f'App manifest endpoint returned HTTP {status_code}. Check the URL or enter details manually.'
            )
        manifest = Manifest.model_validate(raw)
        return manifest.model_dump()
    except HTTPException:
        raise
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='App returned an invalid manifest. Check its app details or enter them manually.',
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


############################
# GetAppDetailsById
############################


@router.get('/{app_id}', response_model=AppAccessResponse)
async def get_app_details_by_id(
    app_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    from open_webui.socket.apps import connections

    app = await get_app_by_id(app_id, db=db)
    result = {**get_app_response(app), 'connection_status': await connections.status(app)}
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
        if form_data.manifest.public_key != app.data['manifest']['public_key']:
            data['data'].pop('connection_token', None)
            data['data'].pop('installation_id', None)
        data['is_active'] = False
    elif form_data.granted_scopes is not None:
        if not set(form_data.granted_scopes) <= set(app.data['manifest']['requested_scopes']):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unrequested scope')
        data['data'] = {**data.get('data', app.data), 'granted_scopes': form_data.granted_scopes}
    app = await Apps.update_app_by_id(app_id, data, access_grants=form_data.access_grants, db=db)
    return get_app_response(app)


############################
# ConnectAppById
############################


@router.post('/{app_id}/connect', response_model=AppResponse)
async def connect_app_by_id(
    app_id: str,
    form_data: AppConnectionForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    app = await get_app_by_id(app_id, db=db)
    from open_webui.socket.apps import connections

    if form_data.api_key is not None:
        cipher = get_app_encryption_cipher()
        value = form_data.api_key.get_secret_value()
        old = cipher.decrypt(app.api_key.encode()).decode() if app.api_key else None
        if value != old:
            app.data = {k: v for k, v in app.data.items() if k not in ('connection_token', 'installation_id')}
            app.api_key = cipher.encrypt(value.encode()).decode()
    if not app.api_key:
        raise HTTPException(400, 'An app API key is required')
    app = await Apps.update_app_by_id(
        app_id,
        {
            'api_key': app.api_key,
            'data': app.data,
            'is_active': False,
            'updated_at': max(time.time_ns(), app.updated_at + 1),
        },
        db=db,
    )
    app = await connections.connect(app)
    return {**get_app_response(app), 'connection_status': 'connected'}


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
        {
            'message_id': message.id,
            'etag': str(message.updated_at),
            'parent_id': message.parent_id,
            'action_id': form_data.action_id,
            'context': action['context'],
        },
        source={'id': message.id, 'updated_at': message.updated_at},
        db=db,
    )
