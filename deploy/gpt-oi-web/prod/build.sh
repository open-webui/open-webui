#!/bin/bash
 
# parameter
SOURCE_CODE=$1
SERVICE_NAME=$2
VERSION=$3
ENV=$4
HARBOR=$5
 
echo "SOURCE_CODE: ${SOURCE_CODE}"
echo "SERVICE_NAME: ${SERVICE_NAME}"
echo "VERSION: ${VERSION}"
echo "ENV: ${ENV}"
echo "HARBOR: ${HARBOR}"
 
Date=$(date +%Y%m%d%H%M%S)
TAG=${HARBOR}/${ENV}/${SERVICE_NAME}:${VERSION}-${Date}
cd ${SOURCE_CODE}
sed -i "s#{{service-name}}#$SERVICE_NAME#g" ${SOURCE_CODE}/deploy/gpt-oi-web/${ENV}/entrypoint.sh
sed -i "s#image:.*#image: $TAG#" ${SOURCE_CODE}/deploy/gpt-oi-web/${ENV}/$SERVICE_NAME.yaml
echo "docker build --build-arg version=${VERSION} --build-arg env=${ENV} --build-arg harbor=${HARBOR} -t ${TAG} . -f deploy/gpt-oi-web/${ENV}/Dockerfile"
docker build --build-arg version=${VERSION} --build-arg env=${ENV} --build-arg harbor=${HARBOR} -t ${TAG} . -f deploy/gpt-oi-web/${ENV}/Dockerfile
echo "Image: ${TAG}"
docker push ${TAG}
