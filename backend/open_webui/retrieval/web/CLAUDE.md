# Retrieval/Web Directory

This directory implements web search and web content loading for Open WebUI's RAG system, providing integration with 21+ search engines and multiple web content extraction methods. It enables augmenting LLM responses with real-time information from the web through search-then-load or direct URL loading workflows.

## Purpose

This directory provides:
- **Multi-Provider Search**: 21+ search engine integrations (free and commercial)
- **Web Content Loading**: Multiple strategies for extracting clean content from URLs
- **URL Safety**: Validation to prevent SSRF and access to private networks
- **Flexible Configuration**: Easy switching between search providers
- **Test Data**: Mock responses for development and testing

## Architecture Overview

### Two-Stage Web RAG Process

```
User Query
  ↓
1. WEB SEARCH (Search Provider)
   - Send query to search engine
   - Receive list of URLs with snippets
   - Time: ~100-500ms
  ↓
Search Results (URLs + Snippets)
  ↓
2. WEB LOADING (Content Extractor)
   - Load full content from URLs
   - Extract clean text (remove ads, navigation)
   - Time: ~1-5s per URL
  ↓
Documents
  ↓
Embed & Insert into Vector DB (optional)
  OR
Direct injection into LLM context
```

## Directory Structure

### Search Provider Files (21 providers)

Each provider file implements a simple search function following the same pattern:

**Free/Self-Hosted Providers:**
- `duckduckgo.py` - DuckDuckGo search (no API key required)
- `searxng.py` - SearXNG meta-search engine (self-hosted)
- `yacy.py` - YaCy P2P search engine (self-hosted)

**Commercial API Providers:**
- `brave.py` - Brave Search API
- `google_pse.py` - Google Programmable Search Engine
- `bing.py` - Bing Web Search API
- `kagi.py` - Kagi Search API
- `serper.py` - Serper.dev Google Search API
- `serpapi.py` - SerpApi multi-engine wrapper
- `searchapi.py` - SearchAPI.io
- `serpstack.py` - SerpStack
- `serply.py` - Serply.io
- `tavily.py` - Tavily Search API (AI-optimized)
- `exa.py` - Exa (formerly Metaphor) neural search
- `perplexity.py` - Perplexity AI search
- `jina_search.py` - Jina AI Search
- `mojeek.py` - Mojeek Search
- `bocha.py` - Bocha Search
- `sougou.py` - Sougou Search (Chinese)

**Web Scraping Services:**
- `firecrawl.py` - FireCrawl scraping service

**External Integration:**
- `external.py` - Custom external search service

### Common Provider Pattern

All providers follow this structure:

```python
def search(
    query: str,
    count: int = 10,
    api_key: Optional[str] = None,
    **kwargs
) -> list[SearchResult]:
    """
    Search the web for query.

    Args:
        query: Search query string
        count: Number of results to return
        api_key: API key for authentication (if required)
        **kwargs: Provider-specific parameters

    Returns:
        List of SearchResult objects with link, title, snippet
    """
```

**SearchResult Model:**
```python
class SearchResult(BaseModel):
    link: str                    # URL
    title: Optional[str]          # Page title
    snippet: Optional[str]        # Short description/excerpt
```

### utils.py - Web Loading Utilities
**Purpose:** Load and extract content from web URLs with multiple strategies.

**Key Classes:**

#### SafeWebBaseLoader
**Purpose:** Async web page loader with SSL verification and safety checks.

**Features:**
- Async HTTP requests via aiohttp
- SSL certificate verification
- URL validation (prevent SSRF)
- Private IP blocking (configurable)
- Custom headers and proxies
- Metadata extraction (title, description, language)

**Usage:**
```python
loader = SafeWebBaseLoader(
    web_paths=["https://example.com/page"],
    verify_ssl=True
)
documents = await loader.aload()  # Returns List[Document]
```

**Safety Features:**
- DNS resolution check (block private IPs)
- URL validation
- Timeout configuration
- SSL verification

#### SafePlaywrightURLLoader
**Purpose:** Browser-based content loading for JavaScript-heavy sites.

**Features:**
- Headless browser automation (Chromium)
- JavaScript execution
- Dynamic content rendering
- Screenshot capability (optional)
- Custom user agent

**Usage:**
```python
loader = SafePlaywrightURLLoader(
    urls=["https://dynamic-site.com"],
    remove_selectors=["header", "footer", "nav"]
)
documents = loader.load()
```

**Configuration:**
- `PLAYWRIGHT_WS_URL` - Browser WebSocket URL (if using remote browser)
- `PLAYWRIGHT_TIMEOUT` - Page load timeout

**When to Use:**
- Single-page applications (React, Vue, Angular)
- Sites with AJAX content loading
- Sites that block simple HTTP requests
- Sites requiring JavaScript execution

#### SafeFireCrawlLoader
**Purpose:** FireCrawl service integration for advanced web scraping.

**Features:**
- Handles anti-bot protection
- Extracts structured data
- Markdown output format
- Screenshot support

**Configuration:**
- `FIRECRAWL_API_BASE_URL` - FireCrawl service endpoint
- `FIRECRAWL_API_KEY` - API key

#### SafeTavilyLoader
**Purpose:** Tavily Extract API for clean content extraction.

**Features:**
- Removes ads and navigation
- AI-optimized content extraction
- Fast processing
- Batch URL support

**Configuration:**
- `TAVILY_API_KEY` - Tavily API key
- `TAVILY_EXTRACT_DEPTH` - Extraction depth level

#### ExternalWebLoader
**Purpose:** Delegate web loading to external custom service.

**Configuration:**
- `EXTERNAL_WEB_LOADER_URL` - External service endpoint
- `EXTERNAL_WEB_LOADER_API_KEY` - API key

**Use Case:** Custom scraping infrastructure (proxies, browser farms)

### Web Loader Selection

**Engine Selection:**
```python
WEB_LOADER_ENGINE = "playwright"  # or "default", "firecrawl", "tavily", "external"

def get_web_loader(urls: list[str]):
    if WEB_LOADER_ENGINE == "playwright":
        return SafePlaywrightURLLoader(urls)
    elif WEB_LOADER_ENGINE == "firecrawl":
        return SafeFireCrawlLoader(urls)
    elif WEB_LOADER_ENGINE == "tavily":
        return SafeTavilyLoader(urls)
    elif WEB_LOADER_ENGINE == "external":
        return ExternalWebLoader(urls)
    else:  # default
        return SafeWebBaseLoader(web_paths=urls)
```

**When to Use Each:**
- **Default (SafeWebBaseLoader)**: Static sites, fast, no JavaScript
- **Playwright**: Dynamic sites, JavaScript-heavy, SPAs
- **FireCrawl**: Anti-bot protection, advanced scraping
- **Tavily**: Clean content, AI-optimized
- **External**: Custom infrastructure, special requirements

### main.py - Search Orchestrator
**Purpose:** Route search requests to appropriate provider.

**Key Function:**
```python
def search_web(engine: str, query: str, count: int = 10) -> list[SearchResult]:
    """
    Route search to appropriate provider.

    Args:
        engine: Provider name ("brave", "duckduckgo", etc.)
        query: Search query
        count: Number of results

    Returns:
        List of SearchResult objects
    """
    if engine == "brave":
        return brave.search(query, count)
    elif engine == "duckduckgo":
        return duckduckgo.search(query, count)
    # ... etc for all 21 providers
```

### testdata/ - Mock Search Responses
**Purpose:** JSON files with sample search results for each provider.

**Contents:**
- `brave.json` - Brave Search sample response
- `duckduckgo.json` - DuckDuckGo sample response
- `google_pse.json` - Google PSE sample response
- `serper.json` - Serper sample response
- ... (one per provider)

**Usage:**
- Development without API keys
- Testing web search integration
- CI/CD pipeline testing

**Example Format:**
```json
{
  "results": [
    {
      "link": "https://example.com",
      "title": "Example Page",
      "snippet": "This is an example page..."
    }
  ]
}
```

## Integration Points

### routers/retrieval.py → web/
**Web Search Endpoint:** Process web search queries.

```python
# In routers/retrieval.py
from open_webui.retrieval.web.main import search_web
from open_webui.retrieval.web.utils import get_web_loader

@app.post("/api/retrieval/web/search")
async def web_search(query: str, engine: str = "duckduckgo"):
    # Search web
    results = search_web(engine=engine, query=query, count=10)

    # Extract URLs
    urls = [r.link for r in results]

    # Load web content
    loader = get_web_loader(urls)
    documents = await loader.aload()

    # Optionally embed and store
    # ...

    return {"results": results, "documents": documents}
```

### utils/middleware.py → web/
**Chat Completion with Web Search:** Automatically search web when query needs current information.

```python
# In utils/middleware.py
if requires_web_search(query):
    results = search_web(engine=WEB_SEARCH_ENGINE, query=query)
    urls = [r.link for r in results[:3]]  # Top 3 results

    # Load content
    loader = get_web_loader(urls)
    documents = await loader.aload()

    # Inject into LLM context
    context = "\n\n".join([doc.page_content for doc in documents])
    messages = add_web_context_to_messages(messages, context)
```

### web/utils.py → External Services
**Content Loading:** HTTP requests to external APIs or web pages.

```
SafeWebBaseLoader
  ↓
HTTP GET https://example.com
  ↓
Parse HTML (BeautifulSoup)
  ↓
Extract text and metadata
  ↓
Return Document
```

## Key Workflows

### Search-Then-Load Workflow
```
1. User query: "Latest news about AI"
2. Search web: search_web("brave", query, count=5)
3. Brave Search API returns 5 results
4. Extract URLs from results
5. Load content: get_web_loader(urls).aload()
6. SafeWebBaseLoader fetches each URL
7. Extract clean text from HTML
8. Return Documents
9. Generate embeddings (optional)
10. Insert into vector DB OR direct LLM context
```

### Direct URL Loading Workflow
```
1. User provides URL: "https://example.com/article"
2. Validate URL (not private IP, valid format)
3. Select loader based on WEB_LOADER_ENGINE
4. If JavaScript required: SafePlaywrightURLLoader
   Else: SafeWebBaseLoader
5. Load content
6. Extract text
7. Return Document
8. Process for RAG
```

### Dynamic Site Loading Workflow
```
1. URL is SPA (React/Vue app)
2. WEB_LOADER_ENGINE="playwright"
3. SafePlaywrightURLLoader instantiated
4. Connect to headless browser
5. Navigate to URL
6. Wait for JavaScript execution
7. Wait for content load (selectors or timeout)
8. Extract rendered HTML
9. Parse and clean
10. Return Document
```

## Important Notes

### Critical Dependencies
- **All Providers**: `requests` or `aiohttp`
- **DuckDuckGo**: `duckduckgo-search` library
- **Playwright**: `playwright` + `playwright install chromium`
- **LangChain**: `langchain-community` (loaders)

### Configuration
Web search configured via environment variables:
- `WEB_SEARCH_ENGINE` - Default search provider
- `WEB_LOADER_ENGINE` - Default content loader
- `ENABLE_RAG_LOCAL_WEB_FETCH` - Allow/block private IPs
- `API keys` - Per-provider (BRAVE_SEARCH_API_KEY, etc.)

### Search Provider Selection Guide

**Choose based on needs:**
- **Free, no account**: DuckDuckGo, SearXNG (self-hosted)
- **Best quality**: Google PSE, Brave, Perplexity
- **AI-optimized**: Tavily, Exa
- **Privacy**: DuckDuckGo, SearXNG, YaCy
- **Lowest cost**: DuckDuckGo (free), Serper (cheapest API)
- **Highest rate limits**: Google PSE, Bing
- **Self-hosted**: SearXNG, YaCy

### URL Safety & SSRF Prevention

**Protections Implemented:**
- URL format validation
- DNS resolution to check for private IPs
- Block localhost, 127.0.0.1, 192.168.x.x, 10.x.x.x
- Block link-local addresses (169.254.x.x)
- Configurable via `ENABLE_RAG_LOCAL_WEB_FETCH`

**Vulnerabilities:**
- DNS rebinding attacks still possible (time-of-check vs time-of-use)
- HTTP redirects not fully protected
- Consider WAF or network-level protections for production

### Performance Considerations
- **Search APIs**: ~100-500ms per query
- **Web Loading (simple)**: ~1-2s per page
- **Web Loading (Playwright)**: ~3-5s per page (browser startup)
- **Batch Loading**: Parallel requests improve throughput
- **Rate Limits**: Most APIs have rate limits (check provider docs)

### Cost Considerations

**Free Options:**
- DuckDuckGo: Free, no API key
- SearXNG: Free (self-hosted)
- YaCy: Free (P2P, self-hosted)

**Paid APIs (approximate):**
- Brave: $5/month for 2000 queries
- Serper: $0.001/query ($1 for 1000)
- SerpApi: $50/month for 5000 queries
- Tavily: $0.01/search

### Error Handling
Common errors:
- **API key invalid**: 401 Unauthorized
- **Rate limit exceeded**: 429 Too Many Requests
- **URL unreachable**: Timeout, connection refused
- **Content extraction failed**: Return empty document (log warning)
- **Private IP detected**: ValueError with INVALID_URL message

### Security Best Practices
- Store API keys in environment variables (never commit)
- Use HTTPS for all API requests
- Validate and sanitize all URLs
- Block access to private networks (default)
- Limit number of URLs loaded per request
- Set timeouts on all HTTP requests
- Rotate API keys regularly

### Testing with Test Data
Use testdata/ for development:
```python
import json

# Load mock response
with open("retrieval/web/testdata/brave.json") as f:
    mock_results = json.load(f)

# Use in tests or development
results = mock_results["results"]
```

### Monitoring
Track web search health:
- Search API response times
- Search API error rates
- Content loading success rates
- Content loading durations
- API quota usage
- Web loader failures (by engine)

### Future Improvements
Potential enhancements:
- Caching search results (TTL-based)
- More granular rate limiting
- Automatic provider fallback (if one fails, try another)
- Parallel web loading (async batch)
- Smart provider selection (quality vs cost vs speed)
- Content summarization (extract key points)
