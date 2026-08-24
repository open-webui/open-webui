#!/usr/bin/env bash
# Backs up the open-webui named Docker volume -- chat history, the admin
# account, the synced claude_cli Pipe function, the claude CLI's own OAuth
# login (CLAUDE_CONFIG_DIR), and sessions.json all live in this one volume.
# Nothing else in this deployment backs it up automatically; losing the
# volume (an accidental `docker compose down -v`, a Docker Desktop reset,
# host disk failure) means starting over from scratch, including a fresh
# `claude auth login` browser flow -- see decisions.md's "long-term
# operation" notes for why this matters more here than it might elsewhere.
#
# Runs while the container stays up (doesn't stop it first) -- a few
# seconds of write-in-progress inconsistency in a JSON blob is a much
# smaller risk in practice than adding downtime to every backup run. If
# perfect point-in-time consistency ever matters more than uptime for a
# given backup, stop the container first.
#
# Usage:
#   ./backup_data_volume.sh [output-dir]      # default: ./backups
#   OPEN_WEBUI_VOLUME=my-volume ./backup_data_volume.sh   # skip auto-discovery
#
# Restore (do this against a *fresh, empty* volume, not a live one -- it
# extracts on top of whatever's already there; substitute the real volume
# name this script printed when it made the backup):
#   docker run --rm -v <volume-name>:/data -v "$(pwd)/backups":/backup alpine \
#     tar xzf /backup/open-webui-data-<timestamp>.tar.gz -C /data

set -euo pipefail

CONTAINER="${OPEN_WEBUI_CONTAINER:-open-webui}"
OUT_DIR="${1:-./backups}"

# Compose prefixes the volume name declared in docker-compose.yaml
# ("open-webui") with the project name, which itself defaults to the
# checkout's directory name -- so the real volume name varies by machine
# (confirmed live: "open-webui_open-webui" here, would differ on a
# checkout in a differently-named directory). Discovered from the running
# container's actual mount instead of guessed, so this doesn't need
# updating per-machine.
if [ -z "${OPEN_WEBUI_VOLUME:-}" ]; then
  VOLUME="$(docker inspect "$CONTAINER" --format '{{range .Mounts}}{{if eq .Destination "/app/backend/data"}}{{.Name}}{{end}}{{end}}' 2>/dev/null || true)"
  if [ -z "$VOLUME" ]; then
    echo "Error: couldn't auto-discover the data volume from container '$CONTAINER' (is it running?)." >&2
    echo "Set OPEN_WEBUI_VOLUME explicitly, or OPEN_WEBUI_CONTAINER if it's not named 'open-webui'." >&2
    exit 1
  fi
else
  VOLUME="$OPEN_WEBUI_VOLUME"
fi

if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  echo "Error: volume '$VOLUME' doesn't exist." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="open-webui-data-$TIMESTAMP.tar.gz"
ABS_OUT_DIR="$(cd "$OUT_DIR" && pwd)"

docker run --rm -v "$VOLUME":/data -v "$ABS_OUT_DIR":/backup alpine \
  tar czf "/backup/$OUT_FILE" -C /data .

echo "Backed up volume '$VOLUME' to $ABS_OUT_DIR/$OUT_FILE"
