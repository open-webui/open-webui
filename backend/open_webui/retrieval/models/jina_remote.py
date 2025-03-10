import requests
import logging

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class JinaRemoteReranker:
    """Wrapper class for Jina remote reranking to match CrossEncoder interface"""

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.url = "https://api.jina.ai/v1/rerank"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def predict(
        self, query: str, documents: list[str], top_n: int = None
    ) -> list[tuple[str, float]]:
        """
        Predict relevance scores for pairs of queries and documents.

        Args:
            query: Query string
            documents: List of document strings
        Returns:
            List of tuples (index, relevance_score)
            - index: index of the document in the original documents list
            - relevance_score: relevance score of the document
        """
        if not query or not documents:
            log.warning("No pairs provided to JinaReranker")
            return []

        try:
            data = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            }

            response = requests.post(self.url, headers=self.headers, json=data)
            response.raise_for_status()

            results = response.json()["results"]
            # Extract scores in same order as input documents
            return [
                (result["index"], result["relevance_score"])
                for result in results
            ]

        except Exception as e:
            log.error(f"Jina reranking failed: {str(e)}")
            # Return neutral scores on error
            return [0.5] * len(documents)
