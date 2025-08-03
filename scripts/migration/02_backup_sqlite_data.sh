#!/bin/bash
# Backup SQLite data before migration

echo "💾 Backing up SQLite databases..."
echo "================================"

# Configuration
BACKUP_ROOT="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/pre_influxdb_migration_$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to backup a database
backup_database() {
    local db_path=$1
    local db_name=$2
    
    if [ -f "$db_path" ]; then
        echo "📦 Backing up $db_name..."
        
        # Copy the database file
        cp "$db_path" "$BACKUP_DIR/${db_name}_$TIMESTAMP.db"
        
        # Create SQL dump
        sqlite3 "$db_path" ".dump" > "$BACKUP_DIR/${db_name}_$TIMESTAMP.sql"
        
        # Create compressed archive
        gzip -c "$BACKUP_DIR/${db_name}_$TIMESTAMP.sql" > "$BACKUP_DIR/${db_name}_$TIMESTAMP.sql.gz"
        
        # Get database stats
        echo "  - Size: $(du -h "$db_path" | cut -f1)"
        echo "  - Tables: $(sqlite3 "$db_path" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "N/A")"
        
        # Export usage data as CSV
        if [[ "$db_name" == "usage_tracking" ]]; then
            echo "  - Exporting usage data to CSV..."
            sqlite3 -header -csv "$db_path" \
                "SELECT * FROM processed_generations ORDER BY created_at DESC;" \
                > "$BACKUP_DIR/processed_generations_$TIMESTAMP.csv" 2>/dev/null || true
            
            sqlite3 -header -csv "$db_path" \
                "SELECT * FROM client_daily_usage ORDER BY usage_date DESC;" \
                > "$BACKUP_DIR/client_daily_usage_$TIMESTAMP.csv" 2>/dev/null || true
        fi
        
        echo "  ✅ Backup completed"
    else
        echo "⚠️  $db_name not found at $db_path"
    fi
}

# Backup main databases
backup_database "backend/data/webui.db" "webui"
backup_database "backend/data/usage_tracking.db" "usage_tracking"
backup_database "backend/data/usage_summary.db" "usage_summary"

# Backup environment configuration
echo ""
echo "📋 Backing up configuration..."
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/env_$TIMESTAMP.txt"
    echo "  ✅ Environment configuration backed up"
fi

# Create backup manifest
echo ""
echo "📝 Creating backup manifest..."
cat > "$BACKUP_DIR/manifest.json" <<EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date)",
    "type": "pre_influxdb_migration",
    "files": [
        $(ls -1 "$BACKUP_DIR" | grep -v manifest.json | awk '{print "\"" $0 "\""}' | paste -sd,)
    ],
    "notes": "Backup created before InfluxDB migration"
}
EOF

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

# Create verification script
cat > "$BACKUP_DIR/verify_backup.sh" <<'EOF'
#!/bin/bash
echo "🔍 Verifying backup integrity..."

ERRORS=0

for db_file in *.db; do
    if [ -f "$db_file" ]; then
        echo -n "Checking $db_file... "
        if sqlite3 "$db_file" "PRAGMA integrity_check;" | grep -q "ok"; then
            echo "✅ OK"
        else
            echo "❌ CORRUPT"
            ((ERRORS++))
        fi
    fi
done

if [ $ERRORS -eq 0 ]; then
    echo "✅ All backups verified successfully!"
else
    echo "❌ $ERRORS backup(s) failed verification!"
    exit 1
fi
EOF

chmod +x "$BACKUP_DIR/verify_backup.sh"

# Summary
echo ""
echo "================================"
echo "✅ Backup completed successfully!"
echo ""
echo "📁 Backup location: $BACKUP_DIR"
echo "💾 Total size: $TOTAL_SIZE"
echo ""
echo "To verify backup integrity, run:"
echo "  cd $BACKUP_DIR && ./verify_backup.sh"
echo ""
echo "⚠️  Keep this backup until migration is confirmed successful!"