#!/usr/bin/env bash

echo "Warning: This will remove all containers and volumes, including persistent data."
echo -n "Do you want to continue? [Y/N] "
read -r ans

if [[ $ans == [Yy] ]]; then
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose down -v
    else
        docker compose down -v
    fi
else
    echo "Operation cancelled."
fi