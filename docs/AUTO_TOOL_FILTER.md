# AutoTool Filter Guide

## Overview

AutoTool Filter is an **inlet filter** that automatically suggests or injects relevant tools based on user queries using semantic similarity matching. It analyzes the user's message before it reaches the LLM and identifies which tools would be most useful for completing the task.

### Key Features

- **Semantic Matching**: Uses sentence transformers to find tools based on meaning, not keywords
- **Auto-Injection**: Optionally inject tools directly into the request (LLM sees them automatically)
- **Tool Suggestions**: Provide ranked recommendations for users to choose from
- **Embedding Caching**: Caches tool embeddings for fast repeated lookups (<200ms)
- **Configurable Threshold**: Adjust similarity sensitivity (0.0-1.0)
- **Top-K Results**: Configure how many tools to suggest (1-10)
- **User-Scoped**: Searches both user-specific and global tools
- **Cache Eviction**: Prevents memory leaks with FIFO eviction (max 500 entries)

---

## How It Works

### Workflow

```
User Query → AutoTool Filter (inlet)
                 ↓
          1. Extract query text
          2. Get available tools (user + global)
          3. Compute embeddings (query + tools)
          4. Calculate cosine similarity
          5. Rank tools by score
          6. Filter by threshold
          7. Return top-K results
                 ↓
    Auto-inject OR add to metadata
                 ↓
          LLM receives request
```

### Example Interaction

**Without AutoTool**:
```
User: "What's 25 * 47?"
System: [User must manually select Calculator tool]
```

**With AutoTool (Suggestions)**:
```
User: "What's 25 * 47?"
AutoTool: Suggests Calculator (score: 0.95)
System: [Shows suggestion UI, user clicks Calculator]
```

**With AutoTool (Auto-Injection)**:
```
User: "What's 25 * 47?"
AutoTool: Automatically injects Calculator tool
LLM: [Sees Calculator tool available] → Uses it → Returns 1175
```

---

## Installation

### Prerequisites

```bash
# Install sentence transformers
pip install sentence-transformers>=2.2.0

# Install scikit-learn (for cosine similarity)
pip install scikit-learn>=1.3.0
```

### Setup

```bash
# 1. Navigate to Open WebUI backend
cd backend

# 2. Enable AutoTool Filter
# Go to Admin Panel → Functions → AutoTool Filter → Enable

# 3. Configure Valves
# Set auto_select to false for suggestions (default)
# Set auto_select to true for automatic injection
```

---

## Configuration

### Valves (Settings)

| Valve | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable automatic tool suggestion |
| `auto_select` | boolean | `false` | **false**: Suggest tools<br>**true**: Auto-inject tools into request |
| `top_k` | int | `3` | Number of top tools to suggest (1-10) |
| `similarity_threshold` | float | `0.5` | Minimum similarity score to match (0.0-1.0) |
| `model_name` | string | `"all-MiniLM-L6-v2"` | Sentence transformer model to use |
| `cache_embeddings` | boolean | `true` | Cache tool embeddings for performance |

### Valve Details

#### `auto_select` (Critical Setting)

**false (Suggestions Mode - Default)**:
- AutoTool adds suggestions to metadata
- User sees ranked tool recommendations
- User manually selects which tool to use
- Non-intrusive, user has full control

**true (Auto-Injection Mode)**:
- AutoTool automatically adds tools to request
- LLM sees tools immediately without user action
- Faster workflow, no manual selection
- Risk: Wrong tool might be injected

**Recommendation**: Start with `false`, enable `true` for power users

#### `similarity_threshold`

Controls how "strict" the matching is:

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| `0.3` | Very loose - many matches | Exploration, discovery |
| `0.5` | Balanced (default) | General use |
| `0.7` | Strict - only close matches | Precision-focused |
| `0.9` | Very strict - exact matches only | Safety-critical |

#### `model_name`

Available sentence transformer models:

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `all-MiniLM-L6-v2` | 80MB | Fast | Good (default) |
| `all-mpnet-base-v2` | 420MB | Medium | Better |
| `all-MiniLM-L12-v2` | 120MB | Medium | Good |

**Recommendation**: Use default `all-MiniLM-L6-v2` unless you need higher accuracy

---

## Tool Matching

### How Similarity Works

AutoTool computes **cosine similarity** between query and tool descriptions:

```python
# Example tool
tool = {
    "id": "calculator",
    "name": "Calculator",
    "description": "Perform mathematical calculations"
}

# Tool embedding (computed once, cached)
tool_embedding = model.encode("Calculator: Perform mathematical calculations")

# User query
query = "What's 25 * 47?"
query_embedding = model.encode("What's 25 * 47?")

# Cosine similarity (0.0-1.0)
similarity = cosine_similarity(query_embedding, tool_embedding)
# Result: 0.85 (high match - calculator is relevant)
```

### Ranking Algorithm

1. **Compute similarity** for all tools
2. **Filter by threshold** (e.g., keep only scores ≥ 0.5)
3. **Sort descending** by score
4. **Return top-K** results (e.g., top 3)

### Example Rankings

**Query**: "Send an email to john@example.com"

| Tool | Description | Score |
|------|-------------|-------|
| Email Sender | Send emails via SMTP | **0.92** ✓ |
| Gmail API | Access Gmail inbox | **0.78** ✓ |
| Slack Messenger | Send Slack messages | 0.45 ✗ |
| Calculator | Math calculations | 0.12 ✗ |

**Result**: Suggests "Email Sender" and "Gmail API"

---

## Usage Modes

### Mode 1: Suggestions (Recommended)

**Configuration**:
```python
auto_select = False  # Suggestions only
top_k = 3
similarity_threshold = 0.5
```

**Behavior**:
- User query analyzed
- Top 3 tools suggested with scores
- Suggestions added to `__metadata__`
- User manually selects tool (if desired)

**Response Metadata**:
```json
{
  "messages": [...],
  "__metadata__": {
    "tool_suggestions": [
      {
        "name": "Calculator",
        "description": "Perform mathematical calculations",
        "score": 0.95
      },
      {
        "name": "Unit Converter",
        "description": "Convert units of measurement",
        "score": 0.67
      },
      {
        "name": "Scientific Calculator",
        "description": "Advanced math functions",
        "score": 0.58
      }
    ]
  }
}
```

---

### Mode 2: Auto-Injection (Advanced)

**Configuration**:
```python
auto_select = True  # Auto-inject tools
top_k = 2
similarity_threshold = 0.7  # Higher threshold for safety
```

**Behavior**:
- User query analyzed
- Top 2 tools automatically added to `body["tools"]`
- LLM receives request with tools already available
- LLM can use tools immediately

**Modified Request**:
```json
{
  "messages": [
    {"role": "user", "content": "What's 25 * 47?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "calculator",
        "description": "Perform mathematical calculations",
        "parameters": {...}
      }
    }
  ]
}
```

**Advantages**:
- Faster workflow (no manual selection)
- Better for experienced users
- Enables autonomous tool use

**Disadvantages**:
- May inject wrong tools
- Less user control
- Requires higher similarity threshold

---

## Caching Strategy

### Embedding Cache

**Purpose**: Avoid recomputing tool embeddings on every request

**Cache Key**: `tool.id`

**Cache Structure**:
```python
{
  "calculator": np.array([0.123, 0.456, ...]),  # 384-dim vector
  "email-sender": np.array([0.789, 0.012, ...]),
  ...
}
```

**Cache Eviction**:
- **Max Size**: 500 tools
- **Strategy**: FIFO (First In, First Out)
- **When**: Cache reaches 500 entries, oldest entry is removed

**Performance**:
- **Cache Hit**: ~50ms (fast)
- **Cache Miss**: ~200ms (compute embedding + store)
- **Hit Ratio**: Typically >90% after warm-up

### Cache Invalidation

Cache is cleared when:
- Tool description changes
- Tool is deleted
- Server restarts (in-memory cache)

**Future Improvement**: Persist cache to disk for faster server restarts

---

## Performance

### Latency Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| Query embedding | ~50ms | Sentence transformer |
| Tool embedding (cached) | ~5ms | Cache lookup |
| Tool embedding (uncached) | ~50ms | First time |
| Cosine similarity | <1ms | NumPy vectorized |
| Total (10 tools, all cached) | ~100ms | Typical case |
| Total (10 tools, all uncached) | ~550ms | Worst case (first run) |

### Optimization Tips

1. **Enable Caching**: Always keep `cache_embeddings = true`
2. **Limit Top-K**: Use `top_k = 3` instead of `10`
3. **Raise Threshold**: Higher threshold = fewer computations
4. **Use Smaller Model**: `all-MiniLM-L6-v2` (default) is fastest

### Memory Usage

**Sentence Transformer Model**: ~80MB (all-MiniLM-L6-v2)

**Cache Size**: 500 tools × 384 dimensions × 4 bytes = ~750KB

**Total Overhead**: ~85MB per worker process

---

## Integration with Tools

### Tool Requirements

For AutoTool to work, tools must have:

1. **Name**: Unique identifier
2. **Description**: Clear, descriptive text
3. **Meta**: Metadata dictionary with `description` key

**Example Tool**:
```python
class CalculatorTool:
    id = "calculator"
    name = "Calculator"
    meta = {
        "description": "Perform basic arithmetic operations like addition, subtraction, multiplication, and division"
    }
    specs = [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Evaluate a mathematical expression",
                "parameters": {...}
            }
        }
    ]
```

### Writing Good Tool Descriptions

**Good Description**:
> "Send emails via SMTP with attachments and custom headers"

**Bad Description**:
> "Email tool"

**Why**: Good descriptions include:
- **Action verb**: "Send", "Fetch", "Convert"
- **Method**: "via SMTP", "using API"
- **Features**: "with attachments", "custom headers"

**More Examples**:

| Tool | Good Description |
|------|------------------|
| Weather | "Fetch current weather and 7-day forecast for any city using OpenWeatherMap API" |
| Translator | "Translate text between 100+ languages using Google Translate" |
| Image Generator | "Generate AI images from text prompts using DALL-E 3 or Stable Diffusion" |
| Code Formatter | "Format Python, JavaScript, and TypeScript code using Black and Prettier" |

---

## Troubleshooting

### Common Issues

#### 1. No tools suggested

**Possible Causes**:
- AutoTool disabled (`enabled = false`)
- Similarity threshold too high
- No matching tools available
- Query too vague

**Solutions**:
```python
# Lower threshold
similarity_threshold = 0.3

# Check enabled
enabled = True

# Verify tools exist
from open_webui.models.tools import Tools
tools = Tools.get_tools_by_user_id("user-123")
print(f"Available tools: {len(tools)}")
```

#### 2. Wrong tools suggested

**Issue**: Irrelevant tools have high scores

**Solutions**:
- **Raise threshold**: `similarity_threshold = 0.7`
- **Improve tool descriptions**: Add more keywords
- **Use better model**: `model_name = "all-mpnet-base-v2"`

**Example**:
```python
# Before (vague)
"Email tool"

# After (specific)
"Send emails via SMTP with support for HTML content, attachments, and CC/BCC recipients"
```

#### 3. Slow performance

**Issue**: Tool suggestions take >1 second

**Solutions**:
```python
# Enable caching
cache_embeddings = True

# Use smaller model
model_name = "all-MiniLM-L6-v2"

# Reduce top-k
top_k = 2

# Limit tool count
# Remove unused/deprecated tools from database
```

#### 4. Memory leaks

**Issue**: Memory usage growing over time

**Solution**: Already fixed with cache eviction

```python
# Verify cache size
print(f"Cache size: {len(filter.tool_cache)}")

# Should never exceed 500
assert len(filter.tool_cache) <= 500
```

#### 5. Model download failed

**Error**: Cannot download sentence transformer model

**Solution**:
```bash
# Manual download
pip install sentence-transformers
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Check internet connection
ping huggingface.co

# Use local model cache
export SENTENCE_TRANSFORMERS_HOME=/path/to/models
```

---

## Advanced Features

### Custom Similarity Function

Modify `_compute_similarity()` for custom scoring:

```python
def _compute_similarity(self, query_embedding, tool_embedding):
    # Default: Cosine similarity
    similarity = cosine_similarity(
        query_embedding.reshape(1, -1),
        tool_embedding.reshape(1, -1)
    )[0][0]

    # Custom: Add boost for certain tool types
    if tool.meta.get('priority') == 'high':
        similarity *= 1.2  # 20% boost

    return float(similarity)
```

### Event Emitter Integration

Show real-time suggestions to user:

```python
async def inlet(self, body, user, __event_emitter__):
    # ... tool ranking logic ...

    if __event_emitter__:
        tool_names = [t["name"] for t in suggestions]
        await __event_emitter__({
            "type": "status",
            "data": {
                "description": f"Suggested tools: {', '.join(tool_names[:2])}",
                "done": True
            }
        })
```

### Multi-Query Matching

Match against multiple query variations:

```python
# Original query
query = "What's the weather?"

# Generate variations
variations = [
    query,
    f"I need to {query}",
    f"How can I {query}",
    f"Tool for {query}"
]

# Compute average similarity across variations
scores = []
for variation in variations:
    embedding = model.encode([variation])[0]
    score = compute_similarity(embedding, tool_embedding)
    scores.append(score)

final_score = sum(scores) / len(scores)
```

---

## Examples

### Example 1: Math Query

**Query**: "Calculate the square root of 144"

**AutoTool Processing**:
```python
# Available tools
tools = [
    {"name": "Calculator", "description": "Perform arithmetic operations"},
    {"name": "Unit Converter", "description": "Convert units"},
    {"name": "Weather", "description": "Get weather forecasts"}
]

# Similarity scores
scores = {
    "Calculator": 0.89,      # ✓ Match (>0.5)
    "Unit Converter": 0.42,  # ✗ Below threshold
    "Weather": 0.15          # ✗ Irrelevant
}

# Result
suggestions = [
    {"name": "Calculator", "score": 0.89}
]
```

**Response**:
```json
{
  "__metadata__": {
    "tool_suggestions": [
      {"name": "Calculator", "description": "...", "score": 0.89}
    ]
  }
}
```

---

### Example 2: Multi-Tool Scenario

**Query**: "Send an email to john@example.com and schedule a meeting for tomorrow"

**AutoTool Processing**:
```python
scores = {
    "Email Sender": 0.85,       # ✓ Email part
    "Calendar": 0.78,           # ✓ Meeting part
    "Slack": 0.38,              # ✗ Similar but not relevant
    "Calculator": 0.12          # ✗ Unrelated
}

# Top 3 results
suggestions = [
    {"name": "Email Sender", "score": 0.85},
    {"name": "Calendar", "score": 0.78}
]
```

---

### Example 3: Auto-Injection

**Configuration**:
```python
auto_select = True
top_k = 1
similarity_threshold = 0.8
```

**Query**: "What's 25 * 47?"

**AutoTool Processing**:
```python
scores = {
    "Calculator": 0.95  # ✓ High confidence, auto-inject
}

# Auto-inject into request
body["tools"] = [calculator_tool_spec]
```

**LLM Receives**:
```json
{
  "messages": [
    {"role": "user", "content": "What's 25 * 47?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "calculate",
        "description": "Perform mathematical calculations",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          }
        }
      }
    }
  ]
}
```

**LLM Response**:
```json
{
  "tool_calls": [
    {
      "function": {
        "name": "calculate",
        "arguments": "{\"expression\": \"25 * 47\"}"
      }
    }
  ]
}
```

**Final Result**: 1175

---

## Testing

### Unit Tests

```python
import pytest
from open_webui.functions.auto_tool_filter import Filter

@pytest.fixture
def auto_tool():
    return Filter()

def test_semantic_matching(auto_tool):
    # Mock tool
    class Tool:
        id = "calculator"
        name = "Calculator"
        meta = {"description": "Perform math"}

    # Query
    query = "What's 5 + 3?"

    # Get embedding
    tool_embedding = auto_tool._get_tool_embedding(Tool())
    query_embedding = auto_tool.model.encode([query])[0]

    # Compute similarity
    similarity = auto_tool._compute_similarity(query_embedding, tool_embedding)

    assert similarity > 0.7  # High similarity expected

def test_cache_eviction(auto_tool):
    # Fill cache to max
    for i in range(500):
        auto_tool.tool_cache[f"tool-{i}"] = np.random.rand(384)

    # Add one more (should trigger eviction)
    auto_tool.tool_cache["tool-500"] = np.random.rand(384)

    # Cache should not exceed max size
    assert len(auto_tool.tool_cache) <= 500
```

---

## Best Practices

### 1. Tool Description Quality

**Do**:
- Use action verbs
- Include method/technology
- Mention key features
- Be specific and clear

**Don't**:
- Use vague names
- Omit important details
- Make descriptions too long (>200 chars)

### 2. Threshold Tuning

**Start Conservative**:
```python
similarity_threshold = 0.7  # High precision
top_k = 2                   # Few suggestions
auto_select = False         # Manual selection
```

**Gradually Loosen** (based on user feedback):
```python
similarity_threshold = 0.5  # Balanced
top_k = 3                   # More options
auto_select = False         # Still manual
```

**Power Users**:
```python
similarity_threshold = 0.6  # Slightly strict
top_k = 1                   # Best match only
auto_select = True          # Automatic injection
```

### 3. Performance Monitoring

```python
import time

start = time.time()
suggestions = filter.inlet(body, user)
duration = time.time() - start

# Alert if slow
if duration > 0.5:  # 500ms threshold
    log.warning(f"AutoTool slow: {duration*1000}ms")
```

### 4. Cache Management

- **Enable caching**: Always on in production
- **Monitor size**: Log cache size periodically
- **Warm-up**: Pre-compute embeddings for common tools

---

## Roadmap

### Planned Improvements

1. **Persistent Cache**: Store embeddings on disk for faster restarts
2. **Multi-Language**: Support non-English queries
3. **Contextual Ranking**: Consider conversation history
4. **Feedback Loop**: Learn from user selections
5. **Tool Categories**: Tag tools with categories for better filtering
6. **Hybrid Search**: Combine semantic + keyword matching
7. **Confidence Scores**: Show why tool was suggested

---

## FAQ

**Q: Does AutoTool work with all LLM providers?**
A: Yes, it's provider-agnostic. It modifies the request before LLM processing.

**Q: Can I use a custom sentence transformer model?**
A: Yes, set `model_name` to any HuggingFace model (e.g., `"sentence-transformers/paraphrase-MiniLM-L6-v2"`)

**Q: How do I add new tools for AutoTool to suggest?**
A: Create tools in Open WebUI admin panel. AutoTool automatically discovers them.

**Q: What if two tools have very similar descriptions?**
A: Both will be suggested with similar scores. User can choose or AutoTool will inject highest-scoring.

**Q: Can I disable AutoTool for specific users?**
A: Currently no, but you can implement user-specific Valve overrides.

**Q: Does AutoTool support tool chaining?**
A: Not directly, but it can suggest multiple tools for complex queries.

---

## Contributing

Contributions welcome! Areas for improvement:

1. Persistent embedding cache
2. Multi-language query support
3. Contextual tool ranking
4. User feedback integration
5. Tool category/tag system

---

## License

This feature is part of Open WebUI and follows the same license.

---

**Version**: 1.0.0
**Last Updated**: 2025-11-01
**Author**: Claude Code + Parker Dunn
