from open_webui.utils.response import normalize_chat_completion_message


def test_normalizes_structured_thinking_delta():
    message = {
        'role': 'assistant',
        'content': [
            {
                'type': 'thinking',
                'thinking': [
                    {'type': 'text', 'text': 'First '},
                    {'type': 'text', 'text': 'reasoning step.'},
                ],
                'closed': False,
            }
        ],
    }

    normalized = normalize_chat_completion_message(message)

    assert normalized == {
        'role': 'assistant',
        'content': '',
        'reasoning_content': 'First reasoning step.',
    }
    assert normalized is not message


def test_normalizes_transition_from_thinking_to_answer():
    message = {
        'content': [
            {'type': 'thinking', 'thinking': [], 'closed': True},
            {'type': 'text', 'text': 'Final answer.'},
        ]
    }

    assert normalize_chat_completion_message(message) == {
        'content': 'Final answer.',
    }


def test_normalizes_complete_structured_response():
    message = {
        'content': [
            {
                'type': 'thinking',
                'thinking': [{'type': 'text', 'text': 'Reasoning.'}],
                'closed': True,
            },
            {'type': 'text', 'text': 'Answer.'},
        ]
    }

    assert normalize_chat_completion_message(message) == {
        'content': 'Answer.',
        'reasoning_content': 'Reasoning.',
    }


def test_preserves_existing_reasoning_field():
    message = {
        'content': [
            {
                'type': 'thinking',
                'thinking': [{'type': 'text', 'text': 'Nested reasoning.'}],
                'closed': True,
            },
            {'type': 'text', 'text': 'Answer.'},
        ],
        'reasoning_content': 'Provider reasoning.',
    }

    assert normalize_chat_completion_message(message) == {
        'content': 'Answer.',
        'reasoning_content': 'Provider reasoning.',
    }


def test_leaves_text_only_content_list_unchanged():
    message = {'content': [{'type': 'text', 'text': 'Text block.'}]}

    assert normalize_chat_completion_message(message) is message


def test_leaves_unknown_content_blocks_unchanged():
    message = {
        'content': [
            {
                'type': 'thinking',
                'thinking': [{'type': 'text', 'text': 'Reasoning.'}],
            },
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,abc'}},
        ]
    }

    assert normalize_chat_completion_message(message) is message


def test_does_not_mistake_anthropic_thinking_for_nested_thinking_chunks():
    message = {
        'content': [
            {'type': 'thinking', 'thinking': 'Anthropic reasoning.', 'signature': 'signature'},
            {'type': 'text', 'text': 'Answer.'},
        ]
    }

    assert normalize_chat_completion_message(message) is message
