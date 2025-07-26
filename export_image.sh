#!/bin/bash

# 设置镜像名称
IMAGE_NAME="emohaa-open-webui:main"
OUTPUT_FILE="emohaa-emohaa-open-webui.tar.gz"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🚀 导出 Emohaa Open WebUI Docker 镜像..."
echo ""

# 检查镜像是否存在
if ! docker images | grep -q "${IMAGE_NAME%:*}.*${IMAGE_NAME#*:}"; then
    echo -e "${RED}❌ 错误: 未找到镜像 ${IMAGE_NAME}${NC}"
    echo "请先运行 ./run-compose.sh 构建镜像"
    exit 1
fi

# 显示镜像信息
echo -e "${YELLOW}📦 镜像信息:${NC}"
docker images | grep -E "REPOSITORY|${IMAGE_NAME%:*}"
echo ""

# 检查是否已存在导出文件
if [ -f "$OUTPUT_FILE" ]; then
    echo -e "${YELLOW}⚠️  发现已存在的导出文件: $OUTPUT_FILE${NC}"
    read -p "是否覆盖? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "退出..."
        exit 0
    fi
    rm -f "$OUTPUT_FILE"
fi

# 导出镜像
echo -e "${YELLOW}🔄 正在导出镜像 (这可能需要几分钟)...${NC}"
docker save "$IMAGE_NAME" | gzip -9 > "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    # 获取文件大小
    FILE_SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
    echo -e "${GREEN}✅ 镜像导出成功！${NC}"
    echo ""
    echo "📊 导出信息:"
    echo "   文件名: $OUTPUT_FILE"
    echo "   大小: $FILE_SIZE"
    echo ""
    echo "📝 下一步:"
    echo "   1. 传输到服务器: scp $OUTPUT_FILE user@server:/path/"
    echo "   2. 在服务器加载: docker load < $OUTPUT_FILE"
    echo "   3. 运行容器: ./run_docker.sh"
else
    echo -e "${RED}❌ 镜像导出失败！${NC}"
    exit 1
fi