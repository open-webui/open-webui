from open_webui.utils.payload import convert_messages_openai_to_ollama, convert_payload_openai_to_ollama


def test_convert_messages_openai_to_ollama_parses_tool_call_arguments_string():
    messages = [
        {
            'role': 'assistant',
            'tool_calls': [
                {
                    'id': 'call_1',
                    'type': 'function',
                    'function': {'name': 'lookup', 'arguments': '{"query": "weather"}'},
                }
            ],
        }
    ]

    result = convert_messages_openai_to_ollama(messages)

    assert result == [
        {
            'role': 'assistant',
            'tool_calls': [
                {
                    'index': 0,
                    'id': 'call_1',
                    'function': {'name': 'lookup', 'arguments': {'query': 'weather'}},
                }
            ],
            'content': '',
        }
    ]


def test_convert_messages_openai_to_ollama_keeps_decoded_tool_call_arguments():
    messages = [
        {
            'role': 'assistant',
            'tool_calls': [
                {
                    'id': 'call_1',
                    'type': 'function',
                    'function': {'name': 'lookup', 'arguments': {'query': 'weather'}},
                }
            ],
        }
    ]

    result = convert_messages_openai_to_ollama(messages)

    assert result[0]['tool_calls'][0]['function']['arguments'] == {'query': 'weather'}


def test_convert_messages_openai_to_ollama_defaults_missing_tool_call_arguments():
    messages = [
        {
            'role': 'assistant',
            'tool_calls': [
                {
                    'id': 'call_1',
                    'type': 'function',
                    'function': {'name': 'lookup'},
                }
            ],
        }
    ]

    result = convert_messages_openai_to_ollama(messages)

    assert result[0]['tool_calls'][0]['function']['arguments'] == {}


def test_convert_payload_openai_to_ollama_forwards_tools_array():
    tools = [
        {
            'type': 'function',
            'function': {
                'name': 'get_current_weather_in_city',
                'description': 'Get the current weather for a city.',
                'parameters': {
                    'type': 'object',
                    'properties': {'city': {'type': 'string'}},
                    'required': ['city'],
                },
            },
        }
    ]
    payload = {
        'model': 'qwen2.5:7b',
        'messages': [{'role': 'user', 'content': 'Weather in Bountiful?'}],
        'tools': tools,
        'stream': False,
    }

    result = convert_payload_openai_to_ollama(payload)

    assert result['tools'] == tools
