from open_webui.utils.misc import get_messages_content


def test_get_messages_content_uses_output_text_when_content_is_empty():
    messages = [
        {'role': 'user', 'content': 'hello'},
        {
            'role': 'assistant',
            'content': '',
            'output': [
                {
                    'type': 'message',
                    'content': [{'type': 'output_text', 'text': 'Hi there.'}],
                }
            ],
        },
    ]

    assert get_messages_content(messages) == 'USER: hello\nASSISTANT: Hi there.'
