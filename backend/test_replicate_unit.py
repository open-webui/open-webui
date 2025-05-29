"""
Simple unit tests for Replicate image generation functionality.
Run with: python -m pytest test_replicate_unit.py -v
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the open_webui module to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'open_webui'))

from open_webui.routers.images import get_replicate_models


class TestReplicateModels:
    """Test Replicate model fetching functionality"""
    
    def test_get_replicate_models_no_token(self):
        """Test that cached models are returned when no API token is provided"""
        result = get_replicate_models("")
        
        assert len(result) == 14
        assert all("id" in model for model in result)
        assert all("name" in model for model in result)
        assert all("description" in model for model in result)
        
        # Check that default model is included
        model_ids = [model["id"] for model in result]
        assert "black-forest-labs/flux-1.1-pro-ultra" in model_ids
        assert "black-forest-labs/flux-1.1-pro" in model_ids

    def test_get_replicate_models_with_token_fallback(self):
        """Test that cached models are returned when API fails"""
        with patch('open_webui.routers.images.replicate') as mock_replicate:
            # Mock API failure
            mock_replicate.models.get.side_effect = Exception("API Error")
            
            result = get_replicate_models("test_token")
            
            # Should still return cached models
            assert len(result) == 14
            assert result[0]["id"] == "black-forest-labs/flux-1.1-pro-ultra"

    def test_get_replicate_models_cached_structure(self):
        """Test that cached models have the correct structure"""
        result = get_replicate_models("")
        
        for model in result:
            assert "id" in model
            assert "name" in model  
            assert "description" in model
            assert isinstance(model["id"], str)
            assert isinstance(model["name"], str)
            assert isinstance(model["description"], str)
            assert len(model["id"]) > 0
            assert len(model["name"]) > 0

    def test_replicate_models_include_popular_options(self):
        """Test that cached models include popular/expected models"""
        result = get_replicate_models("")
        model_ids = [model["id"] for model in result]
        
        # Check for key models that should be included
        expected_models = [
            "black-forest-labs/flux-1.1-pro-ultra",
            "black-forest-labs/flux-1.1-pro", 
            "black-forest-labs/flux-schnell",
            "stability-ai/stable-diffusion-3.5-large",
            "stability-ai/sdxl"
        ]
        
        for expected in expected_models:
            assert expected in model_ids, f"Expected model {expected} not found in cached models"

    def test_get_replicate_models_return_type(self):
        """Test that the function returns a list of dictionaries"""
        result = get_replicate_models("")
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        for model in result:
            assert isinstance(model, dict)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"]) 