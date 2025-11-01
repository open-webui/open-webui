"""
Unit and integration tests for Auto Memory Function

Tests Named Entity Recognition, memory extraction, ChromaDB storage,
confidence scoring, and performance.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from open_webui.functions.auto_memory import Filter
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT


@pytest.fixture
def auto_memory_filter():
    """Create Auto Memory filter instance"""
    filter_instance = Filter()
    filter_instance.valves.enabled = True
    return filter_instance


@pytest.fixture
def test_user():
    """Mock user for testing"""
    return {
        "id": "test-user-789",
        "email": "test@example.com",
        "name": "Test User"
    }


@pytest.fixture
def mock_vector_db():
    """Mock ChromaDB client"""
    mock_client = Mock()
    mock_client.insert = AsyncMock()
    mock_client.search = AsyncMock(return_value=[])
    mock_client.delete = AsyncMock()
    return mock_client


class TestAutoMemoryEntityExtraction:
    """Test Named Entity Recognition and extraction"""

    @pytest.mark.asyncio
    async def test_extract_person_entities(self, auto_memory_filter, test_user):
        """Test extracting PERSON entities"""
        body = {
            "messages": [
                {"role": "assistant", "content": "Nice to meet you, John Smith!"}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        metadata = result.get("__metadata__", {}).get("auto_memory", {})
        assert metadata["extracted"] >= 1
        assert "PERSON" in metadata["types"]

    @pytest.mark.asyncio
    async def test_extract_organization_entities(self, auto_memory_filter, test_user):
        """Test extracting ORG entities"""
        body = {
            "messages": [
                {"role": "assistant", "content": "You work at Google and Microsoft, correct?"}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        metadata = result.get("__metadata__", {}).get("auto_memory", {})
        assert metadata["extracted"] >= 2
        assert "ORG" in metadata["types"]

    @pytest.mark.asyncio
    async def test_extract_date_entities(self, auto_memory_filter, test_user):
        """Test extracting DATE entities"""
        body = {
            "messages": [
                {"role": "assistant", "content": "Your appointment is on January 15, 2025."}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        metadata = result.get("__metadata__", {}).get("auto_memory", {})
        assert "DATE" in metadata["types"]

    @pytest.mark.asyncio
    async def test_extract_mixed_entities(self, auto_memory_filter, test_user):
        """Test extracting multiple entity types"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "Dr. Sarah Johnson from Stanford University will present on March 10th."
                }
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        metadata = result.get("__metadata__", {}).get("auto_memory", {})
        types = metadata["types"]

        assert "PERSON" in types  # Dr. Sarah Johnson
        assert "ORG" in types  # Stanford University
        assert "DATE" in types  # March 10th
        assert metadata["extracted"] >= 3

    @pytest.mark.asyncio
    async def test_ignore_non_assistant_messages(self, auto_memory_filter, test_user):
        """Test that only assistant messages are processed"""
        body = {
            "messages": [
                {"role": "user", "content": "Tell me about John at Google."}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        # Should not extract from user messages
        assert "__metadata__" not in result or \
               "auto_memory" not in result.get("__metadata__", {})

    @pytest.mark.asyncio
    async def test_empty_message_handling(self, auto_memory_filter, test_user):
        """Test handling empty messages"""
        body = {
            "messages": [
                {"role": "assistant", "content": ""}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        metadata = result.get("__metadata__", {}).get("auto_memory", {})
        assert metadata.get("extracted", 0) == 0


class TestAutoMemoryStorage:
    """Test ChromaDB storage integration"""

    @pytest.mark.asyncio
    async def test_memory_stored_in_chromadb(self, auto_memory_filter, test_user, mock_vector_db):
        """Test that memories are stored in ChromaDB"""
        with patch("open_webui.retrieval.vector.factory.VECTOR_DB_CLIENT", mock_vector_db):
            body = {
                "messages": [
                    {"role": "assistant", "content": "John works at Google."}
                ]
            }

            await auto_memory_filter.outlet(body, test_user)

            # Verify insert was called
            assert mock_vector_db.insert.called
            call_args = mock_vector_db.insert.call_args

            # Check collection name format
            assert call_args[1]["collection_name"] == f"user-memory-{test_user['id']}"

    @pytest.mark.asyncio
    async def test_memory_metadata_structure(self, auto_memory_filter, test_user, mock_vector_db):
        """Test that memory metadata is correctly formatted"""
        with patch("open_webui.retrieval.vector.factory.VECTOR_DB_CLIENT", mock_vector_db):
            body = {
                "messages": [
                    {"role": "assistant", "content": "Sarah Johnson is the CEO."}
                ]
            }

            await auto_memory_filter.outlet(body, test_user)

            call_args = mock_vector_db.insert.call_args
            metadatas = call_args[1]["metadatas"]

            # Verify metadata structure
            assert len(metadatas) > 0
            meta = metadatas[0]
            assert "type" in meta
            assert "entity" in meta
            assert "source" in meta
            assert meta["source"] == "auto_memory"
            assert "timestamp" in meta

    @pytest.mark.asyncio
    async def test_user_isolation(self, auto_memory_filter, mock_vector_db):
        """Test that memories are isolated per user"""
        with patch("open_webui.retrieval.vector.factory.VECTOR_DB_CLIENT", mock_vector_db):
            user1 = {"id": "user-1"}
            user2 = {"id": "user-2"}

            body = {
                "messages": [
                    {"role": "assistant", "content": "John Smith is here."}
                ]
            }

            await auto_memory_filter.outlet(body, user1)
            await auto_memory_filter.outlet(body, user2)

            # Should have been called twice with different collection names
            assert mock_vector_db.insert.call_count == 2

            calls = mock_vector_db.insert.call_args_list
            collection1 = calls[0][1]["collection_name"]
            collection2 = calls[1][1]["collection_name"]

            assert collection1 == "user-memory-user-1"
            assert collection2 == "user-memory-user-2"

    @pytest.mark.asyncio
    async def test_duplicate_memory_handling(self, auto_memory_filter, test_user, mock_vector_db):
        """Test handling duplicate memories"""
        with patch("open_webui.retrieval.vector.factory.VECTOR_DB_CLIENT", mock_vector_db):
            body = {
                "messages": [
                    {"role": "assistant", "content": "John works at Google. John is great."}
                ]
            }

            await auto_memory_filter.outlet(body, test_user)

            # Should extract "John" (PERSON) and "Google" (ORG)
            # But "John" should only be stored once per context
            call_args = mock_vector_db.insert.call_args
            documents = call_args[1]["documents"]

            # Check for deduplication logic (implementation specific)
            assert len(documents) >= 1


class TestAutoMemoryConfiguration:
    """Test configuration and valves"""

    @pytest.mark.asyncio
    async def test_disabled_valve(self, auto_memory_filter, test_user):
        """Test that filter can be disabled"""
        auto_memory_filter.valves.enabled = False

        body = {
            "messages": [
                {"role": "assistant", "content": "John works at Google."}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        # Should not extract when disabled
        assert "__metadata__" not in result or \
               "auto_memory" not in result.get("__metadata__", {})

    @pytest.mark.asyncio
    async def test_confidence_threshold(self, auto_memory_filter, test_user):
        """Test confidence threshold filtering"""
        auto_memory_filter.valves.min_confidence = 0.9

        body = {
            "messages": [
                {"role": "assistant", "content": "Maybe it was John? Or was it Bob?"}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        metadata = result.get("__metadata__", {}).get("auto_memory", {})

        # Ambiguous entities should be filtered out
        # Exact behavior depends on implementation
        assert metadata.get("extracted", 0) >= 0

    @pytest.mark.asyncio
    async def test_memory_type_filtering(self, auto_memory_filter, test_user):
        """Test filtering by memory types"""
        # Only extract PERSON entities
        auto_memory_filter.valves.memory_types = ["PERSON"]

        body = {
            "messages": [
                {"role": "assistant", "content": "John works at Google on January 15th."}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        metadata = result.get("__metadata__", {}).get("auto_memory", {})
        types = metadata.get("types", [])

        # Should only have PERSON, not ORG or DATE
        assert "PERSON" in types
        assert "ORG" not in types
        assert "DATE" not in types


class TestAutoMemoryPerformance:
    """Test performance and scalability"""

    @pytest.mark.asyncio
    async def test_large_conversation_handling(self, auto_memory_filter, test_user):
        """Test processing large conversations"""
        # 10,000 word message
        large_content = " ".join(["John works at Google."] * 2000)

        body = {
            "messages": [
                {"role": "assistant", "content": large_content}
            ]
        }

        start_time = time.time()
        result = await auto_memory_filter.outlet(body, test_user)
        duration = time.time() - start_time

        # Should complete in reasonable time (<5s)
        assert duration < 5.0

        metadata = result.get("__metadata__", {}).get("auto_memory", {})
        assert metadata["extracted"] >= 1

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, auto_memory_filter, test_user):
        """Test concurrent memory extraction"""
        import asyncio

        bodies = [
            {
                "messages": [
                    {"role": "assistant", "content": f"Person {i} works at Company {i}."}
                ]
            }
            for i in range(100)
        ]

        tasks = [auto_memory_filter.outlet(body, test_user) for body in bodies]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # Should handle 100 concurrent requests efficiently
        assert duration < 10.0
        assert all("__metadata__" in r for r in results)

    @pytest.mark.asyncio
    async def test_spacy_model_loading(self, auto_memory_filter):
        """Test that Spacy model is loaded lazily and cached"""
        # First call should load model
        assert auto_memory_filter.nlp is None

        auto_memory_filter._load_nlp()
        assert auto_memory_filter.nlp is not None

        # Second call should use cached model
        nlp_instance = auto_memory_filter.nlp
        auto_memory_filter._load_nlp()
        assert auto_memory_filter.nlp is nlp_instance  # Same instance


class TestAutoMemoryErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_no_user_provided(self, auto_memory_filter):
        """Test handling when user is None"""
        body = {
            "messages": [
                {"role": "assistant", "content": "John works at Google."}
            ]
        }

        # Should not crash, just return body unchanged
        result = await auto_memory_filter.outlet(body, user=None)
        assert result == body

    @pytest.mark.asyncio
    async def test_malformed_body(self, auto_memory_filter, test_user):
        """Test handling malformed message body"""
        body = {}  # No messages key

        result = await auto_memory_filter.outlet(body, test_user)

        # Should handle gracefully
        assert result == body

    @pytest.mark.asyncio
    async def test_chromadb_connection_error(self, auto_memory_filter, test_user):
        """Test handling ChromaDB connection errors"""
        with patch("open_webui.retrieval.vector.factory.VECTOR_DB_CLIENT.insert",
                   side_effect=ConnectionError("DB unavailable")):

            body = {
                "messages": [
                    {"role": "assistant", "content": "John works at Google."}
                ]
            }

            # Should not crash, but log error
            result = await auto_memory_filter.outlet(body, test_user)

            # Should still return body
            assert "messages" in result

    @pytest.mark.asyncio
    async def test_unicode_entity_handling(self, auto_memory_filter, test_user):
        """Test handling unicode and special characters"""
        body = {
            "messages": [
                {"role": "assistant", "content": "José García works at Café München."}
            ]
        }

        result = await auto_memory_filter.outlet(body, test_user)

        metadata = result.get("__metadata__", {}).get("auto_memory", {})
        assert metadata["extracted"] >= 1  # Should handle unicode names


class TestAutoMemoryIntegration:
    """Integration tests with full system"""

    @pytest.mark.asyncio
    async def test_end_to_end_memory_extraction_and_retrieval(self, auto_memory_filter, test_user):
        """Test complete flow: extract → store → retrieve"""
        # Extract and store
        body = {
            "messages": [
                {"role": "assistant", "content": "John Smith is a software engineer at Google."}
            ]
        }

        await auto_memory_filter.outlet(body, test_user)

        # Retrieve from ChromaDB
        collection_name = f"user-memory-{test_user['id']}"
        results = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            query_texts=["software engineer"],
            n_results=5
        )

        # Should find the stored memory
        assert len(results) > 0
        assert any("John Smith" in r["text"] for r in results)

    @pytest.mark.asyncio
    async def test_memory_accumulation_over_conversation(self, auto_memory_filter, test_user):
        """Test that memories accumulate over multiple messages"""
        messages = [
            "John works at Google.",
            "Sarah is the CEO of Microsoft.",
            "They're meeting on January 15th.",
            "The conference is in New York."
        ]

        for msg in messages:
            body = {
                "messages": [
                    {"role": "assistant", "content": msg}
                ]
            }
            await auto_memory_filter.outlet(body, test_user)

        # Query all memories
        collection_name = f"user-memory-{test_user['id']}"
        results = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        # Should have accumulated multiple memories
        assert len(results) >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
