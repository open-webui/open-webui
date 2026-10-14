from open_webui.retrieval.web.main import SearchResult, web_search_result_metadata
from open_webui.retrieval.web.perplexity_search import search_perplexity_search
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.middleware import (
    get_citation_source_from_tool_result,
    get_display_sources_from_tool_result,
    get_source_context,
)


def test_provider_publisher_is_normalized_and_preferred_for_display():
    result = SearchResult.from_provider_result(
        {
            'title': 'Research update',
            'url': 'https://www.example.com/research',
            'snippet': 'An update.',
            'publisher': {'name': 'Example Research'},
        }
    )

    assert result.model_dump() == {
        'link': 'https://www.example.com/research',
        'title': 'Research update',
        'snippet': 'An update.',
        'name': 'Research update',
        'publisher': ['Example Research'],
        'display_name': 'Example Research',
    }


def test_hostname_fallback_strips_only_leading_www():
    result = SearchResult(link='https://www.news.example.co.uk/story', title='Story', snippet='Text')

    assert result.publisher == ['news.example.co.uk']
    assert result.display_name == 'news.example.co.uk'


def test_missing_or_malformed_urls_do_not_fabricate_publishers():
    for url in ('', 'not a url', 'http://localhost/page', 'https://10.0.0.1/page'):
        result = SearchResult(link=url, title='Page title', snippet=None)

        assert result.publisher == []
        assert result.display_name == 'Page title'


def test_common_ddgs_schema_preserves_page_title_and_name():
    result = SearchResult.from_provider_result(
        {
            'title': 'DuckDuckGo result title',
            'href': 'https://docs.example.com/page',
            'body': 'Result body',
        }
    )

    assert result.title == 'DuckDuckGo result title'
    assert result.name == 'DuckDuckGo result title'
    assert result.snippet == 'Result body'


def test_perplexity_site_name_uses_same_normalizer():
    result = SearchResult.from_provider_result(
        {
            'title': 'Perplexity result title',
            'url': 'https://example.com/page',
            'snippet': 'Result snippet',
            'site_name': 'Example News',
        }
    )

    assert result.publisher == ['Example News']
    assert result.display_name == 'Example News'


def test_perplexity_search_path_returns_normalized_results(monkeypatch):
    class FakeResponse:
        @staticmethod
        def json():
            return {
                'results': [
                    {
                        'title': 'Perplexity result title',
                        'url': 'https://www.perplexity-result.example/page',
                        'snippet': 'Result snippet',
                    }
                ]
            }

    monkeypatch.setattr(
        'open_webui.retrieval.web.perplexity_search.requests.request',
        lambda *args, **kwargs: FakeResponse(),
    )

    [result] = search_perplexity_search('test-key', 'query', 1)

    assert result.name == 'Perplexity result title'
    assert result.publisher == ['perplexity-result.example']
    assert result.display_name == 'perplexity-result.example'


def test_metadata_normalization_preserves_source_matching_key():
    result = SearchResult(
        link='https://www.example.com/article',
        title='Article title',
        snippet='Article snippet',
        publisher=['Example Publishing'],
    )

    metadata = web_search_result_metadata(
        result,
        {
            'source': 'https://www.example.com/article',
            'loader_field': 'preserved',
        },
    )

    assert metadata == {
        'source': 'https://www.example.com/article',
        'loader_field': 'preserved',
        'link': 'https://www.example.com/article',
        'url': 'https://www.example.com/article',
        'title': 'Article title',
        'name': 'Article title',
        'publisher': ['Example Publishing'],
        'display_name': 'Example Publishing',
        'snippet': 'Article snippet',
    }


def test_native_search_results_become_one_display_only_source_per_url():
    sources = get_display_sources_from_tool_result(
        'search_web',
        JSONCodec.dumps(
            [
                {
                    'url': 'https://www.example.com/article',
                    'title': 'Article title',
                    'content': 'Article snippet',
                    'publisher': {'name': 'Example Publishing'},
                },
                {
                    'link': 'https://www.example.com/article',
                    'title': 'Duplicate URL',
                    'snippet': 'Duplicate snippet',
                },
                {
                    'href': 'https://docs.example.org/guide',
                    'name': 'Guide',
                    'description': 'Guide snippet',
                },
            ]
        ),
    )

    assert [source['source']['url'] for source in sources] == [
        'https://www.example.com/article',
        'https://docs.example.org/guide',
    ]
    assert sources[0] == {
        'source': {
            'id': 'https://www.example.com/article',
            'name': 'Article title',
            'display_name': 'Example Publishing',
            'type': 'web_search',
            'url': 'https://www.example.com/article',
            'citable': False,
            'fetched': False,
        },
        'document': ['Article snippet'],
        'metadata': [
            {
                'source': 'https://www.example.com/article',
                'link': 'https://www.example.com/article',
                'url': 'https://www.example.com/article',
                'title': 'Article title',
                'name': 'Article title',
                'publisher': ['Example Publishing'],
                'display_name': 'Example Publishing',
                'snippet': 'Article snippet',
                'citable': False,
                'fetched': False,
                'provenance': 'web_search',
            }
        ],
    }


def test_native_search_display_sources_ignore_errors_and_malformed_entries():
    assert get_display_sources_from_tool_result('search_web', JSONCodec.dumps({'error': 'failed'})) == []
    assert (
        get_display_sources_from_tool_result(
            'search_web',
            JSONCodec.dumps(
                [
                    {'error': 'provider failed'},
                    None,
                    'not an object',
                    {'title': 'Missing URL', 'snippet': 'No link'},
                    {'link': 'not a URL', 'title': 'Malformed URL'},
                    {'link': 'http://localhost/private', 'title': 'Non-public URL'},
                ]
            ),
        )
        == []
    )


def test_native_search_display_sources_never_enter_model_source_context():
    display_sources = get_display_sources_from_tool_result(
        'search_web',
        JSONCodec.dumps(
            [
                {
                    'link': 'https://example.com/result',
                    'title': 'Unfetched result',
                    'snippet': 'Search-engine snippet only',
                }
            ]
        ),
    )
    fetched_sources = get_citation_source_from_tool_result(
        'fetch_url',
        {'url': 'https://example.com/fetched'},
        'Fetched page content',
    )

    assert get_source_context(display_sources, include_content=False) == ''
    assert get_source_context(fetched_sources, include_content=False).startswith(
        '<source id="1" name="https://example.com/fetched"'
    )
