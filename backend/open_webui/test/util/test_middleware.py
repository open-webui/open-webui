from types import SimpleNamespace
from unittest.mock import patch

from open_webui.utils.middleware import (
    extract_responses_api_tool_calls,
    is_responses_api_model,
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
