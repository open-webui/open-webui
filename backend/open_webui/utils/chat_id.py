from typing import Optional


TEMPORARY_CHAT_ID_PREFIX = 'temporary:'
LEGACY_TEMPORARY_CHAT_ID_PREFIX = 'local:'  # Legacy temporary chat prefix.
CHANNEL_CHAT_ID_PREFIX = 'channel:'

TEMPORARY_CHAT_ID_PREFIXES = (
    TEMPORARY_CHAT_ID_PREFIX,
    LEGACY_TEMPORARY_CHAT_ID_PREFIX,
)
NON_SAVED_CHAT_ID_PREFIXES = (*TEMPORARY_CHAT_ID_PREFIXES, CHANNEL_CHAT_ID_PREFIX)


def is_saved_chat_id(chat_id: Optional[str]) -> bool:
    return bool(chat_id) and not chat_id.startswith(NON_SAVED_CHAT_ID_PREFIXES)


def is_temporary_chat_id(chat_id: Optional[str]) -> bool:
    return bool(chat_id) and chat_id.startswith(TEMPORARY_CHAT_ID_PREFIXES)


def get_temporary_chat_session_id(chat_id: str) -> Optional[str]:
    for prefix in TEMPORARY_CHAT_ID_PREFIXES:
        if chat_id.startswith(prefix):
            return chat_id.removeprefix(prefix)
    return None
