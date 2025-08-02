#!/bin/bash
set -a
if [ -f ../.env.dev ]; then
    source ../.env.dev
elif [ -f ../.env ]; then
    source ../.env
else
    echo "Warning: No environment file found (.env.dev or .env)"
fi
set +a
