"""
Oracle 23ai Vector Database Client - Fixed Version

# .env
VECTOR_DB = "oracle23ai"

## DBCS or oracle 23ai free
ORACLE_DB_USE_WALLET =  false
ORACLE_DB_USER = "DEMOUSER"
ORACLE_DB_PASSWORD = "Welcome123456"
ORACLE_DB_DSN = "localhost:1521/FREEPDB1"

## ADW or ATP
# ORACLE_DB_USE_WALLET =  true
# ORACLE_DB_USER = "DEMOUSER"
# ORACLE_DB_PASSWORD = "Welcome123456"
# ORACLE_DB_DSN = "medium"
# ORACLE_DB_DSN = "(description=  (retry_count=3)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=xx.oraclecloud.com))(connect_data=(service_name=yy.adb.oraclecloud.com))(security=(ssl_server_dn_match=no)))"
# ORACLE_WALLET_DIR = "/home/opc/adb_wallet"
# ORACLE_WALLET_PASSWORD = "Welcome1"

ORACLE_VECTOR_LENGTH = 768

ORACLE_DB_POOL_MIN = 2
ORACLE_DB_POOL_MAX = 10
ORACLE_DB_POOL_INCREMENT = 1
"""

from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
import logging
import os
import threading
import time
import json
import array
import oracledb

from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)

from open_webui.config import (
    ORACLE_DB_USE_WALLET,
    ORACLE_DB_USER,
    ORACLE_DB_PASSWORD,
    ORACLE_DB_DSN,
    ORACLE_WALLET_DIR,
    ORACLE_WALLET_PASSWORD,
    ORACLE_VECTOR_LENGTH,
    ORACLE_DB_POOL_MIN,
    ORACLE_DB_POOL_MAX,
    ORACLE_DB_POOL_INCREMENT,
)
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class Oracle23aiClient(VectorDBBase):
    """
    Oracle Vector Database Client for vector similarity search using Oracle Database 23ai.

    This client provides an interface to store, retrieve, and search vector embeddings
    in an Oracle database. It uses connection pooling for efficient database access
    and supports vector similarity search operations.

    Attributes:
        pool: Connection pool for Oracle database connections
    """

    def __init__(self) -> None:
        """
        Initialize the Oracle23aiClient with a connection pool.

        Creates a connection pool with configurable min/max connections, initializes
        the database schema if needed, and sets up necessary tables and indexes.

        Raises:
            ValueError: If required configuration parameters are missing
            Exception: If database initialization fails
        """
        self.pool = None

        try:
            # Create the appropriate connection pool based on DB type
            if ORACLE_DB_USE_WALLET:
                self._create_adb_pool()
            else:  # DBCS
                self._create_dbcs_pool()

            dsn = ORACLE_DB_DSN
            log.info(f"Creating Connection Pool [{ORACLE_DB_USER}:**@{dsn}]")

            with self.get_connection() as connection:
                log.info(f"Connection version: {connection.version}")
                self._initialize_database(connection)

            log.info("Oracle Vector Search initialization complete.")
        except Exception as e:
            log.exception(f"Error during Oracle Vector Search initialization: {e}")
            raise

    def _create_adb_pool(self) -> None:
        """
        Create connection pool for Oracle Autonomous Database.

        Uses wallet-based authentication.
        """
        self.pool = oracledb.create_pool(
            user=ORACLE_DB_USER,
            password=ORACLE_DB_PASSWORD,
            dsn=ORACLE_DB_DSN,
            min=ORACLE_DB_POOL_MIN,
            max=ORACLE_DB_POOL_MAX,
            increment=ORACLE_DB_POOL_INCREMENT,
            config_dir=ORACLE_WALLET_DIR,
            wallet_location=ORACLE_WALLET_DIR,
            wallet_password=ORACLE_WALLET_PASSWORD,
        )
        log.info("Created ADB connection pool with wallet authentication.")

    def _create_dbcs_pool(self) -> None:
        """
        Create connection pool for Oracle Database Cloud Service.

        Uses basic authentication without wallet.
        """
        self.pool = oracledb.create_pool(
            user=ORACLE_DB_USER,
            password=ORACLE_DB_PASSWORD,
            dsn=ORACLE_DB_DSN,
            min=ORACLE_DB_POOL_MIN,
            max=ORACLE_DB_POOL_MAX,
            increment=ORACLE_DB_POOL_INCREMENT,
        )
        log.info("Created DB connection pool with basic authentication.")

    def get_connection(self):
        """
        Acquire a connection from the connection pool with retry logic.

        Returns:
            connection: A database connection with output type handler configured
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = self.pool.acquire()
                connection.outputtypehandler = self._output_type_handler
                return connection
            except oracledb.DatabaseError as e:
                (error_obj,) = e.args
                log.exception(
                    f"Connection attempt {attempt + 1} failed: {error_obj.message}"
                )

                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    log.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise

    def start_health_monitor(self, interval_seconds: int = 60):
        """
        Start a background thread to periodically check the health of the connection pool.

        Args:
            interval_seconds (int): Number of seconds between health checks
        """

        def _monitor():
            while True:
                try:
                    log.info("[HealthCheck] Running periodic DB health check...")
                    self.ensure_connection()
                    log.info("[HealthCheck] Connection is healthy.")
                except Exception as e:
                    log.exception(f"[HealthCheck] Connection health check failed: {e}")
                time.sleep(interval_seconds)

        thread = threading.Thread(target=_monitor, daemon=True)
        thread.start()
        log.info(f"Started DB health monitor every {interval_seconds} seconds.")

    def _reconnect_pool(self):
        """
        Attempt to reinitialize the connection pool if it's been closed or broken.
        """
        try:
            log.info("Attempting to reinitialize the Oracle connection pool...")

            # Close existing pool if it exists
            if self.pool:
                try:
                    self.pool.close()
                except Exception as close_error:
                    log.warning(f"Error closing existing pool: {close_error}")

            # Re-create the appropriate connection pool based on DB type
            if ORACLE_DB_USE_WALLET:
                self._create_adb_pool()
            else:  # DBCS
                self._create_dbcs_pool()

            log.info("Connection pool reinitialized.")
        except Exception as e:
            log.exception(f"Failed to reinitialize the connection pool: {e}")
            raise

    def ensure_connection(self):
        """
        Ensure the database connection is alive, reconnecting pool if needed.
        """
        try:
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM dual")
        except Exception as e:
            log.exception(
                f"Connection check failed: {e}, attempting to reconnect pool..."
            )
            self._reconnect_pool()

    def _output_type_handler(self, cursor, metadata):
        """
        Handle Oracle vector type conversion.

        Args:
            cursor: Oracle database cursor
            metadata: Metadata for the column

        Returns:
            A variable with appropriate conversion for vector types
        """
        if metadata.type_code is oracledb.DB_TYPE_VECTOR:
            return cursor.var(
                metadata.type_code, arraysize=cursor.arraysize, outconverter=list
            )

    def _initialize_database(self, connection) -> None:
        """
        Initialize database schema, tables and indexes.

        Creates the document_chunk table and necessary indexes if they don't exist.

        Args:
            connection: Oracle database connection

        Raises:
            Exception: If schema initialization fails
        """
        with connection.cursor() as cursor:
            try:
                log.info("Creating Table document_chunk")
                cursor.execute(
                    """
                    BEGIN
                        EXECUTE IMMEDIATE '
                            CREATE TABLE IF NOT EXISTS document_chunk (
                                id VARCHAR2(255) PRIMARY KEY,
                                collection_name VARCHAR2(255) NOT NULL,
                                text CLOB,
                                vmetadata JSON,
                                vector vector(*, float32)
                            )
                        ';
                    EXCEPTION
                        WHEN OTHERS THEN
                            IF SQLCODE != -955 THEN
                                RAISE;
                            END IF;
                    END;
                """
                )

                log.info("Creating Index document_chunk_collection_name_idx")
                cursor.execute(
                    """
                    BEGIN
                        EXECUTE IMMEDIATE '
                            CREATE INDEX IF NOT EXISTS document_chunk_collection_name_idx
                            ON document_chunk (collection_name)
                        ';
                    EXCEPTION
                        WHEN OTHERS THEN
                            IF SQLCODE != -955 THEN
                                RAISE;
                            END IF;
                    END;
                """
                )

                log.info("Creating VECTOR INDEX document_chunk_vector_ivf_idx")
                cursor.execute(
                    """
                    BEGIN
                        EXECUTE IMMEDIATE '
                            CREATE VECTOR INDEX IF NOT EXISTS document_chunk_vector_ivf_idx 
                            ON document_chunk(vector) 
                            ORGANIZATION NEIGHBOR PARTITIONS
                            DISTANCE COSINE
                            WITH TARGET ACCURACY 95
                            PARAMETERS (TYPE IVF, NEIGHBOR PARTITIONS 100)
                        ';
                    EXCEPTION
                        WHEN OTHERS THEN
                            IF SQLCODE != -955 THEN
                                RAISE;
                            END IF;
                    END;
                """
                )

                connection.commit()
                log.info("Database initialization completed successfully.")

            except Exception as e:
                connection.rollback()
                log.exception(f"Error during database initialization: {e}")
                raise

    def check_vector_length(self) -> None:
        """
        Check vector length compatibility (placeholder).

        This method would check if the configured vector length matches the database schema.
        Currently implemented as a placeholder.
        """
        pass

    def _vector_to_blob(self, vector: List[float]) -> bytes:
        """
        Convert a vector to Oracle BLOB format.

        Args:
            vector (List[float]): The vector to convert

        Returns:
            bytes: The vector in Oracle BLOB format
        """
        return array.array("f", vector)

    def adjust_vector_length(self, vector: List[float]) -> List[float]:
        """
        Adjust vector to the expected length if needed.

        Args:
            vector (List[float]): The vector to adjust

        Returns:
            List[float]: The adjusted vector
        """
        return vector

    def _decimal_handler(self, obj):
        """
        Handle Decimal objects for JSON serialization.

        Args:
            obj: Object to serialize

        Returns:
            float: Converted decimal value

        Raises:
            TypeError: If object is not JSON serializable
        """
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"{obj} is not JSON serializable")

    def _metadata_to_json(self, metadata: Dict) -> str:
        """
        Convert metadata dictionary to JSON string.

        Args:
            metadata (Dict): Metadata dictionary

        Returns:
            str: JSON representation of metadata
        """
        return json.dumps(metadata, default=self._decimal_handler) if metadata else "{}"

    def _json_to_metadata(self, json_str: str) -> Dict:
        """
        Convert JSON string to metadata dictionary.

        Args:
            json_str (str): JSON string

        Returns:
            Dict: Metadata dictionary
        """
        return json.loads(json_str) if json_str else {}

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        """
        Insert vector items into the database.

        Args:
            collection_name (str): Name of the collection
            items (List[VectorItem]): List of vector items to insert

        Raises:
            Exception: If insertion fails

        Example:
            >>> client = Oracle23aiClient()
            >>> items = [
            ...     {"id": "1", "text": "Sample text", "vector": [0.1, 0.2, ...], "metadata": {"source": "doc1"}},
            ...     {"id": "2", "text": "Another text", "vector": [0.3, 0.4, ...], "metadata": {"source": "doc2"}}
            ... ]
            >>> client.insert("my_collection", items)
        """
        log.info(f"Inserting {len(items)} items into collection '{collection_name}'.")

        with self.get_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    for item in items:
                        vector_blob = self._vector_to_blob(item["vector"])
                        metadata_json = self._metadata_to_json(item["metadata"])

                        cursor.execute(
                            """
                            INSERT INTO document_chunk 
                            (id, collection_name, text, vmetadata, vector) 
                            VALUES (:id, :collection_name, :text, :metadata, :vector)
                        """,
                            {
                                "id": item["id"],
                                "collection_name": collection_name,
                                "text": item["text"],
                                "metadata": metadata_json,
                                "vector": vector_blob,
                            },
                        )

                connection.commit()
                log.info(
                    f"Successfully inserted {len(items)} items into collection '{collection_name}'."
                )

            except Exception as e:
                connection.rollback()
                log.exception(f"Error during insert: {e}")
                raise

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        """
        Update or insert vector items into the database.

        If an item with the same ID exists, it will be updated;
        otherwise, it will be inserted.

        Args:
            collection_name (str): Name of the collection
            items (List[VectorItem]): List of vector items to upsert

        Raises:
            Exception: If upsert operation fails

        Example:
            >>> client = Oracle23aiClient()
            >>> items = [
            ...     {"id": "1", "text": "Updated text", "vector": [0.1, 0.2, ...], "metadata": {"source": "doc1"}},
            ...     {"id": "3", "text": "New item", "vector": [0.5, 0.6, ...], "metadata": {"source": "doc3"}}
            ... ]
            >>> client.upsert("my_collection", items)
        """
        log.info(f"Upserting {len(items)} items into collection '{collection_name}'.")

        with self.get_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    for item in items:
                        vector_blob = self._vector_to_blob(item["vector"])
                        metadata_json = self._metadata_to_json(item["metadata"])

                        cursor.execute(
                            """
                            MERGE INTO document_chunk d
                            USING (SELECT :merge_id as id FROM dual) s
                            ON (d.id = s.id)
                            WHEN MATCHED THEN
                                UPDATE SET 
                                    collection_name = :upd_collection_name,
                                    text = :upd_text,
                                    vmetadata = :upd_metadata,
                                    vector = :upd_vector
                            WHEN NOT MATCHED THEN
                                INSERT (id, collection_name, text, vmetadata, vector)
                                VALUES (:ins_id, :ins_collection_name, :ins_text, :ins_metadata, :ins_vector)
                        """,
                            {
                                "merge_id": item["id"],
                                "upd_collection_name": collection_name,
                                "upd_text": item["text"],
                                "upd_metadata": metadata_json,
                                "upd_vector": vector_blob,
                                "ins_id": item["id"],
                                "ins_collection_name": collection_name,
                                "ins_text": item["text"],
                                "ins_metadata": metadata_json,
                                "ins_vector": vector_blob,
                            },
                        )

                connection.commit()
                log.info(
                    f"Successfully upserted {len(items)} items into collection '{collection_name}'."
                )

            except Exception as e:
                connection.rollback()
                log.exception(f"Error during upsert: {e}")
                raise

    def search(
        self, collection_name: str, vectors: List[List[Union[float, int]]], limit: int
    ) -> Optional[SearchResult]:
        """
        Search for similar vectors in the database.

        Performs vector similarity search using cosine distance.

        Args:
            collection_name (str): Name of the collection to search
            vectors (List[List[Union[float, int]]]): Query vectors to find similar items for
            limit (int): Maximum number of results to return per query

        Returns:
            Optional[SearchResult]: Search results containing ids, distances, documents, and metadata

        Example:
            >>> client = Oracle23aiClient()
            >>> query_vector = [0.1, 0.2, 0.3, ...]  # Must match VECTOR_LENGTH
            >>> results = client.search("my_collection", [query_vector], limit=5)
            >>> if results:
            ...     log.info(f"Found {len(results.ids[0])} matches")
            ...     for i, (id, dist) in enumerate(zip(results.ids[0], results.distances[0])):
            ...         log.info(f"Match {i+1}: id={id}, distance={dist}")
        """
        log.info(
            f"Searching items from collection '{collection_name}' with limit {limit}."
        )

        try:
            if not vectors:
                log.warning("No vectors provided for search.")
                return None

            num_queries = len(vectors)

            ids = [[] for _ in range(num_queries)]
            distances = [[] for _ in range(num_queries)]
            documents = [[] for _ in range(num_queries)]
            metadatas = [[] for _ in range(num_queries)]

            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    for qid, vector in enumerate(vectors):
                        vector_blob = self._vector_to_blob(vector)

                        cursor.execute(
                            """
                            SELECT dc.id, dc.text, 
                                JSON_SERIALIZE(dc.vmetadata RETURNING VARCHAR2(4096)) as vmetadata,
                                VECTOR_DISTANCE(dc.vector, :query_vector, COSINE) as distance
                            FROM document_chunk dc
                            WHERE dc.collection_name = :collection_name
                            ORDER BY VECTOR_DISTANCE(dc.vector, :query_vector, COSINE)
                            FETCH APPROX FIRST :limit ROWS ONLY
                        """,
                            {
                                "query_vector": vector_blob,
                                "collection_name": collection_name,
                                "limit": limit,
                            },
                        )

                        results = cursor.fetchall()

                        for row in results:
                            ids[qid].append(row[0])
                            documents[qid].append(
                                row[1].read()
                                if isinstance(row[1], oracledb.LOB)
                                else str(row[1])
                            )
                            # 🔧 FIXED: Parse JSON metadata properly
                            metadata_str = (
                                row[2].read()
                                if isinstance(row[2], oracledb.LOB)
                                else row[2]
                            )
                            metadatas[qid].append(self._json_to_metadata(metadata_str))
                            distances[qid].append(float(row[3]))

            log.info(
                f"Search completed. Found {sum(len(ids[i]) for i in range(num_queries))} total results."
            )

            return SearchResult(
                ids=ids, distances=distances, documents=documents, metadatas=metadatas
            )

        except Exception as e:
            log.exception(f"Error during search: {e}")
            return None

    def query(
        self, collection_name: str, filter: Dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """
        Query items based on metadata filters.

        Retrieves items that match specified metadata criteria.

        Args:
            collection_name (str): Name of the collection to query
            filter (Dict[str, Any]): Metadata filters to apply
            limit (Optional[int]): Maximum number of results to return

        Returns:
            Optional[GetResult]: Query results containing ids, documents, and metadata

        Example:
            >>> client = Oracle23aiClient()
            >>> filter = {"source": "doc1", "category": "finance"}
            >>> results = client.query("my_collection", filter, limit=20)
            >>> if results:
            ...     print(f"Found {len(results.ids[0])} matching documents")
        """
        log.info(f"Querying items from collection '{collection_name}' with filters.")

        try:
            limit = limit or 100

            query = """
                SELECT id, text, JSON_SERIALIZE(vmetadata RETURNING VARCHAR2(4096)) as vmetadata 
                FROM document_chunk
                WHERE collection_name = :collection_name
            """

            params = {"collection_name": collection_name}

            for i, (key, value) in enumerate(filter.items()):
                param_name = f"value_{i}"
                query += f" AND JSON_VALUE(vmetadata, '$.{key}' RETURNING VARCHAR2(4096)) = :{param_name}"
                params[param_name] = str(value)

            query += " FETCH FIRST :limit ROWS ONLY"
            params["limit"] = limit

            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()

            if not results:
                log.info("No results found for query.")
                return None

            ids = [[row[0] for row in results]]
            documents = [
                [
                    row[1].read() if isinstance(row[1], oracledb.LOB) else str(row[1])
                    for row in results
                ]
            ]
            # 🔧 FIXED: Parse JSON metadata properly
            metadatas = [
                [
                    self._json_to_metadata(
                        row[2].read() if isinstance(row[2], oracledb.LOB) else row[2]
                    )
                    for row in results
                ]
            ]

            log.info(f"Query completed. Found {len(results)} results.")

            return GetResult(ids=ids, documents=documents, metadatas=metadatas)

        except Exception as e:
            log.exception(f"Error during query: {e}")
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """
        Get all items in a collection.

        Retrieves items from a specified collection up to the limit.

        Args:
            collection_name (str): Name of the collection to retrieve
            limit (Optional[int]): Maximum number of items to retrieve

        Returns:
            Optional[GetResult]: Result containing ids, documents, and metadata

        Example:
            >>> client = Oracle23aiClient()
            >>> results = client.get("my_collection", limit=50)
            >>> if results:
            ...     print(f"Retrieved {len(results.ids[0])} documents from collection")
        """
        log.info(
            f"Getting items from collection '{collection_name}' with limit {limit}."
        )

        try:
            limit = limit or 1000

            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT /*+ MONITOR */ id, text, JSON_SERIALIZE(vmetadata RETURNING VARCHAR2(4096)) as vmetadata
                        FROM document_chunk
                        WHERE collection_name = :collection_name
                        FETCH FIRST :limit ROWS ONLY
                    """,
                        {"collection_name": collection_name, "limit": limit},
                    )

                    results = cursor.fetchall()

            if not results:
                log.info("No results found.")
                return None

            ids = [[row[0] for row in results]]
            documents = [
                [
                    row[1].read() if isinstance(row[1], oracledb.LOB) else str(row[1])
                    for row in results
                ]
            ]
            # 🔧 FIXED: Parse JSON metadata properly
            metadatas = [
                [
                    self._json_to_metadata(
                        row[2].read() if isinstance(row[2], oracledb.LOB) else row[2]
                    )
                    for row in results
                ]
            ]

            return GetResult(ids=ids, documents=documents, metadatas=metadatas)

        except Exception as e:
            log.exception(f"Error during get: {e}")
            return None

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Delete items from the database.

        Deletes items from a collection based on IDs or metadata filters.

        Args:
            collection_name (str): Name of the collection to delete from
            ids (Optional[List[str]]): Specific item IDs to delete
            filter (Optional[Dict[str, Any]]): Metadata filters for deletion

        Raises:
            Exception: If deletion fails

        Example:
            >>> client = Oracle23aiClient()
            >>> # Delete specific items by ID
            >>> client.delete("my_collection", ids=["1", "3", "5"])
            >>> # Or delete by metadata filter
            >>> client.delete("my_collection", filter={"source": "deprecated_source"})
        """
        log.info(f"Deleting items from collection '{collection_name}'.")

        try:
            query = (
                "DELETE FROM document_chunk WHERE collection_name = :collection_name"
            )
            params = {"collection_name": collection_name}

            if ids:
                # 🔧 FIXED: Use proper parameterized query to prevent SQL injection
                placeholders = ",".join([f":id_{i}" for i in range(len(ids))])
                query += f" AND id IN ({placeholders})"
                for i, id_val in enumerate(ids):
                    params[f"id_{i}"] = id_val

            if filter:
                for i, (key, value) in enumerate(filter.items()):
                    param_name = f"value_{i}"
                    query += f" AND JSON_VALUE(vmetadata, '$.{key}' RETURNING VARCHAR2(4096)) = :{param_name}"
                    params[param_name] = str(value)

            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    deleted = cursor.rowcount
                connection.commit()

            log.info(f"Deleted {deleted} items from collection '{collection_name}'.")

        except Exception as e:
            log.exception(f"Error during delete: {e}")
            raise

    def reset(self) -> None:
        """
        Reset the database by deleting all items.

        Deletes all items from the document_chunk table.

        Raises:
            Exception: If reset fails

        Example:
            >>> client = Oracle23aiClient()
            >>> client.reset()  # Warning: Removes all data!
        """
        log.info("Resetting database - deleting all items.")

        try:
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM document_chunk")
                    deleted = cursor.rowcount
                connection.commit()

            log.info(
                f"Reset complete. Deleted {deleted} items from 'document_chunk' table."
            )

        except Exception as e:
            log.exception(f"Error during reset: {e}")
            raise

    def close(self) -> None:
        """
        Close the database connection pool.

        Properly closes the connection pool and releases all resources.

        Example:
            >>> client = Oracle23aiClient()
            >>> # After finishing all operations
            >>> client.close()
        """
        try:
            if hasattr(self, "pool") and self.pool:
                self.pool.close()
                log.info("Oracle Vector Search connection pool closed.")
        except Exception as e:
            log.exception(f"Error closing connection pool: {e}")

    def has_collection(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name (str): Name of the collection to check

        Returns:
            bool: True if the collection exists, False otherwise

        Example:
            >>> client = Oracle23aiClient()
            >>> if client.has_collection("my_collection"):
            ...     print("Collection exists!")
            ... else:
            ...     print("Collection does not exist.")
        """
        try:
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM document_chunk
                        WHERE collection_name = :collection_name
                        FETCH FIRST 1 ROWS ONLY
                    """,
                        {"collection_name": collection_name},
                    )

                    count = cursor.fetchone()[0]

            return count > 0

        except Exception as e:
            log.exception(f"Error checking collection existence: {e}")
            return False

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire collection.

        Removes all items belonging to the specified collection.

        Args:
            collection_name (str): Name of the collection to delete

        Example:
            >>> client = Oracle23aiClient()
            >>> client.delete_collection("obsolete_collection")
        """
        log.info(f"Deleting collection '{collection_name}'.")

        try:
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM document_chunk 
                        WHERE collection_name = :collection_name
                    """,
                        {"collection_name": collection_name},
                    )

                    deleted = cursor.rowcount
                connection.commit()

            log.info(
                f"Collection '{collection_name}' deleted. Removed {deleted} items."
            )

        except Exception as e:
            log.exception(f"Error deleting collection '{collection_name}': {e}")
            raise
