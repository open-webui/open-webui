import re

USER_MENTION_ID_PATTERN = re.compile(r'<@U:([^|>]+)(?:\|[^>]*)?>')


def extract_mentions(message: str, triggerChar: str = '@'):
    # Escape triggerChar in case it's a regex special character
    triggerChar = re.escape(triggerChar)
    pattern = rf'<{triggerChar}([A-Z]):([^|>]+)'

    matches = re.findall(pattern, message)
    return [{'id_type': id_type, 'id': id_value} for id_type, id_value in matches]


def extract_user_mention_ids(message: str, sender_id: str, allowed_user_ids: set[str]) -> list[str]:
    """Return unique, authorized IDs from persisted encoded U mentions."""
    mentioned_ids = set(USER_MENTION_ID_PATTERN.findall(message))
    mentioned_ids.discard(sender_id)
    return sorted(mentioned_ids.intersection(allowed_user_ids))


def contains_user_mentions(message: str) -> bool:
    """Return whether a message contains at least one encoded user mention."""
    return USER_MENTION_ID_PATTERN.search(message) is not None


def replace_mentions(message: str, triggerChar: str = '@', use_label: bool = True):
    """
    Replace mentions in the message with either their label (after the pipe `|`)
    or their id if no label exists.

    Example:
      "<@M:gpt-4.1|GPT-4>" -> "GPT-4"   (if use_label=True)
      "<@M:gpt-4.1|GPT-4>" -> "gpt-4.1" (if use_label=False)
    """
    # Escape triggerChar
    triggerChar = re.escape(triggerChar)

    def replacer(match):
        id_type, id_value, label = match.groups()
        return label if use_label and label else id_value

    # Regex captures: idType, id, optional label
    pattern = rf'<{triggerChar}([A-Z]):([^|>]+)(?:\|([^>]+))?>'
    return re.sub(pattern, replacer, message)
