from types import SimpleNamespace
from unittest.mock import patch

from open_webui.utils.middleware import (
    _split_tool_calls,
    extract_responses_api_tool_calls,
    handle_responses_streaming_event,
    is_responses_api_model,
    prepare_responses_output_for_append,
)


def test_is_responses_api_model_resolves_base_model_id():
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                MODELS={
                    "custom-gpt-5": {
                        "id": "custom-gpt-5",
                        "info": {"base_model_id": "openai/gpt-5.4"},
                    },
                    "openai/gpt-5.4": {
                        "id": "openai/gpt-5.4",
                        "urlIdx": 0,
                    },
                },
                OPENAI_MODELS={
                    "openai/gpt-5.4": {
                        "id": "openai/gpt-5.4",
                        "urlIdx": 0,
                    }
                },
                config=SimpleNamespace(
                    OPENAI_API_BASE_URLS=["https://api.openai.com/v1"],
                    OPENAI_API_CONFIGS={"0": {"api_type": "responses"}},
                ),
            )
        )
    )

    with patch(
        "open_webui.utils.middleware.Models.get_model_by_id",
        return_value=SimpleNamespace(base_model_id="openai/gpt-5.4"),
    ):
        assert (
            is_responses_api_model(
                request,
                model={"id": "custom-gpt-5"},
                model_id="custom-gpt-5",
            )
            is True
        )


def test_extract_responses_api_tool_calls_only_scans_new_suffix():
    output = [
        {
            "type": "function_call",
            "id": "fc_old",
            "call_id": "call_old",
            "name": "search_web",
            "arguments": '{"query":"old"}',
            "status": "completed",
        },
        {
            "type": "function_call_output",
            "id": "fco_old",
            "call_id": "call_old",
            "output": "old result",
            "status": "completed",
        },
        {
            "type": "message",
            "id": "msg_new",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Need another lookup"}],
            "status": "completed",
        },
        {
            "type": "function_call",
            "id": "fc_new",
            "call_id": "call_new",
            "name": "fetch_url",
            "arguments": '{"url":"https://example.com"}',
            "status": "completed",
        },
    ]

    retained_output, tool_calls = extract_responses_api_tool_calls(output, start_index=2)

    assert retained_output == output[:3]
    assert tool_calls == [
        {
            "id": "call_new",
            "output_id": "fc_new",
            "index": 0,
            "function": {
                "name": "fetch_url",
                "arguments": '{"url":"https://example.com"}',
            },
        }
    ]


def test_extract_responses_api_tool_calls_keeps_historical_tool_calls_untouched():
    output = [
        {
            "type": "function_call",
            "id": "fc_old",
            "call_id": "call_old",
            "name": "search_web",
            "arguments": '{"query":"old"}',
            "status": "completed",
        },
        {
            "type": "function_call_output",
            "id": "fco_old",
            "call_id": "call_old",
            "output": "old result",
            "status": "completed",
        },
    ]

    retained_output, tool_calls = extract_responses_api_tool_calls(output, start_index=len(output))

    assert retained_output == output
    assert tool_calls == []


def test_split_tool_calls_assigns_unique_output_ids_for_responses_follow_ups():
    tool_calls = [
        {
            "id": "call_original",
            "output_id": "fc_original",
            "function": {
                "name": "search_web",
                "arguments": '{"query":"first"}{"query":"second"}',
            },
        }
    ]

    split_calls = _split_tool_calls(tool_calls)

    assert len(split_calls) == 2
    assert [tc["function"]["arguments"] for tc in split_calls] == [
        '{"query":"first"}',
        '{"query":"second"}',
    ]
    assert len({tc["id"] for tc in split_calls}) == 2
    assert len({tc["output_id"] for tc in split_calls}) == 2
    assert all(tc["output_id"].startswith("fc_") for tc in split_calls)
    assert all(tc["output_id"] != "fc_original" for tc in split_calls)


def test_prepare_responses_output_for_append_keeps_follow_up_deltas_on_new_item():
    output = [
        {
            "type": "function_call",
            "id": "fc_old",
            "call_id": "call_old",
            "name": "get_current_timestamp",
            "arguments": "{}",
            "status": "completed",
        },
        {
            "type": "function_call_output",
            "id": "fco_old",
            "call_id": "call_old",
            "output": "2026-03-08T18:36:34Z",
            "status": "completed",
        },
        {
            "type": "message",
            "id": "msg_placeholder",
            "role": "assistant",
            "status": "in_progress",
            "content": [{"type": "output_text", "text": ""}],
        },
    ]

    live_output, responses_output_prefix = prepare_responses_output_for_append(output)
    assert live_output == responses_output_prefix
    assert len(live_output) == 2

    live_output, _ = handle_responses_streaming_event(
        {
            "type": "response.output_item.added",
            "output_index": len(responses_output_prefix),
            "item": {
                "type": "message",
                "id": "msg_new",
                "role": "assistant",
                "status": "in_progress",
                "content": [{"type": "output_text", "text": ""}],
            },
        },
        live_output,
    )

    live_output, _ = handle_responses_streaming_event(
        {
            "type": "response.output_text.delta",
            "output_index": len(responses_output_prefix),
            "content_index": 0,
            "delta": "follow-up text",
        },
        live_output,
    )

    assert live_output[-1]["id"] == "msg_new"
    assert live_output[-1]["content"][0]["text"] == "follow-up text"
