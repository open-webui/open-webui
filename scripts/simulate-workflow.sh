#!/bin/bash
# simulate-workflow.sh - 模拟 GitHub Actions workflow 完整流程
# 使用方法: ./scripts/simulate-workflow.sh

set -e

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_job() { echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}[JOB]${NC} $1"; }
echo_step() { echo -e "${GREEN}[STEP]${NC} $1"; }
echo_info() { echo -e "       $1"; }

# ============ 模拟 GitHub Actions 环境变量 ============
export GITHUB_REPOSITORY="ai-friend-coming/open-webui-next"
export GITHUB_SHA=$(git rev-parse HEAD)
export GITHUB_REF=$(git symbolic-ref HEAD)
export GITHUB_REF_NAME=$(git branch --show-current)
export IMAGE_NAME="${GITHUB_REPOSITORY,,}"  # 转小写
export FULL_IMAGE_NAME="ghcr.io/${IMAGE_NAME}"

echo_job "Build Slim Image (amd64)"
echo ""

# ============ Step 1: Set repository and image name ============
echo_step "Set repository and image name to lowercase"
echo_info "IMAGE_NAME=${IMAGE_NAME}"
echo_info "FULL_IMAGE_NAME=${FULL_IMAGE_NAME}"
echo ""

# ============ Step 2: Checkout repository ============
echo_step "Checkout repository"
echo_info "Repository: ${GITHUB_REPOSITORY}"
echo_info "Branch: ${GITHUB_REF_NAME}"
echo_info "Commit: ${GITHUB_SHA:0:7}"
echo ""

# ============ Step 3: Set up Docker Buildx ============
echo_step "Set up Docker Buildx"
if ! docker buildx inspect github-actions > /dev/null 2>&1; then
  docker buildx create --name github-actions --use
  echo_info "Created new builder: github-actions"
else
  docker buildx use github-actions
  echo_info "Using existing builder: github-actions"
fi
docker buildx inspect --bootstrap
echo ""

# ============ Step 4: Log in to GitHub Container Registry ============
echo_step "Log in to GitHub Container Registry"
echo_info "Registry: ghcr.io"
echo_info "Username: $(whoami)"

if [ -z "$CR_PAT" ]; then
  echo -e "${YELLOW}[WARN]${NC} CR_PAT 环境变量未设置,跳过登录"
  echo_info "如需推送,请设置: export CR_PAT=YOUR_PERSONAL_ACCESS_TOKEN"
  SKIP_PUSH=true
else
  echo $CR_PAT | docker login ghcr.io -u ai-friend-coming --password-stdin > /dev/null 2>&1
  echo_info "✅ Login Succeeded"
  SKIP_PUSH=false
fi
echo ""

# ============ Step 5: Extract metadata for Docker images ============
echo_step "Extract metadata for Docker images"

# 生成标签
if [ "$GITHUB_REF_NAME" = "main" ]; then
  TAGS=(
    "${FULL_IMAGE_NAME}:slim"
    "${FULL_IMAGE_NAME}:latest-slim"
    "${FULL_IMAGE_NAME}:${GITHUB_REF_NAME}-slim"
    "${FULL_IMAGE_NAME}:git-${GITHUB_SHA:0:7}-slim"
  )
else
  TAGS=(
    "${FULL_IMAGE_NAME}:${GITHUB_REF_NAME}-slim"
    "${FULL_IMAGE_NAME}:git-${GITHUB_SHA:0:7}-slim"
  )
fi

echo_info "Tags:"
for tag in "${TAGS[@]}"; do
  echo_info "  - ${tag}"
done
echo ""

# 构建标签参数
TAG_ARGS=""
for tag in "${TAGS[@]}"; do
  TAG_ARGS="${TAG_ARGS} --tag ${tag}"
done

# ============ Step 6: Extract metadata for Docker cache ============
echo_step "Extract metadata for Docker cache"
CACHE_TAG="${FULL_IMAGE_NAME}:cache-slim-linux-amd64-${GITHUB_REF_NAME}"
echo_info "Cache: ${CACHE_TAG}"
echo ""

# ============ Step 7: Build and push Docker image ============
echo_step "Build and push Docker image (slim)"
echo_info "Platform: linux/amd64"
echo_info "Build args: BUILD_HASH=${GITHUB_SHA}, USE_SLIM=true"
echo ""

if [ "$SKIP_PUSH" = true ]; then
  # 仅构建,不推送
  docker buildx build \
    --platform linux/amd64 \
    --build-arg BUILD_HASH="${GITHUB_SHA}" \
    --build-arg USE_SLIM=true \
    ${TAG_ARGS} \
    --cache-from type=registry,ref=${CACHE_TAG} \
    --load \
    .
  echo ""
  echo -e "${YELLOW}[WARN]${NC} 跳过推送 (CR_PAT 未设置)"
else
  # 构建并推送
  read -p "确认推送到 GHCR? (y/n): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker buildx build \
      --platform linux/amd64 \
      --build-arg BUILD_HASH="${GITHUB_SHA}" \
      --build-arg USE_SLIM=true \
      ${TAG_ARGS} \
      --cache-from type=registry,ref=${CACHE_TAG} \
      --cache-to type=registry,ref=${CACHE_TAG},mode=max \
      --push \
      .
    echo ""
    echo_info "✅ Image pushed successfully"
  else
    docker buildx build \
      --platform linux/amd64 \
      --build-arg BUILD_HASH="${GITHUB_SHA}" \
      --build-arg USE_SLIM=true \
      ${TAG_ARGS} \
      --cache-from type=registry,ref=${CACHE_TAG} \
      --load \
      .
    echo ""
    echo -e "${YELLOW}[WARN]${NC} 用户取消推送"
  fi
fi
echo ""

# ============ Step 8: Inspect image ============
echo_step "Inspect image"
if [ "$SKIP_PUSH" = false ] && [[ $REPLY =~ ^[Yy]$ ]]; then
  docker buildx imagetools inspect ${FULL_IMAGE_NAME}:slim
else
  docker images | grep open-webui-next | head -5
fi
echo ""

# ============ Step 9: Output image tags ============
echo_step "Output image tags"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🐳 Docker 镜像构建成功${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📦 镜像标签:"
for tag in "${TAGS[@]}"; do
  echo "   ${tag}"
done
echo ""
echo "🚀 拉取命令:"
echo "   docker pull ${FULL_IMAGE_NAME}:slim"
echo ""
echo "🌐 查看镜像:"
echo "   https://github.com/${GITHUB_REPOSITORY}/pkgs/container/open-webui-next"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
