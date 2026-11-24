from uuid import UUID

TEMPORARY_CHAT_ID_PREFIX = 'temporary:'
LEGACY_TEMPORARY_CHAT_ID_PREFIX = 'local:'  # Legacy temporary chat prefix.
CHANNEL_CHAT_ID_PREFIX = 'channel:'
FOLDER_SESSION_ID_PREFIX = 'folder:'  # A person's panels in a folder; not a chat.

TEMPORARY_CHAT_ID_PREFIXES = (
    TEMPORARY_CHAT_ID_PREFIX,
    LEGACY_TEMPORARY_CHAT_ID_PREFIX,
)
NON_SAVED_CHAT_ID_PREFIXES = (*TEMPORARY_CHAT_ID_PREFIXES, CHANNEL_CHAT_ID_PREFIX, FOLDER_SESSION_ID_PREFIX)


def is_saved_chat_id(chat_id: str | None) -> bool:
    return bool(chat_id) and not chat_id.startswith(NON_SAVED_CHAT_ID_PREFIXES)


def is_temporary_chat_id(chat_id: str | None) -> bool:
    return bool(chat_id) and chat_id.startswith(TEMPORARY_CHAT_ID_PREFIXES)


def get_temporary_chat_session_id(chat_id: str) -> str | None:
    for prefix in TEMPORARY_CHAT_ID_PREFIXES:
        if chat_id.startswith(prefix):
            value = chat_id.removeprefix(prefix)
            session_id, separator, conversation_id = value.partition(':')
            if not session_id:
                return None
            if separator:
                try:
                    if str(UUID(conversation_id)) != conversation_id:
                        return None
                except ValueError:
                    return None
            return session_id
    return None


def folder_session_id(folder_id: str, user_id: str) -> str:
    return f'{FOLDER_SESSION_ID_PREFIX}{folder_id}:{user_id}'


def get_folder_id_of_session(session_id: str | None, user_id: str) -> str | None:
    """The folder of a person's folder session id; None when it is not theirs."""
    if not session_id or not session_id.startswith(FOLDER_SESSION_ID_PREFIX):
        return None
    folder_id, _, owner_id = session_id.removeprefix(FOLDER_SESSION_ID_PREFIX).rpartition(':')
    return folder_id if folder_id and owner_id == user_id else None
