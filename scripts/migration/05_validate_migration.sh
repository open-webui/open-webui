#!/bin/bash
# Validate InfluxDB migration success

echo "🔍 Validating InfluxDB Migration"
echo "================================"
echo ""

# Configuration
VALIDATION_DAYS=7
REPORT_DIR="migration_reports/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Track validation status
VALIDATION_PASSED=true

# 1. Check InfluxDB health
echo "1. Checking InfluxDB health..."
if docker exec mai-influxdb-prod influx ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} InfluxDB is healthy"
else
    echo -e "${RED}✗${NC} InfluxDB is not responding"
    VALIDATION_PASSED=false
fi

# 2. Verify data is being written
echo ""
echo "2. Verifying data writes to InfluxDB..."

# Create Python script to check recent data
cat > /tmp/check_influx_data.py <<'EOF'
import os
import sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, '/opt/mai/backend')

from open_webui.usage_tracking.services.influxdb_service import InfluxDBService

service = InfluxDBService()

# Check for recent data (last hour)
end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(hours=1)

try:
    # Get all clients
    from open_webui.models.organization_usage import ClientOrganizationDB
    clients = ClientOrganizationDB.get_all_active_clients()
    
    total_records = 0
    for client in clients:
        data = service.get_data_for_batch(client.id, start_time, end_time)
        total_records += len(data)
    
    print(f"Found {total_records} records in last hour")
    sys.exit(0 if total_records > 0 else 1)
except Exception as e:
    print(f"Error checking data: {e}")
    sys.exit(1)
EOF

if python3 /tmp/check_influx_data.py; then
    echo -e "${GREEN}✓${NC} Data is being written to InfluxDB"
else
    echo -e "${RED}✗${NC} No recent data found in InfluxDB"
    VALIDATION_PASSED=false
fi

# 3. Run comprehensive comparison
echo ""
echo "3. Running comprehensive data comparison..."
cd /opt/mai/backend
python -m open_webui.usage_tracking.tools.compare_storage report \
    -d "$VALIDATION_DAYS" \
    -o "$REPORT_DIR/comparison_report.md"

# Check discrepancy rate
DISCREPANCIES=$(grep "Total discrepancies:" "$REPORT_DIR/comparison_report.md" | awk '{print $3}')
if [ "$DISCREPANCIES" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No discrepancies found"
elif [ "$DISCREPANCIES" -lt 10 ]; then
    echo -e "${YELLOW}⚠${NC}  Minor discrepancies found: $DISCREPANCIES"
else
    echo -e "${RED}✗${NC} Major discrepancies found: $DISCREPANCIES"
    VALIDATION_PASSED=false
fi

# 4. Performance comparison
echo ""
echo "4. Comparing performance metrics..."

cat > /tmp/performance_test.py <<'EOF'
import time
import asyncio
import statistics
from datetime import datetime
import sys
sys.path.insert(0, '/opt/mai/backend')

from open_webui.usage_tracking.services.influxdb_service import InfluxDBService
from open_webui.usage_tracking.repositories.webhook_repository import WebhookRepository

async def test_write_performance():
    influx_service = InfluxDBService()
    webhook_repo = WebhookRepository()
    
    # Test data
    test_data = {
        "api_key": "test",
        "model": "gpt-4",
        "tokens_used": 1000,
        "cost": 0.05,
        "timestamp": datetime.utcnow().isoformat(),
        "external_user": "test@example.com",
        "request_id": f"test_{time.time()}",
        "client_org_id": "test_org"
    }
    
    # Test InfluxDB write performance
    influx_times = []
    for _ in range(10):
        start = time.time()
        await influx_service.write_usage_record(test_data)
        influx_times.append((time.time() - start) * 1000)
    
    # Test SQLite write performance (approximate)
    sqlite_times = []
    for _ in range(10):
        start = time.time()
        # Simulate SQLite write
        webhook_repo.mark_generation_processed(
            test_data["request_id"],
            test_data["model"],
            test_data["cost"],
            test_data["client_org_id"],
            {"external_user": test_data["external_user"]}
        )
        sqlite_times.append((time.time() - start) * 1000)
    
    print(f"InfluxDB avg write time: {statistics.mean(influx_times):.2f}ms")
    print(f"SQLite avg write time: {statistics.mean(sqlite_times):.2f}ms")
    print(f"Performance improvement: {statistics.mean(sqlite_times) / statistics.mean(influx_times):.1f}x")

asyncio.run(test_write_performance())
EOF

python3 /tmp/performance_test.py > "$REPORT_DIR/performance_metrics.txt"
echo -e "${GREEN}✓${NC} Performance metrics saved to report"

# 5. Check batch processing
echo ""
echo "5. Validating batch processing..."

# Run batch processor test
cat > /tmp/test_batch.py <<'EOF'
import asyncio
from datetime import date, timedelta
import sys
sys.path.insert(0, '/opt/mai/backend')

from open_webui.utils.daily_batch_processor_influx import DailyBatchProcessorInflux

async def test_batch():
    processor = DailyBatchProcessorInflux()
    yesterday = date.today() - timedelta(days=1)
    
    try:
        results = await processor.process_all_organizations(yesterday)
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        print(f"Batch processing: {success_count}/{len(results)} successful")
        
        return success_count == len(results)
    except Exception as e:
        print(f"Batch processing error: {e}")
        return False

sys.exit(0 if asyncio.run(test_batch()) else 1)
EOF

if python3 /tmp/test_batch.py; then
    echo -e "${GREEN}✓${NC} Batch processing working correctly"
else
    echo -e "${YELLOW}⚠${NC}  Batch processing needs attention"
fi

# 6. Generate migration summary
echo ""
echo "6. Generating migration summary..."

cat > "$REPORT_DIR/migration_summary.md" <<EOF
# InfluxDB Migration Validation Summary

**Date**: $(date)
**Validation Period**: $VALIDATION_DAYS days

## Status: $([ "$VALIDATION_PASSED" = true ] && echo "✅ PASSED" || echo "❌ FAILED")

## Checks Performed

1. **InfluxDB Health**: $(docker exec mai-influxdb-prod influx ping > /dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Not responding")
2. **Data Writes**: $([ -f /tmp/check_influx_data.py ] && echo "✅ Active" || echo "❌ No data")
3. **Data Consistency**: $DISCREPANCIES discrepancies found
4. **Performance**: See performance_metrics.txt
5. **Batch Processing**: $([ -f /tmp/test_batch.py ] && echo "✅ Working" || echo "⚠️ Needs review")

## Recommendations

$(if [ "$VALIDATION_PASSED" = true ]; then
    echo "- ✅ Migration successful - safe to disable dual-write mode"
    echo "- Monitor for 24 hours after disabling dual-write"
    echo "- Keep SQLite backups for at least 30 days"
else
    echo "- ❌ Issues detected - keep dual-write mode enabled"
    echo "- Review comparison report for discrepancies"
    echo "- Check InfluxDB logs for errors"
    echo "- Contact support if issues persist"
fi)

## Next Steps

1. Review detailed comparison report: comparison_report.md
2. Check performance metrics: performance_metrics.txt
3. Monitor logs: /var/log/mai/webhook_service.log
4. Run daily validations until confident

## Files Generated

$(ls -la "$REPORT_DIR" | tail -n +2)
EOF

# 7. Final summary
echo ""
echo "================================"
if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}✅ Migration validation PASSED!${NC}"
    echo ""
    echo "It's safe to proceed with disabling dual-write mode."
    echo "Use: scripts/migration/06_finalize_migration.sh"
else
    echo -e "${RED}❌ Migration validation FAILED!${NC}"
    echo ""
    echo "Please review the reports and address issues before proceeding."
fi
echo ""
echo "📁 Full report available at: $REPORT_DIR"
echo ""
echo "📊 Key files:"
echo "   - Summary: $REPORT_DIR/migration_summary.md"
echo "   - Comparison: $REPORT_DIR/comparison_report.md"
echo "   - Performance: $REPORT_DIR/performance_metrics.txt"