import datetime as dt
from typing import Any

from open_webui.retrieval.vector.main import SearchResult
from open_webui.utils.misc import sanitize_text_for_db

KEYS_TO_EXCLUDE = ['content', 'pages', 'tables', 'paragraphs', 'sections', 'figures']

# A nested metadata value is deep-copied onto every chunk by the text splitter, so one
# oversized value costs memory proportional to the chunk count. KEYS_TO_EXCLUDE catches the
# field names we know about; this bounds the size of the nested values we do not.
MAX_NESTED_METADATA_CHARS = 4096

# Scalars are exempt on purpose: pinecone.py and s3vector.py put the chunk text itself into
# metadata before calling process_metadata, and dropping that would lose the stored document.
_CONTAINER_TYPES = (list, dict, tuple, set)

# Floor charged per item visited, which is what bounds the walk by the ceiling rather than by
# the size of the value.
_ITEM_OVERHEAD = 2


def _is_unbounded(value: Any) -> bool:
    """True when str() of a container value would exceed MAX_NESTED_METADATA_CHARS characters.

    Stops as soon as the ceiling is passed, so the work is bounded by the ceiling rather than
    by the value, and nothing is serialized in order to measure it. Nesting is charged like any
    other item, so depth cannot hide size and a cycle terminates. The charge under-estimates
    what str() writes, so a value that would fit is never dropped.
    """
    if not isinstance(value, _CONTAINER_TYPES):
        return False

    budget = MAX_NESTED_METADATA_CHARS
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        entries = current.items() if isinstance(current, dict) else enumerate(current)
        for key, item in entries:
            budget -= _ITEM_OVERHEAD + (len(key) if isinstance(key, str) else 0)
            if isinstance(item, _CONTAINER_TYPES):
                stack.append(item)
            elif isinstance(item, (str, bytes, bytearray)):
                # len() is O(1) here, and these are the only leaves that can be large. Never
                # str() a leaf: that materializes what this guard exists to keep out.
                budget -= len(item)
            if budget < 0:
                return True
    return False


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    # Removes large/redundant fields from metadata dict.
    return {key: value for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE and not _is_unbounded(value)}


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    # Removes large fields, converts non-serializable types (datetime, list, dict) to strings,
    # and sanitizes strings for database storage (strips null bytes and invalid surrogates).
    result = {}
    for key, value in metadata.items():
        # Skip large fields
        if key in KEYS_TO_EXCLUDE or _is_unbounded(value):
            continue
        if value is None:
            continue
        # Convert non-serializable fields to strings
        if isinstance(value, (dt.datetime, list, dict)):
            result[key] = sanitize_text_for_db(str(value))
        else:
            result[key] = sanitize_text_for_db(value)
    return result


def merge_hybrid_search_results(
    vector_result: SearchResult | None,
    fts_results: list[dict[str, Any]],
    num_queries: int,
    limit: int,
    hybrid_bm25_weight: float,
) -> SearchResult:
    rank_constant = 60.0
    bm25_weight = min(max(hybrid_bm25_weight, 0.0), 1.0)
    vector_weight = 1.0 - bm25_weight

    ids = [[] for _ in range(num_queries)]
    distances = [[] for _ in range(num_queries)]
    documents = [[] for _ in range(num_queries)]
    metadatas = [[] for _ in range(num_queries)]

    for qid in range(num_queries):
        candidates: dict[str, dict[str, Any]] = {}

        if vector_result and vector_result.ids and qid < len(vector_result.ids):
            for rank, item_id in enumerate(vector_result.ids[qid] or [], start=1):
                score = vector_weight / (rank_constant + rank) if vector_weight > 0 else 0
                if score <= 0:
                    continue

                candidate = candidates.setdefault(
                    item_id,
                    {
                        'score': 0.0,
                        'document': vector_result.documents[qid][rank - 1],
                        'metadata': vector_result.metadatas[qid][rank - 1],
                    },
                )
                candidate['score'] += score

        for rank, row in enumerate(fts_results, start=1):
            score = bm25_weight / (rank_constant + rank) if bm25_weight > 0 else 0
            if score <= 0:
                continue

            item_id = row['id']
            candidate = candidates.setdefault(
                item_id,
                {
                    'score': 0.0,
                    'document': row['text'],
                    'metadata': row['vmetadata'],
                },
            )
            candidate['score'] += score

        ranked = sorted(candidates.items(), key=lambda item: item[1]['score'], reverse=True)[:limit]
        ids[qid] = [item_id for item_id, _ in ranked]
        distances[qid] = [candidate['score'] for _, candidate in ranked]
        documents[qid] = [candidate['document'] for _, candidate in ranked]
        metadatas[qid] = [candidate['metadata'] for _, candidate in ranked]

    return SearchResult(ids=ids, distances=distances, documents=documents, metadatas=metadatas)
