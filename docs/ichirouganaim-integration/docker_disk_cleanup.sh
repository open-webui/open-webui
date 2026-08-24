#!/usr/bin/env bash
# Prints Docker's current disk usage and prunes unused build cache --
# SETUP.md's Prerequisites section already documents why this specifically
# matters here: an out-of-disk-space condition once caused the claude CLI
# to silently produce zero output with no error at all (fixed by a version
# pin, but the underlying disk-pressure risk is still worth watching over
# months of repeated rebuilds).
#
# `docker builder prune -f` only removes unused build cache -- confirmed
# safe by SETUP.md's own Prerequisites section -- so this is safe to run
# unconditionally on a schedule (cron, etc), not just when disk actually
# looks tight.
#
# Usage: ./docker_disk_cleanup.sh

set -euo pipefail

echo "==> Docker disk usage before cleanup:"
docker system df

echo
echo "==> Pruning unused build cache (safe -- doesn't touch images, containers, or volumes)..."
docker builder prune -f

echo
echo "==> Docker disk usage after cleanup:"
docker system df
