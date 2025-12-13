# Deploying RQ Workers on OpenShift

This guide explains how to deploy RQ workers on OpenShift for processing file jobs.

## Prerequisites

### 1. Redis Deployment (Required)

**Verify Redis is deployed and running:**

```bash
# Check Redis StatefulSet
oc get statefulset redis -n rit-genai-naga-dev

# Check Redis pods
oc get pods -l app=redis -n rit-genai-naga-dev

# Check Redis service
oc get svc redis -n rit-genai-naga-dev
```

**Expected output:**
- StatefulSet: `redis 1/1` (Ready)
- Pod: `redis-0 1/1 Running`
- Service: `redis ClusterIP None 6379/TCP`

**Redis Configuration:**
- **Service Name**: `redis`
- **Service Address**: `redis.rit-genai-naga-dev.svc.cluster.local:6379`
- **Secret Name**: `redis-auth`
- **Password Key**: `redis-password`
- **Password Value**: Get from secret: `oc get secret redis-auth -n rit-genai-naga-dev -o jsonpath='{.data.redis-password}' | base64 -d`
- **REDIS_URL Format**: `redis://:PASSWORD@redis.rit-genai-naga-dev.svc.cluster.local:6379/0` (Replace PASSWORD with actual password from secret)

**If Redis is not deployed, deploy it first:**
```bash
cd kubernetes/manifest/redis
oc apply -f redis-secret.yaml -n rit-genai-naga-dev
oc apply -f redis-configmap.yaml -n rit-genai-naga-dev
oc apply -f redis-service.yaml -n rit-genai-naga-dev
oc apply -f redis-statefulset.yaml -n rit-genai-naga-dev
```

### 2. Database Access (Required)

**Verify PostgreSQL is accessible:**

```bash
# Check PostgreSQL pods
oc get pods -n rit-genai-naga-dev | grep postgres

# Check PostgreSQL service
oc get svc -n rit-genai-naga-dev | grep postgres
```

**Database Secret:**
- The DATABASE_URL should be available in a secret (typically managed by Postgres operator)
- Common secret names: `rit-genai-naga-dev-pguser-rit-genai-naga-dev-admin` or similar
- Key: Usually `password` or `uri` or `postgresql`

**To find your database secret:**
```bash
# List secrets containing database credentials
oc get secrets -n rit-genai-naga-dev | grep -i postgres

# Check secret keys
oc describe secret rit-genai-naga-dev-pguser-rit-genai-naga-dev-admin -n rit-genai-naga-dev
```

**If DATABASE_URL is not in a secret, you may need to:**
1. Create a secret with DATABASE_URL, or
2. Set it directly in the deployment (not recommended for production)

### 3. PVC Access (Required)

**Verify PVC exists:**

```bash
oc get pvc open-webui -n rit-genai-naga-dev
```

**Expected output:**
- PVC: `open-webui Bound 10Gi vastdata-cloud`

**If PVC doesn't exist, create it:**
```bash
oc apply -f redis-deployment-info/open-webui-pvc.yaml -n rit-genai-naga-dev
```

### 4. Container Image (Required)

**Verify you have access to the container image:**

The workers use the same image as the main Open WebUI deployment. Check what image your main deployment uses:

```bash
oc get deployment open-webui -n rit-genai-naga-dev -o jsonpath='{.spec.template.spec.containers[0].image}'
```

**Update the worker deployment with the same image.**

### 5. Environment Variables Checklist

Before deploying, ensure you know:

- ✅ **REDIS_URL**: `redis://:PASSWORD@redis.rit-genai-naga-dev.svc.cluster.local:6379/0` (Get password from `redis-auth` secret)
- ✅ **ENABLE_JOB_QUEUE**: Must be `"True"`
- ⚠️ **DATABASE_URL**: Verify the secret name and key (see above)
- ✅ **VECTOR_DB**: `"pgvector"` (or your vector DB type)
- ✅ **PVC Name**: `open-webui`
- ✅ **Namespace**: `rit-genai-naga-dev`

## Pre-Deployment Checklist

Before deploying, verify the following:

- [ ] **Redis is running**: `oc get pods -l app=redis -n rit-genai-naga-dev`
- [ ] **Redis service exists**: `oc get svc redis -n rit-genai-naga-dev`
- [ ] **PostgreSQL is accessible**: `oc get pods -n rit-genai-naga-dev | grep postgres`
- [ ] **PVC exists**: `oc get pvc open-webui -n rit-genai-naga-dev`
- [ ] **Database secret found**: Use command below to find DATABASE_URL secret
- [ ] **Container image identified**: Check your main deployment's image
- [ ] **Namespace confirmed**: `rit-genai-naga-dev`

### Find Your Database Secret

```bash
# List PostgreSQL-related secrets
oc get secrets -n rit-genai-naga-dev | grep -i postgres

# Check what keys are in the secret (likely candidates):
oc describe secret rit-genai-naga-dev-pguser-rit-genai-naga-dev-admin -n rit-genai-naga-dev

# Common secret keys:
# - uri (full connection string)
# - password (just the password)
# - postgresql (connection string)
# - user (username)
# - host (hostname)
```

**If you find a secret with a `uri` key, use that. Otherwise, you may need to construct the DATABASE_URL manually.**

**Example: If your secret has a `uri` key:**
```yaml
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: rit-genai-naga-dev-pguser-rit-genai-naga-dev-admin
      key: uri  # Full connection string
```

**If your secret only has individual components (host, user, password, database):**
You'll need to construct the DATABASE_URL manually or create a new secret with the full URI.

### Find Your Container Image

```bash
# Get the image from your main Open WebUI deployment
oc get deployment open-webui -n rit-genai-naga-dev -o jsonpath='{.spec.template.spec.containers[0].image}'

# Or check the StatefulSet if using that
oc get statefulset open-webui -n rit-genai-naga-dev -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null

# Update the image in rq-worker-deployment-openshift.yaml with the result
```

## Step 1: Deployment File is Ready!

The deployment manifest is located at:
```
kubernetes/manifest/base/rq-worker-deployment-openshift.yaml
```

### ✅ Already Configured:

1. **Namespace**: `rit-genai-naga-dev` ✅
2. **Image**: `registry.cloud.rt.nyu.edu/rit-genai-poc/naga-open-webui:latest` ✅
3. **DATABASE_URL**: Set directly (same as main deployment) ✅
4. **REDIS_URL**: Configured with correct password ✅
5. **PVC**: `open-webui` ✅
6. **Replicas**: 8 (good for 100 concurrent users) ✅

**The deployment file is ready to use!** No updates needed unless you want to change replicas or other settings.

## Step 2: Verify Configuration (Optional)

The deployment file is already configured with:
- ✅ Correct image: `registry.cloud.rt.nyu.edu/rit-genai-poc/naga-open-webui:latest`
- ✅ Correct DATABASE_URL: Set directly (same as main deployment)
- ✅ Correct REDIS_URL: Configured with password
- ✅ Correct PVC: `open-webui`
- ✅ Correct namespace: `rit-genai-naga-dev`

**You can deploy immediately!** No changes needed unless you want to:
- Adjust replica count (currently 8)
- Change resource limits
- Modify environment variables

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: open-webui-rq-worker-deployment
  namespace: rit-genai-naga-dev  # ← Update to your namespace
spec:
  replicas: 8  # ← Start with 8 workers for 100 concurrent users
  selector:
    matchLabels:
      app: open-webui-rq-worker
  template:
    metadata:
      labels:
        app: open-webui-rq-worker
    spec:
      containers:
      - name: rq-worker
        image: your-registry/your-image:tag  # ← Update to your image
        command: ["python", "-m", "open_webui.workers.start_worker"]
```

## Step 3: Configure Environment Variables

### Required Environment Variables:

**⚠️ IMPORTANT**: Your Redis ConfigMap (`redis-config`) only contains `redis.conf`, NOT `REDIS_URL`. 
You must set `REDIS_URL` directly as a value (not from ConfigMap/Secret).

```yaml
env:
  # Redis (REQUIRED) - Get password from secret
  # REDIS_PASSWORD=$(oc get secret redis-auth -n rit-genai-naga-dev -o jsonpath='{.data.redis-password}' | base64 -d)
  - name: REDIS_URL
    value: "redis://:PASSWORD@redis.rit-genai-naga-dev.svc.cluster.local:6379/0"  # Replace PASSWORD with actual password
  
  # WebSocket Redis (Optional but Recommended)
  - name: WEBSOCKET_REDIS_URL
    value: "redis://:PASSWORD@redis.rit-genai-naga-dev.svc.cluster.local:6379/0"  # Replace PASSWORD with actual password
  
  - name: WEBSOCKET_MANAGER
    value: "redis"

  # Job Queue (REQUIRED)
  - name: ENABLE_JOB_QUEUE
    value: "True"
  - name: JOB_TIMEOUT
    value: "3600"  # 1 hour
  - name: JOB_MAX_RETRIES
    value: "3"
  - name: JOB_RETRY_DELAY
    value: "60"
  
  # Database (REQUIRED)
  # Option 1: From Secret (recommended - verify your actual secret name and key)
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: rit-genai-naga-dev-pguser-rit-genai-naga-dev-admin  # Update to your actual secret name
        key: uri  # Or 'password' or 'postgresql' - check with: oc describe secret <secret-name>
  
  # Option 2: Direct value (if secret structure is different)
  # - name: DATABASE_URL
  #   value: "postgresql://user:password@host:5432/dbname"
  
  # Database Pool Configuration (for 100 max_connections)
  - name: DATABASE_POOL_SIZE
    value: "5"  # 5 base connections per worker
  - name: DATABASE_POOL_MAX_OVERFLOW
    value: "2"  # 2 overflow connections per worker
  - name: DATABASE_POOL_TIMEOUT
    value: "30"
  - name: DATABASE_POOL_RECYCLE
    value: "3600"
  
  # Redis Connection Pool
  - name: REDIS_MAX_CONNECTIONS
    value: "50"  # Shared across all pods
  
  # Vector DB (REQUIRED)
  - name: VECTOR_DB
    value: "pgvector"  # or "chroma"
  
  # Embedding Configuration
  - name: RAG_EMBEDDING_ENGINE
    value: "portkey"  # or "openai"
  - name: RAG_EMBEDDING_MODEL
    value: "@openai-embedding/text-embedding-3-small"
  
  # Logging
  - name: WORKER_LOG_LEVEL
    value: "INFO"
  - name: GLOBAL_LOG_LEVEL
    value: "INFO"
```

## Step 4: Deploy to OpenShift

### Option A: Using oc apply (Recommended)

```bash
# 1. Update the deployment file first (see Step 2 above)
# Edit kubernetes/manifest/base/rq-worker-deployment-openshift.yaml
# - Update image name
# - Update DATABASE_URL secret name and key

# 2. Apply the deployment
oc apply -f kubernetes/manifest/base/rq-worker-deployment-openshift.yaml -n rit-genai-naga-dev

# 3. Verify deployment
oc get deployment open-webui-rq-worker-deployment -n rit-genai-naga-dev

# 4. Check pods
oc get pods -n rit-genai-naga-dev | grep rq-worker

# 5. Check logs
oc logs -f deployment/open-webui-rq-worker-deployment -n rit-genai-naga-dev
```

### Option B: Using the deployment script

```bash
# Use the provided script (updates the file path automatically)
./DEPLOY_RQ_WORKERS_OPENSHIFT.sh
```

### Option C: Using oc create

```bash
# Create from file
oc create -f kubernetes/manifest/base/rq-worker-deployment-openshift.yaml -n rit-genai-naga-dev
```

## Step 5: Verify Deployment

### Check Deployment Status

```bash
# Check deployment
oc get deployment open-webui-rq-worker-deployment -n rit-genai-naga-dev

# Check pods
oc get pods -l app=open-webui-rq-worker -n rit-genai-naga-dev

# Describe deployment
oc describe deployment open-webui-rq-worker-deployment -n rit-genai-naga-dev
```

### Check Pod Logs

```bash
# Get all worker pods
oc get pods -l app=open-webui-rq-worker -n rit-genai-naga-dev

# View logs for a specific pod
oc logs <pod-name> -n rit-genai-naga-dev

# Follow logs for deployment
oc logs -f deployment/open-webui-rq-worker-deployment -n rit-genai-naga-dev

# View logs for all worker pods
oc logs -l app=open-webui-rq-worker -n rit-genai-naga-dev --tail=100
```

### Expected Log Output

You should see logs like:
```
================================================================================
RQ Worker Startup - Initializing file processing worker
================================================================================
Job queue is enabled (ENABLE_JOB_QUEUE=True)
Initializing database connection...
Database connection initialized successfully
REDIS_URL configured: redis://...
Connecting to Redis...
Redis connection established successfully
Queue 'file_processing' accessible (current length: 0)
Worker name: file_processor_hostname_pid
================================================================================
✅ RQ Worker 'file_processor_hostname_pid' starting for queue 'file_processing'
   Redis: redis://...
   Hostname: ...
   PID: ...
================================================================================
Worker is ready to process jobs. Waiting for jobs...
```

## Step 6: Scale Workers

### Scale Up/Down

```bash
# Scale to 8 workers
oc scale deployment open-webui-rq-worker-deployment --replicas=8 -n rit-genai-naga-dev

# Scale to 5 workers
oc scale deployment open-webui-rq-worker-deployment --replicas=5 -n rit-genai-naga-dev

# Check current replica count
oc get deployment open-webui-rq-worker-deployment -n rit-genai-naga-dev
```

### Recommended Scaling:

- **Light load (< 10 concurrent users)**: 2-3 workers
- **Medium load (10-50 concurrent users)**: 5-8 workers
- **Heavy load (50-100 concurrent users)**: 8-12 workers
- **Very heavy load (100+ concurrent users)**: 12-15 workers

**Note**: With 100 max_connections in PostgreSQL:
- **Main deployment**: 3 web pods × (25+10=35) = 105 connections (theoretical max)
- **Workers**: 8 workers × (5+2=7) = 56 connections (theoretical max)
- **Total theoretical**: ~161 connections potential
- **In practice**: Connection reuse and proper cleanup (Session.remove()) means actual usage is lower
- **Recommendation**: Monitor connection usage and adjust pool sizes if needed

## Step 7: Monitor Workers

### Check Worker Health

```bash
# Check if workers are running
oc get pods -l app=open-webui-rq-worker -n rit-genai-naga-dev

# Check worker logs for errors
oc logs -l app=open-webui-rq-worker -n rit-genai-naga-dev | grep -i error

# Check worker logs for job processing
oc logs -l app=open-webui-rq-worker -n rit-genai-naga-dev | grep -i "job"
```

### Monitor Resource Usage

```bash
# Check resource usage
oc top pods -l app=open-webui-rq-worker -n rit-genai-naga-dev

# Describe pod to see resource limits
oc describe pod <pod-name> -n rit-genai-naga-dev
```

## Step 8: Troubleshooting

### Worker Not Starting

1. **Check logs for errors:**
   ```bash
   oc logs <pod-name> -n rit-genai-naga-dev
   ```

2. **Common issues:**
   - `ENABLE_JOB_QUEUE` not set to `"True"`
   - `REDIS_URL` incorrect or Redis not accessible
   - `DATABASE_URL` incorrect or database not accessible
   - Image pull errors

3. **Check environment variables:**
   ```bash
   oc describe pod <pod-name> -n rit-genai-naga-dev | grep -A 50 "Environment:"
   ```

### Worker Not Processing Jobs

1. **Check Redis connection:**
   ```bash
   oc logs <pod-name> -n rit-genai-naga-dev | grep -i redis
   ```

2. **Check queue status:**
   ```bash
   # Connect to Redis pod and check queue
   oc exec -it redis-0 -n rit-genai-naga-dev -- redis-cli
   > LLEN rq:queue:file_processing
   ```

3. **Check worker is listening:**
   ```bash
   oc logs <pod-name> -n rit-genai-naga-dev | grep -i "ready to process"
   ```

### Worker Crashes

1. **Check pod events:**
   ```bash
   oc describe pod <pod-name> -n rit-genai-naga-dev
   ```

2. **Check resource limits:**
   ```bash
   oc top pod <pod-name> -n rit-genai-naga-dev
   ```

3. **Check logs for OOM errors:**
   ```bash
   oc logs <pod-name> -n rit-genai-naga-dev | grep -i "out of memory"
   ```

## Step 9: Update Configuration

### Update Environment Variables

```bash
# Edit deployment
oc edit deployment open-webui-rq-worker-deployment -n rit-genai-naga-dev

# Or patch specific environment variable
oc set env deployment/open-webui-rq-worker-deployment \
  WORKER_LOG_LEVEL=DEBUG \
  -n rit-genai-naga-dev
```

### Update Image

```bash
# Set new image
oc set image deployment/open-webui-rq-worker-deployment \
  rq-worker=your-registry/your-image:new-tag \
  -n rit-genai-naga-dev

# Or trigger rollout
oc rollout latest deployment/open-webui-rq-worker-deployment -n rit-genai-naga-dev
```

## Step 10: Clean Up (if needed)

```bash
# Delete deployment
oc delete deployment open-webui-rq-worker-deployment -n rit-genai-naga-dev

# Delete all worker pods
oc delete pods -l app=open-webui-rq-worker -n rit-genai-naga-dev
```

## Quick Reference Commands

```bash
# Deploy (use the OpenShift-specific file)
oc apply -f kubernetes/manifest/base/rq-worker-deployment-openshift.yaml -n rit-genai-naga-dev

# Check status
oc get deployment open-webui-rq-worker-deployment -n rit-genai-naga-dev
oc get pods -l app=open-webui-rq-worker -n rit-genai-naga-dev

# View logs
oc logs -f deployment/open-webui-rq-worker-deployment -n rit-genai-naga-dev

# Scale
oc scale deployment open-webui-rq-worker-deployment --replicas=8 -n rit-genai-naga-dev

# Update
oc set env deployment/open-webui-rq-worker-deployment ENABLE_JOB_QUEUE="True" -n rit-genai-naga-dev
oc rollout restart deployment/open-webui-rq-worker-deployment -n rit-genai-naga-dev
```

## Next Steps

After deploying workers:

1. **Verify workers are processing jobs** - Upload a file and check logs
2. **Monitor resource usage** - Ensure workers have enough CPU/memory
3. **Scale as needed** - Adjust replica count based on load
4. **Set up monitoring** - Add alerts for worker failures
5. **Review logs regularly** - Check for errors or warnings

## Notes

- Workers share the same Redis queue, so jobs are distributed automatically
- Each worker processes jobs sequentially (one at a time)
- More workers = faster job processing (up to a point)
- Workers need access to the same database and vector DB as the main app
- Workers use the same PVC for file storage access

