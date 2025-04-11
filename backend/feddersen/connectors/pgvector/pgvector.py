import ast
import json
import logging
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from feddersen.config import EXTRA_MIDDLEWARE_METADATA_KEY
from feddersen.connectors.base import VectorSearchClient
from feddersen.connectors.pgvector.auth_util import FilterUtils
from feddersen.entra.groups import UserGroupsRetriever
from feddersen.models import ExtraMetadata
from open_webui.config import (
    MICROSOFT_CLIENT_ID,
    MICROSOFT_CLIENT_SECRET,
    MICROSOFT_CLIENT_TENANT_ID,
    PGVECTOR_DB_URL,
    PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import UserModel
from open_webui.retrieval.vector.main import GetResult, SearchResult, VectorItem
from pgvector.sqlalchemy import Vector
from pydantic import ValidationError
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    cast,
    column,
    create_engine,
    select,
    text,
    values,
)
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import true
from sqlalchemy.sql.elements import ColumnElement

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

VECTOR_LENGTH = PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH
Base = declarative_base()


class DocumentAuthChunk(Base):
    __tablename__ = "document_auth_chunk"

    id = Column(Text, primary_key=True)
    vector = Column(Vector(dim=VECTOR_LENGTH), nullable=True)
    collection_name = Column(Text, nullable=False)
    text = Column(Text, nullable=True)
    vmetadata = Column(MutableDict.as_mutable(JSONB), nullable=True)
    file_auth = Column(MutableDict.as_mutable(JSONB), nullable=True)

    @classmethod
    def create(
        cls,
        id: str,
        collection_name: str,
        text: Optional[str] = None,
        vector: Optional[List[float]] = None,
        vmetadata: Optional[Dict[str, Any]] = None,
        custom_metadata_key: str = EXTRA_MIDDLEWARE_METADATA_KEY,
        replace_keys: dict = None,
    ) -> "DocumentAuthChunk":
        """Factory-Methode to create a DocumentAuthChunk. Used to manipulate the metadata"""

        meta, file_auth = cls.prepare_metadata(
            vmetadata, custom_metadata_key, replace_keys
        )

        return cls(
            id=id,
            collection_name=collection_name,
            text=text,
            vector=vector,
            vmetadata=meta,
            file_auth=file_auth,
        )

    @staticmethod
    def prepare_metadata(
        metadata: dict | str,
        custom_metadata_key: str,
        replace_keys: Optional[dict[str]] = None,
    ) -> Tuple[dict, dict]:
        """
        Prepare metadata for storing in the database by separating regular
        metadata from auth metadata.

        Args:
            metadata: The original metadata dictionary
            custom_metadata_key: Key under which custom metadata is stored
                                 replace_keys: Optional dictionary mapping native keys to custom
                                 field names for replacement

        Returns:
            Tuple of (processed metadata dict, auth metadata dict)
        """
        custom_meta = {}

        # Create a copy of the original metadata or start with an empty dict
        meta = deepcopy(metadata) if metadata else {}

        custom_metadata = meta.get(custom_metadata_key)
        if isinstance(custom_metadata, str):
            try:
                # Try to parse the string as JSON
                meta[custom_metadata_key] = json.loads(custom_metadata)
            except json.JSONDecodeError:
                # If parsing as json fails, try parsing as python object (safe version)
                try:
                    meta[custom_metadata_key] = ast.literal_eval(custom_metadata)
                except (ValueError, SyntaxError):
                    # If both parsing attempts fail, keep it as a string
                    log.warning(
                        f"Failed to parse metadata for key '{custom_metadata_key}'. Keeping it as a string."
                    )

        # If there's no custom metadata, return early with defaults
        if (
            not meta
            or custom_metadata_key not in meta
            or not meta.get(custom_metadata_key)
        ):
            # Remove the custom metadata key from the main metadata
            # so that we can check for undefined in the frontend
            meta.pop(custom_metadata_key, None)
            return meta, {"groups": [], "users": []}

        # Extract the custom metadata section
        custom_meta_main = meta.pop(custom_metadata_key, {})

        # Try to validate the custom metadata using Pydantic
        try:
            extra_data = ExtraMetadata.model_validate(custom_meta_main)
            file_auth = extra_data.auth
            custom_meta = extra_data.metadata
        except ValidationError as e:
            log.error(f"Error validating metadata: {str(e)}")

        # Try to add processed custom metadata back to the main metadata
        try:
            meta[custom_metadata_key] = custom_meta.model_dump()
        except (ValidationError, AttributeError) as e:
            log.error(f"Error serializing metadata: {str(e)}")

        # Apply key replacements if specified
        if replace_keys:
            for native_key, custom_field in replace_keys.items():
                try:
                    meta[native_key] = getattr(custom_meta, custom_field)
                except (AttributeError, ValidationError) as e:
                    log.warning(
                        f"Couldn't replace {native_key} with {custom_field}: {str(e)}"
                    )

        # make sure the user_ids are all lower case for exact matching
        file_auth.users = [user.lower() for user in file_auth.users]

        return meta, file_auth.model_dump()


class FeddersenPGVectorConnector(VectorSearchClient):
    def __init__(self, session=None):
        self.middleware_metadata_key = EXTRA_MIDDLEWARE_METADATA_KEY

        self.group_retriever = UserGroupsRetriever(
            sso_app_client_id=MICROSOFT_CLIENT_ID.value,
            sso_app_client_secret=MICROSOFT_CLIENT_SECRET.value,
            sso_app_tenant_id=MICROSOFT_CLIENT_TENANT_ID.value,
            ms_graph_url="https://graph.microsoft.com/v1.0",
            cache_duration=3600 * 24,  # cache the user groups for a day
        )

        if session:
            # allow to insert session for test reasons
            self.session = session
        elif not PGVECTOR_DB_URL:
            # if no pgvector uri, use the existing database connection
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
            # CUSTOM EDIT: USE HNSW INSTEAD OF ivfflat
            self.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunk_vector "
                    "ON document_auth_chunk USING hnsw (vector vector_cosine_ops) "
                    "WITH (m = 16, ef_construction = 100);"
                )
            )
            # Set the ef_search parameter for the HNSW index at query time for this session
            self.session.execute(text("SET hnsw.ef_search = 30;"))
            self.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunk_collection_name ON document_auth_chunk (collection_name);"
                )
            )
            # Add GIN indexes for the JSONB file_auth column used in permission filtering
            self.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunk_file_auth_groups ON document_auth_chunk USING GIN ((file_auth->'groups'));"
                )
            )
            self.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunk_file_auth_users ON document_auth_chunk USING GIN ((file_auth->'users'));"
                )
            )
            self.session.commit()
            log.info("Initialization complete.")
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during initialization: {e}")
            raise

    def adjust_vector_length(self, vector: List[float]) -> List[float]:
        # Adjust vector to have length VECTOR_LENGTH
        current_length = len(vector)
        if current_length < VECTOR_LENGTH:
            # Pad the vector with zeros
            vector += [0.0] * (VECTOR_LENGTH - current_length)
        elif current_length > VECTOR_LENGTH:
            # CUSTOM EDIT: Truncate the vector to VECTOR_LENGTH instead of raising an error
            # Only valid for matryoshka embedding vectors like openai's text-embedding-3-large
            vector = vector[:VECTOR_LENGTH]
        return vector

    def _create_permission_filter(self, user: UserModel) -> ColumnElement:
        # File base filter
        if user is None:
            log.warning(
                "User was not passed through to the PGVector connector. This should not happen."
            )
        user_mail = user.email if user else ""
        user_entra_groups = self.group_retriever.get_user_groups(user_mail)

        # Exception for certain groups to read all documents, like developers
        if user and user.role == "admin":
            return text("true")

        permission_filter_stmt = FilterUtils().create_auth_filter_clause(
            user_mail, user_entra_groups, DocumentAuthChunk.file_auth
        )
        return permission_filter_stmt

    @staticmethod
    def make_titles_unique(metadatas: list):
        # find all duplicate titles and append the date to the title
        source_names = defaultdict(set)
        for m in metadatas:
            name = m.get("name")
            source_names[name].update({m.get("file_id")})

        duplicated_titles = [
            name for name, files in source_names.items() if len(files) > 1
        ]
        if not duplicated_titles:
            # No duplicates found, return original metadata
            return metadatas

        meta_copy = deepcopy(metadatas)
        for duplicated_title in duplicated_titles:
            for m in meta_copy:
                if m.get("name") == duplicated_title:
                    # Append the date to the title
                    date_string = m[EXTRA_MIDDLEWARE_METADATA_KEY].get("date")
                    if date_string:
                        date = datetime.fromisoformat(date_string)
                        # format as MM/YY
                        date_str = date.strftime("%m/%y")
                        m["name"] = f"{duplicated_title} ({date_str})"
        return meta_copy

    def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        limit: Optional[int] = None,
        user: UserModel | None = None,
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
            subq = select(
                DocumentAuthChunk.id,
                DocumentAuthChunk.text,
                DocumentAuthChunk.vmetadata,
                (
                    DocumentAuthChunk.vector.cosine_distance(query_vectors.c.q_vector)
                ).label("distance"),
            ).where(DocumentAuthChunk.collection_name == collection_name)

            # Restrict to documents that the user has access to
            subq = subq.where(self._create_permission_filter(user))

            subq = subq.order_by(
                (DocumentAuthChunk.vector.cosine_distance(query_vectors.c.q_vector))
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
                # normalize and re-orders pgvec distance from [2, 0] to [0, 1] score range
                # https://github.com/pgvector/pgvector?tab=readme-ov-file#querying
                distances[qid].append((2.0 - row.distance) / 2.0)
                documents[qid].append(row.text)
                metadatas[qid].append(row.vmetadata)

            # Make titles unique for each query by adding the date to the name
            for i in range(num_queries):
                metadatas[i] = self.make_titles_unique(metadatas[i])

            return SearchResult(
                ids=ids, distances=distances, documents=documents, metadatas=metadatas
            )
        except Exception as e:
            log.exception(f"Error during search: {e}")
            return None

    def query(
        self,
        collection_name: str,
        filter: Dict[str, Any],
        limit: Optional[int] = None,
        user: UserModel | None = None,
    ) -> Optional[GetResult]:
        try:
            query = self.session.query(DocumentAuthChunk).filter(
                DocumentAuthChunk.collection_name == collection_name
            )

            # Restrict to documents that the user has access to
            permission_filter_stmt = self._create_permission_filter(user)
            query = query.filter(permission_filter_stmt)

            for key, value in filter.items():
                query = query.filter(
                    DocumentAuthChunk.vmetadata[key].astext == str(value)
                )

            if limit is not None:
                query = query.limit(limit)

            results = query.all()

            if not results:
                return None

            ids = [[result.id for result in results]]
            documents = [[result.text for result in results]]
            metadatas = [[result.vmetadata for result in results]]

            # Make titles unique for each query by adding the date to the name
            metadatas[0] = self.make_titles_unique(metadatas[0])

            return GetResult(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as e:
            log.exception(f"Error during query: {e}")
            return None

    def get(
        self,
        collection_name: str,
        limit: Optional[int] = None,
        user: UserModel | None = None,
    ) -> Optional[GetResult]:
        try:
            query = self.session.query(DocumentAuthChunk).filter(
                DocumentAuthChunk.collection_name == collection_name
            )

            # Restrict to documents that the user has access to
            permission_filter_stmt = self._create_permission_filter(user)
            query = query.filter(permission_filter_stmt)

            if limit is not None:
                query = query.limit(limit)

            results = query.all()

            if not results:
                return None

            ids = [[result.id for result in results]]
            documents = [[result.text for result in results]]
            metadatas = [[result.vmetadata for result in results]]

            # Make titles unique for each query by adding the date to the name
            metadatas[0] = self.make_titles_unique(metadatas[0])

            return GetResult(ids=ids, documents=documents, metadatas=metadatas)
        except Exception as e:
            log.exception(f"Error during get: {e}")
            return None

    def check_vector_length(self) -> None:
        """
        Check if the VECTOR_LENGTH matches the existing vector column dimension in the database.
        Raises an exception if there is a mismatch.
        """
        metadata = MetaData()
        try:
            # Attempt to reflect the 'document_auth_chunk' table
            document_chunk_table = Table(
                "document_auth_chunk", metadata, autoload_with=self.session.bind
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
                        f"VECTOR_LENGTH {VECTOR_LENGTH} does not match existing vector column "
                        f"dimension {db_vector_length}. "
                        "Cannot change vector size after initialization without migrating the data."
                    )
            else:
                raise Exception(
                    "The 'vector' column exists but is not of type 'Vector'."
                )
        else:
            raise Exception(
                "The 'vector' column does not exist in the 'document_auth_chunk' table."
            )

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        try:
            new_items = []
            for item in items:
                vector = self.adjust_vector_length(item["vector"])
                new_chunk = DocumentAuthChunk.create(
                    id=item["id"],
                    vector=vector,
                    collection_name=collection_name,
                    text=item["text"],
                    vmetadata=item["metadata"],
                    custom_metadata_key=self.middleware_metadata_key,
                    replace_keys={"name": "title"},
                )
                new_items.append(new_chunk)
            self.session.bulk_save_objects(new_items)
            self.session.commit()
            log.info(
                f"Inserted {len(new_items)} items into collection '{collection_name}'."
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during insert: {e}")
            raise

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        try:
            for item in items:
                vector = self.adjust_vector_length(item["vector"])
                existing = (
                    self.session.query(DocumentAuthChunk)
                    .filter(DocumentAuthChunk.id == item["id"])
                    .first()
                )
                if existing:
                    existing.vector = vector
                    existing.text = item["text"]

                    metadata, auth = DocumentAuthChunk.prepare_metadata(
                        item["metadata"],
                        self.middleware_metadata_key,
                        replace_keys={"name": "title"},
                    )

                    existing.vmetadata = metadata
                    existing.collection_name = (
                        collection_name  # Update collection_name if necessary
                    )
                    existing.file_auth = auth
                else:
                    new_chunk = DocumentAuthChunk.create(
                        id=item["id"],
                        vector=vector,
                        collection_name=collection_name,
                        text=item["text"],
                        vmetadata=item["metadata"],
                        custom_metadata_key=self.middleware_metadata_key,
                        replace_keys={"name": "title"},
                    )
                    self.session.add(new_chunk)
            self.session.commit()
            log.info(
                f"Upserted {len(items)} items into collection '{collection_name}'."
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during upsert: {e}")
            raise

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            query = self.session.query(DocumentAuthChunk).filter(
                DocumentAuthChunk.collection_name == collection_name
            )
            if ids:
                query = query.filter(DocumentAuthChunk.id.in_(ids))
            if filter:
                for key, value in filter.items():
                    query = query.filter(
                        DocumentAuthChunk.vmetadata[key].astext == str(value)
                    )
            deleted = query.delete(synchronize_session=False)
            self.session.commit()
            log.info(f"Deleted {deleted} items from collection '{collection_name}'.")
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during delete: {e}")
            raise

    def reset(self) -> None:
        try:
            deleted = self.session.query(DocumentAuthChunk).delete()
            self.session.commit()
            log.info(
                f"Reset complete. Deleted {deleted} items from 'document_auth_chunk' table."
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during reset: {e}")
            raise

    def has_collection(self, collection_name: str) -> bool:
        try:
            exists = (
                self.session.query(DocumentAuthChunk)
                .filter(DocumentAuthChunk.collection_name == collection_name)
                .first()
                is not None
            )
            return exists
        except Exception as e:
            log.exception(f"Error checking collection existence: {e}")
            return False

    def delete_collection(self, collection_name: str) -> None:
        self.delete(collection_name)
        log.info(f"Collection '{collection_name}' deleted.")

    def close(self) -> None:
        pass
