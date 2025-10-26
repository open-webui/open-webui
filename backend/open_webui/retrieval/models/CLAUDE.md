# Retrieval/Models Directory

This directory implements reranking models for improving RAG search result relevance. Reranking is a two-stage retrieval process: first retrieve many candidates via fast vector search, then rerank those candidates using more sophisticated (but slower) models that better capture query-document relevance. This significantly improves the quality of context provided to LLMs.

## Purpose

This directory provides:
- **Relevance Refinement**: Improve ranking of search results beyond simple vector similarity
- **Multiple Backends**: Support for local models (ColBERT) and external reranking services
- **Unified Interface**: BaseReranker abstract class for all reranking implementations
- **Performance Trade-off**: Balance between speed (vector search) and accuracy (reranking)

## Reranking Concept

### Why Reranking?

**Vector Search Limitations:**
- Simple cosine similarity doesn't capture complex semantic relationships
- Embedding models compress meaning into fixed-size vectors (information loss)
- Query-document interaction not modeled (embeddings created independently)

**Reranking Benefits:**
- Cross-attention between query and document (contextual scoring)
- More sophisticated models (BERT-based, transformer-based)
- Significantly better relevance (15-30% improvement in MRR@10)

**Trade-off:**
- Vector search: Fast (milliseconds), moderate accuracy
- Reranking: Slower (seconds), high accuracy
- Solution: Search for top-100, rerank to top-10

### Two-Stage Retrieval Pipeline

```
User Query
  ↓
1. FAST RETRIEVAL (Vector Search)
   - Generate query embedding
   - Search vector DB for top-100 candidates
   - Time: ~10-50ms
  ↓
100 Candidate Documents
  ↓
2. RERANKING (Cross-Encoder)
   - Score each (query, document) pair
   - Sort by relevance score
   - Select top-10
   - Time: ~100-500ms
  ↓
10 Highest-Quality Results
  ↓
Inject into LLM Context
```

## Files in This Directory

### base_reranker.py
**Purpose:** Abstract base class defining the interface for all reranking implementations.

**BaseReranker Class:**
```python
class BaseReranker(ABC):
    @abstractmethod
    def predict(self, sentences: List[Tuple[str, str]]) -> Optional[List[float]]:
        """
        Rerank query-document pairs.

        Args:
            sentences: List of (query, document) tuples

        Returns:
            List of relevance scores (higher = more relevant)
            Returns None if reranking fails
        """
        pass
```

**Input Format:**
```python
sentences = [
    ("What is Open WebUI?", "Open WebUI is a self-hosted web interface..."),
    ("What is Open WebUI?", "LangChain is a framework for developing..."),
    ("What is Open WebUI?", "Python is a high-level programming language..."),
]
```

**Output Format:**
```python
scores = [0.95, 0.42, 0.15]  # Relevance scores (higher = more relevant)
```

**Used by:**
- `retrieval/utils.py` - get_reranking_function() factory
- Implementations: ColBERT, ExternalReranker

### colbert.py
**Purpose:** Local ColBERT reranking model implementation.

**ColBERT Model:**
- **Late Interaction Architecture**: Query and document encoded separately, then interact at token level
- **MaxSim Operation**: Maximum similarity between query tokens and document tokens
- **High Quality**: State-of-the-art reranking performance
- **GPU Acceleration**: Runs efficiently on GPU

**Key Class: ColBERT**

**Constructor:**
```python
def __init__(self, name, **kwargs):
    """
    Args:
        name: Model name/path (e.g., "colbert-ir/colbertv2.0")
        kwargs: Additional config (env="docker" for Docker workaround)
    """
```

**Configuration:**
- Model loaded from HuggingFace or local path
- Automatically detects CUDA availability
- Docker-specific workaround for torch extensions

**Key Method:**
```python
def predict(self, sentences: List[Tuple[str, str]]) -> Optional[List[float]]:
    """
    Rerank using ColBERT MaxSim scoring.

    Process:
    1. Extract query and documents from tuples
    2. Encode query into token embeddings
    3. Encode each document into token embeddings
    4. Calculate MaxSim score for each pair
    5. Return scores
    """
```

**MaxSim Calculation:**
```python
def calculate_similarity_scores(query_embeddings, document_embeddings):
    """
    MaxSim: For each query token, find max similarity with any document token.
    Then average across all query tokens.

    Shape:
    - query_embeddings: (1, num_query_tokens, embedding_dim)
    - document_embeddings: (num_docs, num_doc_tokens, embedding_dim)

    Returns:
    - scores: (num_docs,) relevance scores
    """
```

**Performance:**
- GPU: ~100-200 pairs/second
- CPU: ~10-20 pairs/second
- Memory: ~2-4 GB (model size)

**Pros:**
- Excellent reranking quality
- Local (no API costs)
- GPU acceleration
- Open-source

**Cons:**
- Requires GPU for good performance
- Large model size (~400 MB)
- Slower than simple cross-encoders
- Memory intensive

**Used by:**
- `retrieval/utils.py` - When RAG_RERANKING_MODEL configured as ColBERT

**Configuration:**
- `RAG_RERANKING_MODEL` - Model name or path
- Requires: `colbert-ai`, `torch`

### external.py
**Purpose:** External reranking service client (e.g., Jina AI Reranker API, Cohere Rerank).

**Key Class: ExternalReranker**

**Constructor:**
```python
def __init__(self, api_key: str, url: str, model: str):
    """
    Args:
        api_key: API key for authentication
        url: Reranking service endpoint (default: http://localhost:8080/v1/rerank)
        model: Model identifier (default: "reranker")
    """
```

**Key Method:**
```python
def predict(self, sentences: List[Tuple[str, str]], user=None) -> Optional[List[float]]:
    """
    Rerank using external API.

    Process:
    1. Extract query and documents
    2. Build API request payload
    3. POST to external service
    4. Parse relevance scores from response
    5. Return scores in original order
    """
```

**API Request Format:**
```python
payload = {
    "model": "reranker",
    "query": "What is Open WebUI?",
    "documents": [
        "Open WebUI is a self-hosted web interface...",
        "LangChain is a framework...",
        "Python is a programming language..."
    ],
    "top_n": 3  # Return all with scores
}
```

**API Response Format:**
```python
{
    "results": [
        {"index": 0, "relevance_score": 0.95},
        {"index": 1, "relevance_score": 0.42},
        {"index": 2, "relevance_score": 0.15}
    ]
}
```

**User Context Forwarding:**
If `ENABLE_FORWARD_USER_INFO_HEADERS` enabled, includes user context:
```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "X-OpenWebUI-User-Name": user.name,
    "X-OpenWebUI-User-Id": user.id,
    "X-OpenWebUI-User-Email": user.email,
    "X-OpenWebUI-User-Role": user.role
}
```

**Compatible Services:**
- **Jina AI Reranker API** - jina-reranker-v1-base-en
- **Cohere Rerank** - rerank-english-v2.0
- **Custom Services** - Any API implementing the format above

**Pros:**
- No local model loading
- Scalable (managed service)
- Fast API calls
- No GPU required

**Cons:**
- API costs (per request)
- Network latency
- Rate limits
- Privacy concerns (data sent to external service)

**Used by:**
- `retrieval/utils.py` - When RAG_RERANKING_MODEL configured as external URL

**Configuration:**
- `RAG_RERANKING_MODEL_EXTERNAL_API_KEY` - API key
- `RAG_RERANKING_MODEL_EXTERNAL_URL` - Service endpoint
- `RAG_RERANKING_MODEL` - Model name

## Architecture & Patterns

### Abstract Base Class Pattern
**Purpose:** Unified interface for all reranking implementations.

**Benefits:**
- Easy to add new rerankers (inherit from BaseReranker)
- Application code doesn't depend on specific implementation
- Testable (mock BaseReranker)

### Factory Pattern (in retrieval/utils.py)
**Purpose:** Select reranker based on configuration.

```python
def get_reranking_function():
    model_name = RAG_RERANKING_MODEL

    if "colbert" in model_name.lower():
        return ColBERT(name=model_name)
    elif "http://" in model_name or "https://" in model_name:
        return ExternalReranker(
            api_key=RAG_RERANKING_MODEL_EXTERNAL_API_KEY,
            url=model_name
        )
    else:
        # Default: Cross-encoder model
        return CrossEncoder(model_name)
```

### Two-Stage Retrieval Pattern
**Purpose:** Balance speed and accuracy.

**Implementation:**
```python
# Stage 1: Fast vector search (top-100)
initial_results = VECTOR_DB_CLIENT.search(
    collection_name=collection,
    vectors=[query_embedding],
    limit=100  # Over-retrieve
)

# Stage 2: Reranking (top-10)
if reranker:
    query = user_query
    docs = [r.document for r in initial_results]
    sentences = [(query, doc) for doc in docs]

    scores = reranker.predict(sentences)

    # Sort by reranked scores
    reranked_results = sorted(
        zip(initial_results, scores),
        key=lambda x: x[1],
        reverse=True
    )[:10]  # Top 10 after reranking
```

## Integration Points

### retrieval/utils.py → models/
**Primary Usage:** RAG utilities use reranking models to improve search quality.

```python
# In retrieval/utils.py
from open_webui.retrieval.models.colbert import ColBERT
from open_webui.retrieval.models.external import ExternalReranker

def query_doc_with_hybrid_search(collection_name, query, k):
    # Vector search for top-100
    results = VECTOR_DB_CLIENT.search(collection_name, [query_embedding], limit=100)

    # Reranking
    if RAG_RERANKING_MODEL:
        reranker = get_reranking_function()
        sentences = [(query, doc.text) for doc in results]
        scores = reranker.predict(sentences)

        # Sort by reranked scores
        results = [r for _, r in sorted(zip(scores, results), reverse=True)][:k]

    return results
```

### routers/retrieval.py → models/ (indirect)
**Route Handler:** Reranking applied during query processing.

```python
# In routers/retrieval.py
@app.post("/api/retrieval/query/doc")
async def query_doc(query: str, k: int = 10):
    # Calls retrieval/utils.py which uses reranking
    results = query_doc_with_hybrid_search(collection_name, query, k)
    return results
```

### models/ → External Services
**External Reranker:** Makes HTTP requests to reranking APIs.

```
ExternalReranker.predict()
  ↓
HTTP POST to external service
  ↓
{
  "model": "reranker",
  "query": "...",
  "documents": [...]
}
  ↓
External service (Jina AI, Cohere, custom)
  ↓
{
  "results": [
    {"index": 0, "relevance_score": 0.95},
    ...
  ]
}
  ↓
Parse and return scores
```

## Key Workflows

### Reranking with ColBERT
```
1. User query: "How do I install Open WebUI?"
2. Generate query embedding
3. Vector search: Retrieve top-100 documents
4. Initialize ColBERT reranker:
   - Load model from HuggingFace
   - Move to GPU if available
5. Prepare sentence pairs:
   sentences = [
       ("How do I install Open WebUI?", doc1.text),
       ("How do I install Open WebUI?", doc2.text),
       ...
   ]  # 100 pairs
6. ColBERT.predict(sentences):
   - Encode query tokens
   - Encode document tokens (batch processing)
   - Calculate MaxSim scores
   - Return scores
7. Sort documents by reranked scores
8. Select top-10
9. Inject into LLM context
```

### Reranking with External API
```
1. User query: "What is RAG?"
2. Vector search: Retrieve top-100 documents
3. Initialize ExternalReranker:
   - API key from config
   - URL: https://api.jina.ai/v1/rerank
4. Prepare API request:
   {
     "model": "jina-reranker-v1-base-en",
     "query": "What is RAG?",
     "documents": [doc1.text, doc2.text, ...],
     "top_n": 100
   }
5. POST to API
6. Wait for response (~100-300ms)
7. Parse relevance scores
8. Sort by scores
9. Select top-10
10. Inject into LLM context
```

### Fallback without Reranking
```
1. User query
2. Vector search: Retrieve top-10 directly (no over-retrieval)
3. Results already sorted by vector similarity
4. Inject into LLM context
5. Faster but potentially lower quality
```

## Important Notes

### Critical Dependencies
- **ColBERT**: `colbert-ai`, `torch`, CUDA (optional but recommended)
- **External**: `requests` library
- **Base**: Python 3.11+ (ABC from standard library)

### Configuration
Reranking configured via environment variables:
- `RAG_RERANKING_MODEL` - Model name or URL
  - ColBERT: "colbert-ir/colbertv2.0"
  - External: "https://api.jina.ai/v1/rerank"
  - None: Disable reranking
- `RAG_RERANKING_MODEL_EXTERNAL_API_KEY` - API key for external service
- `ENABLE_FORWARD_USER_INFO_HEADERS` - Forward user context to external service

### Performance Considerations
- **ColBERT GPU**: ~100-200 pairs/sec
- **ColBERT CPU**: ~10-20 pairs/sec
- **External API**: ~100-500ms per batch (network dependent)
- **Memory**: ColBERT ~2-4 GB
- **Recommendation**: Use GPU for ColBERT or external API for production

### Quality Improvements
Typical improvements with reranking:
- **MRR@10**: +15-30% (Mean Reciprocal Rank)
- **NDCG@10**: +10-25% (Normalized Discounted Cumulative Gain)
- **Precision@10**: +20-35%

Real-world impact:
- Fewer irrelevant chunks in LLM context
- Better grounding for answers
- Reduced hallucination

### When to Use Reranking
**Use reranking when:**
- Quality matters more than speed
- Large document collections (>10,000 docs)
- Complex queries requiring nuanced understanding
- Budget allows (GPU or API costs)

**Skip reranking when:**
- Speed critical (real-time requirements)
- Small document collections (<1,000 docs)
- Simple keyword queries
- Limited resources (no GPU, no API budget)

### Error Handling
- ColBERT model loading failure → Log error, return None (fall back to vector-only)
- External API timeout → Log error, return None (fall back to vector-only)
- Invalid scores returned → Log warning, return None
- GPU OOM → Fall back to CPU (automatic in PyTorch)

### Security Considerations
- **External API**: User data sent to third-party service (privacy concern)
- **API Keys**: Store securely in environment variables
- **User Context Headers**: Only forward if explicitly enabled
- **Model Files**: Verify ColBERT model checksum (avoid malicious models)

### Testing Considerations
- Mock BaseReranker for unit tests
- Test with small document sets (avoid long test times)
- Use CPU-only for CI/CD (avoid GPU dependency)
- Test both ColBERT and External implementations
- Verify score ordering (higher = more relevant)

### Monitoring
Track reranking performance:
- Reranking latency (p50, p95, p99)
- Reranking success rate
- Score distribution (detect anomalies)
- GPU utilization (if using ColBERT)
- API error rates (if using external)

### Future Improvements
Potential enhancements:
- Support for more reranking models (Cohere, OpenAI)
- Batch reranking optimization
- Caching reranked results
- Hybrid scoring (vector similarity + reranking)
- Multi-stage reranking (fast reranker → slow reranker)
