#!/bin/bash
# Enable dual-write mode for safe migration

echo "🔄 Enabling Dual-Write Mode"
echo "==========================="
echo ""

# Configuration
ENV_FILE=".env"
BACKUP_ENV=".env.backup.$(date +%Y%m%d_%H%M%S)"

# Function to update or add environment variable
update_env() {
    local key=$1
    local value=$2
    
    if grep -q "^${key}=" "$ENV_FILE"; then
        # Update existing
        sed -i.tmp "s/^${key}=.*/${key}=${value}/" "$ENV_FILE"
        echo "  Updated: ${key}=${value}"
    else
        # Add new
        echo "${key}=${value}" >> "$ENV_FILE"
        echo "  Added: ${key}=${value}"
    fi
}

# 1. Backup current environment
echo "1. Backing up current environment..."
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$BACKUP_ENV"
    echo "  ✅ Backup created: $BACKUP_ENV"
else
    echo "  ⚠️  No existing .env file found"
    touch "$ENV_FILE"
fi

# 2. Enable InfluxDB integration
echo ""
echo "2. Configuring InfluxDB integration..."
update_env "INFLUXDB_ENABLED" "true"
update_env "INFLUXDB_URL" "${INFLUXDB_URL:-http://localhost:8086}"
update_env "INFLUXDB_TOKEN" "${INFLUXDB_TOKEN}"
update_env "INFLUXDB_ORG" "${INFLUXDB_ORG:-mai-prod}"
update_env "INFLUXDB_BUCKET" "${INFLUXDB_BUCKET:-mai_usage_raw}"

# 3. Enable dual-write mode
echo ""
echo "3. Enabling dual-write mode..."
update_env "DUAL_WRITE_MODE" "true"
update_env "DUAL_WRITE_LOG_DISCREPANCIES" "true"

# 4. Configure performance settings
echo ""
echo "4. Configuring performance settings..."
update_env "INFLUXDB_WRITE_BATCH_SIZE" "1000"
update_env "INFLUXDB_WRITE_FLUSH_INTERVAL" "10000"
update_env "INFLUXDB_WRITE_TIMEOUT" "5000"

# 5. Update Docker containers
echo ""
echo "5. Updating Docker containers with new configuration..."

# Function to update container environment
update_container() {
    local container=$1
    echo "  Updating $container..."
    
    if docker ps | grep -q "$container"; then
        # Export environment and restart container
        docker-compose stop "$container"
        docker-compose up -d "$container"
        echo "  ✅ $container updated"
    else
        echo "  ⚠️  $container not running"
    fi
}

# Update all mAI containers
for client_dir in /opt/mai/clients/*; do
    if [ -d "$client_dir" ]; then
        client_id=$(basename "$client_dir")
        echo "  Processing client: $client_id"
        
        # Copy environment updates to client
        if [ -f "$client_dir/.env" ]; then
            # Backup client env
            cp "$client_dir/.env" "$client_dir/.env.backup.$(date +%Y%m%d_%H%M%S)"
            
            # Update client env with InfluxDB settings
            cd "$client_dir"
            grep "^INFLUXDB_" "$ENV_FILE" >> .env
            grep "^DUAL_WRITE_" "$ENV_FILE" >> .env
            
            # Restart client container
            docker-compose restart
            cd - > /dev/null
        fi
    fi
done

# 6. Verify dual-write mode
echo ""
echo "6. Verifying dual-write mode..."

# Create test script
cat > /tmp/test_dual_write.py <<'EOF'
import os
import sys
sys.path.insert(0, '/opt/mai/backend')

from open_webui.usage_tracking.services.webhook_service import WebhookService

service = WebhookService()
print(f"InfluxDB enabled: {service.influxdb_enabled}")
print(f"Dual-write mode: {service.dual_write_mode}")
print(f"Log discrepancies: {service.log_discrepancies}")

if service.influxdb_enabled and service.dual_write_mode:
    print("✅ Dual-write mode is active!")
else:
    print("❌ Dual-write mode is NOT active!")
    sys.exit(1)
EOF

# Run verification
python3 /tmp/test_dual_write.py

# 7. Create monitoring script
echo ""
echo "7. Creating dual-write monitoring script..."
cat > /opt/mai/monitor_dual_write.sh <<'EOF'
#!/bin/bash
# Monitor dual-write mode discrepancies

LOG_FILE="/var/log/mai/dual_write_discrepancies.log"
ALERT_THRESHOLD=10

# Count recent discrepancies (last hour)
DISCREPANCIES=$(grep "Dual-write discrepancy" "$LOG_FILE" 2>/dev/null | \
                grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" | \
                wc -l)

if [ "$DISCREPANCIES" -gt "$ALERT_THRESHOLD" ]; then
    echo "⚠️  High discrepancy rate: $DISCREPANCIES in last hour"
    echo "Check logs: $LOG_FILE"
    exit 1
else
    echo "✅ Dual-write healthy: $DISCREPANCIES discrepancies in last hour"
    exit 0
fi
EOF
chmod +x /opt/mai/monitor_dual_write.sh

# 8. Summary
echo ""
echo "==========================="
echo "✅ Dual-write mode enabled successfully!"
echo ""
echo "📋 Configuration:"
echo "   - SQLite: Continues to write as before"
echo "   - InfluxDB: Now receiving all webhook data"
echo "   - Discrepancies: Logged for monitoring"
echo ""
echo "🔍 Monitoring:"
echo "   - Check discrepancies: /opt/mai/monitor_dual_write.sh"
echo "   - View logs: tail -f /var/log/mai/webhook_service.log"
echo "   - Compare data: python -m open_webui.usage_tracking.tools.compare_storage today"
echo ""
echo "⏰ Recommended timeline:"
echo "   1. Run in dual-write mode for 24-48 hours"
echo "   2. Monitor discrepancy rates"
echo "   3. Run comparison reports daily"
echo "   4. Disable dual-write when confident"
echo ""
echo "💡 To disable dual-write later:"
echo "   DUAL_WRITE_MODE=false"