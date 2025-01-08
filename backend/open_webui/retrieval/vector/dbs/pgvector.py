from typing import Optional, List, Dict, Any
from sqlalchemy import (
    cast,
    column,
    create_engine,
    Column,
    Integer,
    MetaData,
    select,
    text,
    Text,
    Table,
    values,
)
from sqlalchemy.sql import true
from sqlalchemy.pool import NullPool

from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB, array
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.exc import NoSuchTableError

from open_webui.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import PGVECTOR_DB_URL, PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH

VECTOR_LENGTH = PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH
Base = declarative_base()


class DocumentChunk(Base):
    __tablename__ = "document_chunk"

    id = Column(Text, primary_key=True)
    vector = Column(Vector(dim=VECTOR_LENGTH), nullable=True)
    collection_name = Column(Text, nullable=False)
    text = Column(Text, nullable=True)
    vmetadata = Column(MutableDict.as_mutable(JSONB), nullable=True)


class PgvectorClient:
    def __init__(self) -> None:

        # if no pgvector uri, use the existing database connection
        if not PGVECTOR_DB_URL:
            from open_webui.internal.db import Session

            self.session = Session
        else:
            engine = create_engine(
                PGVECTOR_DB_URL, pool_pre_ping=True, poolclass=NullPool
            )
            SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
            )
            self.session = scoped_session(SessionLocal)

        try:
            # Ensure the pgvector extension is available
            self.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

            # Check vector length consistency
            self.check_vector_length()

            # Create the tables if they do not exist
            # Base.metadata.create_all requires a bind (engine or connection)
            # Get the connection from the session
            connection = self.session.connection()
            Base.metadata.create_all(bind=connection)

            # Create an index on the vector column if it doesn't exist
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
            print("Initialization complete.")
        except Exception as e:
            self.session.rollback()
            print(f"Error during initialization: {e}")
            raise

    def check_vector_length(self) -> None:
        """
        Check if the VECTOR_LENGTH matches the existing vector column dimension in the database.
        Raises an exception if there is a mismatch.
        """
        metadata = MetaData()
        try:
            # Attempt to reflect the 'document_chunk' table
            document_chunk_table = Table(
                "document_chunk", metadata, autoload_with=self.session.bind
            )
        except NoSuchTableError:
            # Table does not exist; no action needed
            return

        # Proceed to check the vector column
        if "vector" in document_chunk_table.columns:
            vector_column = document_chunk_table.columns["vector"]
            vector_type = vector_column.type
            if isinstance(vector_type, Vector):
                db_vector_length = vector_type.dim
                if db_vector_length != VECTOR_LENGTH:
                    raise Exception(
                        f"VECTOR_LENGTH {VECTOR_LENGTH} does not match existing vector column dimension {db_vector_length}. "
                        "Cannot change vector size after initialization without migrating the data."
                    )
            else:
                raise Exception(
                    "The 'vector' column exists but is not of type 'Vector'."
                )
        else:
            raise Exception(
                "The 'vector' column does not exist in the 'document_chunk' table."
            )

    def adjust_vector_length(self, vector: List[float]) -> List[float]:
        # Adjust vector to have length VECTOR_LENGTH
        current_length = len(vector)
        if current_length < VECTOR_LENGTH:
            # Pad the vector with zeros
            vector += [0.0] * (VECTOR_LENGTH - current_length)
        elif current_length > VECTOR_LENGTH:
            raise Exception(
                f"Vector length {current_length} not supported. Max length must be <= {VECTOR_LENGTH}"
            )
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
                    vmetadata=item["metadata"],
                )
                new_items.append(new_chunk)
            self.session.bulk_save_objects(new_items)
            self.session.commit()
            print(
                f"Inserted {len(new_items)} items into collection '{collection_name}'."
            )
        except Exception as e:
            self.session.rollback()
            print(f"Error during insert: {e}")
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
                    existing.vmetadata = item["metadata"]
                    existing.collection_name = (
                        collection_name  # Update collection_name if necessary
                    )
                else:
                    new_chunk = DocumentChunk(
                        id=item["id"],
                        vector=vector,
                        collection_name=collection_name,
                        text=item["text"],
                        vmetadata=item["metadata"],
                    )
                    self.session.add(new_chunk)
            self.session.commit()
            print(f"Upserted {len(items)} items into collection '{collection_name}'.")
        except Exception as e:
            self.session.rollback()
            print(f"Error during upsert: {e}")
            raise

    def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        limit: Optional[int] = None,
    ) -> Optional[SearchResult]:
        try:
            if not vectors:
                return None

            # Adjust query vectors to VECTOR_LENGTH
            vectors = [self.adjust_vector_length(vector) for vector in vectors]
            num_queries = len(vectors)

            def vector_expr(vector):
                return cast(array(vector), Vector(VECTOR_LENGTH))

            # Create the values for query vectors
            qid_col = column("qid", Integer)
            q_vector_col = column("q_vector", Vector(VECTOR_LENGTH))
            query_vectors = (
                values(qid_col, q_vector_col)
                .data(
                    [(idx, vector_expr(vector)) for idx, vector in enumerate(vectors)]
                )
                .alias("query_vectors")
            )

            # Build the lateral subquery for each query vector
            subq = (
                select(
                    DocumentChunk.id,
                    DocumentChunk.text,
                    DocumentChunk.vmetadata,
                    (
                        DocumentChunk.vector.cosine_distance(query_vectors.c.q_vector)
                    ).label("distance"),
                )
                .where(DocumentChunk.collection_name == collection_name)
                .order_by(
                    (DocumentChunk.vector.cosine_distance(query_vectors.c.q_vector))
                )
            )
            if limit is not None:
                subq = subq.limit(limit)
            subq = subq.lateral("result")

            # Build the main query by joining query_vectors and the lateral subquery
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

            if not results:
                return SearchResult(
                    ids=ids,
                    distances=distances,
                    documents=documents,
                    metadatas=metadatas,
                )

            for row in results:
                qid = int(row.qid)
                ids[qid].append(row.id)
                distances[qid].append(row.distance)
                documents[qid].append(row.text)
                metadatas[qid].append(row.vmetadata)

            return SearchResult(
                ids=ids, distances=distances, documents=documents, metadatas=metadatas
            )
        except Exception as e:
            print(f"Error during search: {e}")
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

            return GetResult(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as e:
            print(f"Error during query: {e}")
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

            return GetResult(ids=ids, documents=documents, metadatas=metadatas)
        except Exception as e:
            print(f"Error during get: {e}")
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
            print(f"Deleted {deleted} items from collection '{collection_name}'.")
        except Exception as e:
            self.session.rollback()
            print(f"Error during delete: {e}")
            raise

    def reset(self) -> None:
        try:
            deleted = self.session.query(DocumentChunk).delete()
            self.session.commit()
            print(
                f"Reset complete. Deleted {deleted} items from 'document_chunk' table."
            )
        except Exception as e:
            self.session.rollback()
            print(f"Error during reset: {e}")
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
            return exists
        except Exception as e:
            print(f"Error checking collection existence: {e}")
            return False

    def delete_collection(self, collection_name: str) -> None:
        self.delete(collection_name)
        print(f"Collection '{collection_name}' deleted.")
