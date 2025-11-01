import logging
from typing import List, Optional, Tuple

from google.cloud import discoveryengine_v1 as discoveryengine

from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.models.base_reranker import BaseReranker


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class VertexAIReranker(BaseReranker):
    def __init__(
        self,
        project_id: str,
        location: str = "global",
        ranking_config: str = "default_ranking_config",
        model: str = "semantic-ranker-default@latest",
    ) -> None:
        self.project_id = project_id
        self.location = location
        self.ranking_config_name = ranking_config
        self.model = model
        log.info(
            f"VertexAIReranker:init project='{self.project_id}', location='{self.location}', ranking_config='{self.ranking_config_name}', model='{self.model}'"
        )

        # Client uses Application Default Credentials (ADC)
        self.client = discoveryengine.RankServiceClient()

        self.ranking_config_path = self.client.ranking_config_path(
            project=self.project_id,
            location=self.location,
            ranking_config=self.ranking_config_name,
        )

    def predict(
        self, sentences: List[Tuple[str, str]], documents=None
    ) -> Optional[List[float]]:
        if not sentences:
            return []

        query = sentences[0][0]
        docs = [text for (_, text) in sentences]

        # Extract titles from documents metadata if available
        titles = []
        if documents:
            for doc in documents:
                # Extract filename from metadata using the standard "source" key
                metadata = getattr(doc, "metadata", {})
                title = metadata.get("source", "")
                titles.append(title)
        else:
            titles = [""] * len(docs)

        # Build RankingRecord list with titles
        records = [
            discoveryengine.RankingRecord(id=str(i), title=titles[i], content=doc)
            for i, doc in enumerate(docs)
        ]

        request = discoveryengine.RankRequest(
            ranking_config=self.ranking_config_path,
            model=self.model,
            # Rank all provided docs; downstream compressor applies TOP_K_RERANKER
            top_n=len(docs),
            query=query,
            records=records,
        )

        try:
            response = self.client.rank(request=request)
            log.debug(
                f"VertexAIReranker:rank model='{self.model}', query_len={len(query)}, docs={len(docs)}, returned={len(response.records)}"
            )
            # Response returns records with scores in ranked order; restore scores per original order
            # Map id -> score, then return list aligned to original docs order
            id_to_score = {r.id: getattr(r, "score", 0.0) for r in response.records}
            scores: List[float] = []
            for i in range(len(docs)):
                scores.append(float(id_to_score.get(str(i), 0.0)))
            return scores
        except Exception as e:
            log.exception(f"Error calling Google Vertex AI Ranking API: {e}")
            return None
