import logging
import requests
from typing import Optional, List, Tuple

from open_webui.env import ENABLE_FORWARD_USER_INFO_HEADERS, SRC_LOG_LEVELS
from open_webui.retrieval.models.base_reranker import BaseReranker
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class ExternalReranker(BaseReranker):
    def __init__(
        self,
        api_key: str,
        url: str = "http://localhost:8080/v1/rerank",
        model: str = "reranker",
        user=Depends(get_verified_user),
    ):
        self.api_key = api_key
        self.url = url
        self.model = model

    def predict(self, sentences: List[Tuple[str, str]]) -> Optional[List[float]]:
        query = sentences[0][0]
        docs = [i[1] for i in sentences]

        payload = {
            "model": self.model,
            "query": query,
            "documents": docs,
            "top_n": len(docs),
        }

        try:
            log.info(f"ExternalReranker:predict:model {self.model}")
            log.info(f"ExternalReranker:predict:query {query}")

            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            if ENABLE_FORWARD_USER_INFO_HEADERS:
                headers["X-OpenWebUI-User-Name"] = user.name
                headers["X-OpenWebUI-User-Id"] = user.id
                headers["X-OpenWebUI-User-Email"] = user.email
                headers["X-OpenWebUI-User-Role"] = user.role

            r = requests.post(
                f"{self.url}",
                headers,
                json=payload,
            )

            r.raise_for_status()
            data = r.json()

            if "results" in data:
                sorted_results = sorted(data["results"], key=lambda x: x["index"])
                return [result["relevance_score"] for result in sorted_results]
            else:
                log.error("No results found in external reranking response")
                return None

        except Exception as e:
            log.exception(f"Error in external reranking: {e}")
            return None
