"""Tests for PDF text extraction helpers.

The open_webui.retrieval.utils module has heavy transitive dependencies
(redis, chromadb, etc.) that are impractical to install in a lightweight
test environment.  These tests therefore import only the pure-function
helpers that have no application-level dependencies.

To run:
    PYTHONPATH=backend pytest backend/tests/retrieval/test_pdf_handling.py -v
"""

import io
import os
import sys
import types
import importlib.util
import pytest
from unittest.mock import Mock, patch

# ---------------------------------------------------------------------------
# Minimal stubs so we can exec just the target functions out of utils.py
# without pulling the entire app dependency tree.
# ---------------------------------------------------------------------------

# We import the three functions under test by executing a trimmed snippet
# of the source file.  This avoids the huge transitive import chain.

_UTILS_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        "open_webui",
        "retrieval",
        "utils.py",
    )
)


def _extract_functions():
    """Parse utils.py source and exec just the PDF-related functions."""
    import textwrap

    # Read the raw source
    with open(_UTILS_PATH) as f:
        source = f.read()

    # We only need these functions + their imports.  Build a minimal module.
    # Stub out the open_webui.retrieval.web.utils module so that the inline
    # ``from open_webui.retrieval.web.utils import validate_url`` inside
    # extract_pdf_from_url resolves without pulling the full app dependency tree.
    _web_utils_stub = types.ModuleType("open_webui.retrieval.web.utils")
    _web_utils_stub.validate_url = lambda url: True  # no-op for tests
    sys.modules.setdefault("open_webui", types.ModuleType("open_webui"))
    sys.modules.setdefault("open_webui.retrieval", types.ModuleType("open_webui.retrieval"))
    sys.modules.setdefault("open_webui.retrieval.web", types.ModuleType("open_webui.retrieval.web"))
    sys.modules["open_webui.retrieval.web.utils"] = _web_utils_stub

    code = textwrap.dedent("""\
    import io
    import logging
    import re
    import requests
    from urllib.parse import urlparse
    from langchain_core.documents import Document

    log = logging.getLogger(__name__)
    """)

    # Extract the function definitions we care about from the source.
    import ast
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        # Grab module-level assignments (PDF_MAX_SIZE = ...)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PDF_MAX_SIZE":
                    code += ast.get_source_segment(source, node) + "\n\n"

        # Grab the function definitions we need
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in (
                "extract_text_from_pdf_bytes",
                "extract_pdf_from_url",
                "get_content_from_url",
                "get_loader",
                "is_youtube_url",
            ):
                code += ast.get_source_segment(source, node) + "\n\n"

    ns = {}
    exec(compile(code, _UTILS_PATH, "exec"), ns)
    return ns


_ns = _extract_functions()
extract_text_from_pdf_bytes = _ns["extract_text_from_pdf_bytes"]
extract_pdf_from_url = _ns["extract_pdf_from_url"]
get_content_from_url = _ns["get_content_from_url"]
PDF_MAX_SIZE = _ns["PDF_MAX_SIZE"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_pdf(text: str = "Hello, World!") -> bytes:
    """Create a minimal valid single-page PDF containing *text*."""
    from pypdf import PdfWriter
    from pypdf.generic import (
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
    )

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    page = writer.pages[0]

    font_dict = DictionaryObject()
    font_dict[NameObject("/Type")] = NameObject("/Font")
    font_dict[NameObject("/Subtype")] = NameObject("/Type1")
    font_dict[NameObject("/BaseFont")] = NameObject("/Helvetica")

    resources = page.get("/Resources", DictionaryObject())
    if not isinstance(resources, DictionaryObject):
        resources = DictionaryObject(resources)
    font_resources = resources.get("/Font", DictionaryObject())
    if not isinstance(font_resources, DictionaryObject):
        font_resources = DictionaryObject(font_resources)
    font_resources[NameObject("/F1")] = font_dict
    resources[NameObject("/Font")] = font_resources
    page[NameObject("/Resources")] = resources

    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_data = f"BT /F1 12 Tf 100 700 Td ({escaped}) Tj ET"
    stream = DecodedStreamObject()
    stream.set_data(stream_data.encode("latin-1"))
    page[NameObject("/Contents")] = stream

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_request_mock(verify_ssl=True, trust_env=False):
    """Return a mock that looks like a FastAPI Request."""
    request = Mock()
    request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION = verify_ssl
    request.app.state.config.WEB_SEARCH_TRUST_ENV = trust_env
    return request


# ===========================================================================
# Tests
# ===========================================================================


class TestExtractTextFromPdfBytes:

    def test_valid_pdf(self):
        result = extract_text_from_pdf_bytes(_make_minimal_pdf("Hello, World!"))
        assert "Hello" in result
        assert "World" in result

    def test_blank_pdf_returns_placeholder(self):
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(612, 792)
        buf = io.BytesIO()
        writer.write(buf)

        result = extract_text_from_pdf_bytes(buf.getvalue())
        assert "no extractable text" in result

    def test_corrupted_bytes_raises(self):
        with pytest.raises(Exception):
            extract_text_from_pdf_bytes(b"not a pdf")

    def test_truncated_header_raises(self):
        with pytest.raises(Exception):
            extract_text_from_pdf_bytes(b"%PDF-1.4 broken")


class TestExtractPdfFromUrl:

    def _mock_session(self, mock_resp):
        """Create a mock requests.Session that works as a context manager."""
        session_instance = Mock()
        session_instance.get.return_value = mock_resp
        session_instance.__enter__ = Mock(return_value=session_instance)
        session_instance.__exit__ = Mock(return_value=False)
        return session_instance

    def test_success(self):
        pdf_bytes = _make_minimal_pdf("download test")
        mock_resp = Mock(content=pdf_bytes, headers={})
        mock_resp.raise_for_status = Mock()

        with patch("requests.Session") as cls:
            cls.return_value = self._mock_session(mock_resp)
            result = extract_pdf_from_url(
                _make_request_mock(), "https://example.com/doc.pdf"
            )

        assert "download test" in result

    def test_oversized_raises(self):
        mock_resp = Mock(content=b"x" * (PDF_MAX_SIZE + 1), headers={})
        mock_resp.raise_for_status = Mock()

        with patch("requests.Session") as cls:
            cls.return_value = self._mock_session(mock_resp)
            with pytest.raises(ValueError, match="size limit"):
                extract_pdf_from_url(
                    _make_request_mock(), "https://example.com/huge.pdf"
                )

    def test_content_length_precheck(self):
        """Content-Length header triggers early rejection before full download."""
        mock_resp = Mock(
            content=b"small",
            headers={"Content-Length": str(PDF_MAX_SIZE + 1)},
        )
        mock_resp.raise_for_status = Mock()
        mock_resp.close = Mock()

        with patch("requests.Session") as cls:
            cls.return_value = self._mock_session(mock_resp)
            with pytest.raises(ValueError, match="size limit"):
                extract_pdf_from_url(
                    _make_request_mock(), "https://example.com/big.pdf"
                )
            # Verify response was closed without reading the full body
            mock_resp.close.assert_called_once()


class TestGetContentFromUrl:
    """Test the URL-routing logic in get_content_from_url."""

    def test_pdf_extension_fast_path(self):
        orig = _ns["extract_pdf_from_url"]
        _ns["extract_pdf_from_url"] = Mock(return_value="fast path text")
        try:
            content, docs = get_content_from_url(
                _make_request_mock(), "https://example.com/report.pdf"
            )
            assert content == "fast path text"
            assert len(docs) == 1
            _ns["extract_pdf_from_url"].assert_called_once()
        finally:
            _ns["extract_pdf_from_url"] = orig

    def test_pdf_extension_case_insensitive(self):
        _ns["extract_pdf_from_url"] = Mock(return_value="text")
        try:
            get_content_from_url(_make_request_mock(), "https://example.com/R.PDF")
            _ns["extract_pdf_from_url"].assert_called_once()
        finally:
            _ns["extract_pdf_from_url"] = _extract_functions()["extract_pdf_from_url"]

    def test_pdf_binary_fallback(self):
        from langchain_core.documents import Document

        mock_loader = Mock()
        mock_loader.load.return_value = [
            Document(page_content="%PDF-1.4 garbage", metadata={})
        ]

        _ns["get_loader"] = Mock(return_value=mock_loader)
        _ns["extract_pdf_from_url"] = Mock(return_value="extracted text")
        try:
            content, docs = get_content_from_url(
                _make_request_mock(), "https://example.com/download?id=1"
            )
            assert content == "extracted text"
            _ns["extract_pdf_from_url"].assert_called_once()
        finally:
            ns2 = _extract_functions()
            _ns["get_loader"] = ns2["get_loader"]
            _ns["extract_pdf_from_url"] = ns2["extract_pdf_from_url"]

    def test_pdf_extension_error_fallback(self):
        """When .pdf fast-path extraction fails, an error message is returned."""
        _ns["extract_pdf_from_url"] = Mock(
            side_effect=Exception("connection refused")
        )
        try:
            content, docs = get_content_from_url(
                _make_request_mock(), "https://example.com/broken.pdf"
            )
            assert "[Error:" in content
            assert "broken.pdf" in content
            assert len(docs) == 1
        finally:
            _ns["extract_pdf_from_url"] = _extract_functions()["extract_pdf_from_url"]

    def test_html_content_unchanged(self):
        from langchain_core.documents import Document

        mock_loader = Mock()
        mock_loader.load.return_value = [
            Document(page_content="Hello from the web", metadata={})
        ]
        _ns["get_loader"] = Mock(return_value=mock_loader)
        try:
            content, docs = get_content_from_url(
                _make_request_mock(), "https://example.com/page"
            )
            assert content == "Hello from the web"
        finally:
            _ns["get_loader"] = _extract_functions()["get_loader"]
