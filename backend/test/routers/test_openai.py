from copy import deepcopy

from open_webui.routers.openai import convert_to_responses_payload


def _convert(image_url: object) -> dict:
    payload = {
        'messages': [
            {
                'role': 'user',
                'content': [{'type': 'image_url', 'image_url': image_url}],
            }
        ]
    }
    result = convert_to_responses_payload(deepcopy(payload))
    return result['input'][0]['content'][0]


def test_image_object_without_detail_defaults_to_auto() -> None:
    assert _convert({'url': 'data:image/png;base64,abc'}) == {
        'type': 'input_image',
        'image_url': 'data:image/png;base64,abc',
        'detail': 'auto',
    }


def test_image_object_preserves_explicit_detail() -> None:
    assert _convert({'url': 'https://example.test/image.png', 'detail': 'high'}) == {
        'type': 'input_image',
        'image_url': 'https://example.test/image.png',
        'detail': 'high',
    }


def test_string_image_url_defaults_to_auto() -> None:
    assert _convert('https://example.test/image.png') == {
        'type': 'input_image',
        'image_url': 'https://example.test/image.png',
        'detail': 'auto',
    }
