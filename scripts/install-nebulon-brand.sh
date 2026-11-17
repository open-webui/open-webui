#!/usr/bin/env bash
# Install Nebulon AI logo pack v1.1 into static paths (run from repo root).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${NEBULON_BRAND_SRC:-$ROOT/static/brand/nebulon-ai-logo-v1.1}"
CANON="$ROOT/static/brand/nebulon-ai-logo-v1.1"

if [[ ! -d "$SRC/icons" ]]; then
	echo "Logo pack not found at $SRC" >&2
	exit 1
fi

mkdir -p "$CANON"
if [[ "$SRC" != "$CANON" ]]; then
	cp -a "$SRC"/. "$CANON/"
fi

for SS in "$ROOT/static/static" "$ROOT/backend/open_webui/static"; do
	mkdir -p "$SS/brand"
	cp -a "$CANON" "$SS/brand/"
	BR="$CANON"
	cp "$BR/icons/icon-light-transparent-32.png" "$SS/favicon.png"
	cp "$BR/icons/icon-dark-transparent-32.png" "$SS/favicon-dark.png"
	cp "$BR/icons/icon-light-transparent-128.png" "$SS/favicon-96x96.png"
	cp "$BR/icons/icon-light.svg" "$SS/favicon.svg"
	cp "$BR/icons/icon-dark.svg" "$SS/favicon-dark.svg"
	cp "$BR/icons/favicon-light.ico" "$SS/favicon.ico"
	cp "$BR/icons/favicon-dark.ico" "$SS/favicon-dark.ico"
	cp "$BR/icons/icon-light-transparent-180.png" "$SS/apple-touch-icon.png"
	cp "$BR/icons/icon-light-512.png" "$SS/web-app-manifest-512x512.png"
	cp "$BR/icons/icon-light-256.png" "$SS/web-app-manifest-192x192.png"
	cp "$BR/lockups/nebulon-ai-horizontal-light.png" "$SS/splash.png"
	cp "$BR/lockups/nebulon-ai-horizontal-dark.png" "$SS/splash-dark.png"
	cp "$BR/icons/icon-light-512.png" "$SS/logo.png"
done

cp "$ROOT/static/static/favicon.png" "$ROOT/static/favicon.png"
echo "Nebulon brand assets installed."