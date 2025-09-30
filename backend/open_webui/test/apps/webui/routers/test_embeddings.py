import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app (adjust import as needed for your project structure)
from open_webui.main import app

client = TestClient(app)


def test_embedding_filter_applied(monkeypatch):
    """
    Integration test: Ensure that Filters are applied to embedding requests.
    This test assumes a Filter is registered that adds a known key to the response.
    """

    # Monkeypatch process_filter_functions to simulate a filter effect
    from open_webui.utils import embeddings as embeddings_utils

    async def mock_process_filter_functions(
        request, filter_functions, filter_type, form_data, extra_params
    ):
        # Simulate a filter that adds a marker to the response
        if filter_type == "outlet":
            if isinstance(form_data, dict):
                form_data["filter_marker"] = "applied"
        return form_data, {}

    monkeypatch.setattr(
        "open_webui.utils.filter.process_filter_functions",
        mock_process_filter_functions,
    )

    # Prepare a minimal embedding request
    payload = {"model": "test-embedding-model", "input": "hello world"}

    # Monkeypatch get_sorted_filter_ids to simulate an active filter
    monkeypatch.setattr(
        "open_webui.utils.filter.get_sorted_filter_ids",
        lambda request, model, enabled_filter_ids=None: ["mock_filter_id"],
    )

    # Monkeypatch Functions.get_function_by_id to return a dummy object
    class DummyFunction:
        id = "mock_filter_id"

    import open_webui.models.functions as functions_mod

    monkeypatch.setattr(
        functions_mod.Functions,
        "get_function_by_id",
        staticmethod(lambda fid: DummyFunction() if fid == "mock_filter_id" else None),
    )

    # Monkeypatch model lookup to always return a dummy model
    monkeypatch.setattr(
        embeddings_utils,
        "Models",
        type("Models", (), {"get_model_by_id": staticmethod(lambda mid: {"id": mid})}),
    )

    # Monkeypatch app state to provide the dummy model
    with client:
        client.app.state.MODELS = {
            "test-embedding-model": {"id": "test-embedding-model"}
        }
        response = client.post("/openai/embeddings", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "filter_marker" in data
        assert data["filter_marker"] == "applied"
