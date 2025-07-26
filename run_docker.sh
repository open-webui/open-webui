#!/bin/bash

# 设置镜像名称
IMAGE_NAME="ghcr.io/open-webui/open-webui:main"
CONTAINER_NAME="emohaa-open-webui"
PORT="3000:8080"
VOLUME_NAME="open-webui"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🚀 启动 Emohaa Open WebUI..."

# 检查镜像是否存在
if ! docker images | grep -q "${IMAGE_NAME%:*}.*${IMAGE_NAME#*:}"; then
    echo -e "${RED}❌ 错误: 未找到镜像 ${IMAGE_NAME}${NC}"
    echo "请先加载镜像: docker load < open-webui.tar.gz"
    exit 1
fi

# 检查是否已有同名容器运行
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "⚠️  发现已存在的容器 $CONTAINER_NAME"
    read -p "是否删除旧容器并创建新的? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  删除旧容器..."
        docker stop "$CONTAINER_NAME" 2>/dev/null
        docker rm "$CONTAINER_NAME" 2>/dev/null
    else
        echo "退出..."
        exit 0
    fi
fi

# 运行容器
echo "🔄 启动容器..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT" \
    -v "$VOLUME_NAME:/app/backend/data" \
    --add-host=host.docker.internal:host-gateway \
    --restart always \
    "$IMAGE_NAME"

# 检查容器状态
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 容器启动成功！${NC}"
    echo ""
    echo "📊 容器信息:"
    echo "   名称: $CONTAINER_NAME"
    echo "   端口: http://localhost:${PORT%:*}"
    echo "   数据卷: $VOLUME_NAME"
    echo ""
    echo "🔧 常用命令:"
    echo "   查看日志: docker logs -f $CONTAINER_NAME"
    echo "   停止容器: docker stop $CONTAINER_NAME"
    echo "   启动容器: docker start $CONTAINER_NAME"
    echo "   删除容器: docker rm -f $CONTAINER_NAME"
else
    echo -e "${RED}❌ 容器启动失败！${NC}"
    echo "请检查错误信息并重试。"
    exit 1
fi