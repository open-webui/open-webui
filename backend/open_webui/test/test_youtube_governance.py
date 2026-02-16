from open_webui.retrieval.loaders.youtube import (
    Document,
    get_cached_youtube_docs,
    set_cached_youtube_docs,
    truncate_youtube_docs,
)
from open_webui.retrieval.web.main import SearchResult
from open_webui.routers.retrieval import apply_youtube_result_cap


def test_truncate_youtube_docs_applies_hard_cap():
    docs = [Document(page_content="x" * 25, metadata={"source": "https://youtu.be/a"})]

    truncated = truncate_youtube_docs(docs, max_chars=10)

    assert len(truncated) == 1
    assert truncated[0].page_content == "x" * 10


def test_youtube_cache_roundtrip_returns_copy():
    source = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    original_docs = [
        Document(page_content="hello world", metadata={"source": source})
    ]

    set_cached_youtube_docs(source, original_docs)
    cached_docs = get_cached_youtube_docs(source, ttl_seconds=600)

    assert cached_docs is not None
    assert cached_docs[0].page_content == "hello world"

    # Ensure cache returns a copy (mutation should not leak)
    cached_docs[0].page_content = "mutated"
    cached_again = get_cached_youtube_docs(source, ttl_seconds=600)
    assert cached_again is not None
    assert cached_again[0].page_content == "hello world"


def test_apply_youtube_result_cap_limits_only_youtube_links():
    items = [
        SearchResult(link="https://www.youtube.com/watch?v=dQw4w9WgXcQ", title="Y1", snippet="s1"),
        SearchResult(link="https://example.com/article", title="W1", snippet="s2"),
        SearchResult(link="https://youtu.be/9bZkp7q19f0", title="Y2", snippet="s3"),
    ]

    capped = apply_youtube_result_cap(items, max_youtube_links=1)

    assert len(capped) == 2
    assert capped[0].link.startswith("https://www.youtube.com")
    assert capped[1].link == "https://example.com/article"
