import os
from copy import deepcopy

os.environ.setdefault('WEBUI_SECRET_KEY', 'test-secret')

from open_webui.utils.misc import convert_output_to_messages, flatten_multimodal_tool_messages


def test_text_only_tool_messages_are_unchanged():
    messages = [
        {'role': 'assistant', 'content': '', 'tool_calls': []},
        {'role': 'tool', 'tool_call_id': 'call_1', 'content': 'plain text'},
    ]
    original = deepcopy(messages)

    assert flatten_multimodal_tool_messages(messages) == original


def test_multimodal_output_becomes_text_tool_result_followed_by_user_image():
    output = [
        {
            'type': 'function_call',
            'call_id': 'call_1',
            'name': 'view',
            'arguments': '{}',
        },
        {
            'type': 'function_call_output',
            'call_id': 'call_1',
            'output': [
                {'type': 'input_text', 'text': 'Image loaded.'},
                {'type': 'input_image', 'image_url': 'data:image/png;base64,AAAA'},
            ],
        },
        {
            'type': 'message',
            'role': 'assistant',
            'content': [{'type': 'output_text', 'text': 'Done.'}],
        },
    ]

    messages = flatten_multimodal_tool_messages(convert_output_to_messages(output, raw=True), mark_image_messages=True)

    assert messages[1] == {
        'role': 'tool',
        'tool_call_id': 'call_1',
        'content': 'Image loaded.',
    }
    assert messages[2]['role'] == 'user'
    assert messages[2]['_tool_result_image'] is True
    assert messages[2]['content'][1] == {
        'type': 'image_url',
        'image_url': {'url': 'data:image/png;base64,AAAA'},
    }
    assert messages[3] == {'role': 'assistant', 'content': 'Done.'}


def test_parallel_tool_results_precede_one_user_image_message():
    output = [
        {'type': 'function_call', 'call_id': 'call_1', 'name': 'view', 'arguments': '{}'},
        {'type': 'function_call', 'call_id': 'call_2', 'name': 'view', 'arguments': '{}'},
        {
            'type': 'function_call_output',
            'call_id': 'call_1',
            'output': [
                {'type': 'input_text', 'text': 'First.'},
                {'type': 'input_image', 'image_url': 'data:image/png;base64,AAAA'},
            ],
        },
        {
            'type': 'function_call_output',
            'call_id': 'call_2',
            'output': [
                {'type': 'input_text', 'text': 'Second.'},
                {'type': 'input_image', 'image_url': 'data:image/png;base64,BBBB'},
            ],
        },
        {
            'type': 'message',
            'role': 'assistant',
            'content': [{'type': 'output_text', 'text': 'Done.'}],
        },
    ]

    messages = flatten_multimodal_tool_messages(convert_output_to_messages(output, raw=True))

    assert [message['role'] for message in messages] == ['assistant', 'tool', 'tool', 'user', 'assistant']
    assert [message['tool_call_id'] for message in messages[1:3]] == ['call_1', 'call_2']
    assert [part['image_url']['url'] for part in messages[3]['content'][1:]] == [
        'data:image/png;base64,AAAA',
        'data:image/png;base64,BBBB',
    ]


def test_empty_image_urls_are_omitted():
    messages = [
        {
            'role': 'tool',
            'tool_call_id': 'call_1',
            'content': [
                {'type': 'input_text', 'text': 'Images loaded.'},
                {'type': 'input_image', 'image_url': ''},
                {'type': 'input_image', 'image_url': 'data:image/png;base64,AAAA'},
                {'type': 'input_image', 'image_url': 'data:image/png;base64,BBBB'},
            ],
        }
    ]

    result = flatten_multimodal_tool_messages(messages)

    assert result[0]['content'] == 'Images loaded.'
    assert [part['image_url']['url'] for part in result[1]['content'][1:]] == [
        'data:image/png;base64,AAAA',
        'data:image/png;base64,BBBB',
    ]


def test_source_messages_are_not_mutated():
    messages = [
        {
            'role': 'tool',
            'tool_call_id': 'call_1',
            'content': [
                {'type': 'input_text', 'text': 'Image loaded.'},
                {'type': 'input_image', 'image_url': 'data:image/png;base64,AAAA'},
            ],
        }
    ]
    original = deepcopy(messages)

    result = flatten_multimodal_tool_messages(messages)

    assert messages == original
    assert '_tool_result_image' not in result[1]
