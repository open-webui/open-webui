from __future__ import annotations

from copy import deepcopy
from typing import Any

MESSAGE_STORAGE_VERSION = 1
MESSAGE_STORAGE_KEY = 'messageStorage'
MESSAGE_WINDOW_KEY = 'messageWindow'
MESSAGE_LOADED_KEY = '__loaded'
TOPOLOGY_KEYS = (
    'id',
    'parentId',
    'childrenIds',
    'role',
    'timestamp',
    'model',
    'modelIdx',
    'modelName',
    'models',
    'done',
)


def _message_map(value: Any) -> dict[str, dict]:
    if isinstance(value, dict):
        return {str(message_id): message for message_id, message in value.items() if isinstance(message, dict)}

    if isinstance(value, list):
        return {str(message['id']): message for message in value if isinstance(message, dict) and message.get('id')}

    return {}


def has_embedded_messages(chat: dict | None) -> bool:
    if not isinstance(chat, dict):
        return False
    history = chat.get('history')
    return (isinstance(history, dict) and 'messages' in history) or 'messages' in chat


def uses_normalized_message_storage(chat: dict | None) -> bool:
    if not isinstance(chat, dict):
        return False
    history = chat.get('history')
    storage = history.get(MESSAGE_STORAGE_KEY) if isinstance(history, dict) else None
    return isinstance(storage, dict) and storage.get('version') == MESSAGE_STORAGE_VERSION


def prepare_messages_for_storage(messages: Any) -> dict[str, dict]:
    """Return lossless message copies without response-only window markers."""
    prepared: dict[str, dict] = {}
    for message_id, message in _message_map(messages).items():
        clean_message = deepcopy(message)
        clean_message.pop(MESSAGE_LOADED_KEY, None)
        clean_message.setdefault('id', message_id)
        prepared[message_id] = clean_message
    return prepared


def copy_chat_without_messages(chat: dict | None) -> dict:
    """Copy chat metadata without adding storage-specific response markers."""
    compact = deepcopy(chat or {})
    history = compact.get('history')
    if not isinstance(history, dict):
        history = {}
    else:
        history = deepcopy(history)

    history.pop('messages', None)
    history.pop(MESSAGE_WINDOW_KEY, None)
    compact.pop('messages', None)
    compact['history'] = history
    return compact


def split_chat_messages(chat: dict | None) -> tuple[dict, dict[str, dict]]:
    """Separate embedded messages from compact chat metadata."""
    source = deepcopy(chat or {})
    source_history = source.get('history') if isinstance(source.get('history'), dict) else {}
    messages = _message_map(source_history.get('messages'))
    top_level_messages = source.get('messages')
    if not messages:
        messages = _message_map(top_level_messages)

    compact = copy_chat_without_messages(source)
    history = compact['history']
    history[MESSAGE_STORAGE_KEY] = {'version': MESSAGE_STORAGE_VERSION}
    return compact, prepare_messages_for_storage(messages)


def merge_compact_chat(existing: dict | None, incoming: dict | None) -> tuple[dict, dict[str, dict]]:
    """Merge chat metadata while returning only messages supplied by the caller."""
    existing_compact, _ = split_chat_messages(existing)
    incoming_compact, incoming_messages = split_chat_messages(incoming)

    merged = {**existing_compact, **incoming_compact}
    existing_history = existing_compact.get('history') or {}
    incoming_history = incoming_compact.get('history') or {}
    merged['history'] = {**existing_history, **incoming_history}
    merged['history'][MESSAGE_STORAGE_KEY] = {'version': MESSAGE_STORAGE_VERSION}
    return merged, incoming_messages


def create_message_list(messages: dict[str, dict], current_id: str | None) -> list[dict]:
    message_list: list[dict] = []
    visited: set[str] = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        message = messages.get(current_id)
        if not isinstance(message, dict):
            break
        message_list.append(message)
        current_id = message.get('parentId')

    message_list.reverse()
    return message_list


def create_message_window(
    messages: dict[str, dict],
    current_id: str | None,
    limit: int,
    before_id: str | None = None,
) -> dict:
    """Create a branch window from a legacy in-memory message map."""
    if limit < 1:
        raise ValueError('limit must be at least 1')

    clean_messages = prepare_messages_for_storage(messages)
    if current_id is not None and current_id not in clean_messages:
        raise ValueError('current_id does not exist in this chat')

    topology = {
        message_id: {key: message[key] for key in TOPOLOGY_KEYS if key in message}
        for message_id, message in clean_messages.items()
    }

    branch_ids = [message.get('id') for message in create_message_list(clean_messages, current_id) if message.get('id')]
    if before_id is not None:
        if before_id not in branch_ids:
            raise ValueError('before_id is not an ancestor of current_id')
        branch_ids = branch_ids[: branch_ids.index(before_id)]

    loaded_ids = branch_ids[-limit:]
    return {
        'topology': topology,
        'messages': {message_id: clean_messages[message_id] for message_id in loaded_ids},
        'loaded_ids': loaded_ids,
        'has_more': len(branch_ids) > len(loaded_ids),
        'current_id': current_id,
    }


def hydrate_chat(chat: dict | None, messages: dict[str, dict]) -> dict:
    """Rebuild the legacy full-chat shape for compatibility endpoints."""
    hydrated, _ = split_chat_messages(chat)
    history = hydrated.setdefault('history', {})
    clean_messages = prepare_messages_for_storage(messages)
    history['messages'] = clean_messages
    hydrated['messages'] = create_message_list(clean_messages, history.get('currentId'))
    return hydrated


def build_window_chat(
    chat: dict | None,
    topology: dict[str, dict],
    loaded_messages: dict[str, dict],
    loaded_ids: list[str],
    has_more: bool,
    limit: int,
    current_id: str | None = None,
) -> dict:
    """Build a response containing full topology and only a window of message bodies."""
    window_chat = copy_chat_without_messages(chat)
    history = window_chat.setdefault('history', {})
    if current_id is not None:
        history['currentId'] = current_id

    clean_loaded = prepare_messages_for_storage(loaded_messages)
    messages: dict[str, dict] = {}

    for message_id, topology_message in topology.items():
        topology_copy = deepcopy(topology_message)
        if message_id in clean_loaded:
            messages[message_id] = {
                **clean_loaded[message_id],
                **topology_copy,
                MESSAGE_LOADED_KEY: True,
            }
        else:
            messages[message_id] = {
                **topology_copy,
                MESSAGE_LOADED_KEY: False,
            }

    for message_id, message in clean_loaded.items():
        if message_id not in messages:
            messages[message_id] = {**message, MESSAGE_LOADED_KEY: True}

    unique_loaded_ids = list(dict.fromkeys(loaded_ids))
    history['messages'] = messages
    history[MESSAGE_WINDOW_KEY] = {
        'loadedIds': [message_id for message_id in unique_loaded_ids if message_id in messages],
        'hasMore': has_more,
        'limit': limit,
    }
    return window_chat


def inline_message_images_from_files(messages: list[dict]) -> list[dict]:
    """Move attached images into message content and remove storage-only files."""
    for message in messages:
        raw_files = message.get('files')
        files = raw_files if isinstance(raw_files, list) else []
        image_files = [
            file
            for file in files
            if isinstance(file, dict)
            and (file.get('type') == 'image' or (file.get('content_type') or '').startswith('image/'))
        ]
        if message.get('role') == 'user' and image_files:
            text_content = message.get('content', '')
            if isinstance(text_content, str):
                message['content'] = [
                    {'type': 'text', 'text': text_content},
                    *[
                        {
                            'type': 'image_url',
                            'image_url': {'url': file['url']},
                        }
                        for file in image_files
                        if file.get('url')
                    ],
                ]
        message.pop('files', None)

    return messages
