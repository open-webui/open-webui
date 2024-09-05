#!/bin/bash

image_name="open-webui"
container_name="open-webui"
host_port=3000
container_port=8080
dockerhub_username="hongtaofht"
tag=1.0.0

docker build -t "$image_name" .

docker tag "$image_name:latest" "$dockerhub_username/$image_name:$tag"

# 推送 Docker 镜像到 Docker Hub
docker push "$dockerhub_username/$image_name:$tag"

#docker stop "$container_name" &>/dev/null || true
#docker rm "$container_name" &>/dev/null || true
#
#docker run -d -p "$host_port":"$container_port" \
#    --add-host=host.docker.internal:host-gateway \
#    -v "${image_name}:/app/backend/data" \
#    --name "$container_name" \
#    --restart always \
#    "$image_name"
#
#docker image prune -f
