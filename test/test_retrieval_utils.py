from types import SimpleNamespace

import pytest

from open_webui.retrieval import utils


@pytest.mark.asyncio
async def test_get_sources_from_items_uses_web_search_collection(monkeypatch):
    queried = []

    async def fake_query_collection(*args, **kwargs):
        queried.extend(kwargs['collection_names'])
        return {
            'documents': [['search result content']],
            'metadatas': [[{'source': 'https://example.com'}]],
            'distances': [[0.9]],
        }

    monkeypatch.setattr(utils, 'query_collection', fake_query_collection)

    request = SimpleNamespace()
    user = SimpleNamespace(id='user-1', role='user')

    sources = await utils.get_sources_from_items(
        request,
        items=[
            {
                'type': 'web_search',
                'collection_name': 'web-search-test',
                'name': 'weather query',
                'queries': ['weather query'],
            }
        ],
        queries=['weather query'],
        embedding_function=lambda *args, **kwargs: None,
        k=3,
        reranking_function=None,
        k_reranker=3,
        r=0.0,
        hybrid_bm25_weight=0.5,
        hybrid_search=False,
        user=user,
    )

    assert queried == ['web-search-test']
    assert sources[0]['document'] == ['search result content']
    assert sources[0]['source']['type'] == 'web_search'


@pytest.mark.asyncio
async def test_get_sources_from_items_uses_web_search_docs(monkeypatch):
    async def fake_query_collection(*args, **kwargs):
        raise AssertionError('web search docs should not query vector collections')

    monkeypatch.setattr(utils, 'query_collection', fake_query_collection)

    request = SimpleNamespace()
    user = SimpleNamespace(id='user-1', role='user')

    sources = await utils.get_sources_from_items(
        request,
        items=[
            {
                'type': 'web_search',
                'docs': [
                    {
                        'content': 'direct web search content',
                        'metadata': {'source': 'https://example.com/direct'},
                    }
                ],
            }
        ],
        queries=['weather query'],
        embedding_function=lambda *args, **kwargs: None,
        k=3,
        reranking_function=None,
        k_reranker=3,
        r=0.0,
        hybrid_bm25_weight=0.5,
        hybrid_search=False,
        user=user,
    )

    assert sources[0]['document'] == ['direct web search content']
    assert sources[0]['metadata'] == [{'source': 'https://example.com/direct'}]
    assert sources[0]['source']['type'] == 'web_search'
