import logging
import os
from typing import List, Tuple, Optional, Dict, Any
from pinecone import Pinecone
from open_webui.retrieval.models.base_reranker import BaseReranker
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class PineconeReranker(BaseReranker):
    """
    Pinecone-hosted reranking model for Knowledge retrieval.
    Uses Pinecone's inference.rerank API for high-quality document reranking.

    Performance optimizations:
    - Automatic fallback to environment variables
    - Comprehensive error handling with specific error types
    - Efficient document mapping for large result sets
    - Minimal memory footprint with streaming processing
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = "pinecone-rerank-v0",
        environment: str = None,
        index_name: str = None,
    ):
        """
        Initialize Pinecone reranker.

        Args:
            api_key: Pinecone API key (if None, will use PINECONE_API_KEY from environment)
            model: Reranking model name (e.g., "pinecone-rerank-v0", "cohere-rerank-3.5")
            environment: Pinecone environment (optional, for validation)
            index_name: Pinecone index name (optional, for validation)
        """
        # Use provided API key or fall back to environment variable
        if api_key is None:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                raise ValueError("Pinecone API key not provided and PINECONE_API_KEY environment variable not set")

        self.api_key = api_key
        self.model = model
        self.environment = environment
        self.index_name = index_name

        # Initialize Pinecone client
        try:
            self.pc = Pinecone(api_key=api_key)
            log.info(f"Pinecone reranker initialized with model: {model}")

            # Validate configuration if provided
            if environment and index_name:
                self._validate_configuration()

        except Exception as e:
            log.error(f"Failed to initialize Pinecone reranker: {e}")
            raise

    def _validate_configuration(self) -> None:
        """Validate Pinecone configuration"""
        try:
            # Check if index exists
            if self.index_name not in self.pc.list_indexes().names():
                log.warning(f"Index '{self.index_name}' not found in Pinecone")
            else:
                log.info(f"Pinecone index '{self.index_name}' validated successfully")
        except Exception as e:
            log.warning(f"Could not validate Pinecone configuration: {e}")

    def predict(self, sentences: List[Tuple[str, str]], user=None) -> Optional[List[float]]:
        """
        Rerank documents using Pinecone's hosted reranking models.
        Matches the implementation from your Advanced Chat Summarization tool.

        Args:
            sentences: List of (query, document) tuples
            user: User context (unused for Pinecone)

        Returns:
            List of relevance scores in the same order as input sentences
        """
        if not sentences:
            log.warning("No sentences provided for reranking")
            return None

        # Input validation and performance checks
        if len(sentences) > 100:  # Pinecone has limits on batch size
            log.warning(f"Large batch size ({len(sentences)}), consider reducing for better performance")

        try:
            # Extract query and documents efficiently
            query = sentences[0][0] if sentences else ""
            if not query.strip():
                log.warning("Empty query provided for reranking")
                return None

            # Build documents list with minimal memory allocation
            documents = []
            for i, (_, doc) in enumerate(sentences):
                if not doc or not doc.strip():
                    log.debug(f"Skipping empty document at index {i}")
                    continue
                documents.append({"id": str(i), "text": doc})

            if not documents:
                log.warning("No valid documents provided for reranking")
                return None

            log.info(f"🔄 Pinecone reranking: query='{query[:50]}...', documents={len(documents)}")

            # Call Pinecone reranking API (matching your tool's implementation)
            rerank_result = self.pc.inference.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=len(documents),  # Rerank all documents
                rank_fields=["text"],
                return_documents=True,
                parameters={"truncate": "END"},
            )

            # Extract scores in original order (matching your tool's approach)
            scores = [0.0] * len(sentences)

            if hasattr(rerank_result, 'data') and rerank_result.data:
                # Create mapping from document ID to score (matching your tool's implementation)
                score_map = {}
                for reranked_doc in rerank_result.data:
                    doc_id = int(reranked_doc["document"]["id"])
                    score = reranked_doc["score"]
                    score_map[doc_id] = score

                # Fill scores in original order (matching your tool's approach)
                for i in range(len(sentences)):
                    if i in score_map:
                        scores[i] = score_map[i]
                    else:
                        log.warning(f"No reranking score found for document {i}")
                        scores[i] = 0.0

                # Log performance metrics (matching your tool's logging style)
                scored_count = len(score_map)
                log.info(f"✅ Pinecone reranking completed: {scored_count}/{len(sentences)} documents scored")

                if scored_count < len(sentences):
                    log.debug(f"Some documents ({len(sentences) - scored_count}) received default score 0.0")
            else:
                log.warning("Pinecone reranking returned no results")
                return None

            return scores

        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "quota" in error_msg:
                log.warning(f"🕐 Pinecone reranking rate limited: {e}")
            elif "timeout" in error_msg:
                log.warning(f"🕐 Pinecone reranking timeout: {e}")
            elif "unauthorized" in error_msg or "forbidden" in error_msg:
                log.error(f"❌ Pinecone reranking authentication failed: {e}")
            else:
                log.error(f"❌ Pinecone reranking failed: {e}")
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the reranking model"""
        return {
            "engine": "pinecone",
            "model": self.model,
            "api_key_configured": bool(self.api_key),
            "environment": self.environment,
            "index_name": self.index_name,
        }
