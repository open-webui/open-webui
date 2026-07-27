import json
from unittest.mock import MagicMock, patch
import pytest

from open_webui.retrieval.loaders.main import DoclingLoader


def test_docling_loader_serializes_complex_and_bool_params(tmp_path):
    dummy_file = tmp_path / "test.pdf"
    dummy_file.write_bytes(b"%PDF-1.4 dummy content")

    params = {
        "picture_description_api": {"endpoint": "http://localhost:11434", "model": "llava"},
        "do_picture_description": True,
        "do_ocr": False,
        "max_num_pages": 5,
        "pipeline_options": ["table", "layout"],
        "simple_str": "hello",
    }

    loader = DoclingLoader(
        url="http://localhost:8080",
        api_key="test-key",
        file_path=str(dummy_file),
        mime_type="application/pdf",
        params=params,
    )

    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "document": {"md_content": "Extracted text content"}
    }

    with patch("open_webui.retrieval.loaders.main.requests.post", return_value=mock_response) as mock_post:
        docs = loader.load()

        assert len(docs) == 1
        assert docs[0].page_content == "Extracted text content"

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        data = call_kwargs["data"]

        # Verify dict is JSON-serialized string
        assert data["picture_description_api"] == json.dumps(params["picture_description_api"])
        # Verify bool is JSON-serialized string ("true" / "false")
        assert data["do_picture_description"] == "true"
        assert data["do_ocr"] == "false"
        # Verify list is JSON-serialized string
        assert data["pipeline_options"] == json.dumps(params["pipeline_options"])
        # Verify primitives remain unchanged
        assert data["max_num_pages"] == 5
        assert data["simple_str"] == "hello"
        assert data["image_export_mode"] == "placeholder"
