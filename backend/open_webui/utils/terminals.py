"""Shared routing helpers for admin-configured terminal servers."""

from urllib.parse import quote

from open_webui.utils.chat_id import is_saved_chat_id

TERMINAL_CONTEXT_HEADER = 'X-Terminal-Context-Id'
TERMINAL_CONTEXT_DEFAULT = 'default'
TERMINAL_CONTEXT_TYPES = {'chat', 'automation'}
TERMINAL_CONTEXT_ID_SOURCES = {'chat': 'chat_id', 'automation': 'automation_id'}
TERMINAL_CHAT_UPLOAD_MODES = {'default', 'filesystem'}


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
