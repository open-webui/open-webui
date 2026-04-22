from open_webui.utils.misc import add_reasoning_content_to_tool_messages


class TestAddReasoningContentToToolMessages:
    def test_adds_reasoning_content_for_kimi_tool_messages(self):
        messages = [
            {
                'role': 'assistant',
                'content': '<think>Need to search.</think>',
                'tool_calls': [
                    {
                        'id': 'call_123',
                        'type': 'function',
                        'function': {'name': 'search_web', 'arguments': '{"query":"Rakhi Kaag"}'},
                    }
                ],
            },
            {'role': 'tool', 'tool_call_id': 'call_123', 'content': 'Search results'},
        ]
        output = [
            {
                'type': 'reasoning',
                'summary': [{'type': 'output_text', 'text': 'Need to search.'}],
            },
            {
                'type': 'function_call',
                'call_id': 'call_123',
                'name': 'search_web',
                'arguments': '{"query":"Rakhi Kaag"}',
            },
            {'type': 'function_call_output', 'call_id': 'call_123', 'output': []},
        ]

        adjusted = add_reasoning_content_to_tool_messages(messages, output, 'kimi-k2.6')

        assert adjusted[0]['reasoning_content'] == 'Need to search.'
        assert adjusted[1] == messages[1]

    def test_scopes_reasoning_to_matching_assistant_message(self):
        messages = [
            {
                'role': 'assistant',
                'content': '<think>Need to search the web.</think>',
                'tool_calls': [
                    {
                        'id': 'call_1',
                        'type': 'function',
                        'function': {'name': 'search_web', 'arguments': '{"query":"Rakhi Kaag"}'},
                    }
                ],
            },
            {'role': 'tool', 'tool_call_id': 'call_1', 'content': 'First search results'},
            {
                'role': 'assistant',
                'content': '<think>Need to search notes.</think>',
                'tool_calls': [
                    {
                        'id': 'call_2',
                        'type': 'function',
                        'function': {'name': 'search_notes', 'arguments': '{"query":"Rakhi Kaag"}'},
                    }
                ],
            },
        ]
        output = [
            {
                'type': 'reasoning',
                'summary': [{'type': 'output_text', 'text': 'Need to search the web.'}],
            },
            {
                'type': 'function_call',
                'call_id': 'call_1',
                'name': 'search_web',
                'arguments': '{"query":"Rakhi Kaag"}',
            },
            {'type': 'function_call_output', 'call_id': 'call_1', 'output': []},
            {
                'type': 'reasoning',
                'summary': [{'type': 'output_text', 'text': 'Need to search notes.'}],
            },
            {
                'type': 'function_call',
                'call_id': 'call_2',
                'name': 'search_notes',
                'arguments': '{"query":"Rakhi Kaag"}',
            },
            {'type': 'function_call_output', 'call_id': 'call_2', 'output': []},
        ]

        adjusted = add_reasoning_content_to_tool_messages(messages, output, 'kimi-k2.6')

        assert adjusted[0]['reasoning_content'] == 'Need to search the web.'
        assert adjusted[2]['reasoning_content'] == 'Need to search notes.'

    def test_leaves_non_kimi_models_unchanged(self):
        messages = [
            {
                'role': 'assistant',
                'content': '<think>Need to search.</think>',
                'tool_calls': [
                    {
                        'id': 'call_123',
                        'type': 'function',
                        'function': {'name': 'search_web', 'arguments': '{"query":"Rakhi Kaag"}'},
                    }
                ],
            }
        ]
        output = [
            {
                'type': 'reasoning',
                'summary': [{'type': 'output_text', 'text': 'Need to search.'}],
            },
            {
                'type': 'function_call',
                'call_id': 'call_123',
                'name': 'search_web',
                'arguments': '{"query":"Rakhi Kaag"}',
            },
            {'type': 'function_call_output', 'call_id': 'call_123', 'output': []},
        ]

        adjusted = add_reasoning_content_to_tool_messages(messages, output, 'gpt-4.1')

        assert adjusted == messages

    def test_keeps_existing_reasoning_content(self):
        messages = [
            {
                'role': 'assistant',
                'content': '<think>Need to search.</think>',
                'reasoning_content': 'Existing reasoning',
                'tool_calls': [
                    {
                        'id': 'call_123',
                        'type': 'function',
                        'function': {'name': 'search_web', 'arguments': '{"query":"Rakhi Kaag"}'},
                    }
                ],
            }
        ]
        output = [
            {
                'type': 'reasoning',
                'summary': [{'type': 'output_text', 'text': 'Need to search.'}],
            },
            {
                'type': 'function_call',
                'call_id': 'call_123',
                'name': 'search_web',
                'arguments': '{"query":"Rakhi Kaag"}',
            },
            {'type': 'function_call_output', 'call_id': 'call_123', 'output': []},
        ]

        adjusted = add_reasoning_content_to_tool_messages(messages, output, 'moonshot-v1')

        assert adjusted[0]['reasoning_content'] == 'Existing reasoning'
