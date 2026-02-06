"""
Tests for OpenSearch vector database client - opensearch-py 3.0 compatibility.

Verifies that all opensearch-py API calls use keyword-only arguments,
which is required for compatibility with opensearch-py >= 3.0.0.

See: https://github.com/open-webui/open-webui/issues/20649

Strategy: We load *only* the opensearch.py module using importlib, injecting
mock stubs for all its imports. This avoids pulling in the entire open_webui
package dependency tree (uvicorn, redis, authlib, etc.).
"""

import importlib
import importlib.util
import os
import sys
import types
import pytest
from unittest.mock import Mock, MagicMock, patch, call

# ---------------------------------------------------------------------------
# Locate the source file
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate from test dir up to backend/open_webui/retrieval/vector/dbs/opensearch.py
_BACKEND_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", "..", ".."))
_OPENSEARCH_PY = os.path.join(
    _BACKEND_DIR,
    "open_webui", "retrieval", "vector", "dbs", "opensearch.py",
)
assert os.path.isfile(_OPENSEARCH_PY), f"Cannot find {_OPENSEARCH_PY}"


def _load_opensearch_module():
    """Load the opensearch.py module in isolation with mocked dependencies.

    Returns the loaded module object.
    """
    # Create mock modules for all dependencies
    mock_opensearchpy = types.ModuleType("opensearchpy")
    mock_opensearchpy.OpenSearch = MagicMock
    mock_helpers = types.ModuleType("opensearchpy.helpers")
    mock_helpers.bulk = MagicMock()
    mock_opensearchpy.helpers = mock_helpers

    # Mock the internal imports
    mock_process_metadata = MagicMock(side_effect=lambda x: x)

    mock_vector_utils = types.ModuleType("open_webui.retrieval.vector.utils")
    mock_vector_utils.process_metadata = mock_process_metadata

    # Create VectorDBBase and data classes
    class VectorDBBase:
        pass

    class VectorItem:
        pass

    class SearchResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class GetResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    mock_vector_main = types.ModuleType("open_webui.retrieval.vector.main")
    mock_vector_main.VectorDBBase = VectorDBBase
    mock_vector_main.VectorItem = VectorItem
    mock_vector_main.SearchResult = SearchResult
    mock_vector_main.GetResult = GetResult

    mock_config = types.ModuleType("open_webui.config")
    mock_config.OPENSEARCH_URI = "http://localhost:9200"
    mock_config.OPENSEARCH_SSL = False
    mock_config.OPENSEARCH_CERT_VERIFY = False
    mock_config.OPENSEARCH_USERNAME = "admin"
    mock_config.OPENSEARCH_PASSWORD = "admin"

    # Temporarily inject all mock modules
    saved = {}
    inject = {
        "opensearchpy": mock_opensearchpy,
        "opensearchpy.helpers": mock_helpers,
        "open_webui": types.ModuleType("open_webui"),
        "open_webui.retrieval": types.ModuleType("open_webui.retrieval"),
        "open_webui.retrieval.vector": types.ModuleType("open_webui.retrieval.vector"),
        "open_webui.retrieval.vector.utils": mock_vector_utils,
        "open_webui.retrieval.vector.main": mock_vector_main,
        "open_webui.retrieval.vector.dbs": types.ModuleType("open_webui.retrieval.vector.dbs"),
        "open_webui.config": mock_config,
    }

    for name, mod in inject.items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod

    try:
        spec = importlib.util.spec_from_file_location(
            "open_webui.retrieval.vector.dbs.opensearch",
            _OPENSEARCH_PY,
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        # Restore original sys.modules state
        for name, orig in saved.items():
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig


# Load once at module level
_mod = _load_opensearch_module()
OpenSearchClient = _mod.OpenSearchClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_opensearch_3x_mock():
    """Create a mock OpenSearch client that enforces keyword-only args on refresh().

    In opensearch-py >= 3.0.0, IndicesClient.refresh() rejects positional args:

        TypeError: IndicesClient.refresh() takes 1 positional argument but 2
        positional arguments (and 2 keyword-only arguments) were given

    We replicate this behavior so our tests prove the fix works.
    """
    client = MagicMock()

    # Simulate the 3.0.0 keyword-only signature
    def refresh_keyword_only(*, index=None, params=None, headers=None):
        return {"_shards": {"total": 2, "successful": 1, "failed": 0}}

    client.indices.refresh = Mock(side_effect=refresh_keyword_only)
    client.indices.exists.return_value = True
    client.indices.create.return_value = {"acknowledged": True}
    return client


def _make_test_items(count=1, dim=3):
    """Create test VectorItem-like dicts."""
    return [
        {
            "id": f"test-id-{i}",
            "vector": [0.1 * (i + 1)] * dim,
            "text": f"test document {i}",
            "metadata": {"source": "test"},
        }
        for i in range(count)
    ]


def _make_client_with_mock(mock_client):
    """Create an OpenSearchClient whose underlying client is our mock."""
    obj = object.__new__(OpenSearchClient)
    obj.index_prefix = "open_webui"
    obj.client = mock_client
    return obj


# ===================================================================
# Test class: refresh() must use keyword argument `index=`
# ===================================================================

class TestOpenSearchRefreshKeywordArgs:
    """Test that IndicesClient.refresh() is called with keyword argument `index=`.

    In opensearch-py >= 3.0.0, all auto-generated API methods enforce
    keyword-only arguments. Passing the index name as a positional argument
    to IndicesClient.refresh() raises:

        TypeError: IndicesClient.refresh() takes 1 positional argument but 2
        positional arguments (and 2 keyword-only arguments) were given

    These tests verify the fix for all three call sites in OpenSearchClient:
    - insert()
    - upsert()
    - delete()
    """

    def test_insert_calls_refresh_with_keyword_arg(self):
        """Test that insert() calls indices.refresh(index=...) not refresh(index_name)."""
        mock_client = _make_opensearch_3x_mock()
        client = _make_client_with_mock(mock_client)

        client.insert("test_collection", _make_test_items())

        # Verify refresh was called exactly once
        mock_client.indices.refresh.assert_called_once()

        # Verify it was called with keyword argument index=
        call_kwargs = mock_client.indices.refresh.call_args
        assert "index" in call_kwargs.kwargs, (
            "refresh() must be called with keyword argument 'index=', "
            "not as a positional argument (required by opensearch-py >= 3.0.0)"
        )
        assert call_kwargs.kwargs["index"] == "open_webui_test_collection"

        # Verify NO positional args were passed (only keyword)
        assert len(call_kwargs.args) == 0, (
            "refresh() must not receive positional arguments "
            "(opensearch-py >= 3.0.0 rejects them with TypeError)"
        )

    def test_upsert_calls_refresh_with_keyword_arg(self):
        """Test that upsert() calls indices.refresh(index=...) not refresh(index_name)."""
        mock_client = _make_opensearch_3x_mock()
        client = _make_client_with_mock(mock_client)

        client.upsert("test_collection", _make_test_items())

        mock_client.indices.refresh.assert_called_once()
        call_kwargs = mock_client.indices.refresh.call_args
        assert "index" in call_kwargs.kwargs
        assert call_kwargs.kwargs["index"] == "open_webui_test_collection"
        assert len(call_kwargs.args) == 0

    def test_delete_by_ids_calls_refresh_with_keyword_arg(self):
        """Test that delete(ids=...) calls indices.refresh(index=...) not refresh(index_name)."""
        mock_client = _make_opensearch_3x_mock()
        client = _make_client_with_mock(mock_client)

        client.delete("test_collection", ids=["id1", "id2"])

        mock_client.indices.refresh.assert_called_once()
        call_kwargs = mock_client.indices.refresh.call_args
        assert "index" in call_kwargs.kwargs
        assert call_kwargs.kwargs["index"] == "open_webui_test_collection"
        assert len(call_kwargs.args) == 0

    def test_delete_by_filter_calls_refresh_with_keyword_arg(self):
        """Test that delete(filter=...) calls indices.refresh(index=...) not refresh(index_name)."""
        mock_client = _make_opensearch_3x_mock()
        client = _make_client_with_mock(mock_client)

        client.delete("test_collection", filter={"source": "test"})

        mock_client.indices.refresh.assert_called_once()
        call_kwargs = mock_client.indices.refresh.call_args
        assert "index" in call_kwargs.kwargs
        assert call_kwargs.kwargs["index"] == "open_webui_test_collection"
        assert len(call_kwargs.args) == 0

    def test_refresh_raises_typeerror_with_positional_arg_on_3x(self):
        """Demonstrate that opensearch-py >= 3.0.0 rejects positional args to refresh().

        This test simulates the exact error from issue #20649 to prove our fix
        prevents it. We mock refresh() to enforce keyword-only args (as 3.0.0 does),
        then verify our code does NOT trigger the TypeError.
        """
        mock_client = _make_opensearch_3x_mock()
        client = _make_client_with_mock(mock_client)

        # First, prove the mock enforces keyword-only args (like opensearch-py 3.0.0)
        with pytest.raises(TypeError):
            mock_client.indices.refresh("open_webui_test_collection")

        # Reset the mock call count
        mock_client.indices.refresh.reset_mock()

        # Now verify our fixed code works without raising TypeError
        client.insert("test_collection", _make_test_items())

        # Verify refresh was called successfully with keyword arg
        mock_client.indices.refresh.assert_called_once_with(
            index="open_webui_test_collection"
        )


# ===================================================================
# Test class: audit ALL opensearch-py API calls for keyword args
# ===================================================================

class TestOpenSearchAllApiCallsUseKeywordArgs:
    """Verify ALL opensearch-py API calls in OpenSearchClient use keyword arguments.

    opensearch-py >= 3.0.0 enforces keyword-only arguments for all auto-generated
    API methods. This test class audits that every call complies.
    """

    def test_has_collection_uses_keyword_args(self):
        """Test that has_collection uses indices.exists(index=...)."""
        mock_client = MagicMock()
        client = _make_client_with_mock(mock_client)

        client.has_collection("test_collection")

        mock_client.indices.exists.assert_called_once_with(
            index="open_webui_test_collection"
        )

    def test_delete_collection_uses_keyword_args(self):
        """Test that delete_collection uses indices.delete(index=...)."""
        mock_client = MagicMock()
        client = _make_client_with_mock(mock_client)

        client.delete_collection("test_collection")

        mock_client.indices.delete.assert_called_once_with(
            index="open_webui_test_collection"
        )

    def test_search_uses_keyword_args(self):
        """Test that search() uses client.search(index=..., body=...)."""
        mock_client = MagicMock()
        mock_client.indices.exists.return_value = True
        mock_client.search.return_value = {"hits": {"hits": []}}
        client = _make_client_with_mock(mock_client)

        client.search("test_collection", vectors=[[0.1, 0.2, 0.3]])

        call_kwargs = mock_client.search.call_args
        assert "index" in call_kwargs.kwargs
        assert "body" in call_kwargs.kwargs
        assert len(call_kwargs.args) == 0

    def test_reset_uses_keyword_args(self):
        """Test that reset() uses indices.get(index=...) and indices.delete(index=...)."""
        mock_client = MagicMock()
        mock_client.indices.get.return_value = {
            "open_webui_col1": {},
            "open_webui_col2": {},
        }
        client = _make_client_with_mock(mock_client)

        client.reset()

        mock_client.indices.get.assert_called_once_with(index="open_webui_*")
        assert mock_client.indices.delete.call_count == 2
        for c in mock_client.indices.delete.call_args_list:
            assert "index" in c.kwargs
            assert len(c.args) == 0
