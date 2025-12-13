# Quick Start - Redis & RQ Setup

## M1 Mac Users

```bash
# Build (native ARM64 - fast!)
docker build -t test_a3 .

# Start (uses M1-optimized compose file)
docker-compose -f docker-compose.local.m1.yaml up
```

## Intel/AMD Users

```bash
# Build
docker build -t test_a3 .

# Start
docker-compose -f docker-compose.local.yaml up
```

## That's It! ✅

The setup includes:
- ✅ Redis container (port 6379)
- ✅ Open WebUI app (port 8080)
- ✅ RQ worker (auto-started in app container)
- ✅ All required environment variables configured

## What Works

### Single Replica (Docker Compose)
- ✅ **Works perfectly** - 1 app container with built-in worker
- ✅ Jobs enqueue to Redis
- ✅ Worker processes jobs automatically
- ✅ File embeddings generated correctly

### Multiple Replicas (Kubernetes/OpenShift)
- ✅ **Works perfectly** - N app pods + M worker pods
- ✅ All app pods share same Redis queue
- ✅ All worker pods pull from same queue
- ✅ RQ automatically distributes jobs
- ✅ Scale independently: `kubectl scale deployment open-webui --replicas=3`

**Note:** Docker Compose doesn't auto-scale. Use Kubernetes for production multi-replica setups.

## Verify It's Working

1. **Check logs for worker startup:**
   ```
   RQ worker started with PID: ...
   RQ Worker starting for queue 'file_processing'
   ```

2. **Upload a file** and check logs:
   ```
   Enqueued file processing job: job_id=...
   [JOB START] Processing file job: file_id=...
   [JOB SUCCESS] Successfully processed file
   ```

3. **Test Redis connection:**
   ```bash
   docker exec -it open-webui-redis redis-cli ping
   # Should return: PONG
   ```

## Troubleshooting

**Worker not starting?**
- Check `ENABLE_JOB_QUEUE=True` in environment
- Check `REDIS_URL` is correct
- Check logs: `/tmp/rq-worker.log` inside container

**Jobs not processing?**
- Verify worker is running: `docker exec -it open-webui-app ps aux | grep start_worker`
- Check Redis connection: `docker exec -it open-webui-app python -c "from redis import Redis; r = Redis('redis://redis:6379/0'); print(r.ping())"`

## Environment Variables

All required variables are set in `docker-compose.local.yaml`:
- `REDIS_URL` - Redis connection
- `ENABLE_JOB_QUEUE` - Enable job queue
- `JOB_TIMEOUT`, `JOB_MAX_RETRIES`, etc. - Job configuration
- `VECTOR_DB=chroma` - Vector database (chroma for SQLite, pgvector for PostgreSQL)
- Plus defaults for database, embeddings, etc.

**Key Configuration**:
- **Local**: `VECTOR_DB=chroma` (works with SQLite) ✅
- **Production**: `VECTOR_DB=pgvector` (requires PostgreSQL) ✅

You can override any variable by setting it in your environment or `.env` file.
