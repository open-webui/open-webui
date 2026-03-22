from copy import deepcopy

from open_webui.utils.payload import apply_ephemeral_cache_control_to_last_message


def test_apply_ephemeral_cache_control_to_last_message_can_be_disabled():
    payload = {
        "messages": [
            {"role": "user", "content": "hello"},
        ]
    }

    original = deepcopy(payload)
    result = apply_ephemeral_cache_control_to_last_message(payload, enabled=False)

    assert result == original
    assert "cache_control" not in result["messages"][0]


def test_apply_ephemeral_cache_control_to_last_message_marks_last_text_message():
    payload = {
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
    }

    result = apply_ephemeral_cache_control_to_last_message(payload, enabled=True)

    assert result["messages"][-1]["content"] == [
        {
            "type": "text",
            "text": "world",
            "cache_control": {"type": "ephemeral"},
        }
    ]
