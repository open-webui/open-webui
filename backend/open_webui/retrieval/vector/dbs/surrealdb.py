import logging
import math
import re
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from surrealdb import Surreal

from open_webui.config import (
    SURREALDB_DATABASE,
    SURREALDB_NAMESPACE,
    SURREALDB_PASSWORD,
    SURREALDB_TABLE,
    SURREALDB_URL,
    SURREALDB_USER,
    SURREALDB_VECTOR_INDEX_DIMENSION,
    SURREALDB_VECTOR_INDEX_DISTANCE,
    SURREALDB_VECTOR_INDEX_EFC,
    SURREALDB_VECTOR_INDEX_M,
    SURREALDB_VECTOR_INDEX_ENABLED,
)
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)

NO_LIMIT = 999999999

log = logging.getLogger(__name__)

TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
METADATA_FIELD_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TRANSIENT_ERROR_HINTS = (
    "connection",
    "connect",
    "timeout",
    "timed out",
    "reset",
    "refused",
    "temporar",
    "unavailable",
    "closed",
    "eof",
    "broken pipe",
    "transport",
)


class SurrealDBClient(VectorDBBase):
    def __init__(self):
        self.url = SURREALDB_URL
        self.namespace = SURREALDB_NAMESPACE
        self.database = SURREALDB_DATABASE
        self.username = SURREALDB_USER
        self.password = SURREALDB_PASSWORD
        self.table_name = self._sanitize_table_name(SURREALDB_TABLE)
        self.vector_index_enabled = SURREALDB_VECTOR_INDEX_ENABLED
        self.vector_index_dimension = SURREALDB_VECTOR_INDEX_DIMENSION
        self.vector_index_distance = SURREALDB_VECTOR_INDEX_DISTANCE
        self.vector_index_m = SURREALDB_VECTOR_INDEX_M
        self.vector_index_efc = SURREALDB_VECTOR_INDEX_EFC

        self._client_lock = Lock()
        self.client = None
        self._connect_client()
        self._initialize_schema()

    # VectorDBBase interface methods
    def has_collection(self, collection_name: str) -> bool:
        try:
            statement_results = self._run_query_raw(
                f"SELECT item_id FROM {self.table_name} WHERE collection_name = $collection_name LIMIT 1;",
                {"collection_name": collection_name},
            )
            rows = self._result_rows(statement_results)
            return len(rows) > 0
        except Exception as e:
            log.exception(f"Error checking collection '{collection_name}': {e}")
            return False

    def delete_collection(self, collection_name: str) -> None:
        self._run_query_raw(
            f"DELETE {self.table_name} WHERE collection_name = $collection_name;",
            {"collection_name": collection_name},
        )

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        self.upsert(collection_name, items)

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        if not items:
            return

        for item in items:
            item_id = str(self._item_value(item, "id"))
            record_id = f"{collection_name}::{item_id}"
            text = str(self._item_value(item, "text"))
            vector = self._item_value(item, "vector")
            metadata = self._item_value(item, "metadata")
            if metadata is None:
                metadata = {}
            if not isinstance(metadata, dict):
                metadata = {"value": metadata}

            self._run_query_raw(
                f"UPSERT type::record('{self.table_name}', $record_id) CONTENT "
                "{"
                "item_id: $item_id, "
                "collection_name: $collection_name, "
                "text: $text, "
                "metadata: $metadata, "
                "vector: $vector"
                "};",
                {
                    "record_id": record_id,
                    "item_id": item_id,
                    "collection_name": collection_name,
                    "text": text,
                    "metadata": metadata,
                    "vector": vector,
                },
            )

    def search(
        self,
        collection_name: str,
        vectors: List[List[float | int]],
        filter: Optional[Dict] = None,
        limit: int = 10,
    ) -> Optional[SearchResult]:
        if not vectors:
            return SearchResult(ids=[], documents=[], metadatas=[], distances=[])

        search_limit = NO_LIMIT if limit is None or limit < 0 else int(limit)
        ids: List[List[str]] = []
        documents: List[List[str]] = []
        metadatas: List[List[Any]] = []
        distances: List[List[float]] = []

        metadata_clauses, metadata_params = self._build_metadata_filter_clauses(filter)

        for vector in vectors:
            # Validate vector values early so both index and fallback paths behave consistently.
            self._validate_query_vector(vector)

            rows: List[Dict[str, Any]]
            used_index = False

            if (
                self.vector_index_enabled
                and len(vector) == self.vector_index_dimension
                and search_limit > 0
            ):
                try:
                    rows = self._run_search_indexed(
                        collection_name=collection_name,
                        query_vector=vector,
                        metadata_clauses=metadata_clauses,
                        metadata_params=metadata_params,
                        search_limit=search_limit,
                    )
                    used_index = True

                    # In some SurrealDB setups, indexed path can return empty unexpectedly.
                    # Retry once via fallback metric scan before returning empty results.
                    if len(rows) == 0:
                        fallback_rows = self._run_search_fallback(
                            collection_name=collection_name,
                            query_vector=vector,
                            metadata_clauses=metadata_clauses,
                            metadata_params=metadata_params,
                            search_limit=search_limit,
                        )
                        if len(fallback_rows) > 0:
                            rows = fallback_rows
                            used_index = False
                except Exception as e:
                    log.warning(
                        "SurrealDB indexed vector search failed for collection '%s', falling back to metric scan: %s",
                        collection_name,
                        e,
                    )
                    rows = self._run_search_fallback(
                        collection_name=collection_name,
                        query_vector=vector,
                        metadata_clauses=metadata_clauses,
                        metadata_params=metadata_params,
                        search_limit=search_limit,
                    )
            else:
                rows = self._run_search_fallback(
                    collection_name=collection_name,
                    query_vector=vector,
                    metadata_clauses=metadata_clauses,
                    metadata_params=metadata_params,
                    search_limit=search_limit,
                )

            ids.append([str(row.get("item_id", "")) for row in rows])
            documents.append([str(row.get("text", "")) for row in rows])
            metadatas.append([row.get("metadata", {}) for row in rows])
            if used_index:
                if self.vector_index_distance == "COSINE":
                    scores = [
                        self._distance_to_score(row.get("distance")) for row in rows
                    ]
                else:
                    scores = [
                        self._distance_to_score_inverse(row.get("distance"))
                        for row in rows
                    ]
            else:
                if self.vector_index_distance == "COSINE":
                    scores = [
                        self._similarity_to_score(row.get("similarity")) for row in rows
                    ]
                else:
                    scores = [
                        self._distance_to_score_inverse(row.get("distance"))
                        for row in rows
                    ]
            distances.append(scores)

        return SearchResult(
            ids=ids, documents=documents, metadatas=metadatas, distances=distances
        )

    def query(
        self, collection_name: str, filter: Dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        if not self.has_collection(collection_name):
            return None

        where_clauses = ["collection_name = $collection_name"]
        query_params: Dict[str, Any] = {"collection_name": collection_name}

        metadata_clauses, metadata_params = self._build_metadata_filter_clauses(filter)
        where_clauses.extend(metadata_clauses)
        query_params.update(metadata_params)

        limit_clause = ""
        if limit is not None and limit >= 0:
            limit_clause = f" LIMIT {int(limit)}"

        statement_results = self._run_query_raw(
            f"SELECT item_id, text, metadata FROM {self.table_name} "
            f"WHERE {' AND '.join(where_clauses)}"
            f"{limit_clause};",
            query_params,
        )
        rows = self._result_rows(statement_results)
        return self._rows_to_get_result(rows)

    def get(self, collection_name: str) -> Optional[GetResult]:
        return self.query(collection_name=collection_name, filter={})

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict] = None,
    ) -> None:
        if not self.has_collection(collection_name):
            return

        where_clauses = ["collection_name = $collection_name"]
        query_params: Dict[str, Any] = {"collection_name": collection_name}

        if ids:
            id_clauses = []
            for idx, item_id in enumerate(ids):
                param_name = f"item_id_{idx}"
                query_params[param_name] = str(item_id)
                id_clauses.append(f"item_id = ${param_name}")
            where_clauses.append(f"({' OR '.join(id_clauses)})")

        metadata_clauses, metadata_params = self._build_metadata_filter_clauses(
            filter, param_prefix="delete_meta"
        )
        where_clauses.extend(metadata_clauses)
        query_params.update(metadata_params)

        self._run_query_raw(
            f"DELETE {self.table_name} WHERE {' AND '.join(where_clauses)};",
            query_params,
        )

    def reset(self) -> None:
        self._run_query_raw(f"DELETE {self.table_name};")

    # Connection and query helpers
    def _connect_client(self) -> None:
        client = Surreal(self.url)
        client.signin({"username": self.username, "password": self.password})
        client.use(self.namespace, self.database)
        self.client = client

    def _reconnect_client(self) -> None:
        old_client = self.client
        self._connect_client()
        try:
            if old_client is not None and hasattr(old_client, "close"):
                old_client.close()
        except Exception:
            # Best-effort cleanup of the old connection only.
            pass

    def _run_query_raw(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        def execute_once() -> List[Dict[str, Any]]:
            response = self.client.query_raw(query, params or {})
            if response.get("error") is not None:
                raise RuntimeError(response["error"])

            result = response.get("result", [])
            if not isinstance(result, list):
                raise RuntimeError(f"Unexpected SurrealDB response format: {response}")

            for statement in result:
                status = str(statement.get("status", "")).upper()
                if status and status != "OK":
                    raise RuntimeError(
                        f"SurrealDB query statement failed with status={status}: {statement}"
                    )
            return result

        with self._client_lock:
            try:
                return execute_once()
            except Exception as e:
                if not self._is_transient_error(e):
                    raise
                log.warning(
                    "Transient SurrealDB error while executing query. Reconnecting and retrying once: %s",
                    e,
                )
                self._reconnect_client()
                return execute_once()

    # Schema and search helpers
    def _initialize_schema(self) -> None:
        statements = [
            f"DEFINE TABLE IF NOT EXISTS {self.table_name} SCHEMALESS;",
            f"DEFINE FIELD IF NOT EXISTS item_id ON TABLE {self.table_name} TYPE string;",
            f"DEFINE FIELD IF NOT EXISTS collection_name ON TABLE {self.table_name} TYPE string;",
            f"DEFINE FIELD IF NOT EXISTS text ON TABLE {self.table_name} TYPE string;",
            f"DEFINE FIELD IF NOT EXISTS metadata ON TABLE {self.table_name} TYPE object;",
            f"DEFINE FIELD IF NOT EXISTS vector ON TABLE {self.table_name} TYPE array<float>;",
            f"DEFINE INDEX IF NOT EXISTS idx_{self.table_name}_collection ON TABLE {self.table_name} FIELDS collection_name;",
            f"DEFINE INDEX IF NOT EXISTS idx_{self.table_name}_collection_item ON TABLE {self.table_name} FIELDS collection_name, item_id UNIQUE;",
            f"DEFINE INDEX IF NOT EXISTS idx_{self.table_name}_metadata_hash ON TABLE {self.table_name} FIELDS metadata.hash;",
            f"DEFINE INDEX IF NOT EXISTS idx_{self.table_name}_metadata_file_id ON TABLE {self.table_name} FIELDS metadata.file_id;",
        ]
        if self.vector_index_enabled:
            statements.append(
                f"DEFINE INDEX IF NOT EXISTS idx_{self.table_name}_vector_hnsw ON TABLE {self.table_name} "
                f"FIELDS vector HNSW DIMENSION {self.vector_index_dimension} DIST {self.vector_index_distance} "
                f"EFC {self.vector_index_efc} M {self.vector_index_m};"
            )
        self._run_query_raw("\n".join(statements))

    def _run_search_indexed(
        self,
        collection_name: str,
        query_vector: List[float | int],
        metadata_clauses: List[str],
        metadata_params: Dict[str, Any],
        search_limit: int,
    ) -> List[Dict[str, Any]]:
        vector_literal = self._vector_literal(query_vector)

        where_clauses = [
            "collection_name = $collection_name",
            f"vector <|{search_limit},{self.vector_index_distance}|> {vector_literal}",
        ]
        where_clauses.extend(metadata_clauses)

        statement_results = self._run_query_raw(
            f"SELECT item_id, text, metadata, vector::distance::knn() AS distance "
            f"FROM {self.table_name} "
            f"WHERE {' AND '.join(where_clauses)} "
            f"ORDER BY distance ASC "
            f"LIMIT {search_limit};",
            {"collection_name": collection_name, **metadata_params},
        )
        return self._result_rows(statement_results)

    def _run_search_fallback(
        self,
        collection_name: str,
        query_vector: List[float | int],
        metadata_clauses: List[str],
        metadata_params: Dict[str, Any],
        search_limit: int,
    ) -> List[Dict[str, Any]]:
        where_clauses = ["collection_name = $collection_name"]
        where_clauses.extend(metadata_clauses)

        if self.vector_index_distance == "EUCLIDEAN":
            metric_expr = "vector::distance::euclidean(vector, $query_vector)"
            order = "ASC"
            alias = "distance"
        elif self.vector_index_distance == "MANHATTAN":
            metric_expr = "vector::distance::manhattan(vector, $query_vector)"
            order = "ASC"
            alias = "distance"
        else:
            metric_expr = "vector::similarity::cosine(vector, $query_vector)"
            order = "DESC"
            alias = "similarity"

        statement_results = self._run_query_raw(
            f"SELECT item_id, text, metadata, {metric_expr} AS {alias} "
            f"FROM {self.table_name} "
            f"WHERE {' AND '.join(where_clauses)} "
            f"ORDER BY {alias} {order} "
            f"LIMIT {search_limit};",
            {
                "collection_name": collection_name,
                "query_vector": query_vector,
                **metadata_params,
            },
        )
        return self._result_rows(statement_results)

    def _build_metadata_filter_clauses(
        self, filter: Optional[Dict[str, Any]], param_prefix: str = "meta"
    ) -> Tuple[List[str], Dict[str, Any]]:
        clauses: List[str] = []
        params: Dict[str, Any] = {}

        if not filter:
            return clauses, params

        for idx, (key, value) in enumerate(filter.items()):
            safe_key = self._validate_metadata_field_name(key)

            if isinstance(value, dict) and "$in" in value:
                in_values = value["$in"]
                if not isinstance(in_values, list):
                    raise ValueError(f"Expected list for '$in' filter on '{key}'.")
                if not in_values:
                    clauses.append("false")
                    continue

                in_clauses = []
                for value_idx, in_value in enumerate(in_values):
                    param_name = f"{param_prefix}_{idx}_{value_idx}"
                    params[param_name] = in_value
                    in_clauses.append(f"metadata.{safe_key} = ${param_name}")
                clauses.append(f"({' OR '.join(in_clauses)})")
            else:
                param_name = f"{param_prefix}_{idx}"
                params[param_name] = value
                clauses.append(f"metadata.{safe_key} = ${param_name}")

        return clauses, params

    # Conversion and validation helpers
    @staticmethod
    def _rows_to_get_result(rows: List[Dict[str, Any]]) -> Optional[GetResult]:
        if not rows:
            return None
        return GetResult(
            ids=[[str(row.get("item_id", "")) for row in rows]],
            documents=[[str(row.get("text", "")) for row in rows]],
            metadatas=[[row.get("metadata", {}) for row in rows]],
        )

    @staticmethod
    def _result_rows(statement_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not statement_results:
            return []
        statement = statement_results[0]
        rows = statement.get("result", [])
        return rows if isinstance(rows, list) else []

    @staticmethod
    def _item_value(item: VectorItem | Dict[str, Any], field: str) -> Any:
        if isinstance(item, dict):
            return item[field]
        return getattr(item, field)

    @staticmethod
    def _sanitize_table_name(table_name: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9_]", "_", table_name)
        if not sanitized or not TABLE_NAME_PATTERN.match(sanitized):
            sanitized = f"open_webui_{sanitized}" if sanitized else "open_webui_chunks"
        return sanitized

    @staticmethod
    def _validate_metadata_field_name(field_name: str) -> str:
        if not METADATA_FIELD_PATTERN.match(field_name):
            raise ValueError(
                f"Invalid metadata filter field '{field_name}'. Use alphanumeric/underscore only."
            )
        return field_name

    @staticmethod
    def _validate_query_vector(vector: List[float | int]) -> List[str]:
        if not vector:
            raise ValueError("Query vector must not be empty.")

        sanitized: List[str] = []
        for value in vector:
            v = float(value)
            if not math.isfinite(v):
                raise ValueError("Query vector contains non-finite numeric values.")
            sanitized.append(format(v, ".17g"))
        return sanitized

    @staticmethod
    def _vector_literal(vector: List[float | int]) -> str:
        sanitized = SurrealDBClient._validate_query_vector(vector)
        return "[" + ",".join(sanitized) + "]"

    @staticmethod
    def _is_transient_error(error: Exception) -> bool:
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return True

        message = str(error).lower()
        return any(hint in message for hint in TRANSIENT_ERROR_HINTS)

    @staticmethod
    def _distance_to_score(distance: Any) -> float:
        try:
            d = float(distance)
        except (TypeError, ValueError):
            return 0.0
        score = (2.0 - d) / 2.0
        return max(0.0, min(1.0, score))

    @staticmethod
    def _distance_to_score_inverse(distance: Any) -> float:
        try:
            d = float(distance)
        except (TypeError, ValueError):
            return 0.0
        if d < 0:
            d = 0.0
        return 1.0 / (1.0 + d)

    @staticmethod
    def _similarity_to_score(similarity: Any) -> float:
        try:
            s = float(similarity)
        except (TypeError, ValueError):
            return 0.0
        # Cosine similarity is typically in [-1, 1], normalize to [0, 1].
        return max(0.0, min(1.0, (s + 1.0) / 2.0))
