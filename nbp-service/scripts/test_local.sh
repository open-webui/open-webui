#!/bin/bash
# Test script for NBP service

echo "Testing NBP Service endpoints..."

# Health check
echo -e "\n1. Health Check:"
curl -s http://localhost:8001/health | jq .

# Current rate
echo -e "\n2. Current USD/PLN rate:"
curl -s http://localhost:8001/api/usd-pln-rate | jq .

# Specific date
echo -e "\n3. Rate for 2025-01-15:"
curl -s "http://localhost:8001/api/usd-pln-rate?date=2025-01-15" | jq .

# Date range
echo -e "\n4. Rates for January 2025 (first week):"
curl -s "http://localhost:8001/api/usd-pln-rate/range?start_date=2025-01-01&end_date=2025-01-07" | jq .

# Clear cache
echo -e "\n5. Clear cache:"
curl -s -X POST http://localhost:8001/api/cache/clear | jq .