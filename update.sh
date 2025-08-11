#!/bin/bash

set -e  # Exit on error

LOGFILE="/var/log/openwebui/update.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

echo "${TIMESTAMP}  Starting update..." >> "$LOGFILE"

cd /opt/open-webui || exit 1

# Force reset to match remote main exactly
echo "🔄 Git: reset & pull main" | tee -a "$LOGFILE"
git reset --hard >> "$LOGFILE" 2>&1
git clean -fd >> "$LOGFILE" 2>&1
git fetch origin >> "$LOGFILE" 2>&1
git checkout main >> "$LOGFILE" 2>&1

# Pull and check if any update happened
if git pull --rebase origin main | tee -a "$LOGFILE" | grep -q 'Already up to date'; then
    echo "${TIMESTAMP}  No changes found. Skipping rebuild." >> "$LOGFILE"
    exit 0
else
    echo "${TIMESTAMP}  Changes pulled. Proceeding with update..." >> "$LOGFILE"
fi

# Update backend
cd backend || exit 1
source venv/bin/activate
pip install -r requirements.txt >> "$LOGFILE" 2>&1

# Rebuild frontend
cd /opt/open-webui
npm install --force >> "$LOGFILE" 2>&1

NODE_OPTIONS="--max-old-space-size=4096" npm run build >> "$LOGFILE" 2>&1

# Restart the service
systemctl restart openwebui
echo "${TIMESTAMP}  Update completed and service restarted." >> "$LOGFILE"
