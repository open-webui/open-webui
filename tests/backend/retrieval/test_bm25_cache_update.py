import asyncio
import importlib
import sys
import types
from pathlib import Path

import pytest

# Ensure backend package is importable when running from repository root
BACKEND_ROOT = Path(__file__).resolve().parents[3] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class DummyCollectionResult:
    def __init__(self, documents, metadatas):
        self.documents = [documents]
        self.metadatas = [metadatas]


class DummyVectorClient:
    def __init__(self):
        self._collections: dict[str, DummyCollectionResult] = {}

    def set_collection(self, name: str, documents, metadatas):
        self._collections[name] = DummyCollectionResult(documents, metadatas)

    def get(self, collection_name: str):
        try:
            return self._collections[collection_name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unknown collection: {collection_name}") from exc


@pytest.fixture()
def bm25_modules(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{data_dir / 'webui.db'}")
    monkeypatch.setenv("VECTOR_DB", "chroma")

    dummy_firecrawl = types.ModuleType("firecrawl")
    dummy_firecrawl.Firecrawl = object
    sys.modules["firecrawl"] = dummy_firecrawl

    modules_to_clear = [
        "open_webui.config",
        "open_webui.env",
        "open_webui.retrieval.bm25_cache",
        "open_webui.routers.retrieval",
        "open_webui.retrieval.vector.factory",
        "open_webui.retrieval.vector.dbs.chroma",
    ]
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]

    bm25_cache = importlib.import_module("open_webui.retrieval.bm25_cache")
    retrieval_router = importlib.import_module("open_webui.routers.retrieval")

    return bm25_cache, retrieval_router


def test_update_bm25_cache_rebuilds_and_detects_up_to_date(bm25_modules):
    bm25_cache, retrieval_router = bm25_modules

    dummy_client = DummyVectorClient()
    collection_name = "test_collection"
    documents = ["hello world", "another document"]
    metadatas = [{"id": "1"}, {"id": "2"}]
    dummy_client.set_collection(collection_name, documents, metadatas)

    retrieval_router.VECTOR_DB_CLIENT = dummy_client

    bm25_cache.clear_cache()

    form = retrieval_router.UpdateBM25CacheForm(collection_names=[collection_name], rebuild=True)
    first_result = asyncio.run(retrieval_router.update_bm25_cache(form))

    assert first_result["status"] is True
    assert len(first_result["results"]) == 1

    first_entry = first_result["results"][0]
    assert first_entry["collection_name"] == collection_name
    assert first_entry["rebuilt"] is True
    assert first_entry["status"] == "up_to_date"
    assert first_entry["cache_metadata"] is not None
    assert first_entry["cache_metadata"].get("data_digest") == first_entry["expected_digest"]

    second_result = asyncio.run(retrieval_router.update_bm25_cache(form))
    second_entry = second_result["results"][0]

    assert second_entry["status"] == "up_to_date"
    assert second_entry["rebuilt"] is False
    assert second_entry["invalidated"] == {"memory": 0, "disk": 0}

    cache_metadata = bm25_cache.get_cache_metadata(collection_name)
    assert cache_metadata is not None
    assert cache_metadata.get("data_digest") == first_entry["expected_digest"]
