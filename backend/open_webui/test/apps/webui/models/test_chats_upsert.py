"""Regression tests for the chat-history graph repair in
``apply_message_upsert`` / ``build_chat_message_payload`` (PR #24617).

Pure functions, no DB, so the failure modes that bricked production chats
are locked down deterministically.
"""

from open_webui.models.chats import apply_message_upsert, build_chat_message_payload

NOW = 1_700_000_000


def test_missing_node_partial_payload_gets_full_invariants():
    history = {}
    node = apply_message_upsert(history, 'a', {'content': 'hi', 'done': True}, NOW)
    assert node['id'] == 'a'
    assert node['parentId'] is None
    assert node['childrenIds'] == []
    assert node['role'] == 'assistant'
    assert node['timestamp'] == NOW
    assert history['currentId'] == 'a'
    assert history['messages']['a'] is node


def test_existing_node_partial_update_preserves_structural_fields():
    history = {
        'messages': {
            'a': {
                'id': 'a',
                'parentId': 'u1',
                'childrenIds': ['c1'],
                'role': 'assistant',
                'timestamp': 111,
                'content': 'old',
            }
        },
        'currentId': 'a',
    }
    apply_message_upsert(history, 'a', {'content': 'new', 'done': True}, NOW)
    n = history['messages']['a']
    assert n['parentId'] == 'u1'
    assert n['childrenIds'] == ['c1']
    assert n['timestamp'] == 111
    assert n['role'] == 'assistant'
    assert n['content'] == 'new'


def test_explicit_falsy_values_win_over_existing():
    history = {
        'messages': {
            'a': {
                'id': 'a',
                'parentId': 'u1',
                'childrenIds': ['c1'],
                'role': 'assistant',
                'timestamp': 111,
            }
        }
    }
    apply_message_upsert(history, 'a', {'parentId': None, 'childrenIds': []}, NOW)
    n = history['messages']['a']
    assert n['parentId'] is None
    assert n['childrenIds'] == []


def test_parent_child_link_repaired_and_malformed_children_normalized():
    history = {
        'messages': {'u1': {'id': 'u1', 'parentId': None, 'childrenIds': None, 'role': 'user'}},
        'currentId': 'u1',
    }
    apply_message_upsert(history, 'a', {'parentId': 'u1', 'role': 'assistant'}, NOW)
    assert history['messages']['u1']['childrenIds'] == ['a']


def test_malformed_messages_container_replaced():
    for bad in (None, [], 'x', 3):
        history = {'messages': bad}
        apply_message_upsert(history, 'a', {'content': 'x'}, NOW)
        assert isinstance(history['messages'], dict)
        assert history['messages']['a']['id'] == 'a'


def test_malformed_existing_node_synthesized_not_crash():
    for bad in ([], 'x', 3, True):
        history = {'messages': {'a': bad}, 'currentId': 'a'}
        node = apply_message_upsert(history, 'a', {'content': 'x'}, NOW)
        assert node['id'] == 'a'
        assert node['role'] == 'assistant'


def test_dangling_parent_logged_not_severed():
    history = {'messages': {}, 'currentId': None}
    node = apply_message_upsert(history, 'a', {'parentId': 'missing', 'role': 'assistant'}, NOW)
    # The parent may still exist in chat_message; the link must be preserved.
    assert node['parentId'] == 'missing'


def test_non_str_parentid_coerced_to_none():
    history = {}
    node = apply_message_upsert(history, 'a', {'parentId': ['x'], 'role': 'assistant'}, NOW)
    assert node['parentId'] is None


def test_build_payload_sends_parent_id_only_when_known():
    assert build_chat_message_payload({'id': 'a', 'parentId': 'u1'})['parent_id'] == 'u1'
    assert 'parent_id' not in build_chat_message_payload({'id': 'a', 'parentId': None})
