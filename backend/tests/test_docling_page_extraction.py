"""
Test suite for Docling OCR page extraction functionality.

This test suite verifies that the DoclingLoader can correctly extract
page-level information from documents and create proper Document objects
with page metadata for citation purposes.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_webui.retrieval.loaders.main import DoclingLoader


class TestDoclingPageExtraction(unittest.TestCase):
    """Test cases for Docling page extraction functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_url = "http://test-docling:5001"
        self.test_api_key = "test-api-key"
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, "test.pdf")

        # Create a dummy PDF file for testing
        with open(self.test_file_path, "wb") as f:
            f.write(b"%PDF-1.4\n% Dummy PDF content for testing\n")

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        os.rmdir(self.temp_dir)

    def test_docling_loader_initialization(self):
        """Test DoclingLoader initialization with default parameters."""
        loader = DoclingLoader(
            url=self.test_url, api_key=self.test_api_key, file_path=self.test_file_path
        )

        self.assertEqual(loader.url, self.test_url)
        self.assertEqual(loader.api_key, self.test_api_key)
        self.assertEqual(loader.file_path, self.test_file_path)
        self.assertEqual(loader.file_name, "test.pdf")
        self.assertTrue(loader.extract_pages)
        self.assertEqual(loader.params, {})

    def test_docling_loader_initialization_with_extract_pages_false(self):
        """Test DoclingLoader initialization with extract_pages=False."""
        loader = DoclingLoader(
            url=self.test_url,
            api_key=self.test_api_key,
            file_path=self.test_file_path,
            extract_pages=False,
        )

        self.assertFalse(loader.extract_pages)

    def test_extract_pages_from_json_success(self):
        """Test successful page extraction from JSON content."""
        # Create sample JSON response that mimics Docling's output
        sample_json = {
            "pages": {
                "1": {"size": {"width": 595, "height": 841}, "orientation": "portrait"},
                "2": {"size": {"width": 595, "height": 841}, "orientation": "portrait"},
            },
            "texts": [
                {
                    "text": "This is page 1 content",
                    "prov": [{"page_no": 1}],
                    "bounding_box": [0, 0, 500, 100],
                },
                {
                    "text": "More content on page 1",
                    "prov": [{"page_no": 1}],
                    "bounding_box": [0, 100, 500, 200],
                },
                {
                    "text": "This is page 2 content",
                    "prov": [{"page_no": 2}],
                    "bounding_box": [0, 0, 500, 100],
                },
            ],
        }

        loader = DoclingLoader(
            url=self.test_url,
            api_key=self.test_api_key,
            file_path=self.test_file_path,
            extract_pages=True,
        )

        documents = loader._extract_pages_from_json(sample_json)

        # Verify we got 2 page documents
        self.assertEqual(len(documents), 2)

        # Check first page document
        page1_doc = documents[0]
        self.assertEqual(
            page1_doc.page_content, "This is page 1 content\nMore content on page 1"
        )
        self.assertEqual(page1_doc.metadata["page"], 0)  # 0-based index
        self.assertEqual(page1_doc.metadata["page_label"], 1)  # 1-based label
        self.assertEqual(page1_doc.metadata["total_pages"], 2)
        self.assertEqual(page1_doc.metadata["file_name"], "test.pdf")
        self.assertEqual(page1_doc.metadata["processing_engine"], "docling")
        self.assertEqual(page1_doc.metadata["content_length"], 45)

        # Check second page document
        page2_doc = documents[1]
        self.assertEqual(page2_doc.page_content, "This is page 2 content")
        self.assertEqual(page2_doc.metadata["page"], 1)  # 0-based index
        self.assertEqual(page2_doc.metadata["page_label"], 2)  # 1-based label
        self.assertEqual(page2_doc.metadata["total_pages"], 2)

    def test_extract_pages_from_json_empty_pages(self):
        """Test page extraction when no pages are found."""
        sample_json = {"pages": {}, "texts": []}

        loader = DoclingLoader(
            url=self.test_url,
            api_key=self.test_api_key,
            file_path=self.test_file_path,
            extract_pages=True,
        )

        documents = loader._extract_pages_from_json(sample_json)
        self.assertEqual(len(documents), 0)

    def test_extract_pages_from_json_malformed_data(self):
        """Test page extraction with malformed JSON data."""
        sample_json = {
            "pages": {"1": {"size": {"width": 595, "height": 841}}},
            "texts": [{"text": "Text without prov", "bounding_box": [0, 0, 500, 100]}],
        }

        loader = DoclingLoader(
            url=self.test_url,
            api_key=self.test_api_key,
            file_path=self.test_file_path,
            extract_pages=True,
        )

        documents = loader._extract_pages_from_json(sample_json)
        self.assertEqual(len(documents), 0)

    @patch("requests.post")
    def test_load_with_page_extraction_enabled(self, mock_post):
        """Test the load method with page extraction enabled."""
        # Mock the API response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "document": {
                "json_content": {
                    "pages": {"1": {"size": {"width": 595, "height": 841}}},
                    "texts": [{"text": "Page 1 content", "prov": [{"page_no": 1}]}],
                },
                "md_content": "This shouldn't be used when page extraction works",
            }
        }
        mock_post.return_value = mock_response

        loader = DoclingLoader(
            url=self.test_url,
            api_key=self.test_api_key,
            file_path=self.test_file_path,
            extract_pages=True,
        )

        documents = loader.load()

        # Verify the API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check that we requested both JSON and markdown formats
        self.assertEqual(call_args[1]["data"]["to_formats"], ["json", "md"])

        # Verify we got page-level documents
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].metadata["page"], 0)
        self.assertEqual(documents[0].metadata["page_label"], 1)

    @patch("requests.post")
    def test_load_with_page_extraction_disabled(self, mock_post):
        """Test the load method with page extraction disabled."""
        # Mock the API response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "document": {
                "json_content": {
                    "pages": {"1": {"size": {"width": 595, "height": 841}}}
                },
                "md_content": "Single document content",
            }
        }
        mock_post.return_value = mock_response

        loader = DoclingLoader(
            url=self.test_url,
            api_key=self.test_api_key,
            file_path=self.test_file_path,
            extract_pages=False,
        )

        documents = loader.load()

        # Verify we got a single document without page metadata
        self.assertEqual(len(documents), 1)
        self.assertNotIn("page", documents[0].metadata)
        self.assertNotIn("page_label", documents[0].metadata)
        self.assertEqual(documents[0].page_content, "Single document content")

    @patch("requests.post")
    def test_load_with_api_error(self, mock_post):
        """Test the load method when the API returns an error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.reason = "Internal Server Error"
        mock_response.text = "Service temporarily unavailable"
        mock_post.return_value = mock_response

        loader = DoclingLoader(
            url=self.test_url,
            api_key=self.test_api_key,
            file_path=self.test_file_path,
            extract_pages=True,
        )

        with self.assertRaises(Exception) as context:
            loader.load()

        self.assertIn("Error calling Docling", str(context.exception))

    @patch("requests.post")
    def test_load_fallback_to_markdown(self, mock_post):
        """Test fallback to markdown when JSON extraction fails."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "document": {
                "json_content": None,  # No JSON content
                "md_content": "Fallback markdown content",
            }
        }
        mock_post.return_value = mock_response

        loader = DoclingLoader(
            url=self.test_url,
            api_key=self.test_api_key,
            file_path=self.test_file_path,
            extract_pages=True,
        )

        documents = loader.load()

        # Should fallback to single document with markdown content
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].page_content, "Fallback markdown content")
        self.assertNotIn("page", documents[0].metadata)


if __name__ == "__main__":
    unittest.main()
