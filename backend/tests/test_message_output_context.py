import os

os.environ.setdefault('WEBUI_SECRET_KEY', 'message-output-context-tests-only-secret-key')

from open_webui.utils.misc import expand_messages_with_output


def test_expand_messages_with_output_preserves_tool_result_and_final_text():
    messages = [
        {'role': 'user', 'content': 'Look this up'},
        {
            'role': 'assistant',
            'content': '',
            'output': [
                {
                    'type': 'function_call',
                    'call_id': 'call-1',
                    'name': 'search',
                    'arguments': {'query': 'answer'},
                },
                {
                    'type': 'function_call_output',
                    'call_id': 'call-1',
                    'output': [{'type': 'input_text', 'text': 'tool result'}],
                },
                {
                    'type': 'message',
                    'content': [{'type': 'output_text', 'text': 'final answer'}],
                },
            ],
        },
    ]

    expanded = expand_messages_with_output(messages)

    assert [message['role'] for message in expanded] == ['user', 'assistant', 'tool', 'assistant']
    assert expanded[1]['tool_calls'][0]['function']['arguments'] == '{"query": "answer"}'
    assert expanded[2]['content'] == 'tool result'
    assert expanded[3]['content'] == 'final answer'
    assert all('output' not in message for message in expanded)


def test_expand_messages_with_output_keeps_plain_message_without_output_field():
    original = {'role': 'assistant', 'content': 'plain', 'output': []}

    assert expand_messages_with_output([original]) == [{'role': 'assistant', 'content': 'plain'}]
    assert 'output' in original
