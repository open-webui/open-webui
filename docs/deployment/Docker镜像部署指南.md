# Docker镜像部署指南

本文档介绍如何将本地构建的Emohaa WebUI Docker镜像部署到服务器。

## 镜像信息

- **镜像名称**: `ghcr.io/open-webui/open-webui:main`
- **镜像大小**: 约 2.97GB
- **基础镜像**: Python 3.11-slim-bookworm

## 部署方案

### 方案一：镜像导出/导入（推荐）

这是最简单直接的方式，适合大多数场景。

#### 1. 本地导出镜像

```bash
# 导出为压缩包（推荐，体积更小）
docker save ghcr.io/open-webui/open-webui:main | gzip > emohaa-webui.tar.gz

# 或者导出为tar文件（速度更快，但体积更大）
docker save -o emohaa-webui.tar ghcr.io/open-webui/open-webui:main
```

#### 2. 传输到服务器

```bash
# 使用 scp 上传
scp emohaa-webui.tar.gz user@your-server-ip:/tmp/

# 或使用 rsync（支持断点续传）
rsync -avz --progress emohaa-webui.tar.gz user@your-server-ip:/tmp/
```

#### 3. 服务器导入镜像

```bash
# SSH 登录服务器
ssh user@your-server-ip

# 导入镜像（.tar.gz 文件）
cd /tmp
gunzip -c emohaa-webui.tar.gz | docker load

# 或导入 .tar 文件
docker load -i emohaa-webui.tar

# 验证镜像
docker images | grep open-webui
```

#### 4. 运行容器

```bash
# 基础运行命令
docker run -d \
  --name open-webui \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main

# 带环境变量的完整运行命令
docker run -d \
  --name open-webui \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://ollama:11434 \
  -e WEBUI_SECRET_KEY=your-secret-key \
  --add-host=host.docker.internal:host-gateway \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main
```

### 方案二：使用Docker Compose（生产环境推荐）

#### 1. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    volumes:
      - open-webui:/app/backend/data
    ports:
      - "${OPEN_WEBUI_PORT:-3000}:8080"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    extra_hosts:
      - host.docker.internal:host-gateway
    restart: unless-stopped

volumes:
  open-webui:
```

#### 2. 创建环境变量文件 .env

```bash
# 端口配置
OPEN_WEBUI_PORT=3000

# 安全密钥（请生成随机密钥）
WEBUI_SECRET_KEY=your-random-secret-key

# OpenAI API配置（可选）
OPENAI_API_KEY=your-openai-api-key

# 其他配置
DATA_DIR=/app/backend/data
```

#### 3. 启动服务

```bash
# 前台运行（查看日志）
docker-compose up

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方案三：使用镜像仓库

#### 1. 推送到Docker Hub

```bash
# 登录 Docker Hub
docker login

# 标记镜像
docker tag ghcr.io/open-webui/open-webui:main yourusername/emohaa-webui:latest

# 推送镜像
docker push yourusername/emohaa-webui:latest
```

#### 2. 在服务器拉取

```bash
# 拉取镜像
docker pull yourusername/emohaa-webui:latest

# 运行容器
docker run -d --name open-webui -p 3000:8080 yourusername/emohaa-webui:latest
```

### 方案四：使用私有镜像仓库

如果有私有镜像仓库（如Harbor、GitLab Container Registry等）：

```bash
# 标记镜像
docker tag ghcr.io/open-webui/open-webui:main your-registry.com/emohaa-webui:latest

# 推送到私有仓库
docker push your-registry.com/emohaa-webui:latest

# 在服务器拉取
docker pull your-registry.com/emohaa-webui:latest
```

## 数据持久化

### 重要目录

- `/app/backend/data/`: 主数据目录
  - `uploads/`: 生成的图片存储位置
  - `cache/`: 缓存文件
  - `vector_db/`: 向量数据库
  - `webui.db`: 应用数据库

### 备份数据

```bash
# 备份整个数据卷
docker run --rm \
  -v open-webui:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/webui-backup-$(date +%Y%m%d).tar.gz -C /data .

# 恢复数据
docker run --rm \
  -v open-webui:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/webui-backup-20240125.tar.gz -C /data
```

## 常用管理命令

```bash
# 查看容器状态
docker ps -a | grep open-webui

# 查看容器日志
docker logs -f open-webui

# 进入容器调试
docker exec -it open-webui bash

# 重启容器
docker restart open-webui

# 查看资源使用
docker stats open-webui

# 清理未使用的镜像
docker image prune -a
```

## 故障排查

### 1. 容器无法启动

```bash
# 查看详细日志
docker logs open-webui --tail 50

# 检查端口占用
netstat -tlnp | grep 3000
```

### 2. 数据库错误

```bash
# 进入容器检查数据库
docker exec -it open-webui bash
cd /app/backend/data
ls -la
```

### 3. 权限问题

```bash
# 修复数据目录权限
docker exec -it open-webui chown -R 0:0 /app/backend/data
```

## 性能优化

### 1. 资源限制

```yaml
# docker-compose.yml 中添加
services:
  open-webui:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 2. 日志管理

```yaml
# docker-compose.yml 中添加
services:
  open-webui:
    # ... 其他配置
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 安全建议

1. **使用强密码**: 设置强的 `WEBUI_SECRET_KEY`
2. **限制端口访问**: 使用防火墙限制访问端口
3. **使用HTTPS**: 配置反向代理（Nginx/Traefik）提供SSL
4. **定期更新**: 保持镜像和依赖的更新
5. **备份数据**: 定期备份重要数据

## 更新部署

```bash
# 1. 拉取/导入新镜像
docker pull ghcr.io/open-webui/open-webui:main

# 2. 停止旧容器
docker stop open-webui

# 3. 删除旧容器
docker rm open-webui

# 4. 使用新镜像启动
docker run -d \
  --name open-webui \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main
```

## 联系支持

- 项目仓库: https://github.com/open-webui/open-webui
- 问题反馈: 提交GitHub Issue

---

文档更新日期: 2025-01-25