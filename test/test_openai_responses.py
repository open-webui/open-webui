from copy import deepcopy

from open_webui.routers.openai import convert_to_responses_payload


def _convert_tools(tools):
    return convert_to_responses_payload(
        {
            'messages': [{'role': 'user', 'content': 'input'}],
            'tools': tools,
        }
    )['tools']


def _function_tool(**function_fields):
    return {
        'type': 'function',
        'function': {
            'name': 'lookup',
            'description': 'Return a value',
            'parameters': {
                'type': 'object',
                'properties': {'value': {'type': 'string'}},
                'required': ['value'],
            },
            **function_fields,
        },
    }


def test_chat_completions_function_tool_defaults_strict_to_false():
    converted = _convert_tools([_function_tool()])[0]

    assert converted['strict'] is False


def test_chat_completions_function_tool_preserves_explicit_strict_true():
    assert _convert_tools([_function_tool(strict=True)])[0]['strict'] is True


def test_chat_completions_function_tool_preserves_explicit_strict_false():
    assert _convert_tools([_function_tool(strict=False)])[0]['strict'] is False


def test_chat_completions_function_tool_preserves_schema_and_source_tool():
    tool = _function_tool()
    source_tool = deepcopy(tool)
    source_schema = deepcopy(tool['function']['parameters'])

    converted = _convert_tools([tool])[0]

    assert converted == {
        'type': 'function',
        'name': 'lookup',
        'description': 'Return a value',
        'parameters': source_schema,
        'strict': False,
    }
    assert tool == source_tool


def test_native_responses_tool_without_function_is_unchanged():
    native_tool = {'type': 'web_search_preview', 'search_context_size': 'high'}
    source_tool = deepcopy(native_tool)

    converted = _convert_tools([native_tool])

    assert converted == [source_tool]
    assert native_tool == source_tool
