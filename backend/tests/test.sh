#!/bin/bash

# Set environment variable
export PYTHONPATH=$(pwd)/..

# Set log file
LOG_FILE="test_log.txt"

# Clear log file
> $LOG_FILE

# Redirect log output to log file
exec > >(tee -a $LOG_FILE) 2>&1

# Cleanup function
clean_up() {
    echo "Cleaning up..."
    find $PYTHONPATH -type d -name "__pycache__" -exec rm -r {} + \
        -o -type f -name "*.py[co]" -delete \
        -o -type d -name "*.egg-info" -exec rm -r {} +
    rm -rf build dist data
    pip cache purge
}

# Run tests function
run_tests() {
    echo "Starting tests..."
    local test_dir="."
    local test_files=$(find $test_dir -name "test_*.py")

    for test_file in $test_files; do
        echo "****************************************************"
        total_files=$(echo "$test_files" | wc -l | xargs)
        echo "Running test $test_file number $((++count)) out of $total_files"
        echo "****************************************************"
        # echo "$(date '+%Y-%m-%d %H:%M:%S') Running tests in $test_file with unittest"
        # python3 -m unittest $test_file
        echo "$(date '+%Y-%m-%d %H:%M:%S') Running tests in $test_file with pytest"
        pytest $test_file
    done
    echo "All tests completed."
}

# Execute cleanup and tests
clean_up
run_tests
