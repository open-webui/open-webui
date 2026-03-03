from typing import Optional, List, Dict, Any
import logging
import re
import json
from sqlalchemy import (
    func,
    literal,
    cast,
    column,
    create_engine,
    Column,
    Integer,
    MetaData,
    LargeBinary,
    select,
    text,
    Text,
    Table,
    values,
)
from sqlalchemy.sql import true
from sqlalchemy.pool import NullPool, QueuePool

from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB, array
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.exc import NoSuchTableError

from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.dialects import registry


class OpenGaussDialect(PGDialect_psycopg2):
    name = "opengauss"

    def _get_server_version_info(self, connection):
        try:
            version = connection.exec_driver_sql("SELECT version()").scalar()
            if not version:
                return (9, 0, 0)

            match = re.search(
                r"openGauss\s+(\d+)\.(\d+)\.(\d+)(?:-\w+)?", version, re.IGNORECASE
            )
            if match:
                return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

            return super()._get_server_version_info(connection)
        except Exception:
            return (9, 0, 0)


# Register dialect
registry.register("opengauss", __name__, "OpenGaussDialect")

from open_webui.retrieval.vector.utils import process_metadata
from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)
from open_webui.config import (
    OPENGAUSS_DB_URL,
    OPENGAUSS_INITIALIZE_MAX_VECTOR_LENGTH,
    OPENGAUSS_POOL_SIZE,
    OPENGAUSS_POOL_MAX_OVERFLOW,
    OPENGAUSS_POOL_TIMEOUT,
    OPENGAUSS_POOL_RECYCLE,
)

from open_webui.env import SRC_LOG_LEVELS

VECTOR_LENGTH = OPENGAUSS_INITIALIZE_MAX_VECTOR_LENGTH
Base = declarative_base()

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class DocumentChunk(Base):
    __tablename__ = "document_chunk"

    id = Column(Text, primary_key=True)
    vector = Column(Vector(dim=VECTOR_LENGTH), nullable=True)
    collection_name = Column(Text, nullable=False)
    text = Column(Text, nullable=True)
    vmetadata = Column(MutableDict.as_mutable(JSONB), nullable=True)


class OpenGaussClient(VectorDBBase):
    def __init__(self) -> None:
        if not OPENGAUSS_DB_URL:
            from open_webui.internal.db import ScopedSession

            self.session = ScopedSession
        else:
            engine_kwargs = {"pool_pre_ping": True, "dialect": OpenGaussDialect()}

            if isinstance(OPENGAUSS_POOL_SIZE, int) and OPENGAUSS_POOL_SIZE > 0:
                engine_kwargs.update(
                    {
                        "pool_size": OPENGAUSS_POOL_SIZE,
                        "max_overflow": OPENGAUSS_POOL_MAX_OVERFLOW,
                        "pool_timeout": OPENGAUSS_POOL_TIMEOUT,
                        "pool_recycle": OPENGAUSS_POOL_RECYCLE,
                        "poolclass": QueuePool,
                    }
                )
            else:
                engine_kwargs["poolclass"] = NullPool

            engine = create_engine(OPENGAUSS_DB_URL, **engine_kwargs)

            SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
            )
            self.session = scoped_session(SessionLocal)

        try:
            connection = self.session.connection()
            Base.metadata.create_all(bind=connection)

            self.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunk_vector "
                    "ON document_chunk USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);"
                )
            )
            self.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunk_collection_name "
                    "ON document_chunk (collection_name);"
                )
            )
            self.session.commit()
            log.info("OpenGauss vector database initialization completed.")
        except Exception as e:
            self.session.rollback()
            log.exception(f"OpenGauss Initialization failed.: {e}")
            raise

    def check_vector_length(self) -> None:
        metadata = MetaData()
        try:
            document_chunk_table = Table(
                "document_chunk", metadata, autoload_with=self.session.bind
            )
        except NoSuchTableError:
            return

        if "vector" in document_chunk_table.columns:
            vector_column = document_chunk_table.columns["vector"]
            vector_type = vector_column.type
            if isinstance(vector_type, Vector):
                db_vector_length = vector_type.dim
                if db_vector_length != VECTOR_LENGTH:
                    raise Exception(
                        f"Vector dimension mismatch: configured {VECTOR_LENGTH} vs. {db_vector_length} in the database."
                    )
            else:
                raise Exception("The 'vector' column type is not Vector.")
        else:
            raise Exception(
                "The 'vector' column does not exist in the 'document_chunk' table."
            )

    def adjust_vector_length(self, vector: List[float]) -> List[float]:
        current_length = len(vector)
        if current_length < VECTOR_LENGTH:
            vector += [0.0] * (VECTOR_LENGTH - current_length)
        elif current_length > VECTOR_LENGTH:
            vector = vector[:VECTOR_LENGTH]
        return vector

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        try:
            new_items = []
            for item in items:
                vector = self.adjust_vector_length(item["vector"])
                new_chunk = DocumentChunk(
                    id=item["id"],
                    vector=vector,
                    collection_name=collection_name,
                    text=item["text"],
                    vmetadata=process_metadata(item["metadata"]),
                )
                new_items.append(new_chunk)
            self.session.bulk_save_objects(new_items)
            self.session.commit()
            log.info(
                f"Inserting {len(new_items)} items into collection '{collection_name}'."
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Failed to insert data: {e}")
            raise

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        try:
            for item in items:
                vector = self.adjust_vector_length(item["vector"])
                existing = (
                    self.session.query(DocumentChunk)
                    .filter(DocumentChunk.id == item["id"])
                    .first()
                )
                if existing:
                    existing.vector = vector
                    existing.text = item["text"]
                    existing.vmetadata = process_metadata(item["metadata"])
                    existing.collection_name = collection_name
                else:
                    new_chunk = DocumentChunk(
                        id=item["id"],
                        vector=vector,
                        collection_name=collection_name,
                        text=item["text"],
                        vmetadata=process_metadata(item["metadata"]),
                    )
                    self.session.add(new_chunk)
            self.session.commit()
            log.info(
                f"Inserting/updating {len(items)} items in collection '{collection_name}'."
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Failed to insert or update data.: {e}")
            raise

    def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> Optional[SearchResult]:
        try:
            if not vectors:
                return None

            vectors = [self.adjust_vector_length(vector) for vector in vectors]
            num_queries = len(vectors)

            def vector_expr(vector):
                return cast(array(vector), Vector(VECTOR_LENGTH))

            qid_col = column("qid", Integer)
            q_vector_col = column("q_vector", Vector(VECTOR_LENGTH))
            query_vectors = (
                values(qid_col, q_vector_col)
                .data(
                    [(idx, vector_expr(vector)) for idx, vector in enumerate(vectors)]
                )
                .alias("query_vectors")
            )

            result_fields = [
                DocumentChunk.id,
                DocumentChunk.text,
                DocumentChunk.vmetadata,
                (DocumentChunk.vector.cosine_distance(query_vectors.c.q_vector)).label(
                    "distance"
                ),
            ]

            subq = (
                select(*result_fields)
                .where(DocumentChunk.collection_name == collection_name)
                .order_by(
                    DocumentChunk.vector.cosine_distance(query_vectors.c.q_vector)
                )
            )
            if limit is not None:
                subq = subq.limit(limit)
            subq = subq.lateral("result")

            stmt = (
                select(
                    query_vectors.c.qid,
                    subq.c.id,
                    subq.c.text,
                    subq.c.vmetadata,
                    subq.c.distance,
                )
                .select_from(query_vectors)
                .join(subq, true())
                .order_by(query_vectors.c.qid, subq.c.distance)
            )

            result_proxy = self.session.execute(stmt)
            results = result_proxy.all()

            ids = [[] for _ in range(num_queries)]
            distances = [[] for _ in range(num_queries)]
            documents = [[] for _ in range(num_queries)]
            metadatas = [[] for _ in range(num_queries)]

            for row in results:
                qid = int(row.qid)
                ids[qid].append(row.id)
                distances[qid].append((2.0 - row.distance) / 2.0)
                documents[qid].append(row.text)
                metadatas[qid].append(row.vmetadata)

            self.session.rollback()
            return SearchResult(
                ids=ids, distances=distances, documents=documents, metadatas=metadatas
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Vector search failed: {e}")
            return None

    def query(
        self, collection_name: str, filter: Dict[str, Any], limit: Optional[int] = None
    ) -> Optional[GetResult]:
        try:
            query = self.session.query(DocumentChunk).filter(
                DocumentChunk.collection_name == collection_name
            )

            for key, value in filter.items():
                query = query.filter(DocumentChunk.vmetadata[key].astext == str(value))

            if limit is not None:
                query = query.limit(limit)

            results = query.all()

            if not results:
                return None

            ids = [[result.id for result in results]]
            documents = [[result.text for result in results]]
            metadatas = [[result.vmetadata for result in results]]

            self.session.rollback()
            return GetResult(ids=ids, documents=documents, metadatas=metadatas)
        except Exception as e:
            self.session.rollback()
            log.exception(f"Conditional query failed: {e}")
            return None

    def get(
        self, collection_name: str, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        try:
            query = self.session.query(DocumentChunk).filter(
                DocumentChunk.collection_name == collection_name
            )
            if limit is not None:
                query = query.limit(limit)

            results = query.all()

            if not results:
                return None

            ids = [[result.id for result in results]]
            documents = [[result.text for result in results]]
            metadatas = [[result.vmetadata for result in results]]

            self.session.rollback()
            return GetResult(ids=ids, documents=documents, metadatas=metadatas)
        except Exception as e:
            self.session.rollback()
            log.exception(f"Failed to retrieve data: {e}")
            return None

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            query = self.session.query(DocumentChunk).filter(
                DocumentChunk.collection_name == collection_name
            )
            if ids:
                query = query.filter(DocumentChunk.id.in_(ids))
            if filter:
                for key, value in filter.items():
                    query = query.filter(
                        DocumentChunk.vmetadata[key].astext == str(value)
                    )
            deleted = query.delete(synchronize_session=False)
            self.session.commit()
            log.info(f"Deleted {deleted} items from collection '{collection_name}'")
        except Exception as e:
            self.session.rollback()
            log.exception(f"Failed to delete data: {e}")
            raise

    def reset(self) -> None:
        try:
            deleted = self.session.query(DocumentChunk).delete()
            self.session.commit()
            log.info(f"Reset completed. Deleted {deleted} items")
        except Exception as e:
            self.session.rollback()
            log.exception(f"Reset failed: {e}")
            raise

    def close(self) -> None:
        pass

    def has_collection(self, collection_name: str) -> bool:
        try:
            exists = (
                self.session.query(DocumentChunk)
                .filter(DocumentChunk.collection_name == collection_name)
                .first()
                is not None
            )
            self.session.rollback()
            return exists
        except Exception as e:
            self.session.rollback()
            log.exception(f"Failed to check collection existence: {e}")
            return False

    def delete_collection(self, collection_name: str) -> None:
        self.delete(collection_name)
        log.info(f"Collection '{collection_name}' has been deleted")
