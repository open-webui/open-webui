from open_webui.utils.chat_history import (
    MESSAGE_LOADED_KEY,
    build_window_chat,
    create_message_window,
    has_embedded_messages,
    hydrate_chat,
    merge_compact_chat,
    prepare_messages_for_storage,
    split_chat_messages,
)


def message(message_id, parent_id, content):
    return {
        'id': message_id,
        'parentId': parent_id,
        'childrenIds': [],
        'role': 'user',
        'content': content,
        'customField': {'kept': True},
    }


def test_split_and_hydrate_preserve_arbitrary_message_fields():
    original = {
        'title': 'chat',
        'history': {
            'currentId': 'child',
            'messages': {
                'root': message('root', None, 'one'),
                'child': message('child', 'root', 'two'),
            },
        },
    }

    compact, messages = split_chat_messages(original)

    assert 'messages' not in compact['history']
    assert messages['child']['customField'] == {'kept': True}
    assert hydrate_chat(compact, messages)['messages'][1]['id'] == 'child'
    assert original['history']['messages']['child']['content'] == 'two'


def test_embedded_message_presence_distinguishes_empty_legacy_from_compact_chat():
    assert has_embedded_messages({'history': {'messages': {}}}) is True
    assert has_embedded_messages({'messages': []}) is True
    assert has_embedded_messages({'history': {'messageStorage': {'version': 1}}}) is False


def test_merge_compact_chat_only_returns_incoming_messages():
    existing = {
        'title': 'old',
        'history': {'currentId': 'old', 'messages': {'old': message('old', None, 'old')}},
    }
    incoming = {
        'title': 'new',
        'history': {'currentId': 'new', 'messages': {'new': message('new', 'old', 'new')}},
    }

    compact, messages = merge_compact_chat(existing, incoming)

    assert compact['title'] == 'new'
    assert compact['history']['currentId'] == 'new'
    assert 'messages' not in compact['history']
    assert set(messages) == {'new'}


def test_window_contains_topology_stubs_and_loaded_bodies():
    topology = {
        'root': {'id': 'root', 'parentId': None, 'childrenIds': ['child'], 'role': 'user', 'timestamp': 1},
        'child': {'id': 'child', 'parentId': 'root', 'childrenIds': [], 'role': 'user', 'timestamp': 2},
    }
    loaded = {'child': message('child', 'root', 'body')}

    result = build_window_chat(
        {'history': {'currentId': 'child'}},
        topology,
        loaded,
        ['child'],
        True,
        1,
    )

    assert result['history']['messages']['root'][MESSAGE_LOADED_KEY] is False
    assert result['history']['messages']['child'][MESSAGE_LOADED_KEY] is True
    assert result['history']['messages']['child']['content'] == 'body'
    assert result['history']['messageWindow']['hasMore'] is True


def test_storage_preparation_removes_internal_marker_without_mutation():
    messages = {'id': {**message('id', None, 'body'), MESSAGE_LOADED_KEY: True}}

    prepared = prepare_messages_for_storage(messages)

    assert MESSAGE_LOADED_KEY not in prepared['id']
    assert messages['id'][MESSAGE_LOADED_KEY] is True


def test_legacy_window_uses_parent_chain_and_before_cursor():
    messages = {
        'root': message('root', None, 'root'),
        'middle': message('middle', 'root', 'middle'),
        'leaf': message('leaf', 'middle', 'leaf'),
        'sibling': message('sibling', 'root', 'sibling'),
    }

    window = create_message_window(messages, 'leaf', limit=1, before_id='leaf')

    assert window['loaded_ids'] == ['middle']
    assert window['has_more'] is True
    assert set(window['topology']) == set(messages)
