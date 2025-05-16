from open_webui.routers.retrieval import get_rf
from open_webui.retrieval.models.base_reranker import BaseReranker

class DummyReranker(BaseReranker):
    def __init__(self, **kwargs):
        self.model = kwargs["model"]
        assert self.model == "dummy"

    def predict(self, sentences):
        return [1.0 for _ in sentences]

def test_dummy_reranker():
    engine = "open_webui.test.retrieval.test_reranker.DummyReranker"
    reranker: BaseReranker = get_rf(engine, "dummy")
    assert reranker.predict([("A", "B"), ("C", "D")]) == [1.0, 1.0]
