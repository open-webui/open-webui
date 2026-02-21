#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

source .env.otto

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
POLL_INTERVAL=15   # seconds between polls
POLL_TIMEOUT=3600  # 60 min max wait
NO_WAIT=false
SCREENSHOT_DIR="cypress/screenshots/screenshots.cy.ts"

for arg in "$@"; do
	[[ "$arg" == "--no-wait" ]] && NO_WAIT=true
	[[ "$arg" == --dir=* ]]     && SCREENSHOT_DIR="${arg#--dir=}"
done

# Post header message
HEADER_RESP=$(curl -s -X POST \
	"${OTTO_BASE_URL}/api/v1/channels/${OTTO_DEV_CHANNEL_ID}/messages/post" \
	-H "Authorization: Bearer ${OTTO_API_TOKEN}" \
	-H "Content-Type: application/json" \
	-d "{\"content\": \"📸 Screenshots — branch \`${BRANCH}\` @ ${TIMESTAMP}\"}")

# Anchor: nanosecond timestamp from header message
POSTED_AT=$(echo "$HEADER_RESP" | jq -r '.created_at // empty')
if [ -z "$POSTED_AT" ]; then
	POSTED_AT=$(( $(date +%s) * 1000000000 ))
fi

# Upload + post each screenshot (recursive search in dir)
FOUND=0
while IFS= read -r -d '' SHOT; do
	[ -f "$SHOT" ] || continue
	NAME=$(basename "$SHOT" .png)
	FOUND=$(( FOUND + 1 ))

	RESP=$(curl -s -X POST "${OTTO_BASE_URL}/api/v1/files/" \
		-H "Authorization: Bearer ${OTTO_API_TOKEN}" \
		-F "file=@${SHOT};type=image/png")

	FILE_ID=$(echo "$RESP" | jq -r '.id // empty')
	if [ -z "$FILE_ID" ]; then
		>&2 echo "Upload failed for $NAME: $RESP"
		continue
	fi

	curl -s -X POST \
		"${OTTO_BASE_URL}/api/v1/channels/${OTTO_DEV_CHANNEL_ID}/messages/post" \
		-H "Authorization: Bearer ${OTTO_API_TOKEN}" \
		-H "Content-Type: application/json" \
		-d "{\"content\":\"\`${NAME}\`\",\"data\":{\"files\":[{\"id\":\"${FILE_ID}\",\"type\":\"image\",\"url\":\"/api/v1/files/${FILE_ID}/content\"}]}}" \
		> /dev/null

	>&2 echo "Posted: $NAME"
done < <(find "$SCREENSHOT_DIR" -name "*.png" -print0 2>/dev/null)

if [ "$FOUND" -eq 0 ]; then
	>&2 echo "No screenshots found under $SCREENSHOT_DIR"
	exit 1
fi

# Update anchor to now (after all screenshots posted)
POSTED_AT=$(( $(date +%s) * 1000000000 ))

if $NO_WAIT; then
	>&2 echo "Posted $FOUND screenshot(s). Not waiting for feedback (--no-wait)."
	exit 0
fi

# Poll for user reply (role = "user", created_at > POSTED_AT)
>&2 echo "Waiting for your feedback in #otto-dev channel..."
ELAPSED=0
while [ "$ELAPSED" -lt "$POLL_TIMEOUT" ]; do
	MSGS=$(curl -s \
		"${OTTO_BASE_URL}/api/v1/channels/${OTTO_DEV_CHANNEL_ID}/messages?skip=0&limit=10" \
		-H "Authorization: Bearer ${OTTO_API_TOKEN}")

	FEEDBACK=$(echo "$MSGS" | jq -r --argjson after "$POSTED_AT" '
		[.[] | select(.created_at > $after and .user.role == "user")]
		| sort_by(.created_at)
		| first
		| .content // empty
	' 2>/dev/null || true)

	if [ -n "$FEEDBACK" ]; then
		echo "$FEEDBACK"
		exit 0
	fi

	sleep "$POLL_INTERVAL"
	ELAPSED=$(( ELAPSED + POLL_INTERVAL ))
done

>&2 echo "Timeout: no feedback received within ${POLL_TIMEOUT}s"
exit 1
