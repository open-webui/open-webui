#!/bin/bash
# build-and-push.sh - 本地构建并推送镜像到 GHCR
# 使用方法: ./scripts/build-and-push.sh

set -e  # 遇到错误立即退出

# ============ 颜色输出 ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# ============ 配置变量 ============
REGISTRY="ghcr.io"
IMAGE_NAME="ai-friend-coming/open-webui-next"
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"

# 获取 Git 信息
BUILD_HASH=$(git rev-parse HEAD)
SHORT_HASH=$(git rev-parse --short HEAD)
BRANCH=$(git branch --show-current)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# 检查工作目录
if [ ! -f "Dockerfile" ]; then
  echo_error "请在项目根目录运行此脚本"
  exit 1
fi

echo_info "========================================="
echo_info "构建信息:"
echo_info "  仓库: ${IMAGE_NAME}"
echo_info "  分支: ${BRANCH}"
echo_info "  Commit: ${SHORT_HASH} (${BUILD_HASH:0:40}...)"
echo_info "  时间: ${TIMESTAMP}"
echo_info "========================================="
echo ""

# 检查未提交的更改
if [ -n "$(git status --porcelain)" ]; then
  echo_warn "存在未提交的更改:"
  git status --short
  echo ""
  read -p "继续构建? (y/n): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo_info "已取消"
    exit 0
  fi
fi

# ============ 镜像标签生成 ============
TAGS=(
  "${FULL_IMAGE_NAME}:slim"                    # 主标签
  "${FULL_IMAGE_NAME}:${BRANCH}-slim"          # 分支标签
  "${FULL_IMAGE_NAME}:git-${SHORT_HASH}-slim"  # Git commit 标签
)

# 如果在 main 分支,添加 latest-slim 标签
if [ "$BRANCH" = "main" ]; then
  TAGS+=("${FULL_IMAGE_NAME}:latest-slim")
fi

# 构建标签参数
TAG_ARGS=""
for tag in "${TAGS[@]}"; do
  TAG_ARGS="${TAG_ARGS} -t ${tag}"
done

echo_info "将构建以下标签:"
for tag in "${TAGS[@]}"; do
  echo "  - ${tag}"
done
echo ""

# ============ 构建镜像 ============
echo_step "步骤 1/4: 构建 Docker 镜像"
echo_info "开始构建镜像 (这可能需要 5-10 分钟)..."
echo ""

docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH="${BUILD_HASH}" \
  --build-arg USE_SLIM=true \
  ${TAG_ARGS} \
  --load \
  .

echo ""
echo_info "✅ 镜像构建成功!"
echo ""

# ============ 验证镜像 ============
echo_step "步骤 2/4: 验证镜像"

IMAGE_SIZE=$(docker images ${FULL_IMAGE_NAME}:slim --format "{{.Size}}")
IMAGE_ID=$(docker images ${FULL_IMAGE_NAME}:slim --format "{{.ID}}")

echo_info "镜像信息:"
echo "  - ID: ${IMAGE_ID}"
echo "  - 大小: ${IMAGE_SIZE}"
echo ""

# ============ 测试镜像 ============
echo_step "步骤 3/4: 测试镜像"
read -p "是否运行健康检查测试? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo_info "启动测试容器 (端口 8081)..."

  CONTAINER_ID=$(docker run -d -p 8081:8080 ${FULL_IMAGE_NAME}:slim)
  echo_info "容器 ID: ${CONTAINER_ID}"
  echo ""

  echo_info "等待服务启动 (最多 120 秒)..."
  HEALTH_CHECK_PASSED=false

  for i in {1..120}; do
    if curl -sf http://localhost:8081/health > /dev/null 2>&1; then
      echo_info "✅ 健康检查通过 (耗时 ${i} 秒)"
      HEALTH_CHECK_PASSED=true
      break
    fi

    # 每 10 秒显示一次进度
    if [ $((i % 10)) -eq 0 ]; then
      echo_info "  等待中... (${i}/120 秒)"
    fi

    sleep 1
  done

  if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo_error "健康检查超时!"
    echo_error "容器日志:"
    docker logs ${CONTAINER_ID} | tail -50
    docker stop ${CONTAINER_ID} > /dev/null
    docker rm ${CONTAINER_ID} > /dev/null
    exit 1
  fi

  # 清理测试容器
  echo_info "清理测试容器..."
  docker stop ${CONTAINER_ID} > /dev/null
  docker rm ${CONTAINER_ID} > /dev/null
  echo ""
else
  echo_warn "跳过健康检查"
  echo ""
fi

# ============ 推送镜像 ============
echo_step "步骤 4/4: 推送镜像到 GHCR"
echo_info "将推送 ${#TAGS[@]} 个标签到 ${REGISTRY}"
echo ""

read -p "确认推送? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  # 检查登录状态
  if ! docker info 2>/dev/null | grep -q "Username"; then
    echo_error "未登录 GHCR!"
    echo_error "请先执行:"
    echo "  export CR_PAT=YOUR_PERSONAL_ACCESS_TOKEN"
    echo "  echo \$CR_PAT | docker login ghcr.io -u ai-friend-coming --password-stdin"
    exit 1
  fi

  echo_info "开始推送镜像..."
  echo ""

  for tag in "${TAGS[@]}"; do
    echo_info "推送: ${tag}"
    docker push "${tag}"
  done

  echo ""
  echo_info "✅ 所有镜像推送成功!"
  echo ""
  echo_info "拉取命令:"
  echo "  docker pull ${FULL_IMAGE_NAME}:slim"
  echo ""
  echo_info "查看镜像:"
  echo "  https://github.com/${IMAGE_NAME}/pkgs/container/open-webui-next"
  echo ""
else
  echo_warn "跳过推送"
  echo ""
fi

# ============ 清理 ============
echo_info "清理选项:"
read -p "是否清理本地构建缓存? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo_info "清理构建缓存..."
  docker builder prune -f
  echo_info "✅ 缓存清理完成"
else
  echo_warn "保留构建缓存 (下次构建会更快)"
fi

echo ""
echo_info "========================================="
echo_info "✅ 构建流程完成!"
echo_info "========================================="
