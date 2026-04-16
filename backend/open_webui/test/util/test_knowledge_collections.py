import asyncio
from types import SimpleNamespace

from open_webui.utils.knowledge_collections import reindex_file_in_collection


def test_reindex_file_in_collection_deletes_old_ids_only_after_success():
    calls = []

    class DummyVectorDB:
        async def query(self, collection_name, filter, limit=None):
            calls.append(('query', collection_name, filter))
            return SimpleNamespace(ids=[['old-1', 'old-2']])

        async def delete(self, collection_name, ids=None, filter=None):
            calls.append(('delete', collection_name, ids, filter))

    async def fake_process_file(request, form, user, db):
        calls.append(('process_file', form.file_id, form.collection_name))

    class DummyProcessFileForm:
        def __init__(self, file_id, collection_name=None):
            self.file_id = file_id
            self.collection_name = collection_name

    asyncio.run(
        reindex_file_in_collection(
            request=object(),
            file_id='file-1',
            collection_name='kb-1',
            user=object(),
            db=None,
            process_file_form_factory=DummyProcessFileForm,
            process_file_func=fake_process_file,
            vector_db_client=DummyVectorDB(),
        )
    )

    assert calls == [
        ('query', 'kb-1', {'file_id': 'file-1'}),
        ('process_file', 'file-1', 'kb-1'),
        ('delete', 'kb-1', ['old-1', 'old-2'], None),
    ]


def test_reindex_file_in_collection_preserves_old_ids_when_rebuild_fails():
    calls = []

    class DummyVectorDB:
        async def query(self, collection_name, filter, limit=None):
            calls.append(('query', collection_name, filter))
            return SimpleNamespace(ids=[['old-1']])

        async def delete(self, collection_name, ids=None, filter=None):
            calls.append(('delete', collection_name, ids, filter))

    async def fake_process_file(request, form, user, db):
        calls.append(('process_file', form.file_id, form.collection_name))
        raise RuntimeError('reindex failed')

    class DummyProcessFileForm:
        def __init__(self, file_id, collection_name=None):
            self.file_id = file_id
            self.collection_name = collection_name

    try:
        asyncio.run(
            reindex_file_in_collection(
                request=object(),
                file_id='file-1',
                collection_name='kb-1',
                user=object(),
                db=None,
                process_file_form_factory=DummyProcessFileForm,
                process_file_func=fake_process_file,
                vector_db_client=DummyVectorDB(),
            )
        )
        raise AssertionError('Expected reindex_file_in_collection to raise RuntimeError')
    except RuntimeError as exc:
        assert str(exc) == 'reindex failed'

    assert calls == [
        ('query', 'kb-1', {'file_id': 'file-1'}),
        ('process_file', 'file-1', 'kb-1'),
    ]
