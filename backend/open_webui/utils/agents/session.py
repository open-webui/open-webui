"""Read native conversation state from signed, server-persisted chat messages."""

from urllib.parse import quote

from open_webui.models.chats import Chats
from open_webui.utils.auth import decode_token


def model_id(state):
    return f'agent:{quote(state["terminal_id"], safe="")}:{state["provider"]}:{quote(state["model"], safe="")}'


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
