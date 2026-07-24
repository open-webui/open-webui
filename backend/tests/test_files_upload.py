"""Integration tests for the file upload → sequential-processing flow.

Covers the contract established by the processing queue:
  * upload is accepted fast, persisted as ``pending``, and a job is enqueued
  * a bulk upload enqueues every file without processing any during the request
  * the worker drains a job and drives processing to ``completed``
  * pending files are discoverable for crash recovery

External boundaries (embedding/vector-DB via ``process_file``) are mocked;
storage uses the real local provider writing into a temp ``DATA_DIR``.
"""

import json

import pytest

from open_webui.models.files import Files
from open_webui.services.process_file_queue import (
    _process_queued_file,
    get_file_processing_queue,
)


def _drain(queue) -> None:
    while not queue.empty():
        queue.get_nowait()


@pytest.fixture(autouse=True)
def _clean_queue():
    _drain(get_file_processing_queue())
    yield
    _drain(get_file_processing_queue())


async def _upload(client, name='hello.txt', content=b'hello world', ctype='text/plain', metadata=None, **params):
    data = {'metadata': json.dumps(metadata)} if metadata is not None else None
    return await client.post(
        '/api/v1/files/',
        files={'file': (name, content, ctype)},
        data=data,
        params=params,
    )


async def test_upload_accepts_marks_pending_and_enqueues(async_client, test_user):
    queue = get_file_processing_queue()

    resp = await _upload(async_client)

    assert resp.status_code == 200
    body = resp.json()
    assert body['status'] is True
    file_id = body['id']
    assert body['data']['status'] == 'pending'

    # Exactly one job enqueued, carrying the reconstruction fields the worker needs.
    assert queue.qsize() == 1
    job = queue.get_nowait()
    assert job['file_id'] == file_id
    assert job['user_id'] == test_user.id
    assert job['content_type'] == 'text/plain'

    # Persisted as pending in the DB.
    file = await Files.get_file_by_id(file_id)
    assert file is not None
    assert file.data['status'] == 'pending'


async def test_bulk_upload_accepts_all_without_processing(async_client):
    """Upload-all / process-step-by-step: every file is accepted and queued,
    and none is processed during the request."""
    queue = get_file_processing_queue()
    n = 5

    ids = []
    for i in range(n):
        resp = await _upload(async_client, name=f'f{i}.txt', content=f'content {i}'.encode())
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'pending'
        ids.append(resp.json()['id'])

    assert queue.qsize() == n
    queued_ids = {queue.get_nowait()['file_id'] for _ in range(n)}
    assert queued_ids == set(ids)


async def test_worker_drains_and_processes(async_client, app, monkeypatch):
    calls = []

    async def fake_process_file(request, form_data, user=None, db=None):
        calls.append(form_data.file_id)
        await Files.update_file_data_by_id(form_data.file_id, {'status': 'completed'}, db=db)
        return {'status': True}

    monkeypatch.setattr('open_webui.services.files_service.process_file', fake_process_file)

    resp = await _upload(async_client, name='doc.txt', content=b'body')
    file_id = resp.json()['id']
    job = get_file_processing_queue().get_nowait()

    await _process_queued_file(app, job)

    assert calls == [file_id]
    file = await Files.get_file_by_id(file_id)
    assert file.data['status'] == 'completed'


async def test_worker_full_process_extracts_and_embeds(async_client, app):
    """End-to-end with nothing mocked: real extraction + local embedding into
    the in-process chroma vector DB.

    Exercises the loader, content persistence, hashing, and
    save_docs_to_vector_db against real backends (local sentence-transformers
    embeddings + chroma persisting under the temp DATA_DIR).
    """
    import asyncio

    # save_docs_to_vector_db schedules the embedding coroutine back onto the
    # main loop (set by the app lifespan, which ASGITransport doesn't run).
    app.state.main_loop = asyncio.get_running_loop()

    resp = await _upload(
        async_client,
        name='bio.txt',
        content=b'The mitochondria is the powerhouse of the cell.',
    )
    assert resp.status_code == 200
    file_id = resp.json()['id']

    job = get_file_processing_queue().get_nowait()
    await _process_queued_file(app, job)

    file = await Files.get_file_by_id(file_id)
    assert file.data['status'] == 'completed'
    # Real extraction ran.
    assert 'powerhouse' in (file.data.get('content') or '')
    # collection_name is recorded only after a successful embedding write,
    # so its presence proves the real vector-DB path completed.
    assert file.meta.get('collection_name') == f'file-{file_id}'


async def test_pending_files_are_recoverable(async_client):
    r1 = await _upload(async_client, name='a.txt')
    r2 = await _upload(async_client, name='b.txt')
    uploaded = {r1.json()['id'], r2.json()['id']}

    pending = await Files.get_pending_files()
    pending_ids = {f.id for f in pending}

    assert uploaded <= pending_ids
    assert all(f.data.get('status') == 'pending' for f in pending)


# ── Folder-structure preservation (relative_path → knowledge_directory tree) ──


@pytest.fixture
def _link_only_process(monkeypatch):
    """Stub extraction/embedding so the auto-link + directory-materialization
    path runs against the real DB without touching vector backends."""

    async def fake_process_file(request, form_data, user=None, db=None):
        await Files.update_file_data_by_id(form_data.file_id, {'status': 'completed'}, db=db)
        return {'status': True}

    monkeypatch.setattr('open_webui.services.files_service.process_file', fake_process_file)


async def _new_kb(user_id, name='KB'):
    from open_webui.models.knowledge import KnowledgeForm, Knowledges

    return await Knowledges.insert_new_knowledge(user_id, KnowledgeForm(name=name, description=''))


async def test_upload_stores_relative_path_but_keeps_flat_storage(async_client):
    resp = await _upload(
        async_client,
        name='report.pdf',
        content=b'body',
        metadata={'relative_path': 'Q3/finance/report.pdf'},
    )
    assert resp.status_code == 200
    file_id = resp.json()['id']

    file = await Files.get_file_by_id(file_id)
    # Virtual path preserved as metadata …
    assert file.meta['relative_path'] == 'Q3/finance/report.pdf'
    # … but the physical file is flat ({id}_report.pdf), no subdirectories on disk.
    assert file.filename == 'report.pdf'
    assert file.path.endswith(f'{file_id}_report.pdf')
    assert 'Q3' not in file.path and 'finance' not in file.path


async def test_relative_path_derived_from_webkit_style_filename(async_client):
    # No explicit metadata: the folder path rides in the filename (webkitRelativePath).
    resp = await _upload(async_client, name='docs/sub/a.txt', content=b'x')
    file = await Files.get_file_by_id(resp.json()['id'])
    assert file.meta['relative_path'] == 'docs/sub/a.txt'
    assert file.filename == 'a.txt'


async def test_relative_path_rejects_traversal(async_client):
    resp = await _upload(
        async_client,
        name='passwd',
        content=b'x',
        metadata={'relative_path': '../../etc/passwd'},
    )
    file = await Files.get_file_by_id(resp.json()['id'])
    # '..' segments are stripped down to a safe basename; nothing escapes upward.
    assert file.meta['relative_path'] == 'passwd'
    assert '..' not in file.path


async def test_plain_upload_has_no_relative_path(async_client):
    resp = await _upload(async_client, name='hello.txt')
    file = await Files.get_file_by_id(resp.json()['id'])
    assert file.meta.get('relative_path') is None


async def test_folder_upload_recreates_knowledge_directory_tree(async_client, app, test_user, _link_only_process):
    from open_webui.models.knowledge import Knowledges

    kb = await _new_kb(test_user.id)

    resp = await _upload(
        async_client,
        name='report.pdf',
        content=b'body',
        metadata={'knowledge_id': kb.id, 'relative_path': 'Q3/finance/report.pdf'},
    )
    assert resp.status_code == 200
    file_id = resp.json()['id']

    await _process_queued_file(app, get_file_processing_queue().get_nowait())

    # The Q3 > finance tree was created with correct parent_id foreign keys.
    dirs = {d.name: d for d in await Knowledges.get_all_directories(kb.id)}
    assert set(dirs) == {'Q3', 'finance'}
    assert dirs['Q3'].parent_id is None
    assert dirs['finance'].parent_id == dirs['Q3'].id

    # The file is linked to the leaf directory via the knowledge_file.directory_id FK.
    linked = {f.id: dir_id for f, dir_id in await Knowledges.get_files_with_directory_ids(kb.id)}
    assert linked[file_id] == dirs['finance'].id


async def test_folder_upload_is_idempotent_across_files(async_client, app, test_user, _link_only_process):
    from open_webui.models.knowledge import Knowledges

    kb = await _new_kb(test_user.id)

    for name in ('a.txt', 'b.txt'):
        resp = await _upload(
            async_client,
            name=name,
            content=name.encode(),
            metadata={'knowledge_id': kb.id, 'relative_path': f'shared/{name}'},
        )
        assert resp.status_code == 200
        await _process_queued_file(app, get_file_processing_queue().get_nowait())

    # Both files share one 'shared' directory — no duplicate levels created.
    dirs = [d for d in await Knowledges.get_all_directories(kb.id) if d.name == 'shared']
    assert len(dirs) == 1
    linked = {f.filename: dir_id for f, dir_id in await Knowledges.get_files_with_directory_ids(kb.id)}
    assert linked['a.txt'] == linked['b.txt'] == dirs[0].id
