from copy import deepcopy


def build_fork_history(messages_map: dict, source_message_id: str) -> tuple[dict, list[dict]]:
    if not messages_map:
        raise ValueError('chat has no messages to fork')

    branch: list[tuple[str, dict]] = []
    seen: set[str] = set()
    message_id = source_message_id

    while message_id:
        if message_id in seen:
            raise ValueError('message branch contains a cycle')
        seen.add(message_id)

        message = messages_map.get(message_id)
        if not isinstance(message, dict):
            raise ValueError('message not found')

        branch.append((message_id, message))
        message_id = message.get('parentId')

    fork_messages: dict[str, dict] = {}
    ordered_messages: list[dict] = []
    parent_id = None

    for message_id, message in reversed(branch):
        copied = deepcopy(message)
        copied['id'] = message_id
        copied['parentId'] = parent_id
        copied['childrenIds'] = []

        if parent_id:
            fork_messages[parent_id]['childrenIds'] = [message_id]

        fork_messages[message_id] = copied
        ordered_messages.append(copied)
        parent_id = message_id

    return {'messages': fork_messages, 'currentId': source_message_id}, ordered_messages
