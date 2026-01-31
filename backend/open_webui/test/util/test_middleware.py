import json
import pytest
from open_webui.utils.middleware import get_citation_source_from_tool_result


class TestGetCitationSourceFromToolResult:
    """Tests for get_citation_source_from_tool_result function."""

    # Error handling tests

    def test_search_web_error_returns_empty_list(self):
        """When search_web returns an error dict, should return empty sources."""
        error_result = json.dumps({"error": "Request timed out"})
        sources = get_citation_source_from_tool_result("search_web", {}, error_result)
        assert sources == []

    def test_query_knowledge_files_error_returns_empty_list(self):
        """When query_knowledge_files returns an error dict, should return empty sources."""
        error_result = json.dumps({"error": "Embedding function not configured"})
        sources = get_citation_source_from_tool_result("query_knowledge_files", {}, error_result)
        assert sources == []

    def test_view_knowledge_file_error_returns_empty_list(self):
        """When view_knowledge_file returns an error dict, should return empty sources."""
        error_result = json.dumps({"error": "File not found"})
        sources = get_citation_source_from_tool_result("view_knowledge_file", {}, error_result)
        assert sources == []

    def test_generic_tool_error_returns_empty_list(self):
        """Any tool returning an error dict should return empty sources."""
        error_result = json.dumps({"error": "Some error"})
        sources = get_citation_source_from_tool_result("unknown_tool", {}, error_result)
        assert sources == []

    # Success case tests

    def test_search_web_success_returns_sources(self):
        """When search_web succeeds, should return formatted sources."""
        success_result = json.dumps([
            {"title": "Test Title", "link": "https://example.com", "snippet": "Test snippet"}
        ])
        sources = get_citation_source_from_tool_result("search_web", {}, success_result)

        assert len(sources) == 1
        assert sources[0]["source"]["name"] == "search_web"
        assert sources[0]["document"] == ["Test Title\nTest snippet"]
        assert sources[0]["metadata"][0]["url"] == "https://example.com"

    def test_search_web_multiple_results(self):
        """When search_web returns multiple results, all should be included."""
        success_result = json.dumps([
            {"title": "Result 1", "link": "https://example1.com", "snippet": "Snippet 1"},
            {"title": "Result 2", "link": "https://example2.com", "snippet": "Snippet 2"},
        ])
        sources = get_citation_source_from_tool_result("search_web", {}, success_result)

        assert len(sources) == 1
        assert len(sources[0]["document"]) == 2
        assert len(sources[0]["metadata"]) == 2

    def test_search_web_empty_results(self):
        """When search_web returns empty list, should return source with empty documents."""
        success_result = json.dumps([])
        sources = get_citation_source_from_tool_result("search_web", {}, success_result)

        assert len(sources) == 1
        assert sources[0]["document"] == []
        assert sources[0]["metadata"] == []

    def test_view_knowledge_file_success(self):
        """When view_knowledge_file succeeds, should return file source."""
        success_result = json.dumps({
            "id": "file-123",
            "filename": "test.pdf",
            "content": "File content here",
            "knowledge_name": "My Knowledge Base"
        })
        sources = get_citation_source_from_tool_result("view_knowledge_file", {}, success_result)

        assert len(sources) == 1
        assert sources[0]["source"]["id"] == "file-123"
        assert sources[0]["source"]["name"] == "test.pdf"
        assert sources[0]["document"] == ["File content here"]

    def test_query_knowledge_files_success(self):
        """When query_knowledge_files succeeds, should return chunk sources."""
        success_result = json.dumps([
            {"source": "doc1.pdf", "file_id": "f1", "content": "Chunk 1"},
            {"source": "doc1.pdf", "file_id": "f1", "content": "Chunk 2"},
            {"source": "doc2.pdf", "file_id": "f2", "content": "Chunk 3"},
        ])
        sources = get_citation_source_from_tool_result("query_knowledge_files", {}, success_result)

        # Should be grouped by file
        assert len(sources) == 2

    def test_query_knowledge_files_empty_results(self):
        """When query_knowledge_files returns empty list, should return empty sources."""
        success_result = json.dumps([])
        sources = get_citation_source_from_tool_result("query_knowledge_files", {}, success_result)

        assert sources == []
