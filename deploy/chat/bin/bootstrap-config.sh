#!/usr/bin/env bash
# bootstrap-config.sh — Apply Jawafdehi config to OpenWebUI via REST API
#
# Reads configs/ directory and pushes everything to a running OpenWebUI
# instance. Idempotent: checks if each item already exists before creating.
#
# Usage:
#   export OWUI_BASE_URL="https://chat.jawafdehi.org"
#   export OWUI_API_KEY="sk-..."
#   ./bootstrap-config.sh
#
# Optional:
#   OWUI_DRY_RUN=1    — print actions without making changes
#   OWUI_VERBOSE=1    — show raw API responses

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGS_DIR="$(dirname "$SCRIPT_DIR")/configs"

: "${OWUI_BASE_URL:?OWUI_BASE_URL must be set (e.g. https://chat.jawafdehi.org)}"
: "${OWUI_API_KEY:?OWUI_API_KEY must be set}"
OWUI_API="${OWUI_BASE_URL}/api/v1"

DRY_RUN="${OWUI_DRY_RUN:-0}"
VERBOSE="${OWUI_VERBOSE:-0}"
TMPDIR="${TMPDIR:-/tmp}"

log()  { echo "[bootstrap] $(date -Iseconds) $*"; }
info() { echo "  -> $*"; }
warn() { echo "  !! $*" >&2; }
err()  { echo "  [ERROR] $*" >&2; exit 1; }

# --- API helpers ---

_api_call() {
    local method="$1" path="$2" data="${3:-}"
    local url="${OWUI_API}${path}"
    local curl_args=(-s -w "\n%{http_code}" -H "Authorization: Bearer ${OWUI_API_KEY}")
    curl_args+=(-H "Content-Type: application/json")

    if [ "$method" = "GET" ]; then
        curl_args+=(-X GET)
    elif [ "$method" = "POST" ]; then
        curl_args+=(-X POST -d "$data")
    elif [ "$method" = "PUT" ]; then
        curl_args+=(-X PUT -d "$data")
    elif [ "$method" = "DELETE" ]; then
        curl_args+=(-X DELETE)
    fi

    [ "$VERBOSE" = "1" ] && log "API $method $path"

    local response http_code
    response=$(curl "${curl_args[@]}" "$url" 2>&1) || err "curl failed: $response"
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')

    [ "$VERBOSE" = "1" ] && echo "    HTTP $http_code: $(echo "$body" | head -c 200)"

    if [ "$http_code" -ge 400 ]; then
        warn "$method $path → HTTP $http_code"
        return 1
    fi

    echo "$body"
    return 0
}

# --- Model presets ---

apply_models() {
    log "Applying model presets..."

    local existing
    existing=$(_api_call GET "/models/" "" 2>/dev/null || echo "[]")
    local model_dir="${CONFIGS_DIR}/models"

    [ ! -d "$model_dir" ] && warn "No configs/models/ directory found" && return

    for model_file in "$model_dir"/*.json; do
        [ ! -f "$model_file" ] && continue
        local model_data model_id
        model_data=$(cat "$model_file")
        model_id=$(echo "$model_data" | jq -r '.id // empty')

        [ -z "$model_id" ] && warn "Skipping $model_file: no 'id' field" && continue

        # Check if model already exists
        if echo "$existing" | jq -e --arg id "$model_id" '.items // [] | any(.id == $id)' > /dev/null 2>&1; then
            info "Model '$model_id' already exists — skipping"
            continue
        fi

        if [ "$DRY_RUN" = "1" ]; then
            log "[DRY RUN] Would create model: $model_id"
            continue
        fi

        info "Creating model: $model_id"
        _api_call POST "/models/create" "$model_data" || warn "Failed to create model $model_id"
    done

    log "Model presets done."
}

# --- Knowledge Base ---

apply_knowledge() {
    log "Applying Knowledge Base collections..."

    local kb_dir="${CONFIGS_DIR}/knowledge"
    local collections_file="${kb_dir}/collections.json"

    [ ! -f "$collections_file" ] && warn "No configs/knowledge/collections.json found" && return

    local collections
    collections=$(jq -c '.collections[]' "$collections_file")

    # Get existing KB collections
    local existing
    existing=$(_api_call GET "/knowledge/" "" 2>/dev/null || echo '[]')

    while IFS= read -r col; do
        local col_id col_name col_desc
        col_id=$(echo "$col" | jq -r '.id')
        col_name=$(echo "$col" | jq -r '.name')
        col_desc=$(echo "$col" | jq -r '.description')

        local kb_id
        kb_id=$(echo "$existing" | jq -r --arg name "$col_name" '.[] | select(.name == $name) | .id // empty' 2>/dev/null || echo "")

        if [ -z "$kb_id" ]; then
            if [ "$DRY_RUN" = "1" ]; then
                log "[DRY RUN] Would create KB collection: $col_name"
                kb_id="dry-run-id"
            else
                info "Creating KB collection: $col_name"
                local response
                response=$(_api_call POST "/knowledge/create" \
                    "$(jq -n --arg name "$col_name" --arg desc "$col_desc" '{name: $name, description: $desc}')") || true
                kb_id=$(echo "$response" | jq -r '.id // empty')
                [ -z "$kb_id" ] && warn "Failed to get ID for KB collection: $col_name" && continue
            fi
        else
            info "KB collection '$col_name' exists (id=$kb_id) — skipping create"
        fi

        # Upload documents
        local docs
        docs=$(echo "$col" | jq -r '.documents[]? // empty')
        while IFS= read -r doc; do
            [ -z "$doc" ] && continue
            local doc_path="${kb_dir}/${doc}"
            [ ! -f "$doc_path" ] && warn "Document not found: $doc_path" && continue

            if [ "$DRY_RUN" = "1" ]; then
                log "[DRY RUN] Would upload: $doc"
                continue
            fi

            info "Uploading document: $doc"
            # OpenWebUI KB file upload: POST /knowledge/{id}/file/add
            # Uses multipart form with the file
            #
            # NOTE: curl multipart upload for KB files — may need API tuning.
            # The File upload is multipart POST with the file field.
            if [ "$kb_id" != "dry-run-id" ]; then
                curl -s -X POST "${OWUI_API}/knowledge/${kb_id}/file/add" \
                    -H "Authorization: Bearer ${OWUI_API_KEY}" \
                    -F "file=@${doc_path}" \
                    -o /dev/null -w "%{http_code}" 2>/dev/null || warn "Upload failed for $doc"
            fi
        done <<< "$docs"

    done <<< "$collections"

    log "Knowledge Base done."
}

# --- Main ---

main() {
    log "=== Jawafdehi OpenWebUI Bootstrap ==="
    log "Target: ${OWUI_BASE_URL}"
    [ "$DRY_RUN" = "1" ] && log "DRY RUN — no changes will be made"

    # Verify API connectivity (with retries — nginx may return 502 briefly)
    local health
    for attempt in $(seq 1 10); do
        health=$(curl -s -o /dev/null -w "%{http_code}" "${OWUI_BASE_URL}/api/v1/tools/" \
            -H "Authorization: Bearer ${OWUI_API_KEY}" 2>/dev/null || echo "000")
        [ "$health" = "502" ] && sleep 2 && continue
        break
    done

    if [ "$health" -ge 200 ] 2>/dev/null && [ "$health" -lt 500 ]; then
        info "API reachable (HTTP $health)"
    else
        err "API unreachable (HTTP $health). Check OWUI_BASE_URL and OWUI_API_KEY."
    fi

    apply_models
    apply_knowledge

    log "=== Bootstrap complete ==="
    log "Next: configure system prompts via Admin Settings → Models"
    log "      or use the OWUI Folder API to attach prompts to models."
}

main "$@"
