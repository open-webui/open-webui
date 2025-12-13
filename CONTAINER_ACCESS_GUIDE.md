# Container Access Guide

## Current Running Containers

Based on the system check, here are the containers currently running:

### 1. Main Application Container
- **Name:** `open-webui-app`
- **Image:** `test_a3`
- **Status:** Up and healthy
- **Port:** `8080` (mapped to `0.0.0.0:8080->8080/tcp`)

### 2. Redis Container
- **Name:** `open-webui-redis`
- **Image:** `redis:7-alpine`
- **Status:** Up and healthy
- **Port:** `6379` (mapped to `0.0.0.0:6379->6379/tcp`)

### 3. Worker Container
- **Status:** ❌ **Not running separately**
- **Note:** Worker may be running inside the main app container or needs to be started separately

---

## How to Access Logs

### Main Application Logs (`open-webui-app`)

```bash
# View all logs (follow mode)
docker logs -f open-webui-app

# View last 100 lines
docker logs --tail 100 open-webui-app

# View logs with timestamps
docker logs -f --timestamps open-webui-app

# View logs since specific time
docker logs --since 10m open-webui-app

# View logs and filter for embedding-related messages
docker logs -f open-webui-app | grep -i "embedding\|api key\|\[STEP"

# View logs and filter for errors
docker logs -f open-webui-app | grep -i "❌\|error\|critical"

# View logs and filter for specific file processing
docker logs -f open-webui-app | grep "file_id=<your-file-id>"
```

### Redis Logs (`open-webui-redis`)

```bash
# View all logs (follow mode)
docker logs -f open-webui-redis

# View last 50 lines
docker logs --tail 50 open-webui-redis

# View logs with timestamps
docker logs -f --timestamps open-webui-redis
```

### Worker Logs

**If worker is running inside the main container:**
```bash
# Worker logs will appear in the main app logs
docker logs -f open-webui-app | grep -i "\[JOB\|\[WORKER\|\[STEP"
```

**If you need to start a separate worker container:**
```bash
# Check if there's a worker service in docker-compose
docker-compose ps

# Start worker service (if defined)
docker-compose up -d worker

# View worker logs
docker logs -f <worker-container-name>
```

**If running worker manually:**
```bash
# Enter the main container and run worker
docker exec -it open-webui-app bash
# Then inside container:
python -m open_webui.workers.start_worker
```

---

## View All Logs Together

### Option 1: Using the view_logs.sh Script

```bash
# Make sure the script is executable
chmod +x view_logs.sh

# Set log locations (if needed)
export MAIN_APP_LOG=$(docker inspect --format='{{.LogPath}}' open-webui-app 2>/dev/null || echo "stdout")
export WORKER_LOG=$(docker inspect --format='{{.LogPath}}' <worker-container> 2>/dev/null || echo "stdout")
export REDIS_LOG=$(docker inspect --format='{{.LogPath}}' open-webui-redis 2>/dev/null || echo "stdout")

# Run the script
./view_logs.sh all
```

### Option 2: Manual Multi-Container Log Viewing

```bash
# View main app and Redis logs together
(docker logs -f open-webui-app | sed 's/^/[APP] /' &) && \
(docker logs -f open-webui-redis | sed 's/^/[REDIS] /' &) && \
wait
```

### Option 3: Using Docker Compose (if using docker-compose)

```bash
# View all services logs
docker-compose logs -f

# View specific service
docker-compose logs -f open-webui

# View multiple services
docker-compose logs -f open-webui redis
```

---

## Container Management Commands

### Check Container Status

```bash
# List all running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Check specific container
docker inspect open-webui-app

# Check container health
docker inspect open-webui-app --format='{{.State.Health.Status}}'
```

### Execute Commands Inside Containers

```bash
# Enter main app container
docker exec -it open-webui-app bash

# Enter Redis container
docker exec -it open-webui-redis sh

# Run a command without entering
docker exec open-webui-app python -m open_webui.workers.start_worker
```

### Restart Containers

```bash
# Restart main app
docker restart open-webui-app

# Restart Redis
docker restart open-webui-redis

# Restart all (if using docker-compose)
docker-compose restart
```

---

## Finding Log Files Inside Containers

### Main App Container

```bash
# Check if logs are written to files inside container
docker exec open-webui-app ls -la /tmp/ | grep -i log

# Check for log files
docker exec open-webui-app find / -name "*.log" 2>/dev/null | head -10

# Check stdout/stderr (default location)
docker logs open-webui-app
```

### Redis Container

```bash
# Redis logs are typically in stdout/stderr
docker logs open-webui-redis

# Check Redis configuration
docker exec open-webui-redis redis-cli CONFIG GET logfile
```

---

## Quick Debugging Commands

### Check for API Key Issues

```bash
docker logs -f open-webui-app | grep -i "api key\|embedding_api_key\|❌.*api"
```

### Check for Embedding Failures

```bash
docker logs -f open-webui-app | grep -i "❌\|failed.*embedding\|\[EMBEDDING"
```

### Check for Worker Job Processing

```bash
docker logs -f open-webui-app | grep -i "\[JOB\|\[STEP\|process_file_job"
```

### Check for Critical Bugs

```bash
docker logs -f open-webui-app | grep "CRITICAL BUG"
```

### Monitor Real-Time Processing

```bash
docker logs -f open-webui-app | grep -E "\[STEP|✅|❌|⚠️"
```

---

## Docker Compose File Location

Based on the container labels, the docker-compose file is:
```
docker-compose.local.yaml
```

### Check Docker Compose Services

```bash
# List all services
docker-compose -f docker-compose.local.yaml ps

# View service logs
docker-compose -f docker-compose.local.yaml logs -f

# Check if worker service exists
docker-compose -f docker-compose.local.yaml config --services | grep -i worker
```

---

## Starting a Worker Container (If Needed)

If you need to run a separate worker container:

### Option 1: Add to docker-compose.local.yaml

```yaml
services:
  worker:
    image: test_a3  # Same as main app
    command: python -m open_webui.workers.start_worker
    environment:
      - REDIS_URL=redis://open-webui-redis:6379/0
      - ENABLE_JOB_QUEUE=True
    depends_on:
      - redis
      - open-webui
    volumes:
      - ./backend:/app/backend
    restart: unless-stopped
```

Then start it:
```bash
docker-compose -f docker-compose.local.yaml up -d worker
docker logs -f <worker-container-name>
```

### Option 2: Run Worker Manually

```bash
# In a separate terminal
docker exec -it open-webui-app python -m open_webui.workers.start_worker
```

---

## Summary

### Quick Access Commands

```bash
# Main app logs
docker logs -f open-webui-app

# Redis logs  
docker logs -f open-webui-redis

# Both together
(docker logs -f open-webui-app | sed 's/^/[APP] /' &) && \
(docker logs -f open-webui-redis | sed 's/^/[REDIS] /' &) && \
wait

# Filter for embedding issues
docker logs -f open-webui-app | grep -E "\[EMBEDDING|\[STEP|❌|✅"

# Filter for API key issues
docker logs -f open-webui-app | grep -i "api key.*none\|❌.*api"
```

### Container Names Reference

- **Main App:** `open-webui-app`
- **Redis:** `open-webui-redis`
- **Worker:** Not running separately (check inside main container)

---

## Next Steps

1. **Monitor logs in real-time:**
   ```bash
   docker logs -f open-webui-app
   ```

2. **Upload a file and watch the logs** to see the embedding pipeline in action

3. **Look for the log markers:**
   - `[STEP X]` - Step-by-step progress
   - `✅` - Success
   - `❌` - Error/Critical bug
   - `[EMBEDDING]` - Embedding generation
   - `[PROCESS FILE]` - File processing

4. **If worker is needed separately**, start it using one of the methods above

