import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from open_webui.utils import middleware, tool_approval
from open_webui.utils.tool_approval import (
    assign_tool_approval_statuses,
    get_resolved_call_ids,
    has_unapproved_tool_call,
    is_paused_for_tool_approval,
)


CHAT_ID = 'tool-approval-chat'
MESSAGE_ID = 'tool-approval-message'


def function_call(call_id, name='search', arguments='{}', status='completed'):
    return {
        'type': 'function_call',
        'id': call_id,
        'call_id': call_id,
        'name': name,
        'arguments': arguments,
        'status': status,
    }


def function_output(call_id, text, status='completed'):
    return {
        'type': 'function_call_output',
        'id': f'fco_{call_id}',
        'call_id': call_id,
        'output': [{'type': 'input_text', 'text': text}],
        'status': status,
    }


def call_statuses(output):
    return {item['call_id']: item['status'] for item in output if item.get('type') == 'function_call'}


def results_by_call_id(output):
    return {
        item['call_id']: ''.join(part.get('text', '') for part in item.get('output', []))
        for item in output
        if item.get('type') == 'function_call_output'
    }


def metadata():
    return {
        'chat_id': CHAT_ID,
        'message_id': MESSAGE_ID,
        'assistant_message_id': MESSAGE_ID,
        'params': {'tool_approval_mode': 'ask'},
    }


@pytest.fixture
def state(monkeypatch):
    state = {'message': None, 'writes': []}
    chat = SimpleNamespace(user_id='test-user', variables=None, chat={})

    async def get_chat(chat_id, db=None):
        assert chat_id == CHAT_ID
        return chat

    async def get_message(chat_id, message_id):
        assert (chat_id, message_id) == (CHAT_ID, MESSAGE_ID)
        return state['message']

    async def upsert(chat_id, message_id, patch, *, touch=True):
        assert (chat_id, message_id) == (CHAT_ID, MESSAGE_ID)
        state['writes'].append(patch)
        state['message'] = {**(state['message'] or {}), **patch}
        return state['message']

    async def no_messages(*args, **kwargs):
        return None

    async def no_filters(*args, **kwargs):
        return []

    async def emitter_pair(metadata):
        async def emit(event):
            return None

        return emit, None

    monkeypatch.setattr(middleware.Chats, 'get_chat_by_id', get_chat)
    monkeypatch.setattr(middleware.Chats, 'get_message_by_id_and_message_id', get_message)
    monkeypatch.setattr(middleware.Chats, 'upsert_message_to_chat_by_id_and_message_id', upsert)
    monkeypatch.setattr(middleware, 'load_messages_from_db', no_messages)
    monkeypatch.setattr(middleware, 'get_filter_functions', no_filters)
    monkeypatch.setattr(middleware, 'get_event_emitter_and_caller', emitter_pair)
    monkeypatch.setattr(tool_approval, 'get_event_emitter', AsyncMock(return_value=None))
    return state


async def arm(state, calls):
    state['message'] = {'id': MESSAGE_ID, 'output': calls}
    await middleware.pause_for_tool_approval(CHAT_ID, MESSAGE_ID, calls, {'messages': []}, metadata())


async def resolve(state, call_id, action='approve', *, timed_out=False):
    return await tool_approval.resolve_tool_call_output(
        CHAT_ID,
        MESSAGE_ID,
        tool_approval.ResolveToolCallForm(call_id=call_id, action=action, timed_out=timed_out),
        SimpleNamespace(id='test-user', role='user'),
    )


async def drain(state, monkeypatch, results, executed):
    async def execute(request, form_data, user, metadata, event_caller, event_emitter, tool_call):
        call_id = tool_call['id']
        executed.append(
            {
                'call_id': call_id,
                'name': tool_call['function']['name'],
                'arguments': tool_call['function']['arguments'],
            }
        )
        return {'tool_call_id': call_id, 'content': results[call_id]}

    monkeypatch.setattr(middleware, 'execute_tool_call_for_output', execute)
    return await middleware.drain_approved_tool_calls(
        request=None,
        form_data={'messages': []},
        user=None,
        model={'id': 'test-model'},
        metadata=metadata(),
    )


def test_arms_each_unresolved_call_by_call_id():
    output = [
        function_call('call-a', arguments='{"query":"a"}'),
        function_call('call-b', arguments='{"query":"b"}'),
        function_call('call-c', 'fetch'),
    ]

    assign_tool_approval_statuses(output)

    assert call_statuses(output) == {
        'call-a': 'pending',
        'call-b': 'queued',
        'call-c': 'queued',
    }
    assert has_unapproved_tool_call(output)
    assert is_paused_for_tool_approval(output)


def test_preserves_resolved_and_terminal_calls():
    output = [
        function_call('call-done'),
        function_output('call-done', 'done'),
        function_call('call-rejected', status='rejected'),
        function_call('call-failed', status='failed'),
        function_call('call-next'),
    ]

    assign_tool_approval_statuses(output)

    assert call_statuses(output) == {
        'call-done': 'completed',
        'call-rejected': 'rejected',
        'call-failed': 'failed',
        'call-next': 'pending',
    }
    assert get_resolved_call_ids(output) == {'call-done'}


@pytest.mark.asyncio
async def test_repeated_names_finish_with_correct_arguments_and_results(monkeypatch, state):
    calls = [
        function_call('call-a', arguments='{"query":"a"}'),
        function_call('call-b', arguments='{"query":"b"}'),
        function_call('call-c', arguments='{"query":"c"}'),
    ]
    await arm(state, calls)
    executed = []
    results = {'call-a': 'result-a', 'call-b': 'result-b', 'call-c': 'result-c'}

    for index, call_id in enumerate(results):
        await resolve(state, call_id)
        assert await drain(state, monkeypatch, results, executed) is (index < 2)

    assert call_statuses(state['message']['output']) == {
        'call-a': 'completed',
        'call-b': 'completed',
        'call-c': 'completed',
    }
    assert executed == [
        {'call_id': 'call-a', 'name': 'search', 'arguments': '{"query":"a"}'},
        {'call_id': 'call-b', 'name': 'search', 'arguments': '{"query":"b"}'},
        {'call_id': 'call-c', 'name': 'search', 'arguments': '{"query":"c"}'},
    ]
    assert results_by_call_id(state['message']['output']) == results


@pytest.mark.asyncio
@pytest.mark.parametrize('names', [('search',), ('search', 'fetch'), ('search', 'fetch', 'search')])
async def test_single_mixed_and_repeated_controls(names, monkeypatch, state):
    calls = [function_call(f'call-{index}', name) for index, name in enumerate(names)]
    await arm(state, calls)
    executed = []
    results = {item['call_id']: item['call_id'] for item in calls}

    for call_id in results:
        await resolve(state, call_id)
        await drain(state, monkeypatch, results, executed)

    assert [item['call_id'] for item in executed] == list(results)
    assert all(status == 'completed' for status in call_statuses(state['message']['output']).values())


@pytest.mark.asyncio
async def test_rejection_failure_and_ask_user_timeout_keep_their_semantics(monkeypatch, state):
    calls = [function_call('call-reject'), function_call('call-fail')]
    await arm(state, calls)
    assert (await resolve(state, 'call-reject', action='reject'))['paused'] is True

    executed = []
    assert await drain(state, monkeypatch, {'call-fail': 'Error: upstream failed'}, executed) is True
    await resolve(state, 'call-fail')
    assert await drain(state, monkeypatch, {'call-fail': 'Error: upstream failed'}, executed) is False
    assert call_statuses(state['message']['output']) == {
        'call-reject': 'rejected',
        'call-fail': 'failed',
    }

    ask_user = function_call('call-ask', 'ask_user', status='pending')
    state['message'] = {'id': MESSAGE_ID, 'output': [ask_user]}
    response = await resolve(state, 'call-ask', action='answer', timed_out=True)
    assert response['paused'] is False
    assert json.loads(results_by_call_id(response['output'])['call-ask']) == {
        'status': 'cancelled',
        'answers': {},
        'timed_out': True,
    }


@pytest.mark.asyncio
async def test_persisted_stale_sibling_is_rearmed_before_execution(monkeypatch, state):
    output = [
        function_call('call-a'),
        function_output('call-a', 'result-a'),
        function_call('call-b'),
    ]
    state['message'] = {'id': MESSAGE_ID, 'output': output}
    executed = []

    assert await drain(state, monkeypatch, {'call-b': 'result-b'}, executed) is True
    assert executed == []
    assert call_statuses(state['message']['output']) == {
        'call-a': 'completed',
        'call-b': 'pending',
    }
