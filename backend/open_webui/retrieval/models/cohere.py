import logging
import requests
from typing import Optional, List, Tuple

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

class CohereReranking:
    def __init__(
            self,
            api_key: str,
            url: str = "https://api.cohere.com",
            model: str = "rerank-v3.5",
        ):
        self.api_key = api_key
        self.url = url
        self.model = model

    def predict(self, sentences: List[Tuple[str, str]]) -> Optional[List[float]]:
        try:
            log.info(f"CohereReranking:predict:model {self.model}")
            
            query = sentences[0][0]
            docs = [i[1] for i in sentences]

            json_data = {
                "model": self.model,
                "query": query,
                "documents": docs,
                "top_n": len(docs)
            }

            r = requests.post(
                f"{self.url}/v2/rerank",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=json_data,
            )
            r.raise_for_status()
            data = r.json()
            
            if "results" in data:
                log.debug(f"CohereReranking:predict:results {data['results']}")
                return [result["relevance_score"] for result in data["results"]]
            else:
                log.error("No results found in Cohere reranking response")
                return None
                
        except Exception as e:
            log.exception(f"Error in Cohere reranking: {e}")
            return None
