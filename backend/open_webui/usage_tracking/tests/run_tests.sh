#!/bin/bash
# Run InfluxDBService tests

echo "Running InfluxDBService unit tests..."

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

# Run tests with coverage
echo "Running basic tests..."
pytest backend/open_webui/usage_tracking/tests/services/test_influxdb_service.py -v --cov=backend.open_webui.usage_tracking.services.influxdb_service

echo -e "\nRunning edge case tests..."
pytest backend/open_webui/usage_tracking/tests/services/test_influxdb_service_edge_cases.py -v

echo -e "\nRunning all tests with detailed coverage..."
pytest backend/open_webui/usage_tracking/tests/services/ -v --cov=backend.open_webui.usage_tracking.services.influxdb_service --cov-report=term-missing

echo -e "\nGenerating HTML coverage report..."
pytest backend/open_webui/usage_tracking/tests/services/ --cov=backend.open_webui.usage_tracking.services.influxdb_service --cov-report=html

echo "Tests completed. Check htmlcov/index.html for detailed coverage report."