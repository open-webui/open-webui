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


def test_responses_payload_rejects_conversation_with_previous_response_id(responses_state):
    with pytest.raises(ValueError, match='cannot be used together'):
        responses_state.apply_responses_stateful_payload(
            {
                'conversation': 'conv_1',
                'previous_response_id': 'resp_1',
            },
            is_responses=True,
            enabled=True,
        )


def test_responses_payload_rejects_invalid_native_state_when_automatic_state_is_disabled(
    responses_state,
):
    with pytest.raises(ValueError, match='cannot be used together'):
        responses_state.apply_responses_stateful_payload(
            {
                'conversation': {'id': 'conv_1'},
                'previous_response_id': 'resp_1',
            },
            is_responses=True,
            enabled=False,
        )


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


def test_enabled_stateful_mode_overrides_disabled_storage(responses_state):
    result = responses_state.apply_responses_stateful_payload(
        {'store': False},
        is_responses=True,
        enabled=True,
    )

    assert result['store'] is True


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


def test_streaming_completion_metadata_exposes_response_lifecycle(responses_state):
    usage = {'input_tokens': 10, 'output_tokens': 4}

    metadata = responses_state.get_response_metadata({'id': 'resp_stream', 'status': 'completed', 'usage': usage})

    assert metadata == {
        'usage': usage,
        'done': True,
        'response_id': 'resp_stream',
        'response_status': 'completed',
    }
    assert responses_state.pop_stateful_response_id(metadata, enabled=True) == 'resp_stream'
    assert metadata == {'usage': usage, 'done': True, 'response_status': 'completed'}


@pytest.mark.parametrize('status', ['failed', 'cancelled', 'incomplete'])
def test_terminal_response_metadata_is_marked_done(responses_state, status):
    response = {
        'id': f'resp_{status}',
        'status': status,
        'usage': None,
        'error': {'message': 'failed'} if status == 'failed' else None,
        'incomplete_details': {'reason': 'max_output_tokens'} if status == 'incomplete' else None,
    }

    metadata = responses_state.get_response_metadata(response)

    assert metadata['done'] is True
    assert metadata['response_status'] == status
    assert metadata['response_id'] == f'resp_{status}'


@pytest.mark.parametrize('status', ['queued', 'in_progress'])
def test_non_terminal_response_metadata_is_not_marked_done(responses_state, status):
    metadata = responses_state.get_response_metadata({'id': 'resp_pending', 'status': status})

    assert 'done' not in metadata
    assert metadata['response_status'] == status


def test_completed_lifecycle_event_uses_final_output(responses_state):
    current_output = [{'type': 'message', 'content': []}]
    final_output = [
        {
            'type': 'reasoning',
            'id': 'rs_1',
            'status': 'in_progress',
            'summary': [],
        }
    ]

    output, metadata = responses_state.handle_responses_lifecycle_event(
        'response.completed',
        {'id': 'resp_1', 'status': 'completed', 'output': final_output},
        current_output,
    )

    assert output == [{**final_output[0], 'status': 'completed'}]
    assert metadata['done'] is True
    assert metadata['response_id'] == 'resp_1'


def test_incomplete_lifecycle_event_preserves_partial_output(responses_state):
    partial_output = [{'type': 'message', 'status': 'incomplete', 'content': []}]
    details = {'reason': 'max_output_tokens'}

    output, metadata = responses_state.handle_responses_lifecycle_event(
        'response.incomplete',
        {
            'id': 'resp_partial',
            'status': 'incomplete',
            'incomplete_details': details,
            'output': [],
        },
        partial_output,
    )

    assert output == partial_output
    assert metadata['incomplete_details'] == details
    assert metadata['done'] is True


def test_non_lifecycle_event_is_ignored(responses_state):
    assert (
        responses_state.handle_responses_lifecycle_event(
            'response.output_text.delta',
            {},
            [],
        )
        is None
    )


def test_native_response_items_keep_official_fields_and_drop_webui_fields(responses_state):
    item = {
        'type': 'reasoning',
        'id': 'rs_1',
        'status': 'completed',
        'summary': [{'type': 'summary_text', 'text': 'Summary'}],
        'encrypted_content': 'encrypted',
        'started_at': 1,
        'duration': 2,
        'attributes': {'type': 'reasoning_content'},
    }

    assert responses_state.normalize_responses_input_item(item) == {
        'type': 'reasoning',
        'id': 'rs_1',
        'status': 'completed',
        'summary': [{'type': 'summary_text', 'text': 'Summary'}],
        'encrypted_content': 'encrypted',
    }


def test_unknown_response_items_are_forward_compatible(responses_state):
    item = {
        'type': 'future_tool_call',
        'id': 'future_1',
        'status': 'completed',
        'files': [{'id': 'file_1'}],
        'attributes': {'future': True},
        'new_official_field': True,
    }

    assert responses_state.normalize_responses_input_item(item) == item


def test_openwebui_only_output_items_are_not_replayed(responses_state):
    item = {
        'type': 'open_webui:code_interpreter',
        'id': 'local_1',
        'code': 'print(1)',
    }

    assert responses_state.normalize_responses_input_item(item) is None


def test_function_call_drops_only_openwebui_approval_state(responses_state):
    item = {
        'type': 'function_call',
        'id': 'fc_1',
        'call_id': 'call_1',
        'name': 'terminal',
        'arguments': '{}',
        'status': 'completed',
        'approved': True,
    }

    assert responses_state.normalize_responses_input_item(item) == {
        'type': 'function_call',
        'id': 'fc_1',
        'call_id': 'call_1',
        'name': 'terminal',
        'arguments': '{}',
        'status': 'completed',
    }


def test_function_output_is_normalized_for_stateful_continuation(responses_state):
    tool_output = {
        'type': 'function_call_output',
        'id': 'local_fco',
        'call_id': 'call_1',
        'output': [{'type': 'input_text', 'text': '42'}],
        'status': 'completed',
        'files': [{'url': 'local'}],
    }

    messages = responses_state.build_stateful_tool_continuation_messages(
        {'role': 'system', 'content': 'Instructions'},
        [tool_output],
    )

    assert messages == [
        {'role': 'system', 'content': 'Instructions'},
        {
            'role': 'tool',
            'output': [
                {
                    'type': 'function_call_output',
                    'call_id': 'call_1',
                    'output': [{'type': 'input_text', 'text': '42'}],
                }
            ],
        },
    ]


def test_chat_payload_conversion_preserves_native_stateful_fields(responses_state):
    payload = responses_state.convert_to_responses_payload(
        {
            'model': 'hermes',
            'messages': [
                {'role': 'system', 'content': 'Managed instructions'},
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': 'Inspect this'},
                        {
                            'type': 'image_url',
                            'image_url': {'url': 'data:image/png;base64,abc', 'detail': 'high'},
                        },
                        {
                            'type': 'file',
                            'file': {'file_id': 'file_1', 'filename': 'report.pdf'},
                        },
                    ],
                },
            ],
            'previous_response_id': 'resp_1',
            'store': True,
        }
    )

    assert payload['instructions'] == 'Managed instructions'
    assert payload['previous_response_id'] == 'resp_1'
    assert payload['store'] is True
    assert payload['input'] == [
        {
            'type': 'message',
            'role': 'user',
            'content': [
                {'type': 'input_text', 'text': 'Inspect this'},
                {
                    'type': 'input_image',
                    'image_url': 'data:image/png;base64,abc',
                    'detail': 'high',
                },
                {'type': 'input_file', 'file_id': 'file_1', 'filename': 'report.pdf'},
            ],
        }
    ]


def test_stateful_tool_continuation_converts_to_only_function_outputs(responses_state):
    messages = responses_state.build_stateful_tool_continuation_messages(
        {'role': 'system', 'content': 'Instructions'},
        [
            {
                'type': 'function_call_output',
                'id': 'local_fco',
                'call_id': 'call_1',
                'output': 'done',
                'status': 'completed',
            }
        ],
    )

    payload = responses_state.convert_to_responses_payload(
        {
            'model': 'hermes',
            'messages': messages,
            'previous_response_id': 'resp_tool_call',
        }
    )

    assert payload['instructions'] == 'Instructions'
    assert payload['previous_response_id'] == 'resp_tool_call'
    assert payload['input'] == [
        {
            'type': 'function_call_output',
            'call_id': 'call_1',
            'output': 'done',
        }
    ]


def test_chat_tools_structured_output_and_stream_options_are_converted(responses_state):
    payload = responses_state.convert_to_responses_payload(
        {
            'messages': [{'role': 'user', 'content': 'Go'}],
            'tools': [
                {
                    'type': 'function',
                    'function': {
                        'name': 'lookup',
                        'description': 'Look up a record',
                        'parameters': {'type': 'object'},
                        'strict': True,
                    },
                }
            ],
            'tool_choice': {'type': 'function', 'function': {'name': 'lookup'}},
            'response_format': {
                'type': 'json_schema',
                'json_schema': {
                    'name': 'result',
                    'schema': {'type': 'object'},
                    'strict': True,
                },
            },
            'stream_options': {'include_usage': True, 'include_obfuscation': False},
            'max_completion_tokens': 100,
            'n': 2,
        }
    )

    assert payload['tools'] == [
        {
            'type': 'function',
            'name': 'lookup',
            'description': 'Look up a record',
            'parameters': {'type': 'object'},
            'strict': True,
        }
    ]
    assert payload['tool_choice'] == {'type': 'function', 'name': 'lookup'}
    assert payload['text'] == {
        'format': {
            'type': 'json_schema',
            'name': 'result',
            'schema': {'type': 'object'},
            'strict': True,
        }
    }
    assert payload['stream_options'] == {'include_obfuscation': False}
    assert payload['max_output_tokens'] == 100
    assert 'n' not in payload


def test_native_input_content_and_built_in_tools_pass_through(responses_state):
    payload = responses_state.convert_to_responses_payload(
        {
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'input_text', 'text': 'Search'},
                        {'type': 'input_file', 'file_data': 'data:application/pdf;base64,abc'},
                    ],
                }
            ],
            'tools': [{'type': 'web_search'}],
        }
    )

    assert payload['input'][0]['content'] == [
        {'type': 'input_text', 'text': 'Search'},
        {'type': 'input_file', 'file_data': 'data:application/pdf;base64,abc'},
    ]
    assert payload['tools'] == [{'type': 'web_search'}]


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


def test_non_streaming_incomplete_response_preserves_native_state(responses_state):
    details = {'reason': 'max_output_tokens'}

    result = responses_state.convert_responses_result(
        {
            'id': 'resp_incomplete',
            'model': 'hermes',
            'status': 'incomplete',
            'incomplete_details': details,
            'output': [],
        }
    )

    assert result['response_status'] == 'incomplete'
    assert result['incomplete_details'] == details
    assert result['choices'][0]['finish_reason'] == 'incomplete'
