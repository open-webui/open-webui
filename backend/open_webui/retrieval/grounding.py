"""
RAG Grounding Step Module

Implements a lightweight grounding step after retrieval to prevent silent semantic drift
when using different embedding models. Addresses community feedback about "ghost matches"
where retrieved content seems relevant but generates off-topic responses.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)


class GroundingResult:
    """Result of the grounding step validation"""

    def __init__(
        self,
        validated_documents: List[Dict[str, Any]],
        filtered_count: int,
        average_confidence: float,
        validation_scores: List[float],
    ):
        self.validated_documents = validated_documents
        self.filtered_count = filtered_count
        self.average_confidence = average_confidence
        self.validation_scores = validation_scores


def apply_grounding_step(
    query: str,
    query_embedding: List[float],
    retrieved_documents: List[Dict[str, Any]],
    embedding_function,
    threshold: float = 0.3,
    user=None,
) -> GroundingResult:
    """
    Apply grounding step to validate retrieved documents against the original query.

    Args:
        query: Original query string
        query_embedding: Query embedding vector
        retrieved_documents: List of documents from retrieval step
        embedding_function: Function to generate embeddings for document texts
        threshold: Minimum relevance threshold (0.0 to 1.0)
        user: User context for embedding function

    Returns:
        GroundingResult with validated documents and metrics
    """
    if not retrieved_documents:
        return GroundingResult([], 0, 0.0, [])

    try:
        # Extract document texts for re-embedding
        document_texts = []
        for doc in retrieved_documents:
            if isinstance(doc, dict):
                text = doc.get("document", doc.get("text", doc.get("content", "")))
                document_texts.append(str(text) if text else "")
            else:
                document_texts.append(str(doc))

        # Generate embeddings for documents using the same embedding function
        log.debug(f"Grounding step: re-embedding {len(document_texts)} documents")
        document_embeddings = embedding_function(document_texts, prefix=None, user=user)

        if not document_embeddings:
            log.warning("Failed to generate document embeddings in grounding step")
            return GroundingResult(
                retrieved_documents, 0, 1.0, [1.0] * len(retrieved_documents)
            )

        # Calculate cosine similarities
        query_vec = np.array(query_embedding).reshape(1, -1)
        doc_vecs = np.array(document_embeddings)
        similarities = cosine_similarity(query_vec, doc_vecs)[0]

        # Filter documents above threshold
        valid_indices = [
            i for i, score in enumerate(similarities) if score >= threshold
        ]
        validated_documents = [retrieved_documents[i] for i in valid_indices]
        filtered_count = len(retrieved_documents) - len(validated_documents)

        # Calculate metrics
        valid_scores = [similarities[i] for i in valid_indices] if valid_indices else []
        average_confidence = float(np.mean(valid_scores)) if valid_scores else 0.0

        if filtered_count > 0:
            log.info(
                f"Grounding step filtered {filtered_count} documents below threshold {threshold}"
            )

        return GroundingResult(
            validated_documents=validated_documents,
            filtered_count=filtered_count,
            average_confidence=average_confidence,
            validation_scores=similarities.tolist(),
        )

    except Exception as e:
        log.error(f"Error in grounding step: {e}")
        # Fallback: return original documents if grounding fails
        return GroundingResult(
            validated_documents=retrieved_documents,
            filtered_count=0,
            average_confidence=1.0,
            validation_scores=[1.0] * len(retrieved_documents),
        )


def format_documents_for_retrieval(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format validated documents back to the expected retrieval format."""
    if not documents:
        return {
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "documents": [[]],
            "embeddings": None,
        }

    ids = []
    distances = []
    metadatas = []
    doc_texts = []

    for doc in documents:
        if isinstance(doc, dict):
            ids.append(doc.get("id", ""))
            distances.append(doc.get("distance", 0.0))
            metadatas.append(doc.get("metadata", {}))
            doc_texts.append(
                doc.get("document", doc.get("text", doc.get("content", "")))
            )
        else:
            ids.append("")
            distances.append(0.0)
            metadatas.append({})
            doc_texts.append(str(doc))

    return {
        "ids": [ids],
        "distances": [distances],
        "metadatas": [metadatas],
        "documents": [doc_texts],
        "embeddings": None,
    }