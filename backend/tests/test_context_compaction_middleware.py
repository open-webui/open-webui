from open_webui.utils.middleware import add_context_summary_system_message


def test_context_summary_appends_to_existing_system_prompt():
    messages = [
        {'role': 'user', 'content': 'recent question'},
        {'role': 'assistant', 'content': 'recent answer'},
    ]

    result = add_context_summary_system_message(
        messages,
        'Earlier turns summarized here.',
        system_prompt='Always stay in character.',
    )

    assert result[0] == {
        'role': 'system',
        'content': 'Always stay in character.\n[CONVERSATION SUMMARY]\nEarlier turns summarized here.',
    }
    assert result[1:] == messages


def test_context_summary_stays_system_message_without_system_prompt():
    messages = [{'role': 'user', 'content': 'recent question'}]

    result = add_context_summary_system_message(messages, 'Earlier turns summarized here.')

    assert result[0] == {
        'role': 'system',
        'content': '[CONVERSATION SUMMARY]\nEarlier turns summarized here.',
    }
    assert result[1:] == messages
