# Local Redis and RQ Testing Guide

This guide explains how to test Open WebUI with Redis and RQ (Redis Queue) for file processing locally.

## Problem

When Redis is configured but the RQ worker isn't running, file processing jobs get enqueued but never processed, causing embeddings to fail.

## Solution

The application now automatically starts an RQ worker when `ENABLE_JOB_QUEUE=True` and Redis is available.

## Quick Start

### Option 1: Using Docker Compose (Recommended)

**For M1 Mac users:**
```bash
# Build the image (native ARM64, faster)
docker build -t test_a3 .

# Start Redis and the application
docker-compose -f docker-compose.local.m1.yaml up
```

**For Intel/AMD or cross-platform:**
```bash
# Build the image
docker build -t test_a3 .

# Start Redis and the application
docker-compose -f docker-compose.local.yaml up
```

**Or simply (auto-detects):**
```bash
docker build -t test_a3 .
docker-compose -f docker-compose.local.yaml up
```

   This will:
   - Start Redis on port 6379
   - Start Open WebUI on port 8080
   - Automatically start the RQ worker when `ENABLE_JOB_QUEUE=True`

3. **Access the application:**
   - Open WebUI: http://localhost:8080
   - Redis: localhost:6379

4. **Stop everything:**
   ```bash
   docker-compose -f docker-compose.local.yaml down
   ```

### Option 2: Using Docker Run with Local Redis

If you have Redis running locally (e.g., via `brew install redis`):

1. **Start Redis locally:**
   ```bash
   redis-server
   ```

2. **Build and run the container:**
   ```bash
   docker build -t test_a3 .
   docker run -it -p 8080:8080 \
     -e REDIS_URL=redis://host.docker.internal:6379/0 \
     -e ENABLE_JOB_QUEUE=True \
     test_a3
   ```

   Note: `host.docker.internal` allows the container to access Redis on your host machine.

### Option 3: Disable Job Queue (Fallback to BackgroundTasks)

If you don't want to use Redis/RQ:

```bash
docker build -t test_a3 .
docker run -it -p 8080:8080 \
  -e ENABLE_JOB_QUEUE=False \
  test_a3
```

This will use FastAPI BackgroundTasks (in-memory, single process).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `ENABLE_JOB_QUEUE` | `True` | Enable/disable RQ job queue |
| `JOB_TIMEOUT` | `3600` | Job timeout in seconds (1 hour) |
| `JOB_MAX_RETRIES` | `3` | Maximum retries for failed jobs |
| `JOB_RETRY_DELAY` | `60` | Retry delay in seconds |
| `VECTOR_DB` | `chroma` | Vector database: `chroma` (SQLite) or `pgvector` (PostgreSQL) |
| `DATABASE_URL` | `sqlite:///{DATA_DIR}/webui.db` | Database URL (SQLite for local, PostgreSQL for production) |

**Important**: 
- **Local (SQLite)**: Use `VECTOR_DB=chroma` (default)
- **Production (PostgreSQL)**: Use `VECTOR_DB=pgvector` with `DATABASE_URL=postgresql://...`

See [VECTOR_DB_CONFIG.md](./VECTOR_DB_CONFIG.md) for details.

## How It Works

1. **File Upload**: When a file is uploaded, the application checks if the job queue is available.

2. **Job Enqueueing**: If `ENABLE_JOB_QUEUE=True` and Redis is available:
   - Job is enqueued to Redis via RQ
   - RQ worker processes the job asynchronously
   - File is processed and embeddings are generated

3. **Fallback**: If the job queue is unavailable:
   - Falls back to FastAPI BackgroundTasks
   - Processing happens in the same process (synchronous)

4. **Worker Startup**: When `ENABLE_JOB_QUEUE=True`, `start.sh` automatically starts an RQ worker in the background.

## Troubleshooting

### Jobs Not Processing

1. **Check if worker is running:**
   ```bash
   # Inside the container
   ps aux | grep start_worker
   ```

2. **Check Redis connection:**
   ```bash
   # Test Redis from container
   redis-cli -h redis ping
   # Or if using host Redis
   redis-cli -h host.docker.internal ping
   ```

3. **Check job queue status:**
   - Look for logs: `"Enqueued file processing job"` or `"RQ Worker starting"`
   - Check for errors: `"Failed to connect to Redis"` or `"Worker cannot start"`

### Redis Connection Issues

- **Docker Compose**: Redis service name is `redis`, use `redis://redis:6379/0`
- **Local Redis**: Use `redis://host.docker.internal:6379/0` from container
- **Network**: Ensure Redis port 6379 is accessible

### Worker Not Starting

- Check `ENABLE_JOB_QUEUE` is set to `True`
- Check `REDIS_URL` is correct and Redis is accessible
- Check logs for worker startup errors

## Testing File Processing

1. **Upload a file** (PDF, DOCX, etc.) through the UI
2. **Check logs** for:
   - `"Enqueued file processing job: job_id=..."`
   - `"[JOB START] Processing file job: file_id=..."`
   - `"[JOB SUCCESS] Successfully processed file"`
3. **Verify embeddings** by querying the file in a chat

## Replicas and Scaling

See [REPLICAS_AND_SCALING.md](./REPLICAS_AND_SCALING.md) for detailed information.

**Quick Summary:**
- **Single replica**: Works perfectly ✅ (1 app + 1 worker in same container)
- **Multiple replicas**: Works perfectly ✅ (N app pods + M worker pods, all share Redis queue)
- **Auto-scaling**: Configure HPA in Kubernetes/OpenShift
- **Docker Compose**: Single replica only (for local testing)

**Key Points:**
- All app replicas enqueue to the same Redis queue
- All worker replicas pull from the same Redis queue
- RQ automatically distributes jobs across workers
- Scale app and worker deployments independently

## Production Deployment

In production (e.g., OpenShift/Kubernetes):
- Use separate worker pods (see `kubernetes/manifest/base/rq-worker-deployment.yaml`)
- Configure Redis as a separate service
- Set `ENABLE_JOB_QUEUE=True` and `REDIS_URL` appropriately
- Scale app and worker deployments independently based on load
