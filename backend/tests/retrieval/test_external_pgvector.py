from types import SimpleNamespace

import pytest
from open_webui.retrieval.external import _retrieve_pgvector


@pytest.mark.asyncio
async def test_retrieve_pgvector_passes_query_embedding_as_pgvector_vector(monkeypatch):
    import pgvector.psycopg
    import psycopg
    from pgvector import Vector

    captured = {}

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            captured['params'] = params

        def fetchall(self):
            return [
                {
                    'id': 'doc-1',
                    'content': 'matched content',
                    'metadata': {},
                    'distance': 0.1,
                }
            ]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(psycopg, 'connect', lambda *args, **kwargs: FakeConnection())
    monkeypatch.setattr(pgvector.psycopg, 'register_vector', lambda conn: None)

    async def embedding_function(query):
        return [0.1, 0.2, 0.3]

    knowledge = SimpleNamespace(
        id='knowledge-1',
        name='External KB',
        meta={
            'external': {
                'source': {
                    'name': 'support_docs',
                    'config': {
                        'table_name': 'public.document_chunks',
                        'vector_field': 'embedding',
                    },
                }
            }
        },
    )

    result = await _retrieve_pgvector(
        {'endpoint': 'postgresql://example/db', 'config': {}},
        {},
        knowledge,
        'reset password',
        1,
        embedding_function,
    )

    assert isinstance(captured['params'][0], Vector)
    assert result[0]['content'] == 'matched content'
