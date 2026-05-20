#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Interactive docker compose launcher for Open WebUI.
# Supports GPU auto-detection, configurable ports, data mounts, and Playwright.
# ---------------------------------------------------------------------------

readonly BOLD='\033[1m'
readonly GREEN='\033[1;32m'
readonly WHITE='\033[1;37m'
readonly RED='\033[0;31m'
readonly RESET='\033[0m'
readonly CHECK_MARK='\xE2\x9C\x93'

# ── GPU detection ─────────────────────────────────────────────────────────────

detect_gpu_driver() {
  if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
    echo "nvidia"
  elif lspci 2>/dev/null | grep -qi 'vga.*amd\|display.*amd'; then
    if lspci | grep -qiE 'Radeon (RX|R[579]|HD [78])'; then
      echo "amdgpu"
    else
      echo "radeon"
    fi
  elif lspci 2>/dev/null | grep -qi 'vga.*intel\|display.*intel'; then
    echo "i915"
  else
    echo >&2 "Error: No supported GPU detected."
    return 1
  fi
}

# ── Argument helpers ──────────────────────────────────────────────────────────

extract_bracket_value() {
  local input="$1" fallback="${2:-}"
  if [[ "$input" =~ \[.*=(.*)\] ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    echo "$fallback"
  fi
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --enable-gpu[count=N]   Enable GPU passthrough (N = number or "all")
  --enable-api[port=PORT] Expose the Ollama API on PORT (default: 11435)
  --webui[port=PORT]      Set the WebUI port (default: 3000)
  --data[folder=PATH]     Bind-mount a host path for Ollama data
  --playwright            Enable Playwright for web scraping
  --build                 Build images before starting
  --drop                  Tear down the compose project
  -q, --quiet             Skip the confirmation prompt
  -h, --help              Show this help message

Examples:
  $(basename "$0") --drop
  $(basename "$0") --enable-gpu[count=1]
  $(basename "$0") --enable-gpu[count=all] --webui[port=8080]
  $(basename "$0") --enable-gpu[count=1] --enable-api[port=12345] --data[folder=./data] --build
EOF
}

# ── Defaults ──────────────────────────────────────────────────────────────────

enable_gpu=false
enable_api=false
enable_playwright=false
build_image=false
headless=false
drop_project=false
gpu_count=1
api_port=11435
webui_port=3000
data_dir=""

# ── Parse arguments ───────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --enable-gpu*)  enable_gpu=true;       gpu_count=$(extract_bracket_value "$1" "1") ;;
    --enable-api*)  enable_api=true;       api_port=$(extract_bracket_value "$1" "11435") ;;
    --webui*)       webui_port=$(extract_bracket_value "$1" "3000") ;;
    --data*)        data_dir=$(extract_bracket_value "$1" "./ollama-data") ;;
    --playwright)   enable_playwright=true ;;
    --build)        build_image=true ;;
    --drop)         drop_project=true ;;
    -q|--quiet)     headless=true ;;
    -h|--help)      usage; exit 0 ;;
    *)              echo "Unknown option: $1"; usage; exit 1 ;;
  esac
  shift
done

# ── Drop mode ─────────────────────────────────────────────────────────────────

if [[ "$drop_project" == true ]]; then
  docker compose down --remove-orphans
  echo -e "${GREEN}${BOLD}Compose project stopped and cleaned up.${RESET}"
  exit 0
fi

# ── Build compose command ─────────────────────────────────────────────────────

compose_files=("-f" "docker-compose.yaml")

if [[ "$enable_gpu" == true ]]; then
  if ! [[ "$gpu_count" =~ ^([0-9]+|all)$ ]]; then
    echo >&2 "Error: Invalid GPU count '${gpu_count}'. Must be a number or 'all'."
    exit 1
  fi
  export OLLAMA_GPU_DRIVER
  OLLAMA_GPU_DRIVER=$(detect_gpu_driver)
  export OLLAMA_GPU_COUNT="$gpu_count"
  compose_files+=("-f" "docker-compose.gpu.yaml")
fi

if [[ "$enable_api" == true ]]; then
  export OLLAMA_WEBAPI_PORT="$api_port"
  compose_files+=("-f" "docker-compose.api.yaml")
fi

if [[ -n "$data_dir" ]]; then
  export OLLAMA_DATA_DIR="$data_dir"
  compose_files+=("-f" "docker-compose.data.yaml")
fi

if [[ "$enable_playwright" == true ]]; then
  compose_files+=("-f" "docker-compose.playwright.yaml")
fi

export OPEN_WEBUI_PORT="$webui_port"

up_args=("up" "-d" "--remove-orphans" "--force-recreate")
if [[ "$build_image" == true ]]; then
  up_args+=("--build")
fi

# ── Confirmation ──────────────────────────────────────────────────────────────

echo
echo -e "${WHITE}${BOLD}Current Setup:${RESET}"
echo -e "   ${GREEN}${BOLD}GPU Driver:${RESET}  ${OLLAMA_GPU_DRIVER:-Disabled}"
echo -e "   ${GREEN}${BOLD}GPU Count:${RESET}   ${OLLAMA_GPU_COUNT:-Disabled}"
echo -e "   ${GREEN}${BOLD}API Port:${RESET}    ${OLLAMA_WEBAPI_PORT:-Disabled}"
echo -e "   ${GREEN}${BOLD}Data Dir:${RESET}    ${data_dir:-Docker volume}"
echo -e "   ${GREEN}${BOLD}WebUI Port:${RESET}  ${webui_port}"
echo -e "   ${GREEN}${BOLD}Playwright:${RESET}  ${enable_playwright}"
echo

if [[ "$headless" != true ]]; then
  read -rp "$(echo -e "${WHITE}${BOLD}Proceed with this setup? [Y/n]: ${RESET}")" confirm
  if [[ "${confirm,,}" == "n" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

# ── Launch ────────────────────────────────────────────────────────────────────

if docker compose "${compose_files[@]}" "${up_args[@]}"; then
  echo
  echo -e "${GREEN}${BOLD}${CHECK_MARK} Compose project started successfully.${RESET}"
else
  echo
  echo -e "${RED}${BOLD}Failed to start compose project.${RESET}"
  exit 1
fi

echo
