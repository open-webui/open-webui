from types import SimpleNamespace

import pytest

from open_webui.retrieval import utils


@pytest.mark.asyncio
async def test_get_sources_from_items_queries_web_search_collection(monkeypatch):
    captured = {}

    async def fake_filter_accessible_collections(collection_names, user):
        captured['filtered_collection_names'] = collection_names
        return collection_names

    async def fake_query_collection(request, collection_names, queries, embedding_function, k):
        captured['queried_collection_names'] = collection_names
        captured['queries'] = queries
        return {
            'documents': [['current web result']],
            'metadatas': [[{'source': 'https://example.com/news'}]],
        }

    monkeypatch.setattr(utils, 'filter_accessible_collections', fake_filter_accessible_collections)
    monkeypatch.setattr(utils, 'query_collection', fake_query_collection)

    user = SimpleNamespace(id='user-id', role='user')
    sources = await utils.get_sources_from_items(
        request=SimpleNamespace(),
        items=[
            {
                'type': 'web_search',
                'collection_name': 'web-search-current-ai-news',
                'name': 'current AI news',
            }
        ],
        queries=['current AI news'],
        embedding_function=None,
        k=3,
        reranking_function=None,
        k_reranker=0,
        r=0.0,
        hybrid_bm25_weight=0.0,
        hybrid_search=False,
        user=user,
    )

    assert captured['filtered_collection_names'] == {'web-search-current-ai-news'}
    assert captured['queried_collection_names'] == {'web-search-current-ai-news'}
    assert captured['queries'] == ['current AI news']
    assert sources == [
        {
            'source': {
                'type': 'web_search',
                'collection_name': 'web-search-current-ai-news',
                'name': 'current AI news',
            },
            'document': ['current web result'],
            'metadata': [{'source': 'https://example.com/news'}],
        }
    ]
