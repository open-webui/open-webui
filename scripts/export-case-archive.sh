#!/usr/bin/env bash
# export-case-archive.sh — Export Jawafdehi case archive from API
#
# Usage:
#   ./scripts/export-case-archive.sh [OPTIONS]
#
# Options:
#   --output-dir DIR      Output directory (default: ./case-archive)
#   --format FORMAT       Output format: jsonl (default) or json
#   --case-type TYPE      Filter by case type (CORRUPTION, PROMISES)
#   --search TERM         Full-text search filter
#   --include-sources     Fetch detailed source info per case (slower)
#   --include-entities    Fetch entity details per case
#   --max-pages N         Maximum pages to fetch (default: unlimited)
#   --base-url URL        API base URL (default: https://api.jawafdehi.org/api)
#   --api-key KEY         API key for token auth (optional, used for draft access)
#   --resume              Resume from last checkpoint
#   --help                Show this message
#
# Requirements: curl, jq
#
# Output structure:
#   <output-dir>/
#   ├── cases/                    # Individual case JSON files
#   │   └── <slug>.json
#   ├── cases.jsonl               # All cases as JSONL
#   ├── cases.json                # All cases as JSON array
#   ├── index.json                # Export manifest
#   └── checkpoint                # Resume checkpoint

set -euo pipefail

# ── defaults ──────────────────────────────────────────────
OUTPUT_DIR="./case-archive"
FORMAT="jsonl"
CASE_TYPE=""
SEARCH=""
INCLUDE_SOURCES=false
INCLUDE_ENTITIES=false
MAX_PAGES=0
BASE_URL="${JAWAFDEHI_API_URL:-https://api.jawafdehi.org/api}"
API_KEY="${JAWAFDEHI_API_KEY:-}"
RESUME=false
PAGE_SIZE=20

# ── parse args ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)      OUTPUT_DIR="$2"; shift 2 ;;
    --format)          FORMAT="$2"; shift 2 ;;
    --case-type)       CASE_TYPE="$2"; shift 2 ;;
    --search)          SEARCH="$2"; shift 2 ;;
    --include-sources) INCLUDE_SOURCES=true; shift ;;
    --include-entities) INCLUDE_ENTITIES=true; shift ;;
    --max-pages)       MAX_PAGES="$2"; shift 2 ;;
    --base-url)        BASE_URL="$2"; shift 2 ;;
    --api-key)         API_KEY="$2"; shift 2 ;;
    --resume)          RESUME=true; shift ;;
    --help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage."
      exit 1
      ;;
  esac
done

# ── auth header ───────────────────────────────────────────
AUTH_HEADER=()
if [[ -n "$API_KEY" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $API_KEY")
fi

# ── setup directories ─────────────────────────────────────
CASES_DIR="$OUTPUT_DIR/cases"
CHECKPOINT_FILE="$OUTPUT_DIR/checkpoint"
mkdir -p "$CASES_DIR"

# ── resume ────────────────────────────────────────────────
START_PAGE=1
if $RESUME && [[ -f "$CHECKPOINT_FILE" ]]; then
  START_PAGE=$(cat "$CHECKPOINT_FILE")
  echo "[export] Resuming from page $START_PAGE"
fi

# ── build query params ────────────────────────────────────
build_url() {
  local page=$1
  local url="$BASE_URL/cases/?page=$page"
  [[ -n "$CASE_TYPE" ]] && url="$url&case_type=$CASE_TYPE"
  [[ -n "$SEARCH" ]] && url="$url&search=${SEARCH// /%20}"
  echo "$url"
}

# ── fetch case detail ─────────────────────────────────────
fetch_case_detail() {
  local slug=$1
  local detail_url="$BASE_URL/cases/$slug/"
  if $INCLUDE_SOURCES; then
    detail_url="$detail_url?fetch_sources=true"
  fi
  curl -sS --connect-timeout 10 --max-time 30 "${AUTH_HEADER[@]}" "$detail_url"
}

# ── main export loop ──────────────────────────────────────
echo "[export] Starting case archive export"
echo "[export] Base URL: $BASE_URL"
echo "[export] Output: $OUTPUT_DIR"
echo "[export] Format: $FORMAT"

TOTAL_CASES=0
PAGE=$START_PAGE

# Clear output files on fresh start
if ! $RESUME || [[ $START_PAGE -eq 1 ]]; then
  : > "$OUTPUT_DIR/cases.jsonl"
  echo "[]" > "$OUTPUT_DIR/cases.json"
fi

while :; do
  # Check max pages limit
  if [[ $MAX_PAGES -gt 0 && $PAGE -gt $MAX_PAGES ]]; then
    echo "[export] Reached max pages limit ($MAX_PAGES)"
    break
  fi

  URL=$(build_url "$PAGE")
  echo "[export] Fetching page $PAGE: $URL"

  RESPONSE=$(curl -sS --connect-timeout 10 --max-time 30 "${AUTH_HEADER[@]}" "$URL")

  # Check for API errors
  ERROR_MSG=$(echo "$RESPONSE" | jq -r '.detail // .error // empty' 2>/dev/null)
  if [[ -n "$ERROR_MSG" ]]; then
    echo "[export] API error on page $PAGE: $ERROR_MSG"
    break
  fi

  # Extract results
  RESULTS=$(echo "$RESPONSE" | jq -c '.results' 2>/dev/null)
  COUNT=$(echo "$RESULTS" | jq 'length' 2>/dev/null)

  if [[ -z "$COUNT" || "$COUNT" -eq 0 ]]; then
    echo "[export] No more results — export complete"
    break
  fi

  # Process each case on this page
  PAGE_CASES=0
  for i in $(seq 0 $((COUNT - 1))); do
    CASE_JSON=$(echo "$RESULTS" | jq -c ".[$i]")
    SLUG=$(echo "$CASE_JSON" | jq -r '.slug // empty')

    # Save individual case file
    echo "$CASE_JSON" | jq '.' > "$CASES_DIR/${SLUG}.json"

    # Fetch detail if requested
    if $INCLUDE_SOURCES || $INCLUDE_ENTITIES; then
      DETAIL=$(fetch_case_detail "$SLUG")
      if [[ -n "$DETAIL" ]]; then
        echo "$DETAIL" | jq '.' > "$CASES_DIR/${SLUG}.json"
        CASE_JSON="$DETAIL"
      fi
    fi

    # Append to JSONL
    echo "$CASE_JSON" >> "$OUTPUT_DIR/cases.jsonl"

    PAGE_CASES=$((PAGE_CASES + 1))
    TOTAL_CASES=$((TOTAL_CASES + 1))
  done

  echo "[export] Page $PAGE: $PAGE_CASES cases (total: $TOTAL_CASES)"

  # Save checkpoint
  echo "$((PAGE + 1))" > "$CHECKPOINT_FILE"

  # Check if we got a full page (if not, we're at the end)
  if [[ "$COUNT" -lt $PAGE_SIZE ]]; then
    echo "[export] Partial page — export complete"
    break
  fi

  PAGE=$((PAGE + 1))
  sleep 0.3  # Rate limiting
done

# ── build JSON array ──────────────────────────────────────
if [[ $TOTAL_CASES -gt 0 ]]; then
  echo "[export] Building JSON array..."
  jq -s '.' "$OUTPUT_DIR/cases.jsonl" > "$OUTPUT_DIR/cases.json"
fi

# ── create manifest ───────────────────────────────────────
EXPORT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EXPORT_DATE_PT=$(TZ=America/Los_Angeles date +"%Y-%m-%dT%H:%M:%S%z")
MANIFEST=$(cat <<JSON
{
  "export_date_utc": "$EXPORT_DATE",
  "export_date_pt": "$EXPORT_DATE_PT",
  "total_cases": $TOTAL_CASES,
  "base_url": "$BASE_URL",
  "case_type": "${CASE_TYPE:-all}",
  "search": "${SEARCH:-none}",
  "include_sources": $INCLUDE_SOURCES,
  "include_entities": $INCLUDE_ENTITIES,
  "format": "$FORMAT",
  "files": {
    "cases_jsonl": "cases.jsonl",
    "cases_json": "cases.json",
    "cases_dir": "cases/",
    "manifest": "index.json"
  }
}
JSON
)
echo "$MANIFEST" | jq '.' > "$OUTPUT_DIR/index.json"

# ── summary ───────────────────────────────────────────────
echo ""
echo "──────────── Export Summary ────────────"
echo "  Total cases:       $TOTAL_CASES"
echo "  Output directory:  $OUTPUT_DIR"
echo "  Manifest:          $OUTPUT_DIR/index.json"
echo "  Cases JSONL:       $OUTPUT_DIR/cases.jsonl"
echo "  Cases JSON:        $OUTPUT_DIR/cases.json"
echo "  Individual cases:  $CASES_DIR/"
echo "  Export date (PT):  $EXPORT_DATE_PT"
echo "────────────────────────────────────────"

# Clean up checkpoint on successful completion
if [[ $TOTAL_CASES -gt 0 ]]; then
  rm -f "$CHECKPOINT_FILE"
  echo "[export] Done — checkpoint cleared"
fi
