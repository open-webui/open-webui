"""Read native conversation state from signed, server-persisted chat messages."""

import hashlib
import re
from urllib.parse import quote

from open_webui.models.chats import ChatModel, Chats
from open_webui.utils.auth import decode_token


def model_id(state):
    model = re.sub(r'[^a-zA-Z0-9_-]+', '-', state['model']).strip('-')
    if model != state['model']:
        # Keeps CLI model names apart that only differ in the replaced characters.
        model = f'{model}-{hashlib.sha256(state["model"].encode()).hexdigest()[:8]}'
    return f'agent:{quote(state["terminal_id"], safe="")}:{state["provider"]}:{model}'


async def ensure_chat_selections(chat):
    if all(key in (chat.chat or {}) for key in ('models', 'terminal_id', 'working_directory')):
        return chat
    state = await get_session(chat)
    if not state:
        return chat
    async with Chats._chat_transaction(chat.id) as (_, row):
        if row is None:
            return chat
        # Check missing fields under the lock so concurrent selection changes win.
        data = dict(row.chat or {})
        data.setdefault('models', [model_id(state)])
        data.setdefault('terminal_id', state['terminal_id'])
        if data['terminal_id'] == state['terminal_id']:
            data.setdefault('working_directory', state['cwd'])
        row.chat = data
        chat = ChatModel.model_validate(row)
    return chat


async def get_session(chat, message_id=None):
    message_id = (
        message_id or getattr(chat, 'current_message_id', None) or (chat.chat or {}).get('history', {}).get('currentId')
    )
    if not message_id:
        return None
    messages = await Chats.get_messages_map_by_chat_id(chat.id) or {}
    visited = set()
    while message_id and message_id not in visited:
        visited.add(message_id)
        message = messages.get(message_id)
        if not message:
            return None
        token = (message.get('meta') or {}).get('agent')
        if token:
            state = decode_token(token) if isinstance(token, str) else None
            if state and state.get('purpose') == 'terminal-agent':
                if state.get('chat') != chat.id:
                    return None  # Forks and clones start independent native conversations.
                if all(
                    isinstance(state.get(key), str) and state[key]
                    for key in ('terminal_id', 'provider', 'model', 'cwd', 'user')
                ):
                    return state
        message_id = message.get('parentId')
    return None
