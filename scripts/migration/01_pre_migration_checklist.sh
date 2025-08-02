#!/bin/bash
# Pre-migration checklist for InfluxDB deployment

echo "🔍 mAI InfluxDB Pre-Migration Checklist"
echo "======================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
ALL_GOOD=true

# Function to check status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ALL_GOOD=false
    fi
}

# 1. Check Docker version
echo "1. Checking Docker environment..."
docker --version > /dev/null 2>&1
check_status $? "Docker is installed"

docker-compose --version > /dev/null 2>&1
check_status $? "Docker Compose is installed"

# 2. Check required environment variables
echo ""
echo "2. Checking environment variables..."
[ ! -z "$INFLUXDB_URL" ]
check_status $? "INFLUXDB_URL is set"

[ ! -z "$INFLUXDB_TOKEN" ]
check_status $? "INFLUXDB_TOKEN is set"

[ ! -z "$INFLUXDB_ORG" ]
check_status $? "INFLUXDB_ORG is set"

[ ! -z "$INFLUXDB_BUCKET" ]
check_status $? "INFLUXDB_BUCKET is set"

# 3. Check InfluxDB connectivity
echo ""
echo "3. Testing InfluxDB connectivity..."
if [ ! -z "$INFLUXDB_URL" ] && [ ! -z "$INFLUXDB_TOKEN" ]; then
    curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Token $INFLUXDB_TOKEN" \
        "$INFLUXDB_URL/api/v2/ping" | grep -q "204"
    check_status $? "InfluxDB is reachable"
else
    echo -e "${YELLOW}⚠${NC}  Cannot test InfluxDB connectivity (missing credentials)"
fi

# 4. Check NBP service
echo ""
echo "4. Checking NBP service readiness..."
[ -d "nbp-service" ]
check_status $? "NBP service directory exists"

[ -f "nbp-service/Dockerfile" ]
check_status $? "NBP service Dockerfile exists"

# 5. Check database backups
echo ""
echo "5. Checking database backups..."
BACKUP_DIR="backups/$(date +%Y%m%d)"
[ -d "$BACKUP_DIR" ] || mkdir -p "$BACKUP_DIR"
check_status $? "Backup directory created: $BACKUP_DIR"

# 6. Check existing data
echo ""
echo "6. Analyzing existing data..."
if [ -f "backend/data/usage_tracking.db" ]; then
    SIZE=$(du -h backend/data/usage_tracking.db | cut -f1)
    echo -e "${GREEN}✓${NC} SQLite database found (size: $SIZE)"
else
    echo -e "${YELLOW}⚠${NC}  No existing SQLite database found"
fi

# 7. Check code readiness
echo ""
echo "7. Checking code readiness..."
[ -f "backend/open_webui/usage_tracking/services/influxdb_service.py" ]
check_status $? "InfluxDBService implemented"

grep -q "INFLUXDB_ENABLED" backend/open_webui/usage_tracking/services/webhook_service.py
check_status $? "Feature flags implemented in WebhookService"

# 8. Check monitoring tools
echo ""
echo "8. Checking monitoring tools..."
[ -f "backend/open_webui/utils/influxdb_sqlite_comparison.py" ]
check_status $? "Data comparison tool available"

[ -f "backend/open_webui/usage_tracking/tools/compare_storage.py" ]
check_status $? "CLI comparison tool available"

# Summary
echo ""
echo "======================================="
if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}✅ All checks passed! Ready for migration.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please address issues before migrating.${NC}"
    exit 1
fi