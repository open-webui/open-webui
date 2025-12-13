# RQ Worker Deployment Issue

## Problem

The RQ worker pods are crashing with:
```
ModuleNotFoundError: No module named 'open_webui.workers'
```

## Root Cause

The Docker image `registry.cloud.rt.nyu.edu/rit-genai-poc/naga-open-webui:latest` was built **before** the `backend/open_webui/workers/` directory was added to the codebase.

The workers module exists in your local codebase but is **not in the container image**.

## Solution

You need to **rebuild the Docker image** with the latest code that includes the workers module.

### Steps to Fix

1. **Rebuild the Docker image** with the workers code:
   ```bash
   # Build the image (adjust command based on your build process)
   docker build -t registry.cloud.rt.nyu.edu/rit-genai-poc/naga-open-webui:latest .
   
   # Push to registry
   docker push registry.cloud.rt.nyu.edu/rit-genai-poc/naga-open-webui:latest
   ```

2. **After rebuilding**, the worker pods should automatically pick up the new image and start successfully.

3. **Verify the workers directory exists in the new image** (optional):
   ```bash
   docker run --rm registry.cloud.rt.nyu.edu/rit-genai-poc/naga-open-webui:latest ls -la /app/backend/open_webui/workers
   ```

### Alternative: Verify Workers in Current Image

To confirm the workers directory is missing:

```bash
# Check what's in the current image
oc exec -it open-webui-0 -n rit-genai-naga-dev -- ls -la /app/backend/open_webui/ | grep workers
# Should return nothing (directory doesn't exist)
```

## After Rebuilding

Once you've rebuilt and pushed the new image:

1. The worker pods should automatically restart with the new image
2. Check pod status:
   ```bash
   oc get pods -l app=open-webui-rq-worker -n rit-genai-naga-dev
   ```
3. Check logs:
   ```bash
   oc logs -f deployment/open-webui-rq-worker-deployment -n rit-genai-naga-dev
   ```
4. Expected output: You should see "Worker is ready to process jobs. Waiting for jobs..." instead of module errors.

