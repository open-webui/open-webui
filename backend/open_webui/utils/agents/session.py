"""Read native conversation state from signed, server-persisted chat messages."""

import hashlib
import re
from urllib.parse import quote

from open_webui.utils.machines import normalize_machine_id
from open_webui.models.chat_messages import ChatMessages
from open_webui.models.chats import Chats
from open_webui.utils.auth import decode_token


def model_id(state):
    model = re.sub(r'[^a-zA-Z0-9_-]+', '-', state['model']).strip('-')
    if model != state['model']:
        # Keeps CLI model names apart that only differ in the replaced characters.
        model = f'{model}-{hashlib.sha256(state["model"].encode()).hexdigest()[:8]}'
    return f'agent:{quote(state["machine_id"], safe="")}:{state["provider"]}:{model}'


async def ensure_chat_selections(chat):
    data = normalize_machine_id(dict(chat.chat or {}))
    if all(key in data for key in ('models', 'machine_id', 'working_directory')):
        return chat
    state = await get_session(chat)
    if not state:
        return chat
    async with Chats._chat_transaction(chat.id) as (_, row):
        if row is None:
            return chat
        # Check missing fields under the lock so concurrent selection changes win.
        data = normalize_machine_id(dict(row.chat or {}))
        data.setdefault('models', [model_id(state)])
        data.setdefault('machine_id', state['machine_id'])
        if data['machine_id'] == state['machine_id']:
            data.setdefault('working_directory', state['cwd'])
        row.chat = data
        chat = chat.model_copy(update={'chat': {**(chat.chat or {}), **data}})
    return chat


def _state(message):
    token = (message.get('meta') or {}).get('agent')
    state = decode_token(token) if isinstance(token, str) else None
    return normalize_machine_id(state) if state and state.get('typ') == 'agent_session' else None


def _find(chat, messages, message_id, user_id=None):
    """The nearest saved native conversation above `message_id`.

    A fork or clone copies its source's messages, and their conversations belong to that chat. With `user_id`,
    those owned by this user are returned for the fork to copy; otherwise the copied messages end the search.
    """
    visited = set()
    while message_id and message_id not in visited:
        visited.add(message_id)
        message = messages.get(message_id)
        if not message:
            return None, None
        state = _state(message)
        if state:
            if state.get('chat') != chat.id and (
                not user_id or (state.get('instance_user_id') or state.get('user')) != user_id
            ):
                return None, None
            if all(
                isinstance(state.get(key), str) and state[key]
                for key in ('machine_id', 'provider', 'model', 'cwd', 'user')
            ):
                return state, message_id
        message_id = message.get('parentId')
    return None, None


async def get_session(chat, message_id=None):
    message_id = (
        message_id or getattr(chat, 'current_message_id', None) or (chat.chat or {}).get('history', {}).get('currentId')
    )
    if not message_id:
        return None
    messages = await ChatMessages.get_message_metadata_map_by_chat_id(chat.id) or {}
    return _find(chat, messages, message_id)[0]


async def get_resume_point(chat, message_id, user_id, exclude=None):
    """The native conversation to continue from `message_id`, whether later turns were added to it, and
    whether it belongs to the chat this one was forked or cloned from.

    Regenerating or editing an earlier message reaches a reply whose native conversation already holds
    the turns that came after it; that conversation then continues from the reply instead of its latest turn.
    A forked chat continues from a copy, so the two chats never write to the same conversation.
    """
    messages = await Chats.get_messages_map_by_chat_id(chat.id) or {}
    state, found_id = _find(chat, messages, message_id, user_id)
    if state is None or not state.get('session_id'):
        return state, False, False
    copied = state['chat'] != chat.id
    if copied:
        # Its later turns, if any, are in the source chat. A deleted source can't say, so assume there were.
        messages = await Chats.get_messages_map_by_chat_id(state['chat'])
        if not messages or found_id not in messages:
            return state, True, True
    timestamp = messages[found_id].get('timestamp') or 0
    for other_id, other in messages.items():
        if other_id in (found_id, exclude) or (other.get('timestamp') or 0) < timestamp:
            continue
        other_state = _state(other)
        if (
            other_state
            and other_state.get('chat') == state['chat']
            and other_state.get('session_id') == state['session_id']
            and other_state.get('provider') == state.get('provider')
            and other_state.get('machine_id') == state.get('machine_id')
        ):
            return state, True, copied
    return state, False, copied
