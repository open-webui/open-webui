#!/bin/bash
# Database Backup Script for Client Organization System
# Usage: ./db_backup.sh [daily|weekly|monthly]

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-mai_db}"
DB_USER="${DB_USER:-mai_user}"
BACKUP_DIR="${BACKUP_DIR:-/backup}"
LOG_FILE="${LOG_FILE:-/var/log/mai_backup.log}"

# Create backup directories
mkdir -p "$BACKUP_DIR"/{daily,weekly,monthly,archives}

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Backup function
perform_backup() {
    local backup_type="$1"
    local backup_file="$BACKUP_DIR/$backup_type/mai_db_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    log "Starting $backup_type backup..."
    
    # Create compressed backup
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$backup_file"; then
        log "✅ Backup completed: $backup_file"
        
        # Get backup size
        local size=$(du -h "$backup_file" | cut -f1)
        log "📦 Backup size: $size"
        
        # Verify backup integrity
        if gunzip -t "$backup_file" 2>/dev/null; then
            log "✅ Backup integrity verified"
            return 0
        else
            log "❌ Backup integrity check failed"
            return 1
        fi
    else
        log "❌ Backup failed"
        return 1
    fi
}

# Cleanup old backups
cleanup_backups() {
    local backup_type="$1"
    local retention_days="$2"
    
    log "🧹 Cleaning up $backup_type backups older than $retention_days days..."
    
    find "$BACKUP_DIR/$backup_type" -name "mai_db_*.sql.gz" -mtime +$retention_days -delete
    
    local remaining=$(find "$BACKUP_DIR/$backup_type" -name "mai_db_*.sql.gz" | wc -l)
    log "📁 $remaining $backup_type backup(s) remaining"
}

# Check database connectivity
check_connectivity() {
    log "🔍 Checking database connectivity..."
    
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; then
        log "✅ Database is accessible"
        return 0
    else
        log "❌ Database is not accessible"
        return 1
    fi
}

# Generate backup report
generate_report() {
    local backup_type="$1"
    
    log "📊 Generating backup report..."
    
    # Database size
    local db_size=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'))" 2>/dev/null | xargs)
    
    # Table counts
    local client_orgs=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM client_organizations" 2>/dev/null | xargs)
    local usage_records=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM client_usage WHERE usage_date >= CURRENT_DATE - INTERVAL '30 days'" 2>/dev/null | xargs)
    
    log "📈 Database Stats:"
    log "   Database size: ${db_size:-Unknown}"
    log "   Client organizations: ${client_orgs:-Unknown}"
    log "   Usage records (30 days): ${usage_records:-Unknown}"
}

# Send notification (customize for your notification system)
send_notification() {
    local status="$1"
    local message="$2"
    
    # Example: Send to Slack, email, or logging system
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"MAI Backup $status: $message\"}" \
    #   "$SLACK_WEBHOOK_URL"
    
    log "📢 Notification: $status - $message"
}

# Main backup logic
main() {
    local backup_type="${1:-daily}"
    
    log "🚀 Starting MAI database backup ($backup_type)"
    
    # Check prerequisites
    if ! command -v pg_dump >/dev/null 2>&1; then
        log "❌ pg_dump not found. Please install PostgreSQL client tools."
        exit 1
    fi
    
    if ! check_connectivity; then
        send_notification "FAILED" "Database connectivity check failed"
        exit 1
    fi
    
    # Perform backup based on type
    case "$backup_type" in
        daily)
            if perform_backup "daily"; then
                cleanup_backups "daily" 7
                generate_report "daily"
                send_notification "SUCCESS" "Daily backup completed"
            else
                send_notification "FAILED" "Daily backup failed"
                exit 1
            fi
            ;;
        weekly)
            if perform_backup "weekly"; then
                cleanup_backups "weekly" 28
                generate_report "weekly"
                send_notification "SUCCESS" "Weekly backup completed"
            else
                send_notification "FAILED" "Weekly backup failed"
                exit 1
            fi
            ;;
        monthly)
            if perform_backup "monthly"; then
                cleanup_backups "monthly" 365
                generate_report "monthly"
                send_notification "SUCCESS" "Monthly backup completed"
            else
                send_notification "FAILED" "Monthly backup failed"
                exit 1
            fi
            ;;
        *)
            log "❌ Invalid backup type: $backup_type"
            log "Usage: $0 [daily|weekly|monthly]"
            exit 1
            ;;
    esac
    
    log "✅ Backup process completed"
}

# Run main function
main "$@"