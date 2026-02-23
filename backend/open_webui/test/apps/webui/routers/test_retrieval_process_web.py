import types

import pytest
from langchain_core.documents import Document

from open_webui.routers import retrieval


@pytest.mark.asyncio
async def test_process_web_sets_add_true_when_overwrite_false(monkeypatch):
    captured = {}

    async def fake_run_in_threadpool(func, *args, **kwargs):
        if func is retrieval.get_content_from_url:
            return "content", [Document(page_content="hello", metadata={})]

        if func is retrieval.save_docs_to_vector_db:
            captured["kwargs"] = kwargs
            return True

        raise AssertionError(f"Unexpected function passed to run_in_threadpool: {func}")

    monkeypatch.setattr(retrieval, "run_in_threadpool", fake_run_in_threadpool)

    request = types.SimpleNamespace(
        app=types.SimpleNamespace(
            state=types.SimpleNamespace(
                config=types.SimpleNamespace(
                    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL=False
                )
            )
        )
    )
    form_data = retrieval.ProcessUrlForm(
        url="https://example.com", collection_name="test-collection"
    )
    user = types.SimpleNamespace(id="user-1")

    response = await retrieval.process_web(
        request=request,
        form_data=form_data,
        process=True,
        overwrite=False,
        user=user,
    )

    assert response["status"] is True
    assert captured["kwargs"]["overwrite"] is False
    assert captured["kwargs"]["add"] is True


@pytest.mark.asyncio
async def test_process_web_keeps_add_false_when_overwrite_true(monkeypatch):
    captured = {}

    async def fake_run_in_threadpool(func, *args, **kwargs):
        if func is retrieval.get_content_from_url:
            return "content", [Document(page_content="hello", metadata={})]

        if func is retrieval.save_docs_to_vector_db:
            captured["kwargs"] = kwargs
            return True

        raise AssertionError(f"Unexpected function passed to run_in_threadpool: {func}")

    monkeypatch.setattr(retrieval, "run_in_threadpool", fake_run_in_threadpool)

    request = types.SimpleNamespace(
        app=types.SimpleNamespace(
            state=types.SimpleNamespace(
                config=types.SimpleNamespace(
                    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL=False
                )
            )
        )
    )
    form_data = retrieval.ProcessUrlForm(
        url="https://example.com", collection_name="test-collection"
    )
    user = types.SimpleNamespace(id="user-1")

    response = await retrieval.process_web(
        request=request,
        form_data=form_data,
        process=True,
        overwrite=True,
        user=user,
    )

    assert response["status"] is True
    assert captured["kwargs"]["overwrite"] is True
    assert captured["kwargs"]["add"] is False
