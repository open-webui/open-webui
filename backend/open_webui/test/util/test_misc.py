from open_webui.utils.misc import (
    build_responses_api_continuation_messages,
    collapse_responses_api_messages,
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


def test_collapse_responses_api_messages_keeps_system_and_delta_suffix():
    messages = [
        {"role": "system", "content": "You are precise."},
        {
            "role": "assistant",
            "response_id": "resp_123",
            "output": [
                {
                    "type": "message",
                    "id": "msg_existing123",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "cached reply"}],
                }
            ],
        },
        {"role": "user", "content": "What changed?"},
    ]

    collapsed_messages, previous_response_id = collapse_responses_api_messages(
        messages
    )

    assert previous_response_id == "resp_123"
    assert collapsed_messages == [
        {"role": "system", "content": "You are precise."},
        {"role": "user", "content": "What changed?"},
    ]


def test_build_responses_api_continuation_messages_trims_placeholder():
    messages = [{"role": "system", "content": "You are precise."}]
    output_items = [
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": "tool result",
            "status": "completed",
        },
        {
            "type": "message",
            "role": "assistant",
            "status": "in_progress",
            "content": [{"type": "output_text", "text": ""}],
        },
    ]

    continuation_messages = build_responses_api_continuation_messages(
        messages, output_items
    )

    assert continuation_messages == [
        {"role": "system", "content": "You are precise."},
        {
            "role": "assistant",
            "output": [
                {
                    "type": "function_call_output",
                    "call_id": "call_123",
                    "output": "tool result",
                    "status": "completed",
                }
            ],
        },
    ]
