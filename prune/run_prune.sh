#!/bin/bash
##############################################################################
# Open WebUI Prune Script Wrapper
#
# This wrapper script sets up the environment and runs the standalone prune
# script. It handles:
# - Loading environment variables from .env file
# - Activating Python virtual environment (if present)
# - Setting up Python path
# - Passing through all command-line arguments
#
# Usage:
#   ./run_prune.sh --help
#   ./run_prune.sh --dry-run
#   ./run_prune.sh --days 60 --execute
##############################################################################

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "  Open WebUI Prune Script Wrapper"
echo "=================================================="
echo "Script directory: $SCRIPT_DIR"
echo "Repository root: $REPO_ROOT"
echo ""

# Change to repository root
cd "$REPO_ROOT"

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    set -a  # Export all variables
    source .env
    set +a
    echo "✓ Environment loaded"
else
    echo "ℹ No .env file found, using existing environment variables"
fi

# Activate virtual environment if it exists
if [ -d .venv ]; then
    echo "Activating Python virtual environment..."
    source .venv/bin/activate
    echo "✓ Virtual environment activated: $(which python)"
elif [ -d venv ]; then
    echo "Activating Python virtual environment..."
    source venv/bin/activate
    echo "✓ Virtual environment activated: $(which python)"
else
    echo "ℹ No virtual environment found, using system Python: $(which python)"
fi

# Verify we can import Open WebUI modules
echo ""
echo "Checking Python environment..."
python -c "import sys; print(f'Python version: {sys.version}')"
python -c "from backend.open_webui.models.users import Users; print('✓ Can import Open WebUI modules')" || {
    echo "✗ ERROR: Cannot import Open WebUI modules"
    echo ""
    echo "Make sure you have:"
    echo "  1. Installed Open WebUI dependencies (pip install -r requirements.txt)"
    echo "  2. Running from the Open WebUI directory"
    exit 1
}

# Check database connection
echo ""
echo "Checking database connection..."
if [ -z "$DATABASE_URL" ]; then
    echo "⚠ WARNING: DATABASE_URL not set, using default SQLite database"
else
    echo "✓ DATABASE_URL: $DATABASE_URL"
fi

# Run the prune script with all passed arguments
echo ""
echo "=================================================="
echo "  Running Prune Script"
echo "=================================================="
echo ""

python "$SCRIPT_DIR/standalone_prune.py" "$@"
EXIT_CODE=$?

echo ""
echo "=================================================="
echo "  Script completed with exit code: $EXIT_CODE"
echo "=================================================="

exit $EXIT_CODE
