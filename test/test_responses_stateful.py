import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope='module')
def responses_state():
    """Load the dependency-free production module without booting OpenWebUI."""
    source = Path(__file__).parents[1] / 'backend/open_webui/utils/responses_state.py'
    spec = importlib.util.spec_from_file_location('open_webui_responses_state', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_response_id_follows_the_selected_branch(responses_state):
    messages = {
        'assistant-a': {'role': 'assistant', 'model': 'hermes', 'responseId': 'resp_branch_a'},
        'assistant-b': {'role': 'assistant', 'model': 'hermes', 'responseId': 'resp_branch_b'},
        'user-a': {'role': 'user', 'parentId': 'assistant-a'},
        'user-b': {'role': 'user', 'parentId': 'assistant-b'},
    }

    assert responses_state.get_stateful_response_id(messages, 'user-a', 'hermes') == 'resp_branch_a'
    assert responses_state.get_stateful_response_id(messages, 'user-b', 'hermes') == 'resp_branch_b'


def test_response_id_accepts_normalized_database_key(responses_state):
    messages = {
        'assistant': {'role': 'assistant', 'model': 'hermes', 'response_id': 'resp_from_database'},
        'user': {'role': 'user', 'parentId': 'assistant'},
    }

    assert responses_state.get_stateful_response_id(messages, 'user', 'hermes') == 'resp_from_database'


def test_response_id_is_not_reused_after_model_switch(responses_state):
    messages = {
        'assistant': {'role': 'assistant', 'model': 'hermes', 'responseId': 'resp_hermes'},
        'user': {'role': 'user', 'parentId': 'assistant'},
    }

    assert responses_state.get_stateful_response_id(messages, 'user', 'other-model') is None


@pytest.mark.parametrize(
    ('messages', 'user_message_id'),
    [
        ({}, 'user'),
        ({'user': {'role': 'assistant'}}, 'user'),
        ({'user': {'role': 'user', 'parentId': 'missing'}}, 'user'),
        ({'assistant': {'role': 'user'}, 'user': {'role': 'user', 'parentId': 'assistant'}}, 'user'),
        (
            {
                'assistant': {'role': 'assistant', 'model': 'hermes'},
                'user': {'role': 'user', 'parentId': 'assistant'},
            },
            'user',
        ),
    ],
)
def test_response_id_rejects_incomplete_message_chains(responses_state, messages, user_message_id):
    assert responses_state.get_stateful_response_id(messages, user_message_id, 'hermes') is None


def test_openai_connection_is_resolved_for_base_model_and_profile(responses_state):
    models = {'hermes-base': {'urlIdx': 7}}

    assert responses_state.get_openai_url_idx(models['hermes-base'], models) == 7
    assert (
        responses_state.get_openai_url_idx(
            {'id': 'hermes-profile', 'info': {'base_model_id': 'hermes-base'}},
            models,
        )
        == 7
    )


def test_openai_connection_rejects_models_without_a_connection(responses_state):
    assert responses_state.get_openai_url_idx({}, {}) is None
    assert responses_state.get_openai_url_idx({'info': {'base_model_id': 'missing'}}, {}) is None


def test_responses_payload_keeps_anchor_and_enables_storage(responses_state):
    payload = {
        'messages': [{'role': 'user', 'content': 'Next turn'}],
        'previous_response_id': 'resp_hermes_1',
    }

    result = responses_state.apply_responses_stateful_payload(payload, is_responses=True, enabled=True)

    assert result['previous_response_id'] == 'resp_hermes_1'
    assert result['store'] is True


def test_chat_completions_payload_drops_stateful_anchor(responses_state):
    payload = {
        'messages': [{'role': 'user', 'content': 'Next turn'}],
        'previous_response_id': 'resp_from_old_connection',
    }

    result = responses_state.apply_responses_stateful_payload(payload, is_responses=False, enabled=True)

    assert 'previous_response_id' not in result
    assert 'store' not in result


def test_disabled_stateful_mode_does_not_force_storage(responses_state):
    payload = {'messages': [{'role': 'user', 'content': 'Next turn'}]}

    result = responses_state.apply_responses_stateful_payload(payload, is_responses=True, enabled=False)

    assert 'store' not in result


def test_stateful_messages_keep_system_and_current_user_only(responses_state):
    system = {'role': 'system', 'content': 'Instructions'}
    current_user = {'role': 'user', 'content': 'Current'}
    messages = [
        system,
        {'role': 'user', 'content': 'Previous'},
        {'role': 'assistant', 'content': 'Previous answer'},
        current_user,
    ]

    assert responses_state.trim_stateful_messages(messages) == [system, current_user]


def test_guided_regeneration_keeps_original_and_regeneration_prompts(responses_state):
    original = {'role': 'user', 'content': 'Original'}
    regeneration = {'role': 'user', 'content': 'Try another way'}

    assert responses_state.trim_stateful_messages(
        [original, {'role': 'assistant', 'content': 'Old answer'}, regeneration],
        regeneration=True,
    ) == [original, regeneration]


def test_streaming_completion_metadata_exposes_response_id(responses_state):
    usage = {'input_tokens': 10, 'output_tokens': 4}

    metadata = responses_state.get_completed_response_metadata({'id': 'resp_stream', 'usage': usage})

    assert metadata == {'usage': usage, 'done': True, 'response_id': 'resp_stream'}
    assert responses_state.pop_stateful_response_id(metadata, enabled=True) == 'resp_stream'
    assert metadata == {'usage': usage, 'done': True}


def test_streaming_response_id_is_not_consumed_when_stateful_mode_is_disabled(responses_state):
    metadata = {'done': True, 'response_id': 'resp_stream'}

    assert responses_state.pop_stateful_response_id(metadata, enabled=False) is None
    assert metadata['response_id'] == 'resp_stream'


def test_non_streaming_response_preserves_text_and_response_id(responses_state):
    result = responses_state.convert_responses_result(
        {
            'id': 'resp_non_stream',
            'model': 'hermes',
            'output': [
                {
                    'type': 'message',
                    'content': [
                        {'type': 'output_text', 'text': 'Hello '},
                        {'type': 'output_text', 'text': 'world'},
                    ],
                }
            ],
            'usage': {'input_tokens': 2, 'output_tokens': 2},
        }
    )

    assert result['response_id'] == 'resp_non_stream'
    assert result['choices'][0]['message']['content'] == 'Hello world'
    assert result['output'][0]['type'] == 'message'


def test_non_streaming_function_call_remains_available_for_processing(responses_state):
    function_call = {
        'type': 'function_call',
        'call_id': 'call_1',
        'name': 'terminal',
        'arguments': '{}',
    }

    result = responses_state.convert_responses_result({'id': 'resp_tool', 'model': 'hermes', 'output': [function_call]})

    assert result['response_id'] == 'resp_tool'
    assert result['choices'][0]['message']['content'] == ''
    assert result['output'] == [function_call]
