# Auto Memory Guide

## Overview

Auto Memory is an **outlet filter** that automatically extracts and stores conversation facts using Named Entity Recognition (NER). It runs after the LLM generates a response, analyzing the text to identify and remember entities like people, organizations, dates, and locations.

### Key Features

- **Automatic Extraction**: No manual tagging required - memories are extracted from natural conversation
- **Named Entity Recognition**: Powered by Spacy's `en_core_web_sm` model
- **ChromaDB Storage**: Vector embeddings for semantic search and retrieval
- **User Privacy**: Isolated memory collections per user (`user-memory-{user_id}`)
- **Deduplication**: Prevents storing duplicate memories within 10-minute window
- **Context Preservation**: Stores surrounding sentence for better recall
- **Memory Types**: Supports 7 entity types (Person, Organization, Location, Date, Time, Money, Product)
- **Cache Eviction**: Prevents memory leaks with FIFO eviction (max 1000 entries)

---

## How It Works

### Workflow

```
User Query → LLM Response → Auto Memory (outlet filter)
                                 ↓
                          1. Extract entities (NER)
                          2. Filter by confidence
                          3. Check deduplication
                          4. Store in ChromaDB
                          5. Add metadata to response
```

### Example Interaction

**User**: "I'm John and I work at Google in San Francisco"

**Auto Memory Processing**:
1. **Entity Extraction**:
   - `PERSON`: "John"
   - `ORG`: "Google"
   - `GPE`: "San Francisco"
2. **Context Capture**: Full sentence for each entity
3. **ChromaDB Storage**: Store with embeddings in `user-memory-{user_id}`

**Later Retrieval**:

**User**: "Where do I work?"

**System**: Searches ChromaDB → Finds "Google" → Returns context

---

## Installation

### Prerequisites

```bash
# 1. Install Spacy
pip install spacy>=3.7.0

# 2. Download English model
python -m spacy download en_core_web_sm
```

⚠️ **Important**: The Spacy model **must** be downloaded manually. Auto Memory will **fail gracefully** with a clear error message if the model is missing.

### Setup

```bash
# 1. Navigate to Open WebUI backend
cd backend

# 2. Enable Auto Memory filter
# Go to Admin Panel → Functions → Auto Memory → Enable

# 3. Configure Valves (optional)
# Adjust settings in the Admin Panel
```

---

## Configuration

### Valves (Settings)

Auto Memory is configured using "Valves" in the Open WebUI admin panel:

| Valve | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable automatic memory extraction |
| `min_confidence` | float | `0.7` | Minimum confidence threshold (0.0-1.0) for entity extraction |
| `memory_types` | list | See below | Entity types to extract and store |
| `max_context_length` | int | `200` | Maximum characters of context to store with each memory |
| `deduplicate` | boolean | `true` | Avoid storing duplicate memories within time window |

**Default Memory Types**:
```json
["PERSON", "ORG", "GPE", "DATE", "TIME", "MONEY", "PRODUCT"]
```

### Memory Type Descriptions

| Type | Description | Examples |
|------|-------------|----------|
| `PERSON` | People names | "John Smith", "Alice" |
| `ORG` | Organizations | "Google", "OpenAI", "MIT" |
| `GPE` | Geopolitical entities | "San Francisco", "California", "USA" |
| `DATE` | Dates | "January 1st", "2024", "last Monday" |
| `TIME` | Times | "3:00 PM", "morning", "noon" |
| `MONEY` | Monetary values | "$100", "50 euros" |
| `PRODUCT` | Products | "iPhone", "Tesla Model 3" |

### Advanced Configuration

**Adjusting Confidence Threshold**:
```python
# Lower confidence = more memories (may include false positives)
min_confidence = 0.5

# Higher confidence = fewer memories (only high-quality)
min_confidence = 0.9
```

**Custom Memory Types**:
```python
# Add more Spacy entity types
memory_types = [
    "PERSON", "ORG", "GPE",       # Default
    "EVENT", "WORK_OF_ART", "LAW", # Additional
    "LANGUAGE", "PERCENT"          # Additional
]
```

**Disable Deduplication** (for testing):
```python
deduplicate = False
```

---

## Memory Storage

### ChromaDB Integration

Auto Memory uses ChromaDB for vector storage:

**Collection Name Format**: `user-memory-{user_id}`

**Storage Structure**:
```python
{
  "documents": ["PERSON: John (Context: I'm John and I work at Google)"],
  "metadatas": [{
    "type": "PERSON",
    "entity": "John",
    "context": "I'm John and I work at Google",
    "source": "auto_memory",
    "confidence": 0.9,
    "timestamp": 1698765432,
    "version": "1.0.0"
  }]
}
```

### Deduplication Strategy

**Time Window**: 10 minutes (600 seconds)

**Cache Key Format**: `{user_id}:{entity_type}:{entity_text_lowercase}`

**Example**:
```python
# First mention at 12:00 PM
entity = {"type": "PERSON", "text": "John"}
# Stored in cache: "user-123:PERSON:john" → timestamp

# Second mention at 12:05 PM (within 10 minutes)
# Skipped (duplicate)

# Third mention at 12:15 PM (after 10 minutes)
# Stored again (cache expired)
```

### Cache Eviction

**Maximum Cache Size**: 1000 entries

**Eviction Strategy**: Time-based cleanup

```python
# When cache reaches 1000 entries
# Remove all entries older than 10 minutes
cutoff_time = current_time - 600  # 10 minutes
cache = {k: v for k, v in cache.items() if v > cutoff_time}
```

---

## Usage

### Enabling Auto Memory

**Admin Panel**:
1. Navigate to **Admin Panel** → **Functions**
2. Find **Auto Memory**
3. Toggle **Enabled** to `ON`
4. Adjust Valves as needed
5. Click **Save**

### Verifying Installation

**Test Spacy Model**:
```bash
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('Spacy model loaded successfully')"
```

**Test Memory Extraction**:
```python
# In Python console
from open_webui.functions.auto_memory import Filter

filter = Filter()
text = "My name is Alice and I work at Microsoft"
entities = filter._extract_entities(text)
print(entities)
# Output: [{'text': 'Alice', 'type': 'PERSON', ...}, {'text': 'Microsoft', 'type': 'ORG', ...}]
```

### Viewing Stored Memories

Memories are stored in ChromaDB. To query:

```python
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

# Query user's memories
collection_name = "user-memory-user-123"
results = VECTOR_DB_CLIENT.query(
    collection_name=collection_name,
    query_texts=["work"],
    n_results=5
)

print(results['documents'])
# Output: [
#   "ORG: Google (Context: I work at Google in San Francisco)",
#   "GPE: San Francisco (Context: I work at Google in San Francisco)"
# ]
```

---

## Response Metadata

Auto Memory adds metadata to the response body:

**Successful Extraction**:
```json
{
  "messages": [...],
  "__metadata__": {
    "auto_memory": {
      "extracted": 5,
      "stored": 3,
      "types": ["PERSON", "ORG", "GPE"]
    }
  }
}
```

**No Entities Found**:
```json
{
  "__metadata__": {
    "auto_memory": {
      "extracted": 0,
      "stored": 0,
      "types": []
    }
  }
}
```

**Error Occurred**:
```json
{
  "__metadata__": {
    "auto_memory": {
      "error": "Spacy model not installed",
      "extracted": 0,
      "stored": 0
    }
  }
}
```

---

## Privacy & Security

### User Isolation

- **Collection Naming**: Each user has a separate ChromaDB collection (`user-memory-{user_id}`)
- **No Cross-User Access**: User A cannot access User B's memories
- **Automatic Cleanup**: When user is deleted, their memory collection should be deleted (implement in user deletion logic)

### Data Retention

**Current Implementation**: Memories are stored indefinitely

**Recommended**: Implement periodic cleanup

```python
# Cleanup script (run monthly)
import time
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

def cleanup_old_memories(user_id, days=90):
    """Delete memories older than N days"""
    collection_name = f"user-memory-{user_id}"
    cutoff_timestamp = int(time.time()) - (days * 24 * 60 * 60)

    # Query old memories
    results = VECTOR_DB_CLIENT.query(
        collection_name=collection_name,
        where={"timestamp": {"$lt": cutoff_timestamp}},
        n_results=1000
    )

    # Delete old memories
    for id in results['ids']:
        VECTOR_DB_CLIENT.delete(
            collection_name=collection_name,
            ids=[id]
        )
```

### Sensitive Data

Auto Memory **does not filter** sensitive information. Consider:

1. **Custom Entity Types**: Remove `MONEY`, `DATE` if privacy concern
2. **Post-Processing Filter**: Add filter to remove SSN, credit cards
3. **User Consent**: Add opt-in/opt-out mechanism

---

## Troubleshooting

### Common Issues

#### 1. "Spacy model not installed"

**Error**:
```
RuntimeError: Spacy model not installed. Run: python -m spacy download en_core_web_sm
```

**Solution**:
```bash
# Install the model
python -m spacy download en_core_web_sm

# Verify installation
python -c "import spacy; spacy.load('en_core_web_sm')"

# Restart Open WebUI
systemctl restart open-webui
```

#### 2. No memories being extracted

**Possible Causes**:
- Auto Memory disabled (check Valves)
- Confidence threshold too high
- No entities in conversation
- Only processing assistant messages (not user messages)

**Solutions**:
```python
# Lower confidence threshold
min_confidence = 0.5  # Try lower value

# Check enabled status
enabled = True

# Verify entity types
memory_types = ["PERSON", "ORG", "GPE", "DATE", "TIME", "MONEY", "PRODUCT"]
```

#### 3. Duplicate memories

**Issue**: Same entity stored multiple times

**Solution**:
```python
# Ensure deduplication is enabled
deduplicate = True

# Increase deduplication window
_dedup_window_seconds = 3600  # 1 hour instead of 10 minutes
```

#### 4. Memory leaks / High memory usage

**Issue**: Deduplication cache growing unbounded

**Solution**: Already fixed in latest version with cache eviction

```python
# Check cache size
print(f"Cache size: {len(filter._recent_memories)}")

# Cache should never exceed 1000 entries
assert len(filter._recent_memories) <= 1000
```

#### 5. ChromaDB connection errors

**Error**: Cannot connect to ChromaDB

**Solution**:
```bash
# Check ChromaDB is running
# Verify environment variables
echo $CHROMA_HOST
echo $CHROMA_PORT

# Test connection
python -c "from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT; print(VECTOR_DB_CLIENT)"
```

---

## Performance

### Memory Usage

**Spacy Model**: ~40MB loaded in memory

**Cache**: Max 1000 entries ≈ 100KB

**Total Overhead**: ~50MB per worker process

### Latency

**Typical Extraction Time**:
- Short message (< 50 words): ~50ms
- Medium message (50-200 words): ~150ms
- Long message (200+ words): ~300ms

**ChromaDB Storage**: ~50ms per entity

**Total Overhead per Message**: ~200-400ms

### Optimization Tips

1. **Reduce Context Length**:
   ```python
   max_context_length = 100  # Reduce from 200
   ```

2. **Increase Confidence Threshold**:
   ```python
   min_confidence = 0.8  # Fewer extractions
   ```

3. **Limit Memory Types**:
   ```python
   memory_types = ["PERSON", "ORG"]  # Only names and companies
   ```

---

## Examples

### Example 1: Personal Information

**Conversation**:
```
User: Hi, I'm Sarah Johnson and I live in Seattle.
Assistant: Hello Sarah! Nice to meet you. How can I help you today?
```

**Extracted Memories**:
```json
[
  {
    "type": "PERSON",
    "entity": "Sarah Johnson",
    "context": "Hi, I'm Sarah Johnson and I live in Seattle."
  },
  {
    "type": "GPE",
    "entity": "Seattle",
    "context": "Hi, I'm Sarah Johnson and I live in Seattle."
  }
]
```

**Later Retrieval**:
```
User: Where do I live?
Assistant: [Searches ChromaDB] You live in Seattle.
```

---

### Example 2: Work Context

**Conversation**:
```
User: I started working at OpenAI on January 15th, 2024.
Assistant: Congratulations on joining OpenAI!
```

**Extracted Memories**:
```json
[
  {
    "type": "ORG",
    "entity": "OpenAI",
    "context": "I started working at OpenAI on January 15th, 2024."
  },
  {
    "type": "DATE",
    "entity": "January 15th, 2024",
    "context": "I started working at OpenAI on January 15th, 2024."
  }
]
```

---

### Example 3: Project Details

**Conversation**:
```
User: I'm working on the Tesla Cybertruck launch event.
Assistant: That sounds exciting! Tell me more about the project.
```

**Extracted Memories**:
```json
[
  {
    "type": "ORG",
    "entity": "Tesla",
    "context": "I'm working on the Tesla Cybertruck launch event."
  },
  {
    "type": "PRODUCT",
    "entity": "Cybertruck",
    "context": "I'm working on the Tesla Cybertruck launch event."
  }
]
```

---

## Integration with RAG

Auto Memory can enhance RAG (Retrieval-Augmented Generation) pipelines:

### Custom RAG Integration

```python
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

def enhance_prompt_with_memories(user_id, query):
    """Add user's memories to LLM prompt"""

    # Search user's memories
    collection_name = f"user-memory-{user_id}"
    results = VECTOR_DB_CLIENT.query(
        collection_name=collection_name,
        query_texts=[query],
        n_results=5
    )

    # Extract relevant memories
    memories = results['documents'][0] if results['documents'] else []

    # Build enhanced prompt
    if memories:
        memory_context = "\n".join([f"- {mem}" for mem in memories])
        enhanced_query = f"""
User Query: {query}

Relevant User Information:
{memory_context}

Please use this information to provide a personalized response.
"""
    else:
        enhanced_query = query

    return enhanced_query
```

**Usage**:
```python
user_id = "user-123"
query = "What projects am I working on?"
enhanced_query = enhance_prompt_with_memories(user_id, query)

# Send to LLM
response = llm.generate(enhanced_query)
```

---

## Advanced Configuration

### Custom Entity Extraction

**Add Custom Patterns**:
```python
import spacy
from spacy.tokens import Span

# Load model
nlp = spacy.load("en_core_web_sm")

# Add custom entity ruler
ruler = nlp.add_pipe("entity_ruler", before="ner")

patterns = [
    {"label": "PROJECT", "pattern": "Cybertruck"},
    {"label": "PROJECT", "pattern": "Starship"},
    {"label": "SKILL", "pattern": [{"LOWER": "python"}, {"LOWER": "programming"}]}
]

ruler.add_patterns(patterns)
```

### Event Emitter Integration

Auto Memory supports event emitters for real-time notifications:

```python
# Event emitter example
async def outlet(self, body, user, __event_emitter__):
    # ... extraction logic ...

    if __event_emitter__:
        await __event_emitter__({
            "type": "status",
            "data": {
                "description": f"Auto Memory: Stored {stored_count} new memories",
                "done": True
            }
        })
```

---

## Testing

### Unit Tests

```python
import pytest
from open_webui.functions.auto_memory import Filter

@pytest.fixture
def auto_memory():
    return Filter()

def test_extract_entities(auto_memory):
    text = "My name is Alice and I work at Microsoft"
    entities = auto_memory._extract_entities(text)

    assert len(entities) == 2
    assert entities[0]['type'] == 'PERSON'
    assert entities[0]['text'] == 'Alice'
    assert entities[1]['type'] == 'ORG'
    assert entities[1]['text'] == 'Microsoft'

def test_deduplication(auto_memory):
    entity = {"type": "PERSON", "text": "John"}
    user_id = "user-123"

    # First call should return True (store)
    assert auto_memory._should_store_memory(entity, user_id) == True

    # Second call within 10 minutes should return False (skip)
    assert auto_memory._should_store_memory(entity, user_id) == False
```

---

## Best Practices

### 1. Model Management

- **Keep Spacy Updated**: Periodically update to latest stable version
- **Model Selection**: Use `en_core_web_sm` for speed, `en_core_web_lg` for accuracy
- **Language Support**: Install language-specific models for non-English users

### 2. Memory Hygiene

- **Regular Cleanup**: Delete old memories (90-180 day retention)
- **User Control**: Allow users to view/delete their memories
- **Quality Filtering**: Monitor and remove low-quality extractions

### 3. Performance

- **Lazy Loading**: Model loaded on first use (not at startup)
- **Cache Management**: Eviction prevents unbounded growth
- **Batch Processing**: Process multiple messages together when possible

### 4. Privacy

- **Informed Consent**: Notify users about automatic memory extraction
- **Opt-Out Mechanism**: Allow users to disable Auto Memory
- **Data Export**: Provide users with their stored memories (GDPR compliance)

---

## Roadmap

### Planned Improvements

1. **Multi-Language Support**: Support for non-English conversations
2. **Custom Entity Types**: User-defined entity patterns
3. **Memory Relationships**: Store connections between entities (knowledge graph)
4. **Confidence Scores**: Store Spacy's confidence for each entity
5. **Memory Search UI**: Admin interface to browse stored memories
6. **Smart Deduplication**: Semantic similarity instead of exact match
7. **Memory Expiry**: Automatic deletion after N days

---

## FAQ

**Q: Does Auto Memory work for user messages or assistant messages?**
A: Currently **assistant messages only** (outlet filter). To process user messages, implement as inlet filter.

**Q: Can I use a different NER model?**
A: Yes, modify `_load_nlp()` to load any Spacy model (`en_core_web_md`, `en_core_web_lg`, etc.)

**Q: How do I export a user's memories?**
A: Query ChromaDB for `user-memory-{user_id}` collection and export documents.

**Q: Does this work with non-English languages?**
A: No, currently English only. Install language-specific Spacy models for other languages.

**Q: How do I delete all memories for a user?**
A: Delete the ChromaDB collection: `VECTOR_DB_CLIENT.delete_collection(f"user-memory-{user_id}")`

**Q: Can I store custom metadata with memories?**
A: Yes, modify `_store_memory()` to add custom fields to the metadata dictionary.

---

## Contributing

Contributions welcome! Areas for improvement:

1. Multi-language NER support
2. Memory search UI
3. Custom entity patterns
4. Performance optimizations
5. GDPR compliance features

---

## License

This feature is part of Open WebUI and follows the same license.

---

**Version**: 1.0.0
**Last Updated**: 2025-11-01
**Author**: Claude Code + Parker Dunn
