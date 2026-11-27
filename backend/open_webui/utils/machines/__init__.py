"""Shared routing helpers for admin-configured terminal servers."""

import asyncio
import hashlib
import logging
import ntpath
import posixpath
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from uuid import uuid4

import aiohttp

from fastapi import HTTPException

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT_MACHINE, ENABLE_TOOL_SERVERS
from open_webui.utils.headers import bearer_auth_header
from open_webui.utils.chat_id import (
    FOLDER_SESSION_ID_PREFIX,
    folder_session_id,
    get_folder_id_of_session,
    is_saved_chat_id,
)
from open_webui.utils.skill_files import (
    SKILL_CONTENT_MAX_CHARS,
    bounded_skill_manifest,
    format_skill_content,
    skill_content_page,
    skill_overview,
)


# Machines were called terminals, and saved data and older clients can still use the old names.
# Write the new names and read both: machine_id/machineId (terminal_id/terminalId), owned_by and skill
# source 'machine' ('terminal'), 'machine:' skill and tool ids ('terminal:'), automation data.machine
# (data.terminal) and the 'machine' access grant type ('terminal'; stored rows are migrated).
LEGACY_KEYS = {'machine_id': 'terminal_id', 'machineId': 'terminalId'}
MACHINE = 'machine'
LEGACY_MACHINE = 'terminal'
MACHINE_PREFIX = 'machine:'
LEGACY_MACHINE_PREFIX = 'terminal:'


def machine_id_of(data, key: str = 'machine_id'):
    """The machine id in a dict, under its current or former key. A present current key wins, even when empty."""
    if not isinstance(data, dict):
        return None
    return (data[key] if key in data else data.get(LEGACY_KEYS[key])) or None


def normalize_machine_id(data, key: str = 'machine_id'):
    """Move a former `terminal_id` onto `machine_id`, in place, and return the dict."""
    if isinstance(data, dict) and LEGACY_KEYS[key] in data:
        legacy = data.pop(LEGACY_KEYS[key])
        data.setdefault(key, legacy)
    return data


def is_machine(value) -> bool:
    """For owned_by, skill source and access grant type values."""
    return value in (MACHINE, LEGACY_MACHINE)


def normalize_machine_type(value):
    return MACHINE if value == LEGACY_MACHINE else value


def is_machine_ref(value) -> bool:
    """A 'machine:' (or former 'terminal:') skill or tool id."""
    return isinstance(value, str) and value.startswith((MACHINE_PREFIX, LEGACY_MACHINE_PREFIX))


def strip_machine_prefix(value: str) -> str:
    for prefix in (MACHINE_PREFIX, LEGACY_MACHINE_PREFIX):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def automation_machine_of(data) -> dict:
    """An automation's machine settings, stored under `machine` (formerly `terminal`)."""
    if not isinstance(data, dict):
        return {}
    return data.get('machine') or data.get('terminal') or {}


MACHINE_CHAT_UPLOAD_MODES = {'default', 'filesystem'}
MAX_AGENTS_MD_BYTES = 32 * 1024

log = logging.getLogger(__name__)

# Machines Open WebUI installed Open Terminal on itself (see managed.py).
MANAGED_SCHEMES = ('ssh://', 'local://')


class MachineError(Exception):
    pass


def get_machine_client(url, user_id=None, service='open_terminal', **kwargs):
    """Return an aiohttp-like client for any machine URL.

    tether:// goes through the user's device relay, ssh:// through the machine's SSH tunnel,
    local:// to Open Terminal on this computer, anything else is a plain aiohttp session.
    Callers use `await`/`async with` the same way.
    """
    if str(url).startswith('tether://'):
        from open_webui.utils.tether import RelayClient

        return RelayClient(user_id, service=service, timeout=kwargs.get('timeout'))
    if str(url).startswith(MANAGED_SCHEMES):
        from open_webui.utils.machines.managed import MachineClient

        return MachineClient(urlsplit(str(url)).hostname, **kwargs)
    return aiohttp.ClientSession(**kwargs)


async def notify_machines_changed(user_ids) -> None:
    """Tell these users' open pages that their machines changed."""
    from open_webui.socket.main import emit_to_users

    await emit_to_users('events', {'data': {'type': 'machines:changed'}}, list(user_ids))


def is_terminal_orchestrator(connection: dict) -> bool:
    return connection.get('server_type') == 'orchestrator'


def get_machine_url(connection: dict) -> str:
    return str(connection.get('url') or '').rstrip('/')


def machine_chat_uploads(connection: dict) -> str:
    """Return normalized main-chat upload behavior for this connection."""
    value = (connection.get('config') or {}).get('chat_uploads')
    return value if value in MACHINE_CHAT_UPLOAD_MODES else 'default'


async def server_request(connection, path, *, method='GET', body=None, params=None):
    if not connection.get('key'):
        raise HTTPException(503, 'A Terminals server key is required')
    url = connection['url'].rstrip('/') + '/' + path.lstrip('/')
    try:
        async with aiohttp.ClientSession(trust_env=True, timeout=aiohttp.ClientTimeout(total=180)) as session:
            async with session.request(
                method,
                url,
                headers=bearer_auth_header(connection['key']),
                json=body,
                params=params,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                allow_redirects=False,
            ) as response:
                if response.status >= 300:
                    try:
                        detail = (await response.json()).get('detail', 'Terminals request failed')
                    except Exception:
                        detail = 'Terminals request failed'
                    raise HTTPException(response.status if response.status >= 400 else 502, detail)
                return await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        raise HTTPException(503, 'Terminals is unavailable')


async def get_connection(user, connection_id):
    from open_webui.models.config import Config
    from open_webui.utils.access_control import has_connection_access

    if not ENABLE_TOOL_SERVERS:
        raise HTTPException(403, 'Tool servers are disabled')
    connections = await Config.get('machines.connections', []) or []
    connection = next((c for c in connections if c.get('id') == connection_id), None)
    if not connection or not connection.get('enabled', True) or connection.get('server_type') != 'orchestrator':
        raise HTTPException(404, 'Managed machine connection not found')
    if not await has_connection_access(user, connection) and not await has_connection_write_access(user, connection):
        raise HTTPException(403, 'Machine connection access denied')
    return connection


async def has_connection_write_access(user, connection, user_group_ids=None):
    from open_webui.models.groups import Groups
    from open_webui.utils.access_control import has_access

    from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL

    if user.role == 'admin' and (
        BYPASS_ADMIN_ACCESS_CONTROL or not (connection.get('config') or {}).get('access_grants')
    ):
        return True
    if user_group_ids is None:
        user_group_ids = {g.id for g in await Groups.get_groups_by_member_id(user.id, include_inherited=True)}
    return await has_access(user.id, 'write', (connection.get('config') or {}).get('access_grants', []), user_group_ids)


def template_machine_id(connection_id, template_id):
    return f'template:{connection_id}:{quote(template_id, safe="")}'


async def has_machine_write_access(user, machine_id):
    """Write access to a terminal's connection, the right that lists, restarts and deletes its instances."""
    if not machine_id.startswith('template:'):
        return False
    connection_id, _ = split_template_id(machine_id)
    return await has_connection_write_access(user, await get_connection(user, connection_id))


async def has_machine_access(principal_type: str, principal_id: str, machine_id: str, owner_id: str) -> bool:
    """Whether a user, or every member of a group through the group itself, can use the machine."""
    from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
    from open_webui.models.access_grants import AccessGrants
    from open_webui.models.config import Config
    from open_webui.models.groups import Groups
    from open_webui.models.users import Users
    from open_webui.utils.access_control import has_access

    # A personal machine is only ever its owner's.
    if machine_id.startswith('tether:'):
        return principal_type == 'user' and principal_id == owner_id

    is_admin = False
    if principal_type == 'user':
        target = await Users.get_user_by_id(principal_id)
        if not target:
            return False
        if target.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
            return True
        is_admin = target.role == 'admin'
        user_id = target.id
        group_ids = {group.id for group in await Groups.get_groups_by_member_id(target.id, include_inherited=True)}
    else:
        user_id, group_ids = '', {principal_id}

    template = machine_id.startswith('template:')
    connection_id = split_template_id(machine_id)[0] if template else machine_id
    connections = await Config.get('machines.connections', []) or []
    connection = next((c for c in connections if c.get('id') == connection_id and c.get('enabled', True)), None)
    if not connection:
        return False
    grants = (connection.get('config') or {}).get('access_grants', [])
    # Connections without grants are admin-only, as in has_connection_access.
    if not grants:
        return is_admin
    if not template:
        return await has_access(user_id, 'read', grants, group_ids)
    if await has_access(user_id, 'write', grants, group_ids):
        return True
    if not await has_access(user_id, 'read', grants, group_ids):
        return False
    return machine_id in await AccessGrants.get_accessible_resource_ids(
        user_id=user_id, resource_type='machine', resource_ids=[machine_id], user_group_ids=group_ids
    )


def split_template_id(machine_id):
    if not machine_id.startswith('template:'):
        raise HTTPException(400, 'Invalid template machine ID')
    connection_id, separator, encoded = machine_id.removeprefix('template:').rpartition(':')
    template_id = unquote(encoded)
    if (
        not separator
        or not connection_id
        or not template_id
        or template_machine_id(connection_id, template_id) != machine_id
    ):
        raise HTTPException(400, 'Invalid template machine ID')
    return connection_id, template_id


async def require_machine_access(user, machine_id):
    from open_webui.models.access_grants import AccessGrants
    from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL

    if user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
        return
    if await AccessGrants.has_access(user.id, 'machine', machine_id, 'read'):
        return
    raise HTTPException(403, 'Machine access denied')


async def template_connection(user, machine_id, permission='read'):
    connection_id, template_id = split_template_id(machine_id)
    connection = await get_connection(user, connection_id)
    if not await has_connection_write_access(user, connection):
        if permission == 'write':
            raise HTTPException(403, 'Machine connection write access required')
        await require_machine_access(user, machine_id)
    template = await server_request(connection, f'api/v1/terminals/templates/{quote(template_id, safe="")}')
    return connection, template


async def list_template_connections(user, connections):
    from open_webui.models.access_grants import AccessGrants
    from open_webui.models.groups import Groups
    from open_webui.models.users import UserModel
    from open_webui.utils.access_control import has_connection_access

    if not isinstance(user, UserModel):
        user = UserModel(**user)
    group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id, include_inherited=True)}
    result = []
    for connection in connections:
        if connection.get('server_type') != 'orchestrator' or not connection.get('enabled', True):
            continue
        writable = await has_connection_write_access(user, connection, group_ids)
        if not writable and not await has_connection_access(user, connection, group_ids):
            continue
        try:
            templates = await server_request(connection, 'api/v1/terminals/templates')
        except HTTPException as exc:
            log.warning('Cannot list templates for connection %s: HTTP %s', connection['id'], exc.status_code)
            continue
        selectors = [template_machine_id(connection['id'], template['id']) for template in templates]
        readable = (
            set(selectors)
            if writable
            else await AccessGrants.get_accessible_resource_ids(
                user_id=user.id,
                resource_type='machine',
                resource_ids=selectors,
                permission='read',
                user_group_ids=group_ids,
            )
        )
        for template, selector in zip(templates, selectors):
            if selector not in readable:
                continue
            data = template.get('data') or {}
            result.append(
                {
                    **connection,
                    'id': selector,
                    'name': data.get('name') or template['id'],
                    'template_id': template['id'],
                    'scope': data.get('scope'),
                    'auth_type': 'bearer',
                }
            )
    return result


class MissingMachineContext(HTTPException):
    def __init__(self, scope):
        detail = 'This machine requires a saved chat' if scope == 'chat' else f'This machine requires a {scope}'
        super().__init__(409, detail)


def get_machine_context(template, user_id, metadata=None):
    """Validate a template's scope and return context for its environment."""
    metadata = metadata or {}
    scope = (template.get('data') or {}).get('scope')
    if scope not in (None, 'user', 'chat', 'model'):
        raise HTTPException(422, 'Invalid template scope')
    chat_id = metadata.get('chat_id')
    model_id = metadata.get('model_id') or metadata.get('model')
    if scope == 'chat' and not is_saved_chat_id(chat_id):
        raise MissingMachineContext(scope)
    if scope == 'model' and not model_id:
        raise MissingMachineContext(scope)
    return {
        'user_id': user_id,
        'chat_id': chat_id if is_saved_chat_id(chat_id) else None,
        'model_id': model_id if scope == 'model' else None,
    }


async def require_model_access(user, model_id, machine_id, request=None):
    if not model_id:
        raise MissingMachineContext('model')
    if model_id.startswith('agent:'):
        parts = model_id.split(':', 3)
        if len(parts) != 4 or unquote(parts[1]) != machine_id or not all(parts[1:]):
            raise HTTPException(403, 'Agent model does not belong to this machine')
        # Agent access follows its machine. Execution still validates the live agent catalog.
        return
    from open_webui.models.models import Models
    from open_webui.utils.models import check_model_access, get_all_models, get_filtered_models

    if request is not None:
        models = await get_all_models(request, user=user)
        permitted = await get_filtered_models(models, user)
        if not any(model['id'] == model_id for model in permitted):
            raise HTTPException(403, 'Model access denied')
    else:
        row = await Models.get_model_by_id(model_id)
        if row is None:
            raise HTTPException(403, 'Model not found')
        try:
            await check_model_access(user, {'id': model_id}, row)
        except Exception as exc:
            raise HTTPException(403, 'Model access denied') from exc


def machine_headers(connection):
    """Only consumes context produced by find_machine_connection, never browser headers."""
    headers = {}
    if connection.get('workspace'):
        headers['X-Workspace-Id'] = connection['workspace']['id']
        if connection['workspace'].get('directory'):
            headers['X-Workspace-Directory'] = quote(connection['workspace']['directory'])
    if not connection.get('template_id'):
        if connection.get('instance_user_id'):
            headers['X-User-Id'] = connection['instance_user_id']
        return headers
    context = connection['machine_context']
    headers |= {
        'X-Terminal-Template-Id': connection['template_id'],
        'X-User-Id': context['user_id'],
    }
    if context.get('chat_id'):
        headers['X-Terminal-Chat-Id'] = context['chat_id']
    if context.get('model_id'):
        headers['X-Terminal-Model-Id'] = context['model_id']
    return headers


async def find_machine_connection(user, machine_id, metadata=None, request=None):
    from open_webui.models.chats import Chats
    from open_webui.models.users import UserModel, Users
    from open_webui.utils.access_control import has_connection_access
    from open_webui.utils.tether import get_machine_connections

    if not ENABLE_TOOL_SERVERS:
        raise HTTPException(403, 'Tool servers are disabled')
    if not isinstance(user, UserModel):
        user = UserModel(**user)
    metadata = dict(metadata or {})

    async def find_instance_user_connection(instance_user_id):
        # Another person's instance is reached as they would reach it, by whoever manages the machine.
        instance_user = (
            await Users.get_user_by_id(instance_user_id) if await has_machine_write_access(user, machine_id) else None
        )
        if instance_user is None:
            raise HTTPException(403, 'Instance access denied')
        connection = await find_machine_connection(instance_user, machine_id, metadata, request=request)
        return connection and {'instance_user_id': instance_user.id, **connection}

    instance_user_id = metadata.pop('instance_user_id', None)
    if instance_user_id and instance_user_id != user.id:
        return await find_instance_user_connection(instance_user_id)
    chat = None
    shared_session = None
    instance_user = user
    chat_id = metadata.get('chat_id')
    folder_id = None
    if isinstance(chat_id, str) and chat_id.startswith(FOLDER_SESSION_ID_PREFIX):
        folder_id = get_folder_id_of_session(chat_id, user.id)
        await require_folder_panels(user, folder_id)
    elif chat_id and is_saved_chat_id(chat_id):
        chat = await Chats.get_chat_metadata_by_id(chat_id)
        if chat is None or not await Chats.has_chat_access(chat_id, user, permission='write', chat=chat):
            if chat is None or not await has_machine_write_access(user, machine_id):
                raise HTTPException(403, 'Chat access denied')
            return await find_instance_user_connection(chat.user_id)
        chat_meta = chat.meta or {}
        if chat_meta.get('internal') is True and chat_meta.get('type') == 'subagent':
            # A sub-agent shares the instance and files of its parent chat.
            metadata['chat_id'] = chat_meta.get('parent_chat_id')
            return await find_machine_connection(user, machine_id, metadata, request=request)
        from open_webui.utils.agents.session import get_session, model_id

        folder_id = chat.folder_id
        if folder_id and await get_folder_machine_mismatch(folder_id, machine_id):
            # A chat that was on another machine before keeps it.
            full_chat = await Chats.get_chat_by_id(chat_id)
            if full_chat is None or machine_id_of(full_chat.chat) != machine_id:
                raise HTTPException(409, 'Chats in this folder run on its machine')
        if not chat.current_message_id:
            # Only the full chat knows where the history ends.
            chat = await Chats.get_chat_by_id(chat_id)
            if chat is None:
                raise HTTPException(403, 'Chat access denied')
        shared_session = await get_session(chat)
        if shared_session and shared_session['machine_id'] != machine_id:
            shared_session = None
        if shared_session:
            metadata['model_id'] = model_id(shared_session)
            instance_user_id = shared_session.get('instance_user_id') or shared_session['user']
            instance_user = user if instance_user_id == user.id else await Users.get_user_by_id(instance_user_id)
            if instance_user is None:
                raise HTTPException(403, 'Agent machine owner is unavailable')

    workspace = None
    if folder_id:
        folder_machine = await get_folder_machine(folder_id)
        workspace = {
            'id': folder_session_id(folder_id, user.id),
            'directory': folder_machine['working_directory']
            if folder_machine and folder_machine['machine_id'] == machine_id
            else None,
        }

    def authorized_connection(connection):
        if workspace:
            connection = {**connection, 'workspace': workspace}
        if shared_session:
            connection = {**connection, 'instance_user_id': instance_user.id}
        return connection

    if not machine_id.startswith('template:'):
        connections = await get_machine_connections(instance_user, include_templates=False)
        connection = next((c for c in connections if c.get('id') == machine_id), None)
        if (
            not connection
            or not connection.get('enabled', True)
            or not await has_connection_access(instance_user, connection)
        ):
            return None
        if is_terminal_orchestrator(connection):
            raise HTTPException(409, 'Select a machine template')
        return authorized_connection(connection)

    connection_id, template_id = split_template_id(machine_id)
    connection = await get_connection(instance_user, connection_id)
    template = await server_request(connection, f'api/v1/terminals/templates/{quote(template_id, safe="")}')
    scope = (template.get('data') or {}).get('scope')

    if chat and not shared_session:
        full_chat = await Chats.get_chat_by_id(chat_id)
        if full_chat is None:
            raise HTTPException(403, 'Chat access denied')
        stored = machine_id_of(full_chat.chat)
        if chat.user_id != user.id and stored != machine_id:
            raise HTTPException(403, 'Use the machine selected by the chat owner')
        if stored and stored != machine_id:
            raise HTTPException(409, 'Chat machine selection changed; refresh the chat')

    principal = instance_user
    if not shared_session and scope == 'chat' and chat:
        owner = user if chat.user_id == user.id else await Users.get_user_by_id(chat.user_id)
        if owner is None:
            raise HTTPException(403, 'Chat owner is unavailable')
        if (
            owner.id != instance_user.id
            and not await has_connection_access(owner, connection)
            and not await has_connection_write_access(owner, connection)
        ):
            raise HTTPException(403, 'Machine connection access denied')
        principal = owner
    if not await has_connection_write_access(principal, connection):
        await require_machine_access(principal, machine_id)

    context = get_machine_context(template, instance_user.id, metadata)
    if scope == 'model':
        await require_model_access(instance_user, context['model_id'], machine_id, request)
    if metadata.get('automation_id'):
        from open_webui.models.automations import Automations

        automation = await Automations.get_by_id(metadata['automation_id'])
        if not automation or automation.user_id != user.id:
            raise HTTPException(403, 'Automation machine access denied')
    return authorized_connection(
        {
            **connection,
            'id': machine_id,
            'name': (template.get('data') or {}).get('name') or template_id,
            'template_id': template_id,
            'scope': scope,
            'auth_type': 'bearer',
            'machine_context': context,
        }
    )


async def resolve_machine_connection(request, user, metadata):
    """Resolve an authorized backend connection and trusted instance headers."""
    machine_id = metadata.get('machine_id')
    if not ENABLE_TOOL_SERVERS or not machine_id:
        return None
    from open_webui.models.users import UserModel
    from open_webui.utils.tools import build_tool_server_headers

    user_model = user if isinstance(user, UserModel) else UserModel(**user)
    connection = await find_machine_connection(user_model, machine_id, metadata, request=request)

    if connection:
        headers, cookies = await build_tool_server_headers(
            connection,
            request,
            user_model,
            metadata=metadata,
        )
        headers.update(machine_headers(connection))
        headers['Accept'] = 'application/json'
        headers['X-User-Id'] = connection.get('instance_user_id', user_model.id)
        if metadata.get('chat_id'):
            headers['X-Session-Id'] = metadata['chat_id']
        return connection, headers, cookies
    return None


async def get_machine_json(
    request,
    user,
    metadata: dict,
    path: str,
    extra_params: dict | None = None,
    *,
    file: dict | None = None,
    method: str = 'GET',
    body: dict | None = None,
):
    """Read JSON or upload a file through the chat's terminal connection."""
    metadata = metadata or {}
    machine_id = metadata.get('machine_id')
    if not ENABLE_TOOL_SERVERS or not machine_id:
        return None

    import aiohttp
    from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL

    resolved = await resolve_machine_connection(request, user, metadata)
    if resolved:
        connection, headers, cookies = resolved
        json_body = body
        body = None
        if file:
            from open_webui.models.files import Files
            from open_webui.storage.provider import Storage

            source = await Files.get_file_by_id(file['id'])
            if not source or source.user_id != (user.id if hasattr(user, 'id') else user['id']) or not source.path:
                return None
            local_path = await asyncio.to_thread(Storage.get_file, source.path)
            body = aiohttp.FormData()
            body.add_field(
                'file',
                open(local_path, 'rb'),
                filename=file['name'],
                content_type=(source.meta or {}).get('content_type') or 'application/octet-stream',
            )
            headers = {key: value for key, value in headers.items() if key.lower() != 'content-type'}
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MACHINE)
        try:
            async with get_machine_client(
                get_machine_url(connection),
                connection.get('instance_user_id') or (user.id if hasattr(user, 'id') else user['id']),
                service=connection.get('service', 'open_terminal'),
                timeout=timeout,
                trust_env=True,
            ) as session:
                async with session.request(
                    'POST' if file else method,
                    f'{get_machine_url(connection)}{path}',
                    headers=headers,
                    cookies=cookies,
                    data=body,
                    json=None if file else json_body,
                    ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
                    allow_redirects=False,
                ) as response:
                    return await response.json() if 200 <= response.status < 300 else None
        except TimeoutError as error:
            raise TimeoutError(
                f"Machine '{connection.get('name') or machine_id}' timed out. "
                'It may still be starting. Please try again.'
            ) from error
    return None


async def get_folder_machine_defaults(user, folder_id):
    if not folder_id:
        return {}
    from fastapi import HTTPException
    from open_webui.models.folders import Folders
    from open_webui.utils.access_control.folders import has_folder_access

    folder = await Folders.get_folder_by_id(folder_id)
    if not folder or not await has_folder_access(user.id, folder, 'write', None):
        raise HTTPException(403, 'Folder is unavailable')
    return await get_folder_machine(folder_id) or {}


async def get_folder_machine(folder_id):
    """The machine a folder is on, and the directory there."""
    from open_webui.models.folders import Folders

    folder = await Folders.get_folder_by_id(folder_id)
    data = (folder.data or {}) if folder else {}
    if not machine_id_of(data):
        return None
    return {'machine_id': machine_id_of(data), 'working_directory': data.get('working_directory')}


async def get_folder_machine_mismatch(folder_id, machine_id):
    """The folder's machine id when it is a different one that everything in the folder has to use."""
    folder_machine = await get_folder_machine(folder_id)
    if not folder_machine or folder_machine['machine_id'] == machine_id:
        return None
    if folder_machine['machine_id'].startswith('template:'):
        # A machine per chat or model is not one place, so the folder only suggests it.
        from open_webui.models.users import Users
        from open_webui.models.folders import Folders

        folder = await Folders.get_folder_by_id(folder_id)
        owner = await Users.get_user_by_id(folder.user_id)
        try:
            _, template = await template_connection(owner, folder_machine['machine_id'])
        except HTTPException:
            return None
        if (template.get('data') or {}).get('scope') in ('chat', 'model'):
            return None
    return folder_machine['machine_id']


async def get_folder_directory(folder_id):
    """The directory everything in the folder starts in, when its machine is fixed and it has one."""
    if not folder_id or not await get_folder_machine_mismatch(folder_id, None):
        return None
    return (await get_folder_machine(folder_id))['working_directory']


async def can_use_machine(user, machine_id, request=None):
    try:
        return await find_machine_connection(user, machine_id, request=request) is not None
    except HTTPException:
        return False


async def require_chat_folder_machine(folder_id, machine_id):
    if folder_id and machine_id and await get_folder_machine_mismatch(folder_id, machine_id):
        raise HTTPException(409, 'Chats in this folder run on its machine')


async def require_folder_panels(user, folder_id):
    """Check that a person may have panels in a folder; machine access is checked apart.

    Shells left on the folder's earlier machine stay reachable, so its current one is not required.
    """
    from open_webui.models.folders import Folders
    from open_webui.utils.access_control.folders import has_folder_access

    folder = await Folders.get_folder_by_id(folder_id) if folder_id else None
    if not folder or (user.role != 'admin' and not await has_folder_access(user.id, folder, 'read', None)):
        raise HTTPException(403, 'Folder access denied')


async def initialize_machine_directory(request, user, metadata, machine_id, path):
    if not machine_id or not path:
        return
    from fastapi import HTTPException
    from open_webui.utils.tether import get_machine_connections

    if not isinstance(path, str):
        raise HTTPException(400, 'Invalid working directory')
    # A machine only the browser reaches gets its folder from the browser.
    if not any(connection.get('id') == machine_id for connection in await get_machine_connections(user)):
        return
    result = await get_machine_json(
        request,
        user,
        {**metadata, 'machine_id': machine_id},
        '/files/cwd',
        method='POST',
        body={'path': path},
    )
    if not result or not result.get('cwd'):
        raise HTTPException(400, 'Working directory is unavailable. Check the machine connection and path.')
    metadata['initial_machine_cwd'] = result['cwd']


async def filter_user_terminal_tools(request, user, tools: dict, metadata: dict, extra_params: dict):
    """Let Open Terminal, which owns the shells, confirm availability for this user and chat."""
    machine_id = metadata.get('machine_id')
    shell_tools = {
        name: tool
        for name, tool in tools.items()
        if name in {'read_user_terminal', 'send_user_terminal_input'} and tool.get('type') == 'terminal'
    }
    selected = {
        name: tool
        for name, tool in shell_tools.items()
        if machine_id and is_machine_ref(tool.get('tool_id')) and strip_machine_prefix(tool['tool_id']) == machine_id
    }
    available = False
    if selected and not metadata.get('automation_id') and not metadata.get('internal'):
        available = any(tool.get('user_shell_tools') == 'always' for tool in selected.values())
        if not available and metadata.get('chat_id'):
            try:
                # This endpoint checks ownership, a live process, and a connected shell.
                # Its output is discarded; the model must explicitly read the terminal tab.
                async with asyncio.timeout(5):
                    state = await get_machine_json(request, user, metadata, '/api/terminals/user/output', extra_params)
                available = isinstance(state, dict) and isinstance(state.get('output'), str)
            except Exception as error:
                log.debug('User terminal availability check failed (%s)', type(error).__name__)

    for name in shell_tools:
        if not available or name not in selected:
            tools.pop(name)

    if available and 'read_user_terminal' in selected:
        tool = selected['read_user_terminal']
        tools['read_user_terminal'] = {
            **tool,
            'spec': {
                **tool['spec'],
                'description': tool['spec'].get('description', '')
                + "\nReads the user's Open WebUI Terminal tab, separate from the Desktop. "
                'Use this tool when the user refers to an open terminal tab.',
            },
        }


async def upload_files_to_machine(request, user, files: list[dict], metadata: dict, extra_params: dict):
    """Copy Open WebUI files to the selected terminal, adding machine_path or machine_error to each entry."""
    if not metadata.get('machine_id') or not files:
        return
    try:
        cwd = await asyncio.wait_for(
            get_machine_json(request, user, metadata, '/files/cwd', extra_params),
            timeout=AIOHTTP_CLIENT_TIMEOUT_MACHINE,
        )
        directory = cwd.get('cwd') if isinstance(cwd, dict) else None
        if not directory:
            raise ValueError('Machine working directory unavailable')
        path = f'/files/upload?directory={quote(directory, safe="")}'
        for entry in files:
            try:
                # The file ID keeps separate files from overwriting one another.
                file = {'id': entry['id'], 'name': f'{entry["id"]}{Path(entry["name"]).suffix}'}
                result = await asyncio.wait_for(
                    get_machine_json(request, user, metadata, path, extra_params, file=file),
                    timeout=AIOHTTP_CLIENT_TIMEOUT_MACHINE,
                )
                if not isinstance(result, dict) or not isinstance(result.get('path'), str) or not result['path']:
                    raise ValueError('Machine upload failed')
                entry['machine_path'] = result['path']
            except Exception as error:
                log.warning('File terminal upload failed (%s)', type(error).__name__)
                entry['machine_error'] = 'File saved in Open WebUI, but upload to the selected terminal failed.'
    except Exception as error:
        log.warning('File terminal unavailable (%s)', type(error).__name__)
        for entry in files:
            entry['machine_error'] = 'File saved in Open WebUI, but the selected terminal is unavailable.'


async def save_tool_result_to_machine(request, user, metadata: dict | None, content: str) -> str | None:
    """Save a tool's full result where the model's machine tools can read it, and return its path."""
    tools = (metadata or {}).get('tools') or {}
    if not any(tool.get('type') == 'terminal' for tool in tools.values()):
        return None
    try:
        # Beside the user's recent folders (src/lib/apis/machines/recentFolders.ts).
        home = (await get_machine_json(request, user, metadata, '/files/cwd'))['home']
        path = posixpath.join(home, f'.open-webui/users/{user.id}/outputs/{uuid4().hex}.txt')
        body = {'path': path, 'content': content}
        result = await get_machine_json(request, user, metadata, '/files/write', method='POST', body=body)
        return result['path'] if result else None
    except Exception as error:
        log.warning('Tool result could not be saved to the machine (%s)', type(error).__name__)
        return None


async def get_machine_file(request, user, metadata: dict, path: str, *, max_bytes: int) -> bytes:
    """Read a bounded file through the authorized terminal connection."""
    import aiohttp
    from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL

    resolved = await resolve_machine_connection(request, user, metadata)
    if not resolved:
        raise ValueError('Reading files requires a machine connection reachable by Open WebUI.')
    connection, headers, cookies = resolved
    base_url = get_machine_url(connection)
    async with get_machine_client(
        base_url,
        connection.get('instance_user_id') or (user.id if hasattr(user, 'id') else user['id']),
        service=connection.get('service', 'open_terminal'),
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MACHINE),
        trust_env=True,
    ) as session:
        async with session.get(
            f'{base_url}/files/view?path={quote(path, safe="")}',
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
            allow_redirects=False,
        ) as response:
            if response.status != 200:
                raise ValueError(f'Could not read {path} from the machine.')
            data = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                if len(data) + len(chunk) > max_bytes:
                    raise ValueError(f'File exceeds the {max_bytes}-byte limit.')
                data.extend(chunk)
    return bytes(data)


async def get_chat_folder_directory(metadata: dict) -> str | None:
    """The directory of the chat's folder, when the chat runs on the folder's machine."""
    from open_webui.models.chats import Chats

    chat_id = metadata.get('chat_id')
    chat = await Chats.get_chat_metadata_by_id(chat_id) if is_saved_chat_id(chat_id) else None
    folder_machine = await get_folder_machine(chat.folder_id) if chat and chat.folder_id else None
    if not folder_machine or folder_machine['machine_id'] != metadata.get('machine_id'):
        return None
    return folder_machine['working_directory']


async def get_machine_agents_md(request, user, metadata: dict, extra_params: dict | None = None) -> str | None:
    """Load the machine user's home AGENTS.md, then the folder's, afresh for this turn."""
    try:
        async with asyncio.timeout(5):
            data = await get_machine_json(request, user, metadata, '/files/cwd', extra_params)
            home = data.get('home') if isinstance(data, dict) else None
            if not isinstance(home, str) or not (posixpath.isabs(home) or ntpath.isabs(home)):
                return None
            contents = []
            candidates = [[home, ('AGENTS.md',)]]
            directory = await get_chat_folder_directory(metadata)
            if directory and directory != home:
                candidates.append([directory, ('AGENTS.md', 'CLAUDE.md')])
            for directory, names in candidates:
                for name in names:
                    path = quote(posixpath.join(directory, name), safe='')
                    data = await get_machine_json(request, user, metadata, f'/files/read?path={path}', extra_params)
                    content = data.get('content') if isinstance(data, dict) else None
                    if not isinstance(content, str) or not content.strip():
                        continue
                    size = sum(len(text.encode('utf-8')) for text in [*contents, content])
                    if size > MAX_AGENTS_MD_BYTES:
                        log.warning('Skipping machine %s: exceeds %s bytes', name, MAX_AGENTS_MD_BYTES)
                    else:
                        contents.append(f'# {name}\n\n{content}')
                    break
        return '\n\n'.join(contents) or None
    except Exception as e:
        log.debug('Failed to load terminal AGENTS.md (%s)', type(e).__name__)
        return None


def add_machine_agents_md(messages: list[dict], agents_md: str) -> list[dict]:
    """Place file instructions before user requests without changing their content."""
    for index, message in enumerate(messages):
        if message.get('role') == 'user':
            return [*messages[:index], {'role': 'user', 'content': agents_md}, *messages[index:]]
    return messages


async def load_machine_skill(
    request,
    user,
    metadata: dict,
    skill_name: str,
    extra_params: dict | None = None,
    *,
    refresh: bool = True,
) -> dict | None:
    """Load the full source internally and pin/check its fingerprint before shaping model output."""
    skill = await get_machine_json(
        request, user, metadata, f'/skills/read?name={quote(skill_name, safe="")}', extra_params
    )

    if not isinstance(skill, dict) or not isinstance(skill.get('content'), str):
        return None

    context = metadata.get('chat_context') or {}
    metadata['chat_context'] = context
    fingerprints = context.setdefault('machine_skill_fingerprints', {}).setdefault(metadata['machine_id'], {})
    skill_id = f'machine:{quote(skill_name, safe="")}'
    fingerprint = hashlib.sha256(skill['content'].encode('utf-8')).hexdigest()
    previous = fingerprints.get(skill_id)
    if not refresh and previous is not None and previous != fingerprint:
        raise ValueError('Skill changed while reading. Call view_skill again and restart reading.')
    fingerprints[skill_id] = fingerprint
    return skill


async def get_machine_skill(
    request,
    user,
    metadata: dict,
    skill_name: str,
    extra_params: dict | None = None,
    *,
    offset: int = 0,
    max_chars: int = SKILL_CONTENT_MAX_CHARS,
    refresh: bool = True,
    overview: bool = False,
    tools_enabled: bool = True,
) -> dict | None:
    skill = await load_machine_skill(request, user, metadata, skill_name, extra_params, refresh=refresh)
    if skill is None:
        return None

    location = skill.get('location') or skill.get('path') or ''
    directory = location.rsplit('/', 1)[0] if '/' in location else location
    resources = skill.get('resources') if isinstance(skill.get('resources'), list) else []
    return {
        'name': skill.get('name'),
        'description': skill.get('description'),
        'directory': directory,
        **(
            await skill_overview(skill['content'], resources, 'resources', tools_enabled)
            if overview
            else {
                **await skill_content_page(skill['content'], offset, max_chars),
                **bounded_skill_manifest(resources, 'resources'),
            }
        ),
    }


def format_machine_skill_context(skill: dict, skill_id: str, tools_enabled: bool) -> str:
    resources = skill.get('resources') if isinstance(skill.get('resources'), list) else []
    parts = [f'<skill name="{skill.get("name") or ""}">', format_skill_content(skill, skill_id, tools_enabled)]
    if skill.get('directory'):
        parts.append(f'<directory>{skill["directory"]}</directory>')
    if resources:
        parts.append('<resources>')
        parts.extend(f'<file>{resource}</file>' for resource in resources)
        parts.append('</resources>')
    if skill.get('notice'):
        parts.append(skill['notice'])
    parts.append('</skill>')
    return '\n'.join(parts)


def format_machine_skill_manifest_entry(skill: dict) -> str:
    location = skill.get('location') or skill.get('path') or ''
    location_tag = f'<location>{location}</location>\n' if location else ''
    return (
        f'<skill>\n<id>{skill["id"]}</id>\n<name>{skill["name"]}</name>\n'
        f'<description>{skill.get("description") or ""}</description>\n'
        f'<source>terminal</source>\n'
        f'{location_tag}'
        f'</skill>\n'
    )
