def convert_image_url_to_response_part(image_url: object) -> dict[str, object]:
    """Convert a Chat Completions image part to Responses API format."""
    if isinstance(image_url, dict):
        url = image_url.get('url', '')
        detail = image_url.get('detail') or 'auto'
    else:
        url = image_url
        detail = 'auto'

    return {'type': 'input_image', 'image_url': url, 'detail': detail}
