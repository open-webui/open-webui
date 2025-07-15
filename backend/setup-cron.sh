#!/bin/bash

# Create the wrapper script
cat > /app/backend/run-cleanup-script.sh << 'EOL'
#!/bin/bash
# This script runs the clean-orphaned-files.py script with the proper environment variables

# Export all environment variables to the script
export DATABASE_URL="${DATABASE_URL}"
export ADMIN_TOKEN="${ADMIN_TOKEN:-your_admin_token}"
export TEAMS_WEBHOOK_URL="${TEAMS_WEBHOOK_URL:-your_ms_teams_incoming_webhook_url}"

# Check if the script exists (it should be in a mounted volume)
if [ -f /app/backend/data/scripts/clean-orphaned-files.py ]; then
    /usr/local/bin/python /app/backend/data/scripts/clean-orphaned-files.py --admin-token "${ADMIN_TOKEN}" --teams-webhook-url "${TEAMS_WEBHOOK_URL}" >> /var/log/clean-orphaned-files.log 2>&1
else
    echo "$(date): Warning - clean-orphaned-files.py not found in mounted volume" >> /var/log/clean-orphaned-files.log
fi
EOL

# Make the wrapper script executable
chmod +x /app/backend/run-cleanup-script.sh

# Create the cron job entry
CRONJOB="0 */6 * * * /app/backend/run-cleanup-script.sh"

# Setup the crontab
(crontab -l 2>/dev/null || echo "") | grep -v "run-cleanup-script.sh" | { cat; echo "$CRONJOB"; } | crontab -

echo "Cron job has been set up successfully."
