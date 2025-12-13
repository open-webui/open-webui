# Scalability Analysis: 100 Concurrent Users on OpenShift

## ❌ **CRITICAL ISSUES - WILL CAUSE FAILURES**

### 1. **Database Connection Pool Exhaustion (CRITICAL)**
**Current Configuration:**
```python
DATABASE_POOL_SIZE = 0  # Default: NO POOLING!
DATABASE_POOL_MAX_OVERFLOW = 0
```

**Problem:**
- With `pool_size=0`, SQLAlchemy uses `NullPool`, creating a **new database connection for EVERY request**
- Each file upload/job creates multiple DB connections (AppConfig, file metadata, user lookup, etc.)
- **100 concurrent users × 3-5 DB operations each = 300-500 simultaneous connections**
- PostgreSQL default `max_connections` is typically **100-200**, will be **EXCEEDED IMMEDIATELY**

**Impact:**
- ❌ Database connection limit exceeded errors
- ❌ Requests will fail with "too many connections"
- ❌ System will become unresponsive
- ❌ Jobs will fail to enqueue or process

**Fix Required:**
```bash
# Set in environment or ConfigMap
DATABASE_POOL_SIZE=20          # Base pool size
DATABASE_POOL_MAX_OVERFLOW=10  # Allow temporary overflow
```

**With 100 users, you need:**
- **Estimated required pool size**: 30-50 connections
- **Formula**: (Concurrent Users × Avg DB Operations per Request) / Worker Threads + Buffer
- **Recommendation**: Start with `DATABASE_POOL_SIZE=30, DATABASE_POOL_MAX_OVERFLOW=20`

---

### 2. **Insufficient RQ Worker Capacity (CRITICAL)**
**Current Configuration:**
```yaml
# kubernetes/manifest/base/rq-worker-deployment.yaml
replicas: 1  # Only 1 worker!
```

**Problem:**
- Each RQ worker processes **1 job at a time** (single-threaded)
- File processing jobs take **30 seconds to 10 minutes** each (embeddings, large files)
- **100 concurrent file uploads = 100 jobs in queue**
- With 1 worker: **100 × 5 minutes average = 500 minutes (8+ hours) queue time**

**Impact:**
- ❌ Users wait hours for file processing
- ❌ Jobs queue up and timeout (1 hour timeout)
- ❌ Redis queue fills up
- ❌ Poor user experience, possible job failures

**Fix Required:**
```yaml
# Scale workers based on load
replicas: 10  # For 100 concurrent users, need 10-20 workers
```

**Calculation:**
- **Target processing time**: < 5 minutes per job
- **Average job duration**: 2-5 minutes
- **Concurrent users**: 100
- **Required workers**: 100 / (5 min / 2 min per worker) = **40 workers**
- **Realistic minimum**: **10-20 workers** (assuming not all 100 upload simultaneously)

---

### 3. **Worker Redis Connection Pool Too Small**
**Current Configuration:**
```python
# start_worker.py:117
max_connections=10  # Per worker
```

**Problem:**
- Each worker has 10 Redis connections
- With 10 workers: **10 × 10 = 100 connections just for workers**
- Main app pool: **100 connections**
- **Total: 200 Redis connections** (may be fine, but tight)

**Impact:**
- ⚠️ Potential Redis connection limit if scaled further
- ⚠️ Worker connections are mostly idle (workers use 1 connection each)

**Fix:**
- Current setting is acceptable but monitor
- Consider reducing to `max_connections=5` per worker (workers need 1-2 connections)

---

### 4. **Main App Redis Pool May Be Insufficient**
**Current Configuration:**
```python
REDIS_MAX_CONNECTIONS = 100  # Default
```

**Problem:**
- 100 concurrent users on **1 webui replica**
- Each user upload triggers: lock acquisition, job enqueue, cache lookups
- **100 users × 2-3 Redis operations = 200-300 concurrent Redis operations**
- Pool of 100 may cause **connection waits** under peak load

**Impact:**
- ⚠️ Slower response times during peak load
- ⚠️ Possible connection timeout errors

**Fix Required:**
```bash
REDIS_MAX_CONNECTIONS=200  # Increase for 100 concurrent users
```

**OR scale webui replicas:**
```yaml
replicas: 3  # Distribute load across pods
# Each pod: 100 connections / 3 = ~33 connections per pod
```

---

### 5. **No Database Connection Cleanup in Workers (CRITICAL)**
**Current Issue:**
- Worker creates `AppConfig()` per job → creates DB connections
- No explicit cleanup → connections leak
- With 100 jobs, **100+ leaked connections**

**Impact:**
- ❌ Connection pool exhaustion even with proper pool size
- ❌ Memory leaks
- ❌ System degradation over time

**Fix:** See ISSUES_AND_RECOMMENDATIONS.md

---

## ⚠️ **HIGH PRIORITY ISSUES**

### 6. **AppConfig Initialization Per Job**
**Problem:**
- Each job creates `AppConfig()` which queries database
- 100 jobs = 100 database queries just for config
- Slows down job processing

**Impact:**
- Slower job processing
- Extra database load
- Poor performance

---

### 7. **Embedding Model Reinitialization**
**Problem:**
- Heavy models (SentenceTransformer) loaded per job
- 100 jobs = 100 model loads = **HUGE memory usage**

**Impact:**
- Memory exhaustion
- Slow job startup
- Possible OOM kills

---

### 8. **Single WebUI Replica**
**Current Configuration:**
```yaml
replicas: 1  # All 100 users hit same pod
```

**Problem:**
- All 100 users served by 1 pod
- Single point of failure
- No load distribution

**Recommendation:**
```yaml
replicas: 3  # Distribute load
```

---

## 📊 **RESOURCE REQUIREMENTS SUMMARY**

### Current Setup (WILL FAIL):
```
WebUI Pods: 1
Workers: 1
DB Pool Size: 0 (NO POOLING)
Redis Connections: 100 (main) + 10 (worker)
```

### Required Setup for 100 Concurrent Users:
```
WebUI Pods: 3-5 replicas
Workers: 10-20 replicas
DB Pool Size: 30-50 connections
DB Max Overflow: 20 connections
Redis Connections: 200 (main) + 50 (workers)
```

---

## 🎯 **IMMEDIATE ACTION ITEMS**

### Priority 1 (Fix Before Deployment):
1. ✅ Set `DATABASE_POOL_SIZE=30`
2. ✅ Set `DATABASE_POOL_MAX_OVERFLOW=20`
3. ✅ Scale RQ workers to `replicas: 10`
4. ✅ Add database connection cleanup in workers
5. ✅ Cache AppConfig at worker startup

### Priority 2 (Performance):
6. ✅ Increase `REDIS_MAX_CONNECTIONS=200`
7. ✅ Scale WebUI to `replicas: 3`
8. ✅ Cache embedding models at worker startup

### Priority 3 (Monitoring):
9. ✅ Add connection pool metrics
10. ✅ Monitor Redis connection usage
11. ✅ Monitor database connection pool usage
12. ✅ Add job queue length alerts

---

## 📈 **EXPECTED BEHAVIOR WITH FIXES**

### With Proper Configuration:
- ✅ 100 concurrent file uploads: **Queue in Redis, processed within 5-10 minutes**
- ✅ Database connections: **Pooled, reused, no exhaustion**
- ✅ Redis connections: **Within limits, properly managed**
- ✅ Worker capacity: **10-20 jobs processed simultaneously**
- ✅ User experience: **Files process in reasonable time**

### Without Fixes:
- ❌ 100 concurrent uploads: **Database connection errors, jobs fail**
- ❌ Queue time: **Hours or days**
- ❌ System: **Unresponsive, crashes**
- ❌ User experience: **Terrible, errors everywhere**

---

## 🔧 **RECOMMENDED CONFIGURATION VALUES**

### Environment Variables (ConfigMap/Secrets):
```yaml
# Database Pooling (CRITICAL)
DATABASE_POOL_SIZE: "30"
DATABASE_POOL_MAX_OVERFLOW: "20"
DATABASE_POOL_TIMEOUT: "30"
DATABASE_POOL_RECYCLE: "3600"

# Redis Configuration
REDIS_MAX_CONNECTIONS: "200"

# Job Queue Configuration
JOB_TIMEOUT: "3600"  # 1 hour
JOB_MAX_RETRIES: "3"
JOB_RETRY_DELAY: "60"
```

### Kubernetes Deployment Scaling:
```yaml
# webui-deployment.yaml
replicas: 3

# rq-worker-deployment.yaml
replicas: 10  # Start with 10, scale to 20 if needed
```

---

## 🧪 **LOAD TESTING RECOMMENDATIONS**

1. **Test with 10 users first** - Verify fixes work
2. **Gradually increase to 50 users** - Monitor connection pools
3. **Scale to 100 users** - Verify all systems stable
4. **Monitor:**
   - Database connection pool usage
   - Redis connection count
   - Job queue length
   - Worker processing rate
   - Error rates

---

## 🚨 **RED FLAGS TO WATCH FOR**

- Database connection errors: "too many connections"
- Redis connection timeouts
- Job queue length > 50 jobs
- Worker CPU/Memory > 80%
- Job processing time > 10 minutes
- Error rate > 5%

