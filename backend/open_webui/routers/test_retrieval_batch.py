from types import SimpleNamespace

import pytest
from open_webui.constants import ERROR_MESSAGES
from open_webui.models.files import FileModel
from open_webui.routers import knowledge as knowledge_router
from open_webui.routers import retrieval
from open_webui.utils.misc import calculate_sha256_string


def make_file(file_id: str, content: str, user_id: str = 'user-1') -> FileModel:
    return FileModel(
        id=file_id,
        user_id=user_id,
        filename=f'{file_id}.txt',
        path=None,
        data={'content': content},
        meta={},
        created_at=1,
        updated_at=1,
    )


class User:
    id = 'user-1'
    role = 'user'


def test_vector_result_duplicate_detection_ignores_same_file():
    result = SimpleNamespace(
        ids=[['chunk-1']],
        metadatas=[[{'file_id': 'file-1'}]],
    )

    assert retrieval.vector_result_has_hash_for_other_file(result, 'file-1') is False


def test_vector_result_duplicate_detection_finds_other_file():
    result = SimpleNamespace(
        ids=[['chunk-1', 'chunk-2']],
        metadatas=[[{'file_id': 'file-1'}, {'file_id': 'file-2'}]],
    )

    assert retrieval.vector_result_has_hash_for_other_file(result, 'file-1') is True


def test_vector_result_duplicate_detection_treats_missing_metadata_as_duplicate():
    result = SimpleNamespace(ids=[['chunk-1']], metadatas=[[]])

    assert retrieval.vector_result_has_hash_for_other_file(result, 'file-1') is True


@pytest.mark.asyncio
async def test_process_files_batch_skips_existing_collection_hash(monkeypatch):
    file = make_file('file-1', 'duplicate content')

    async def get_file_by_id(file_id, db=None):
        return file

    async def validate_collection_access(collection_names, user, access_type='read'):
        return None

    async def run_in_threadpool(fn, *args, **kwargs):
        if fn is retrieval.vector_collection_has_hash_for_other_file:
            return True

        raise AssertionError('duplicate files should not be embedded')

    monkeypatch.setattr(retrieval.Files, 'get_file_by_id', get_file_by_id)
    monkeypatch.setattr(retrieval, '_validate_collection_access', validate_collection_access)
    monkeypatch.setattr(retrieval, 'run_in_threadpool', run_in_threadpool)

    result = await retrieval.process_files_batch(
        request=SimpleNamespace(),
        form_data=retrieval.BatchProcessFilesForm(files=[file], collection_name='knowledge-1'),
        user=User(),
        db=None,
    )

    assert result.results == []
    assert len(result.errors) == 1
    assert result.errors[0].file_id == 'file-1'
    assert result.errors[0].error == ERROR_MESSAGES.DUPLICATE_CONTENT


@pytest.mark.asyncio
async def test_process_files_batch_adds_hash_metadata_and_updates_files(monkeypatch):
    first = make_file('file-1', 'first content')
    second = make_file('file-2', 'second content')
    saved_docs = []
    file_updates = {}

    async def get_file_by_id(file_id, db=None):
        return {'file-1': first, 'file-2': second}[file_id]

    async def update_file_by_id(id, form_data, db=None):
        file_updates[id] = form_data
        return None

    async def validate_collection_access(collection_names, user, access_type='read'):
        return None

    async def run_in_threadpool(fn, *args, **kwargs):
        if fn is retrieval.vector_collection_has_hash_for_other_file:
            return False
        if fn is retrieval.save_docs_to_vector_db:
            saved_docs.extend(args[1])
            return True

        raise AssertionError(f'unexpected threaded call: {fn}')

    monkeypatch.setattr(retrieval.Files, 'get_file_by_id', get_file_by_id)
    monkeypatch.setattr(retrieval.Files, 'update_file_by_id', update_file_by_id)
    monkeypatch.setattr(retrieval, '_validate_collection_access', validate_collection_access)
    monkeypatch.setattr(retrieval, 'run_in_threadpool', run_in_threadpool)

    result = await retrieval.process_files_batch(
        request=SimpleNamespace(),
        form_data=retrieval.BatchProcessFilesForm(files=[first, second], collection_name='knowledge-1'),
        user=User(),
        db=None,
    )

    assert [item.status for item in result.results] == ['completed', 'completed']
    assert result.errors == []
    assert [doc.metadata['hash'] for doc in saved_docs] == [
        calculate_sha256_string('first content'),
        calculate_sha256_string('second content'),
    ]
    assert file_updates['file-1'].hash == calculate_sha256_string('first content')
    assert file_updates['file-2'].hash == calculate_sha256_string('second content')


@pytest.mark.asyncio
async def test_process_files_batch_skips_duplicate_hash_inside_same_batch(monkeypatch):
    first = make_file('file-1', 'same content')
    second = make_file('file-2', 'same content')
    saved_docs = []

    async def get_file_by_id(file_id, db=None):
        return {'file-1': first, 'file-2': second}[file_id]

    async def update_file_by_id(id, form_data, db=None):
        return None

    async def validate_collection_access(collection_names, user, access_type='read'):
        return None

    async def run_in_threadpool(fn, *args, **kwargs):
        if fn is retrieval.vector_collection_has_hash_for_other_file:
            return False
        if fn is retrieval.save_docs_to_vector_db:
            saved_docs.extend(args[1])
            return True

        raise AssertionError(f'unexpected threaded call: {fn}')

    monkeypatch.setattr(retrieval.Files, 'get_file_by_id', get_file_by_id)
    monkeypatch.setattr(retrieval.Files, 'update_file_by_id', update_file_by_id)
    monkeypatch.setattr(retrieval, '_validate_collection_access', validate_collection_access)
    monkeypatch.setattr(retrieval, 'run_in_threadpool', run_in_threadpool)

    result = await retrieval.process_files_batch(
        request=SimpleNamespace(),
        form_data=retrieval.BatchProcessFilesForm(files=[first, second], collection_name='knowledge-1'),
        user=User(),
        db=None,
    )

    assert len(saved_docs) == 1
    assert result.results[0].file_id == 'file-1'
    assert result.results[0].status == 'completed'
    assert len(result.errors) == 1
    assert result.errors[0].file_id == 'file-2'
    assert result.errors[0].error == ERROR_MESSAGES.DUPLICATE_CONTENT


@pytest.mark.asyncio
async def test_add_files_to_knowledge_batch_skips_already_linked_files(monkeypatch):
    file = make_file('file-1', 'already linked')
    user = User()

    knowledge = SimpleNamespace(
        id='knowledge-1',
        user_id=user.id,
        model_dump=lambda: {
            'id': 'knowledge-1',
            'user_id': user.id,
            'name': 'Knowledge',
            'description': '',
            'meta': None,
            'access_grants': [],
            'created_at': 1,
            'updated_at': 1,
        },
    )

    async def get_knowledge_by_id(id, db=None):
        return knowledge

    async def get_files_by_ids(ids, db=None):
        return [file]

    async def get_file_ids_by_id(id, db=None):
        return {'file-1'}

    async def get_file_metadatas_by_id(id, db=None):
        return []

    async def process_files_batch(**kwargs):
        raise AssertionError('already-linked files should not be reprocessed')

    monkeypatch.setattr(knowledge_router.Knowledges, 'get_knowledge_by_id', get_knowledge_by_id)
    monkeypatch.setattr(knowledge_router.Knowledges, 'get_file_ids_by_id', get_file_ids_by_id)
    monkeypatch.setattr(knowledge_router.Knowledges, 'get_file_metadatas_by_id', get_file_metadatas_by_id)
    monkeypatch.setattr(knowledge_router.Files, 'get_files_by_ids', get_files_by_ids)
    monkeypatch.setattr(knowledge_router, 'process_files_batch', process_files_batch)

    response = await knowledge_router.add_files_to_knowledge_batch(
        request=SimpleNamespace(),
        id='knowledge-1',
        form_data=[knowledge_router.KnowledgeFileIdForm(file_id='file-1')],
        user=user,
        db=None,
    )

    assert response.warnings == {
        'message': 'Some files failed to process',
        'errors': [f'file-1: {ERROR_MESSAGES.FILE_EXISTS}'],
    }
