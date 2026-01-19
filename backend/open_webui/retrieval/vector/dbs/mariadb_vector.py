from __future__ import annotations

import array
import json
import logging
import math
import re
import sys
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool, QueuePool

from open_webui.config import (
    MARIADB_VECTOR_DB_URL,
    MARIADB_VECTOR_DISTANCE_STRATEGY,
    MARIADB_VECTOR_INDEX_M,
    MARIADB_VECTOR_INITIALIZE_MAX_VECTOR_LENGTH,
    MARIADB_VECTOR_POOL_SIZE,
    MARIADB_VECTOR_POOL_MAX_OVERFLOW,
    MARIADB_VECTOR_POOL_TIMEOUT,
    MARIADB_VECTOR_POOL_RECYCLE,
)
from open_webui.retrieval.vector.main import GetResult, SearchResult, VectorDBBase, VectorItem
from open_webui.retrieval.vector.utils import process_metadata

log = logging.getLogger(__name__)

VECTOR_LENGTH = int(MARIADB_VECTOR_INITIALIZE_MAX_VECTOR_LENGTH)


def _embedding_to_f32_bytes(vec: List[float]) -> bytes:
    """
    Convert a Python float vector into the binary payload expected by MariaDB VECTOR.

    MariaDB Vector expects the vector argument to be bound as a little-endian float32
    byte sequence. We use array('f') to avoid a numpy dependency and byteswap on
    big-endian platforms for portability.
    """
    a = array.array("f", [float(x) for x in vec])  # float32
    if sys.byteorder != "little":
        a.byteswap()
    return a.tobytes()


def _safe_json(v: Any) -> Dict[str, Any]:
    """
    Normalize a potentially JSON-like value into a Python dict.

    Accepts:
      - dict: returned as-is
      - str / bytes: parsed as JSON if possible
      - None / other types: returns {}
    """
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, (bytes, bytearray)):
        try:
            v = v.decode("utf-8")
        except Exception:
            return {}
    if isinstance(v, str):
        try:
            j = json.loads(v)
            return j if isinstance(j, dict) else {}
        except Exception:
            return {}
    return {}


class MariaDBVectorClient(VectorDBBase):
    """
    MariaDB + MariaDB Vector backend using DBAPI cursor parameter binding.

    IMPORTANT:
      - Intended for: mariadb+mariadbconnector://... (official MariaDB driver).
      - Uses qmark ("?") params and binds vectors as float32 bytes.
      - Uses binary binding for BOTH inserts/updates and distance computations.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        vector_length: int = VECTOR_LENGTH,
        distance_strategy: str = MARIADB_VECTOR_DISTANCE_STRATEGY,
        index_m: int = MARIADB_VECTOR_INDEX_M,
    ) -> None:
        """
        Initialize a MariaDB Vector-backed VectorDBBase implementation.

        Validates URL scheme/driver requirements, ensures schema exists, and guards
        against dimension mismatch with an existing VECTOR(n) column.
        """
        self.db_url = (db_url or MARIADB_VECTOR_DB_URL).strip()
        self.vector_length = int(vector_length)
        self.distance_strategy = (distance_strategy or "cosine").strip().lower()
        self.index_m = int(index_m)

        if self.distance_strategy not in {"cosine", "euclidean"}:
            raise ValueError("distance_strategy must be 'cosine' or 'euclidean'")

        if not self.db_url.lower().startswith("mariadb+mariadbconnector://"):
            raise ValueError(
                "MariaDBVectorClient requires mariadb+mariadbconnector:// (official MariaDB driver) "
                "to ensure qmark paramstyle and correct VECTOR binding."
            )

        if isinstance(MARIADB_VECTOR_POOL_SIZE, int):
            if MARIADB_VECTOR_POOL_SIZE > 0:
                self.engine = create_engine(
                    self.db_url,
                    pool_size=MARIADB_VECTOR_POOL_SIZE,
                    max_overflow=MARIADB_VECTOR_POOL_MAX_OVERFLOW,
                    pool_timeout=MARIADB_VECTOR_POOL_TIMEOUT,
                    pool_recycle=MARIADB_VECTOR_POOL_RECYCLE,
                    pool_pre_ping=True,
                    poolclass=QueuePool,
                )
            else:
                self.engine = create_engine(
                    self.db_url, pool_pre_ping=True, poolclass=NullPool
                )
        else:
            self.engine = create_engine(self.db_url, pool_pre_ping=True)
        self._init_schema()
        self._check_vector_length()

    @contextmanager
    def _connect(self):
        """
        Yield a context-managed DBAPI connection (SQLAlchemy raw_connection()).

        Callers can use:
          with self._connect() as conn:
            with conn.cursor() as cur:
              ...
        """
        conn = self.engine.raw_connection()
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _init_schema(self) -> None:
        """
        Create the backing table and vector index if they do not exist.

        Uses a PK definition compatible with MariaDB Vector's VECTOR INDEX key-size constraints.
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                try:
                    dist = self.distance_strategy
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS document_chunk (
                            -- MariaDB Vector requires the table PRIMARY KEY used with a VECTOR INDEX to be <= 256 bytes.
                            -- VARCHAR has internal length/metadata overhead, so VARCHAR(255) can exceed the 256-byte limit.
                            -- We use VARCHAR(254) to stay safely under the limit, and force ASCII (1 byte/char) so the byte
                            -- size is predictable (avoid utf8mb4 where a "255 char" key could be up to 1020 bytes).
                            -- ascii_bin gives bytewise, case-sensitive comparisons for stable ID matching.
                            id VARCHAR(254) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
                            embedding VECTOR({self.vector_length}) NOT NULL,
                            collection_name VARCHAR(255) NOT NULL,
                            text LONGTEXT NULL,
                            vmetadata JSON NULL,
                            VECTOR INDEX (embedding) M={self.index_m} DISTANCE={dist},
                            INDEX idx_document_chunk_collection_name (collection_name)
                        ) ENGINE=InnoDB;
                        """
                    )
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    log.exception(f"Error during database initialization: {e}")
                    raise

    def _check_vector_length(self) -> None:
        """
        Validate that the existing VECTOR column dimension matches this client's configured dimension.

        Dimension guard: if table already exists with
        a different VECTOR(n), refuse to silently mismatch.
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SHOW CREATE TABLE document_chunk")
                row = cur.fetchone()
                if not row or len(row) < 2:
                    return
                ddl = row[1]
                m = re.search(r"vector\\((\\d+)\\)", ddl, flags=re.IGNORECASE)
                if not m:
                    return
                existing = int(m.group(1))
                if existing != int(self.vector_length):
                    raise Exception(
                        f"VECTOR_LENGTH {self.vector_length} does not match existing vector column dimension {existing}. "
                        "Cannot change vector size after initialization without migrating the data."
                    )

    def adjust_vector_length(self, vector: List[float]) -> List[float]:
        """
        Pad or truncate a vector to match `self.vector_length`.
        """
        n = len(vector)
        if n < self.vector_length:
            return vector + [0.0] * (self.vector_length - n)
        if n > self.vector_length:
            return vector[: self.vector_length]
        return vector

    def _dist_fn(self) -> str:
        """
        Return the MariaDB Vector distance function name for the configured strategy.
        """
        return "vec_distance_cosine" if self.distance_strategy == "cosine" else "vec_distance_euclidean"

    def _score_from_dist(self, dist: float) -> float:
        """
        Convert a DB distance value into a normalized score in (0, 1].

        - cosine: score ~= 1 - cosine_distance, clamped to [0, 1]
        - euclidean: score = 1 / (1 + dist)
        """
        if self.distance_strategy == "cosine":
            score = 1.0 - dist
            if score < 0.0:
                score = 0.0
            if score > 1.0:
                score = 1.0
            return score
        return 1.0 / (1.0 + max(0.0, dist))

    def _build_filter_sql_qmark(self, expr: Any) -> Tuple[str, List[Any]]:
        """
        Build a WHERE-clause fragment and qmark params from a minimal Mongo-like filter.

        Supported forms:
          - {"field": "v"}
          - {"field": {"$in": ["a","b"]}}
          - {"$and": [ ... ]}
          - {"$or":  [ ... ]}
        """
        if not expr or not isinstance(expr, dict):
            return "", []

        if "$and" in expr:
            parts: List[str] = []
            params: List[Any] = []
            for e in expr.get("$and") or []:
                s, p = self._build_filter_sql_qmark(e)
                if s:
                    parts.append(s)
                    params.extend(p)
            return ("(" + " AND ".join(parts) + ")") if parts else "", params

        if "$or" in expr:
            parts: List[str] = []
            params: List[Any] = []
            for e in expr.get("$or") or []:
                s, p = self._build_filter_sql_qmark(e)
                if s:
                    parts.append(s)
                    params.extend(p)
            return ("(" + " OR ".join(parts) + ")") if parts else "", params

        clauses: List[str] = []
        params: List[Any] = []
        for key, value in expr.items():
            if key.startswith("$"):
                continue
            json_expr = f"JSON_UNQUOTE(JSON_EXTRACT(vmetadata, '$.{key}'))"
            if isinstance(value, dict) and "$in" in value:
                vals = [str(v) for v in (value.get("$in") or [])]
                if not vals:
                    clauses.append("0=1")
                    continue
                ors = []
                for v in vals:
                    ors.append(f"{json_expr} = ?")
                    params.append(v)
                clauses.append("(" + " OR ".join(ors) + ")")
            else:
                clauses.append(f"{json_expr} = ?")
                params.append(str(value))
        return ("(" + " AND ".join(clauses) + ")") if clauses else "", params

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        """
        Insert items into the given collection (best-effort, ignores duplicates).

        Uses executemany() with binary VECTOR binding for high-throughput ingestion.
        """
        if not items:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                try:
                    sql = """
                        INSERT IGNORE INTO document_chunk
                          (id, embedding, collection_name, text, vmetadata)
                        VALUES
                          (?, ?, ?, ?, ?)
                    """
                    params: List[Tuple[Any, ...]] = []
                    for item in items:
                        v = self.adjust_vector_length(item["vector"])
                        emb = _embedding_to_f32_bytes(v)
                        meta = process_metadata(item.get("metadata") or {})
                        params.append(
                            (
                                item["id"],
                                emb,
                                collection_name,
                                item.get("text"),
                                json.dumps(meta),
                            )
                        )
                    cur.executemany(sql, params)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    log.exception(f"Error during insert: {e}")
                    raise

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        """
        Insert or update items in the given collection by primary key.

        Uses executemany() and updates embedding/text/metadata on conflicts.
        """
        if not items:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                try:
                    sql = """
                        INSERT INTO document_chunk
                          (id, embedding, collection_name, text, vmetadata)
                        VALUES
                          (?, ?, ?, ?, ?)
                        ON DUPLICATE KEY UPDATE
                          embedding = VALUES(embedding),
                          collection_name = VALUES(collection_name),
                          text = VALUES(text),
                          vmetadata = VALUES(vmetadata)
                    """
                    params: List[Tuple[Any, ...]] = []
                    for item in items:
                        v = self.adjust_vector_length(item["vector"])
                        emb = _embedding_to_f32_bytes(v)
                        meta = process_metadata(item.get("metadata") or {})
                        params.append(
                            (
                                item["id"],
                                emb,
                                collection_name,
                                item.get("text"),
                                json.dumps(meta),
                            )
                        )
                    cur.executemany(sql, params)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    log.exception(f"Error during upsert: {e}")
                    raise

    def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> Optional[SearchResult]:
        """
        Perform a vector similarity search.

        Args:
          collection_name: Logical collection partition key.
          vectors: One or more query vectors.
          filter: Optional metadata filter (Mongo-like subset).
          limit: Top-k per query vector.

        Returns a SearchResult where distances are normalized scores (higher is better).
        """
        if not vectors:
            return None

        dist_fn = self._dist_fn()
        ids: List[List[str]] = [[] for _ in vectors]
        distances: List[List[float]] = [[] for _ in vectors]
        documents: List[List[str]] = [[] for _ in vectors]
        metadatas: List[List[Any]] = [[] for _ in vectors]

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    fsql, fparams = self._build_filter_sql_qmark(filter or {})
                    where = "collection_name = ?"
                    base_params: List[Any] = [collection_name]
                    if fsql:
                        where = where + " AND " + fsql
                        base_params.extend(fparams)

                    sql = f"""
                        SELECT
                          id,
                          text,
                          vmetadata,
                          {dist_fn}(embedding, ?) AS dist
                        FROM document_chunk
                        WHERE {where}
                        ORDER BY dist ASC
                        LIMIT ?
                    """

                    for q_idx, q in enumerate(vectors):
                        qv = self.adjust_vector_length(q)
                        qbin = _embedding_to_f32_bytes(qv)
                        params = [qbin] + list(base_params) + [int(limit)]
                        cur.execute(sql, params)
                        rows = cur.fetchall()

                        for r in rows:
                            rid, rtext, rmeta, rdist = r[0], r[1], r[2], r[3]
                            ids[q_idx].append(str(rid))
                            try:
                                dist = float(rdist) if rdist is not None else 1.0
                            except Exception:
                                dist = 1.0
                            if math.isnan(dist) or math.isinf(dist):
                                dist = 1.0
                            distances[q_idx].append(self._score_from_dist(dist))
                            documents[q_idx].append(rtext)
                            metadatas[q_idx].append(_safe_json(rmeta))

                    return SearchResult(ids=ids, distances=distances, documents=documents, metadatas=metadatas)
        except Exception as e:
            log.exception(f"[MARIADB_VECTOR] search() failed: {e}")
            return None

    def query(self, collection_name: str, filter: Dict[str, Any], limit: Optional[int] = None) -> Optional[GetResult]:
        """
        Retrieve documents by metadata filter (non-vector query).
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                fsql, fparams = self._build_filter_sql_qmark(filter or {})
                where = "collection_name = ?"
                params: List[Any] = [collection_name]
                if fsql:
                    where = where + " AND " + fsql
                    params.extend(fparams)
                sql = f"SELECT id, text, vmetadata FROM document_chunk WHERE {where}"
                if limit is not None:
                    sql += " LIMIT ?"
                    params.append(int(limit))
                cur.execute(sql, params)
                rows = cur.fetchall()
                if not rows:
                    return None
                ids = [[str(r[0]) for r in rows]]
                documents = [[r[1] for r in rows]]
                metadatas = [[_safe_json(r[2]) for r in rows]]
                return GetResult(ids=ids, documents=documents, metadatas=metadatas)

    def get(self, collection_name: str, limit: Optional[int] = None) -> Optional[GetResult]:
        """
        Retrieve documents in a collection without filtering (optionally limited).
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                sql = "SELECT id, text, vmetadata FROM document_chunk WHERE collection_name = ?"
                params: List[Any] = [collection_name]
                if limit is not None:
                    sql += " LIMIT ?"
                    params.append(int(limit))
                cur.execute(sql, params)
                rows = cur.fetchall()
                if not rows:
                    return None
                ids = [[str(r[0]) for r in rows]]
                documents = [[r[1] for r in rows]]
                metadatas = [[_safe_json(r[2]) for r in rows]]
                return GetResult(ids=ids, documents=documents, metadatas=metadatas)

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Delete rows from a collection by id list and/or metadata filter.

        If both are provided, they are combined with AND semantics.
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                try:
                    where = ["collection_name = ?"]
                    params: List[Any] = [collection_name]

                    if ids:
                        ph = ", ".join(["?"] * len(ids))
                        where.append(f"id IN ({ph})")
                        params.extend(ids)

                    if filter:
                        fsql, fparams = self._build_filter_sql_qmark(filter)
                        if fsql:
                            where.append(fsql)
                            params.extend(fparams)

                    sql = "DELETE FROM document_chunk WHERE " + " AND ".join(where)
                    cur.execute(sql, params)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    log.exception(f"Error during delete: {e}")
                    raise

    def reset(self) -> None:
        """
        Truncate the vector table (drops all collections).
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("TRUNCATE TABLE document_chunk")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    log.exception(f"Error during reset: {e}")
                    raise

    def has_collection(self, collection_name: str) -> bool:
        """
        Return True if the collection contains at least one row, else False.
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM document_chunk WHERE collection_name = ? LIMIT 1", (collection_name,))
                    return cur.fetchone() is not None
        except Exception:
            return False

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete all rows in a collection.
        """
        self.delete(collection_name)

    def close(self) -> None:
        """
        Dispose the underlying SQLAlchemy engine.
        """
        try:
            self.engine.dispose()
        except Exception as e:
            log.exception(f"Error during dispose the underlying SQLAlchemy engine: {e}")
