#!/usr/bin/env bash
#
# generate-sbom.sh — Generate a clean CycloneDX SBOM using Syft
#
# Produces a single SBOM from resolved manifests only — no directory scanning,
# no venv pollution, no local state. Works identically locally and in CI.
#
# How it works:
#   1. Python: uv pip compile resolves all transitive deps from requirements.txt
#   2. JavaScript: package-lock.json already contains the full resolved tree
#   3. Syft scans these resolved files, not the filesystem
#
# Usage:
#   ./scripts/generate-sbom.sh              # generate sbom.cdx.json from manifests
#   ./scripts/generate-sbom.sh docker       # generate from Docker image (best license coverage)
#   ./scripts/generate-sbom.sh docker IMG   # generate from a specific image
#   ./scripts/generate-sbom.sh validate     # validate existing SBOM
#
# Requirements:
#   - syft (brew install syft)
#   - uv  (brew install uv)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

info()  { echo -e "${BOLD}${GREEN}▸${RESET} $1"; }
warn()  { echo -e "${BOLD}${RED}▸${RESET} $1"; }
dim()   { echo -e "${DIM}  $1${RESET}"; }

OUTPUT="$ROOT_DIR/sbom.cdx.json"

check_deps() {
    local missing=()
    command -v syft &>/dev/null || missing+=("syft")
    command -v uv &>/dev/null   || missing+=("uv")
    if [[ ${#missing[@]} -gt 0 ]]; then
        warn "Missing: ${missing[*]}. Install with: brew install ${missing[*]}"
        exit 1
    fi
    dim "Using $(syft --version), $(uv --version)"
}

generate() {
    info "Generating SBOM from resolved manifests..."
    check_deps

    local VERSION
    VERSION="$(python3 -c "import json; print(json.load(open('$ROOT_DIR/package.json'))['version'])")"

    local WORK_DIR
    WORK_DIR="$(mktemp -d)"
    trap 'rm -rf "$WORK_DIR"' RETURN

    # --- Python: resolve all transitive deps without installing ---
    dim "Resolving Python transitive deps (uv pip compile)..."
    uv pip compile "$ROOT_DIR/backend/requirements.txt" \
        --python-version 3.11 \
        --quiet \
        > "$WORK_DIR/requirements-resolved.txt" 2>/dev/null

    # --- JavaScript: package-lock.json is already fully resolved ---
    if [[ -f "$ROOT_DIR/package-lock.json" ]]; then
        cp "$ROOT_DIR/package-lock.json" "$WORK_DIR/package-lock.json"
        # Syft needs package.json alongside the lockfile
        cp "$ROOT_DIR/package.json" "$WORK_DIR/package.json"
    else
        warn "package-lock.json not found — JS deps will be skipped"
    fi

    # --- Scan only the resolved files ---
    dim "Scanning resolved manifests with Syft..."
    syft scan "dir:$WORK_DIR" \
        --output "cyclonedx-json=$OUTPUT" \
        --source-name open-webui \
        --source-version "$VERSION" \
        --quiet

    # Print summary
    python3 -c "
import json
with open('$OUTPUT') as f:
    data = json.load(f)
comps = data.get('components', [])
py = [c for c in comps if 'pypi' in c.get('purl', '')]
js = [c for c in comps if 'npm' in c.get('purl', '')]
with_lic = sum(1 for c in comps if c.get('licenses'))
print(f'  {len(comps)} total ({len(py)} Python, {len(js)} JavaScript)')
print(f'  {with_lic}/{len(comps)} with license info')
print(f'  Serial: {data.get(\"serialNumber\", \"none\")}')
print(f'  Timestamp: {data.get(\"metadata\", {}).get(\"timestamp\", \"none\")}')
"

    info "SBOM written → sbom.cdx.json"
}

generate_docker() {
    local IMAGE="${1:-ghcr.io/open-webui/open-webui:latest}"
    info "Generating SBOM from Docker image: $IMAGE"

    if ! command -v syft &>/dev/null; then
        warn "syft is not installed. Install with: brew install syft"
        exit 1
    fi

    dim "Pulling and scanning image..."
    syft scan "docker:$IMAGE" \
        --output "cyclonedx-json=$OUTPUT" \
        --quiet

    python3 -c "
import json
with open('$OUTPUT') as f:
    data = json.load(f)
comps = data.get('components', [])
with_lic = sum(1 for c in comps if c.get('licenses'))
print(f'  {len(comps)} total components')
print(f'  {with_lic}/{len(comps)} with license info ({round(with_lic/max(len(comps),1)*100)}%)')
"

    info "SBOM written → sbom.cdx.json"
}

validate() {
    info "Validating SBOM..."

    python3 -c "
import json, sys

try:
    with open('$OUTPUT') as f:
        data = json.load(f)
except FileNotFoundError:
    print('  ✗ sbom.cdx.json not found — run ./scripts/generate-sbom.sh first')
    sys.exit(1)

issues = []
if data.get('bomFormat') != 'CycloneDX':
    issues.append('Not CycloneDX format')
if not data.get('specVersion'):
    issues.append('Missing specVersion')
if not data.get('serialNumber'):
    issues.append('Missing serial number')

components = data.get('components', [])

# Check for phantom local packages
phantoms = []
for c in components:
    for ref in c.get('externalReferences', []):
        url = ref.get('url', '')
        if 'file://' in url and '/Users/' in url:
            phantoms.append(c['name'])
if phantoms:
    issues.append(f'Phantom local packages: {phantoms}')

with_lic = sum(1 for c in components if c.get('licenses'))
lic_pct = round(with_lic / max(len(components), 1) * 100)

if issues:
    print(f'  ✗ {len(components)} components, {lic_pct}% licensed')
    for i in issues:
        print(f'    ✗ {i}')
    sys.exit(1)
else:
    print(f'  ✓ {len(components)} components, {lic_pct}% licensed — PASS')
"
}

# --- Main ---
cd "$ROOT_DIR"
TARGET="${1:-generate}"

case "$TARGET" in
    generate) generate ;;
    docker)   generate_docker "${2:-}" ;;
    validate) validate ;;
    *)
        warn "Unknown target: $TARGET"
        echo "Usage: $0 [generate|docker [IMAGE]|validate]"
        exit 1
        ;;
esac

echo ""
info "Done."
