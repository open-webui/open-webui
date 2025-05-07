#!/usr/bin/env bash 
set -euo pipefail 
 
# 
# backup_webui.sh 
# – Dumps the sqlite file from Docker container 
# – Compresses it with gzip 
# – Names it with a timestamp 
# – Keeps only the latest 10 backups 
# 
 
# ——— Configuration ——— 
CONTAINER="w-open-webui" 
SRC_PATH="/app/backend/data/webui.db" 
BACKUP_DIR="${BACKUP_DIR:-$(dirname "$0")/backups}" 
PREFIX="webui" 
MAX_BACKUPS=10 
 
# ——— Prepare backup dir ——— 
mkdir -p "$BACKUP_DIR" 
 
# ——— Copy and compress ——— 
TIMESTAMP=$(date +'%Y%m%d_%H%M%S') 
TMP_DB=$(mktemp --suffix=.db) 
sudo docker cp "${CONTAINER}:${SRC_PATH}" "$TMP_DB"
sudo gzip -c "$TMP_DB" > "${BACKUP_DIR}/${PREFIX}_${TIMESTAMP}.db.gz"
sudo rm -f "$TMP_DB"

# ——— Rotate ———
cd "$BACKUP_DIR"
# List files sorted by time, skip the newest $MAX_BACKUPS, delete the rest
sudo ls -1t ${PREFIX}_*.db.gz \
  | tail -n +"$((MAX_BACKUPS+1))" \
  | xargs -r rm --

exit 0