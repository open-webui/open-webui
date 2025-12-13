# Quick RQ Worker Deployment Checklist

## Before You Start

- [ ] Logged into OpenShift: `oc whoami`
- [ ] In correct project: `oc project rit-genai-naga-dev`

## Prerequisites Verification

Run these commands to verify everything is ready:

```bash
# 1. Check Redis
oc get statefulset redis -n rit-genai-naga-dev
oc get pods -l app=redis -n rit-genai-naga-dev
oc get svc redis -n rit-genai-naga-dev

# 2. Check PostgreSQL
oc get pods -n rit-genai-naga-dev | grep postgres

# 3. Check PVC
oc get pvc open-webui -n rit-genai-naga-dev

# 4. Find database secret
oc get secrets -n rit-genai-naga-dev | grep postgres
oc describe secret <secret-name> -n rit-genai-naga-dev

# 5. Get container image from main deployment
oc get deployment open-webui -n rit-genai-naga-dev -o jsonpath='{.spec.template.spec.containers[0].image}'
# OR
oc get statefulset open-webui -n rit-genai-naga-dev -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null
```

## ✅ Deployment File is Ready!

**No updates needed!** The deployment file is already configured with:
- ✅ **Image**: `registry.cloud.rt.nyu.edu/rit-genai-poc/naga-open-webui:latest`
- ✅ **DATABASE_URL**: Set directly (same as main deployment)
- ✅ **REDIS_URL**: `redis://:PASSWORD@redis.rit-genai-naga-dev.svc.cluster.local:6379/0` (Get password from `redis-auth` secret)
- ✅ **PVC**: `open-webui`
- ✅ **Namespace**: `rit-genai-naga-dev`
- ✅ **Replicas**: 8

**You can deploy immediately!**

## Deploy

```bash
# Option 1: Use deployment script (recommended)
./DEPLOY_RQ_WORKERS_OPENSHIFT.sh

# Option 2: Manual deployment
oc apply -f kubernetes/manifest/base/rq-worker-deployment-openshift.yaml -n rit-genai-naga-dev
```

## Verify

```bash
# Check deployment
oc get deployment open-webui-rq-worker-deployment -n rit-genai-naga-dev

# Check pods
oc get pods -l app=open-webui-rq-worker -n rit-genai-naga-dev

# Check logs
oc logs -f deployment/open-webui-rq-worker-deployment -n rit-genai-naga-dev
```

## Expected Results

- Deployment: `open-webui-rq-worker-deployment 8/8` (Ready)
- Pods: 8 pods with `1/1 Running` status
- Logs: Should show "Worker is ready to process jobs. Waiting for jobs..."

## Troubleshooting

**Pods not starting?**
- Check logs: `oc logs <pod-name> -n rit-genai-naga-dev`
- Check events: `oc describe pod <pod-name> -n rit-genai-naga-dev`

**Connection errors?**
- Verify REDIS_URL is correct
- Verify DATABASE_URL secret name and key
- Check Redis is running: `oc get pods -l app=redis -n rit-genai-naga-dev`

**Image pull errors?**
- Verify image name is correct
- Check image pull secrets: `oc get secrets -n rit-genai-naga-dev | grep dockercfg`

