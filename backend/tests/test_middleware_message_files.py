from open_webui.utils.chat_history import inline_message_images_from_files


def test_inline_message_images_accepts_null_files():
    messages = [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'hello', 'files': None},
        {'role': 'assistant', 'content': 'hi', 'files': None},
    ]

    assert inline_message_images_from_files(messages) == [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'hello'},
        {'role': 'assistant', 'content': 'hi'},
    ]


def test_inline_message_images_preserves_text_and_image_urls():
    messages = [
        {
            'role': 'user',
            'content': 'describe this',
            'files': [
                {'type': 'image', 'url': 'data:image/png;base64,abc'},
                {'type': 'file', 'content_type': 'text/plain', 'url': '/files/note'},
            ],
        }
    ]

    assert inline_message_images_from_files(messages) == [
        {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': 'describe this'},
                {
                    'type': 'image_url',
                    'image_url': {'url': 'data:image/png;base64,abc'},
                },
            ],
        }
    ]
