#!/bin/bash

echo "[Stopping all servers...]"

pkill -f "python -m app.server"
pkill -f "start.sh"
pkill -f "vite preview"

echo "[All servers stopped.]"
~