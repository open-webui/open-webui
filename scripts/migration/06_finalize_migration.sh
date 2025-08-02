#!/bin/bash
# Finalize InfluxDB migration - disable dual-write mode

echo "🎯 Finalizing InfluxDB Migration"
echo "================================"
echo ""

# Safety check
echo "⚠️  WARNING: This will disable dual-write mode!"
echo "SQLite will no longer receive webhook data."
echo ""
read -p "Have you validated the migration? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Aborted. Run validation first: ./05_validate_migration.sh"
    exit 1
fi

# Configuration
ENV_FILE=".env"
BACKUP_DIR="backups/finalization_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 1. Final backup
echo ""
echo "1. Creating final SQLite backup..."
./02_backup_sqlite_data.sh
cp -r backups/pre_influxdb_migration_* "$BACKUP_DIR/"
echo "  ✅ Final backup completed"

# 2. Disable dual-write mode
echo ""
echo "2. Disabling dual-write mode..."

# Update environment
sed -i.bak "s/DUAL_WRITE_MODE=true/DUAL_WRITE_MODE=false/" "$ENV_FILE"
echo "  ✅ Environment updated"

# 3. Update all client containers
echo ""
echo "3. Updating client containers..."

for client_dir in /opt/mai/clients/*; do
    if [ -d "$client_dir" ]; then
        client_id=$(basename "$client_dir")
        echo "  Processing client: $client_id"
        
        # Update client environment
        cd "$client_dir"
        sed -i.bak "s/DUAL_WRITE_MODE=true/DUAL_WRITE_MODE=false/" .env
        
        # Restart container
        docker-compose restart
        cd - > /dev/null
        
        echo "  ✅ $client_id updated"
    fi
done

# 4. Verify configuration
echo ""
echo "4. Verifying configuration..."

cat > /tmp/verify_config.py <<'EOF'
import os
import sys
sys.path.insert(0, '/opt/mai/backend')

from open_webui.usage_tracking.services.webhook_service import WebhookService

service = WebhookService()
print(f"InfluxDB enabled: {service.influxdb_enabled}")
print(f"Dual-write mode: {service.dual_write_mode}")

if service.influxdb_enabled and not service.dual_write_mode:
    print("✅ InfluxDB is now the primary storage!")
else:
    print("❌ Configuration error!")
    sys.exit(1)
EOF

python3 /tmp/verify_config.py

# 5. Update monitoring
echo ""
echo "5. Updating monitoring configuration..."

# Create post-migration monitoring script
cat > /opt/mai/monitor_influxdb_primary.sh <<'EOF'
#!/bin/bash
# Monitor InfluxDB as primary storage

# Check InfluxDB health
if ! docker exec mai-influxdb-prod influx ping > /dev/null 2>&1; then
    echo "CRITICAL: InfluxDB not responding - data loss risk!"
    # Send alert to ops team
    exit 2
fi

# Check recent writes (last 5 minutes)
RECENT_WRITES=$(docker exec mai-influxdb-prod influx query \
    -o mai-prod \
    'from(bucket: "mai_usage_raw")
     |> range(start: -5m)
     |> count()' \
    2>/dev/null | grep -v "_start" | wc -l)

if [ "$RECENT_WRITES" -eq 0 ]; then
    echo "WARNING: No recent writes to InfluxDB"
    exit 1
fi

echo "OK: InfluxDB healthy, $RECENT_WRITES recent writes"
exit 0
EOF
chmod +x /opt/mai/monitor_influxdb_primary.sh

# 6. Clean up old SQLite data (optional)
echo ""
echo "6. SQLite data cleanup..."
echo "  ℹ️  SQLite webhook data is no longer being updated"
echo "  ℹ️  Daily summaries will continue to use SQLite"
echo "  ℹ️  Raw webhook tables can be archived after 30 days"

# Create cleanup script for future use
cat > /opt/mai/archive_sqlite_webhooks.sh <<'EOF'
#!/bin/bash
# Archive old SQLite webhook data (run after 30 days)

ARCHIVE_DIR="/archives/sqlite_webhooks_$(date +%Y%m%d)"
mkdir -p "$ARCHIVE_DIR"

echo "Archiving SQLite webhook data..."

# Export data before cleanup
for db in /opt/mai/clients/*/data/usage_tracking.db; do
    if [ -f "$db" ]; then
        client=$(basename $(dirname $(dirname "$db")))
        sqlite3 "$db" ".dump processed_generations" > "$ARCHIVE_DIR/${client}_webhooks.sql"
        
        # Optional: Clear old data
        # sqlite3 "$db" "DELETE FROM processed_generations WHERE created_at < date('now', '-30 days');"
    fi
done

tar -czf "$ARCHIVE_DIR.tar.gz" -C "$(dirname "$ARCHIVE_DIR")" "$(basename "$ARCHIVE_DIR")"
rm -rf "$ARCHIVE_DIR"

echo "Archive created: $ARCHIVE_DIR.tar.gz"
EOF
chmod +x /opt/mai/archive_sqlite_webhooks.sh

# 7. Update cron jobs
echo ""
echo "7. Updating scheduled tasks..."

# Update crontab
(crontab -l 2>/dev/null | grep -v "dual_write") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/mai/monitor_influxdb_primary.sh") | crontab -

echo "  ✅ Monitoring updated"

# 8. Create rollback script
echo ""
echo "8. Creating rollback script (just in case)..."

cat > /opt/mai/rollback_to_dual_write.sh <<EOF
#!/bin/bash
# Emergency rollback to dual-write mode

echo "🔄 Rolling back to dual-write mode..."

# Re-enable dual-write
sed -i "s/DUAL_WRITE_MODE=false/DUAL_WRITE_MODE=true/" /opt/mai/.env

# Restart all containers
for client_dir in /opt/mai/clients/*; do
    if [ -d "\$client_dir" ]; then
        cd "\$client_dir"
        sed -i "s/DUAL_WRITE_MODE=false/DUAL_WRITE_MODE=true/" .env
        docker-compose restart
        cd - > /dev/null
    fi
done

echo "✅ Rolled back to dual-write mode"
echo "Run validation again before retrying migration"
EOF
chmod +x /opt/mai/rollback_to_dual_write.sh

# 9. Final summary
echo ""
echo "================================"
echo "🎉 InfluxDB Migration Complete!"
echo ""
echo "📊 Current Configuration:"
echo "   - Primary storage: InfluxDB"
echo "   - SQLite: Daily summaries only"
echo "   - Dual-write: DISABLED"
echo ""
echo "📋 Post-Migration Checklist:"
echo "   [ ] Monitor InfluxDB health closely for 24 hours"
echo "   [ ] Check webhook processing logs"
echo "   [ ] Run daily comparison reports for 1 week"
echo "   [ ] Update documentation"
echo "   [ ] Notify team of migration completion"
echo ""
echo "🔧 Useful Commands:"
echo "   - Monitor: /opt/mai/monitor_influxdb_primary.sh"
echo "   - Rollback: /opt/mai/rollback_to_dual_write.sh"
echo "   - Archive SQLite: /opt/mai/archive_sqlite_webhooks.sh (after 30 days)"
echo ""
echo "📁 Backups stored in: $BACKUP_DIR"
echo ""
echo "✅ Migration finalized successfully!"