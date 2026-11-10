"""Template management and context-authorized terminal lifecycle operations."""
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.utils.access_control import validate_access_grants
from open_webui.utils.auth import get_verified_user
from open_webui.utils.terminals import (
    has_connection_write_access, get_connection, server_request, template_terminal_id, template_connection,
    get_terminal_context, find_terminal_connection,
)

router = APIRouter()


class CreateForm(BaseModel):
    id: UUID
    connection_id: str
    data: dict = Field(default_factory=dict)


class ShareForm(BaseModel):
    access_grants: list[dict]


class InstanceForm(BaseModel):
    user_id: str | None = Field(default=None, min_length=1)
    chat_id: str | None = None
    model_id: str | None = None


def path(template_id, suffix=''):
    return f'api/v1/terminals/templates/{quote(template_id, safe="")}{suffix}'


async def changed(user_id, terminal_id, previous=()):
    from open_webui.socket.main import emit_to_users
    current = await AccessGrants.get_grants_by_resource('terminal', terminal_id)
    recipients = {user_id}
    recipients.update(await AccessGrants.get_user_ids_by_access_grants([*previous, *current], 'read'))
    await emit_to_users('events', {'data': {'type': 'terminals:changed'}}, list(recipients))


@router.get('/connections')
async def management_connections(user=Depends(get_verified_user)):
    result = []
    for connection in await Config.get('terminal_server.connections', []) or []:
        if connection.get('server_type') != 'orchestrator' or not connection.get('enabled', True):
            continue
        try:
            await get_connection(user, connection['id'])
        except HTTPException:
            continue
        if await has_connection_write_access(user, connection):
            result.append({'id': connection['id'], 'name': connection.get('name', connection['id'])})
    return result


@router.get('/connections/{connection_id}/status')
async def connection_status(connection_id: str, user=Depends(get_verified_user)):
    connection = await get_connection(user, connection_id)
    if not await has_connection_write_access(user, connection):
        raise HTTPException(403, 'Creation is not allowed')
    return await server_request(connection, 'api/v1/terminals/status')


@router.post('', status_code=201)
async def create_template(body: CreateForm, user=Depends(get_verified_user)):
    connection = await get_connection(user, body.connection_id)
    if not await has_connection_write_access(user, connection):
        raise HTTPException(403, 'Creation is not allowed')
    row = await server_request(connection, 'api/v1/terminals/templates', method='POST',
                               body={'id': str(body.id), 'data': body.data})
    selector = template_terminal_id(connection['id'], row['id'])
    try:
        await AccessGrants.set_access_grants('terminal', selector, [
            {'principal_type': 'user', 'principal_id': user.id, 'permission': 'read'}
        ])
    except Exception:
        await server_request(connection, path(row['id']), method='DELETE')
        raise
    await changed(user.id, selector)
    return {**row, 'terminal_id': selector}


@router.get('/{terminal_id}')
async def get_template(terminal_id: str, user=Depends(get_verified_user)):
    _, template = await template_connection(user, terminal_id, 'write')
    return template


@router.patch('/{terminal_id}')
async def update_template(terminal_id: str, body: dict, user=Depends(get_verified_user)):
    connection, template = await template_connection(user, terminal_id, 'write')
    result = await server_request(connection, path(template['id']), method='PATCH', body=body)
    await changed(user.id, terminal_id)
    return result


@router.delete('/{terminal_id}')
async def delete_template(terminal_id: str, user=Depends(get_verified_user)):
    connection, template = await template_connection(user, terminal_id, 'write')
    previous = await AccessGrants.get_grants_by_resource('terminal', terminal_id)
    result = await server_request(connection, path(template['id']), method='DELETE')
    await AccessGrants.set_access_grants('terminal', terminal_id, [])
    await changed(user.id, terminal_id, previous)
    return result


@router.get('/{terminal_id}/access')
async def get_shares(terminal_id: str, user=Depends(get_verified_user)):
    await template_connection(user, terminal_id, 'write')
    return [grant for grant in await AccessGrants.get_grants_by_resource('terminal', terminal_id)
            if grant.permission == 'read']


@router.post('/{terminal_id}/access')
async def set_shares(terminal_id: str, body: ShareForm, user=Depends(get_verified_user)):
    await template_connection(user, terminal_id, 'write')
    if any(g.get('principal_type') not in ('user', 'group') or g.get('principal_id') in (None, '', '*')
           for g in body.access_grants):
        raise HTTPException(400, 'Public terminal sharing is not allowed')
    grants = await validate_access_grants(await Config.get('user.permissions'), user.id, user.role,
                                           body.access_grants, resource_type='terminal')
    previous = await AccessGrants.get_grants_by_resource('terminal', terminal_id)
    await AccessGrants.set_access_grants('terminal', terminal_id, grants)
    await changed(user.id, terminal_id, previous)
    return {'ok': True}


@router.get('/{terminal_id}/instance')
async def current_instance(terminal_id: str, request: Request, chat_id: str | None = None,
                          model_id: str | None = None, user=Depends(get_verified_user)):
    connection = await find_terminal_connection(user, terminal_id, {'chat_id': chat_id, 'model_id': model_id}, request=request)
    if not connection or not connection.get('template_id'):
        raise HTTPException(404, 'Template not found')
    result = await server_request(connection, path(connection['template_id'], '/instance'),
                                  params={k: v for k, v in connection['terminal_context'].items() if v is not None})
    return result


@router.get('/{terminal_id}/instances')
async def list_instances(terminal_id: str, user=Depends(get_verified_user)):
    from open_webui.models.chats import Chats
    from open_webui.models.models import Models
    from open_webui.models.users import Users

    connection, template = await template_connection(user, terminal_id, 'write')
    rows = await server_request(connection, path(template['id'], '/instances'))
    for row in rows:
        kind, _, value = (row.get('context_id') or '').partition(':')
        row['context'] = {f'{kind}_id': value} if value else {}
        if kind == 'chat':
            chat = await Chats.get_chat_by_id(value)
            owner = await Users.get_user_by_id(chat.user_id) if chat else None
            row['label'] = chat.title if chat else None
            row['user_name'] = owner.name if owner else None
        elif kind == 'user':
            owner = await Users.get_user_by_id(value)
            row['label'] = owner.name if owner else None
        elif kind == 'model':
            model = await Models.get_model_by_id(value)
            row['label'] = model.name if model else value
    return rows


async def instance_action(terminal_id, action, body, user):
    connection, template = await template_connection(user, terminal_id, 'write')
    context = get_terminal_context(template, body.user_id or user.id, body.model_dump(exclude_none=True))
    result = await server_request(connection, path(template['id'], '/instance' if action == 'delete' else '/' + action),
        method='DELETE' if action == 'delete' else 'POST', body=context)
    await changed(user.id, terminal_id)
    return result


@router.post('/{terminal_id}/restart')
async def restart(terminal_id: str, body: InstanceForm, user=Depends(get_verified_user)):
    return await instance_action(terminal_id, 'restart', body, user)


@router.post('/{terminal_id}/stop')
async def stop(terminal_id: str, body: InstanceForm, user=Depends(get_verified_user)):
    return await instance_action(terminal_id, 'stop', body, user)


@router.post('/{terminal_id}/start')
async def start(terminal_id: str, body: InstanceForm, user=Depends(get_verified_user)):
    return await instance_action(terminal_id, 'start', body, user)


@router.post('/{terminal_id}/reset')
async def reset(terminal_id: str, body: InstanceForm, user=Depends(get_verified_user)):
    return await instance_action(terminal_id, 'reset', body, user)


@router.delete('/{terminal_id}/instance')
async def delete_instance(terminal_id: str, body: InstanceForm, user=Depends(get_verified_user)):
    return await instance_action(terminal_id, 'delete', body, user)
