# How Redis and RQ Manage Work and Embeddings - Current Architecture

## Overview

The system uses **RQ (Redis Queue)** for distributed job processing in a multi-replica Kubernetes environment. This replaces FastAPI BackgroundTasks which only work in-memory on a single pod.

---

## Architecture Components

### 1. **Redis Server**
- **Purpose**: Central message broker and job storage
- **Location**: External Redis instance (configured via `REDIS_URL`)
- **Role**: 
  - Stores job queue (`file_processing` queue)
  - Stores job metadata (status, results, errors)
  - Provides distributed locking for coordination
  - Enables communication between multiple pods

### 2. **RQ (Redis Queue) Library**
- **Purpose**: Python library for job queuing
- **Components**:
  - `Queue`: Manages job enqueueing
  - `Worker`: Processes jobs from queue
  - `Job`: Represents a single job with status tracking

### 3. **Main Application (FastAPI)**
- **Role**: Enqueues jobs to Redis
- **Location**: `backend/open_webui/routers/retrieval.py` → `process_file()`
- **Behavior**: 
  - Validates API key
  - Creates job with all parameters
  - Enqueues to Redis queue
  - Returns immediately (async processing)

### 4. **Worker Processes**
- **Purpose**: Process jobs from Redis queue
- **Location**: `backend/open_webui/workers/file_processor.py`
- **Behavior**:
  - Poll Redis for jobs (blocking wait)
  - Process file when job received
  - Update job status in Redis
  - Handle retries on failure

---

## Complete Flow: File Upload to Embedding Storage

### Step 1: File Upload (Main App)
**Location**: `backend/open_webui/routers/files.py` → `upload_file()`

1. User uploads file via frontend
2. File saved to disk storage
3. File record created in database
4. Calls `process_file()` to start processing

---

### Step 2: Job Enqueueing (Main App)
**Location**: `backend/open_webui/routers/retrieval.py` → `process_file()`

**Process**:
```python
# 1. Check if Redis/RQ is available
if is_job_queue_available():
    # 2. Get user's embedding API key (RBAC-protected)
    embedding_api_key = request.app.state.config.RAG_OPENAI_API_KEY.get(user.email)
    
    # 3. Validate API key exists
    if not embedding_api_key:
        return error  # Early exit
    
    # 4. Enqueue job to Redis
    job_id = enqueue_file_processing_job(
        file_id=file_id,
        content=content,
        collection_name=collection_name,
        knowledge_id=knowledge_id,
        user_id=user.id,
        embedding_api_key=embedding_api_key,  # CRITICAL: Passed to worker
    )
```

**What Happens in Redis**:
- Job is serialized (pickled) and stored in Redis
- Job ID: `file_processing_{file_id}`
- Job status: `QUEUED`
- Job stored in queue: `file_processing`
- Job metadata includes all parameters (file_id, user_id, embedding_api_key, etc.)

**Redis Data Structure**:
```
Redis Keys:
- rq:queue:file_processing (list) - Contains job IDs
- rq:job:{job_id} (hash) - Job metadata and pickled function
- rq:job:{job_id}:result (string) - Job result (after completion)
- rq:job:{job_id}:exc_info (string) - Exception info (if failed)
```

---

### Step 3: Worker Picks Up Job
**Location**: `backend/open_webui/workers/start_worker.py` → `start_worker()`

**Worker Startup**:
1. Worker process starts (separate from main app)
2. Connects to Redis using `REDIS_URL`
3. Creates `Worker` instance for queue `file_processing`
4. Calls `worker.work()` - **blocks waiting for jobs**

**How Worker Gets Jobs**:
- Worker uses Redis `BRPOP` (blocking right pop) on queue
- Blocks indefinitely until job appears
- When job found, worker:
  - Deserializes job from Redis
  - Extracts function to call: `process_file_job`
  - Extracts arguments: `file_id`, `user_id`, `embedding_api_key`, etc.
  - Updates job status to `STARTED` in Redis
  - Calls `process_file_job()` function

**Worker Configuration**:
```python
# Connection pool for workers
worker_pool = ConnectionPool.from_url(
    REDIS_URL,
    decode_responses=False,  # CRITICAL: RQ stores binary pickled data
    socket_timeout=None,  # CRITICAL: No timeout for blocking operations
    max_connections=10,
)

# Create worker
worker = Worker([queue], name=f"file_processor_{hostname}_{pid}")
worker.work()  # Blocks here, processing jobs
```

---

### Step 4: Job Processing (Worker)
**Location**: `backend/open_webui/workers/file_processor.py` → `process_file_job()`

**Process**:

#### 4.1 Initialize Mock Request Object
```python
# Create mock request (workers don't have FastAPI Request object)
request = MockRequest(embedding_api_key=embedding_api_key)

# MockRequest creates:
# - MockApp with AppConfig
# - MockState with config and embedding functions
# - Initializes base embedding function (ef) - no API key needed
```

#### 4.2 Initialize Embedding Function with API Key
```python
# CRITICAL: Initialize per-job with user's API key
request.app.state.initialize_embedding_function(embedding_api_key=embedding_api_key)

# This creates EMBEDDING_FUNCTION that uses:
# - embedding_api_key (from job, RBAC-protected)
# - base_url (from config)
# - embedding_model (from config)
```

**Why Per-Job Initialization?**
- Each admin has their own API key (RBAC)
- Users inherit from group admin's key
- API key must be passed from main app (where user context exists)
- Worker doesn't have user context, so API key comes from job

#### 4.3 Get User Object
```python
user = Users.get_user_by_id(user_id)  # From database

# Set API key in config for save_docs_to_vector_db
if embedding_api_key and user.email:
    request.app.state.config.RAG_OPENAI_API_KEY.set(user.email, embedding_api_key)
```

#### 4.4 Extract Content from File
```python
# Same logic as non-Redis scenario:
# 1. Check if content already in vector DB (cache)
# 2. Check if content in file.data
# 3. Extract from file using Loader (PyPDF, Tika, etc.)
```

#### 4.5 Generate Embeddings
```python
# Call save_docs_to_vector_db or save_docs_to_multiple_collections
# These functions:
# 1. Get API key from config (set in step 4.3)
# 2. Initialize embedding function
# 3. Generate embeddings via API call
# 4. Save to vector database
```

**Embedding Function Flow**:
```python
# In save_docs_to_vector_db():
user_api_key = request.app.state.config.RAG_OPENAI_API_KEY.get(user.email)

embedding_function = get_single_batch_embedding_function(
    engine=RAG_EMBEDDING_ENGINE,
    model=RAG_EMBEDDING_MODEL,
    ef=request.app.state.ef,
    url=base_url,
    key=user_api_key,  # Uses API key from config
    batch_size=RAG_EMBEDDING_BATCH_SIZE,
)

embeddings = embedding_function(texts, user=user)
```

#### 4.6 Save to Vector Database
```python
# Insert embeddings into vector DB (Postgres/SQLite)
VECTOR_DB_CLIENT.insert(
    collection_name=collection_name,
    items=[{
        "id": uuid,
        "text": text,
        "vector": embedding,
        "metadata": metadata,
    }]
)
```

#### 4.7 Update File Status
```python
Files.update_file_metadata_by_id(
    file_id,
    {
        "processing_status": "completed",
        "processing_completed_at": timestamp,
    }
)
```

#### 4.8 Update Job Status in Redis
```python
# RQ automatically updates job status:
# - STARTED → when worker picks up job
# - FINISHED → when function returns successfully
# - FAILED → when exception raised
# - Result stored in Redis: rq:job:{job_id}:result
```

---

## Key Mechanisms

### 1. **Job Serialization**
- Jobs are **pickled** (Python serialization) before storing in Redis
- All arguments must be JSON-serializable (basic validation)
- Function reference (`process_file_job`) is stored, not the function itself
- Worker imports and calls the function

### 2. **API Key Management**
**Problem**: Workers don't have user context (no FastAPI Request)

**Solution**:
1. Main app retrieves API key: `RAG_OPENAI_API_KEY.get(user.email)`
2. API key passed as job argument: `embedding_api_key`
3. Worker receives API key in job
4. Worker sets API key in config: `config.RAG_OPENAI_API_KEY.set(user.email, key)`
5. Embedding functions retrieve from config: `config.RAG_OPENAI_API_KEY.get(user.email)`

**RBAC Flow**:
- Admin sets API key in Settings → stored in database
- `UserScopedConfig.get(email)` checks:
  1. User's own config
  2. Group creator's config (if user in group)
  3. Default (usually None)
- Main app gets key and passes to worker
- Worker uses same key for embeddings

### 3. **Job Retry Logic**
```python
job = queue.enqueue(
    process_file_job,
    retry=Retry(max=MAX_RETRIES, interval=RETRY_DELAY),
    job_timeout=JOB_TIMEOUT,  # Default: 1 hour
)
```

- If job fails (exception raised), RQ automatically retries
- Max retries: `JOB_MAX_RETRIES` (configurable)
- Retry delay: `JOB_RETRY_DELAY` (configurable)
- After max retries, job marked as `FAILED`

### 4. **Job Status Tracking**
**Job Statuses**:
- `QUEUED`: Job in queue, waiting for worker
- `STARTED`: Worker picked up job, processing
- `FINISHED`: Job completed successfully
- `FAILED`: Job failed (exception or timeout)
- `DEFERRED`: Job deferred (not used here)
- `CANCELED`: Job canceled

**Status Storage**:
- Stored in Redis: `rq:job:{job_id}` hash
- Can be queried: `get_job_status(job_id)`
- Main app can check job status via API

### 5. **Distributed Processing**
**Multi-Replica Support**:
- Multiple worker pods can process jobs
- RQ automatically distributes jobs across workers
- Load balancing: First available worker gets job
- No duplicate processing: Job ID ensures uniqueness

**Worker Identification**:
```python
worker_name = f"file_processor_{hostname}_{pid}"
```
- Each worker has unique name
- Helps with debugging and monitoring

### 6. **Connection Management**
**Main App**:
- Uses connection pool: `get_redis_pool(REDIS_URL)`
- Queue instances cached per queue name
- Reuses connections for efficiency

**Workers**:
- Separate connection pool for workers
- `decode_responses=False` (RQ uses binary pickled data)
- `socket_timeout=None` (allows blocking BRPOP)
- Health checks every 30 seconds

---

## Configuration

### Environment Variables

**Required**:
- `REDIS_URL`: Redis connection string (e.g., `redis://localhost:6379/0`)
- `ENABLE_JOB_QUEUE`: Must be `True` to use RQ

**Optional**:
- `JOB_TIMEOUT`: Job timeout in seconds (default: 3600 = 1 hour)
- `JOB_MAX_RETRIES`: Max retries on failure (default: 3)
- `JOB_RETRY_DELAY`: Delay between retries in seconds (default: 60)
- `JOB_RESULT_TTL`: How long to keep job results (default: 3600)
- `JOB_FAILURE_TTL`: How long to keep failed job info (default: 86400)

---

## Worker Startup

### Manual Start
```bash
python -m open_webui.workers.start_worker
```

### Automatic Start (in start.sh)
```bash
if [[ "${ENABLE_JOB_QUEUE,,}" == "true" ]]; then
    python -m open_webui.workers.start_worker &
    worker_pid=$!
    echo "RQ Worker started (PID: $worker_pid)"
fi
```

### Kubernetes Deployment
- Workers typically run as separate pods/deployments
- Multiple worker replicas for scalability
- Each worker connects to same Redis instance

---

## Error Handling

### Job Failure
1. Exception raised in `process_file_job()`
2. RQ catches exception
3. Updates job status to `FAILED` in Redis
4. Stores exception info: `rq:job:{job_id}:exc_info`
5. Retries if retries remaining
6. After max retries, job stays `FAILED`

### Worker Failure
- If worker crashes, job remains in `STARTED` status
- RQ has mechanism to detect stale jobs
- Can be manually requeued or cleaned up

### Redis Failure
- If Redis unavailable:
  - `is_job_queue_available()` returns `False`
  - Falls back to BackgroundTasks (non-Redis)
  - Jobs not processed until Redis restored

---

## Current Issues (From Analysis)

### 1. **API Key Not Validated in Worker**
- Worker receives `embedding_api_key` but doesn't validate it's not None
- If None, embedding function initialization may fail silently
- Should fail early with clear error

### 2. **Config Initialization May Fail**
- `AppConfig()` initialization in worker may fail
- Falls back to environment variables
- May miss critical config values

### 3. **No Rollback on Partial Failure**
- If saving to multiple collections and one fails, others succeed
- Creates inconsistent state
- Should use transactions or rollback

### 4. **Job Status Not Synced with File Status**
- Job status in Redis may differ from file status in database
- No automatic synchronization
- Can cause confusion

---

## Summary

**Redis Role**:
- Central job queue storage
- Job metadata and status tracking
- Distributed coordination

**RQ Role**:
- Job serialization/deserialization
- Worker job distribution
- Retry logic
- Status management

**Worker Role**:
- Process jobs from queue
- Initialize embedding functions with API key
- Extract content, generate embeddings, save to vector DB
- Update file status in database

**Key Flow**:
1. Main app enqueues job with API key → Redis
2. Worker picks up job from Redis
3. Worker initializes embedding function with API key
4. Worker processes file and generates embeddings
5. Worker saves to vector DB
6. Worker updates file status
7. Job status updated in Redis

**Critical Point**: API key is passed from main app (where user context exists) to worker (where processing happens) via job arguments, ensuring RBAC-protected keys are used.

