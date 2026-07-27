import urllib.parse


def normalize_oauth_metadata(metadata: dict, metadata_url: str) -> dict:
    normalized = dict(metadata)
    parsed_url = urllib.parse.urlparse(metadata_url)
    origin = f'{parsed_url.scheme}://{parsed_url.netloc}'
    normalized.setdefault('issuer', origin)

    for field, value in normalized.items():
        if isinstance(value, str) and (field == 'issuer' or field.endswith('_endpoint') or field == 'jwks_uri'):
            normalized[field] = urllib.parse.urljoin(f'{origin}/', value)

    return normalized
