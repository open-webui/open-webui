# 本地镜像构建与推送指南

本指南介绍如何在本地构建 Docker 镜像并手动推送到 GitHub Container Registry (GHCR)。

## 当前仓库信息

- **仓库**: `ai-friend-coming/open-webui-next`
- **镜像仓库**: `ghcr.io/ai-friend-coming/open-webui-next`
- **当前分支**: `main`
- **当前 commit**: `88396a16e`

---

## 前置准备

### 1. 登录 GitHub Container Registry

#### 创建 Personal Access Token (PAT)

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token" → "Generate new token (classic)"
3. 设置权限:
   - `write:packages` - 推送容器镜像
   - `read:packages` - 拉取容器镜像
   - `delete:packages` - (可选) 删除镜像
4. 生成并保存 Token

#### 登录 GHCR

```bash
# 方式 1: 使用 PAT 登录 (推荐)
export CR_PAT=YOUR_PERSONAL_ACCESS_TOKEN
echo $CR_PAT | docker login ghcr.io -u ai-friend-coming --password-stdin

# 方式 2: 交互式登录
docker login ghcr.io -u ai-friend-coming
# Password: [输入 PAT]
```

成功登录后会显示:
```
Login Succeeded
```

### 2. 验证 Docker 环境

```bash
# 检查 Docker 版本
docker --version
# 推荐: Docker version 24.0.0 或更高

# 检查 Buildx 插件
docker buildx version
# 推荐: v0.11.0 或更高

# 创建 Buildx builder (如果不存在)
docker buildx create --name multiarch-builder --use
docker buildx inspect --bootstrap
```

---

## 构建与推送流程

### 方式一: 模拟 GitHub Actions 流程 (推荐)

完全模拟 `.github/workflows/docker-build.yaml` 的构建流程:

```bash
#!/bin/bash
# build-and-push.sh

set -e  # 遇到错误立即退出

# ============ 配置变量 ============
REGISTRY="ghcr.io"
IMAGE_NAME="ai-friend-coming/open-webui-next"
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"

# 获取 Git 信息
BUILD_HASH=$(git rev-parse HEAD)
SHORT_HASH=$(git rev-parse --short HEAD)
BRANCH=$(git branch --show-current)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "========================================="
echo "构建信息:"
echo "  仓库: ${IMAGE_NAME}"
echo "  分支: ${BRANCH}"
echo "  Commit: ${SHORT_HASH}"
echo "  时间: ${TIMESTAMP}"
echo "========================================="

# ============ 镜像标签生成 ============
TAGS=(
  "${FULL_IMAGE_NAME}:slim"                    # 主标签
  "${FULL_IMAGE_NAME}:${BRANCH}-slim"          # 分支标签
  "${FULL_IMAGE_NAME}:git-${SHORT_HASH}-slim"  # Git commit 标签
  "${FULL_IMAGE_NAME}:${TIMESTAMP}-slim"       # 时间戳标签
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

echo ""
echo "将构建以下标签:"
for tag in "${TAGS[@]}"; do
  echo "  - ${tag}"
done
echo ""

# ============ 构建镜像 ============
echo "开始构建镜像..."
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH="${BUILD_HASH}" \
  --build-arg USE_SLIM=true \
  ${TAG_ARGS} \
  --load \
  .

echo ""
echo "✅ 镜像构建成功!"
echo ""

# ============ 推送镜像 ============
read -p "是否推送镜像到 GHCR? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "开始推送镜像..."

  for tag in "${TAGS[@]}"; do
    echo "推送: ${tag}"
    docker push "${tag}"
  done

  echo ""
  echo "✅ 所有镜像推送成功!"
  echo ""
  echo "拉取命令:"
  echo "  docker pull ${FULL_IMAGE_NAME}:slim"
  echo ""
  echo "查看镜像:"
  echo "  https://github.com/${IMAGE_NAME}/pkgs/container/open-webui-next"
else
  echo "跳过推送"
fi

# ============ 清理 ============
echo ""
read -p "是否清理本地构建缓存? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "清理构建缓存..."
  docker builder prune -f
  echo "✅ 缓存清理完成"
fi
```

**使用方法**:

```bash
# 添加执行权限
chmod +x build-and-push.sh

# 执行构建
./build-and-push.sh
```

### 方式二: 手动分步执行

#### 1. 构建镜像

```bash
# 获取当前 commit SHA
BUILD_HASH=$(git rev-parse HEAD)
SHORT_HASH=$(git rev-parse --short HEAD)

# 构建镜像
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH="${BUILD_HASH}" \
  --build-arg USE_SLIM=true \
  -t ghcr.io/ai-friend-coming/open-webui-next:slim \
  -t ghcr.io/ai-friend-coming/open-webui-next:main-slim \
  -t ghcr.io/ai-friend-coming/open-webui-next:git-${SHORT_HASH}-slim \
  --load \
  .
```

**构建参数说明**:
- `--platform linux/amd64`: 构建 x86_64 架构镜像
- `--build-arg BUILD_HASH`: 传入 Git commit SHA
- `--build-arg USE_SLIM=true`: 构建精简版 (不预装模型)
- `-t`: 指定镜像标签 (可以多个)
- `--load`: 加载到本地 Docker (用于单平台构建)

#### 2. 验证镜像

```bash
# 查看镜像大小
docker images | grep open-webui-next

# 查看镜像详细信息
docker inspect ghcr.io/ai-friend-coming/open-webui-next:slim

# 测试运行
docker run --rm -p 8080:8080 ghcr.io/ai-friend-coming/open-webui-next:slim
```

#### 3. 推送镜像

```bash
# 推送所有标签
docker push ghcr.io/ai-friend-coming/open-webui-next:slim
docker push ghcr.io/ai-friend-coming/open-webui-next:main-slim
docker push ghcr.io/ai-friend-coming/open-webui-next:git-${SHORT_HASH}-slim
```

或批量推送:

```bash
# 批量推送
docker images | grep "ghcr.io/ai-friend-coming/open-webui-next" | awk '{print $1":"$2}' | xargs -I {} docker push {}
```

#### 4. 验证推送

```bash
# 从 GHCR 拉取验证
docker pull ghcr.io/ai-friend-coming/open-webui-next:slim

# 访问 GitHub Packages 页面
# https://github.com/ai-friend-coming/open-webui-next/pkgs/container/open-webui-next
```

---

## 构建不同镜像变体

### Slim 版本 (默认, 推荐)

```bash
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH=$(git rev-parse HEAD) \
  --build-arg USE_SLIM=true \
  -t ghcr.io/ai-friend-coming/open-webui-next:slim \
  --load \
  .
```

**特点**:
- 镜像较小 (~7.8GB)
- 首次运行时自动下载 AI 模型
- 适合生产环境

### 标准版本 (预装模型)

```bash
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH=$(git rev-parse HEAD) \
  --build-arg USE_SLIM=false \
  -t ghcr.io/ai-friend-coming/open-webui-next:latest \
  --load \
  .
```

**特点**:
- 镜像较大 (~10GB)
- 预装 AI 模型,启动更快
- 适合离线环境

### CUDA 版本 (GPU 加速)

```bash
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH=$(git rev-parse HEAD) \
  --build-arg USE_CUDA=true \
  --build-arg USE_CUDA_VER=cu128 \
  -t ghcr.io/ai-friend-coming/open-webui-next:cuda \
  --load \
  .
```

**特点**:
- 支持 NVIDIA GPU 加速
- 需要宿主机安装 NVIDIA Docker runtime
- 镜像更大 (~15GB)

---

## 高级功能

### 1. 多架构构建 (amd64 + arm64)

```bash
# 创建 multiarch builder
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap

# 构建并推送多架构镜像
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg BUILD_HASH=$(git rev-parse HEAD) \
  --build-arg USE_SLIM=true \
  -t ghcr.io/ai-friend-coming/open-webui-next:slim \
  --push \
  .
```

**注意**:
- 多架构构建会自动推送 (不支持 `--load`)
- ARM64 构建可能需要 1-2 小时

### 2. 使用缓存加速构建

```bash
# 第一次构建: 导出缓存
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH=$(git rev-parse HEAD) \
  --build-arg USE_SLIM=true \
  -t ghcr.io/ai-friend-coming/open-webui-next:slim \
  --cache-to type=registry,ref=ghcr.io/ai-friend-coming/open-webui-next:cache-slim-amd64 \
  --load \
  .

# 后续构建: 使用缓存
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH=$(git rev-parse HEAD) \
  --build-arg USE_SLIM=true \
  -t ghcr.io/ai-friend-coming/open-webui-next:slim \
  --cache-from type=registry,ref=ghcr.io/ai-friend-coming/open-webui-next:cache-slim-amd64 \
  --load \
  .
```

**效果**: 构建时间从 5 分钟降低到 1-2 分钟

### 3. 本地缓存 (更快)

```bash
# 使用本地缓存
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH=$(git rev-parse HEAD) \
  --build-arg USE_SLIM=true \
  -t ghcr.io/ai-friend-coming/open-webui-next:slim \
  --cache-to type=local,dest=/tmp/docker-cache \
  --cache-from type=local,src=/tmp/docker-cache \
  --load \
  .
```

---

## 故障排查

### 1. 构建内存不足

**错误**:
```
FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory
```

**解决方案**:
- ✅ 确认 Dockerfile 第 30 行已取消注释: `ENV NODE_OPTIONS="--max-old-space-size=4096"`
- ✅ 增加 Docker 内存限制: Docker Desktop → Settings → Resources → Memory (建议 8GB+)

### 2. 推送权限被拒绝

**错误**:
```
denied: permission_denied: write_package
```

**解决方案**:
```bash
# 检查登录状态
docker info | grep Username

# 重新登录
docker logout ghcr.io
echo $CR_PAT | docker login ghcr.io -u ai-friend-coming --password-stdin

# 确认 PAT 有 write:packages 权限
```

### 3. 镜像推送超时

**错误**:
```
error: timeout exceeded
```

**解决方案**:
```bash
# 增加 Docker 推送超时
export DOCKER_CLIENT_TIMEOUT=300
export COMPOSE_HTTP_TIMEOUT=300

# 或分别推送每个标签
docker push ghcr.io/ai-friend-coming/open-webui-next:slim
```

### 4. Buildx 不可用

**错误**:
```
ERROR: buildx: command not found
```

**解决方案**:
```bash
# 更新 Docker Desktop 到最新版本
# 或手动安装 Buildx 插件
mkdir -p ~/.docker/cli-plugins
curl -Lo ~/.docker/cli-plugins/docker-buildx https://github.com/docker/buildx/releases/download/v0.11.2/buildx-v0.11.2.linux-amd64
chmod +x ~/.docker/cli-plugins/docker-buildx
```

---

## 清理与维护

### 清理本地镜像

```bash
# 删除 dangling 镜像
docker image prune -f

# 删除所有未使用的镜像
docker image prune -a -f

# 删除特定镜像
docker rmi ghcr.io/ai-friend-coming/open-webui-next:slim
```

### 清理构建缓存

```bash
# 清理 Buildx 缓存
docker buildx prune -f

# 清理所有 Docker 缓存 (谨慎使用)
docker system prune -a --volumes -f
```

### 查看镜像层信息

```bash
# 使用 dive 工具分析镜像
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest \
  ghcr.io/ai-friend-coming/open-webui-next:slim
```

---

## 自动化脚本示例

### 完整的 CI/CD 本地模拟脚本

保存为 `scripts/local-build.sh`:

```bash
#!/bin/bash
# scripts/local-build.sh
# 完整的本地构建、测试、推送流程

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
REGISTRY="ghcr.io"
IMAGE_NAME="ai-friend-coming/open-webui-next"
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"
VARIANT="slim"

# Git 信息
BUILD_HASH=$(git rev-parse HEAD)
SHORT_HASH=$(git rev-parse --short HEAD)
BRANCH=$(git branch --show-current)

# 检查工作目录
if [ ! -f "Dockerfile" ]; then
  echo_error "请在项目根目录运行此脚本"
  exit 1
fi

# 检查未提交的更改
if [ -n "$(git status --porcelain)" ]; then
  echo_warn "存在未提交的更改:"
  git status --short
  read -p "继续构建? (y/n): " -n 1 -r
  echo
  [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

echo_info "========================================="
echo_info "构建配置:"
echo_info "  仓库: ${IMAGE_NAME}"
echo_info "  分支: ${BRANCH}"
echo_info "  Commit: ${SHORT_HASH}"
echo_info "  变体: ${VARIANT}"
echo_info "========================================="

# 1. 构建镜像
echo_info "步骤 1/5: 构建镜像..."
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_HASH="${BUILD_HASH}" \
  --build-arg USE_SLIM=true \
  -t ${FULL_IMAGE_NAME}:${VARIANT} \
  -t ${FULL_IMAGE_NAME}:git-${SHORT_HASH}-${VARIANT} \
  --load \
  .

# 2. 验证镜像大小
echo_info "步骤 2/5: 验证镜像..."
IMAGE_SIZE=$(docker images ${FULL_IMAGE_NAME}:${VARIANT} --format "{{.Size}}")
echo_info "  镜像大小: ${IMAGE_SIZE}"

# 3. 测试镜像
echo_info "步骤 3/5: 测试镜像..."
CONTAINER_ID=$(docker run -d -p 8081:8080 ${FULL_IMAGE_NAME}:${VARIANT})
echo_info "  测试容器 ID: ${CONTAINER_ID}"

# 等待健康检查
echo_info "  等待服务启动 (最多 60 秒)..."
for i in {1..60}; do
  if curl -sf http://localhost:8081/health > /dev/null 2>&1; then
    echo_info "  ✅ 健康检查通过"
    break
  fi
  sleep 1
  [ $i -eq 60 ] && echo_error "健康检查超时" && docker logs ${CONTAINER_ID} && exit 1
done

# 清理测试容器
docker stop ${CONTAINER_ID} > /dev/null
docker rm ${CONTAINER_ID} > /dev/null
echo_info "  测试容器已清理"

# 4. 推送镜像
echo_info "步骤 4/5: 推送镜像到 GHCR..."
read -p "确认推送? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  # 检查登录状态
  if ! docker info | grep -q "Username: ai-friend-coming"; then
    echo_error "未登录 GHCR,请先登录:"
    echo "  echo \$CR_PAT | docker login ghcr.io -u ai-friend-coming --password-stdin"
    exit 1
  fi

  docker push ${FULL_IMAGE_NAME}:${VARIANT}
  docker push ${FULL_IMAGE_NAME}:git-${SHORT_HASH}-${VARIANT}
  echo_info "  ✅ 推送成功"
else
  echo_warn "跳过推送"
fi

# 5. 清理
echo_info "步骤 5/5: 清理..."
docker builder prune -f > /dev/null
echo_info "  构建缓存已清理"

echo_info "========================================="
echo_info "✅ 构建流程完成!"
echo_info ""
echo_info "拉取命令:"
echo_info "  docker pull ${FULL_IMAGE_NAME}:${VARIANT}"
echo_info ""
echo_info "查看镜像:"
echo_info "  https://github.com/${IMAGE_NAME}/pkgs/container/open-webui-next"
echo_info "========================================="
```

**使用方法**:

```bash
chmod +x scripts/local-build.sh
./scripts/local-build.sh
```

---

## 最佳实践

### 1. 构建前检查清单

- [ ] 代码已提交到 Git
- [ ] Docker 有足够内存 (8GB+)
- [ ] 已登录 GHCR
- [ ] 磁盘空间充足 (20GB+)

### 2. 标签命名规范

```bash
# 生产环境
ghcr.io/ai-friend-coming/open-webui-next:v1.2.3-slim

# 测试环境
ghcr.io/ai-friend-coming/open-webui-next:dev-slim

# 特性分支
ghcr.io/ai-friend-coming/open-webui-next:feature-auth-slim
```

### 3. 安全建议

- 不要在脚本中硬编码 PAT
- 使用环境变量: `export CR_PAT=xxx`
- 定期轮换 PAT (90 天)
- 使用 `.gitignore` 排除敏感文件

### 4. 性能优化

- 使用 `--cache-from` 复用缓存
- 本地缓存构建结果到 `/tmp`
- 使用 SSD 存储 Docker 数据
- 增大 Docker 内存限制

---

## 常用命令速查

```bash
# 构建
docker buildx build -t IMAGE:TAG --load .

# 推送
docker push IMAGE:TAG

# 拉取
docker pull IMAGE:TAG

# 登录
echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin

# 清理
docker system prune -a -f

# 查看镜像
docker images | grep open-webui-next

# 测试镜像
docker run --rm -p 8080:8080 IMAGE:TAG
```

---

**最后更新**: 2024-11-14
