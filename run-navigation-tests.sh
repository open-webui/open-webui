#!/bin/bash
# Script to run navigation Cypress tests following docs/CYPRESS_TEST_SETUP.md

set -e

echo "=== Navigation Tests Runner ==="
echo ""

# Check if services are running
echo "Checking if backend is running..."
if ! curl -s http://localhost:8080/health > /dev/null; then
    echo "ERROR: Backend is not running on port 8080"
    echo "Please start it with: cd backend && ./start.sh"
    exit 1
fi
echo "✓ Backend is running"

echo ""
echo "Checking if frontend is running..."
FRONTEND_PORT=""
if curl -s http://localhost:5173 > /dev/null; then
    FRONTEND_PORT="5173"
    echo "✓ Frontend is running on port 5173"
elif curl -s http://localhost:5174 > /dev/null; then
    FRONTEND_PORT="5174"
    echo "✓ Frontend is running on port 5174"
else
    echo "ERROR: Frontend is not running on port 5173 or 5174"
    echo "Please start it with: npm run dev"
    exit 1
fi

echo ""
echo "=== Running Navigation Tests ==="
echo ""

# Set environment variables as per documentation
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:${FRONTEND_PORT}

# Run tests with xvfb-run for headless execution
xvfb-run -a npx cypress run --headless --spec cypress/e2e/navigation.cy.ts

echo ""
echo "=== Tests Complete ==="
