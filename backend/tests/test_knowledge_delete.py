"""Storage/DB cleanup when files and folders are deleted from a knowledge base.

Verifies the shared teardown (`_purge_knowledge_file`): removing a file or a
folder drops its physical bytes and DB row — except when the file is still
linked to another knowledge base (reference guard).

Extraction/embedding is stubbed; local storage writes into the temp DATA_DIR,
so ``os.path.exists`` reflects real files on disk.
"""

import json
import os

import pytest

from open_webui.models.files import Files
from open_webui.models.knowledge import KnowledgeForm, Knowledges
from open_webui.services.process_file_queue import _process_queued_file, get_file_processing_queue


@pytest.fixture(autouse=True)
def _mock_process(monkeypatch):
    async def fake_process_file(request, form_data, user=None, db=None):
        await Files.update_file_data_by_id(form_data.file_id, {'status': 'completed'}, db=db)
        return {'status': True}

    monkeypatch.setattr('open_webui.services.files_service.process_file', fake_process_file)


async def _new_kb(user_id, name='KB'):
    return await Knowledges.insert_new_knowledge(user_id, KnowledgeForm(name=name, description=''))


async def _upload_into_kb(async_client, app, kb_id, name, content=b'body', relative_path=None):
    meta = {'knowledge_id': kb_id}
    if relative_path:
        meta['relative_path'] = relative_path
    resp = await async_client.post(
        '/api/v1/files/',
        files={'file': (name, content, 'text/plain')},
        data={'metadata': json.dumps(meta)},
    )
    assert resp.status_code == 200
    file_id = resp.json()['id']
    await _process_queued_file(app, get_file_processing_queue().get_nowait())
    return file_id


async def test_file_remove_deletes_db_row_and_storage(async_client, app, test_user):
    kb = await _new_kb(test_user.id)
    file_id = await _upload_into_kb(async_client, app, kb.id, 'report.pdf')

    file = await Files.get_file_by_id(file_id)
    assert os.path.exists(file.path)

    resp = await async_client.post(f'/api/v1/knowledge/{kb.id}/file/remove', json={'file_id': file_id})
    assert resp.status_code == 200

    assert await Files.get_file_by_id(file_id) is None
    assert not os.path.exists(file.path)


async def test_directory_delete_removes_files_and_storage(async_client, app, test_user):
    kb = await _new_kb(test_user.id)
    file_id = await _upload_into_kb(async_client, app, kb.id, 'a.txt', relative_path='docs/a.txt')

    file = await Files.get_file_by_id(file_id)
    assert os.path.exists(file.path)
    docs = next(d for d in await Knowledges.get_all_directories(kb.id) if d.name == 'docs')

    resp = await async_client.delete(
        f'/api/v1/knowledge/{kb.id}/dirs/{docs.id}/delete', params={'move_files': 'false'}
    )
    assert resp.status_code == 200

    # File fully torn down, folder gone.
    assert await Files.get_file_by_id(file_id) is None
    assert not os.path.exists(file.path)
    assert not any(d.name == 'docs' for d in await Knowledges.get_all_directories(kb.id))


async def test_shared_file_kept_when_linked_to_another_kb(async_client, app, test_user):
    kb1 = await _new_kb(test_user.id, 'KB1')
    kb2 = await _new_kb(test_user.id, 'KB2')

    file_id = await _upload_into_kb(async_client, app, kb1.id, 'shared.txt')
    file = await Files.get_file_by_id(file_id)
    # Link the same file into a second KB.
    await Knowledges.add_file_to_knowledge_by_id(kb2.id, file_id, test_user.id)

    # Remove from KB1 (delete_file defaults True) — reference guard must keep bytes.
    resp = await async_client.post(f'/api/v1/knowledge/{kb1.id}/file/remove', json={'file_id': file_id})
    assert resp.status_code == 200

    assert await Files.get_file_by_id(file_id) is not None
    assert os.path.exists(file.path)
    assert await Knowledges.has_file(kb2.id, file_id)
    assert not await Knowledges.has_file(kb1.id, file_id)


async def test_directory_delete_keeps_shared_file_bytes(async_client, app, test_user):
    kb1 = await _new_kb(test_user.id, 'KB1')
    kb2 = await _new_kb(test_user.id, 'KB2')

    file_id = await _upload_into_kb(async_client, app, kb1.id, 'a.txt', relative_path='docs/a.txt')
    file = await Files.get_file_by_id(file_id)
    await Knowledges.add_file_to_knowledge_by_id(kb2.id, file_id, test_user.id)

    docs = next(d for d in await Knowledges.get_all_directories(kb1.id) if d.name == 'docs')
    resp = await async_client.delete(
        f'/api/v1/knowledge/{kb1.id}/dirs/{docs.id}/delete', params={'move_files': 'false'}
    )
    assert resp.status_code == 200

    # Unlinked from KB1's folder, but bytes survive for KB2.
    assert await Files.get_file_by_id(file_id) is not None
    assert os.path.exists(file.path)
    assert await Knowledges.has_file(kb2.id, file_id)
