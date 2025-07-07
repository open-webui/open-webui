from typing import Optional, List, Dict, Any
from decimal import Decimal

import os
import oracledb

from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)

from open_webui.config import (
    ORACLE_DB_USER,
    ORACLE_DB_PASSWORD,
    ORACLE_DB_DSN,
    ORACLE_WALLET_DIR,
    ORACLE_WALLET_PASSWORD,
    ORACLE_VECTOR_LENGTH,
)

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
        
        Creates a connection pool with min=2 and max=10 connections, initializes
        the database schema if needed, and sets up necessary tables and indexes.
        
        Raises:
            ValueError: If required configuration parameters are missing
            Exception: If database initialization fails
        """
        try:
            if not ORACLE_DB_DSN:
                raise ValueError("ORACLE_DB_DSN is required for Oracle Vector Search")
                
            self.pool = oracledb.create_pool(
                user=ORACLE_DB_USER,
                password=ORACLE_DB_PASSWORD,
                dsn=ORACLE_DB_DSN,
                min=2,
                max=10,
                increment=1,
                config_dir=ORACLE_WALLET_DIR,
                wallet_location=ORACLE_WALLET_DIR,
                wallet_password=ORACLE_WALLET_PASSWORD
            )
            
            print(f" >>> Creating Connection Pool [{ORACLE_DB_USER}:**@{ORACLE_DB_DSN}]")
            
            with self.get_connection() as connection:
                print("Connection version:", connection.version)
                self._initialize_database(connection)
                
            print("Oracle Vector Search initialization complete.")
        except Exception as e:
            print(f"Error during Oracle Vector Search initialization: {e}")
            raise
    
    def get_connection(self):
        """
        Acquire a connection from the connection pool.
        
        Returns:
            connection: A database connection with output type handler configured
        """
        connection = self.pool.acquire()
        connection.outputtypehandler = self._output_type_handler
        return connection
            
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
            return cursor.var(metadata.type_code, arraysize=cursor.arraysize,
                            outconverter=list)

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
            print(f" >>> Creating Table document_chunk")
            cursor.execute(f"""
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
            """)
            
            print(f" >>> Creating Table document_chunk_collection_name_idx")
            cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE INDEX IF NOT exists document_chunk_collection_name_idx
                        ON document_chunk (collection_name)
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            
            print(f" >>> Creating VECTOR INDEX document_chunk_vector_ivf_idx")
            cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE '
                        create vector index  IF NOT EXISTS   document_chunk_vector_ivf_idx on document_chunk(vector) 
                            organization neighbor partitions
                            distance cosine
                            with target accuracy 95
                            PARAMETERS  (type IVF, NEIGHBOR PARTITIONS 100) 
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            
            connection.commit()

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
        import array
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
        import json
        return json.dumps(metadata, default=self._decimal_handler) if metadata else "{}"

    def _json_to_metadata(self, json_str: str) -> Dict:
        """
        Convert JSON string to metadata dictionary.
        
        Args:
            json_str (str): JSON string
            
        Returns:
            Dict: Metadata dictionary
        """
        import json
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
        print(f"Oracle23aiClient:Inserting {len(items)} items into collection '{collection_name}'.")
        with self.get_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    for item in items:
                        vector_blob = self._vector_to_blob(item["vector"])
                        metadata_json = self._metadata_to_json(item["metadata"])
                        
                        cursor.execute("""
                            INSERT INTO document_chunk 
                            (id, collection_name, text, vmetadata, vector) 
                            VALUES (:id, :collection_name, :text, :metadata, :vector)
                        """, {
                            'id': item["id"],
                            'collection_name': collection_name,
                            'text': item["text"],
                            'metadata': metadata_json,
                            'vector': vector_blob                   
                        })
                
                connection.commit()
                print(f"Oracle23aiClient:Inserted {len(items)} items into collection '{collection_name}'.")
            except Exception as e:
                connection.rollback()
                print(f"Error during insert: {e}")
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
        with self.get_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    for item in items:
                        vector_blob = self._vector_to_blob(item["vector"])
                        metadata_json = self._metadata_to_json(item["metadata"])
                        
                        cursor.execute("""
                            MERGE INTO document_chunk d
                            USING (SELECT :id as id FROM dual) s
                            ON (d.id = s.id)
                            WHEN MATCHED THEN
                                UPDATE SET 
                                    collection_name = :collection_name,
                                    text = :text,
                                    vmetadata = :metadata,
                                    vector = :vector
                            WHEN NOT MATCHED THEN
                                INSERT (id, collection_name, text, vmetadata, vector)
                                VALUES (:id, :collection_name, :text, :metadata, :vector)
                        """, {
                            'id': item["id"],
                            'collection_name': collection_name,
                            'text': item["text"],
                            'metadata': metadata_json,
                            'vector': vector_blob,                    
                            'id': item["id"],
                            'collection_name': collection_name,
                            'text': item["text"],
                            'metadata': metadata_json,
                            'vector': vector_blob
                        })
                
                connection.commit()
                print(f"Upserted {len(items)} items into collection '{collection_name}'.")
            except Exception as e:
                connection.rollback()
                print(f"Error during upsert: {e}")
                raise

    def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        limit: Optional[int] = None
    ) -> Optional[SearchResult]:
        """
        Search for similar vectors in the database.
        
        Performs vector similarity search using cosine distance.
        
        Args:
            collection_name (str): Name of the collection to search
            vectors (List[List[float]]): Query vectors to find similar items for
            limit (Optional[int]): Maximum number of results to return per query
            
        Returns:
            Optional[SearchResult]: Search results containing ids, distances, documents, and metadata
            
        Example:
            >>> client = Oracle23aiClient()
            >>> query_vector = [0.1, 0.2, 0.3, ...]  # Must match VECTOR_LENGTH
            >>> results = client.search("my_collection", [query_vector], limit=5)
            >>> if results:
            ...     print(f"Found {len(results.ids[0])} matches")
            ...     for i, (id, dist) in enumerate(zip(results.ids[0], results.distances[0])):
            ...         print(f"Match {i+1}: id={id}, distance={dist}")
        """
        print(f"Oracle23aiClient:Searching items from collection '{collection_name}'.")
        try:
            if not vectors:
                return None
            
            limit = limit or 10
            num_queries = len(vectors)
            
            ids = [[] for _ in range(num_queries)]
            distances = [[] for _ in range(num_queries)]
            documents = [[] for _ in range(num_queries)]
            metadatas = [[] for _ in range(num_queries)]
            
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    for qid, vector in enumerate(vectors):
                        vector_blob = self._vector_to_blob(vector)
                        
                        cursor.execute("""
                            SELECT dc.id, dc.text, 
                                JSON_SERIALIZE(dc.vmetadata) as vmetadata,
                                VECTOR_DISTANCE(dc.vector, :query_vector, COSINE) as distance
                            FROM document_chunk dc
                            WHERE dc.collection_name = :collection_name
                            ORDER BY VECTOR_DISTANCE(dc.vector, :query_vector, COSINE)
                            FETCH APPROX FIRST :limit ROWS ONLY
                        """, {
                            'query_vector': vector_blob,
                            'collection_name': collection_name,
                            'limit': limit
                        })
                        
                        results = cursor.fetchall()
                        
                        for row in results:
                            ids[qid].append(row[0])
                            documents[qid].append(row[1].read() if isinstance(row[1], oracledb.LOB) else str(row[1]))
                            metadatas[qid].append(row[2].read() if isinstance(row[2], oracledb.LOB) else row[2])
                            distances[qid].append(float(row[3]))
            
            return SearchResult(
                ids=ids,
                distances=distances,
                documents=documents,
                metadatas=metadatas
            )
        except Exception as e:
            print(f"Error during search: {e}")
            import traceback
            print(traceback.format_exc())
            return None

    def query(
        self, 
        collection_name: str, 
        filter: Dict[str, Any], 
        limit: Optional[int] = None
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
        print(f"Oracle23aiClient:Querying items from collection '{collection_name}'.")
        try:
            limit = limit or 100
            
            query = """
                SELECT id, text, vmetadata
                FROM document_chunk
                WHERE collection_name = :collection_name
            """
            
            params = {'collection_name': collection_name}
            
            for i, (key, value) in enumerate(filter.items()):
                param_name = f"value_{i}"
                query += f" AND JSON_VALUE(vmetadata, '$.{key}' RETURNING VARCHAR2(4096)) = :{param_name}"
                params[param_name] = str(value)
            
            query += " FETCH FIRST :limit ROWS ONLY"
            params['limit'] = limit
            
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
            
            if not results:
                return None
            
            ids = [[row[0] for row in results]]
            documents = [[row[1].read() if isinstance(row[1], oracledb.LOB) else str(row[1]) for row in results]]
            metadatas = [[row[2].read() if isinstance(row[2], oracledb.LOB) else row[2] for row in results]]
            
            return GetResult(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
        except Exception as e:
            print(f"Error during query: {e}")
            import traceback
            print(traceback.format_exc())
            return None

    def get(
        self, 
        collection_name: str, 
        limit: Optional[int] = None
    ) -> Optional[GetResult]:
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
        try:
            limit = limit or 100
            
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT /*+ MONITOR */ id, text, vmetadata
                        FROM document_chunk
                        WHERE collection_name = :collection_name
                        FETCH FIRST :limit ROWS ONLY
                    """, {
                        'collection_name': collection_name,
                        'limit': limit
                    })
                    
                    results = cursor.fetchall()
            
            if not results:
                return None
            
            ids = [[row[0] for row in results]]
            documents = [[row[1].read() if isinstance(row[1], oracledb.LOB) else str(row[1]) for row in results]]
            metadatas = [[row[2].read() if isinstance(row[2], oracledb.LOB) else row[2] for row in results]]
            
            return GetResult(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
        except Exception as e:
            print(f"Error during get: {e}")
            import traceback
            print(traceback.format_exc())
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
        try:
            query = "DELETE FROM document_chunk WHERE collection_name = :collection_name"
            params = {'collection_name': collection_name}
            
            if ids:
                id_list = ",".join([f"'{id}'" for id in ids])
                query += f" AND id IN ({id_list})"
            
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
            
            print(f"Deleted {deleted} items from collection '{collection_name}'.")
        except Exception as e:
            print(f"Error during delete: {e}")
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
        try:
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM document_chunk")
                    deleted = cursor.rowcount
                connection.commit()
            print(f"Reset complete. Deleted {deleted} items from 'document_chunk' table.")
        except Exception as e:
            print(f"Error during reset: {e}")
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
            if hasattr(self, 'pool') and self.pool:
                self.pool.close()
            print("Oracle Vector Search connection pool closed.")
        except Exception as e:
            print(f"Error closing connection pool: {e}")

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
                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM document_chunk
                        WHERE collection_name = :collection_name
                        FETCH FIRST 1 ROWS ONLY
                    """, {'collection_name': collection_name})
                    
                    count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"Error checking collection existence: {e}")
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
        self.delete(collection_name)
        print(f"Collection '{collection_name}' deleted.")