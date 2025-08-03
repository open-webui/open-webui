#!/bin/bash
#
# Test Runner Script - Permanent Solution for Import Errors
#
# This script ensures tests always run in the correct virtual environment,
# eliminating the 'No module named typer' error once and for all.
#
# Usage:
#   ./run_test.sh test_script.py
#   ./run_test.sh test_nbp_integration_final.py
#

# Check if script argument provided
if [ $# -eq 0 ]; then
    echo "❌ Error: No test script provided"
    echo "Usage: ./run_test.sh <test_script.py>"
    echo "Example: ./run_test.sh test_nbp_integration_final.py"
    exit 1
fi

TEST_SCRIPT=$1

# Check if test script exists
if [ ! -f "$TEST_SCRIPT" ]; then
    echo "❌ Error: Test script '$TEST_SCRIPT' not found"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment 'venv' not found"
    echo "Please create virtual environment first:"
    echo "python3 -m venv venv"
    echo "source venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

echo "🚀 Running test with virtual environment activated..."
echo "📁 Script: $TEST_SCRIPT"
echo "🐍 Virtual env: $(pwd)/venv"
echo ""

# Activate virtual environment and run the test
source venv/bin/activate && python3 "$TEST_SCRIPT"

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Test completed successfully!"
else
    echo ""
    echo "❌ Test failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE