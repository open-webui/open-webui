from open_webui.utils.misc import (
    convert_output_to_input_messages,
    trim_trailing_empty_output_messages,
)


def test_trim_trailing_empty_output_messages_removes_placeholder():
    output = [
        {
            "type": "function_call",
            "call_id": "call_123",
            "name": "get_current_timestamp",
            "arguments": "{}",
            "status": "completed",
        },
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": [{"type": "input_text", "text": "2026-03-08T18:36:34Z"}],
            "status": "completed",
        },
        {
            "type": "message",
            "role": "assistant",
            "status": "in_progress",
            "content": [{"type": "output_text", "text": ""}],
        },
    ]

    trimmed_output = trim_trailing_empty_output_messages(output)

    assert len(trimmed_output) == 2
    assert trimmed_output[-1]["type"] == "function_call_output"
    assert output[-1]["content"][0]["text"] == ""


def test_convert_output_to_input_messages_preserves_responses_output():
    output = [
        {
            "type": "function_call",
            "call_id": "call_123",
            "name": "get_current_timestamp",
            "arguments": "{}",
            "status": "completed",
        },
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": [{"type": "input_text", "text": "2026-03-08T18:36:34Z"}],
            "status": "completed",
        },
        {
            "type": "message",
            "role": "assistant",
            "status": "in_progress",
            "content": [{"type": "output_text", "text": ""}],
        },
    ]

    messages = convert_output_to_input_messages(output, raw=True, responses_api=True)

    assert messages == [
        {
            "role": "assistant",
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call_123",
                    "name": "get_current_timestamp",
                    "arguments": "{}",
                    "status": "completed",
                },
                {
                    "type": "function_call_output",
                    "call_id": "call_123",
                    "output": [
                        {"type": "input_text", "text": "2026-03-08T18:36:34Z"}
                    ],
                    "status": "completed",
                },
            ],
        }
    ]


def test_convert_output_to_input_messages_chat_completion_mode():
    output = [
        {
            "type": "function_call",
            "call_id": "call_123",
            "name": "get_current_timestamp",
            "arguments": "{}",
            "status": "completed",
        },
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": [{"type": "input_text", "text": "2026-03-08T18:36:34Z"}],
            "status": "completed",
        },
    ]

    messages = convert_output_to_input_messages(output, raw=True, responses_api=False)

    assert messages == [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_current_timestamp",
                        "arguments": "{}",
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_123",
            "content": "2026-03-08T18:36:34Z",
        },
    ]
