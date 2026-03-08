from open_webui.routers.openai import convert_to_responses_payload


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
