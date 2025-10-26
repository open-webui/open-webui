# Retrieval/Vector Directory

This directory defines the core abstraction layer for vector database operations in Open WebUI. It provides the interface (abstract base class) that all vector database implementations must follow, data models for vector items and search results, a factory pattern for instantiating the correct backend, and type definitions for supported vector databases.

## Purpose

This directory provides:
- **Unified Interface**: VectorDBBase abstract class defines contract for all vector DB implementations
- **Data Models**: Pydantic models for type-safe vector operations (VectorItem, SearchResult, GetResult)
- **Factory Pattern**: Single point for instantiating vector database clients
- **Type Safety**: Enum for supported vector database types
- **Backend Agnostic**: Application code doesn't need to know which vector DB is used

## Files in This Directory

### main.py
**Purpose:** Core data models and abstract base class defining the interface all vector database implementations must follow.

**Key Data Models:**

#### VectorItem
**Purpose:** Represents a single vector with associated metadata for insertion into vector DB.

**Schema:**
```python
class VectorItem(BaseModel):
    id: str                    # Unique identifier (e.g., "file-123-chunk-0")
    text: str                  # Original text content
    vector: List[float | int]  # Embedding vector (typically 384 or 1536 dimensions)
    metadata: Any              # Flexible metadata (file_id, page, source, etc.)
```

**Usage:**
```python
item = VectorItem(
    id="doc-123-chunk-5",
    text="Open WebUI is a self-hosted web interface...",
    vector=[0.123, 0.456, ...],  # 384-dim embedding
    metadata={
        "file_id": "doc-123",
        "page": 5,
        "source": "document.pdf",
        "chunk_index": 5
    }
)
```

**Used by:**
- `retrieval/utils.py` - Constructs VectorItems before insertion
- All vector DB implementations - Accept List[VectorItem] for insert/upsert

#### GetResult
**Purpose:** Result format for query operations (metadata filtering without vector search).

**Schema:**
```python
class GetResult(BaseModel):
    ids: Optional[List[List[str]]]          # Document IDs (nested for batch queries)
    documents: Optional[List[List[str]]]     # Text content
    metadatas: Optional[List[List[Any]]]     # Metadata objects
```

**Nested Lists:** Results are nested to support batch queries:
- Outer list: Multiple queries
- Inner list: Results per query

**Usage:**
```python
# Query by metadata filter
result = vector_db.query(
    collection_name="file-123",
    filter={"page": 5}
)

# Result format:
# result.ids = [["doc-123-chunk-0", "doc-123-chunk-1"]]
# result.documents = [["First chunk text", "Second chunk text"]]
# result.metadatas = [[{"page": 5, "file_id": "123"}, {"page": 5, ...}]]
```

#### SearchResult
**Purpose:** Result format for vector similarity search (extends GetResult with distance scores).

**Schema:**
```python
class SearchResult(GetResult):
    distances: Optional[List[List[float | int]]]  # Similarity/distance scores
```

**Distance Semantics:**
- **Lower is better** for distance metrics (L2, Euclidean)
- **Higher is better** for similarity metrics (Cosine, Inner Product)
- Each implementation normalizes to [0, 1] where **higher = more similar**

**Usage:**
```python
# Vector similarity search
result = vector_db.search(
    collection_name="file-123",
    vectors=[[0.123, 0.456, ...]],  # Query embedding
    limit=10
)

# Result format:
# result.ids = [["doc-123-chunk-5", "doc-123-chunk-8", ...]]
# result.distances = [[0.92, 0.87, 0.85, ...]]  # Normalized similarity
```

**Used by:**
- `retrieval/utils.py` - Processes search results
- All vector DB implementations - Return SearchResult from search()

### VectorDBBase (Abstract Base Class)
**Purpose:** Interface contract that all vector database implementations must implement.

**Abstract Methods:**

#### Collection Management
```python
@abstractmethod
def has_collection(self, collection_name: str) -> bool:
    """Check if collection exists"""
    pass

@abstractmethod
def delete_collection(self, collection_name: str) -> None:
    """Delete entire collection"""
    pass
```

#### Vector Operations
```python
@abstractmethod
def insert(self, collection_name: str, items: List[VectorItem]) -> None:
    """Insert new vectors (fail if IDs exist)"""
    pass

@abstractmethod
def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
    """Insert or update vectors (replace if IDs exist)"""
    pass
```

#### Search Operations
```python
@abstractmethod
def search(
    self,
    collection_name: str,
    vectors: List[List[Union[float, int]]],
    limit: int
) -> Optional[SearchResult]:
    """Vector similarity search"""
    pass

@abstractmethod
def query(
    self,
    collection_name: str,
    filter: Dict,
    limit: Optional[int] = None
) -> Optional[GetResult]:
    """Metadata filter query (no vector search)"""
    pass

@abstractmethod
def get(self, collection_name: str) -> Optional[GetResult]:
    """Retrieve all vectors from collection"""
    pass
```

#### Delete Operations
```python
@abstractmethod
def delete(
    self,
    collection_name: str,
    ids: Optional[List[str]] = None,
    filter: Optional[Dict] = None,
) -> None:
    """Delete vectors by ID or metadata filter"""
    pass

@abstractmethod
def reset(self) -> None:
    """Reset entire vector database (delete all collections)"""
    pass
```

**Contract Guarantees:**
- All implementations must provide these methods
- Return types must match
- Distance normalization to [0, 1] similarity range
- Thread-safe operations (where applicable)

**Implemented by:**
- `vector/dbs/chroma.py` - ChromaClient
- `vector/dbs/qdrant.py` - QdrantClient
- `vector/dbs/pinecone.py` - PineconeClient
- `vector/dbs/milvus.py` - MilvusClient
- `vector/dbs/elasticsearch.py` - ElasticsearchClient
- `vector/dbs/opensearch.py` - OpenSearchClient
- `vector/dbs/pgvector.py` - PgVectorClient
- `vector/dbs/qdrant_multitenancy.py` - QdrantMultiTenancyClient

### factory.py
**Purpose:** Factory function and singleton instance for vector database client.

**Key Components:**

#### get_vector() Factory Function
**Purpose:** Instantiate appropriate vector database client based on type.

**Signature:**
```python
def get_vector(vector_db_type: VectorType):
    """
    Factory function to get vector database client.

    Args:
        vector_db_type: VectorType enum value

    Returns:
        VectorDBBase implementation instance

    Raises:
        ValueError: If vector_db_type not supported
    """
```

**Implementation:**
```python
def get_vector(vector_db_type: VectorType):
    if vector_db_type == VectorType.CHROMA:
        from .dbs.chroma import ChromaClient
        return ChromaClient()
    elif vector_db_type == VectorType.QDRANT:
        from .dbs.qdrant import QdrantClient
        return QdrantClient()
    elif vector_db_type == VectorType.PINECONE:
        from .dbs.pinecone import PineconeClient
        return PineconeClient()
    # ... etc for all 8 backends
    else:
        raise ValueError(f"Unsupported vector DB: {vector_db_type}")
```

**Lazy Import Pattern:** Imports are inside function to avoid loading unused dependencies.

#### VECTOR_DB_CLIENT Singleton
**Purpose:** Global singleton instance of vector database client.

**Initialization:**
```python
from open_webui.env import VECTOR_DB

# Parse VECTOR_DB environment variable to VectorType
vector_type = VectorType[VECTOR_DB.upper()]

# Instantiate singleton
VECTOR_DB_CLIENT = get_vector(vector_type)
```

**Used by:**
- `retrieval/utils.py` - All RAG operations use this singleton
- `routers/retrieval.py` - Directly accesses for special operations

**Benefits:**
- Single instance (connection pooling)
- Configuration-driven (via env variable)
- No need to pass client around

### type.py
**Purpose:** Enum defining supported vector database types.

**VectorType Enum:**
```python
from enum import Enum

class VectorType(str, Enum):
    CHROMA = "chroma"
    QDRANT = "qdrant"
    PINECONE = "pinecone"
    MILVUS = "milvus"
    ELASTICSEARCH = "elasticsearch"
    OPENSEARCH = "opensearch"
    PGVECTOR = "pgvector"
    QDRANT_MULTITENANCY = "qdrant_multitenancy"
```

**Usage:**
```python
# Configuration
VECTOR_DB = "chroma"  # From environment

# Parse to enum
vector_type = VectorType[VECTOR_DB.upper()]

# Use in factory
client = get_vector(vector_type)
```

**Benefits:**
- Type safety (can't typo database name)
- IDE autocomplete
- Enum-based switch statements
- Clear list of supported backends

## Architecture & Patterns

### Abstract Base Class Pattern
**Purpose:** Define interface contract that all implementations must follow.

**Benefits:**
- **Polymorphism**: Application code works with VectorDBBase, not specific implementation
- **Testability**: Easy to mock for testing
- **Extensibility**: Add new backends by implementing interface
- **Type Safety**: Python enforces all abstract methods implemented

**Example:**
```python
# Application code uses abstract interface
vector_db: VectorDBBase = get_vector(VectorType.CHROMA)
vector_db.insert(collection_name, items)  # Works with any implementation

# Later, switch to Qdrant (no code changes)
vector_db: VectorDBBase = get_vector(VectorType.QDRANT)
vector_db.insert(collection_name, items)  # Same interface
```

### Factory Pattern
**Purpose:** Centralize object creation logic.

**Benefits:**
- **Single Responsibility**: Factory handles creation, implementations handle behavior
- **Configuration-Driven**: Runtime selection based on config
- **Lazy Loading**: Only import needed implementation
- **Testability**: Easy to inject mock factory

### Singleton Pattern
**Purpose:** Single global instance of vector database client.

**Benefits:**
- **Resource Efficiency**: Single connection pool
- **Consistency**: All code uses same client
- **Convenience**: No need to pass client as parameter

**Trade-offs:**
- Global state (harder to test)
- Can't easily use multiple vector DBs simultaneously
- Initialization order dependencies

### Pydantic Models for Data
**Purpose:** Type-safe, validated data structures.

**Benefits:**
- **Validation**: Automatic type checking and validation
- **Documentation**: Schema serves as documentation
- **Serialization**: Easy JSON conversion
- **IDE Support**: Autocomplete and type hints

**Example:**
```python
# Validation
item = VectorItem(
    id="123",
    text="Hello",
    vector=[0.1, 0.2],
    metadata={"page": 1}
)  # ✓ Valid

item = VectorItem(
    id=123,  # Wrong type
    text="Hello",
    vector="not a list",  # Wrong type
    metadata={"page": 1}
)  # ✗ ValidationError
```

## Integration Points

### retrieval/utils.py → vector/
**Primary Consumer:** Utilities use VECTOR_DB_CLIENT singleton for all operations.

**Example:**
```python
# In retrieval/utils.py
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.retrieval.vector.main import VectorItem

def query_doc(collection_name, query_text):
    # Generate embedding
    embedding = get_embedding_function()(query_text)

    # Search vectors
    results = VECTOR_DB_CLIENT.search(
        collection_name=collection_name,
        vectors=[embedding],
        limit=10
    )

    return results
```

### routers/retrieval.py → vector/
**Direct Access:** Some endpoints need direct vector DB operations.

**Example:**
```python
# In routers/retrieval.py
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

@app.delete("/api/retrieval/collection/{collection_name}")
async def delete_collection(collection_name: str):
    VECTOR_DB_CLIENT.delete_collection(collection_name)
    return {"status": "success"}
```

### vector/dbs/* → vector/main.py
**Implementation:** All concrete implementations inherit from VectorDBBase.

**Example:**
```python
# In vector/dbs/chroma.py
from open_webui.retrieval.vector.main import VectorDBBase, VectorItem, SearchResult

class ChromaClient(VectorDBBase):
    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        # ChromaDB-specific implementation
        collection = self.client.get_or_create_collection(collection_name)
        collection.upsert(
            ids=[item.id for item in items],
            embeddings=[item.vector for item in items],
            documents=[item.text for item in items],
            metadatas=[item.metadata for item in items]
        )

    def search(self, collection_name, vectors, limit) -> SearchResult:
        # ChromaDB-specific implementation
        # ...
```

### env.py → vector/factory.py
**Configuration:** Environment variable determines which backend to use.

**Flow:**
```
VECTOR_DB environment variable (e.g., "chroma")
  ↓
Imported by factory.py
  ↓
Parsed to VectorType enum
  ↓
Passed to get_vector() factory
  ↓
Returns appropriate implementation
  ↓
Stored in VECTOR_DB_CLIENT singleton
```

## Key Workflows

### Application Startup
```
1. Import factory.py
2. Read VECTOR_DB environment variable
3. Parse to VectorType enum
4. Call get_vector(vector_type)
5. Lazy import appropriate implementation module
6. Instantiate client (connects to vector DB)
7. Store in VECTOR_DB_CLIENT singleton
8. Application ready to use vector operations
```

### Vector Insertion
```
1. Document loaded and chunked
2. Generate embeddings for chunks
3. Create VectorItem for each chunk:
   VectorItem(
       id=f"{file_id}-chunk-{i}",
       text=chunk.text,
       vector=embedding,
       metadata={...}
   )
4. Call VECTOR_DB_CLIENT.insert(collection_name, items)
5. Implementation-specific insertion logic executes
6. Vectors stored in vector DB
```

### Vector Search
```
1. User sends query
2. Generate query embedding
3. Call VECTOR_DB_CLIENT.search(collection, [embedding], k=10)
4. Implementation executes similarity search
5. Returns SearchResult with:
   - ids: Document IDs
   - documents: Text content
   - metadatas: Metadata objects
   - distances: Similarity scores (normalized to [0,1])
6. Application processes results (reranking, formatting)
7. Results injected into LLM context
```

### Switching Vector Databases
```
1. Change VECTOR_DB environment variable (e.g., "chroma" → "qdrant")
2. Migrate data:
   a. Export all vectors from old DB
   b. Insert all vectors into new DB
3. Restart application
4. Factory creates new implementation instance
5. All code works unchanged (same interface)
```

## Important Notes

### Critical Dependencies
- **Pydantic**: Data models
- **Python 3.11+**: Union types (float | int)
- **Vector DB libraries**: Specific to each implementation (loaded lazily)

### Configuration
- `VECTOR_DB` environment variable (required)
- Must match VectorType enum value (case-insensitive)
- Invalid value raises ValueError at startup

### Distance Normalization Contract
**Critical:** All implementations must normalize distances to [0, 1] similarity range:
- **0.0** = Completely dissimilar
- **1.0** = Identical
- **Higher = More similar**

This ensures consistent behavior across backends regardless of underlying distance metric.

### Thread Safety
- Implementations should be thread-safe where possible
- Singleton VECTOR_DB_CLIENT accessed from multiple threads
- Connection pooling recommended

### Error Handling
- Abstract methods should not catch exceptions (let implementations decide)
- Implementations should raise descriptive errors
- Application code handles retries and fallbacks

### Testing Considerations
- Mock VectorDBBase for unit tests
- Use in-memory implementations for fast tests
- Test each implementation separately for integration tests
- Verify distance normalization consistency across backends

### Performance Considerations
- Batch operations preferred (insert list of items vs. one-by-one)
- Connection pooling critical for performance
- Lazy imports reduce startup time
- Singleton reduces connection overhead

### Adding New Vector Database
To add support for a new vector database:

1. Create implementation file in `vector/dbs/new_db.py`
2. Inherit from VectorDBBase
3. Implement all abstract methods
4. Add VectorType enum value in `type.py`
5. Add case in factory.py `get_vector()` function
6. Test all operations
7. Document configuration in dbs/CLAUDE.md
