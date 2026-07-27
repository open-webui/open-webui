from typing import Optional


NON_SAVED_CHAT_ID_PREFIXES = ('local:', 'channel:')


def is_saved_chat_id(chat_id: Optional[str]) -> bool:
    return bool(chat_id) and not chat_id.startswith(NON_SAVED_CHAT_ID_PREFIXES)
