#!/bin/bash
# Deploy InfluxDB for production use

echo "🚀 Deploying InfluxDB for Production"
echo "===================================="
echo ""

# Check if running as root (recommended for production)
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Warning: Not running as root. Some operations may fail."
fi

# Configuration
INFLUXDB_VERSION="2.7"
INFLUXDB_CONFIG_PATH="/etc/influxdb"
INFLUXDB_DATA_PATH="/var/lib/influxdb2"
INFLUXDB_PORT="8086"

# Function to generate secure token
generate_token() {
    openssl rand -base64 48 | tr -d "=+/" | cut -c1-88
}

# 1. Create InfluxDB directories
echo "1. Creating InfluxDB directories..."
mkdir -p "$INFLUXDB_CONFIG_PATH"
mkdir -p "$INFLUXDB_DATA_PATH"
chmod 700 "$INFLUXDB_DATA_PATH"

# 2. Generate production configuration
echo ""
echo "2. Generating production configuration..."

# Generate secure admin password if not provided
if [ -z "$INFLUXDB_ADMIN_PASSWORD" ]; then
    INFLUXDB_ADMIN_PASSWORD=$(openssl rand -base64 32)
    echo "Generated admin password: $INFLUXDB_ADMIN_PASSWORD"
    echo "⚠️  SAVE THIS PASSWORD - YOU WILL NEED IT!"
fi

# Generate token if not provided
if [ -z "$INFLUXDB_ADMIN_TOKEN" ]; then
    INFLUXDB_ADMIN_TOKEN=$(generate_token)
    echo "Generated admin token: $INFLUXDB_ADMIN_TOKEN"
fi

# 3. Create docker-compose for production
echo ""
echo "3. Creating production docker-compose..."
cat > docker-compose.influxdb.prod.yml <<EOF
version: '3.8'

services:
  influxdb:
    image: influxdb:${INFLUXDB_VERSION}
    container_name: mai-influxdb-prod
    restart: always
    
    environment:
      # Initial setup
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=${INFLUXDB_ADMIN_PASSWORD}
      - DOCKER_INFLUXDB_INIT_ORG=mai-prod
      - DOCKER_INFLUXDB_INIT_BUCKET=mai_usage_raw
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${INFLUXDB_ADMIN_TOKEN}
      - DOCKER_INFLUXDB_INIT_RETENTION=30d
      
      # Production settings
      - INFLUXD_HTTP_BIND_ADDRESS=:8086
      - INFLUXD_REPORTING_DISABLED=true
      - INFLUXD_LOG_LEVEL=warn
      
    ports:
      - "127.0.0.1:${INFLUXDB_PORT}:8086"  # Only bind to localhost
      
    volumes:
      - ${INFLUXDB_DATA_PATH}:/var/lib/influxdb2:rw
      - ${INFLUXDB_CONFIG_PATH}:/etc/influxdb2:rw
      
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
        
    healthcheck:
      test: ["CMD", "influx", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
      
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
        
networks:
  default:
    name: mai-production
    external: true
EOF

# 4. Create systemd service
echo ""
echo "4. Creating systemd service..."
cat > /etc/systemd/system/mai-influxdb.service <<EOF
[Unit]
Description=mAI InfluxDB Service
Requires=docker.service
After=docker.service

[Service]
Type=simple
Restart=always
RestartSec=5
WorkingDirectory=/opt/mai
ExecStart=/usr/local/bin/docker-compose -f docker-compose.influxdb.prod.yml up
ExecStop=/usr/local/bin/docker-compose -f docker-compose.influxdb.prod.yml down
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 5. Create backup script
echo ""
echo "5. Creating backup script..."
cat > /opt/mai/backup_influxdb.sh <<'EOF'
#!/bin/bash
# InfluxDB backup script

BACKUP_DIR="/backups/influxdb/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup InfluxDB
docker exec mai-influxdb-prod influx backup "$BACKUP_DIR" \
    -t "$INFLUXDB_ADMIN_TOKEN" \
    --host http://localhost:8086

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
rm -rf "$BACKUP_DIR"

# Keep only last 7 days of backups
find /backups/influxdb -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR.tar.gz"
EOF
chmod +x /opt/mai/backup_influxdb.sh

# 6. Create monitoring script
echo ""
echo "6. Creating monitoring script..."
cat > /opt/mai/monitor_influxdb.sh <<'EOF'
#!/bin/bash
# InfluxDB monitoring script

# Check if InfluxDB is running
if ! docker ps | grep -q mai-influxdb-prod; then
    echo "CRITICAL: InfluxDB container not running"
    exit 2
fi

# Check InfluxDB health
if ! docker exec mai-influxdb-prod influx ping > /dev/null 2>&1; then
    echo "CRITICAL: InfluxDB not responding to ping"
    exit 2
fi

# Check disk usage
DISK_USAGE=$(df -h /var/lib/influxdb2 | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "WARNING: Disk usage at ${DISK_USAGE}%"
    exit 1
fi

echo "OK: InfluxDB healthy, disk usage at ${DISK_USAGE}%"
exit 0
EOF
chmod +x /opt/mai/monitor_influxdb.sh

# 7. Create production environment file
echo ""
echo "7. Creating production environment file..."
cat > /opt/mai/.env.influxdb.prod <<EOF
# InfluxDB Production Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=${INFLUXDB_ADMIN_TOKEN}
INFLUXDB_ORG=mai-prod
INFLUXDB_BUCKET=mai_usage_raw

# Feature flags
INFLUXDB_ENABLED=true
DUAL_WRITE_MODE=true  # Enable initially for safety
DUAL_WRITE_LOG_DISCREPANCIES=true

# Performance settings
INFLUXDB_WRITE_BATCH_SIZE=1000
INFLUXDB_WRITE_FLUSH_INTERVAL=10000
INFLUXDB_WRITE_RETRY_INTERVAL=5000
INFLUXDB_WRITE_MAX_RETRIES=5
EOF
chmod 600 /opt/mai/.env.influxdb.prod

# 8. Summary and next steps
echo ""
echo "===================================="
echo "✅ InfluxDB production setup complete!"
echo ""
echo "📋 Configuration saved to:"
echo "   - Docker Compose: docker-compose.influxdb.prod.yml"
echo "   - Environment: /opt/mai/.env.influxdb.prod"
echo "   - Systemd service: /etc/systemd/system/mai-influxdb.service"
echo ""
echo "🔐 Credentials:"
echo "   - Admin user: admin"
echo "   - Admin password: $INFLUXDB_ADMIN_PASSWORD"
echo "   - Admin token: $INFLUXDB_ADMIN_TOKEN"
echo ""
echo "⚠️  IMPORTANT: Save these credentials securely!"
echo ""
echo "📚 Next steps:"
echo "   1. Start InfluxDB: systemctl start mai-influxdb"
echo "   2. Enable auto-start: systemctl enable mai-influxdb"
echo "   3. Check status: systemctl status mai-influxdb"
echo "   4. Set up daily backups: crontab -e"
echo "      0 2 * * * /opt/mai/backup_influxdb.sh"
echo "   5. Configure monitoring in your monitoring system"
echo ""
echo "🔍 To access InfluxDB UI (via SSH tunnel):"
echo "   ssh -L 8086:localhost:8086 your-server"
echo "   Then open: http://localhost:8086"