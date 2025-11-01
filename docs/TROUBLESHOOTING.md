# Troubleshooting Guide - Open WebUI Automation Features

## Overview

This guide covers common issues and solutions for:
- **N8N Integration**: Workflow automation problems
- **Auto Memory**: NER and memory storage issues
- **AutoTool Filter**: Tool suggestion and matching problems

---

## Quick Diagnostic Checklist

Before diving into specific issues, verify:

```bash
# 1. Check Python version (must be 3.9-3.12)
python --version

# 2. Verify dependencies installed
pip list | grep -E "spacy|sentence-transformers|scikit-learn"

# 3. Check Open WebUI is running
curl http://localhost:8080/api/health

# 4. View logs
tail -f /var/log/open-webui/app.log
# OR (Docker)
docker logs -f open-webui

# 5. Test database connectivity
python -c "from open_webui.internal.db import get_db; print('DB OK')"
```

---

## Installation Issues

### Issue: Python Version Incompatibility

**Symptoms**:
```
ERROR: unstructured==0.16.17 does not support Python 3.13
```

**Cause**: Open WebUI requires Python 3.9-3.12, not 3.13+

**Solution**:
```bash
# Check current version
python --version

# Install compatible Python version
# Option 1: Using pyenv
pyenv install 3.12.0
pyenv local 3.12.0

# Option 2: Using conda
conda create -n openwebui python=3.12
conda activate openwebui

# Option 3: Using venv with system Python 3.12
python3.12 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: Spacy Model Not Found

**Symptoms**:
```
OSError: [E050] Can't find model 'en_core_web_sm'
RuntimeError: Spacy model not installed
```

**Cause**: Spacy NER model not downloaded

**Solution**:
```bash
# Download the model
python -m spacy download en_core_web_sm

# Verify installation
python -c "import spacy; spacy.load('en_core_web_sm'); print('Model OK')"

# If download fails (firewall/proxy):
# 1. Download manually from https://github.com/explosion/spacy-models/releases
# 2. Install locally
pip install en_core_web_sm-3.7.0-py3-none-any.whl

# Restart Open WebUI
systemctl restart open-webui
```

**Prevention**: Add model check to startup script:
```python
# In startup.py
try:
    import spacy
    spacy.load("en_core_web_sm")
except OSError:
    print("WARNING: Spacy model not installed. Auto Memory will not work.")
    print("Run: python -m spacy download en_core_web_sm")
```

---

### Issue: Sentence Transformers Download Fails

**Symptoms**:
```
URLError: <urlopen error [Errno 111] Connection refused>
Cannot download sentence transformer model
```

**Cause**: Network issues or HuggingFace API unavailable

**Solution**:
```bash
# 1. Test connectivity
ping huggingface.co
curl https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

# 2. Manual download
export HF_HOME=/path/to/models
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# 3. Use local cache
export SENTENCE_TRANSFORMERS_HOME=/path/to/models
export TRANSFORMERS_CACHE=/path/to/models

# 4. Download via proxy (if corporate network)
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

---

### Issue: Database Migration Failed

**Symptoms**:
```
sqlalchemy.exc.OperationalError: no such table: n8n_config
```

**Cause**: Database migration not applied

**Solution**:
```bash
# 1. Check current migration version
cd backend
alembic current

# 2. Run migrations
alembic upgrade head

# 3. Verify tables exist
sqlite3 webui.db
> .tables
> .schema n8n_config
> .quit

# 4. If migration file missing, check git
git status
git pull origin main

# 5. Restart Open WebUI
systemctl restart open-webui
```

**Rollback if needed**:
```bash
# Revert last migration
alembic downgrade -1

# Revert to specific version
alembic downgrade <revision_id>
```

---

## N8N Integration Issues

### Issue: "Configuration not found"

**Symptoms**:
```json
{
  "detail": "Configuration not found"
}
```

**Debugging**:
```bash
# 1. List all configs for user
curl http://localhost:8080/api/n8n/configs \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. Check database directly
sqlite3 webui.db "SELECT id, user_id, name FROM n8n_config;"

# 3. Verify user_id matches
# Check JWT token payload
python -c "import jwt; print(jwt.decode('YOUR_TOKEN', options={'verify_signature': False}))"
```

**Solutions**:
- Verify `config_id` is correct UUID
- Ensure user owns the configuration (check `user_id`)
- Configuration may have been deleted (check with admin)

---

### Issue: "Workflow timeout after Xs"

**Symptoms**:
```json
{
  "status": "timeout",
  "error_message": "Workflow timeout after 120s"
}
```

**Solutions**:

**Option 1: Increase Timeout**
```python
# Update configuration
PUT /api/n8n/config/{config_id}
{
  "timeout_seconds": 300  # 5 minutes instead of 2
}
```

**Option 2: Optimize N8N Workflow**
```
# In N8N workflow editor:
1. Remove unnecessary nodes
2. Use "Execute Once" instead of loops where possible
3. Add intermediate HTTP Response nodes for long workflows
4. Break into smaller workflows (chain with webhooks)
```

**Option 3: Enable Streaming**
```python
# For long workflows, use streaming
POST /api/n8n/trigger/{config_id}/stream
# Prevents timeouts, provides real-time updates
```

---

### Issue: "Connection refused" to N8N Server

**Symptoms**:
```
httpx.ConnectError: [Errno 111] Connection refused
```

**Debugging**:
```bash
# 1. Verify N8N server is running
curl http://n8n.example.com/webhook/test

# 2. Check network connectivity
ping n8n.example.com
telnet n8n.example.com 5678

# 3. Verify firewall rules
sudo iptables -L | grep 5678

# 4. Check N8N logs
docker logs n8n
```

**Solutions**:
- Start N8N server: `docker-compose up -d n8n`
- Update `n8n_url` in configuration (check protocol: http vs https)
- Add firewall exception
- Verify N8N webhook is active (toggle in N8N editor)

---

### Issue: "Invalid webhook_id format"

**Symptoms**:
```json
{
  "detail": "Webhook ID must contain only alphanumeric characters, hyphens, and underscores"
}
```

**Solutions**:
```python
# Invalid examples
webhook_id = "process.emails"   # No dots
webhook_id = "handle@orders"    # No @ symbols
webhook_id = "workflow#123"     # No # symbols

# Valid examples
webhook_id = "process-emails"   # ✓
webhook_id = "handle_orders"    # ✓
webhook_id = "workflow123"      # ✓
webhook_id = "my-workflow-v2"   # ✓
```

---

### Issue: N8N Returns 401 Unauthorized

**Symptoms**:
```
httpx.HTTPStatusError: 401 Unauthorized
```

**Solutions**:

**Verify API Key**:
```bash
# Test manually
curl https://n8n.example.com/webhook/test \
  -H "Authorization: Bearer YOUR_N8N_API_KEY"
```

**Update Configuration**:
```python
PUT /api/n8n/config/{config_id}
{
  "api_key": "correct-n8n-api-key"
}
```

**Check N8N Webhook Settings**:
1. Open N8N workflow editor
2. Click Webhook node
3. Verify "Authentication" is set correctly
4. If using "Header Auth", ensure header name matches

---

## Auto Memory Issues

### Issue: No Memories Being Extracted

**Symptoms**:
- Metadata shows `"extracted": 0`
- No entities in ChromaDB

**Debugging**:
```python
# Test extraction manually
from open_webui.functions.auto_memory import Filter

filter = Filter()
text = "My name is Alice and I work at Microsoft"
entities = filter._extract_entities(text)
print(entities)
```

**Solutions**:

**1. Auto Memory Disabled**
```python
# Check Valves in Admin Panel
enabled = True  # Must be True
```

**2. Confidence Threshold Too High**
```python
# Lower threshold
min_confidence = 0.5  # Try lower value (default: 0.7)
```

**3. No Entities in Text**
```python
# Test with entity-rich text
text = "John Smith works at Google in San Francisco since January 2024"
# Should extract: PERSON, ORG, GPE, DATE
```

**4. Wrong Message Role**
```python
# Auto Memory only processes assistant messages (outlet filter)
# User messages are skipped
# To process user messages, modify code to check:
if last_message.get("role") in ["assistant", "user"]:
```

---

### Issue: Duplicate Memories Stored

**Symptoms**:
- Same entity stored multiple times
- ChromaDB query returns duplicates

**Solutions**:

**Enable Deduplication**:
```python
# Check Valves
deduplicate = True  # Must be enabled
```

**Adjust Deduplication Window**:
```python
# In auto_memory.py
_dedup_window_seconds = 3600  # 1 hour instead of 10 minutes
```

**Manual Cleanup**:
```python
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

# Delete duplicates
collection_name = "user-memory-user-123"
VECTOR_DB_CLIENT.delete_collection(collection_name)
# Next extraction will create fresh collection
```

---

### Issue: ChromaDB Connection Error

**Symptoms**:
```
chromadb.errors.ConnectionError: Could not connect to ChromaDB
```

**Debugging**:
```bash
# 1. Check ChromaDB service
systemctl status chromadb
docker ps | grep chroma

# 2. Verify environment variables
echo $CHROMA_HOST
echo $CHROMA_PORT

# 3. Test connection
curl http://localhost:8000/api/v1/heartbeat
```

**Solutions**:

**Start ChromaDB**:
```bash
# Docker
docker-compose up -d chromadb

# Standalone
chroma run --host localhost --port 8000

# Verify
curl http://localhost:8000/api/v1/heartbeat
# Should return: {"status": "ok"}
```

**Update Configuration**:
```bash
# In .env or environment
export CHROMA_HOST=localhost
export CHROMA_PORT=8000

# Restart Open WebUI
systemctl restart open-webui
```

---

### Issue: "Spacy model not installed" Runtime Error

**Symptoms**:
```
RuntimeError: Spacy model not installed. Run: python -m spacy download en_core_web_sm
```

**Root Cause**: Model download attempted via `subprocess.run()` (security risk, now removed)

**Solution**:
```bash
# Manual installation (required)
python -m spacy download en_core_web_sm

# Verify
python -c "import spacy; spacy.load('en_core_web_sm')"

# Restart Open WebUI
systemctl restart open-webui
```

**Note**: Automatic download was removed for security. Manual installation is now required.

---

## AutoTool Filter Issues

### Issue: No Tools Suggested

**Symptoms**:
- Metadata shows `"tool_suggestions": []`
- Empty recommendations

**Debugging**:
```python
# Test tool retrieval
from open_webui.models.tools import Tools

tools = Tools.get_tools_by_user_id("user-123")
print(f"Available tools: {len(tools)}")

for tool in tools:
    print(f"- {tool.name}: {tool.meta.get('description', 'NO DESCRIPTION')}")
```

**Solutions**:

**1. AutoTool Disabled**
```python
# Check Valves
enabled = True
```

**2. No Tools Available**
```bash
# Create at least one tool in Admin Panel
# Verify tools have descriptions
```

**3. Similarity Threshold Too High**
```python
# Lower threshold
similarity_threshold = 0.3  # Try very low value
top_k = 5  # Increase to see more results
```

**4. Query Too Vague**
```python
# Test with specific query
query = "Calculate 5 + 3"  # Instead of "Help me"

# Verify tool has good description
tool.meta["description"] = "Perform arithmetic calculations like addition, subtraction, multiplication, division"
```

---

### Issue: Wrong Tools Suggested

**Symptoms**:
- Irrelevant tools have high scores
- Expected tools not in results

**Solutions**:

**1. Raise Similarity Threshold**
```python
similarity_threshold = 0.7  # Higher = more strict
```

**2. Improve Tool Descriptions**
```python
# Bad description
"Email tool"

# Good description
"Send emails via SMTP with attachments, HTML content, and CC/BCC support"
```

**3. Use Better Model**
```python
# In Valves
model_name = "all-mpnet-base-v2"  # More accurate than default
```

**4. Check Query Embedding**
```python
# Debug similarity scores
from open_webui.functions.auto_tool_filter import Filter

filter = Filter()
query = "Send email"
tools = [...]  # Your tools

ranked = filter._rank_tools(query, tools)
for tool in ranked:
    print(f"{tool['name']}: {tool['score']}")
```

---

### Issue: Slow Performance (>1s)

**Symptoms**:
- Tool suggestions take too long
- Request latency high

**Debugging**:
```python
import time

start = time.time()
# Run AutoTool filter
suggestions = filter.inlet(body, user)
duration = time.time() - start

print(f"AutoTool latency: {duration*1000}ms")
```

**Solutions**:

**1. Enable Caching**
```python
cache_embeddings = True  # Must be enabled
```

**2. Use Smaller Model**
```python
model_name = "all-MiniLM-L6-v2"  # Fastest (default)
```

**3. Reduce Top-K**
```python
top_k = 2  # Fewer results = faster
```

**4. Remove Unused Tools**
```sql
-- Delete old/unused tools from database
DELETE FROM tools WHERE id IN ('tool-1', 'tool-2');
```

**5. Profile Code**
```python
import cProfile

cProfile.run('filter.inlet(body, user)', 'profile.stats')

# Analyze
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(10)
```

---

## Performance Issues

### Issue: High Memory Usage

**Symptoms**:
```
MemoryError: Cannot allocate memory
High RSS in process monitoring
```

**Debugging**:
```bash
# Check memory usage
ps aux | grep open-webui
top -p $(pgrep -f open-webui)

# Python memory profiler
pip install memory-profiler
python -m memory_profiler backend/main.py
```

**Solutions**:

**1. Verify Cache Eviction**
```python
# Check cache sizes
from open_webui.functions.auto_memory import Filter as AutoMem
from open_webui.functions.auto_tool_filter import Filter as AutoTool

automem = AutoMem()
autotool = AutoTool()

print(f"Auto Memory cache: {len(automem._recent_memories)}")  # Should be <= 1000
print(f"AutoTool cache: {len(autotool.tool_cache)}")  # Should be <= 500
```

**2. Reduce Cache Sizes**
```python
# In filters
_cache_max_size = 500  # Reduce from 1000
```

**3. Unload Models When Idle**
```python
# Add to Filter.__del__()
def __del__(self):
    if self.model:
        del self.model
        import gc
        gc.collect()
```

---

### Issue: Slow Database Queries

**Symptoms**:
```
Slow response times
Database lock errors
```

**Solutions**:

**1. Add Indexes** (already included in migration):
```sql
CREATE INDEX idx_n8n_config_user_id ON n8n_config(user_id);
CREATE INDEX idx_n8n_executions_config_id ON n8n_executions(config_id);
CREATE INDEX idx_n8n_executions_created_at ON n8n_executions(created_at);
```

**2. Analyze Queries**:
```python
# Enable SQLAlchemy logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

**3. Cleanup Old Data**:
```sql
-- Delete old N8N executions (keep last 90 days)
DELETE FROM n8n_executions
WHERE created_at < (strftime('%s', 'now') - 90*24*60*60);

-- Vacuum database
VACUUM;
```

---

## Security Issues

### Issue: API Key Exposed in Logs

**Symptoms**:
- API keys visible in logs
- Secrets in error messages

**Solutions**:

**1. Configure Logging**:
```python
# In logging config
import logging

class SensitiveFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        # Redact API keys
        import re
        msg = re.sub(r'api_key["\']:\s*["\'][^"\']+["\']', 'api_key: "***"', msg)
        return msg
```

**2. Encrypt API Keys in Database**:
```python
# TODO: Implement in production
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt before storing
encrypted = cipher.encrypt(api_key.encode())

# Decrypt when using
api_key = cipher.decrypt(encrypted).decode()
```

---

### Issue: Command Injection Risk

**Symptoms**:
- Security scanners flag `subprocess.run()`
- Arbitrary code execution possible

**Solution**: Already fixed in latest version

```python
# REMOVED (vulnerable):
subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])

# REPLACED WITH (secure):
raise RuntimeError("Spacy model not installed. Run: python -m spacy download en_core_web_sm")
```

**Verification**:
```bash
# Search for subprocess usage
grep -r "subprocess" backend/open_webui/functions/

# Should return no results in auto_memory.py
```

---

## Debugging Techniques

### Enable Debug Logging

```python
# In .env or environment
LOG_LEVEL=DEBUG

# Or programmatically
import logging
logging.getLogger('open_webui').setLevel(logging.DEBUG)

# View logs
tail -f /var/log/open-webui/app.log | grep -E "N8N|AutoTool|AutoMemory"
```

### Test Features Independently

**N8N Integration**:
```bash
# Create config
curl -X POST http://localhost:8080/api/n8n/config \
  -H "Authorization: Bearer TOKEN" \
  -d '{"name": "Test", "n8n_url": "http://n8n.local", "webhook_id": "test"}'

# Trigger workflow
curl -X POST http://localhost:8080/api/n8n/trigger/CONFIG_ID \
  -H "Authorization: Bearer TOKEN" \
  -d '{"prompt": "test"}'
```

**Auto Memory**:
```python
# Test extraction
from open_webui.functions.auto_memory import Filter

filter = Filter()
result = filter._extract_entities("John works at Google")
print(result)
```

**AutoTool**:
```python
# Test ranking
from open_webui.functions.auto_tool_filter import Filter

filter = Filter()
tools = [...]  # Mock tools
ranked = filter._rank_tools("Calculate 5 + 3", tools)
print(ranked)
```

### Analyze Request Flow

```python
# Add middleware to log all requests
from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    print(f"{request.method} {request.url.path} - {duration*1000}ms")
    return response
```

---

## Common Error Messages

### `ModuleNotFoundError: No module named 'spacy'`

**Solution**:
```bash
pip install spacy>=3.7.0
```

### `ModuleNotFoundError: No module named 'sentence_transformers'`

**Solution**:
```bash
pip install sentence-transformers>=2.2.0
```

### `sqlalchemy.exc.OperationalError: no such table`

**Solution**:
```bash
alembic upgrade head
systemctl restart open-webui
```

### `403 Forbidden: Not authorized to access this configuration`

**Solution**:
- Verify you own the configuration (user_id matches)
- Check authentication token is valid
- Ensure user has necessary permissions

### `ValueError: Data payload too large (max 1048576 bytes)`

**Solution**:
- Reduce size of `data` object in N8N trigger request
- Send large files via URLs instead of inline
- Split into multiple smaller requests

---

## Health Checks

### System Health Check Script

```bash
#!/bin/bash

echo "=== Open WebUI Automation Features Health Check ==="

# 1. Python version
echo "1. Python Version:"
python --version

# 2. Dependencies
echo "2. Dependencies:"
pip list | grep -E "spacy|sentence-transformers|scikit-learn|httpx|chromadb"

# 3. Spacy model
echo "3. Spacy Model:"
python -c "import spacy; spacy.load('en_core_web_sm'); print('✓ Installed')" 2>&1

# 4. Sentence Transformers
echo "4. Sentence Transformers:"
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('✓ Loaded')" 2>&1

# 5. Database tables
echo "5. Database Tables:"
sqlite3 webui.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'n8n%';"

# 6. ChromaDB
echo "6. ChromaDB:"
curl -s http://localhost:8000/api/v1/heartbeat

# 7. Open WebUI API
echo "7. Open WebUI API:"
curl -s http://localhost:8080/api/health

echo "=== Health Check Complete ==="
```

---

## Getting Help

### Before Asking for Help

1. **Check logs**: Review error messages carefully
2. **Search documentation**: Check feature guides for your issue
3. **Test independently**: Isolate the problem (N8N, AutoMemory, or AutoTool)
4. **Gather info**: Collect version numbers, error messages, logs

### Information to Provide

```
**Environment**:
- Open WebUI version: X.X.X
- Python version: X.X.X
- OS: Linux/Windows/Mac
- Deployment: Docker/Standalone

**Issue**:
- Feature affected: N8N/AutoMemory/AutoTool
- Error message: [Full error]
- Steps to reproduce: [Detailed steps]

**Logs**:
[Relevant log entries]

**Configuration**:
- Valves settings: [Screenshot or JSON]
- Environment variables: [Redacted]
```

### Support Channels

1. **GitHub Issues**: https://github.com/open-webui/open-webui/issues
2. **Documentation**: Check all feature guides first
3. **Community Forum**: [If available]

---

## FAQ

**Q: Why are tests failing with Python 3.13?**
A: Open WebUI requires Python 3.9-3.12. Use Python 3.12 for best compatibility.

**Q: How do I reset Auto Memory for a user?**
A: Delete their ChromaDB collection: `VECTOR_DB_CLIENT.delete_collection(f"user-memory-{user_id}")`

**Q: Can I disable a feature without uninstalling?**
A: Yes, set `enabled = False` in the filter's Valves (Admin Panel → Functions)

**Q: How do I backup N8N configurations?**
A: `sqlite3 webui.db "SELECT * FROM n8n_config;" > n8n_configs.sql`

**Q: What's the maximum N8N timeout?**
A: 600 seconds (10 minutes). Configurable via `timeout_seconds`.

**Q: How do I clear AutoTool cache?**
A: Restart Open WebUI. Cache is in-memory only (not persisted).

---

**Version**: 1.0.0
**Last Updated**: 2025-11-01
**Author**: Claude Code + Parker Dunn
