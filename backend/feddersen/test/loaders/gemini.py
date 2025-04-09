import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from langchain_core.documents import Document

from feddersen.loaders.gemini import GeminiLoader

env_path = Path(__file__).parent.parent / ".env.test"


@pytest.mark.skipif(not env_path.exists(), reason="requires set env variables")
class TestGeminiLoader:
    """Test class for GeminiLoader"""

    @pytest.mark.asyncio
    async def test_alazy_load_success(self):
        """Test successful call to alazy_load"""
        # Get API credentials from environment - these should be loaded by the fixture
        if env_path.exists():
            load_dotenv(env_path)
        base_url = os.environ.get("OPENAI_API_BASE_URL")
        api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")

        # Use a test PDF file
        test_file_path = (
            Path(__file__).parent.parent / "test_files" / "rothschild_giraffe.pdf"
        )

        # If test file doesn't exist, skip the test
        if not test_file_path.exists():
            pytest.skip(
                f"Test file {test_file_path} does not exist. Please create a sample PDF file."
            )

        # Initialize the loader
        loader = GeminiLoader(
            base_url=base_url, api_key=api_key, file_path=test_file_path
        )

        # Call the method
        async for result in loader.alazy_load():
            # Verify the result is not None
            assert result is not None

            assert isinstance(result, Document)

            # Verify the result contains markdown content
            assert len(result.page_content) > 0

            print(result)
