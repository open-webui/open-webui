import datetime as dt
from typing import Any

from open_webui.env import RAG_METADATA_MAX_VALUE_CHARS
from open_webui.retrieval.vector.main import SearchResult
from open_webui.utils.misc import sanitize_text_for_db

KEYS_TO_EXCLUDE = [
    'content',
    'pages',
    'tables',
    'paragraphs',
    'sections',
    'figures',
    'documents',
    'keyValuePairs',
    'styles',
    'languages',
]


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    # Removes large/redundant fields from metadata dict.
    result = {}
    for key, value in metadata.items():
        if key in KEYS_TO_EXCLUDE:
            continue
        if RAG_METADATA_MAX_VALUE_CHARS is not None and isinstance(value, (list, dict)):
            try:
                if len(str(value)) > RAG_METADATA_MAX_VALUE_CHARS:
                    continue
            except (MemoryError, RecursionError, ValueError):
                continue
        result[key] = value
    return result


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    # Removes large fields, converts non-serializable types (datetime, list, dict) to strings,
    # and sanitizes strings for database storage (strips null bytes and invalid surrogates).
    result = {}
    for key, value in metadata.items():
        # Skip large fields
        if key in KEYS_TO_EXCLUDE:
            continue
        if value is None:
            continue
        if RAG_METADATA_MAX_VALUE_CHARS is not None and isinstance(value, (list, dict)):
            try:
                if len(str(value)) > RAG_METADATA_MAX_VALUE_CHARS:
                    continue
            except (MemoryError, RecursionError, ValueError):
                continue
        # Convert non-serializable fields to strings
        if isinstance(value, (dt.datetime, list, dict)):
            result[key] = sanitize_text_for_db(str(value))
        else:
            result[key] = sanitize_text_for_db(value)
    return result


def iter_filter_conditions(filter: dict[str, Any] | None):
    for key, value in (filter or {}).items():
        if isinstance(value, dict):
            if set(value) != {'$in'}:
                raise ValueError(f"Unsupported metadata filter for '{key}': {value}")
            yield key, '$in', list(value['$in'])
        else:
            yield key, '$eq', value


def normalize_filter(filter: dict[str, Any] | None) -> dict[str, Any]:
    return {key: {'$in': value} if op == '$in' else value for key, op, value in iter_filter_conditions(filter)}


def metadata_matches_filter(metadata: dict[str, Any], filter: dict[str, Any] | None) -> bool:
    if not isinstance(metadata, dict):
        return False
    for key, op, value in iter_filter_conditions(filter):
        actual = metadata.get(key)
        if op == '$in':
            if actual not in value:
                return False
        elif actual != value:
            return False
    return True


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
