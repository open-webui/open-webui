from urllib.parse import urlparse

import validators


def is_valid_search_result_url(url: str | None) -> bool:
    if not url:
        return False

    if isinstance(validators.url(url), validators.ValidationError):
        return False

    if any(ch in url for ch in ('\\', '\t', '\n', '\r')):
        return False

    parsed_url = urlparse(url)
    return parsed_url.scheme in ('http', 'https')
