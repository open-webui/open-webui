import pytest
import asyncio
from unittest.mock import MagicMock, patch


class TestGetEmbeddingFunction:
    """Tests for get_embedding_function in retrieval/utils.py"""

    @pytest.mark.asyncio
    async def test_sentence_transformers_batch_size_is_passed(self):
        """Test that batch_size is correctly passed to sentence-transformers encode method.

        This test verifies the fix for issue #20053:
        https://github.com/open-webui/open-webui/issues/20053
        """
        from open_webui.retrieval.utils import get_embedding_function

        # Create a mock embedding function that tracks call arguments
        mock_embedding_func = MagicMock()
        mock_embedding_func.encode = MagicMock(return_value=MagicMock(tolist=lambda: [[0.1, 0.2, 0.3]]))

        embedding_batch_size = 8

        # Get the async embedding function with sentence-transformers (embedding_engine="")
        async_embedding_func = get_embedding_function(
            embedding_engine="",
            embedding_model="test-model",
            embedding_function=mock_embedding_func,
            url="",
            key="",
            embedding_batch_size=embedding_batch_size,
        )

        # Call the function
        test_query = ["test query 1", "test query 2"]
        await async_embedding_func(test_query)

        # Verify batch_size was passed to encode
        mock_embedding_func.encode.assert_called_once()
        call_kwargs = mock_embedding_func.encode.call_args
        assert call_kwargs[1].get("batch_size") == embedding_batch_size

    @pytest.mark.asyncio
    async def test_sentence_transformers_batch_size_with_prefix(self):
        """Test that batch_size and prefix are correctly passed together."""
        from open_webui.retrieval.utils import get_embedding_function

        mock_embedding_func = MagicMock()
        mock_embedding_func.encode = MagicMock(return_value=MagicMock(tolist=lambda: [[0.1, 0.2, 0.3]]))

        embedding_batch_size = 4

        async_embedding_func = get_embedding_function(
            embedding_engine="",
            embedding_model="test-model",
            embedding_function=mock_embedding_func,
            url="",
            key="",
            embedding_batch_size=embedding_batch_size,
        )

        # Call with prefix
        test_query = "test query"
        test_prefix = "query: "
        await async_embedding_func(test_query, prefix=test_prefix)

        # Verify both batch_size and prompt were passed
        mock_embedding_func.encode.assert_called_once()
        call_kwargs = mock_embedding_func.encode.call_args
        assert call_kwargs[1].get("batch_size") == embedding_batch_size
        assert call_kwargs[1].get("prompt") == test_prefix

    @pytest.mark.asyncio
    async def test_sentence_transformers_batch_size_string_conversion(self):
        """Test that batch_size is correctly converted to int if passed as string."""
        from open_webui.retrieval.utils import get_embedding_function

        mock_embedding_func = MagicMock()
        mock_embedding_func.encode = MagicMock(return_value=MagicMock(tolist=lambda: [[0.1, 0.2, 0.3]]))

        # Pass batch_size as string (simulating config value)
        embedding_batch_size = "16"

        async_embedding_func = get_embedding_function(
            embedding_engine="",
            embedding_model="test-model",
            embedding_function=mock_embedding_func,
            url="",
            key="",
            embedding_batch_size=embedding_batch_size,
        )

        await async_embedding_func("test query")

        # Verify batch_size was converted to int
        call_kwargs = mock_embedding_func.encode.call_args
        assert call_kwargs[1].get("batch_size") == 16
        assert isinstance(call_kwargs[1].get("batch_size"), int)
