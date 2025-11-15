# 构建脚本使用指南

本目录包含用于本地构建和推送 Docker 镜像的自动化脚本。

## 脚本列表

### 1. `build-and-push.sh` - 完整构建和推送流程 (推荐)

**功能**: 完整的构建、测试、推送流程,包含健康检查

**使用方法**:
```bash
# 1. 登录 GHCR (如需推送)
export CR_PAT=YOUR_PERSONAL_ACCESS_TOKEN
echo $CR_PAT | docker login ghcr.io -u ai-friend-coming --password-stdin

# 2. 运行脚本
./scripts/build-and-push.sh
```

**流程**:
1. 检查 Git 状态和未提交更改
2. 构建 Docker 镜像 (slim 版本)
3. 验证镜像大小和 ID
4. 运行健康检查测试 (可选)
5. 推送镜像到 GHCR (需确认)
6. 清理构建缓存 (可选)

**适用场景**: 正式发布前的完整测试和推送

---

### 2. `quick-build.sh` - 快速本地构建

**功能**: 快速构建镜像用于本地测试,不推送

**使用方法**:
```bash
./scripts/quick-build.sh
```

**特点**:
- 无交互式确认
- 仅构建,不推送
- 构建速度快 (如有缓存)

**适用场景**: 本地开发和快速测试

---

### 3. `simulate-workflow.sh` - 模拟 GitHub Actions

**功能**: 完整模拟 `.github/workflows/docker-build.yaml` 的执行流程

**使用方法**:
```bash
# 设置 CR_PAT (可选)
export CR_PAT=YOUR_PERSONAL_ACCESS_TOKEN

# 运行模拟
./scripts/simulate-workflow.sh
```

**特点**:
- 模拟 GitHub Actions 环境变量
- 创建独立的 Buildx builder
- 使用 registry 缓存
- 输出格式与 GitHub Actions 一致

**适用场景**:
- 测试 workflow 配置
- 在推送代码前验证构建流程
- 排查 CI/CD 问题

---

## 使用示例

### 场景 1: 本地快速测试

```bash
# 1. 快速构建
./scripts/quick-build.sh

# 2. 运行测试
docker run -d -p 8080:8080 ghcr.io/ai-friend-coming/open-webui-next:slim

# 3. 验证
curl http://localhost:8080/health
```

### 场景 2: 发布新版本

```bash
# 1. 确保代码已提交
git add .
git commit -m "feat: add new feature"
git push

# 2. 登录 GHCR
export CR_PAT=ghp_xxxxxxxxxxxx
echo $CR_PAT | docker login ghcr.io -u ai-friend-coming --password-stdin

# 3. 构建和推送
./scripts/build-and-push.sh
# 按提示操作: 运行健康检查 → 确认推送 → 清理缓存

# 4. 验证推送成功
docker pull ghcr.io/ai-friend-coming/open-webui-next:slim
```

### 场景 3: 测试 GitHub Actions workflow

```bash
# 1. 模拟 workflow 执行
export CR_PAT=ghp_xxxxxxxxxxxx
./scripts/simulate-workflow.sh

# 2. 查看构建结果
docker images | grep open-webui-next

# 3. 如果成功,推送代码触发真实 workflow
git push origin main
```

---

## 环境要求

### 必需软件

- **Docker**: 24.0.0+
- **Docker Buildx**: v0.11.0+
- **Git**: 任意版本
- **Bash**: 4.0+

### 系统要求

- **内存**: 建议 8GB+
- **磁盘空间**: 至少 20GB 可用空间
- **网络**: 需要访问 ghcr.io

### Docker 配置

确保 Docker 有足够的资源:

```bash
# Docker Desktop 配置 (推荐):
# - Memory: 8GB
# - Swap: 2GB
# - Disk image size: 64GB
```

---

## 常见问题

### 1. 构建失败 - 内存不足

**错误信息**:
```
FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory
```

**解决方案**:
- 确认 `Dockerfile` 第 30 行已启用: `ENV NODE_OPTIONS="--max-old-space-size=4096"`
- 增加 Docker Desktop 内存限制到 8GB+

### 2. 推送失败 - 未登录

**错误信息**:
```
unauthorized: authentication required
```

**解决方案**:
```bash
# 设置 PAT
export CR_PAT=ghp_your_token_here

# 登录 GHCR
echo $CR_PAT | docker login ghcr.io -u ai-friend-coming --password-stdin
```

### 3. 脚本无执行权限

**错误信息**:
```
Permission denied
```

**解决方案**:
```bash
chmod +x scripts/*.sh
```

### 4. Buildx 不可用

**错误信息**:
```
ERROR: buildx: command not found
```

**解决方案**:
```bash
# 安装 Buildx 插件
docker buildx install

# 或更新 Docker Desktop 到最新版本
```

---

## 标签规则

所有脚本都会生成以下标签:

| 标签格式 | 示例 | 说明 |
|---------|------|------|
| `slim` | `ghcr.io/ai-friend-coming/open-webui-next:slim` | 主标签 (main 分支) |
| `latest-slim` | `ghcr.io/ai-friend-coming/open-webui-next:latest-slim` | 最新版本 (仅 main 分支) |
| `{branch}-slim` | `ghcr.io/ai-friend-coming/open-webui-next:main-slim` | 分支标签 |
| `git-{sha}-slim` | `ghcr.io/ai-friend-coming/open-webui-next:git-88396a1-slim` | Git commit 标签 |

---

## 安全最佳实践

### PAT (Personal Access Token) 管理

1. **权限设置**: 仅授予 `read:packages` 和 `write:packages`
2. **存储位置**: 使用环境变量,不要硬编码到脚本
3. **轮换周期**: 建议每 90 天轮换一次
4. **作用域**: 为不同用途创建不同的 PAT

### 环境变量设置

```bash
# 临时设置 (当前会话)
export CR_PAT=ghp_xxxxxxxxxxxx

# 永久设置 (添加到 ~/.bashrc 或 ~/.zshrc)
echo 'export CR_PAT=ghp_xxxxxxxxxxxx' >> ~/.bashrc
source ~/.bashrc
```

**注意**: 不要提交 PAT 到 Git 仓库

---

## 性能优化

### 使用构建缓存

```bash
# 第一次构建会较慢 (5-10 分钟)
./scripts/build-and-push.sh

# 后续构建会使用缓存 (1-2 分钟)
# 前提: 没有清理缓存
```

### 并行构建 (高级)

如果需要同时构建多个变体:

```bash
# 构建 slim 和 cuda 版本
docker buildx build --build-arg USE_SLIM=true -t IMAGE:slim . &
docker buildx build --build-arg USE_CUDA=true -t IMAGE:cuda . &
wait
```

---

## 清理命令

### 清理所有本地镜像

```bash
# 删除所有 open-webui-next 镜像
docker images | grep open-webui-next | awk '{print $3}' | xargs docker rmi -f

# 清理悬空镜像
docker image prune -f

# 清理所有未使用的镜像
docker image prune -a -f
```

### 清理构建缓存

```bash
# 清理 Buildx 缓存
docker buildx prune -f

# 清理所有 Docker 数据 (谨慎使用)
docker system prune -a --volumes -f
```

---

## 相关文档

- [本地推送完整指南](../docs/LOCAL-PUSH-GUIDE.md)
- [Docker 部署指南](../docs/DOCKER-DEPLOYMENT.md)
- [GitHub Actions Workflow](../.github/workflows/docker-build.yaml)

---

## 获取帮助

如果遇到问题:

1. 查看脚本输出的错误信息
2. 参考本文档的"常见问题"部分
3. 查看详细文档: `docs/LOCAL-PUSH-GUIDE.md`
4. 提交 Issue: https://github.com/ai-friend-coming/open-webui-next/issues

---

**最后更新**: 2024-11-14
