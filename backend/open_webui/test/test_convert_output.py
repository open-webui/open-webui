"""Tests for convert_output_to_messages orphaned tool-call fix."""

from open_webui.utils.misc import convert_output_to_messages


def test_normal_function_call_with_output():
    """A function_call followed by its function_call_output should produce
    an assistant message with tool_calls and a matching tool message."""
    output = [
        {
            "type": "function_call",
            "call_id": "call_1",
            "name": "web_search",
            "arguments": '{"query": "hello"}',
        },
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": [{"type": "input_text", "text": "search results"}],
        },
        {
            "type": "message",
            "content": [{"type": "output_text", "text": "Here are the results."}],
        },
    ]
    messages = convert_output_to_messages(output)
    assert messages[0]["role"] == "assistant"
    assert messages[0]["tool_calls"][0]["id"] == "call_1"
    assert messages[1]["role"] == "tool"
    assert messages[1]["tool_call_id"] == "call_1"
    assert messages[1]["content"] == "search results"
    assert messages[2]["role"] == "assistant"
    assert messages[2]["content"] == "Here are the results."
    # No synthetic tool messages should be added
    assert len(messages) == 3


def test_orphaned_function_call_gets_synthetic_response():
    """A function_call with no matching function_call_output should get a
    synthetic tool response appended so providers don't reject the conversation."""
    output = [
        {
            "type": "message",
            "content": [{"type": "output_text", "text": "Let me search."}],
        },
        {
            "type": "function_call",
            "call_id": "call_orphan",
            "name": "web_search",
            "arguments": '{"query": "test"}',
        },
    ]
    messages = convert_output_to_messages(output)
    # assistant message with content + tool_calls
    assert messages[0]["role"] == "assistant"
    assert messages[0]["tool_calls"][0]["id"] == "call_orphan"
    # synthetic tool response
    assert messages[1]["role"] == "tool"
    assert messages[1]["tool_call_id"] == "call_orphan"
    assert messages[1]["content"] == "[Tool execution did not return a result]"


def test_multiple_orphaned_tool_calls():
    """Multiple orphaned tool calls should each get a synthetic response."""
    output = [
        {
            "type": "function_call",
            "call_id": "call_a",
            "name": "web_search",
            "arguments": '{"query": "a"}',
        },
        {
            "type": "function_call",
            "call_id": "call_b",
            "name": "web_search",
            "arguments": '{"query": "b"}',
        },
    ]
    messages = convert_output_to_messages(output)
    assert messages[0]["role"] == "assistant"
    assert len(messages[0]["tool_calls"]) == 2
    assert messages[1]["role"] == "tool"
    assert messages[1]["tool_call_id"] == "call_a"
    assert messages[2]["role"] == "tool"
    assert messages[2]["tool_call_id"] == "call_b"
    assert len(messages) == 3


def test_empty_output():
    """An empty output list should return an empty message list."""
    assert convert_output_to_messages([]) == []


def test_output_with_only_messages():
    """Output containing only message items should not trigger the fix."""
    output = [
        {
            "type": "message",
            "content": [{"type": "output_text", "text": "Hello world"}],
        },
    ]
    messages = convert_output_to_messages(output)
    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"] == "Hello world"
    assert "tool_calls" not in messages[0]
