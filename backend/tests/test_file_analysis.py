"""Integration tests for AI ingestion analysis (analyze_file / describe_folder)
and its gate inside the file-processing flow.

The task-model LLM call (``generate_chat_completion``) is mocked so verdicts are
deterministic; extraction and (for the eligible case) embedding run for real.
"""

import pytest

from open_webui.models.files import Files
from open_webui.services.file_analysis import analyze_file, describe_folder
from open_webui.services.process_file_queue import (
    _process_queued_file,
    get_file_processing_queue,
)
from open_webui.utils.automations import _build_request


def _drain(queue) -> None:
    while not queue.empty():
        queue.get_nowait()


@pytest.fixture(autouse=True)
def _clean_queue():
    _drain(get_file_processing_queue())
    yield
    _drain(get_file_processing_queue())


@pytest.fixture
def models_available(app):
    """Make _resolve_task_model_id return a model (lifespan didn't load any)."""
    original = app.state.MODELS
    app.state.MODELS = {'test-model': {'connection_type': 'local', 'id': 'test-model'}}
    yield
    app.state.MODELS = original


@pytest.fixture
def analysis_enabled(app, models_available):
    app.state.config.ENABLE_INGESTION_ANALYSIS = True
    yield
    app.state.config.ENABLE_INGESTION_ANALYSIS = False


def _fake_completion(content: str):
    async def _f(request, form_data=None, user=None, **kwargs):
        return {'choices': [{'message': {'content': content}}]}

    return _f


def _raising_completion():
    async def _f(request, form_data=None, user=None, **kwargs):
        raise RuntimeError('boom')

    return _f


async def _upload_unprocessed(client, name='doc.txt', content=b'text'):
    """Create a file row without kicking off processing (process=false)."""
    resp = await client.post(
        '/api/v1/files/',
        files={'file': (name, content, 'text/plain')},
        params={'process': 'false'},
    )
    assert resp.status_code == 200
    return resp.json()['id']


# ── analyze_file (unit-ish, direct calls) ──────────────────────────────────


async def test_analyze_file_eligible_persists_description(async_client, app, test_user, models_available, monkeypatch):
    monkeypatch.setattr(
        'open_webui.services.file_analysis.generate_chat_completion',
        _fake_completion('{"eligible": true, "description": "A note about cell biology."}'),
    )
    file_id = await _upload_unprocessed(async_client, name='bio.txt')

    eligible, description = await analyze_file(
        _build_request(app), file_id, test_user, content='The cell is the basic unit of life.'
    )

    assert eligible is True
    assert description == 'A note about cell biology.'
    file = await Files.get_file_by_id(file_id)
    assert file.data.get('description') == 'A note about cell biology.'


async def test_analyze_file_ineligible(async_client, app, test_user, models_available, monkeypatch):
    monkeypatch.setattr(
        'open_webui.services.file_analysis.generate_chat_completion',
        _fake_completion('{"eligible": false, "description": "Empty boilerplate."}'),
    )
    file_id = await _upload_unprocessed(async_client)

    eligible, description = await analyze_file(_build_request(app), file_id, test_user, content='...')

    assert eligible is False
    assert description == 'Empty boilerplate.'


async def test_analyze_file_fails_open_on_llm_error(async_client, app, test_user, models_available, monkeypatch):
    monkeypatch.setattr(
        'open_webui.services.file_analysis.generate_chat_completion',
        _raising_completion(),
    )
    file_id = await _upload_unprocessed(async_client)

    eligible, description = await analyze_file(_build_request(app), file_id, test_user, content='some text')

    # Fail-open: an LLM outage must not silently drop the upload.
    assert eligible is True
    assert description == ''


async def test_analyze_file_empty_content_short_circuits(async_client, app, test_user):
    """No extracted content → not eligible, and no LLM call (no model needed)."""
    file_id = await _upload_unprocessed(async_client)

    eligible, description = await analyze_file(_build_request(app), file_id, test_user, content='   ')

    assert eligible is False
    assert description == ''


# ── gate inside process_file (end-to-end via the worker) ───────────────────


async def test_process_file_skips_non_embeddable_type(async_client, app, test_user, analysis_enabled, monkeypatch):
    """Embedding eligibility is an extension allowlist: a code file is not embedded,
    but its AI context/description is still generated and kept."""
    monkeypatch.setattr(
        'open_webui.services.file_analysis.generate_chat_completion',
        _fake_completion('{"eligible": true, "description": "Python script."}'),
    )
    resp = await async_client.post(
        '/api/v1/files/',
        files={'file': ('script.py', b'print("hello world")', 'text/x-python')},
    )
    file_id = resp.json()['id']
    job = get_file_processing_queue().get_nowait()

    await _process_queued_file(app, job)

    file = await Files.get_file_by_id(file_id)
    assert file.data['status'] == 'skipped'
    assert file.data.get('skipped_reason') == 'not_embeddable_type'
    # Context is kept even though it wasn't embedded.
    assert file.data.get('description') == 'Python script.'
    # Never embedded — no collection recorded.
    assert (file.meta or {}).get('collection_name') is None


async def test_process_file_embeds_eligible(async_client, app, test_user, analysis_enabled, monkeypatch):
    import asyncio

    app.state.main_loop = asyncio.get_running_loop()
    monkeypatch.setattr(
        'open_webui.services.file_analysis.generate_chat_completion',
        _fake_completion('{"eligible": true, "description": "About mitochondria."}'),
    )
    resp = await async_client.post(
        '/api/v1/files/',
        files={'file': ('bio.txt', b'The mitochondria is the powerhouse of the cell.', 'text/plain')},
    )
    file_id = resp.json()['id']
    job = get_file_processing_queue().get_nowait()

    await _process_queued_file(app, job)

    file = await Files.get_file_by_id(file_id)
    assert file.data['status'] == 'completed'
    assert file.data.get('description') == 'About mitochondria.'
    assert file.meta.get('collection_name') == f'file-{file_id}'


# ── describe_folder ────────────────────────────────────────────────────────


async def test_describe_folder_aggregates_descriptions(async_client, app, test_user, models_available, monkeypatch):
    ids = []
    for i, desc in enumerate(['Invoices for Q1.', 'Invoices for Q2.']):
        fid = await _upload_unprocessed(async_client, name=f'inv{i}.txt')
        await Files.update_file_data_by_id(fid, {'description': desc})
        ids.append(fid)

    monkeypatch.setattr(
        'open_webui.services.file_analysis.generate_chat_completion',
        _fake_completion('This folder contains quarterly invoices.'),
    )

    summary = await describe_folder(_build_request(app), ids, test_user)

    assert summary == 'This folder contains quarterly invoices.'


async def test_describe_folder_empty_when_no_descriptions(async_client, app, test_user, models_available):
    fid = await _upload_unprocessed(async_client)  # no description set
    summary = await describe_folder(_build_request(app), [fid], test_user)
    assert summary == ''
