"""Shared routing helpers for admin-configured terminal servers."""

import asyncio
import logging
import ntpath
import posixpath
from urllib.parse import quote

from open_webui.utils.chat_id import is_saved_chat_id

TERMINAL_CONTEXT_HEADER = 'X-Terminal-Context-Id'
TERMINAL_CONTEXT_DEFAULT = 'default'
TERMINAL_CONTEXT_TYPES = {'chat', 'automation'}
TERMINAL_CONTEXT_ID_SOURCES = {'chat': 'chat_id', 'automation': 'automation_id'}
TERMINAL_CHAT_UPLOAD_MODES = {'default', 'filesystem'}
MAX_AGENTS_MD_BYTES = 32 * 1024

log = logging.getLogger(__name__)


def is_terminal_orchestrator(connection: dict) -> bool:
    """Return whether this connection points at Terminals, not raw Open Terminal."""
    return connection.get('server_type') == 'orchestrator' or bool(connection.get('policy_id'))


def get_terminal_server_url(connection: dict) -> str:
    """Return the upstream base URL for a terminal connection.

    An explicit policy uses the named-policy route. Connections without one
    keep their existing root route.
    """
    base_url = str(connection.get('url') or '').rstrip('/')
    policy_id = str(connection.get('policy_id') or '').strip()
    if policy_id:
        return f'{base_url}/p/{quote(policy_id, safe="")}'
    return base_url


def terminal_context_config(connection: dict, context: str) -> dict | bool:
    """Return config for an OpenWebUI terminal context.

    Missing config is legacy behavior: available, shared default terminal.
    """
    if not is_terminal_orchestrator(connection):
        return {}

    contexts = (connection.get('config') or {}).get('contexts')
    if not isinstance(contexts, dict):
        return {}

    value = contexts.get(context, {})
    if value is False:
        return False
    return value if isinstance(value, dict) else {}


def terminal_context_available(connection: dict, context: str) -> bool:
    """Return whether this terminal is exposed in an OpenWebUI context."""
    if context not in TERMINAL_CONTEXT_TYPES:
        return False
    return terminal_context_config(connection, context) is not False


def terminal_context_id(
    connection: dict,
    metadata: dict | None = None,
    context: str = 'chat',
) -> str | None:
    """Return the terminal runtime context for trusted request metadata."""
    if not is_terminal_orchestrator(connection) or not terminal_context_available(connection, context):
        return None

    config = terminal_context_config(connection, context)
    context_id_source = config.get('context_id') if isinstance(config, dict) else None
    if not context_id_source or context_id_source == TERMINAL_CONTEXT_DEFAULT:
        return None

    if context_id_source != TERMINAL_CONTEXT_ID_SOURCES.get(context):
        return None

    metadata = metadata or {}

    if context == 'automation':
        automation_id = metadata.get('automation_id')
        return f'automation:{automation_id}' if automation_id else None

    chat_id = metadata.get('chat_id')
    if context == 'chat' and chat_id and is_saved_chat_id(chat_id):
        return f'chat:{chat_id}'
    return None


def terminal_contexts(connection: dict) -> dict:
    """Return normalized sparse context config for clients."""
    if not is_terminal_orchestrator(connection):
        return {}

    contexts = (connection.get('config') or {}).get('contexts')
    if not isinstance(contexts, dict):
        return {}

    result = {}
    for context, value in contexts.items():
        if context not in TERMINAL_CONTEXT_TYPES:
            continue
        if value is False:
            result[context] = False
        elif isinstance(value, dict):
            context_id_source = value.get('context_id')
            if context_id_source in {TERMINAL_CONTEXT_DEFAULT, TERMINAL_CONTEXT_ID_SOURCES[context]}:
                result[context] = {'context_id': context_id_source}
            else:
                result[context] = {}
    return result


def terminal_chat_uploads(connection: dict) -> str:
    """Return normalized main-chat upload behavior for this connection."""
    value = (connection.get('config') or {}).get('chat_uploads')
    return value if value in TERMINAL_CHAT_UPLOAD_MODES else 'default'


async def get_terminal_json(request, user, metadata: dict, path: str, extra_params: dict | None = None):
    """Read from an admin terminal on the backend or a personal terminal in its browser."""
    import aiohttp

    from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL, AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA
    from open_webui.models.config import Config
    from open_webui.models.groups import Groups
    from open_webui.models.users import UserModel
    from open_webui.utils.access_control import has_connection_access
    from open_webui.utils.tools import build_tool_server_headers

    metadata = metadata or {}
    terminal_id = metadata.get('terminal_id')
    if not terminal_id:
        return None

    user_model = user if isinstance(user, UserModel) else UserModel(**user)
    connections = await Config.get('terminal_server.connections', []) or []
    connection = next((item for item in connections if item.get('id') == terminal_id), None)

    if connection:
        terminal_context = 'automation' if metadata.get('automation_id') else 'chat'
        context_id = terminal_context_id(connection, metadata, terminal_context)
        config = terminal_context_config(connection, terminal_context)
        if (
            not connection.get('enabled', True)
            or not terminal_context_available(connection, terminal_context)
            or (config.get('context_id') in {'chat_id', 'automation_id'} and not context_id)
        ):
            return None
        user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user_model.id)}
        if not await has_connection_access(user_model, connection, user_group_ids):
            return None

        headers, cookies = await build_tool_server_headers(
            connection,
            request,
            user_model,
            metadata=metadata,
            extra_params=extra_params,
        )
        headers['Accept'] = 'application/json'
        headers['X-User-Id'] = user_model.id
        if metadata.get('chat_id'):
            headers['X-Session-Id'] = metadata['chat_id']
        if context_id:
            headers[TERMINAL_CONTEXT_HEADER] = context_id
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                f'{get_terminal_server_url(connection)}{path}',
                headers=headers,
                cookies=cookies,
                ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
                allow_redirects=False,
            ) as response:
                return await response.json() if response.status == 200 else None

    event_caller = (extra_params or {}).get('__event_call__')
    if event_caller:
        result = await event_caller(
            {
                'type': 'request:terminal',
                'data': {'terminal_id': terminal_id, 'path': path, 'session_id': metadata.get('session_id')},
            }
        )
        return result.get('data') if isinstance(result, dict) else None
    return None


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


async def get_terminal_skill(
    request, user, metadata: dict, skill_name: str, extra_params: dict | None = None
) -> dict | None:
    skill = await get_terminal_json(
        request, user, metadata, f'/skills/read?name={quote(skill_name, safe="")}', extra_params
    )

    if not isinstance(skill, dict):
        return None

    location = skill.get('location') or skill.get('path') or ''
    directory = location.rsplit('/', 1)[0] if '/' in location else location
    resources = skill.get('resources') if isinstance(skill.get('resources'), list) else []
    return {
        'name': skill.get('name'),
        'description': skill.get('description'),
        'content': skill.get('content'),
        'directory': directory,
        'resources': resources,
    }


def format_terminal_skill_context(skill: dict) -> str:
    resources = skill.get('resources') if isinstance(skill.get('resources'), list) else []
    parts = [f'<skill name="{skill.get("name") or ""}">', skill.get('content') or '']
    if skill.get('directory'):
        parts.append(f'<directory>{skill["directory"]}</directory>')
    if resources:
        parts.append('<resources>')
        parts.extend(f'<file>{resource}</file>' for resource in resources)
        parts.append('</resources>')
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
