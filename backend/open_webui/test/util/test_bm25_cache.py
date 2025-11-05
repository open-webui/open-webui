"""Tests for the BM25 retriever cache helpers."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, MutableMapping, Optional

import pytest
from langchain_community.retrievers import BM25Retriever

from open_webui.retrieval import bm25_cache


@pytest.mark.parametrize("bm25_params", [None, {"k1": 1.5, "b": 0.75}])
def test_get_or_build_bm25_retriever_persists_and_reuses_cache(
    tmp_path, monkeypatch, bm25_params
) -> None:
    """Ensure BM25 retrievers are cached in-memory and on disk."""

    # Use an isolated persistent cache directory and cache instance for the test.
    monkeypatch.setattr(bm25_cache, "_PERSISTENT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        bm25_cache, "_cache", bm25_cache._BM25LRUCache(max_items=8)  # type: ignore[attr-defined]
    )

    texts = [
        "Alpha document about testing BM25 caching.",
        "Beta document discussing retrieval strategies.",
    ]
    metadatas = [{"id": 1}, {"id": 2}]

    call_count = 0

    def builder(
        texts: Iterable[str],
        metadatas: Iterable[Mapping[str, Any]],
        bm25_params: Optional[MutableMapping[str, Any]] = None,
    ) -> BM25Retriever:
        nonlocal call_count
        call_count += 1
        return BM25Retriever.from_texts(
            list(texts),
            list(metadatas),
            bm25_params=bm25_params,
        )

    # First call should build the retriever via the builder and persist it.
    retriever1 = bm25_cache.get_or_build_bm25_retriever(
        collection_name="test-collection",
        texts=texts,
        metadatas=metadatas,
        bm25_params=bm25_params,
        builder=builder,
    )
    assert call_count == 1

    cache_files = list(tmp_path.glob("*.pkl"))
    assert len(cache_files) == 1

    # Second call should reuse the in-memory cache without calling the builder.
    retriever2 = bm25_cache.get_or_build_bm25_retriever(
        collection_name="test-collection",
        texts=list(texts),
        metadatas=list(metadatas),
        bm25_params=bm25_params,
        builder=builder,
    )
    assert retriever2 is retriever1
    assert call_count == 1

    # Clear the in-memory cache to force a disk load on the next call.
    bm25_cache._cache.clear()  # type: ignore[attr-defined]

    retriever3 = bm25_cache.get_or_build_bm25_retriever(
        collection_name="test-collection",
        texts=texts,
        metadatas=metadatas,
        bm25_params=bm25_params,
        builder=builder,
    )

    # Loading from disk should still avoid invoking the builder.
    assert call_count == 1
    assert retriever3 is not None
    assert retriever3 is not retriever1

    retriever3.k = 1
    docs = retriever3.invoke("testing bm25")
    assert docs
    assert docs[0].page_content in texts
