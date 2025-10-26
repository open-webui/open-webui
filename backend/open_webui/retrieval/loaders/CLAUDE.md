# Retrieval/Loaders Directory

This directory implements document content extraction for Open WebUI's RAG system, converting various file formats (PDF, Word, Excel, HTML, etc.) into LangChain Document objects that can be chunked, embedded, and stored in vector databases. It provides a unified interface for loading documents from multiple sources and formats using different extraction engines (Tika, Docling, Mistral OCR, etc.).

## Files in This Directory

### main.py
**Purpose:** Core document loader with strategy pattern for selecting appropriate loader based on file type and configured engine.

**Key Classes:**

#### Loader
Main orchestrator class that selects and executes appropriate loader.

**Constructor Parameters:**
- `engine` - Loader engine name ("tika", "docling", "langchain", "mistral", "datalab_marker")
- `file_path` - Local file path
- `mime_type` - MIME type (optional, auto-detected if not provided)
- `file_id` - File database ID (optional)
- `config` - Engine-specific configuration (optional)

**Key Method:**
```python
def load(self) -> list[Document]:
    """Extract text content and return LangChain Documents"""
    pass
```

**Loader Selection Logic:**
```
if engine == "tika":
    return TikaLoader(...)
elif engine == "docling":
    return DoclingLoader(...)
elif engine == "mistral":
    return MistralLoader(...) if is_pdf else fallback
elif engine == "datalab_marker":
    return DatalabMarkerLoader(...) if is_pdf else fallback
elif engine == "azure":
    return AzureAIDocumentIntelligenceLoader(...)
else:
    # LangChain built-in loaders
    if mime_type == "application/pdf":
        return PyPDFLoader(file_path)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return Docx2txtLoader(file_path)
    # ... etc
```

#### TikaLoader
**Purpose:** Load documents via Apache Tika server (supports 100+ formats).

**Configuration:**
- `TIKA_SERVER_URL` - Tika server endpoint (e.g., http://tika:9998)

**Supported Formats:** PDF, Word, Excel, PowerPoint, images (with OCR), email formats, etc.

**Method:**
```python
def load(self) -> list[Document]:
    # POST file to Tika server
    # Parse JSON/XML response
    # Extract text and metadata
    # Return Document objects
```

**Pros:**
- Supports widest range of formats
- Robust metadata extraction
- Handles complex documents well

**Cons:**
- Requires separate Tika server (external dependency)
- Slower than native parsers
- Image extraction limited

#### DoclingLoader
**Purpose:** Load documents via Docling microservice (specialized for scientific PDFs).

**Configuration:**
- `DOCLING_URL` - Docling service endpoint

**Supported Formats:** PDF (with excellent table/figure extraction)

**Features:**
- Superior table extraction
- Preserves document structure
- Markdown output format
- Mathematical formula support

**Method:**
```python
def load(self) -> list[Document]:
    # POST file to Docling service
    # Receive markdown response
    # Parse into Document objects
    # Preserve structure (headers, tables, lists)
```

**Pros:**
- Best for academic/technical documents
- Excellent table extraction
- Preserves formatting

**Cons:**
- Requires separate service
- PDF-only
- Slower processing

#### LangChain Built-in Loaders
**Purpose:** Use LangChain's native document loaders (no external dependencies).

**Supported Loaders:**
- `PyPDFLoader` - PDF documents
- `Docx2txtLoader` - Word documents (.docx)
- `UnstructuredExcelLoader` - Excel spreadsheets
- `UnstructuredPowerPointLoader` - PowerPoint presentations
- `CSVLoader` - CSV files
- `BSHTMLLoader` - HTML files
- `TextLoader` - Plain text files
- `UnstructuredEPubLoader` - eBooks
- `UnstructuredODTLoader` - OpenDocument text
- `UnstructuredXMLLoader` - XML files
- `UnstructuredRSTLoader` - reStructuredText
- `OutlookMessageLoader` - Outlook emails (.msg)
- `YoutubeLoader` - YouTube transcripts (via youtube-transcript-api)

**Code File Extensions:** Also handles code files as text (see `known_source_ext` list: py, js, java, etc.)

**Pros:**
- No external dependencies
- Fast loading
- Built-in

**Cons:**
- Less robust than Tika
- Limited OCR support
- Basic metadata extraction

**Used by:**
- `routers/retrieval.py` - process_file() endpoint
- Default fallback when specialized loaders unavailable

### mistral.py
**Purpose:** Mistral AI OCR loader for PDFs using Mistral's multimodal models.

**Key Class:**

#### MistralLoader
**Purpose:** Extract text from PDFs using Mistral AI's vision model for high-quality OCR.

**Configuration:**
- `MISTRAL_OCR_API_KEY` - Mistral API key
- `MISTRAL_OCR_MODEL` - Model name (default: "pixtral-12b-2409")

**Method:**
```python
def load(self) -> list[Document]:
    # Convert PDF pages to images
    # For each page image:
    #   - Encode as base64
    #   - POST to Mistral chat completions
    #   - Extract text from response
    # Return Document per page
```

**Features:**
- High-quality OCR via vision model
- Retry logic with exponential backoff
- Per-page processing (maintains page structure)
- Configurable retry parameters

**Retry Configuration:**
- Max retries: 3
- Backoff multiplier: 2
- Initial delay: 1 second

**Pros:**
- Excellent OCR quality (better than Tesseract)
- Handles complex layouts
- Multi-language support

**Cons:**
- API cost (paid service)
- Slower than local OCR
- Requires API key
- May hit rate limits

**Used by:**
- `main.py` Loader when engine="mistral"

### datalab_marker.py
**Purpose:** Datalab Marker loader for PDFs with advanced layout detection.

**Key Class:**

#### DatalabMarkerLoader
**Purpose:** Extract text from PDFs using Datalab Marker service (excellent for tables and complex layouts).

**Configuration:**
- `DATALAB_MARKER_API_URL` - Marker service endpoint

**Method:**
```python
def load(self) -> list[Document]:
    # POST PDF file to Marker service
    # Receive markdown response with preserved structure
    # Parse into Document objects
    # Include page numbers in metadata
```

**Features:**
- Superior table extraction
- Layout preservation
- Page number tracking
- Markdown output

**Pros:**
- Best table extraction quality
- Preserves document structure
- Fast processing

**Cons:**
- Requires external service
- PDF-only
- Less common than Tika

**Used by:**
- `main.py` Loader when engine="datalab_marker"

### youtube.py
**Purpose:** YouTube video transcript extraction.

**Key Function:**
```python
def load_youtube_transcript(url, language="en") -> list[Document]:
    """Extract transcript from YouTube video"""
    # Parse video ID from URL
    # Fetch transcript via youtube-transcript-api
    # Return Document with text and metadata
```

**Features:**
- Multiple language support
- Auto-generated transcript fallback
- Timestamp preservation (optional)

**Metadata Included:**
- Video title
- Video ID
- Channel
- Duration
- Language

**Used by:**
- `routers/retrieval.py` - process_web_search() when URL is YouTube

### tavily.py
**Purpose:** Tavily Extract API for web content extraction.

**Key Class:**

#### TavilyExtractLoader
**Purpose:** Extract clean content from web URLs using Tavily's extraction service.

**Configuration:**
- `TAVILY_API_KEY` - Tavily API key

**Method:**
```python
def load(urls: list[str]) -> list[Document]:
    # POST URLs to Tavily Extract API
    # Receive cleaned content
    # Return Document per URL
```

**Features:**
- Removes ads and navigation
- Extracts main content
- Handles JavaScript-heavy sites
- Batch URL processing

**Pros:**
- Clean content extraction
- Handles dynamic content
- Fast processing

**Cons:**
- API cost (paid service)
- Requires API key
- Rate limits

**Used by:**
- `routers/retrieval.py` - Web search content loading

### external_document.py
**Purpose:** Load documents via external custom service.

**Key Class:**

#### ExternalDocumentLoader
**Purpose:** Delegate document loading to external HTTP service.

**Configuration:**
- `EXTERNAL_DOCUMENT_LOADER_URL` - External service endpoint

**Method:**
```python
def load(self) -> list[Document]:
    # POST file to external service
    # Expect JSON response with documents
    # Parse and return Documents
```

**Expected Response Format:**
```json
{
  "documents": [
    {
      "page_content": "Text content",
      "metadata": {"page": 1, "source": "doc.pdf"}
    }
  ]
}
```

**Use Case:** Custom document processing pipelines (e.g., proprietary OCR, specialized parsers)

### external_web.py
**Purpose:** Load web content via external custom service.

**Key Class:**

#### ExternalWebLoader
**Purpose:** Delegate web content extraction to external HTTP service.

**Configuration:**
- `EXTERNAL_WEB_LOADER_URL` - External service endpoint

**Method:**
```python
def load(urls: list[str]) -> list[Document]:
    # POST URLs to external service
    # Expect JSON response with documents
    # Parse and return Documents
```

**Use Case:** Custom web scraping infrastructure (e.g., browser farm, custom proxies)

## Architecture & Patterns

### Strategy Pattern
Loader class selects appropriate loader based on engine and file type:

```python
class Loader:
    def __init__(self, engine, file_path, mime_type):
        self.engine = engine
        self.file_path = file_path
        self.mime_type = mime_type

    def load(self):
        if self.engine == "tika":
            return TikaLoader(...).load()
        elif self.engine == "mistral":
            return MistralLoader(...).load()
        # ... etc
```

Benefits:
- Easy to add new loaders
- Consistent interface
- Runtime engine selection

### Fallback Chain
If specialized loader fails or unavailable, fall back to LangChain built-ins:

```
Try: MistralLoader
  ↓ (if fails or unavailable)
Try: TikaLoader
  ↓ (if fails or unavailable)
Try: PyPDFLoader (LangChain)
  ↓ (if fails)
Return error
```

### Unified Output Format
All loaders return `list[Document]`:

```python
Document(
    page_content="Extracted text content",
    metadata={
        "source": "file.pdf",
        "page": 1,
        "total_pages": 10,
        # ... other metadata
    }
)
```

This enables consistent downstream processing (chunking, embedding).

### Configuration-Driven Selection
Loader engine configured via environment variable:

```bash
export RAG_DOCUMENT_LOADER="mistral"  # or "tika", "docling", etc.
```

Application selects loader at runtime based on configuration.

## Integration Points

### routers/retrieval.py → loaders/
File processing endpoint uses loaders:

```python
# In routers/retrieval.py
@app.post("/api/retrieval/process/file")
async def process_file(file_id: str, collection_name: str):
    # Get file metadata from database
    file = Files.get_file_by_id(file_id)

    # Download file to local path (if cloud storage)
    local_path = Storage.get_file(file.path)

    # Load document
    loader = Loader(
        engine=RAG_DOCUMENT_LOADER,
        file_path=local_path,
        mime_type=file.meta.get("content_type")
    )
    documents = loader.load()

    # Chunk documents
    text_splitter = RecursiveCharacterTextSplitter(...)
    chunks = text_splitter.split_documents(documents)

    # Generate embeddings
    embeddings = get_embedding_function()(...)

    # Insert into vector database
    VECTOR_DB_CLIENT.insert(collection_name, items)
```

### storage/provider.py → loaders/
Loaders receive local file paths:

```python
# Storage provider always returns local path
local_path = Storage.get_file(file.path)

# Loader reads from local filesystem
loader = Loader(file_path=local_path, ...)
```

Even for cloud storage (S3, GCS, Azure), files downloaded to local cache before loading.

### loaders/ → LangChain
Most loaders wrap LangChain document loaders:

```python
# In main.py
from langchain_community.document_loaders import PyPDFLoader

def load_pdf_langchain(file_path):
    loader = PyPDFLoader(file_path)
    return loader.load()
```

### loaders/ → External Services
Specialized loaders call external APIs:

```python
# Mistral OCR
response = requests.post(
    "https://api.mistral.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {MISTRAL_OCR_API_KEY}"},
    json={...}
)

# Tika
response = requests.put(
    f"{TIKA_SERVER_URL}/tika",
    data=file_bytes,
    headers={"Accept": "application/json"}
)
```

## Key Workflows

### PDF Loading with Mistral OCR
```
1. User uploads PDF
2. POST /api/retrieval/process/file
3. Loader engine="mistral"
4. MistralLoader instantiated
5. Convert PDF pages to images (pdf2image)
6. For each page:
   a. Encode image as base64
   b. POST to Mistral API with vision model
   c. Extract text from response
   d. Create Document(page_content=text, metadata={page: i})
7. Retry with exponential backoff if rate limited
8. Return list[Document] (one per page)
9. Continue to chunking and embedding
```

### Word Document Loading (LangChain)
```
1. User uploads .docx
2. POST /api/retrieval/process/file
3. MIME type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
4. Loader selects Docx2txtLoader
5. Docx2txtLoader reads .docx file
6. Extracts text (ignoring formatting)
7. Returns single Document
8. Continue to chunking and embedding
```

### YouTube Transcript Loading
```
1. User provides YouTube URL
2. POST /api/retrieval/web/search or direct URL
3. Detect YouTube URL
4. load_youtube_transcript(url)
5. Parse video ID from URL
6. Fetch transcript via youtube-transcript-api
7. If not available, try auto-generated
8. Return Document with transcript text
9. Include metadata (title, channel, duration)
10. Embed and store in vector database
```

### Tika Server Loading (Multi-Format)
```
1. User uploads any supported file (PDF, Excel, PPT, etc.)
2. engine="tika"
3. TikaLoader reads file bytes
4. PUT request to Tika server /tika endpoint
5. Tika extracts text and metadata
6. Parse JSON response
7. Return Document with content and metadata
8. Handle errors (timeout, server unavailable)
9. Fallback to LangChain if Tika fails
```

## Important Notes

### Critical Dependencies
- **LangChain Community** - Most built-in loaders
- **python-magic** or **python-magic-bin** - MIME type detection
- **pdf2image** + **poppler** - PDF to image conversion (for OCR loaders)
- **youtube-transcript-api** - YouTube transcripts
- External services require API keys and network access

### Configuration
All loaders configured via environment variables:
- `RAG_DOCUMENT_LOADER` - Default loader engine
- `TIKA_SERVER_URL` - Tika server endpoint
- `DOCLING_URL` - Docling service endpoint
- `MISTRAL_OCR_API_KEY` - Mistral API key
- `MISTRAL_OCR_MODEL` - Mistral model name
- `DATALAB_MARKER_API_URL` - Marker service endpoint
- `TAVILY_API_KEY` - Tavily API key

### Performance Considerations
- **Local loaders** (LangChain) fastest (10-100ms per file)
- **Tika** moderate (100-500ms per file)
- **OCR loaders** (Mistral, Marker) slowest (1-10s per page)
- Large PDFs can take minutes with OCR
- Consider async processing for large batches

### Error Handling
All loaders should handle errors gracefully:
- File not found → Clear error message
- Unsupported format → Fallback to TextLoader
- External service unavailable → Retry or fallback
- Timeout → Configurable timeout limits
- Rate limits → Exponential backoff

### File Type Detection
MIME type detection:
1. Check file metadata (if available)
2. Use python-magic (libmagic)
3. Fall back to file extension

Always validate MIME type before loading.

### Memory Management
Large files can cause memory issues:
- Stream file reading when possible
- Process pages/chunks incrementally
- Clear intermediate data structures
- Monitor memory usage for OCR loaders

### Security Considerations
- Validate file paths (prevent directory traversal)
- Sanitize external API responses
- Rate limit external API calls (prevent DoS)
- Validate file sizes before loading
- Scan uploaded files for malware (not implemented)

### Testing Considerations
- Mock external services (Tika, Mistral, etc.)
- Test with variety of file formats
- Test error conditions (corrupted files, timeouts)
- Verify metadata extraction
- Test fallback mechanisms
