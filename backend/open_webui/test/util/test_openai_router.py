from open_webui.routers.openai import (
    convert_to_responses_payload,
    is_openai_reasoning_model,
    normalize_responses_payload,
    openai_reasoning_model_handler,
)


def test_convert_to_responses_payload_normalizes_stored_message_item_ids():
    payload = {
        "model": "openai/gpt-5.4",
        "messages": [
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "output": [
                    {
                        "type": "message",
                        "id": "88atacOkNLK6kdUP44TSoQY",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": "first reply"},
                        ],
                    }
                ],
            },
        ],
    }

    converted = convert_to_responses_payload(payload)

    assert converted["input"][0] == {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "hello"}],
    }
    assert converted["input"][1]["type"] == "message"
    assert converted["input"][1]["id"].startswith("msg_")
    assert converted["input"][1]["id"] != "88atacOkNLK6kdUP44TSoQY"
    assert converted["input"][1]["content"][0]["text"] == "first reply"


def test_convert_to_responses_payload_preserves_valid_stored_message_item_ids():
    payload = {
        "model": "openai/gpt-5.4",
        "messages": [
            {
                "role": "assistant",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_existing123",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": "cached reply"},
                        ],
                    }
                ],
            }
        ],
    }

    converted = convert_to_responses_payload(payload)

    assert converted["input"] == [
        {
            "type": "message",
            "id": "msg_existing123",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": "cached reply"}],
        }
    ]


def test_convert_to_responses_payload_anchors_on_stored_response_id():
    payload = {
        "model": "openai/gpt-5.4",
        "messages": [
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
                        "content": [
                            {"type": "output_text", "text": "cached reply"},
                        ],
                    }
                ],
            },
            {"role": "user", "content": "What changed?"},
        ],
    }

    converted = convert_to_responses_payload(payload)

    assert converted["previous_response_id"] == "resp_123"
    assert converted["instructions"] == "You are precise."
    assert converted["input"] == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "What changed?"}],
        }
    ]


def test_convert_to_responses_payload_maps_reasoning_effort_to_reasoning_object():
    payload = {
        "model": "openai/gpt-5.4",
        "reasoning_effort": "xhigh",
        "messages": [{"role": "user", "content": "hello"}],
    }

    converted = convert_to_responses_payload(payload)

    assert converted["reasoning"] == {"effort": "xhigh", "summary": "auto"}
    assert "reasoning_effort" not in converted


def test_normalize_responses_payload_preserves_existing_reasoning_fields():
    payload = {
        "model": "openai/gpt-5.4",
        "input": [],
        "reasoning_effort": "high",
        "reasoning": {"summary": "auto"},
    }

    converted = normalize_responses_payload(payload)

    assert converted["reasoning"] == {"summary": "auto", "effort": "high"}
    assert "reasoning_effort" not in converted


def test_convert_to_responses_payload_defaults_reasoning_summary_for_reasoning_models():
    payload = {
        "model": "gpt-5.4",
        "messages": [{"role": "user", "content": "hello"}],
    }

    converted = convert_to_responses_payload(payload)

    assert converted["reasoning"] == {"summary": "auto"}


def test_normalize_responses_payload_preserves_explicit_reasoning_summary():
    payload = {
        "model": "gpt-5.4",
        "input": [],
        "reasoning": {"summary": "detailed"},
    }

    converted = normalize_responses_payload(payload)

    assert converted["reasoning"] == {"summary": "detailed"}


def test_is_openai_reasoning_model_accepts_prefixed_model_ids():
    assert is_openai_reasoning_model("openai/gpt-5.4") is True


def test_openai_reasoning_model_handler_keeps_prefixed_o1_mini_on_user_role():
    payload = {
        "model": "openai/o1-mini",
        "messages": [
            {"role": "system", "content": "You are precise."},
            {"role": "user", "content": "hello"},
        ],
    }

    converted = openai_reasoning_model_handler(payload)

    assert converted["messages"][0]["role"] == "user"
