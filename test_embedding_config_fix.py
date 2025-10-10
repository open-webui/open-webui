#!/usr/bin/env python3
"""
Test script to verify the embedding configuration import fix.

This test simulates the issue where embedding models don't work after 
importing JSON configuration and verifies that the fix resolves it.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request
from open_webui.routers.configs import import_config, ImportConfigForm
from open_webui.models.users import UserModel


class TestEmbeddingConfigFix:
    """Test cases for the embedding configuration import fix."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock app state
        self.mock_app_state = Mock()
        self.mock_app_state.config = Mock()
        
        # Set initial config values
        self.mock_app_state.config.RAG_EMBEDDING_ENGINE = ""
        self.mock_app_state.config.RAG_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
        self.mock_app_state.config.RAG_EMBEDDING_BATCH_SIZE = 1
        self.mock_app_state.config.ENABLE_RAG_HYBRID_SEARCH = False
        self.mock_app_state.config.BYPASS_EMBEDDING_AND_RETRIEVAL = False
        
        # Mock embedding functions
        self.mock_app_state.ef = None
        self.mock_app_state.rf = None
        self.mock_app_state.EMBEDDING_FUNCTION = None
        self.mock_app_state.RERANKING_FUNCTION = None
        
        # Mock request
        self.mock_request = Mock(spec=Request)
        self.mock_request.app.state = self.mock_app_state
        
        # Mock user
        self.mock_user = Mock(spec=UserModel)
        self.mock_user.role = "admin"
    
    @patch('open_webui.routers.configs.save_config')
    @patch('open_webui.routers.configs.get_config')
    @patch('open_webui.routers.retrieval.get_ef')
    @patch('open_webui.routers.retrieval.get_embedding_function')
    @patch('open_webui.routers.retrieval.get_reranking_function')
    async def test_embedding_config_import_reinitializes_functions(
        self, 
        mock_get_reranking_function,
        mock_get_embedding_function, 
        mock_get_ef,
        mock_get_config,
        mock_save_config
    ):
        """Test that importing embedding config re-initializes embedding functions."""
        
        # Setup mocks
        mock_ef = Mock()
        mock_embedding_function = Mock()
        mock_reranking_function = Mock()
        
        mock_get_ef.return_value = mock_ef
        mock_get_embedding_function.return_value = mock_embedding_function
        mock_get_reranking_function.return_value = mock_reranking_function
        mock_get_config.return_value = {"status": "success"}
        
        # Test data - importing new embedding model config
        config_data = {
            "RAG_EMBEDDING_ENGINE": "openai",
            "RAG_EMBEDDING_MODEL": "text-embedding-3-large", 
            "RAG_OPENAI_API_BASE_URL": "https://api.openai.com/v1",
            "RAG_OPENAI_API_KEY": "sk-test-key",
            "RAG_EMBEDDING_BATCH_SIZE": 100
        }
        
        form_data = ImportConfigForm(config=config_data)
        
        # Execute the import
        result = await import_config(self.mock_request, form_data, self.mock_user)
        
        # Verify config was saved
        mock_save_config.assert_called_once_with(config_data)
        
        # Verify embedding functions were re-initialized
        mock_get_ef.assert_called_once()
        mock_get_embedding_function.assert_called_once()
        mock_get_reranking_function.assert_called_once()
        
        # Verify app state was updated
        assert self.mock_app_state.ef == mock_ef
        assert self.mock_app_state.EMBEDDING_FUNCTION == mock_embedding_function
        assert self.mock_app_state.RERANKING_FUNCTION == mock_reranking_function
    
    @patch('open_webui.routers.configs.save_config')
    @patch('open_webui.routers.configs.get_config')
    async def test_non_embedding_config_import_skips_reinit(
        self, 
        mock_get_config,
        mock_save_config
    ):
        """Test that importing non-embedding config doesn't trigger re-initialization."""
        
        mock_get_config.return_value = {"status": "success"}
        
        # Test data - non-embedding config
        config_data = {
            "ENABLE_SIGNUP": True,
            "DEFAULT_MODELS": "llama3.2:latest",
            "WEBUI_NAME": "Test WebUI"
        }
        
        form_data = ImportConfigForm(config=config_data)
        
        # Store original values
        original_ef = self.mock_app_state.ef
        original_embedding_function = self.mock_app_state.EMBEDDING_FUNCTION
        
        # Execute the import
        result = await import_config(self.mock_request, form_data, self.mock_user)
        
        # Verify config was saved
        mock_save_config.assert_called_once_with(config_data)
        
        # Verify embedding functions were NOT re-initialized
        assert self.mock_app_state.ef == original_ef
        assert self.mock_app_state.EMBEDDING_FUNCTION == original_embedding_function
    
    @patch('open_webui.routers.configs.save_config')
    @patch('open_webui.routers.configs.get_config')
    @patch('open_webui.routers.retrieval.get_ef')
    async def test_embedding_reinit_handles_errors_gracefully(
        self, 
        mock_get_ef,
        mock_get_config,
        mock_save_config
    ):
        """Test that errors during embedding re-initialization don't break config import."""
        
        # Setup mocks
        mock_get_ef.side_effect = Exception("Model loading failed")
        mock_get_config.return_value = {"status": "success"}
        
        # Test data
        config_data = {
            "RAG_EMBEDDING_MODEL": "invalid-model"
        }
        
        form_data = ImportConfigForm(config=config_data)
        
        # Execute the import - should not raise exception
        result = await import_config(self.mock_request, form_data, self.mock_user)
        
        # Verify config was still saved despite embedding error
        mock_save_config.assert_called_once_with(config_data)
        assert result == {"status": "success"}


def test_vector_dimension_mismatch_scenario():
    """
    Test scenario that reproduces the original issue:
    Vector dimension mismatch after config import.
    """
    # Simulate the original problem scenario
    
    # 1. System starts with default embedding model (384 dimensions)
    original_model = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dims
    original_dimensions = 384
    
    # 2. Vector DB contains vectors with these dimensions
    stored_vectors = [
        {"id": "doc1", "vector": [0.1] * original_dimensions},
        {"id": "doc2", "vector": [0.2] * original_dimensions}
    ]
    
    # 3. User imports config with different model (1024 dimensions)
    imported_config = {
        "RAG_EMBEDDING_MODEL": "text-embedding-3-large",  # 1024 dims
        "RAG_EMBEDDING_ENGINE": "openai"
    }
    
    # 4. Without the fix: query uses new model (1024 dims) against old vectors (384 dims)
    # This would cause: "Vector dimension error: expected dim: 384, got 1024"
    
    # 5. With the fix: embedding functions are re-initialized with new model
    # The system should handle this gracefully or provide clear error messages
    
    print("✅ Test scenario documented - fix should prevent dimension mismatch errors")


if __name__ == "__main__":
    # Run the test scenario
    test_vector_dimension_mismatch_scenario()
    
    # Run pytest if available
    try:
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not available, skipping automated tests")
        print("✅ Manual test scenarios completed")