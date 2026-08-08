import pytest

from open_webui.utils.openai_responses import convert_image_url_to_response_part


@pytest.mark.parametrize(
    ('image_url', 'expected_detail'),
    [
        ({'url': 'data:image/png;base64,AAAA'}, 'auto'),
        ({'url': 'data:image/png;base64,AAAA', 'detail': 'high'}, 'high'),
        ('data:image/png;base64,AAAA', 'auto'),
    ],
)
def test_convert_image_url_to_response_part_preserves_detail(
    image_url: dict[str, str] | str, expected_detail: str
) -> None:
    assert convert_image_url_to_response_part(image_url) == {
        'type': 'input_image',
        'image_url': 'data:image/png;base64,AAAA',
        'detail': expected_detail,
    }
