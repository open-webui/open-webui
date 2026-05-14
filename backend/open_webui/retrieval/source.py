import ipaddress
import re
from urllib.parse import urlparse


SOURCE_URL_METADATA_KEYS = ('source_url', 'source-url', 'sourceUrl', 'sourceURL')
HOST_LABEL_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$')


def is_valid_url_hostname(hostname: str | None) -> bool:
    if not hostname:
        return False

    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        pass

    try:
        hostname = hostname.encode('idna').decode('ascii')
    except UnicodeError:
        return False

    if hostname.endswith('.'):
        hostname = hostname[:-1]

    if not hostname or len(hostname) > 253:
        return False

    return all(HOST_LABEL_RE.match(label) for label in hostname.split('.'))


def normalize_source_url(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value or '\\' in value or any(char.isspace() or ord(char) < 32 for char in value):
        return None

    try:
        parsed = urlparse(value)
        parsed.port
    except ValueError:
        return None

    if (
        parsed.scheme not in {'http', 'https'}
        or not parsed.netloc
        or not is_valid_url_hostname(parsed.hostname)
        or parsed.username
        or parsed.password
    ):
        return None

    return value


def get_source_url_from_metadata(metadata: dict | None) -> str | None:
    if not isinstance(metadata, dict):
        return None

    nested_metadata = metadata.get('data') if isinstance(metadata.get('data'), dict) else {}

    for values in (metadata, nested_metadata):
        for key in SOURCE_URL_METADATA_KEYS:
            source_url = normalize_source_url(values.get(key))
            if source_url:
                return source_url

    return None


def get_source_url_metadata(metadata: dict | None) -> dict:
    source_url = get_source_url_from_metadata(metadata)
    return {'source_url': source_url} if source_url else {}


def get_first_source_url_metadata(*metadata_items: dict | None) -> dict:
    for metadata in metadata_items:
        source_url = get_source_url_from_metadata(metadata)
        if source_url:
            return {'source_url': source_url}

    return {}


def get_file_source_url_metadata(file) -> dict:
    return get_source_url_metadata(getattr(file, 'meta', None))


def merge_source_url_metadata(metadata: dict | None, source_metadata: dict | None) -> dict:
    metadata = metadata if isinstance(metadata, dict) else {}
    return {**get_source_url_metadata(source_metadata), **metadata}
