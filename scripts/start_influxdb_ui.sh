#!/bin/bash
# Script to start InfluxDB and open the UI in browser

echo "🚀 Starting InfluxDB for mAI development..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create network if it doesn't exist
echo "📦 Checking Docker network..."
if ! docker network ls | grep -q "mai-dev-network"; then
    echo "Creating mai-dev-network..."
    docker network create mai-dev-network
fi

# Start InfluxDB container
echo "🔄 Starting InfluxDB container..."
docker-compose -f docker-compose.influxdb.yml up -d influxdb

# Wait for InfluxDB to be ready
echo "⏳ Waiting for InfluxDB to be ready..."
for i in {1..30}; do
    if docker exec mai-influxdb-dev influx ping > /dev/null 2>&1; then
        echo "✅ InfluxDB is ready!"
        break
    fi
    echo -n "."
    sleep 2
done

# Show connection details
echo ""
echo "📊 InfluxDB UI Access Details:"
echo "================================"
echo "URL:      http://localhost:8086"
echo "Username: admin"
echo "Password: adminpassword123"
echo "Token:    dev-token-for-testing-only"
echo "Org:      mAI-dev"
echo "Bucket:   mai_usage_raw_dev"
echo "================================"

# Open browser (works on macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🌐 Opening InfluxDB UI in browser..."
    sleep 2
    open "http://localhost:8086"
elif command -v xdg-open > /dev/null; then
    # Linux
    echo "🌐 Opening InfluxDB UI in browser..."
    sleep 2
    xdg-open "http://localhost:8086"
else
    echo "👉 Please open http://localhost:8086 in your browser"
fi

# Show useful commands
echo ""
echo "📝 Useful commands:"
echo "  View logs:    docker logs -f mai-influxdb-dev"
echo "  Stop:         docker-compose -f docker-compose.influxdb.yml stop influxdb"
echo "  Remove:       docker-compose -f docker-compose.influxdb.yml down"
echo "  Shell access: docker exec -it mai-influxdb-dev influx"

# Check if Grafana is also needed
read -p "Would you also like to start Grafana for advanced visualization? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Starting Grafana..."
    docker-compose -f docker-compose.influxdb.yml up -d grafana
    echo "✅ Grafana started at http://localhost:3001 (admin/admin)"
fi