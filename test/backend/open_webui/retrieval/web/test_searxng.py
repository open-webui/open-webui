import os
import tempfile

os.environ.setdefault('WEBUI_SECRET_KEY', 'test-secret-key')
os.environ.setdefault('STATIC_DIR', tempfile.mkdtemp())

from open_webui.retrieval.web.searxng import _normalize_query_url


def test_normalize_query_url_keeps_search_path():
    query_url, params = _normalize_query_url('http://127.0.0.1:80/searxng/search')

    assert query_url == 'http://127.0.0.1:80/searxng/search'
    assert params == {}


def test_normalize_query_url_preserves_non_query_options():
    query_url, params = _normalize_query_url(
        'http://127.0.0.1:80/searxng/search?categories=general&language=en'
    )

    assert query_url == 'http://127.0.0.1:80/searxng/search'
    assert params == {'categories': 'general', 'language': 'en'}


def test_normalize_query_url_removes_legacy_query_placeholder():
    query_url, params = _normalize_query_url(
        'http://127.0.0.1:80/searxng/search?q=<query>&format=json'
    )

    assert query_url == 'http://127.0.0.1:80/searxng/search'
    assert params == {'format': 'json'}