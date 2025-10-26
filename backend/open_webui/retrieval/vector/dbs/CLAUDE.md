# Retrieval/Vector/DBs Directory

This directory contains concrete implementations of the VectorDBBase interface for 8 different vector database backends. Each implementation provides a unified interface for storing, searching, and managing vector embeddings, allowing Open WebUI to work seamlessly with various vector database solutions based on deployment needs, scale requirements, and infrastructure preferences.

## Purpose

This directory provides:
- **Multiple Backend Support**: 8 vector database implementations
- **Unified Interface**: All implement VectorDBBase abstract class
- **Flexible Deployment**: Choose backend based on infrastructure (local, cloud, on-premise)
- **Performance Optimization**: Each backend optimized for specific use cases
- **Vendor Independence**: Switch backends without code changes

## Supported Vector Databases

### chroma.py - ChromaDB
**Purpose:** Default vector database, excellent for local development and small-medium deployments.

**Deployment Modes:**
- **Persistent Local**: SQLite-backed storage on disk
- **HTTP Client**: Connect to remote Chroma server

**Configuration:**
```python
CHROMA_CLIENT = "http"  # or "persistent"
CHROMA_HTTP_HOST = "localhost"
CHROMA_HTTP_PORT = 8000
CHROMA_DATA_PATH = "./data/vector_db/chroma"
```

**Key Features:**
- Simple setup (no external dependencies for local mode)
- Built-in metadata filtering
- Collection management
- Distance metrics: L2, cosine, inner product

**Key Methods:**
- `insert(collection_name, items)` - Batch upsert vectors
- `search(collection_name, vectors, k)` - Similarity search
- `query(collection_name, filter)` - Metadata filtering
- `delete_collection(name)` - Remove entire collection
- `has_collection(name)` - Check if collection exists
- `delete_items(collection_name, ids)` - Delete specific items

**Distance Normalization:**
```python
# Chroma returns L2 or cosine distance
# Normalize to [0,1] similarity:
if distance_metric == "cosine":
    similarity = 1 - distance
elif distance_metric == "l2":
    similarity = 1 / (1 + distance)
```

**Pros:**
- Easy setup
- Fast local development
- Good documentation
- Active community

**Cons:**
- Limited scalability (compared to Milvus/Pinecone)
- Single-node (HTTP mode supports distributed)
- Basic indexing (no advanced index types)

**Used by:**
- Default backend for new installations
- Development environments
- Small to medium deployments (<100M vectors)

### qdrant.py - Qdrant
**Purpose:** High-performance vector database with advanced filtering capabilities.

**Deployment Modes:**
- **Local**: In-memory or disk-backed
- **Cloud**: Qdrant Cloud service
- **Self-hosted**: Docker/Kubernetes deployment

**Configuration:**
```python
QDRANT_URL = "http://localhost:6333"
QDRANT_API_KEY = "your-api-key"  # Optional
```

**Key Features:**
- **Payload Filtering**: Rich metadata filtering with AND/OR/NOT
- **Distance Metrics**: Cosine, Euclidean, Dot product
- **Batch Operations**: Efficient batch uploads
- **Snapshots**: Backup and restore collections
- **Hybrid Search**: Combine vector + keyword search

**Key Methods:** (Same interface as base, plus Qdrant-specific optimizations)
- Batch upload with automatic chunking
- Efficient metadata filtering via payload

**Distance Normalization:**
```python
# Qdrant returns raw scores
# Normalize based on metric:
if distance_metric == "cosine":
    similarity = (score + 1) / 2  # [-1, 1] → [0, 1]
elif distance_metric == "euclid":
    similarity = 1 / (1 + score)
```

**Pros:**
- Excellent performance
- Advanced filtering
- Scalable (horizontal scaling)
- Rich API

**Cons:**
- Requires separate service
- More complex setup than Chroma
- Resource intensive

**Used by:**
- Production deployments
- Large-scale applications (>100M vectors)
- Advanced filtering requirements

### qdrant_multitenancy.py - Qdrant (Multi-Tenant Mode)
**Purpose:** Qdrant implementation with multi-tenancy support via payload filtering.

**Multi-Tenancy Pattern:**
Instead of separate collections per tenant, uses single collection with tenant_id in payload:

```python
{
  "vector": [0.1, 0.2, ...],
  "payload": {
    "tenant_id": "user123",
    "text": "Document content",
    "metadata": {...}
  }
}
```

**Collection Naming:**
All items stored in single collection, tenant separation via filter:

```python
# Insert
client.upsert(
    collection_name="shared_collection",
    points=[{"id": id, "vector": vec, "payload": {"tenant_id": tenant, ...}}]
)

# Search (tenant-isolated)
client.search(
    collection_name="shared_collection",
    query_vector=vec,
    query_filter={"must": [{"key": "tenant_id", "match": {"value": tenant}}]}
)
```

**Pros:**
- Resource efficient (one collection for all tenants)
- Simplified management
- Faster tenant onboarding

**Cons:**
- All tenants share indexes (potential performance impact)
- Tenant data not physically isolated
- Deletion requires filtering (slower)

**Used by:**
- SaaS deployments with many small tenants
- Shared infrastructure environments

### pinecone.py - Pinecone
**Purpose:** Cloud-native vector database with managed infrastructure.

**Deployment:** Cloud-only (no self-hosting)

**Configuration:**
```python
PINECONE_API_KEY = "your-api-key"
PINECONE_ENVIRONMENT = "us-west1-gcp"  # or other region
PINECONE_NAMESPACE = "default"  # Optional namespace for partitioning
```

**Key Features:**
- **Fully Managed**: No infrastructure management
- **Auto-Scaling**: Scales automatically
- **High Availability**: Built-in redundancy
- **gRPC Support**: Fast protocol for large batches
- **Namespaces**: Logical partitioning within index

**Batch Upload Optimization:**
```python
# Pinecone supports parallel batch uploads
def insert(self, collection_name, items):
    batches = chunk_items(items, batch_size=100)

    # Parallel upload
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(self.index.upsert, vectors=batch, namespace=collection_name)
            for batch in batches
        ]
        wait(futures)
```

**gRPC vs HTTP:**
- gRPC: Faster for large batches (>1000 vectors)
- HTTP: Simpler for small operations

**Distance Normalization:**
```python
# Pinecone returns similarity scores in [0,1] or [-1,1]
# Already normalized, minimal processing needed
similarity = score
```

**Pros:**
- Zero infrastructure management
- Excellent scalability
- High performance
- Strong SLA

**Cons:**
- Cloud-only (vendor lock-in)
- Cost (per-vector pricing)
- No self-hosting option
- Regional availability

**Used by:**
- Cloud-native deployments
- High-scale production (>1B vectors)
- Teams without infrastructure expertise

### milvus.py - Milvus
**Purpose:** Enterprise-grade vector database with advanced indexing and massive scale support.

**Deployment Modes:**
- **Standalone**: Single-node for development
- **Cluster**: Distributed for production
- **Cloud**: Zilliz Cloud (managed Milvus)

**Configuration:**
```python
MILVUS_URI = "localhost:19530"
MILVUS_TOKEN = "auth-token"  # Optional
MILVUS_COLLECTION_NAME = "default"
MILVUS_INDEX_TYPE = "IVF_FLAT"  # or HNSW, IVF_SQ8, etc.
```

**Index Types:**
- **FLAT**: Brute force (best accuracy, slow for large datasets)
- **IVF_FLAT**: Inverted file index (balanced)
- **IVF_SQ8**: Scalar quantization (reduced memory)
- **HNSW**: Hierarchical navigable small world (best performance)
- **ANNOY**: Approximate nearest neighbors

**Key Features:**
- **Multiple Index Types**: Choose speed vs accuracy tradeoff
- **Hybrid Search**: Vector + attribute filtering
- **Partitioning**: Physical data partitioning for scale
- **Replication**: High availability
- **GPU Support**: Accelerated search

**Index Configuration:**
```python
index_params = {
    "index_type": "HNSW",
    "metric_type": "L2",
    "params": {"M": 16, "efConstruction": 256}
}
```

**Distance Normalization:**
```python
# Milvus returns distances based on metric type
if metric == "L2":
    similarity = 1 / (1 + distance)
elif metric == "IP":  # Inner product
    similarity = distance  # Already similarity
elif metric == "COSINE":
    similarity = 1 - distance
```

**Pros:**
- Best for massive scale (>10B vectors)
- Advanced indexing options
- Excellent performance
- Strong community

**Cons:**
- Complex setup
- Requires significant resources
- Steep learning curve
- Overkill for small deployments

**Used by:**
- Enterprise deployments
- Massive scale (>10B vectors)
- Performance-critical applications

### elasticsearch.py - Elasticsearch
**Purpose:** Leverage existing Elasticsearch infrastructure for vector search.

**Configuration:**
```python
ELASTICSEARCH_URL = "http://localhost:9200"
ELASTICSEARCH_API_KEY = "api-key"  # Optional
```

**Key Features:**
- **Hybrid Search**: Combine full-text + vector search
- **Existing Infrastructure**: Reuse Elasticsearch cluster
- **Rich Filtering**: Elasticsearch query DSL
- **Aggregations**: Combine search with analytics

**Vector Field Configuration:**
```python
mapping = {
    "properties": {
        "vector": {
            "type": "dense_vector",
            "dims": 384,  # Embedding dimension
            "index": True,
            "similarity": "cosine"  # or l2_norm, dot_product
        },
        "text": {"type": "text"},
        "metadata": {"type": "object"}
    }
}
```

**kNN Search:**
```python
query = {
    "knn": {
        "field": "vector",
        "query_vector": [0.1, 0.2, ...],
        "k": 10,
        "num_candidates": 100
    }
}
```

**Distance Normalization:**
```python
# Elasticsearch returns scores (higher is better)
# Already normalized by similarity metric
similarity = score
```

**Pros:**
- Leverage existing Elasticsearch
- Powerful hybrid search
- Rich ecosystem
- Familiar query language

**Cons:**
- Vector search not primary feature
- Performance lags specialized DBs
- Resource intensive
- Complexity

**Used by:**
- Teams with existing Elasticsearch
- Hybrid search requirements (text + vectors)
- Unified search platform

### opensearch.py - OpenSearch
**Purpose:** Open-source alternative to Elasticsearch with vector search capabilities.

**Configuration:**
```python
OPENSEARCH_URL = "http://localhost:9200"
OPENSEARCH_API_KEY = "api-key"  # Optional
```

**Key Features:**
Same as Elasticsearch (OpenSearch is Elasticsearch fork):
- k-NN plugin for vector search
- Hybrid search
- Rich filtering
- Aggregations

**k-NN Plugin:**
```python
mapping = {
    "properties": {
        "vector": {
            "type": "knn_vector",
            "dimension": 384,
            "method": {
                "name": "hnsw",
                "space_type": "cosinesimil",
                "engine": "nmslib"
            }
        }
    }
}
```

**Distance Normalization:** Same as Elasticsearch

**Pros:**
- Open-source (no licensing issues)
- Similar to Elasticsearch
- Active development
- AWS OpenSearch Service available

**Cons:**
- Same limitations as Elasticsearch
- Smaller community than Elasticsearch
- Feature parity concerns

**Used by:**
- Teams avoiding Elastic license
- AWS infrastructure
- Open-source preference

### pgvector.py - PostgreSQL + pgvector
**Purpose:** Add vector search to existing PostgreSQL database.

**Configuration:**
```python
PGVECTOR_DB_URL = "postgresql://user:pass@localhost/db"
PGVECTOR_COLLECTION_NAME = "embeddings"
PGVECTOR_ENCRYPT_VECTORS = True  # Optional encryption
```

**Key Features:**
- **Unified Database**: Store vectors + relational data in PostgreSQL
- **ACID Transactions**: Full transactional support
- **SQL Queries**: Combine vector search with SQL
- **Encryption**: Optional vector encryption at rest

**Table Schema:**
```sql
CREATE TABLE embeddings (
    id TEXT PRIMARY KEY,
    collection_name TEXT,
    vector vector(384),  -- pgvector type
    document TEXT,
    metadata JSONB,
    created_at TIMESTAMP
);

CREATE INDEX ON embeddings USING ivfflat (vector vector_cosine_ops);
```

**Index Types:**
- **ivfflat**: Inverted file with flat quantization
- **hnsw**: Hierarchical navigable small world (PostgreSQL 15+)

**Encryption:**
If enabled, vectors encrypted using Fernet symmetric encryption before storage.

**Distance Operators:**
- `<->` : L2 distance
- `<#>` : Negative inner product
- `<=>` : Cosine distance

**Distance Normalization:**
```python
# pgvector returns distances
# Normalize based on operator
if operator == "<=>":  # Cosine
    similarity = 1 - distance
else:  # L2
    similarity = 1 / (1 + distance)
```

**Pros:**
- Reuse PostgreSQL infrastructure
- ACID transactions
- SQL integration
- Mature ecosystem

**Cons:**
- Limited scale (compared to specialized DBs)
- Performance not optimal for large datasets
- Index building can be slow

**Used by:**
- Teams with existing PostgreSQL
- Small to medium scale
- Transactional requirements

## Architecture & Patterns

### Factory Pattern
All implementations instantiated via factory:

```python
# In vector/factory.py
def get_vector_db(db_type: VectorType):
    if db_type == VectorType.CHROMA:
        return ChromaClient()
    elif db_type == VectorType.QDRANT:
        return QdrantClient()
    # ... etc
```

### Unified Interface
All implementations conform to VectorDBBase:

```python
class VectorDBBase(ABC):
    @abstractmethod
    def insert(self, collection_name, items): pass

    @abstractmethod
    def search(self, collection_name, vectors, k): pass

    @abstractmethod
    def query(self, collection_name, filter): pass

    @abstractmethod
    def delete_collection(self, name): pass
```

### Distance Normalization Pattern
Each implementation normalizes distances to [0,1] similarity range for consistency across backends.

### Batch Upload Optimization
Most implementations support batch operations:
- Pinecone: Parallel batch uploads via ThreadPoolExecutor
- Qdrant: Automatic batching with configurable size
- Milvus: Bulk insert operations
- Others: Batch via list comprehension

## Integration Points

### retrieval/vector/factory.py → dbs/
Factory selects implementation:

```python
VECTOR_DB_CLIENT = get_vector_db(VectorType[VECTOR_DB])
```

### retrieval/utils.py → dbs/
Utilities use VECTOR_DB_CLIENT singleton:

```python
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

def query_doc(collection_name, query):
    embedding = get_embedding_function()(query)
    results = VECTOR_DB_CLIENT.search(collection_name, [embedding], k=10)
    return results
```

### routers/retrieval.py → dbs/
Routes insert and query vectors:

```python
@app.post("/api/retrieval/process/file")
async def process_file(file_id, collection_name):
    # ... load and chunk file ...

    items = [
        VectorItem(id=id, vector=vec, text=text, metadata=meta)
        for id, vec, text, meta in zip(...)
    ]

    VECTOR_DB_CLIENT.insert(collection_name, items)
```

## Important Notes

### Critical Dependencies
Each backend has specific dependencies:
- **Chroma**: `chromadb`
- **Qdrant**: `qdrant-client`
- **Pinecone**: `pinecone-client`
- **Milvus**: `pymilvus`
- **Elasticsearch**: `elasticsearch`
- **OpenSearch**: `opensearch-py`
- **pgvector**: `psycopg2`, `pgvector`

### Configuration
Backend selected via `VECTOR_DB` environment variable:
```bash
export VECTOR_DB=chroma  # or qdrant, pinecone, milvus, etc.
```

### Performance Comparison
Approximate throughput (vectors/sec) for 384-dim embeddings:

| Backend | Insert | Search (k=10) | Scale |
|---------|--------|---------------|-------|
| Chroma | 1K/s | 100 QPS | <100M |
| Qdrant | 10K/s | 1K QPS | <1B |
| Pinecone | 100K/s | 10K QPS | >1B |
| Milvus | 100K/s | 10K QPS | >10B |
| Elasticsearch | 5K/s | 500 QPS | <500M |
| OpenSearch | 5K/s | 500 QPS | <500M |
| pgvector | 1K/s | 50 QPS | <10M |

(Approximate, depends on hardware/configuration)

### Migration Between Backends
Changing vector databases requires:
1. Export all collections from old backend
2. Re-insert all vectors into new backend
3. Update VECTOR_DB environment variable
4. Restart application

No automated migration tool exists.

### Testing Considerations
- Mock vector DB for unit tests
- Use Docker Compose for integration tests with real DBs
- Test each backend separately (requires different containers)
- Verify distance normalization consistency
- Test batch upload performance

### Security Considerations
- **Pinecone**: API key rotation
- **Qdrant**: API key authentication
- **Elasticsearch/OpenSearch**: TLS, authentication
- **pgvector**: Database credentials, optional encryption
- **Network**: Firewall rules for database ports
