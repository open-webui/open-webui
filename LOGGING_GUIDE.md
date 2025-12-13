# Comprehensive Logging Guide for Embedding Pipeline

## Overview

This guide explains where to find logs and how to use the enhanced logging system to debug embedding failures in Redis/RQ environment.

---

## Log Locations

### 1. Main Application Logs (FastAPI/OpenWebUI)

**Default Locations:**
- **Local/Docker**: stdout/stderr (redirected to console)
- **Systemd**: `journalctl -u open-webui -f`
- **Docker**: `docker logs -f <container-name>`
- **Kubernetes**: `kubectl logs -f <pod-name>`
- **Custom file**: Set `LOG_FILE` environment variable

**How to Access:**
```bash
# Docker
docker logs -f open-webui

# Kubernetes
kubectl logs -f <pod-name> -c open-webui

# Systemd
journalctl -u open-webui -f

# Direct stdout (if running manually)
# Logs appear in terminal where uvicorn is running
```

---

### 2. Worker Logs (RQ Workers)

**Default Locations:**
- **Local**: `/tmp/rq-worker.log` (if redirected) or stdout/stderr
- **Docker**: stdout/stderr (check container logs)
- **Kubernetes**: `kubectl logs -f <worker-pod-name>`
- **Systemd**: `journalctl -u rq-worker -f`

**How to Access:**
```bash
# Local file
tail -f /tmp/rq-worker.log

# Docker
docker logs -f <worker-container-name>

# Kubernetes
kubectl logs -f <worker-pod-name>

# Systemd
journalctl -u rq-worker -f

# Direct stdout (if running manually)
python -m open_webui.workers.start_worker
# Logs appear in terminal
```

**Note**: Worker logs use both `print()` and `log.info()` to ensure visibility. All critical steps are logged with `[STEP X]` prefixes.

---

### 3. Redis Logs

**Default Locations:**
- **Local**: `/var/log/redis/redis-server.log`
- **Docker**: `docker logs -f <redis-container-name>`
- **Kubernetes**: `kubectl logs -f <redis-pod-name>`
- **Systemd**: `journalctl -u redis -f`

**How to Access:**
```bash
# Local
tail -f /var/log/redis/redis-server.log

# Docker
docker logs -f redis

# Kubernetes
kubectl logs -f <redis-pod-name>
```

---

## Unified Log Viewer Script

A script is provided to view all logs together: `view_logs.sh`

### Usage:

```bash
# Interactive menu
./view_logs.sh

# View main app logs only
./view_logs.sh main

# View worker logs only
./view_logs.sh worker

# View Redis logs only
./view_logs.sh redis

# View all logs together (interleaved)
./view_logs.sh all

# View main app + worker combined
./view_logs.sh combined
```

### Custom Log Locations:

```bash
export MAIN_APP_LOG=/path/to/main.log
export WORKER_LOG=/path/to/worker.log
export REDIS_LOG=/path/to/redis.log
./view_logs.sh
```

---

## Log Format and Markers

### Print Statements (Easy to Read)

All critical steps use `print()` statements with clear markers:

```
[PROCESS FILE] Starting file processing request
  [STEP 1] Checking embedding engine: portkey
  [STEP 1.1] Engine is OpenAI/Portkey, retrieving API key...
  [STEP 1.2] API key retrieval result:
    embedding_api_key is None: False
    embedding_api_key length: 51
  [STEP 1.3] ✅ API key retrieved and validated

[EMBEDDING] Starting embedding generation
  [STEP 1] User context:
    user_email: user@example.com
  [STEP 2] Retrieving API key from config...
  [STEP 2.1] API key retrieval result:
    user_api_key is None: False
    user_api_key length: 51
  [STEP 2.2] ✅ API key validated
  [STEP 3] Getting base URL...
  [STEP 4] Validating API key before embedding function creation...
  [STEP 5] Creating embedding function...
  [STEP 6] Generating embeddings for 10 chunks...
  [STEP 6.1] ✅ Embeddings generated successfully
  [STEP 7] Inserting into vector DB...
  [STEP 7.1] ✅ Successfully inserted
```

### Log Levels

- **ERROR/❌**: Critical failures that stop processing
- **WARNING/⚠️**: Issues that may cause problems but don't stop processing
- **INFO/✅**: Successful operations and progress updates
- **DEBUG**: Detailed debugging information

---

## Key Log Markers to Watch For

### 1. API Key Validation

**Success:**
```
[STEP 1.2] API key retrieval result:
  embedding_api_key is None: False
  embedding_api_key length: 51
[STEP 1.3] ✅ API key retrieved and validated
```

**Failure:**
```
[STEP 1.2] API key retrieval result:
  embedding_api_key is None: True
  embedding_api_key length: 0
[STEP 1.3] ❌ CRITICAL BUG: No embedding API key configured...
```

### 2. Embedding Function Initialization

**Success:**
```
[EMBEDDING INIT] Starting embedding function initialization
  [STEP 1] API key resolution: Using provided key
  [STEP 4] ✅ API key validated
  [STEP 6] ✅ Embedding function created successfully
[EMBEDDING INIT] ✅ Initialization completed successfully
```

**Failure:**
```
[EMBEDDING INIT] Starting embedding function initialization
  [STEP 4] ❌ CRITICAL: No embedding API key provided in job!
[EMBEDDING INIT] ❌ Failed to initialize EMBEDDING_FUNCTION
```

### 3. Embedding Generation

**Success:**
```
[STEP 6] Generating embeddings for 10 chunks in a single batch
[STEP 6.1] Embedding generation result:
  embeddings is None: False
  embeddings length: 10
  first embedding length: 1536
[STEP 6.1] ✅ Embeddings generated successfully
```

**Failure:**
```
[STEP 6] Generating embeddings for 10 chunks...
[STEP 6] ❌ Failed to generate embeddings: 401 Unauthorized
```

### 4. Vector DB Insert

**Success:**
```
[STEP 7] Inserting embeddings into 2 collection(s)
  [STEP 7.1] ✅ Successfully inserted into collection: file-123
  [STEP 7.2] ✅ Successfully inserted into collection: knowledge-456
[EMBEDDING] ✅ All embeddings saved successfully
```

**Failure:**
```
[STEP 7.1] Processing collection: file-123
[STEP 7.1] ❌ Failed to insert into collection file-123: Connection error
```

---

## Debugging Workflow

### Step 1: Check Job Enqueueing (Main App)

Look for:
```
[PROCESS FILE] Starting file processing request
  [STEP 1] Checking embedding engine: portkey
  [STEP 1.2] API key retrieval result:
    embedding_api_key is None: False  ← Should be False
    embedding_api_key length: 51      ← Should be > 0
  [STEP 1.3] ✅ API key retrieved and validated
```

**If API key is None:**
- Check admin has configured API key in Settings > Documents
- Check user is in a group created by that admin
- Check `UserScopedConfig.get()` is working

### Step 2: Check Worker Job Processing

Look for:
```
[JOB START] Processing file job: file_id=...
  INPUT PARAMETERS:
    embedding_api_key=PROVIDED (51 chars, ends with ...xyz)  ← Should be PROVIDED
  [STEP 1.2] Validating embedding API key...
    embedding_api_key is None: False  ← Should be False
  [STEP 1.2] ✅ API key validation passed
  [STEP 1.3] Initializing EMBEDDING_FUNCTION...
  [STEP 1.3] ✅ EMBEDDING_FUNCTION initialized successfully
```

**If API key is None in job:**
- Check `enqueue_file_processing_job()` is passing the key
- Check job serialization (should include key)

### Step 3: Check Embedding Generation

Look for:
```
[EMBEDDING] Starting embedding generation
  [STEP 2.1] API key retrieval result:
    user_api_key is None: False  ← Should be False
  [STEP 4] Validating API key before embedding function creation...
    api_key_to_use is None: False  ← Should be False
  [STEP 5] Creating embedding function...
  [STEP 6] Generating embeddings for 10 chunks...
  [STEP 6.1] ✅ Embeddings generated successfully
```

**If embedding generation fails:**
- Check API key is valid (not expired/revoked)
- Check base URL is correct
- Check embedding API is accessible
- Check rate limits

### Step 4: Check Vector DB Save

Look for:
```
[STEP 7] Inserting embeddings into 2 collection(s)
  [STEP 7.1] ✅ Successfully inserted into collection: file-123
  [STEP 7.2] ✅ Successfully inserted into collection: knowledge-456
[EMBEDDING] ✅ All embeddings saved successfully
```

**If vector DB insert fails:**
- Check vector DB connection
- Check collection exists or can be created
- Check vector dimensions match
- Check disk space

---

## Common Error Patterns

### Pattern 1: API Key is None

**Symptoms:**
```
embedding_api_key is None: True
embedding_api_key length: 0
❌ CRITICAL BUG: No embedding API key provided...
```

**Causes:**
- Admin hasn't configured API key
- User not in group
- `UserScopedConfig.get()` returning None
- API key not passed to job

**Fix:**
1. Check admin has API key in Settings > Documents
2. Check user is in group created by that admin
3. Check `RAG_OPENAI_API_KEY.get(user.email)` returns value

---

### Pattern 2: Embedding Function is None

**Symptoms:**
```
EMBEDDING_FUNCTION is None: True
❌ CRITICAL BUG: EMBEDDING_FUNCTION is None after initialization
```

**Causes:**
- API key is None (see Pattern 1)
- Base URL is invalid
- Embedding model not configured
- `get_embedding_function()` returned None

**Fix:**
1. Check API key is not None
2. Check base URL is valid (not "None" string)
3. Check embedding model is configured
4. Check `get_embedding_function()` implementation

---

### Pattern 3: Embedding Generation Fails

**Symptoms:**
```
[STEP 6] Generating embeddings for 10 chunks...
[STEP 6] ❌ Failed to generate embeddings: 401 Unauthorized
```

**Causes:**
- Invalid API key
- API key expired/revoked
- Wrong base URL
- Rate limit exceeded
- Network error

**Fix:**
1. Verify API key is valid
2. Check base URL is correct
3. Check API rate limits
4. Check network connectivity

---

### Pattern 4: Vector DB Insert Fails

**Symptoms:**
```
[STEP 7.1] ❌ Failed to insert into collection: Connection error
```

**Causes:**
- Vector DB connection lost
- Collection doesn't exist
- Vector dimension mismatch
- Disk full
- Transaction error

**Fix:**
1. Check vector DB connection
2. Check collection exists
3. Check vector dimensions
4. Check disk space

---

## Log Search Tips

### Find All API Key Issues:
```bash
grep -i "api key\|embedding_api_key\|user_api_key" <log-file> | grep -i "none\|empty\|❌"
```

### Find All Embedding Failures:
```bash
grep -i "embedding\|❌\|failed" <log-file>
```

### Find All Worker Errors:
```bash
grep -i "\[JOB\|\[STEP\|❌" <worker-log-file>
```

### Find Specific File Processing:
```bash
grep "file_id=<file-id>" <log-file>
```

### Find All Critical Bugs:
```bash
grep "CRITICAL BUG" <log-file>
```

---

## Real-Time Monitoring

### Watch Main App + Worker Logs Together:

```bash
# Using the script
./view_logs.sh combined

# Or manually
(tail -f /path/to/main.log | sed 's/^/[MAIN] /' &) && \
(tail -f /path/to/worker.log | sed 's/^/[WORKER] /' &) && \
wait
```

### Watch for Specific Patterns:

```bash
# Watch for API key issues
tail -f <log-file> | grep --color=always -i "api key\|embedding_api_key"

# Watch for errors
tail -f <log-file> | grep --color=always -i "❌\|error\|failed"

# Watch for embedding steps
tail -f <log-file> | grep --color=always -i "\[STEP\|\[EMBEDDING"
```

---

## Kubernetes-Specific Log Access

### View All Pods:
```bash
kubectl get pods
```

### View Main App Logs:
```bash
kubectl logs -f <main-app-pod-name>
```

### View Worker Logs:
```bash
kubectl logs -f <worker-pod-name>
```

### View Redis Logs:
```bash
kubectl logs -f <redis-pod-name>
```

### View All Logs Together:
```bash
# All pods with label app=open-webui
kubectl logs -f -l app=open-webui

# Specific container in pod
kubectl logs -f <pod-name> -c <container-name>
```

### View Logs with Timestamps:
```bash
kubectl logs -f <pod-name> --timestamps
```

### View Last N Lines:
```bash
kubectl logs --tail=100 <pod-name>
```

### Search Logs:
```bash
kubectl logs <pod-name> | grep "CRITICAL BUG"
```

---

## Docker-Specific Log Access

### View Container Logs:
```bash
# All logs
docker logs -f <container-name>

# Last 100 lines
docker logs --tail=100 <container-name>

# With timestamps
docker logs -f --timestamps <container-name>

# Since specific time
docker logs --since 10m <container-name>
```

### View Multiple Containers:
```bash
# Main app
docker logs -f open-webui &

# Worker
docker logs -f open-webui-worker &

# Redis
docker logs -f redis &

wait
```

---

## Log File Rotation

If logs get too large, consider setting up log rotation:

### Using logrotate:
```bash
# /etc/logrotate.d/open-webui
/path/to/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Using Docker:
```bash
docker run --log-opt max-size=10m --log-opt max-file=3 ...
```

---

## Summary

1. **Main App Logs**: Check API key retrieval and job enqueueing
2. **Worker Logs**: Check job processing and embedding generation
3. **Redis Logs**: Check job queue and Redis connectivity
4. **Use `view_logs.sh`**: Unified viewer for all logs
5. **Look for markers**: `[STEP X]`, `✅`, `❌`, `[EMBEDDING]`
6. **Check API key**: Should never be None
7. **Check embedding function**: Should never be None
8. **Check errors**: Look for `❌ CRITICAL BUG` messages

---

## Quick Reference

```bash
# View all logs together
./view_logs.sh all

# View worker logs only
./view_logs.sh worker

# View main app logs only  
./view_logs.sh main

# Search for API key issues
grep -i "api key.*none\|❌.*api key" <log-file>

# Search for embedding failures
grep -i "❌\|failed.*embedding" <log-file>

# Follow logs in real-time
tail -f <log-file>
```

