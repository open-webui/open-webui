#!/bin/bash
# 
# mAI Daily Batch Processing Cron Script
# Runs daily at 00:00 to process usage data and update exchange rates
#
# Add to crontab with:
# 0 0 * * * /path/to/mAI/scripts/daily_batch_cron.sh
#

# Configuration
MAI_PROJECT_DIR="/app"
LOG_DIR="/app/logs"
PYTHON_ENV="/app/backend/.venv"
SCRIPT_NAME="daily_batch_processor.py"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log file with date
LOG_FILE="$LOG_DIR/daily_batch_$(date +%Y%m%d).log"

# Start logging
echo "========================================" >> "$LOG_FILE"
echo "mAI Daily Batch Processing" >> "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Change to backend directory
cd "$MAI_PROJECT_DIR/backend" || {
    echo "ERROR: Cannot change to backend directory" >> "$LOG_FILE"
    exit 1
}

# Activate virtual environment if it exists
if [ -d "$PYTHON_ENV" ]; then
    source "$PYTHON_ENV/bin/activate" >> "$LOG_FILE" 2>&1
    echo "Virtual environment activated" >> "$LOG_FILE"
fi

# Run the daily batch processor
echo "Running daily batch processor..." >> "$LOG_FILE"
python -m open_webui.utils.daily_batch_processor >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# Log completion
echo "========================================" >> "$LOG_FILE"
echo "Completed at: $(date)" >> "$LOG_FILE"
echo "Exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Clean up old log files (keep last 30 days)
find "$LOG_DIR" -name "daily_batch_*.log" -mtime +30 -delete 2>/dev/null

# Exit with the same code as the Python script
exit $EXIT_CODE