"""
Regression test for issue #28286:
convert_to_responses_payload() drops the source `detail` value when converting a Chat
Completions `image_url` content part to a Responses API `input_image` part, and emits
no compatibility default. Strict Responses implementations (e.g. vLLM 0.26.0) reject
the converted request with HTTP 400 during Pydantic validation.

This test replicates the image_url handling branch of
backend/open_webui/routers/openai.py (must stay in sync) because importing the router
module requires the full application dependency stack.
"""

import pytest


def convert_image_url_part(part: dict) -> dict:
    """Replicated image_url branch from convert_to_responses_payload (keep in sync)."""
    url_data = part.get('image_url', {})
    if isinstance(url_data, dict):
        url = url_data.get('url', '')
        image_item = {
            'type': 'input_image',
            'image_url': url,
            'detail': url_data.get('detail') or 'auto',
        }
    else:
        image_item = {
            'type': 'input_image',
            'image_url': url_data,
            'detail': 'auto',
        }
    return image_item


class TestImageUrlDetail:
    def test_preserves_source_detail_value(self):
        part = {
            'type': 'image_url',
            'image_url': {'url': 'data:image/png;base64,AAAA', 'detail': 'high'},
        }
        assert convert_image_url_part(part) == {
            'type': 'input_image',
            'image_url': 'data:image/png;base64,AAAA',
            'detail': 'high',
        }

    def test_defaults_detail_to_auto_when_absent(self):
        part = {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,AAAA'}}
        assert convert_image_url_part(part)['detail'] == 'auto'

    def test_defaults_detail_to_auto_for_string_form(self):
        part = {'type': 'image_url', 'image_url': 'data:image/png;base64,AAAA'}
        assert convert_image_url_part(part) == {
            'type': 'input_image',
            'image_url': 'data:image/png;base64,AAAA',
            'detail': 'auto',
        }

    def test_treats_null_detail_as_absent(self):
        part = {
            'type': 'image_url',
            'image_url': {'url': 'data:image/png;base64,AAAA', 'detail': None},
        }
        assert convert_image_url_part(part)['detail'] == 'auto'

