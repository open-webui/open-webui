import pytest
from open_webui.routers.openai import convert_to_responses_payload


def test_convert_to_responses_payload_preserves_image_detail():
    # 1. Test image_url dict with explicit detail="high"
    payload_high = {
        "model": "test-vision-model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
    }

    res_high = convert_to_responses_payload(payload_high)
    parts_high = res_high["input"][0]["content"]
    assert len(parts_high) == 2
    assert parts_high[1]["type"] == "input_image"
    assert parts_high[1]["detail"] == "high"
    assert "data:image/png;base64" in parts_high[1]["image_url"]

    # 2. Test image_url dict without detail -> defaults to "auto"
    payload_no_detail = {
        "model": "test-vision-model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://example.com/test.png",
                        },
                    }
                ],
            }
        ],
    }

    res_no_detail = convert_to_responses_payload(payload_no_detail)
    parts_no_detail = res_no_detail["input"][0]["content"]
    assert parts_no_detail[0]["type"] == "input_image"
    assert parts_no_detail[0]["detail"] == "auto"
    assert parts_no_detail[0]["image_url"] == "https://example.com/test.png"

    # 3. Test string image_url form -> defaults to "auto"
    payload_str_url = {
        "model": "test-vision-model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": "https://example.com/string-url.png",
                    }
                ],
            }
        ],
    }

    res_str_url = convert_to_responses_payload(payload_str_url)
    parts_str_url = res_str_url["input"][0]["content"]
    assert parts_str_url[0]["type"] == "input_image"
    assert parts_str_url[0]["detail"] == "auto"
    assert parts_str_url[0]["image_url"] == "https://example.com/string-url.png"
