from types import SimpleNamespace

import pytest

from open_webui.retrieval.source import (
    get_first_source_url_metadata,
    get_file_source_url_metadata,
    get_source_url_from_metadata,
    get_source_url_metadata,
    is_valid_url_hostname,
    merge_source_url_metadata,
    normalize_source_url,
)


def _file(meta, filename='uploaded.pdf'):
    return SimpleNamespace(meta=meta, filename=filename)


def test_get_source_url_from_metadata_uses_nested_api_source_url_metadata():
    source_url = 'https://gitlab.example.com/group/project/-/blob/main/docs/spec.pdf'

    assert get_source_url_from_metadata({'data': {'source_url': source_url}}) == source_url


def test_get_source_url_from_metadata_prefers_explicit_source_url_keys():
    meta = {
        'sourceUrl': 'https://example.com/top-level-source-url',
        'data': {
            'source_url': 'https://example.com/nested-source-url',
        },
    }

    assert get_source_url_from_metadata(meta) == 'https://example.com/top-level-source-url'


def test_get_source_url_metadata_returns_empty_dict_for_missing_source_url():
    meta = {
        'source_url': '   ',
        'url': 'https://example.com/generic-url-is-not-source-url',
    }

    assert get_source_url_metadata(meta) == {}


@pytest.mark.parametrize(
    'source_url',
    [
        None,
        '',
        '   ',
        123,
        [],
        {},
        '/relative/path',
        '//example.com/missing-scheme',
        'gitlab.example.com/group/project',
        'https:///missing-host',
        'https://exa mple.com/path',
        'https://example.com/path with spaces',
        'https://example.com\\@evil.example/path',
        'https://example.com\\path',
        'https://[::1',
        'https://%zz',
        'https://example.com:bad/path',
        'https://user@example.com/path',
        'https://user:pass@example.com/path',
        'https://.com',
        'https://example..com',
        'javascript:alert(1)',
        'data:text/html,<script>alert(1)</script>',
        'file:///etc/passwd',
        'blob:https://example.com/source-id',
        'mailto:user@example.com',
    ],
)
def test_normalize_source_url_rejects_invalid_or_non_http_urls(source_url):
    assert normalize_source_url(source_url) is None
    assert get_source_url_metadata({'source_url': source_url}) == {}


def test_normalize_source_url_accepts_http_https_and_preserves_encoded_characters():
    http_url = 'http://gitlab.example.com/group/project/-/blob/main/docs/spec.pdf'
    encoded_url = 'https://gitlab.example.com/docs/spec%20file.pdf?ref=%3Cmain%3E'

    assert normalize_source_url(http_url) == http_url
    assert normalize_source_url(encoded_url) == encoded_url


def test_normalize_source_url_trims_and_accepts_source_url_alias():
    source_url = 'https://gitlab.example.com/group/project/-/blob/main/docs/spec.pdf'

    assert normalize_source_url(f'  {source_url}  ') == source_url
    assert get_source_url_from_metadata({'sourceURL': source_url}) == source_url


def test_normalize_source_url_accepts_local_and_ip_hosts():
    localhost_url = 'https://localhost/docs/spec.pdf'
    ipv4_url = 'http://192.168.1.10/docs/spec.pdf'
    ipv6_url = 'https://[2001:db8::1]/docs/spec.pdf'

    assert normalize_source_url(localhost_url) == localhost_url
    assert normalize_source_url(ipv4_url) == ipv4_url
    assert normalize_source_url(ipv6_url) == ipv6_url


def test_is_valid_url_hostname_handles_idn_hostnames():
    assert is_valid_url_hostname('münich.example')


def test_get_first_source_url_metadata_preserves_upload_meta_when_content_metadata_exists():
    source_url = 'https://gitlab.example.com/group/project/-/blob/main/docs/spec.pdf'
    file_metadata = {'data': {'source_url': source_url}}
    content_metadata = {'source': 'uploaded.pdf'}

    assert get_first_source_url_metadata(file_metadata, content_metadata) == {
        'source_url': source_url
    }


def test_get_first_source_url_metadata_falls_back_to_content_metadata():
    source_url = 'https://gitlab.example.com/group/project/-/blob/main/docs/spec.pdf'

    assert get_first_source_url_metadata({}, {'source_url': source_url}) == {
        'source_url': source_url
    }


def test_get_file_source_url_metadata_promotes_nested_source_url():
    source_url = 'https://gitlab.example.com/group/project/-/blob/main/docs/spec.pdf'

    assert get_file_source_url_metadata(_file({'data': {'source_url': source_url}})) == {
        'source_url': source_url
    }


def test_merge_source_url_metadata_adds_missing_source_url_without_overwriting_existing_metadata():
    source_url = 'https://gitlab.example.com/group/project/-/blob/main/docs/spec.pdf'
    existing_source_url = 'https://example.com/already-indexed'

    assert merge_source_url_metadata({'name': 'spec.pdf'}, {'source_url': source_url}) == {
        'name': 'spec.pdf',
        'source_url': source_url,
    }
    assert merge_source_url_metadata(
        {'source_url': existing_source_url},
        {'source_url': source_url},
    ) == {'source_url': existing_source_url}
