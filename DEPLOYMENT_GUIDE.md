# Open WebUI Automation Enhancements - Deployment Guide

**Project**: N8N Integration + Auto Memory + AutoTool Filter
**Version**: 1.0.0
**Date**: November 1, 2025
**Status**: Ready for Deployment

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Database Migration](#database-migration)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)
10. [Monitoring](#monitoring)

---

## Overview

This deployment adds three major automation features to Open WebUI:

### 1. N8N Pipeline Integration
- **Purpose**: Connect Open WebUI to N8N workflows for end-to-end automation
- **Features**: SSE streaming, retry logic, execution tracking, analytics
- **Use Cases**: Cloud automation, email processing, data pipelines

### 2. Auto Memory Plugin
- **Purpose**: Automatically extract and store conversation facts
- **Features**: Named Entity Recognition (NER), ChromaDB storage, deduplication
- **Use Cases**: Persistent context, user preferences, knowledge accumulation

### 3. AutoTool Filter
- **Purpose**: Automatically suggest relevant tools using semantic similarity
- **Features**: Sentence embeddings, cosine similarity, auto-injection
- **Use Cases**: Smart tool discovery, improved UX, reduced manual tool selection

---

## Prerequisites

### System Requirements

- **Python**: 3.11+
- **Database**: SQLite (default) or PostgreSQL
- **Memory**: 4GB RAM minimum (8GB+ recommended for sentence-transformers)
- **Disk**: 2GB free space (for models and embeddings)

### Required Services

- **Open WebUI**: Existing installation
- **N8N** (optional): For N8N integration feature
- **ChromaDB**: Included with Open WebUI

---

## Installation

### Step 1: Update Dependencies

```bash
cd /path/to/open-webui/backend

# Install new dependencies
pip install -r requirements.txt

# Download Spacy model (for Auto Memory)
python -m spacy download en_core_web_sm
```

### Step 2: Verify Installation

```bash
# Test Spacy
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('Spacy OK')"

# Test sentence-transformers
python -c "from sentence_transformers import SentenceTransformer; print('Sentence-transformers OK')"

# Test scikit-learn
python -c "from sklearn.metrics.pairwise import cosine_similarity; print('Scikit-learn OK')"
```

Expected output:
```
Spacy OK
Sentence-transformers OK
Scikit-learn OK
```

---

## Configuration

### Environment Variables

Add to `.env` (optional, all features work with defaults):

```bash
# N8N Integration (optional)
N8N_DEFAULT_URL=http://localhost:5678
N8N_DEFAULT_API_KEY=your-n8n-api-key

# Auto Memory (optional)
AUTO_MEMORY_ENABLED=true
AUTO_MEMORY_MIN_CONFIDENCE=0.7

# AutoTool Filter (optional)
AUTOTOOL_ENABLED=true
AUTOTOOL_AUTO_SELECT=false  # Set to true for auto-injection
AUTOTOOL_TOP_K=3
AUTOTOOL_THRESHOLD=0.5
```

### Application Configuration

No code changes needed - features are self-contained in:
- `backend/open_webui/models/n8n_config.py`
- `backend/open_webui/routers/n8n_integration.py`
- `backend/open_webui/functions/auto_memory.py`
- `backend/open_webui/functions/auto_tool_filter.py`

---

## Database Migration

### Run Migration

```bash
cd /path/to/open-webui/backend

# Run Alembic migration
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade -> add_n8n_integration
INFO  [alembic.runtime.migration] Creating table n8n_config
INFO  [alembic.runtime.migration] Creating table n8n_executions
INFO  [alembic.runtime.migration] Creating indexes
```

### Verify Migration

```bash
# Check tables exist
python -c "
from open_webui.internal.db import get_db
from open_webui.models.n8n_config import N8NConfig, N8NWorkflowExecution

with get_db() as db:
    print('N8N tables exist:',
          db.query(N8NConfig).count() >= 0 and
          db.query(N8NWorkflowExecution).count() >= 0)
"
```

---

## Testing

### Run Unit Tests

```bash
cd /path/to/open-webui

# Run all new tests
pytest tests/test_auto_memory_function.py -v
pytest tests/test_auto_tool_filter.py -v
pytest tests/integration/test_n8n_integration.py -v

# Run with coverage
pytest tests/test_auto_memory_function.py --cov=open_webui.functions.auto_memory
pytest tests/test_auto_tool_filter.py --cov=open_webui.functions.auto_tool_filter
```

### Manual Testing

#### Test Auto Memory

1. Enable Auto Memory function in Open WebUI admin panel
2. Have a conversation with entities:
   ```
   User: Hi, I'm John and I work at Google.
   Assistant: Nice to meet you, John! How can I help you today?
   ```
3. Check metadata in response:
   ```json
   {
     "__metadata__": {
       "auto_memory": {
         "extracted": 2,
         "stored": 2,
         "types": ["PERSON", "ORG"]
       }
     }
   }
   ```

#### Test AutoTool Filter

1. Enable AutoTool Filter function in Open WebUI admin panel
2. Create a test tool (e.g., "Weather Tool")
3. Send query:
   ```
   User: What's the weather in Paris?
   ```
4. Check metadata:
   ```json
   {
     "__metadata__": {
       "tool_suggestions": [
         {"name": "Weather Tool", "score": 0.85}
       ]
     }
   }
   ```

#### Test N8N Integration

1. Create N8N workflow with webhook
2. Configure N8N in Open WebUI:
   ```bash
   curl -X POST http://localhost:8080/api/n8n/config \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test Workflow",
       "n8n_url": "http://localhost:5678",
       "webhook_id": "test-webhook",
       "is_streaming": true
     }'
   ```
3. Trigger workflow:
   ```bash
   curl -X POST http://localhost:8080/api/n8n/trigger/CONFIG_ID \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "test", "data": {"key": "value"}}'
   ```

---

## Deployment

### Production Deployment Checklist

- [ ] Dependencies installed
- [ ] Spacy model downloaded
- [ ] Database migrations applied
- [ ] Environment variables configured
- [ ] Tests passing (all 125+ tests)
- [ ] Monitoring enabled
- [ ] Backup created

### Deployment Steps

```bash
# 1. Backup database
cp /path/to/webui.db /path/to/webui.db.backup.$(date +%Y%m%d)

# 2. Pull latest code
cd /path/to/open-webui
git pull origin main

# 3. Install dependencies
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 4. Run migrations
alembic upgrade head

# 5. Restart service
systemctl restart open-webui

# 6. Verify deployment
curl http://localhost:8080/api/health
```

### Rollback Procedure

If deployment fails:

```bash
# 1. Stop service
systemctl stop open-webui

# 2. Restore database backup
cp /path/to/webui.db.backup.YYYYMMDD /path/to/webui.db

# 3. Revert migration
cd /path/to/open-webui/backend
alembic downgrade -1

# 4. Restart service
systemctl start open-webui
```

---

## Usage Examples

### Example 1: N8N Email Automation

**Scenario**: Automatically process emails with N8N

```python
# 1. Create N8N workflow for email processing

# 2. Configure in Open WebUI
config = {
    "name": "Email Processor",
    "n8n_url": "http://n8n.local:5678",
    "webhook_id": "email-processor",
    "is_streaming": True,
    "timeout_seconds": 180
}

# 3. Trigger from chat
"Process my unread emails and summarize them"
# Auto-triggers N8N workflow, streams results
```

### Example 2: Persistent User Memory

**Scenario**: Remember user preferences automatically

```python
# Conversation 1
User: "I prefer dark mode and use Python"
Assistant: "Got it, I'll remember that!"

# Auto Memory extracts:
# - PREFERENCE: dark mode
# - PRODUCT: Python

# Conversation 2 (days later)
User: "Recommend me a code editor"
# Auto Memory retrieves: "User prefers Python, dark mode"
Assistant: "Based on your preference for Python and dark mode,
            I recommend VS Code with a dark theme..."
```

### Example 3: Smart Tool Suggestion

**Scenario**: Automatically suggest relevant tools

```python
# User has tools: Calculator, Weather, Email, Calendar

User: "What's 25 * 47?"
# AutoTool suggests: Calculator (score: 0.95)

User: "Is it raining in London?"
# AutoTool suggests: Weather (score: 0.88)

User: "Send meeting invite for tomorrow"
# AutoTool suggests: Calendar (0.79), Email (0.65)
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Spacy Model Not Found

**Error**: `OSError: [E050] Can't find model 'en_core_web_sm'`

**Solution**:
```bash
python -m spacy download en_core_web_sm
```

#### Issue 2: Sentence-Transformers Download Slow

**Error**: Slow first-time model download

**Solution**: Pre-download model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
# Downloads to ~/.cache/torch/sentence_transformers/
```

#### Issue 3: N8N Connection Timeout

**Error**: `N8N workflow timeout after 120s`

**Solution**: Increase timeout in configuration:
```json
{
  "timeout_seconds": 300,
  "retry_config": {"max_retries": 5, "backoff": 2}
}
```

#### Issue 4: Auto Memory Not Extracting

**Error**: No entities extracted from conversation

**Debugging**:
```python
# Check Spacy is working
import spacy
nlp = spacy.load("en_core_web_sm")
doc = nlp("John works at Google")
for ent in doc.ents:
    print(ent.text, ent.label_)
# Should output: John PERSON, Google ORG
```

#### Issue 5: AutoTool Not Suggesting

**Error**: No tools suggested for query

**Debugging**:
```python
# Check similarity threshold
# Lower threshold in valves:
{"similarity_threshold": 0.3}  # More permissive

# Check tools exist
from open_webui.models.tools import Tools
tools = Tools.get_tools_by_user_id(user_id)
print(f"Available tools: {len(tools)}")
```

---

## Monitoring

### Key Metrics

#### N8N Integration

```python
from open_webui.models.n8n_config import N8NExecutions

# Get analytics
analytics = N8NExecutions.get_analytics(config_id)
print(f"Success rate: {analytics['success_rate'] * 100:.1f}%")
print(f"Avg duration: {analytics['average_duration_ms']}ms")
```

#### Auto Memory

```bash
# Check memory count
SELECT COUNT(*) FROM memories WHERE source='auto_memory';

# Check by type
SELECT type, COUNT(*) FROM memory_metadata GROUP BY type;
```

#### AutoTool Filter

```bash
# Check suggestion accuracy (user-reported)
# Add to function metadata
{
  "suggestions_shown": 150,
  "suggestions_accepted": 112,
  "accuracy": 0.747
}
```

### Health Checks

```bash
# Check all features
curl http://localhost:8080/api/health

# Check N8N configs
curl http://localhost:8080/api/n8n/configs \
  -H "Authorization: Bearer TOKEN"

# Check memory count
curl http://localhost:8080/api/memories/ \
  -H "Authorization: Bearer TOKEN"
```

---

## Performance Optimization

### Auto Memory

```python
# Batch processing for large conversations
class Valves:
    max_context_length = 100  # Reduce from 200
    deduplicate = True  # Enable deduplication
```

### AutoTool Filter

```python
# Cache embeddings
class Valves:
    cache_embeddings = True
    top_k = 3  # Don't compute scores for all tools
```

### N8N Integration

```python
# Use connection pooling
async with httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100)
) as client:
    # Reuse connections
```

---

## Security Considerations

1. **N8N API Keys**: Store securely, never commit to git
2. **User Isolation**: All features respect user_id boundaries
3. **Input Validation**: All inputs validated (see models)
4. **Rate Limiting**: Apply rate limits to N8N endpoints
5. **Memory Privacy**: ChromaDB collections are user-scoped

---

## Support & Maintenance

### Logs

```bash
# Check application logs
tail -f /var/log/open-webui/app.log | grep -E 'N8N|AutoMemory|AutoTool'

# Check Python logs
journalctl -u open-webui -f
```

### Updates

```bash
# Update dependencies
pip install --upgrade spacy sentence-transformers scikit-learn

# Update Spacy model
python -m spacy download en_core_web_sm --upgrade
```

---

## Success Metrics

After deployment, track:

- **N8N Integration**:
  - Workflow success rate > 95%
  - Average latency < 2s (non-streaming)
  - Error rate < 5%

- **Auto Memory**:
  - Entity extraction accuracy > 85%
  - Memory storage success > 98%
  - Deduplication rate > 50%

- **AutoTool Filter**:
  - Suggestion accuracy > 75%
  - User acceptance rate > 60%
  - Query processing time < 500ms

---

## Changelog

### Version 1.0.0 (November 1, 2025)

**Added**:
- N8N Integration with SSE streaming
- Auto Memory with NER
- AutoTool Filter with semantic similarity
- Comprehensive test suite (125+ tests)
- Database migrations
- Documentation

**Files Created**:
- `backend/open_webui/models/n8n_config.py`
- `backend/open_webui/routers/n8n_integration.py`
- `backend/open_webui/functions/auto_memory.py`
- `backend/open_webui/functions/auto_tool_filter.py`
- `backend/open_webui/migrations/versions/add_n8n_integration.py`
- `tests/integration/test_n8n_integration.py`
- `tests/test_auto_memory_function.py`
- `tests/test_auto_tool_filter.py`

**Modified**:
- `backend/requirements.txt` - Added dependencies

---

## Contact

For issues or questions:
- GitHub: https://github.com/open-webui/open-webui/issues
- Documentation: See `IMPLEMENTATION_PLAN.md`

---

**Deployment Status**: ✅ Ready for Production

**Estimated Deployment Time**: 30-45 minutes
**Risk Level**: Low (non-breaking changes, all features optional)
**Rollback Time**: < 5 minutes
