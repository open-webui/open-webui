# Retrieval/Web/Testdata Directory

This directory contains mock JSON response files for all web search providers supported by Open WebUI. These files enable development, testing, and CI/CD without requiring actual API keys or making live API calls to external search services.

## Purpose

This directory provides:
- **Development Without API Keys**: Test web search integration locally
- **Consistent Test Data**: Reproducible test results across environments
- **CI/CD Support**: Automated testing without external dependencies
- **Response Format Examples**: Documentation of each provider's response structure
- **Offline Development**: Work on web search features without internet

## Files

Each file contains a sample response from the corresponding search provider:

- **`brave.json`** - Brave Search API response format
- **`bing.json`** - Bing Web Search API response
- **`google_pse.json`** - Google Programmable Search Engine response
- **`searchapi.json`** - SearchAPI.io response
- **`searxng.json`** - SearXNG meta-search engine response
- **`serper.json`** - Serper.dev response
- **`serply.json`** - Serply.io response
- **`serpstack.json`** - SerpStack response

## File Format

All JSON files follow this general structure:

```json
{
  "query": "sample search query",
  "results": [
    {
      "link": "https://example.com/page1",
      "title": "Example Page Title",
      "snippet": "This is a snippet from the page content..."
    },
    {
      "link": "https://example.com/page2",
      "title": "Another Example",
      "snippet": "Another snippet of content..."
    }
  ],
  "metadata": {
    "provider": "brave",
    "timestamp": "2024-01-15T10:30:00Z",
    "total_results": 10
  }
}
```

**Common Fields:**
- `query` - The search query string
- `results` - Array of search results
  - `link` - URL of the result
  - `title` - Page title
  - `snippet` - Short description/excerpt
- `metadata` - Provider-specific metadata (optional)

## Usage

### In Development

**Load mock data instead of calling API:**
```python
import json
from pathlib import Path

def get_mock_search_results(provider: str):
    testdata_dir = Path(__file__).parent / "testdata"
    mock_file = testdata_dir / f"{provider}.json"

    with open(mock_file) as f:
        data = json.load(f)

    return data["results"]

# Usage
if DEVELOPMENT_MODE:
    results = get_mock_search_results("brave")
else:
    results = brave.search(query, count=10)
```

### In Unit Tests

**Test web search without external calls:**
```python
import pytest
import json

@pytest.fixture
def mock_brave_response():
    with open("testdata/brave.json") as f:
        return json.load(f)

def test_process_search_results(mock_brave_response):
    results = mock_brave_response["results"]
    assert len(results) > 0
    assert all("link" in r for r in results)
    assert all("title" in r for r in results)
```

### In CI/CD Pipeline

**Test without API keys:**
```yaml
# .github/workflows/test.yml
- name: Run tests
  env:
    USE_MOCK_SEARCH_DATA: true  # Use testdata instead of real APIs
  run: pytest tests/
```

## Response Format by Provider

### Brave Search
```json
{
  "query": "open webui",
  "results": [
    {
      "link": "https://github.com/open-webui/open-webui",
      "title": "Open WebUI - GitHub",
      "snippet": "A self-hosted WebUI for running Large Language Models..."
    }
  ]
}
```

### Google PSE (Programmable Search Engine)
```json
{
  "query": "open webui",
  "results": [
    {
      "link": "https://openwebui.com",
      "title": "Open WebUI - Official Website",
      "snippet": "User-friendly WebUI for LLMs. Supports OpenAI, Ollama..."
    }
  ],
  "searchInformation": {
    "totalResults": "1240000"
  }
}
```

### SearXNG
```json
{
  "query": "open webui",
  "results": [
    {
      "link": "https://...",
      "title": "...",
      "snippet": "...",
      "engine": "google"
    }
  ]
}
```

Note: SearXNG aggregates results from multiple engines, so results include `engine` field.

## Maintenance

### Adding New Provider Test Data

When adding a new search provider:

1. **Create JSON file**: `{provider_name}.json`
2. **Make real API call**: Get actual response from provider
3. **Sanitize data**: Remove API keys, personal info
4. **Extract structure**: Keep only essential fields (link, title, snippet)
5. **Add metadata**: Include provider name and timestamp
6. **Commit to git**: Include in version control

**Example Process:**
```python
# 1. Make real API call
response = new_provider.search("test query", api_key=API_KEY)

# 2. Save to JSON
import json
with open("testdata/new_provider.json", "w") as f:
    json.dump({
        "query": "test query",
        "results": response["results"][:5],  # Only first 5 results
        "metadata": {
            "provider": "new_provider",
            "note": "Sample response for testing"
        }
    }, f, indent=2)
```

### Updating Existing Test Data

**When to update:**
- Provider API changes response format
- Need more diverse test cases
- Found edge cases not covered

**How to update:**
1. Make new API call with updated query
2. Replace old JSON file
3. Update any tests that depend on specific data
4. Document changes in commit message

## Important Notes

### Data Freshness
- Test data is static snapshots
- Real API responses may differ
- Update periodically to match current API formats
- Include timestamp in metadata

### Privacy Considerations
- Never include real user queries
- Use generic test queries ("test", "example", "sample")
- Sanitize any personal information
- Review before committing

### Not a Replacement for Integration Tests
- Mock data tests code paths, not actual integrations
- Still need integration tests with real APIs
- Use mock data for unit tests, real APIs for integration tests
- Consider periodic live API health checks

### Git and File Size
- Keep files small (<100 KB each)
- Only include essential fields
- Limit number of results (5-10 sufficient)
- Consider gitattributes for JSON formatting

### Documentation Value
- Files serve as API response documentation
- New developers can see expected formats
- Useful when provider documentation is incomplete
- Include comments (if JSON allows) or separate README

## Testing Strategy

**Three-Tier Approach:**

1. **Unit Tests (Mock Data)**
   - Use testdata/ files
   - Fast, no external dependencies
   - Test data processing logic

2. **Integration Tests (Real APIs)**
   - Use actual API keys (CI secrets)
   - Slower, external dependencies
   - Test actual provider integration
   - Run less frequently

3. **Manual Testing (Development)**
   - Use testdata during development
   - Switch to real APIs for final verification
   - Toggle via environment variable

**Environment Variable Pattern:**
```python
USE_MOCK_DATA = os.getenv("USE_MOCK_SEARCH_DATA", "false").lower() == "true"

def search(query: str):
    if USE_MOCK_DATA:
        return load_mock_data("brave.json")
    else:
        return real_brave_search(query)
```

## Future Improvements

Potential enhancements:
- **Multiple scenarios**: Success, error, empty results
- **Parametric data**: Generate test data programmatically
- **Response variants**: Different query types (informational, navigational, etc.)
- **Locale variants**: Different language/region results
- **Error responses**: 429 rate limit, 401 auth failure, etc.
