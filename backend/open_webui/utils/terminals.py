"""Shared routing helpers for admin-configured terminal servers."""

import asyncio
import hashlib
import logging
import ntpath
import posixpath
from pathlib import Path
from urllib.parse import quote, unquote

import aiohttp

from fastapi import HTTPException

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT_TERMINAL, ENABLE_TOOL_SERVERS
from open_webui.utils.headers import bearer_auth_header
from open_webui.utils.chat_id import is_saved_chat_id
from open_webui.utils.skill_files import (
    SKILL_CONTENT_MAX_CHARS,
    bounded_skill_manifest,
    format_skill_content,
    skill_content_page,
    skill_overview,
)

TERMINAL_CHAT_UPLOAD_MODES = {'default', 'filesystem'}
MAX_AGENTS_MD_BYTES = 32 * 1024

log = logging.getLogger(__name__)


def is_terminal_orchestrator(connection: dict) -> bool:
    return connection.get('server_type') == 'orchestrator'


def get_terminal_server_url(connection: dict) -> str:
    return str(connection.get('url') or '').rstrip('/')


def terminal_chat_uploads(connection: dict) -> str:
    """Return normalized main-chat upload behavior for this connection."""
    value = (connection.get('config') or {}).get('chat_uploads')
    return value if value in TERMINAL_CHAT_UPLOAD_MODES else 'default'


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
    connections = await Config.get('terminal_server.connections', []) or []
    connection = next((c for c in connections if c.get('id') == connection_id), None)
    if not connection or not connection.get('enabled', True) or connection.get('server_type') != 'orchestrator':
        raise HTTPException(404, 'Managed terminal connection not found')
    if not await has_connection_access(user, connection) and not await has_connection_write_access(user, connection):
        raise HTTPException(403, 'Terminal connection access denied')
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


def template_terminal_id(connection_id, template_id):
    return f'template:{connection_id}:{quote(template_id, safe="")}'


def split_template_id(terminal_id):
    if not terminal_id.startswith('template:'):
        raise HTTPException(400, 'Invalid template terminal ID')
    connection_id, separator, encoded = terminal_id.removeprefix('template:').rpartition(':')
    template_id = unquote(encoded)
    if not separator or not connection_id or not template_id or template_terminal_id(connection_id, template_id) != terminal_id:
        raise HTTPException(400, 'Invalid template terminal ID')
    return connection_id, template_id


async def require_terminal_access(user, terminal_id):
    from open_webui.models.access_grants import AccessGrants
    from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL

    if user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
        return
    if await AccessGrants.has_access(user.id, 'terminal', terminal_id, 'read'):
        return
    raise HTTPException(403, 'Terminal access denied')


async def template_connection(user, terminal_id, permission='read'):
    connection_id, template_id = split_template_id(terminal_id)
    connection = await get_connection(user, connection_id)
    if not await has_connection_write_access(user, connection):
        if permission == 'write':
            raise HTTPException(403, 'Terminal connection write access required')
        await require_terminal_access(user, terminal_id)
    template = await server_request(connection, f'api/v1/terminals/templates/{quote(template_id, safe="")}')
    return connection, template


async def list_template_connections(user, connections):
    from open_webui.models.access_grants import AccessGrants
    from open_webui.models.groups import Groups
    from open_webui.models.users import UserModel
    from open_webui.utils.access_control import has_connection_access

    if not isinstance(user, UserModel):
        user = UserModel(**user)
    group_ids = {
        group.id for group in await Groups.get_groups_by_member_id(user.id, include_inherited=True)
    }
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
        selectors = [template_terminal_id(connection['id'], template['id']) for template in templates]
        readable = set(selectors) if writable else await AccessGrants.get_accessible_resource_ids(
            user_id=user.id, resource_type='terminal', resource_ids=selectors,
            permission='read', user_group_ids=group_ids,
        )
        for template, selector in zip(templates, selectors):
            if selector not in readable:
                continue
            data = template.get('data') or {}
            result.append({
                **connection, 'id': selector,
                'name': data.get('name') or template['id'],
                'template_id': template['id'], 'scope': data.get('scope'),
                'auth_type': 'bearer',
            })
    return result


class MissingTerminalContext(HTTPException):
    def __init__(self, scope):
        detail = 'This terminal requires a saved chat' if scope == 'chat' else f'This terminal requires a {scope}'
        super().__init__(409, detail)


def get_terminal_context(template, user_id, metadata=None):
    """Validate a template's scope and return context for its environment."""
    metadata = metadata or {}
    scope = (template.get('data') or {}).get('scope')
    if scope not in (None, 'user', 'chat', 'model'):
        raise HTTPException(422, 'Invalid template scope')
    chat_id = metadata.get('chat_id')
    model_id = metadata.get('model_id') or metadata.get('model')
    if scope == 'chat' and not is_saved_chat_id(chat_id):
        raise MissingTerminalContext(scope)
    if scope == 'model' and not model_id:
        raise MissingTerminalContext(scope)
    return {
        'user_id': user_id,
        'chat_id': chat_id if is_saved_chat_id(chat_id) else None,
        'model_id': model_id if scope == 'model' else None,
    }


async def require_model_access(user, model_id, terminal_id, request=None):
    if not model_id:
        raise MissingTerminalContext('model')
    if model_id.startswith('agent:'):
        parts = model_id.split(':', 3)
        if len(parts) != 4 or unquote(parts[1]) != terminal_id or not all(parts[1:]):
            raise HTTPException(403, 'Agent model does not belong to this terminal')
        # Agent access follows its terminal. Execution still validates the live agent catalog.
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


def terminal_headers(connection):
    """Only consumes context produced by find_terminal_connection, never browser headers."""
    if not connection.get('template_id'):
        return {'X-User-Id': connection['instance_user_id']} if connection.get('instance_user_id') else {}
    context = connection['terminal_context']
    headers = {
        'X-Terminal-Template-Id': connection['template_id'],
        'X-User-Id': context['user_id'],
    }
    if context.get('chat_id'):
        headers['X-Terminal-Chat-Id'] = context['chat_id']
    if context.get('model_id'):
        headers['X-Terminal-Model-Id'] = context['model_id']
    return headers


async def find_terminal_connection(user, terminal_id, metadata=None, request=None):
    from open_webui.models.chats import Chats
    from open_webui.models.users import UserModel, Users
    from open_webui.utils.access_control import has_connection_access
    from open_webui.utils.tether import get_terminal_connections

    if not ENABLE_TOOL_SERVERS:
        raise HTTPException(403, 'Tool servers are disabled')
    if not isinstance(user, UserModel):
        user = UserModel(**user)
    metadata = dict(metadata or {})
    chat = None
    shared_session = None
    instance_user = user
    chat_id = metadata.get('chat_id')
    if chat_id and is_saved_chat_id(chat_id):
        chat = await Chats.get_accessible_chat_by_id(chat_id, user, permission='write')
        if chat is None:
            raise HTTPException(403, 'Chat access denied')
        if chat.meta.get('internal') is True and chat.meta.get('type') == 'subagent':
            # A sub-agent shares the machine and files of its parent chat.
            metadata['chat_id'] = chat.meta.get('parent_chat_id')
            return await find_terminal_connection(user, terminal_id, metadata, request=request)
        from open_webui.utils.agents.session import get_session, model_id
        shared_session = await get_session(chat)
        if shared_session and shared_session['terminal_id'] != terminal_id:
            shared_session = None
        if shared_session:
            metadata['model_id'] = model_id(shared_session)
            instance_user_id = shared_session.get('terminal_user_id') or shared_session['user']
            instance_user = user if instance_user_id == user.id else await Users.get_user_by_id(instance_user_id)
            if instance_user is None:
                raise HTTPException(403, 'Agent terminal owner is unavailable')

    def authorized_connection(connection):
        if shared_session:
            connection = {**connection, 'instance_user_id': instance_user.id}
        return connection

    if not terminal_id.startswith('template:'):
        connections = await get_terminal_connections(instance_user, include_templates=False)
        connection = next((c for c in connections if c.get('id') == terminal_id), None)
        if not connection or not connection.get('enabled', True) or not await has_connection_access(instance_user, connection):
            return None
        if is_terminal_orchestrator(connection):
            raise HTTPException(409, 'Select a terminal template')
        return authorized_connection(connection)

    connection_id, template_id = split_template_id(terminal_id)
    connection = await get_connection(instance_user, connection_id)
    template = await server_request(connection, f'api/v1/terminals/templates/{quote(template_id, safe="")}')
    scope = (template.get('data') or {}).get('scope')

    if chat and not shared_session:
        stored = (chat.chat or {}).get('terminal_id')
        if chat.user_id != user.id and stored != terminal_id:
            raise HTTPException(403, 'Use the terminal selected by the chat owner')
        if stored and stored != terminal_id:
            raise HTTPException(409, 'Chat terminal selection changed; refresh the chat')

    principal = instance_user
    if not shared_session and scope == 'chat' and chat:
        owner = user if chat.user_id == user.id else await Users.get_user_by_id(chat.user_id)
        if owner is None:
            raise HTTPException(403, 'Chat owner is unavailable')
        if owner.id != instance_user.id and not await has_connection_access(owner, connection) and not await has_connection_write_access(owner, connection):
            raise HTTPException(403, 'Terminal connection access denied')
        principal = owner
    if not await has_connection_write_access(principal, connection):
        await require_terminal_access(principal, terminal_id)

    context = get_terminal_context(template, instance_user.id, metadata)
    if scope == 'model':
        await require_model_access(instance_user, context['model_id'], terminal_id, request)
    if metadata.get('automation_id'):
        from open_webui.models.automations import Automations
        automation = await Automations.get_by_id(metadata['automation_id'])
        if not automation or automation.user_id != user.id:
            raise HTTPException(403, 'Automation terminal access denied')
    return authorized_connection({
        **connection, 'id': terminal_id,
        'template_id': template_id, 'scope': scope, 'auth_type': 'bearer',
        'terminal_context': context,
    })


async def resolve_terminal_connection(request, user, metadata):
    """Resolve an authorized backend connection and trusted instance headers."""
    terminal_id = metadata.get('terminal_id')
    if not ENABLE_TOOL_SERVERS or not terminal_id:
        return None
    from open_webui.models.users import UserModel
    from open_webui.utils.tools import build_tool_server_headers

    user_model = user if isinstance(user, UserModel) else UserModel(**user)
    connection = await find_terminal_connection(user_model, terminal_id, metadata, request=request)

    if connection:
        headers, cookies = await build_tool_server_headers(
            connection,
            request,
            user_model,
            metadata=metadata,
        )
        headers.update(terminal_headers(connection))
        headers['Accept'] = 'application/json'
        headers['X-User-Id'] = connection.get('instance_user_id', user_model.id)
        if metadata.get('chat_id'):
            headers['X-Session-Id'] = metadata['chat_id']
        return connection, headers, cookies
    return None


async def get_terminal_json(
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
    """Read JSON or upload a file through an admin terminal or a personal terminal's browser."""
    metadata = metadata or {}
    terminal_id = metadata.get('terminal_id')
    if not ENABLE_TOOL_SERVERS or not terminal_id:
        return None

    import aiohttp
    from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
    from open_webui.utils.tether import get_terminal_client

    resolved = await resolve_terminal_connection(request, user, metadata)
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
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_TERMINAL)
        try:
            async with get_terminal_client(
                get_terminal_server_url(connection),
                connection.get('instance_user_id') or (user.id if hasattr(user, 'id') else user['id']),
                timeout=timeout,
                trust_env=True,
            ) as session:
                async with session.request(
                    'POST' if file else method,
                    f'{get_terminal_server_url(connection)}{path}',
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
                f"Terminal '{connection.get('name') or terminal_id}' timed out. "
                'It may still be starting. Please try again.'
            ) from error

    event_caller = (extra_params or {}).get('__event_call__')
    if event_caller:
        result = await event_caller(
            {
                'type': 'request:terminal',
                'data': {
                    'terminal_id': terminal_id,
                    'path': path,
                    'session_id': metadata.get('session_id'),
                    **({'file': file} if file else {}),
                },
            }
        )
        return result.get('data') if isinstance(result, dict) else None
    return None


async def get_folder_terminal_defaults(user, folder_id):
    if not folder_id:
        return {}
    from fastapi import HTTPException
    from open_webui.models.folders import Folders
    from open_webui.utils.access_control.folders import has_folder_access

    folder = await Folders.get_folder_by_id(folder_id)
    if not folder or not await has_folder_access(user.id, folder, 'write', None):
        raise HTTPException(403, 'Folder is unavailable')
    data = folder.data or {}
    return {
        'terminal_id': data.get('terminal_id'),
        'working_directory': data.get('working_directory'),
    }


async def initialize_terminal_directory(request, user, metadata, terminal_id, path):
    if not terminal_id or not path:
        return
    from fastapi import HTTPException
    from open_webui.utils.tether import get_terminal_connections

    if not isinstance(path, str):
        raise HTTPException(400, 'Invalid working directory')
    # A terminal only the browser reaches gets its folder from the browser.
    if not any(connection.get('id') == terminal_id for connection in await get_terminal_connections(user)):
        return
    result = await get_terminal_json(
        request,
        user,
        {**metadata, 'terminal_id': terminal_id},
        '/files/cwd',
        method='POST',
        body={'path': path},
    )
    if not result or not result.get('cwd'):
        raise HTTPException(400, 'Working directory is unavailable. Check the terminal connection and path.')
    metadata['initial_terminal_cwd'] = result['cwd']


async def filter_user_terminal_tools(request, user, tools: dict, metadata: dict, extra_params: dict):
    """Let Open Terminal, which owns the shells, confirm availability for this user and chat."""
    terminal_id = metadata.get('terminal_id')
    shell_tools = {
        name: tool
        for name, tool in tools.items()
        if name in {'read_user_terminal', 'send_user_terminal_input'}
        and (tool.get('type') == 'terminal' or tool.get('server', {}).get('is_terminal') is True)
    }
    selected = {
        name: tool
        for name, tool in shell_tools.items()
        if terminal_id
        and (
            tool.get('tool_id') == f'terminal:{terminal_id}'
            or (tool.get('direct') and tool.get('server', {}).get('url') == terminal_id)
        )
    }
    available = False
    if selected and not metadata.get('automation_id') and not metadata.get('internal'):
        available = any(
            tool.get('user_shell_tools') == 'always'
            or (tool.get('direct') and (tool.get('server', {}).get('config') or {}).get('user_shell_tools') == 'always')
            for tool in selected.values()
        )
        if not available and metadata.get('chat_id'):
            try:
                # This endpoint checks ownership, a live process, and a connected shell.
                # Its output is discarded; the model must explicitly read the terminal.
                async with asyncio.timeout(5):
                    state = await get_terminal_json(request, user, metadata, '/api/terminals/user/output', extra_params)
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


async def upload_files_to_terminal(request, user, files: list[dict], metadata: dict, extra_params: dict):
    """Copy Open WebUI files to the selected terminal, adding terminal_path or terminal_error to each entry."""
    if not metadata.get('terminal_id') or not files:
        return
    try:
        cwd = await asyncio.wait_for(
            get_terminal_json(request, user, metadata, '/files/cwd', extra_params),
            timeout=AIOHTTP_CLIENT_TIMEOUT_TERMINAL,
        )
        directory = cwd.get('cwd') if isinstance(cwd, dict) else None
        if not directory:
            raise ValueError('Terminal working directory unavailable')
        path = f'/files/upload?directory={quote(directory, safe="")}'
        for entry in files:
            try:
                # The file ID keeps separate files from overwriting one another.
                file = {'id': entry['id'], 'name': f'{entry["id"]}{Path(entry["name"]).suffix}'}
                result = await asyncio.wait_for(
                    get_terminal_json(request, user, metadata, path, extra_params, file=file),
                    timeout=AIOHTTP_CLIENT_TIMEOUT_TERMINAL,
                )
                if not isinstance(result, dict) or not isinstance(result.get('path'), str) or not result['path']:
                    raise ValueError('Terminal upload failed')
                entry['terminal_path'] = result['path']
            except Exception as error:
                log.warning('File terminal upload failed (%s)', type(error).__name__)
                entry['terminal_error'] = 'File saved in Open WebUI, but upload to the selected terminal failed.'
    except Exception as error:
        log.warning('File terminal unavailable (%s)', type(error).__name__)
        for entry in files:
            entry['terminal_error'] = 'File saved in Open WebUI, but the selected terminal is unavailable.'


async def get_terminal_file(request, user, metadata: dict, path: str, *, max_bytes: int) -> bytes:
    """Read a bounded file through the authorized terminal connection."""
    import aiohttp
    from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
    from open_webui.utils.tether import get_terminal_client

    resolved = await resolve_terminal_connection(request, user, metadata)
    if not resolved:
        raise ValueError('Reading files requires a terminal connection reachable by Open WebUI.')
    connection, headers, cookies = resolved
    base_url = get_terminal_server_url(connection)
    async with get_terminal_client(
        base_url,
        connection.get('instance_user_id') or (user.id if hasattr(user, 'id') else user['id']),
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_TERMINAL),
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
                raise ValueError(f'Could not read {path} from the terminal.')
            data = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                if len(data) + len(chunk) > max_bytes:
                    raise ValueError(f'File exceeds the {max_bytes}-byte limit.')
                data.extend(chunk)
    return bytes(data)


async def get_terminal_agents_md(request, user, metadata: dict, extra_params: dict | None = None) -> str | None:
    """Load the selected terminal user's home AGENTS.md afresh for this turn."""
    try:
        async with asyncio.timeout(5):
            data = await get_terminal_json(request, user, metadata, '/files/cwd', extra_params)
            home = data.get('home') if isinstance(data, dict) else None
            if not isinstance(home, str) or not (posixpath.isabs(home) or ntpath.isabs(home)):
                return None
            path = quote(posixpath.join(home, 'AGENTS.md'), safe='')
            data = await get_terminal_json(request, user, metadata, f'/files/read?path={path}', extra_params)

        content = data.get('content') if isinstance(data, dict) else None
        if not isinstance(content, str) or not content.strip():
            return None
        if len(content.encode('utf-8')) > MAX_AGENTS_MD_BYTES:
            log.warning('Skipping terminal AGENTS.md: exceeds %s bytes', MAX_AGENTS_MD_BYTES)
            return None
        return f'# AGENTS.md\n\n{content}'
    except Exception as e:
        log.debug('Failed to load terminal AGENTS.md (%s)', type(e).__name__)
        return None


def add_terminal_agents_md(messages: list[dict], agents_md: str) -> list[dict]:
    """Place file instructions before user requests without changing their content."""
    for index, message in enumerate(messages):
        if message.get('role') == 'user':
            return [*messages[:index], {'role': 'user', 'content': agents_md}, *messages[index:]]
    return messages


async def load_terminal_skill(
    request,
    user,
    metadata: dict,
    skill_name: str,
    extra_params: dict | None = None,
    *,
    refresh: bool = True,
) -> dict | None:
    """Load the full source internally and pin/check its fingerprint before shaping model output."""
    skill = await get_terminal_json(
        request, user, metadata, f'/skills/read?name={quote(skill_name, safe="")}', extra_params
    )

    if not isinstance(skill, dict) or not isinstance(skill.get('content'), str):
        return None

    context = metadata.get('chat_context') or {}
    metadata['chat_context'] = context
    fingerprints = context.setdefault('terminal_skill_fingerprints', {}).setdefault(metadata['terminal_id'], {})
    skill_id = f'terminal:{quote(skill_name, safe="")}'
    fingerprint = hashlib.sha256(skill['content'].encode('utf-8')).hexdigest()
    previous = fingerprints.get(skill_id)
    if not refresh and previous is not None and previous != fingerprint:
        raise ValueError('Skill changed while reading. Call view_skill again and restart reading.')
    fingerprints[skill_id] = fingerprint
    return skill


async def get_terminal_skill(
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
    skill = await load_terminal_skill(request, user, metadata, skill_name, extra_params, refresh=refresh)
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


def format_terminal_skill_context(skill: dict, skill_id: str, tools_enabled: bool) -> str:
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


def format_terminal_skill_manifest_entry(skill: dict) -> str:
    location = skill.get('location') or skill.get('path') or ''
    location_tag = f'<location>{location}</location>\n' if location else ''
    return (
        f'<skill>\n<id>{skill["id"]}</id>\n<name>{skill["name"]}</name>\n'
        f'<description>{skill.get("description") or ""}</description>\n'
        f'<source>terminal</source>\n'
        f'{location_tag}'
        f'</skill>\n'
    )
