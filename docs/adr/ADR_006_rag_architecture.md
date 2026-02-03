# ADR 006: RAG Architecture and Vector Database Strategy

> **Status:** Accepted
> **Date:** Foundational decision
> **Deciders:** Open WebUI core team

## Context

Open WebUI supports Retrieval-Augmented Generation (RAG) to enhance AI responses with user-provided documents. Requirements include:
- Upload and process various document types (PDF, DOCX, etc.)
- Store document embeddings for semantic search
- Retrieve relevant context at query time
- Support multiple deployment scales (local to enterprise)

Key challenges:
- Document parsing varies by format
- Embedding models have different capabilities
- Vector databases have different operational characteristics
- Query latency impacts user experience

## Decision

Implement a **pluggable RAG architecture** with:
1. **Document loaders:** Format-specific parsers returning LangChain Documents
2. **Embedding models:** Configurable sentence-transformer models
3. **Vector databases:** Pluggable backends (ChromaDB default)
4. **Hybrid search:** Combine semantic (vector) with keyword (BM25) search

Key design choices:
- **ChromaDB default:** Zero-config embedded database for simple deployments
- **External DB support:** Qdrant, Pinecone, Weaviate, Milvus for scale
- **Lazy loading:** Embedding models loaded on first use
- **Chunking strategy:** Configurable chunk size and overlap

## Consequences

### Positive
- **Flexibility:** Users choose vector DB based on scale and requirements
- **Simple start:** ChromaDB requires no external infrastructure
- **Quality:** Hybrid search improves retrieval relevance
- **Extensibility:** New loaders/DBs can be added without core changes

### Negative
- **Complexity:** Multiple vector DB integrations to maintain
- **Inconsistency:** Different DBs have different query capabilities
- **Resource usage:** Embedding models require significant memory
- **Latency:** Document processing can be slow for large files

### Neutral
- Need for chunking strategy tuning per use case
- Trade-offs between retrieval precision and recall

## Implementation

**RAG Pipeline:**

```
Document Upload
       │
       ▼
┌─────────────────┐
│ Document Loader │ (PDF, DOCX, TXT, etc.)
│ /retrieval/     │
│  loaders/       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Chunking     │ (size: 1500, overlap: 100)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Embedding     │ (sentence-transformers)
│    Model        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vector Store   │ (ChromaDB, Qdrant, etc.)
└─────────────────┘

Query Time:
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│Vector │ │ BM25  │ (hybrid search)
│Search │ │Search │
└───┬───┘ └───┬───┘
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│   Reranking     │ (optional)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Inject  │ → LLM Prompt
└─────────────────┘
```

**Configuration:**

```python
# Environment variables
RAG_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DB = "chroma"  # or "qdrant", "pinecone", etc.
CHROMA_DATA_PATH = f"{DATA_DIR}/vector_db"

# For external vector DBs
QDRANT_URL = "http://localhost:6333"
PINECONE_API_KEY = "..."
```

**Document loader pattern:**

```python
# retrieval/loaders/main.py
def load_document(file_path: str, file_type: str) -> List[Document]:
    """Load document using appropriate loader."""
    loaders = {
        "pdf": PDFLoader,
        "docx": DocxLoader,
        "txt": TextLoader,
        "md": MarkdownLoader,
        "html": HTMLLoader,
        "youtube": YoutubeLoader,
        # ... more loaders
    }

    loader_class = loaders.get(file_type)
    if not loader_class:
        raise ValueError(f"Unsupported file type: {file_type}")

    loader = loader_class(file_path)
    return loader.load()
```

**Vector DB abstraction:**

```python
# retrieval/vector/factory.py
def get_vector_client(db_type: str):
    """Get configured vector database client."""
    clients = {
        "chroma": ChromaDBClient,
        "qdrant": QdrantClient,
        "pinecone": PineconeClient,
        "weaviate": WeaviateClient,
        "milvus": MilvusClient,
        "opensearch": OpenSearchClient,
    }
    return clients[db_type]()
```

**Embedding generation:**

```python
# Lazy-loaded embedding model
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(RAG_EMBEDDING_MODEL)
    return _embedding_model

def embed_text(text: str) -> List[float]:
    model = get_embedding_model()
    return model.encode(text).tolist()
```

## Supported Vector Databases

| Database | Type | Best For |
|----------|------|----------|
| ChromaDB | Embedded | Personal/small team, simple setup |
| Qdrant | Self-hosted | Production, open-source preference |
| Pinecone | Managed | Serverless, minimal ops |
| Weaviate | Self-hosted | Complex filtering, hybrid search |
| Milvus | Self-hosted | Large scale, high performance |
| OpenSearch | Self-hosted | Existing OpenSearch infrastructure |

## Alternatives Considered

### LangChain Full Stack
- Provides complete RAG pipeline
- Heavy dependency, less control
- Version compatibility issues
- Rejected for being too opinionated

### Custom Vector Search
- SQLite with vector extension
- PostgreSQL pgvector
- Simpler but less capable
- Rejected for limited scalability

### No RAG (External Only)
- Rely on LLM context windows
- Simpler architecture
- Can't handle large document collections
- Rejected as core feature requirement

## Related Documents

- `DIRECTIVE_adding_rag_loader.md` — How to add document loaders
- `DOMAIN_GLOSSARY.md` — RAG, Embedding, Vector Database terms
- `SYSTEM_TOPOLOGY.md` — RAG data flow

---

*Last updated: 2026-02-03*
