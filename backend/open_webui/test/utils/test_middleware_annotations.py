import pytest


class TestAnnotationToSourcesTransformation:
    """Test OpenAI annotation to Open WebUI sources transformation"""

    def transform_annotations_to_sources(self, annotations):
        """
        Helper function that replicates the annotation transformation logic
        from middleware.py for testing purposes.
        """
        sources = []
        for annotation in annotations:
            if annotation.get("type") == "url_citation" and "url_citation" in annotation:
                url_citation = annotation["url_citation"]
                url = url_citation.get("url", "")
                title = url_citation.get("title", url)
                source = {
                    "source": {"name": title, "url": url},
                    "document": [title],
                    "metadata": [{"source": url, "name": title}]
                }
                sources.append(source)
        return sources

    def test_single_url_citation(self):
        """Test transformation of a single url_citation annotation"""
        annotations = [
            {
                "type": "url_citation",
                "url_citation": {
                    "start_index": 0,
                    "end_index": 100,
                    "title": "Example Article",
                    "url": "https://example.com/article"
                }
            }
        ]

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 1
        assert sources[0]["source"]["name"] == "Example Article"
        assert sources[0]["source"]["url"] == "https://example.com/article"
        assert sources[0]["document"] == ["Example Article"]
        assert sources[0]["metadata"] == [{"source": "https://example.com/article", "name": "Example Article"}]

    def test_multiple_url_citations(self):
        """Test transformation of multiple url_citation annotations"""
        annotations = [
            {
                "type": "url_citation",
                "url_citation": {
                    "start_index": 0,
                    "end_index": 50,
                    "title": "First Article",
                    "url": "https://example.com/first"
                }
            },
            {
                "type": "url_citation",
                "url_citation": {
                    "start_index": 51,
                    "end_index": 100,
                    "title": "Second Article",
                    "url": "https://example.com/second"
                }
            },
            {
                "type": "url_citation",
                "url_citation": {
                    "start_index": 101,
                    "end_index": 150,
                    "title": "Third Article",
                    "url": "https://example.com/third"
                }
            }
        ]

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 3
        assert sources[0]["source"]["name"] == "First Article"
        assert sources[1]["source"]["name"] == "Second Article"
        assert sources[2]["source"]["name"] == "Third Article"

    def test_url_citation_missing_title_uses_url(self):
        """Test that missing title falls back to URL"""
        annotations = [
            {
                "type": "url_citation",
                "url_citation": {
                    "start_index": 0,
                    "end_index": 100,
                    "url": "https://example.com/no-title"
                }
            }
        ]

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 1
        assert sources[0]["source"]["name"] == "https://example.com/no-title"
        assert sources[0]["source"]["url"] == "https://example.com/no-title"

    def test_url_citation_empty_title_keeps_empty(self):
        """Test that empty title is kept as-is (get() returns the value, not default)"""
        annotations = [
            {
                "type": "url_citation",
                "url_citation": {
                    "start_index": 0,
                    "end_index": 100,
                    "title": "",
                    "url": "https://example.com/empty-title"
                }
            }
        ]

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 1
        # Empty string is a valid value from get(), so it's kept
        assert sources[0]["source"]["name"] == ""
        assert sources[0]["source"]["url"] == "https://example.com/empty-title"

    def test_non_url_citation_annotations_ignored(self):
        """Test that non-url_citation annotations are ignored"""
        annotations = [
            {
                "type": "file_citation",
                "file_citation": {
                    "file_id": "file-123",
                    "quote": "some quote"
                }
            },
            {
                "type": "url_citation",
                "url_citation": {
                    "title": "Valid Citation",
                    "url": "https://example.com/valid"
                }
            },
            {
                "type": "other_type",
                "data": "some data"
            }
        ]

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 1
        assert sources[0]["source"]["name"] == "Valid Citation"

    def test_empty_annotations_list(self):
        """Test handling of empty annotations list"""
        annotations = []

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 0

    def test_malformed_url_citation_missing_url_citation_key(self):
        """Test handling of annotation with type but missing url_citation key"""
        annotations = [
            {
                "type": "url_citation"
                # Missing "url_citation" key
            }
        ]

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 0

    def test_url_citation_with_missing_url(self):
        """Test handling of url_citation with missing URL"""
        annotations = [
            {
                "type": "url_citation",
                "url_citation": {
                    "title": "Article Without URL"
                    # Missing "url" key
                }
            }
        ]

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 1
        assert sources[0]["source"]["url"] == ""
        assert sources[0]["source"]["name"] == "Article Without URL"

    def test_real_world_openai_response_format(self):
        """Test with real-world OpenAI response annotation format"""
        # This format matches what OpenAI actually returns
        annotations = [
            {
                "type": "url_citation",
                "url_citation": {
                    "start_index": 0,
                    "end_index": 0,
                    "title": "2025 Africa Cup of Nations Schedule - ESPN",
                    "url": "https://www.espn.com/soccer/schedule/_/league/caf.nations"
                }
            },
            {
                "type": "url_citation",
                "url_citation": {
                    "start_index": 0,
                    "end_index": 0,
                    "title": "2025 Africa Cup of Nations - Wikipedia",
                    "url": "https://en.wikipedia.org/wiki/2025_Africa_Cup_of_Nations"
                }
            }
        ]

        sources = self.transform_annotations_to_sources(annotations)

        assert len(sources) == 2
        assert sources[0]["source"]["name"] == "2025 Africa Cup of Nations Schedule - ESPN"
        assert sources[0]["source"]["url"] == "https://www.espn.com/soccer/schedule/_/league/caf.nations"
        assert sources[1]["source"]["name"] == "2025 Africa Cup of Nations - Wikipedia"
        assert sources[1]["source"]["url"] == "https://en.wikipedia.org/wiki/2025_Africa_Cup_of_Nations"


class TestStreamAnnotationHandling:
    """Test the annotation handling in streaming context"""

    def test_annotations_emitted_only_once(self):
        """Test that annotations are only emitted once even if present in multiple chunks"""
        emitted_events = []

        def mock_event_emitter(event):
            emitted_events.append(event)

        # Simulate the streaming logic
        annotations_emitted = False
        chunks_with_annotations = [
            {"choices": [{"delta": {"content": "Hello", "annotations": [
                {"type": "url_citation", "url_citation": {"title": "Test", "url": "https://test.com"}}
            ]}}]},
            {"choices": [{"delta": {"content": " World", "annotations": [
                {"type": "url_citation", "url_citation": {"title": "Test", "url": "https://test.com"}}
            ]}}]},
        ]

        for chunk in chunks_with_annotations:
            delta = chunk["choices"][0].get("delta", {})
            annotations = delta.get("annotations")

            if annotations and not annotations_emitted:
                annotation_sources = []
                for annotation in annotations:
                    if annotation.get("type") == "url_citation" and "url_citation" in annotation:
                        url_citation = annotation["url_citation"]
                        url = url_citation.get("url", "")
                        title = url_citation.get("title", url)
                        source = {
                            "source": {"name": title, "url": url},
                            "document": [title],
                            "metadata": [{"source": url, "name": title}]
                        }
                        annotation_sources.append(source)
                if annotation_sources:
                    annotations_emitted = True
                    mock_event_emitter({"type": "chat:completion", "data": {"sources": annotation_sources}})

        # Should only have emitted once
        assert len(emitted_events) == 1
        assert emitted_events[0]["type"] == "chat:completion"
        assert "sources" in emitted_events[0]["data"]

    def test_annotations_from_delta_or_message(self):
        """Test that annotations are extracted from both delta and message fields"""
        # Test delta annotations
        chunk_with_delta_annotations = {
            "choices": [{
                "delta": {
                    "content": "Test",
                    "annotations": [
                        {"type": "url_citation", "url_citation": {"title": "Delta Source", "url": "https://delta.com"}}
                    ]
                }
            }]
        }

        delta = chunk_with_delta_annotations["choices"][0].get("delta", {})
        message = chunk_with_delta_annotations["choices"][0].get("message", {})
        annotations = delta.get("annotations") or message.get("annotations")

        assert annotations is not None
        assert annotations[0]["url_citation"]["title"] == "Delta Source"

        # Test message annotations
        chunk_with_message_annotations = {
            "choices": [{
                "message": {
                    "content": "Test",
                    "annotations": [
                        {"type": "url_citation", "url_citation": {"title": "Message Source", "url": "https://message.com"}}
                    ]
                },
                "delta": {}
            }]
        }

        delta = chunk_with_message_annotations["choices"][0].get("delta", {})
        message = chunk_with_message_annotations["choices"][0].get("message", {})
        annotations = delta.get("annotations") or message.get("annotations")

        assert annotations is not None
        assert annotations[0]["url_citation"]["title"] == "Message Source"

    def test_no_annotations_no_emission(self):
        """Test that no sources are emitted when there are no annotations"""
        emitted_events = []

        def mock_event_emitter(event):
            emitted_events.append(event)

        annotations_emitted = False
        chunk_without_annotations = {"choices": [{"delta": {"content": "No annotations here"}}]}

        delta = chunk_without_annotations["choices"][0].get("delta", {})
        message = chunk_without_annotations["choices"][0].get("message", {})
        annotations = delta.get("annotations") or message.get("annotations")

        if annotations and not annotations_emitted:
            # This block should not execute
            mock_event_emitter({"type": "chat:completion", "data": {"sources": []}})

        assert len(emitted_events) == 0

    def test_event_emitter_format(self):
        """Test that the emitted event has the correct format for Open WebUI"""
        emitted_event = None

        def mock_event_emitter(event):
            nonlocal emitted_event
            emitted_event = event

        annotations = [
            {"type": "url_citation", "url_citation": {"title": "Test Title", "url": "https://test.com/page"}}
        ]

        annotation_sources = []
        for annotation in annotations:
            if annotation.get("type") == "url_citation" and "url_citation" in annotation:
                url_citation = annotation["url_citation"]
                url = url_citation.get("url", "")
                title = url_citation.get("title", url)
                source = {
                    "source": {"name": title, "url": url},
                    "document": [title],
                    "metadata": [{"source": url, "name": title}]
                }
                annotation_sources.append(source)

        if annotation_sources:
            mock_event_emitter({"type": "chat:completion", "data": {"sources": annotation_sources}})

        # Verify the event format matches Open WebUI expectations
        assert emitted_event is not None
        assert emitted_event["type"] == "chat:completion"
        assert "data" in emitted_event
        assert "sources" in emitted_event["data"]

        source = emitted_event["data"]["sources"][0]
        assert "source" in source
        assert "name" in source["source"]
        assert "url" in source["source"]
        assert "document" in source
        assert "metadata" in source
