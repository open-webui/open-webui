#!/bin/bash
set -e
pwd
ls -al
whoami
sudo docker login -u _json_key --password-stdin https://europe-west3-docker.pkg.dev < w-calderone-d9ee5a55bf37.json
sudo docker compose pull
sudo docker compose down
sudo docker compose up -d
echo "deploy finished"
