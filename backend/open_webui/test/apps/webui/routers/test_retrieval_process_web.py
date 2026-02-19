from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from open_webui.routers import retrieval


def _build_request(bypass_embedding_and_retrieval: bool = False):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL=bypass_embedding_and_retrieval
                )
            )
        )
    )


@pytest.mark.asyncio
async def test_process_web_defaults_to_overwrite_true(monkeypatch):
    calls = []

    async def fake_run_in_threadpool(func, *args, **kwargs):
        calls.append((func, args, kwargs))
        if func is retrieval.get_content_from_url:
            return ("example content", [Document(page_content="doc", metadata={})])
        if func is retrieval.save_docs_to_vector_db:
            return True
        raise AssertionError(f"Unexpected threadpool function: {func}")

    monkeypatch.setattr(retrieval, "run_in_threadpool", fake_run_in_threadpool)

    response = await retrieval.process_web(
        request=_build_request(),
        form_data=retrieval.ProcessUrlForm(
            url="https://example.com", collection_name="test-collection"
        ),
        process=True,
        user=SimpleNamespace(id="test-user"),
    )

    assert response["status"] is True
    save_call = calls[1]
    assert save_call[0] is retrieval.save_docs_to_vector_db
    assert save_call[2]["overwrite"] is True


@pytest.mark.asyncio
async def test_process_web_respects_overwrite_false(monkeypatch):
    calls = []

    async def fake_run_in_threadpool(func, *args, **kwargs):
        calls.append((func, args, kwargs))
        if func is retrieval.get_content_from_url:
            return ("example content", [Document(page_content="doc", metadata={})])
        if func is retrieval.save_docs_to_vector_db:
            return True
        raise AssertionError(f"Unexpected threadpool function: {func}")

    monkeypatch.setattr(retrieval, "run_in_threadpool", fake_run_in_threadpool)

    response = await retrieval.process_web(
        request=_build_request(),
        form_data=retrieval.ProcessUrlForm(
            url="https://example.com",
            collection_name="test-collection",
            overwrite=False,
        ),
        process=True,
        user=SimpleNamespace(id="test-user"),
    )

    assert response["status"] is True
    save_call = calls[1]
    assert save_call[0] is retrieval.save_docs_to_vector_db
    assert save_call[2]["overwrite"] is False
