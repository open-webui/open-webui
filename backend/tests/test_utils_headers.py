from open_webui.utils.headers import get_custom_headers


def test_get_custom_headers_expands_lowercase_and_uppercase_chat_id():
    headers = {
        'X-Lowercase': '{{chat_id}}',
        'X-Uppercase': '{{CHAT_ID}}',
    }

    assert get_custom_headers(headers, metadata={'chat_id': 'chat-123'}) == {
        'X-Lowercase': 'chat-123',
        'X-Uppercase': 'chat-123',
    }


def test_get_custom_headers_preserves_static_values_and_coerces_non_strings():
    headers = {
        'X-Mixed': 'chat={{chat_id}}; static=value',
        'X-Static': 'unchanged',
        'X-Number': 42,
    }

    assert get_custom_headers(headers, metadata={'chat_id': 'chat-123'}) == {
        'X-Mixed': 'chat=chat-123; static=value',
        'X-Static': 'unchanged',
        'X-Number': '42',
    }


def test_get_custom_headers_uses_empty_string_for_missing_known_values():
    assert get_custom_headers({'X-Chat': 'before-{{chat_id}}-after'}) == {
        'X-Chat': 'before--after'
    }


def test_get_custom_headers_preserves_unknown_tokens():
    assert get_custom_headers({'X-Unknown': '{{unknown}}'}) == {
        'X-Unknown': '{{unknown}}'
    }
