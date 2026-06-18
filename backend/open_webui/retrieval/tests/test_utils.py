import os
from types import SimpleNamespace

import pytest

os.environ.setdefault('WEBUI_SECRET_KEY', 'test-secret-key')

from open_webui.retrieval import utils


@pytest.mark.asyncio
async def test_get_sources_from_items_retrieves_web_search_collection(monkeypatch):
    async def mock_filter_accessible_collections(collection_names, user, access_type='read'):
        return {name for name in collection_names if name.startswith('web-search-')}

    async def mock_query_collection(request, collection_names, queries, embedding_function, k):
        assert collection_names == {'web-search-example'}
        assert queries == ['test query']

        return {
            'documents': [['search result content']],
            'metadatas': [[{'source': 'https://example.com', 'title': 'Example'}]],
        }

    monkeypatch.setattr(utils, 'filter_accessible_collections', mock_filter_accessible_collections)
    monkeypatch.setattr(utils, 'query_collection', mock_query_collection)

    sources = await utils.get_sources_from_items(
        request=SimpleNamespace(),
        items=[
            {
                'type': 'web_search',
                'collection_name': 'web-search-example',
                'name': 'test query',
                'urls': ['https://example.com'],
            }
        ],
        queries=['test query'],
        embedding_function=lambda query, prefix=None: [],
        k=3,
        reranking_function=None,
        k_reranker=3,
        r=0.0,
        hybrid_bm25_weight=0.5,
        hybrid_search=False,
        user=SimpleNamespace(id='user-id', role='user'),
    )

    assert sources == [
        {
            'source': {
                'type': 'web_search',
                'collection_name': 'web-search-example',
                'name': 'test query',
                'urls': ['https://example.com'],
            },
            'document': ['search result content'],
            'metadata': [{'source': 'https://example.com', 'title': 'Example'}],
        }
    ]
