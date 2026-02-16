from open_webui.retrieval.web.main import SearchResult
from open_webui.routers.retrieval import (
    Document,
    apply_doc_content_cap,
    apply_web_search_governance,
    build_web_search_fallback_response,
)


def test_apply_web_search_governance_dedup_and_cap():
    items = [
        SearchResult(link="https://example.com/a", title="A", snippet="s1"),
        SearchResult(link="https://example.com/a/", title="A2", snippet="s2"),
        SearchResult(link="https://example.com/b", title="B", snippet="s3"),
        SearchResult(link="https://example.com/c", title="C", snippet="s4"),
    ]

    governed = apply_web_search_governance(
        result_items=items,
        domain_filter_list=[],
        max_total_results=2,
        snippet_max_chars=100,
    )

    assert len(governed) == 2
    assert governed[0].link == "https://example.com/a"
    assert governed[1].link == "https://example.com/b"


def test_apply_web_search_governance_truncates_snippet():
    items = [
        SearchResult(
            link="https://example.com/x",
            title="X",
            snippet="x" * 50,
        )
    ]

    governed = apply_web_search_governance(
        result_items=items,
        domain_filter_list=[],
        max_total_results=5,
        snippet_max_chars=10,
    )

    assert governed[0].snippet == "x" * 10


def test_apply_doc_content_cap_truncates_docs():
    docs = [
        Document(page_content="a" * 25, metadata={"source": "https://example.com/a"}),
        Document(page_content="short", metadata={"source": "https://example.com/b"}),
    ]

    capped = apply_doc_content_cap(docs, max_doc_chars=10)

    assert len(capped) == 2
    assert capped[0].page_content == "a" * 10
    assert capped[1].page_content == "short"


def test_build_web_search_fallback_response_includes_metadata(monkeypatch):
    monkeypatch.setenv(
        "WEB_SEARCH_FALLBACK_MESSAGE",
        "Fallback for {queries} ({reason})",
    )

    response = build_web_search_fallback_response(
        queries=["kimi claw", ""],
        reason="no-search-results",
    )

    assert response["status"] is True
    assert response["items"] == []
    assert response["docs"] == []
    assert response["loaded_count"] == 0
    assert response["fallback"]["reason"] == "no-search-results"
    assert response["fallback"]["queries"] == ["kimi claw"]
    assert response["warning"] == "Fallback for kimi claw (no-search-results)"
