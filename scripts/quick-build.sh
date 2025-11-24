#!/bin/bash
# quick-build.sh - 快速本地构建 (不推送)
# 使用方法: ./scripts/quick-build.sh

set -e

# 获取 Git 信息
BUILD_HASH=$(git rev-parse HEAD)
SHORT_HASH=$(git rev-parse --short HEAD)

echo "🏗️  开始快速构建..."
echo "📋 Commit: ${SHORT_HASH}"
echo ""

# 构建镜像
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH="${BUILD_HASH}" \
  --build-arg USE_SLIM=true \
  -t ghcr.io/ai-friend-coming/open-webui-next:slim \
  -t ghcr.io/ai-friend-coming/open-webui-next:dev \
  --load \
  .

echo ""
echo "✅ 构建完成!"
echo ""
echo "🚀 运行命令:"
echo "   docker run -d -p 8080:8080 ghcr.io/ai-friend-coming/open-webui-next:slim"
