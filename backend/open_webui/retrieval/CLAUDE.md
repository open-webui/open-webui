# Backend Retrieval Directory

This directory implements Open WebUI's Retrieval-Augmented Generation (RAG) system, providing document processing, embedding generation, vector storage, web search, and semantic retrieval capabilities to augment LLM responses with contextual information.

## Directory Structure

### loaders/ - Document Content Extraction
Converts various file formats into LangChain Document objects.

**Key Files:**
- `main.py` - Core Loader class (strategy pattern for format selection)
- `youtube.py` - YouTube transcript extraction via youtube-transcript-api
- `tavily.py` - Tavily Extract API for web content
- `mistral.py` - Mistral OCR with retry logic
- `datalab_marker.py` - Datalab Marker for complex PDFs
- `external_document.py`, `external_web.py` - External service integration

**Supported Engines:**
- Tika (Apache Tika server)
- Docling (microservice)
- Datalab Marker (API)
- Mistral OCR (API)
- Azure Document Intelligence
- LangChain built-in (PDF, Word, Excel, HTML, etc.)

**Used by:**
- `routers/retrieval.py` - process_file() endpoint

**Returns:**
- List[Document] with page_content and metadata

### vector/ - Vector Database Abstraction
Pluggable interface supporting 8 vector database backends.

**Key Files:**
- `main.py` - VectorDBBase abstract class, VectorItem/SearchResult/GetResult models
- `factory.py` - VECTOR_DB_CLIENT singleton, Vector.get_vector() factory
- `type.py` - VectorType enum

**vector/dbs/ Implementations:**
- `chroma.py` - ChromaDB (local/HTTP)
- `qdrant.py` + `qdrant_multitenancy.py` - Qdrant with optional multi-tenant mode
- `pinecone.py` - Pinecone (cloud, with gRPC and parallel batching)
- `milvus.py` - Milvus (configurable index types)
- `elasticsearch.py` - Elasticsearch dense_vector
- `opensearch.py` - OpenSearch KNN
- `pgvector.py` - PostgreSQL pgvector (with optional encryption)

**Used by:**
- `routers/retrieval.py` - Inserts embeddings, queries collections
- `retrieval/utils.py` - VectorSearchRetriever, query helpers

**Key Methods:**
- `insert(collection_name, items)` - Add vectors
- `search(collection_name, vectors, k)` - Similarity search
- `query(collection_name, filter)` - Metadata filtering
- `delete_collection(name)` - Remove collection

### web/ - Web Search Integration
Provides 21 search engine integrations and web content loading.

**Search Providers:**
- Free: DuckDuckGo, SearXNG, YaCy
- Commercial: Brave, Google PSE, Kagi, Bing, Tavily, Serper, SerpStack, etc.
- Self-hosted: SearXNG, YaCy

**Web Loaders:**
- `SafeWebBaseLoader` - Async HTTP with SSL verification
- `SafePlaywrightURLLoader` - Browser automation for dynamic content
- `SafeFireCrawlLoader` - FireCrawl scraping service
- `SafeTavilyLoader` - Tavily content extraction
- `ExternalWebLoader` - Custom external service

**Used by:**
- `routers/retrieval.py` - process_web_search() endpoint

**Returns:**
- List[SearchResult] with link, title, snippet
- List[Document] after web loading

### utils.py - Core RAG Utilities
Main orchestration and embedding functions.

**Key Functions:**
- `get_embedding_function()` - Factory for local/OpenAI/Azure/Ollama embeddings
- `get_reranking_function()` - Optional cross-encoder reranking
- `query_doc()` - Single collection vector search
- `query_doc_with_hybrid_search()` - BM25 + vector ensemble
- `query_collection()` - Multi-collection parallel search
- `get_sources_from_items()` - Main orchestrator (files/notes/collections → searchable sources)
- `generate_embeddings()` - Unified embedding dispatcher

**Used by:**
- `utils/middleware.py` - chat_completion_files_handler() calls get_sources_from_items()
- `routers/retrieval.py` - Query endpoints

**Uses:**
- `vector/factory.py` - VECTOR_DB_CLIENT for search
- `models/files.py`, `models/knowledge.py`, `models/notes.py` - Content access

## Architecture & Patterns

### Document Processing Pipeline
```
File Upload
  ↓
Loader.load(file_path, content_type) → Extract text
  ↓
Text Splitter (Recursive/Token/Markdown) → Chunks
  ↓
get_embedding_function()(...) → Generate embeddings
  ↓
VECTOR_DB_CLIENT.insert(collection, items) → Store vectors
```

### Query Pipeline
```
User Query
  ↓
get_embedding_function()(query_text) → Query embedding
  ↓
VECTOR_DB_CLIENT.search(collection, vector, k) → Top-k results
  ↓
Optional: RerankCompressor → Rerank by relevance
  ↓
SearchResult with documents + distances
```

### Hybrid Search Pattern
```
BM25Retriever (keyword search)
           +
VectorSearchRetriever (semantic search)
           ↓
EnsembleRetriever (weighted combination)
           ↓
ContextualCompressionRetriever (reranking)
           ↓
Deduplicated results
```

### Factory Pattern for Backends
```python
# Configuration-driven selection
VECTOR_DB = "chroma"  # or qdrant, pinecone, etc.

# Singleton initialization
VECTOR_DB_CLIENT = Vector.get_vector(VectorType[VECTOR_DB])

# Uniform interface
VECTOR_DB_CLIENT.insert(...)
VECTOR_DB_CLIENT.search(...)
```

## Integration Points

### Frontend RAG Workflow
```
User uploads PDF
  ↓
POST /api/files (FormData)
  ↓
Storage.upload_file() → Disk/Cloud storage
  ↓
Files.insert_new_file() → Database record
  ↓
process_file(file_id, collection_name)
  ↓
Loader extracts text
  ↓
Chunks embedded and stored in vector DB
  ↓
Frontend: User enables file in chat
  ↓
get_sources_from_items() queries vector DB
  ↓
Results injected into LLM context
```

### Chat Completion with RAG
```
POST /api/chat/completions
  ↓
Middleware: chat_completion_files_handler()
  ↓
get_sources_from_items(files, collections, query)
  ↓
For each file:
  - Full context mode: Include entire file
  - Retrieval mode: query_doc() → Top-k chunks
  ↓
Sources formatted and added to system prompt
  ↓
LLM generates response with context
```

### Web Search Integration
```
POST /api/retrieval/web/search
  ↓
search_web() calls provider (Brave, DuckDuckGo, etc.)
  ↓
Extract URLs from SearchResult[]
  ↓
get_web_loader() loads page content
  ↓
Optional: Embed pages into collection
  ↓
Return documents for LLM context
```

### Knowledge Base Workflow
```
Admin creates knowledge base
  ↓
POST /api/knowledge (name, description)
  ↓
Knowledge.insert_new_knowledge()
  ↓
Add files: POST /api/knowledge/{id}/file/add
  ↓
process_file(file_id, collection_name=knowledge_id)
  ↓
Embeddings stored under knowledge_id collection
  ↓
Chat query: query_collection([knowledge_id], query)
```

## Key Workflows

### Embedding Generation
```
Text → get_embedding_function() → Callable
  ↓
Local: sentence-transformers model
OR
OpenAI: POST https://api.openai.com/v1/embeddings
OR
Azure: POST {endpoint}/openai/deployments/{model}/embeddings
OR
Ollama: POST http://ollama:11434/api/embeddings
  ↓
Returns: List[float] (embedding vector)
```

### Vector Database Backend Selection
Configured via `VECTOR_DB` environment variable:
- **Chroma** (default) - Simple, local/HTTP
- **Qdrant** - High performance, optional multitenancy
- **Pinecone** - Cloud-only, scalable
- **Milvus** - Enterprise-grade, configurable indexes
- **PgVector** - PostgreSQL extension, optional encryption
- **Elasticsearch/OpenSearch** - Full-text + vector hybrid

Distance normalization: All backends normalize to [0,1] range for consistency.

### Collection Naming Conventions
- Files: `file-{file_id}`
- Knowledge bases: `{knowledge_id}`
- User memories: `user-memory-{user_id}`
- Web search: `web-search-{query_hash}`

### Reranking Pipeline (Optional)
```
Initial retrieval: Top-100 results
  ↓
Reranking model scores each (query, document) pair
  ↓
Sort by relevance score
  ↓
Threshold filtering (min relevance score)
  ↓
Return top-k reranked results
```

## Important Notes

**Critical Dependencies:**
- Embedding model must be configured before use (RAG_EMBEDDING_ENGINE)
- Vector database must be accessible (VECTOR_DB configuration)
- Collection names must match between insert and query operations
- File paths resolved via Storage.get_file() (always returns local path)

**Performance Considerations:**
- Batch embedding for efficiency (RAG_EMBEDDING_BATCH_SIZE)
- Hybrid search slower due to full collection retrieval for BM25
- Large knowledge bases benefit from reranking
- Vector DB cold start can be slow on first search

**Security:**
- Access control enforced at router level, not vector DB
- Knowledge bases have access_control field
- Files linked to knowledge bases inherit permissions
- Web content sanitization via DOMPurify

**Configuration Gotchas:**
- Embedding dimension must match across model and vector DB
- Changing embedding model requires re-indexing all collections
- Collection deletion irreversible (no backup mechanism)
- Prefix support for asymmetric search (RAG_EMBEDDING_QUERY_PREFIX)

**Best Practices:**
- Use knowledge bases for grouping related documents
- Reindex after embedding model changes (reindexKnowledgeFiles)
- Monitor vector DB storage growth
- Configure appropriate chunk size (default 800 tokens, 400 overlap)
- Use hybrid search for better recall on keyword-heavy queries
