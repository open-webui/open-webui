from open_webui.utils.middleware import process_messages_with_output


def test_process_messages_with_output_drops_empty_assistant_placeholders():
    messages = [
        {'role': 'user', 'content': 'first prompt'},
        {'role': 'assistant', 'content': '', 'done': False},
        {'role': 'user', 'content': 'next prompt'},
    ]

    assert process_messages_with_output(messages) == [
        {'role': 'user', 'content': 'first prompt'},
        {'role': 'user', 'content': 'next prompt'},
    ]


def test_process_messages_with_output_keeps_useful_assistant_messages():
    messages = [
        {'role': 'assistant', 'content': 'done'},
        {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'call-1'}]},
        {'role': 'assistant', 'content': [{'type': 'image_url', 'image_url': {'url': 'data:'}}]},
    ]

    assert process_messages_with_output(messages) == messages
