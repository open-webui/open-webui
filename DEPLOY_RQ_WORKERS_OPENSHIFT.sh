#!/bin/bash
# Quick deployment script for RQ workers on OpenShift
# Usage: ./DEPLOY_RQ_WORKERS_OPENSHIFT.sh

set -e

NAMESPACE="rit-genai-naga-dev"
DEPLOYMENT_FILE="kubernetes/manifest/base/rq-worker-deployment-openshift.yaml"
REPLICAS=8

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Deploying RQ Workers to OpenShift"
echo "=========================================="
echo "Namespace: $NAMESPACE"
echo "Deployment file: $DEPLOYMENT_FILE"
echo "Replicas: $REPLICAS"
echo "=========================================="
echo ""

# Check if namespace exists
if ! oc get namespace "$NAMESPACE" &>/dev/null; then
    echo -e "${RED}❌ Namespace '$NAMESPACE' not found!${NC}"
    echo "   Create it with: oc create namespace $NAMESPACE"
    exit 1
fi

# Check if deployment file exists
if [ ! -f "$DEPLOYMENT_FILE" ]; then
    echo -e "${RED}❌ Deployment file not found: $DEPLOYMENT_FILE${NC}"
    exit 1
fi

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check Redis
if ! oc get statefulset redis -n "$NAMESPACE" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Redis StatefulSet not found.${NC}"
    echo "   Deploy Redis first: cd kubernetes/manifest/redis && oc apply -f ."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ Redis StatefulSet found${NC}"
fi

# Check PVC
if ! oc get pvc open-webui -n "$NAMESPACE" &>/dev/null; then
    echo -e "${YELLOW}⚠️  PVC 'open-webui' not found.${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ PVC 'open-webui' found${NC}"
fi

# Check PostgreSQL
if ! oc get pods -n "$NAMESPACE" | grep -q postgres; then
    echo -e "${YELLOW}⚠️  PostgreSQL pods not found.${NC}"
    echo "   Workers need database access. Verify DATABASE_URL secret is correct."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ PostgreSQL pods found${NC}"
fi

echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Before deploying, verify:${NC}"
echo "   1. Image name in deployment file matches your Open WebUI image"
echo "   2. DATABASE_URL secret name and key are correct"
echo "   To find database secret: oc get secrets -n $NAMESPACE | grep postgres"
echo ""
read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi
echo ""

# Apply deployment
echo "📦 Applying deployment..."
oc apply -f "$DEPLOYMENT_FILE" -n "$NAMESPACE"

# Wait for deployment to be ready
echo ""
echo "⏳ Waiting for deployment to be ready..."
oc wait --for=condition=available --timeout=300s \
    deployment/open-webui-rq-worker-deployment \
    -n "$NAMESPACE" || {
    echo "⚠️  Deployment not ready after 5 minutes, checking status..."
    oc get deployment open-webui-rq-worker-deployment -n "$NAMESPACE"
    exit 1
}

# Check pod status
echo ""
echo "📊 Checking pod status..."
oc get pods -l app=open-webui-rq-worker -n "$NAMESPACE"

# Show logs from one pod
echo ""
echo "📋 Showing logs from worker pod (last 20 lines)..."
POD_NAME=$(oc get pods -l app=open-webui-rq-worker -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$POD_NAME" ]; then
    echo "Pod: $POD_NAME"
    oc logs "$POD_NAME" -n "$NAMESPACE" --tail=20
else
    echo "⚠️  No worker pods found yet"
fi

echo ""
echo "=========================================="
echo "✅ Deployment complete!"
echo "=========================================="
echo ""
echo "Useful commands:"
echo "  # View all worker pods:"
echo "  oc get pods -l app=open-webui-rq-worker -n $NAMESPACE"
echo ""
echo "  # View logs:"
echo "  oc logs -f deployment/open-webui-rq-worker-deployment -n $NAMESPACE"
echo ""
echo "  # Scale workers:"
echo "  oc scale deployment open-webui-rq-worker-deployment --replicas=10 -n $NAMESPACE"
echo ""
echo "  # Check deployment status:"
echo "  oc get deployment open-webui-rq-worker-deployment -n $NAMESPACE"
echo ""

