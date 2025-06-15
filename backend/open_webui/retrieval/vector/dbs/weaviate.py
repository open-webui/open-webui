import weaviate
import re
import uuid
from typing import Any, Dict, List, Optional, Union

from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)
from open_webui.config import WEAVIATE_HTTP_HOST, WEAVIATE_HTTP_PORT, WEAVIATE_GRPC_PORT


def _convert_uuids_to_strings(obj: Any) -> Any:
    """
    Recursively convert UUID objects to strings in nested data structures.
    
    This function handles:
    - UUID objects -> string
    - Dictionaries with UUID values
    - Lists/Tuples with UUID values
    - Nested combinations of the above
    
    Args:
        obj: Any object that might contain UUIDs
        
    Returns:
        The same object structure with UUIDs converted to strings
    """
    if isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: _convert_uuids_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_convert_uuids_to_strings(item) for item in obj)
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        return obj


class WeaviateClient(VectorDBBase):
    def __init__(self):
        self.url = WEAVIATE_HTTP_HOST
        try:
            self.client = weaviate.connect_to_local(
                host=self.url,
                port=WEAVIATE_HTTP_PORT,
                grpc_port=WEAVIATE_GRPC_PORT,
            )
            self.client.connect()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Weaviate: {e}") from e

    def _sanitize_collection_name(self, collection_name: str) -> str:
        """Sanitize collection name to be a valid Weaviate class name."""
        if not isinstance(collection_name, str) or not collection_name.strip():
            raise ValueError("Collection name must be a non-empty string")

        # Requirements for a valid Weaviate class name:
        # The collection name must begin with a capital letter.
        # The name can only contain letters, numbers, and the underscore (_) character. Spaces are not allowed.

        # Replace hyphens with underscores and keep only alphanumeric characters
        name = re.sub(r'[^a-zA-Z0-9_]', '', collection_name.replace("-", "_"))
        name = name.strip("_")

        if not name:
            raise ValueError("Could not sanitize collection name to be a valid Weaviate class name")

        # Ensure it starts with a letter and is capitalized
        if not name[0].isalpha():
            name = "C" + name
        
        return name[0].upper() + name[1:]

    def has_collection(self, collection_name: str) -> bool:
        sane_collection_name = self._sanitize_collection_name(collection_name)
        return self.client.collections.exists(sane_collection_name)

    def delete_collection(self, collection_name: str) -> None:
        sane_collection_name = self._sanitize_collection_name(collection_name)
        if self.client.collections.exists(sane_collection_name):
            self.client.collections.delete(sane_collection_name)

    def _create_collection(self, collection_name: str) -> None:
        self.client.collections.create(
            name=collection_name,
            vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
            properties=[
                weaviate.classes.config.Property(name="text", data_type=weaviate.classes.config.DataType.TEXT),
            ]
        )

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        sane_collection_name = self._sanitize_collection_name(collection_name)
        if not self.client.collections.exists(sane_collection_name):
            self._create_collection(sane_collection_name)

        collection = self.client.collections.get(sane_collection_name)
        
        with collection.batch.fixed_size(batch_size=100) as batch:
            for item in items:
                # Use item["id"] if it's a valid UUID, otherwise generate one
                item_uuid = None
                if item["id"]:
                    try:
                        # Convert to UUID first to validate, then back to string
                        validated_uuid = uuid.UUID(str(item["id"]))
                        item_uuid = str(validated_uuid)
                    except (ValueError, TypeError):
                        item_uuid = str(uuid.uuid4())
                else:
                    item_uuid = str(uuid.uuid4())
                
                properties = {"text": item["text"]}
                if item["metadata"]:
                    # Convert any UUID objects in metadata to strings
                    clean_metadata = _convert_uuids_to_strings(item["metadata"])
                    properties.update(clean_metadata)
                
                batch.add_object(
                    properties=properties,
                    uuid=item_uuid,
                    vector=item["vector"]
                )

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        sane_collection_name = self._sanitize_collection_name(collection_name)
        if not self.client.collections.exists(sane_collection_name):
            self._create_collection(sane_collection_name)

        collection = self.client.collections.get(sane_collection_name)
        
        with collection.batch.fixed_size(batch_size=100) as batch:
            for item in items:
                # Use item["id"] if provided and valid UUID format
                item_uuid = None
                if item["id"]:
                    try:
                        # Convert to UUID first to validate, then back to string
                        validated_uuid = uuid.UUID(str(item["id"]))
                        item_uuid = str(validated_uuid)
                    except (ValueError, TypeError):
                        pass
                
                properties = {"text": item["text"]}
                if item["metadata"]:
                    # Convert any UUID objects in metadata to strings
                    clean_metadata = _convert_uuids_to_strings(item["metadata"])
                    properties.update(clean_metadata)
                
                batch.add_object(
                    properties=properties,
                    uuid=item_uuid,  # None means Weaviate will auto-generate
                    vector=item["vector"]
                )

    def search(
        self, collection_name: str, vectors: List[List[Union[float, int]]], limit: int
    ) -> Optional[SearchResult]:
        sane_collection_name = self._sanitize_collection_name(collection_name)
        if not self.client.collections.exists(sane_collection_name):
            return None

        collection = self.client.collections.get(sane_collection_name)
        all_ids: List[List[str]] = []
        all_documents: List[List[str]] = []
        all_metadatas: List[List[Any]] = []
        all_distances: List[List[float | int]] = []

        for vector_embedding in vectors:
            try:
                response = collection.query.near_vector(
                    near_vector=vector_embedding,
                    limit=limit,
                    return_metadata=weaviate.classes.query.MetadataQuery(distance=True),
                )
            except Exception:
                # Append empty results for this query vector
                all_ids.append([])
                all_documents.append([])
                all_metadatas.append([])
                all_distances.append([])
                continue
            
            batch_ids: List[str] = []
            batch_documents: List[str] = []
            batch_metadatas: List[Any] = []
            batch_distances: List[float | int] = []

            for obj in response.objects:
                batch_ids.append(str(obj.uuid))
                
                current_properties = dict(obj.properties) if obj.properties else {}
                doc_text = current_properties.pop("text", "") 
                batch_documents.append(doc_text)
                # Convert any UUID objects in metadata to strings
                clean_properties = _convert_uuids_to_strings(current_properties)
                batch_metadatas.append(clean_properties)

                if obj.metadata and obj.metadata.distance is not None:
                    batch_distances.append(obj.metadata.distance)
                else:
                    batch_distances.append(float('inf'))

            all_ids.append(batch_ids)
            all_documents.append(batch_documents)
            all_metadatas.append(batch_metadatas)
            all_distances.append(batch_distances)
        
        return SearchResult(
            ids=all_ids,
            documents=all_documents,
            metadatas=all_metadatas,
            distances=all_distances
        )

    def query(
        self, collection_name: str, filter: Dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        sane_collection_name = self._sanitize_collection_name(collection_name)
        if not self.client.collections.exists(sane_collection_name):
            return None

        collection = self.client.collections.get(sane_collection_name)
        
        # Simple filter handling - only support basic equality
        weaviate_filter = None
        if filter:
            for key, value in filter.items():
                prop_filter = weaviate.classes.query.Filter.by_property(name=key).equal(value)
                if weaviate_filter is None:
                    weaviate_filter = prop_filter
                else:
                    weaviate_filter = weaviate.classes.query.Filter.all_of([weaviate_filter, prop_filter])
        
        try:
            response = collection.query.fetch_objects(
                filters=weaviate_filter,
                limit=limit,
                )
        except Exception:
            return None

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Any] = []

        for obj in response.objects:
            ids.append(str(obj.uuid))
            current_properties = dict(obj.properties) if obj.properties else {}
            doc_text = current_properties.pop("text", "")
            documents.append(doc_text)
            # Convert any UUID objects in metadata to strings
            clean_properties = _convert_uuids_to_strings(current_properties)
            metadatas.append(clean_properties)

        return GetResult(
            ids=[ids],
            documents=[documents],
            metadatas=[metadatas]
        )

    def get(self, collection_name: str) -> Optional[GetResult]:
        sane_collection_name = self._sanitize_collection_name(collection_name)
        if not self.client.collections.exists(sane_collection_name):
            return None

        collection = self.client.collections.get(sane_collection_name)
        
        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Any] = []

        try:
            for item in collection.iterator():
                ids.append(str(item.uuid))
                current_properties = dict(item.properties) if item.properties else {}
                doc_text = current_properties.pop("text", "")
                documents.append(doc_text)
                # Convert any UUID objects in metadata to strings
                clean_properties = _convert_uuids_to_strings(current_properties)
                metadatas.append(clean_properties)
        except Exception:
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

        if not ids:
             return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

        return GetResult(
            ids=[ids],
            documents=[documents],
            metadatas=[metadatas]
        )

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict] = None,
    ) -> None:
        sane_collection_name = self._sanitize_collection_name(collection_name)
        if not self.client.collections.exists(sane_collection_name):
            return

        collection = self.client.collections.get(sane_collection_name)

        try:
            if ids:
                for item_id in ids:
                    collection.data.delete_by_id(uuid=item_id)
            elif filter:
                # Simple filter handling
                weaviate_filter = None
                for key, value in filter.items():
                    prop_filter = weaviate.classes.query.Filter.by_property(name=key).equal(value)
                    if weaviate_filter is None:
                        weaviate_filter = prop_filter
                    else:
                        weaviate_filter = weaviate.classes.query.Filter.all_of([weaviate_filter, prop_filter])
                    
                if weaviate_filter:
                    collection.data.delete_many(where=weaviate_filter)
        except Exception:
            pass

    def reset(self) -> None:
        try:
            all_collections = self.client.collections.list_all()
            for collection_name in all_collections.keys():
                self.client.collections.delete(collection_name)
        except Exception:
            pass
