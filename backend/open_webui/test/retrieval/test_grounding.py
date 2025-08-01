"""
Tests for RAG grounding step functionality across different embedding providers.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from open_webui.retrieval.grounding import apply_grounding_step, format_documents_for_retrieval, GroundingResult


class TestGroundingStep:
    """Test grounding step functionality with various embedding providers."""

    def setup_method(self):
        """Set up test data."""
        self.sample_query = "What is artificial intelligence?"
        self.sample_query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # 5-dimensional for testing
        
        self.sample_documents = [
            {
                "document": "Artificial intelligence is a branch of computer science.",
                "metadata": {"source": "doc1.txt", "page": 1},
                "distance": 0.1,
            },
            {
                "document": "Machine learning is a subset of artificial intelligence.",
                "metadata": {"source": "doc2.txt", "page": 1},
                "distance": 0.2,
            },
            {
                "document": "The weather today is sunny and warm.",  # Irrelevant document
                "metadata": {"source": "doc3.txt", "page": 1},
                "distance": 0.8,
            },
        ]

    def create_mock_embedding_function(self, embeddings_map):
        """Create a mock embedding function that returns predefined embeddings."""
        def mock_embedding_function(texts, prefix=None, user=None):
            if isinstance(texts, str):
                texts = [texts]
            return [embeddings_map.get(text, [0.0] * 5) for text in texts]
        return mock_embedding_function

    def test_grounding_step_basic_functionality(self):
        """Test basic grounding step functionality."""
        # Create embeddings that should pass the threshold
        embeddings_map = {
            "Artificial intelligence is a branch of computer science.": [0.1, 0.2, 0.3, 0.4, 0.5],  # High similarity
            "Machine learning is a subset of artificial intelligence.": [0.1, 0.2, 0.3, 0.4, 0.4],  # High similarity
            "The weather today is sunny and warm.": [0.9, 0.1, 0.1, 0.1, 0.1],  # Low similarity
        }
        
        embedding_function = self.create_mock_embedding_function(embeddings_map)
        
        result = apply_grounding_step(
            query=self.sample_query,
            query_embedding=self.sample_query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=embedding_function,
            threshold=0.5,  # Set threshold to filter out weather document
        )
        
        assert isinstance(result, GroundingResult)
        assert len(result.validated_documents) == 2  # Should filter out weather document
        assert result.filtered_count == 1
        assert result.average_confidence > 0.5
        assert len(result.validation_scores) == 3  # All original documents scored

    def test_grounding_step_with_openai_style_embeddings(self):
        """Test grounding step with OpenAI-style embedding function."""
        def openai_embedding_function(texts, prefix=None, user=None):
            """Mock OpenAI embedding function."""
            if isinstance(texts, str):
                texts = [texts]
            
            # Simulate OpenAI embeddings (1536 dimensions, normalized)
            embeddings = []
            for text in texts:
                if "artificial intelligence" in text.lower():
                    # High similarity to query
                    embedding = [0.1] * 1536
                elif "weather" in text.lower():
                    # Low similarity to query
                    embedding = [-0.1] * 1536
                else:
                    # Medium similarity
                    embedding = [0.05] * 1536
                embeddings.append(embedding)
            return embeddings
        
        # Use higher dimensional query embedding
        query_embedding = [0.1] * 1536
        
        result = apply_grounding_step(
            query=self.sample_query,
            query_embedding=query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=openai_embedding_function,
            threshold=0.8,
        )
        
        assert len(result.validated_documents) >= 1
        assert all("artificial intelligence" in doc["document"].lower() 
                  for doc in result.validated_documents)

    def test_grounding_step_with_google_style_embeddings(self):
        """Test grounding step with Google Gecko-style embedding function."""
        def google_embedding_function(texts, prefix=None, user=None):
            """Mock Google embedding function."""
            if isinstance(texts, str):
                texts = [texts]
            
            # Simulate Google embeddings (768 dimensions)
            embeddings = []
            for text in texts:
                if "artificial intelligence" in text.lower() or "machine learning" in text.lower():
                    # High semantic similarity
                    embedding = [0.2] * 768
                elif "weather" in text.lower():
                    # Low semantic similarity
                    embedding = [-0.2] * 768
                else:
                    embedding = [0.0] * 768
                embeddings.append(embedding)
            return embeddings
        
        query_embedding = [0.2] * 768
        
        result = apply_grounding_step(
            query=self.sample_query,
            query_embedding=query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=google_embedding_function,
            threshold=0.7,
        )
        
        assert len(result.validated_documents) >= 1
        assert result.filtered_count >= 1  # Should filter out weather document

    def test_grounding_step_with_ollama_style_embeddings(self):
        """Test grounding step with Ollama-style embedding function."""
        def ollama_embedding_function(texts, prefix=None, user=None):
            """Mock Ollama embedding function."""
            if isinstance(texts, str):
                texts = [texts]
            
            # Simulate Ollama embeddings (smaller dimensions, different range)
            embeddings = []
            for text in texts:
                if "artificial intelligence" in text.lower():
                    embedding = [1.0, 0.8, 0.9, 0.7] * 64  # 256 dims
                elif "machine learning" in text.lower():
                    embedding = [0.9, 0.8, 1.0, 0.6] * 64
                else:
                    embedding = [0.1, 0.2, 0.1, 0.3] * 64
                embeddings.append(embedding[:256])  # Ensure consistent size
            return embeddings
        
        query_embedding = [1.0, 0.8, 0.9, 0.7] * 64
        
        result = apply_grounding_step(
            query=self.sample_query,
            query_embedding=query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=ollama_embedding_function,
            threshold=0.6,
        )
        
        assert isinstance(result, GroundingResult)
        assert len(result.validation_scores) == len(self.sample_documents)

    def test_grounding_step_empty_documents(self):
        """Test grounding step with empty document list."""
        embedding_function = self.create_mock_embedding_function({})
        
        result = apply_grounding_step(
            query=self.sample_query,
            query_embedding=self.sample_query_embedding,
            retrieved_documents=[],
            embedding_function=embedding_function,
            threshold=0.5,
        )
        
        assert len(result.validated_documents) == 0
        assert result.filtered_count == 0
        assert result.average_confidence == 0.0
        assert result.validation_scores == []

    def test_grounding_step_embedding_failure(self):
        """Test grounding step graceful handling of embedding failures."""
        def failing_embedding_function(texts, prefix=None, user=None):
            raise Exception("Embedding service unavailable")
        
        result = apply_grounding_step(
            query=self.sample_query,
            query_embedding=self.sample_query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=failing_embedding_function,
            threshold=0.5,
        )
        
        # Should fallback to original documents
        assert len(result.validated_documents) == len(self.sample_documents)
        assert result.filtered_count == 0
        assert result.average_confidence == 1.0
        assert all(score == 1.0 for score in result.validation_scores)

    def test_grounding_step_empty_embeddings(self):
        """Test grounding step when embedding function returns empty results."""
        def empty_embedding_function(texts, prefix=None, user=None):
            return []
        
        result = apply_grounding_step(
            query=self.sample_query,
            query_embedding=self.sample_query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=empty_embedding_function,
            threshold=0.5,
        )
        
        # Should fallback to original documents
        assert len(result.validated_documents) == len(self.sample_documents)
        assert result.filtered_count == 0
        assert result.average_confidence == 1.0

    def test_grounding_step_various_thresholds(self):
        """Test grounding step with different threshold values."""
        embeddings_map = {
            "Artificial intelligence is a branch of computer science.": [0.9, 0.1, 0.1, 0.1, 0.1],  # ~0.9 similarity
            "Machine learning is a subset of artificial intelligence.": [0.7, 0.3, 0.1, 0.1, 0.1],  # ~0.7 similarity
            "The weather today is sunny and warm.": [0.1, 0.1, 0.1, 0.1, 0.9],  # ~0.1 similarity
        }
        
        embedding_function = self.create_mock_embedding_function(embeddings_map)
        query_embedding = [1.0, 0.0, 0.0, 0.0, 0.0]
        
        # Test high threshold
        result_high = apply_grounding_step(
            query=self.sample_query,
            query_embedding=query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=embedding_function,
            threshold=0.8,
        )
        assert len(result_high.validated_documents) == 1  # Only highest similarity doc
        
        # Test medium threshold
        result_medium = apply_grounding_step(
            query=self.sample_query,
            query_embedding=query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=embedding_function,
            threshold=0.6,
        )
        assert len(result_medium.validated_documents) == 2  # Two highest similarity docs
        
        # Test low threshold
        result_low = apply_grounding_step(
            query=self.sample_query,
            query_embedding=query_embedding,
            retrieved_documents=self.sample_documents,
            embedding_function=embedding_function,
            threshold=0.05,
        )
        assert len(result_low.validated_documents) == 3  # All docs pass

    def test_format_documents_for_retrieval(self):
        """Test document formatting for retrieval."""
        documents = [
            {"document": "Test content 1", "metadata": {"source": "test1"}, "distance": 0.1},
            {"document": "Test content 2", "metadata": {"source": "test2"}, "distance": 0.2},
        ]
        
        result = format_documents_for_retrieval(documents)
        
        assert "ids" in result
        assert "distances" in result
        assert "metadatas" in result
        assert "documents" in result
        assert "embeddings" in result
        
        assert len(result["documents"][0]) == 2
        assert result["documents"][0][0] == "Test content 1"
        assert result["documents"][0][1] == "Test content 2"
        
        assert len(result["distances"][0]) == 2
        assert result["distances"][0][0] == 0.1
        assert result["distances"][0][1] == 0.2

    def test_format_documents_empty_list(self):
        """Test document formatting with empty list."""
        result = format_documents_for_retrieval([])
        
        assert result["ids"] == [[]]
        assert result["distances"] == [[]]
        assert result["metadatas"] == [[]]
        assert result["documents"] == [[]]
        assert result["embeddings"] is None

    def test_grounding_result_attributes(self):
        """Test GroundingResult class attributes."""
        validated_docs = [{"document": "test"}]
        filtered_count = 2
        avg_confidence = 0.75
        validation_scores = [0.8, 0.7, 0.2]
        
        result = GroundingResult(
            validated_documents=validated_docs,
            filtered_count=filtered_count,
            average_confidence=avg_confidence,
            validation_scores=validation_scores,
        )
        
        assert result.validated_documents == validated_docs
        assert result.filtered_count == filtered_count
        assert result.average_confidence == avg_confidence
        assert result.validation_scores == validation_scores

    def test_grounding_step_with_user_context(self):
        """Test grounding step with user context passed to embedding function."""
        def user_aware_embedding_function(texts, prefix=None, user=None):
            # Mock function that considers user context
            if user and user.get("id") == "test_user":
                # Return different embeddings based on user
                return [[0.8, 0.2, 0.1, 0.1, 0.1] for _ in texts]
            else:
                return [[0.1, 0.1, 0.1, 0.1, 0.1] for _ in texts]
        
        user_context = {"id": "test_user", "preferences": "technical"}
        
        result = apply_grounding_step(
            query=self.sample_query,
            query_embedding=[0.9, 0.1, 0.1, 0.1, 0.1],
            retrieved_documents=self.sample_documents,
            embedding_function=user_aware_embedding_function,
            threshold=0.5,
            user=user_context,
        )
        
        assert isinstance(result, GroundingResult)
        # Should pass all documents with user-aware embeddings
        assert len(result.validated_documents) == len(self.sample_documents)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])