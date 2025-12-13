# Replicas and Scaling Guide

## Overview

This document explains how Open WebUI handles multiple replicas with Redis and RQ job queue.

## Architecture

```
┌─────────────────┐     ┌──────────┐     ┌─────────────────┐
│  App Replica 1  │────▶│          │◀────│ Worker Replica 1│
│  (enqueues)     │     │  Redis   │     │  (processes)    │
└─────────────────┘     │  Queue   │     └─────────────────┘
                        │          │
┌─────────────────┐     │          │     ┌─────────────────┐
│  App Replica 2  │────▶│          │◀────│ Worker Replica 2│
│  (enqueues)     │     │          │     │  (processes)    │
└─────────────────┘     └──────────┘     └─────────────────┘
```

## How It Works

### Single Replica (Local/Docker Compose)

**Setup:**
- 1 app container
- 1 Redis container
- 1 RQ worker (started automatically in app container)

**Flow:**
1. User uploads file → App enqueues job to Redis
2. RQ worker (same container) picks up job from Redis
3. Worker processes file and generates embeddings
4. Job completes

**Works perfectly** ✅

### Multiple Replicas (Kubernetes/OpenShift)

**Setup:**
- N app pods (e.g., 3 replicas)
- 1 Redis service (shared)
- M worker pods (e.g., 2 replicas)

**Flow:**
1. User uploads file → Any app pod enqueues job to Redis
2. Any available worker pod picks up job from Redis
3. RQ automatically distributes jobs across all workers
4. Worker processes file and generates embeddings
5. Job completes

**Works perfectly** ✅

## Scaling Behavior

### App Replicas (Web Server)

**Purpose:** Handle HTTP requests, enqueue jobs

**Scaling:**
```bash
# Kubernetes
kubectl scale deployment open-webui --replicas=3

# Docker Compose (not recommended - use K8s for production)
# Would need manual service duplication
```

**Behavior:**
- Each replica can handle requests independently
- All replicas share the same Redis queue
- Load balancer distributes requests across replicas
- Jobs are enqueued to the same Redis queue regardless of which replica receives the request

### Worker Replicas (Job Processors)

**Purpose:** Process file jobs from Redis queue

**Scaling:**
```bash
# Kubernetes
kubectl scale deployment open-webui-rq-worker --replicas=2
```

**Behavior:**
- All workers pull from the same Redis queue
- RQ automatically distributes jobs (round-robin)
- More workers = faster processing (parallel)
- Workers are stateless - any worker can process any job

## Auto-Scaling

### Horizontal Pod Autoscaler (HPA)

**For App Pods:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: open-webui-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: open-webui
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**For Worker Pods:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: open-webui-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: open-webui-rq-worker
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

**Custom Metrics (Queue Length):**
You can also scale workers based on Redis queue length:
```yaml
metrics:
- type: External
  external:
    metric:
      name: redis_queue_length
    target:
      type: AverageValue
      averageValue: "10"  # Scale when queue has 10+ jobs
```

## Docker Compose Limitations

**Important:** Docker Compose is for **local testing only**.

**Limitations:**
- No built-in auto-scaling
- Manual replica configuration (duplicate services)
- Not recommended for production

**For Production:**
- Use Kubernetes/OpenShift
- Separate app and worker deployments
- Configure HPA for auto-scaling
- Use Redis as a separate service

## Testing Locally

### Single Replica (Default)
```bash
docker build -t test_a3 .
docker-compose -f docker-compose.local.yaml up
```
- 1 app container with built-in worker
- 1 Redis container
- Works perfectly ✅

### Multiple Replicas (Docker Compose - Not Recommended)
You'd need to manually duplicate services:
```yaml
services:
  open-webui-1:
    # ... same config
  open-webui-2:
    # ... same config
```
**Better:** Use Kubernetes for multi-replica testing.

## Best Practices

1. **App Replicas:** Scale based on HTTP request load
2. **Worker Replicas:** Scale based on file processing queue length
3. **Redis:** Single instance is usually enough (or Redis Cluster for high availability)
4. **Monitoring:** Track queue length, job processing time, worker utilization
5. **Resource Limits:** Set appropriate CPU/memory limits for both app and worker pods

## Troubleshooting

### Jobs Not Processing
- Check if workers are running: `kubectl get pods -l app=open-webui-rq-worker`
- Check Redis connection: `kubectl exec -it <pod> -- redis-cli -h redis ping`
- Check queue length: `kubectl exec -it <pod> -- python -c "from rq import Queue; from redis import Redis; q = Queue('file_processing', connection=Redis('redis://redis:6379/0')); print(len(q))"`

### Uneven Job Distribution
- RQ automatically distributes jobs - this is normal
- If one worker is slow, jobs will queue up
- Monitor worker CPU/memory usage

### High Queue Length
- Scale up workers: `kubectl scale deployment open-webui-rq-worker --replicas=5`
- Check if workers are stuck: `kubectl logs -l app=open-webui-rq-worker --tail=100`
