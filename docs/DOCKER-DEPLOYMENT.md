# Open WebUI Docker 生产环境部署指南

本指南介绍如何在生产环境中部署 Open WebUI Docker 镜像，并连接到外部 MySQL 数据库。

## 目录

- [镜像说明](#镜像说明)
- [镜像获取方式](#镜像获取方式)
- [前置准备](#前置准备)
- [快速开始](#快速开始)
- [MySQL 数据库配置](#mysql-数据库配置)
- [环境变量完整列表](#环境变量完整列表)
- [高级配置](#高级配置)
- [故障排查](#故障排查)

---

## 镜像说明

### 镜像仓库
```
ghcr.io/<your-username>/open-webui-next:slim
```

### 镜像特性
- **架构**: linux/amd64 (x86_64)
- **变体**: Slim 精简版（不预装 AI 模型，首次运行时自动下载）
- **包含**: 前端 (SvelteKit) + 后端 (FastAPI)
- **不包含**: 数据库服务（需要外部 MySQL）

### 镜像标签规则

| 标签 | 说明 | 示例 |
|------|------|------|
| `slim` | 主分支最新精简版 | `ghcr.io/user/repo:slim` |
| `main-slim` | 主分支最新构建 | `ghcr.io/user/repo:main-slim` |
| `v1.2.3-slim` | 版本标签 | `ghcr.io/user/repo:v1.2.3-slim` |
| `git-abc1234-slim` | Git commit SHA | `ghcr.io/user/repo:git-abc1234-slim` |

---

## 镜像获取方式

### 从 GitHub Container Registry (GHCR) 拉取

#### 方式一：拉取公开镜像（推荐）

如果仓库是公开的，直接拉取即可：

```bash
# 拉取最新 slim 版本
docker pull ghcr.io/<your-username>/open-webui-next:slim

# 拉取特定版本标签
docker pull ghcr.io/<your-username>/open-webui-next:v1.2.3-slim

# 拉取特定 Git commit
docker pull ghcr.io/<your-username>/open-webui-next:git-abc1234-slim
```

验证镜像拉取成功：

```bash
# 查看本地镜像列表
docker images | grep open-webui-next

# 查看镜像详细信息
docker inspect ghcr.io/<your-username>/open-webui-next:slim
```

#### 方式二：拉取私有镜像（需要认证）

如果仓库是私有的，需要先登录 GHCR：

**步骤 1: 创建 GitHub Personal Access Token (PAT)**

1. 访问 GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 "Generate new token (classic)"
3. 设置以下权限:
   - `read:packages` - 读取容器镜像
   - `write:packages` - (可选) 推送镜像
4. 生成并保存 Token (只显示一次)

**步骤 2: 登录 GHCR**

```bash
# 使用 PAT 登录
echo "YOUR_PERSONAL_ACCESS_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 或交互式输入密码
docker login ghcr.io -u YOUR_GITHUB_USERNAME
# Password: [输入 PAT]
```

登录成功后会显示:
```
Login Succeeded
```

**步骤 3: 拉取镜像**

```bash
docker pull ghcr.io/<your-username>/open-webui-next:slim
```

**步骤 4: 退出登录（可选）**

```bash
docker logout ghcr.io
```

### 生产服务器部署流程

#### 场景一：单服务器部署

```bash
# 1. SSH 登录生产服务器
ssh user@production-server

# 2. 登录 GHCR (如果是私有仓库)
echo "YOUR_PAT" | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# 3. 拉取最新镜像
docker pull ghcr.io/<your-username>/open-webui-next:slim

# 4. 停止旧容器 (如果存在)
docker stop open-webui || true
docker rm open-webui || true

# 5. 启动新容器
docker run -d \
  --name open-webui \
  --restart unless-stopped \
  -p 8080:8080 \
  -e DATABASE_URL="mysql://..." \
  -v /data/open-webui/data:/app/backend/data \
  ghcr.io/<your-username>/open-webui-next:slim

# 6. 验证部署
docker ps | grep open-webui
curl -f http://localhost:8080/health || echo "Health check failed"
```

#### 场景二：CI/CD 自动化部署

**GitHub Actions 自动部署示例**:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  workflow_run:
    workflows: ["Build and Push Docker Image (Production)"]
    types:
      - completed

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}

    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.PROD_SERVER_HOST }}
          username: ${{ secrets.PROD_SERVER_USER }}
          key: ${{ secrets.PROD_SERVER_SSH_KEY }}
          script: |
            # 拉取最新镜像
            docker pull ghcr.io/${{ github.repository }}:slim

            # 滚动更新
            docker stop open-webui || true
            docker rm open-webui || true

            docker run -d \
              --name open-webui \
              --restart unless-stopped \
              -p 8080:8080 \
              --env-file /opt/openwebui/.env \
              -v /data/open-webui/data:/app/backend/data \
              ghcr.io/${{ github.repository }}:slim

            # 健康检查
            sleep 10
            docker ps | grep open-webui
            curl -f http://localhost:8080/health
```

#### 场景三：多服务器部署（使用镜像同步）

如果有多台服务器，可以先拉取到一台，然后导出/导入：

```bash
# 服务器 A: 从 GHCR 拉取
docker pull ghcr.io/<your-username>/open-webui-next:slim

# 导出镜像到文件
docker save ghcr.io/<your-username>/open-webui-next:slim | gzip > open-webui-slim.tar.gz

# 传输到其他服务器
scp open-webui-slim.tar.gz user@server-b:/tmp/
scp open-webui-slim.tar.gz user@server-c:/tmp/

# 服务器 B/C: 导入镜像
gunzip -c /tmp/open-webui-slim.tar.gz | docker load
```

### 镜像更新策略

#### 自动更新（使用 Watchtower）

```bash
# 部署 Watchtower 容器监控镜像更新
docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 3600 \
  --cleanup \
  open-webui
```

Watchtower 会每小时检查一次 `open-webui` 容器的镜像更新，如果有新版本会自动拉取并重启容器。

#### 手动更新（推荐生产环境）

```bash
# 1. 拉取最新镜像
docker pull ghcr.io/<your-username>/open-webui-next:slim

# 2. 检查镜像是否有更新
OLD_ID=$(docker inspect --format='{{.Image}}' open-webui)
NEW_ID=$(docker inspect --format='{{.Id}}' ghcr.io/<your-username>/open-webui-next:slim)

if [ "$OLD_ID" != "$NEW_ID" ]; then
  echo "New image available, updating..."

  # 3. 备份当前容器配置
  docker inspect open-webui > /backup/open-webui-config-$(date +%Y%m%d).json

  # 4. 停止并删除旧容器
  docker stop open-webui
  docker rm open-webui

  # 5. 启动新容器
  docker run -d \
    --name open-webui \
    --restart unless-stopped \
    -p 8080:8080 \
    --env-file /opt/openwebui/.env \
    -v /data/open-webui/data:/app/backend/data \
    ghcr.io/<your-username>/open-webui-next:slim

  # 6. 清理旧镜像
  docker image prune -f
else
  echo "Already up to date"
fi
```

### 镜像访问故障排查

#### 问题 1: 拉取失败 - 认证错误

```
Error response from daemon: unauthorized: authentication required
```

**解决方案**:
- 检查是否已登录: `docker info | grep Username`
- 重新登录: `docker login ghcr.io -u YOUR_USERNAME`
- 确认 PAT 有 `read:packages` 权限
- 确认仓库可见性（公开/私有）

#### 问题 2: 拉取失败 - 网络超时

```
Error response from daemon: Get https://ghcr.io/v2/: dial tcp: i/o timeout
```

**解决方案**:
```bash
# 检查 DNS 解析
nslookup ghcr.io

# 检查网络连接
ping ghcr.io
curl -I https://ghcr.io

# 配置 Docker 镜像代理（如果在国内服务器）
# /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://mirror.gcr.io"
  ]
}

# 重启 Docker
sudo systemctl restart docker
```

#### 问题 3: 拉取失败 - 镜像不存在

```
Error response from daemon: manifest for ghcr.io/user/repo:slim not found
```

**解决方案**:
- 确认镜像名称和标签拼写正确
- 检查 GitHub Actions 构建是否成功
- 查看仓库 Packages 页面确认镜像已发布
- 使用 `docker search ghcr.io/<your-username>` 搜索可用镜像

#### 问题 4: 权限不足

```
Error response from daemon: pull access denied for ghcr.io/user/repo
```

**解决方案**:
- 确认 GitHub 用户有仓库访问权限
- 如果是组织仓库，确认用户在组织中
- 管理员在仓库 Settings → Actions → General → Workflow permissions 中启用 "Read and write permissions"

---

## 前置准备

### 1. MySQL 数据库准备

在您的 MySQL 服务器上创建数据库和用户：

```sql
-- 创建数据库
CREATE DATABASE openwebui CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户并授权（替换密码）
CREATE USER 'openwebui'@'%' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON openwebui.* TO 'openwebui'@'%';
FLUSH PRIVILEGES;

-- 验证创建
SHOW DATABASES LIKE 'openwebui';
SELECT User, Host FROM mysql.user WHERE User = 'openwebui';
```

**安全建议**:
- 生产环境使用强密码（至少 16 位，包含大小写字母、数字、特殊字符）
- 如果 MySQL 和 Docker 在同一网络，限制 `Host` 为具体 IP 而非 `%`
- 启用 MySQL SSL 连接（见高级配置）

### 2. 网络连通性检查

确保 Docker 容器可以访问 MySQL 服务器：

```bash
# 在 Docker 宿主机测试 MySQL 连接
mysql -h <mysql_host> -P 3306 -u openwebui -p

# 或使用 telnet 测试端口
telnet <mysql_host> 3306
```

### 3. 数据持久化目录

创建用于挂载的数据目录：

```bash
mkdir -p /data/open-webui/data
chmod 755 /data/open-webui/data
```

---

## 快速开始

### 方式一：使用环境变量（推荐）

```bash
docker run -d \
  --name open-webui \
  --restart unless-stopped \
  -p 8080:8080 \
  -e DATABASE_URL="mysql://openwebui:your_secure_password@mysql.example.com:3306/openwebui" \
  -v /data/open-webui/data:/app/backend/data \
  ghcr.io/<your-username>/open-webui-next:slim
```

### 方式二：使用分离的数据库环境变量

```bash
docker run -d \
  --name open-webui \
  --restart unless-stopped \
  -p 8080:8080 \
  -e DATABASE_TYPE="mysql" \
  -e DATABASE_HOST="mysql.example.com" \
  -e DATABASE_PORT="3306" \
  -e DATABASE_NAME="openwebui" \
  -e DATABASE_USER="openwebui" \
  -e DATABASE_PASSWORD="your_secure_password" \
  -v /data/open-webui/data:/app/backend/data \
  ghcr.io/<your-username>/open-webui-next:slim
```

### 方式三：使用 .env 文件（推荐生产环境）

创建 `.env` 文件：

```bash
# .env
DATABASE_URL=mysql://openwebui:your_secure_password@mysql.example.com:3306/openwebui
WEBUI_NAME=Open WebUI Production
WEBUI_SECRET_KEY=your_random_secret_key_here
```

运行容器：

```bash
docker run -d \
  --name open-webui \
  --restart unless-stopped \
  -p 8080:8080 \
  --env-file .env \
  -v /data/open-webui/data:/app/backend/data \
  ghcr.io/<your-username>/open-webui-next:slim
```

---

## MySQL 数据库配置

### 数据库连接方式

#### 选项 1: 使用完整 DATABASE_URL（推荐）

```bash
# 标准 MySQL 连接
DATABASE_URL=mysql://username:password@host:port/database

# 带参数的连接（UTF-8 编码）
DATABASE_URL=mysql://username:password@host:port/database?charset=utf8mb4

# MySQL 8.0+ 使用 PyMySQL 驱动
DATABASE_URL=mysql+pymysql://username:password@host:port/database

# SSL 连接
DATABASE_URL=mysql://username:password@host:port/database?ssl=true
```

#### 选项 2: 使用分离的环境变量

```bash
DATABASE_TYPE=mysql          # 数据库类型
DATABASE_HOST=mysql.example.com  # 主机地址
DATABASE_PORT=3306           # 端口
DATABASE_NAME=openwebui      # 数据库名
DATABASE_USER=openwebui      # 用户名
DATABASE_PASSWORD=password   # 密码
```

### 支持的数据库类型

| 数据库 | DATABASE_TYPE | 驱动 | 示例 URL |
|--------|---------------|------|----------|
| MySQL 5.7+ | `mysql` | mysqlclient | `mysql://user:pass@host/db` |
| MySQL 8.0+ | `mysql+pymysql` | pymysql | `mysql+pymysql://user:pass@host/db` |
| PostgreSQL | `postgresql` | psycopg2 | `postgresql://user:pass@host/db` |
| SQLite | `sqlite` | 内置 | `sqlite:///path/to/db.db` |

### 数据库性能优化

#### 连接池配置

```bash
# 连接池大小（默认：10）
DATABASE_POOL_SIZE=20

# 最大溢出连接数（默认：0）
DATABASE_POOL_MAX_OVERFLOW=10

# 连接回收时间（秒，防止断线）
DATABASE_POOL_RECYCLE=3600

# 连接超时时间（秒）
DATABASE_CONNECT_TIMEOUT=10
```

#### MySQL 特定优化

在 MySQL 服务器配置文件 `my.cnf` 中：

```ini
[mysqld]
# 连接数限制
max_connections = 500

# InnoDB 缓冲池大小（推荐物理内存的 50-70%）
innodb_buffer_pool_size = 2G

# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# 二进制日志（用于备份和恢复）
log_bin = /var/log/mysql/mysql-bin.log
expire_logs_days = 7
```

---

## 环境变量完整列表

### 数据库配置

| 环境变量 | 说明 | 默认值 | 示例 |
|---------|------|--------|------|
| `DATABASE_URL` | 完整数据库连接 URL | `sqlite:///{DATA_DIR}/webui.db` | `mysql://user:pass@host/db` |
| `DATABASE_TYPE` | 数据库类型 | - | `mysql`, `postgresql` |
| `DATABASE_HOST` | 数据库主机 | - | `mysql.example.com` |
| `DATABASE_PORT` | 数据库端口 | - | `3306` |
| `DATABASE_NAME` | 数据库名称 | - | `openwebui` |
| `DATABASE_USER` | 数据库用户名 | - | `openwebui` |
| `DATABASE_PASSWORD` | 数据库密码 | - | `password` |
| `DATABASE_SCHEMA` | 数据库 Schema | - | `public` |
| `DATABASE_POOL_SIZE` | 连接池大小 | `10` | `20` |
| `DATABASE_POOL_MAX_OVERFLOW` | 最大溢出连接 | `0` | `10` |

### 应用基础配置

| 环境变量 | 说明 | 默认值 | 示例 |
|---------|------|--------|------|
| `WEBUI_NAME` | 应用名称 | `Open WebUI` | `My AI Platform` |
| `WEBUI_URL` | 外部访问 URL | `http://localhost:8080` | `https://ai.example.com` |
| `WEBUI_SECRET_KEY` | JWT 密钥（必须设置） | 自动生成 | 随机字符串 |
| `PORT` | 服务端口 | `8080` | `8080` |
| `HOST` | 监听地址 | `0.0.0.0` | `0.0.0.0` |
| `DATA_DIR` | 数据目录 | `/app/backend/data` | - |

### 认证与安全

| 环境变量 | 说明 | 默认值 | 示例 |
|---------|------|--------|------|
| `WEBUI_AUTH` | 启用认证 | `true` | `true`, `false` |
| `WEBUI_AUTH_TRUSTED_EMAIL_HEADER` | 信任的邮箱 Header | - | `X-User-Email` |
| `DEFAULT_USER_ROLE` | 默认用户角色 | `pending` | `user`, `admin` |
| `ENABLE_SIGNUP` | 允许注册 | `true` | `true`, `false` |
| `JWT_EXPIRES_IN` | JWT 过期时间 | `30d` | `7d`, `24h` |

### LLM 提供商配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `OPENAI_API_BASE_URL` | OpenAI API 基础 URL | `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://localhost:11434` |
| `ANTHROPIC_API_KEY` | Claude API 密钥 | - |
| `GOOGLE_API_KEY` | Gemini API 密钥 | - |

### RAG（向量数据库）配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `VECTOR_DB` | 向量数据库类型 | `chroma` |
| `CHROMA_DATA_PATH` | ChromaDB 数据路径 | `{DATA_DIR}/vector_db` |
| `QDRANT_URI` | Qdrant 连接地址 | - |
| `OPENSEARCH_URI` | OpenSearch 连接地址 | - |

### 日志配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `GLOBAL_LOG_LEVEL` | 全局日志级别 | `INFO` |
| `LOG_LEVEL` | 应用日志级别 | `INFO` |
| `UVICORN_LOG_LEVEL` | Uvicorn 日志级别 | `info` |

---

## 高级配置

### 1. 使用 Docker Compose（推荐）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  open-webui:
    image: ghcr.io/<your-username>/open-webui-next:slim
    container_name: open-webui
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      # 数据库配置
      DATABASE_URL: mysql://openwebui:${DB_PASSWORD}@mysql.example.com:3306/openwebui

      # 应用配置
      WEBUI_NAME: "Open WebUI Production"
      WEBUI_SECRET_KEY: ${WEBUI_SECRET_KEY}
      WEBUI_URL: https://ai.example.com

      # 认证配置
      ENABLE_SIGNUP: "false"
      DEFAULT_USER_ROLE: "pending"

      # LLM 配置
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OLLAMA_BASE_URL: http://ollama:11434

      # 日志配置
      GLOBAL_LOG_LEVEL: INFO

    volumes:
      - /data/open-webui/data:/app/backend/data

    # 健康检查
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    # 资源限制
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  # 可选：如果需要在同一网络部署 Ollama
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    volumes:
      - /data/ollama:/root/.ollama
    deploy:
      resources:
        limits:
          memory: 8G
```

创建 `.env` 文件（不要提交到 Git）：

```bash
# .env
DB_PASSWORD=your_secure_mysql_password
WEBUI_SECRET_KEY=your_random_secret_key_here
OPENAI_API_KEY=sk-your-openai-key
```

启动服务：

```bash
docker-compose up -d
```

### 2. MySQL SSL 连接

如果 MySQL 启用了 SSL，配置连接：

```bash
# 方式 1: 在 DATABASE_URL 中指定
DATABASE_URL="mysql://user:pass@host/db?ssl=true&ssl_ca=/path/to/ca-cert.pem"

# 方式 2: 使用环境变量
DATABASE_SSL=true
DATABASE_SSL_CA=/path/to/ca-cert.pem
DATABASE_SSL_CERT=/path/to/client-cert.pem
DATABASE_SSL_KEY=/path/to/client-key.pem
```

挂载证书到容器：

```bash
docker run -d \
  -v /path/to/certs:/certs:ro \
  -e DATABASE_URL="mysql://user:pass@host/db?ssl_ca=/certs/ca-cert.pem" \
  ghcr.io/<your-username>/open-webui-next:slim
```

### 3. 反向代理（Nginx）

生产环境推荐在 Docker 前配置 Nginx 反向代理：

```nginx
# /etc/nginx/sites-available/openwebui
upstream open_webui {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name ai.example.com;

    # HTTPS 重定向
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai.example.com;

    # SSL 证书
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 日志
    access_log /var/log/nginx/openwebui_access.log;
    error_log /var/log/nginx/openwebui_error.log;

    # 客户端最大请求体大小（上传文件）
    client_max_body_size 100M;

    location / {
        proxy_pass http://open_webui;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（用于实时聊天）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/openwebui /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. 数据备份策略

#### MySQL 数据库备份

```bash
#!/bin/bash
# backup-mysql.sh

BACKUP_DIR="/backup/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/openwebui_$DATE.sql.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
mysqldump -h mysql.example.com -u openwebui -p openwebui | gzip > $BACKUP_FILE

# 删除 7 天前的备份
find $BACKUP_DIR -name "openwebui_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

设置 cron 定时任务：

```bash
# 每天凌晨 2 点备份
0 2 * * * /path/to/backup-mysql.sh
```

#### 数据目录备份

```bash
#!/bin/bash
# backup-data.sh

BACKUP_DIR="/backup/openwebui"
DATE=$(date +%Y%m%d_%H%M%S)
DATA_DIR="/data/open-webui/data"

mkdir -p $BACKUP_DIR

# 备份数据目录（包含上传的文件、模型等）
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" -C "$DATA_DIR" .

# 删除 30 天前的备份
find $BACKUP_DIR -name "data_*.tar.gz" -mtime +30 -delete

echo "Data backup completed: $BACKUP_DIR/data_$DATE.tar.gz"
```

### 5. 监控与告警

#### 健康检查脚本

```bash
#!/bin/bash
# healthcheck.sh

HEALTH_URL="http://localhost:8080/health"
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

    if [ $HTTP_CODE -eq 200 ]; then
        echo "Health check passed"
        exit 0
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 5
done

echo "Health check failed after $MAX_RETRIES retries"
exit 1
```

#### Docker 健康检查

在 `docker-compose.yml` 中已配置健康检查：

```bash
# 查看健康状态
docker ps | grep open-webui

# 查看健康检查日志
docker inspect --format='{{json .State.Health}}' open-webui | jq
```

---

## 故障排查

### 1. 数据库连接失败

**症状**: 容器启动后立即退出，日志显示数据库连接错误

**排查步骤**:

```bash
# 查看容器日志
docker logs open-webui

# 进入容器测试数据库连接
docker exec -it open-webui bash
apt-get update && apt-get install -y mysql-client
mysql -h mysql.example.com -u openwebui -p
```

**常见问题**:
- ✅ 确认 MySQL 用户权限：`GRANT ALL PRIVILEGES ON openwebui.* TO 'openwebui'@'%'`
- ✅ 确认防火墙规则：允许 Docker 容器 IP 访问 MySQL 3306 端口
- ✅ 确认 `DATABASE_URL` 格式正确
- ✅ 如果使用 MySQL 8.0，尝试 `mysql+pymysql://` 驱动

### 2. 模型下载失败（Slim 镜像首次运行）

**症状**: 应用启动缓慢，日志显示模型下载错误

**解决方案**:

```bash
# 方式 1: 预先下载模型到挂载目录
# 在宿主机上执行
mkdir -p /data/open-webui/data/cache
cd /data/open-webui/data/cache

# 下载 sentence-transformers 模型
wget https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/pytorch_model.bin

# 方式 2: 设置 HuggingFace 镜像
docker run -d \
  -e HF_ENDPOINT=https://hf-mirror.com \
  ...
```

### 3. 容器内存不足

**症状**: 容器频繁重启，日志显示 OOM (Out of Memory)

**解决方案**:

```bash
# 限制容器内存使用
docker run -d \
  --memory="4g" \
  --memory-swap="4g" \
  ...

# 或在 docker-compose.yml 中配置资源限制（见高级配置）
```

### 4. 文件上传失败

**症状**: 上传大文件时出现 413 错误

**解决方案**:

```bash
# 如果使用 Nginx 反向代理，增加上传大小限制
# /etc/nginx/nginx.conf
http {
    client_max_body_size 100M;
}

# 重启 Nginx
sudo systemctl reload nginx
```

### 5. WebSocket 连接断开

**症状**: 实时聊天功能不工作，日志显示 WebSocket 错误

**解决方案**:

检查 Nginx 配置是否支持 WebSocket：

```nginx
location / {
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    ...
}
```

### 6. 数据库迁移错误

**症状**: 从 SQLite 迁移到 MySQL 后数据丢失

**解决方案**:

Open WebUI 不支持自动数据迁移，需要手动导出导入：

```bash
# 1. 从旧容器导出数据（使用 SQLite）
docker exec old-container python -m open_webui.utils.export_data > data.json

# 2. 启动新容器（使用 MySQL）
docker run -d \
  -e DATABASE_URL=mysql://... \
  --name new-container \
  ghcr.io/<your-username>/open-webui-next:slim

# 3. 导入数据
docker exec -i new-container python -m open_webui.utils.import_data < data.json
```

---

## 维护操作

### 更新镜像

```bash
# 拉取最新镜像
docker pull ghcr.io/<your-username>/open-webui-next:slim

# 停止并删除旧容器
docker stop open-webui
docker rm open-webui

# 启动新容器（数据卷保留）
docker run -d \
  --name open-webui \
  ... # 相同参数
  ghcr.io/<your-username>/open-webui-next:slim
```

### 查看日志

```bash
# 实时查看日志
docker logs -f open-webui

# 查看最近 100 行日志
docker logs --tail 100 open-webui

# 查看特定时间范围日志
docker logs --since "2024-01-01T00:00:00" open-webui
```

### 进入容器调试

```bash
# 进入容器 bash
docker exec -it open-webui bash

# 查看环境变量
docker exec open-webui env

# 查看进程
docker exec open-webui ps aux
```

---

## 安全建议

1. **不要在 DATABASE_URL 中明文暴露密码**
   - 使用 Docker secrets 或环境变量文件
   - `.env` 文件添加到 `.gitignore`

2. **定期更新镜像**
   - 订阅 GitHub 仓库 Release 通知
   - 定期执行 `docker pull` 更新

3. **限制容器权限**
   ```bash
   docker run -d \
     --security-opt=no-new-privileges \
     --cap-drop=ALL \
     --read-only \
     --tmpfs /tmp \
     ...
   ```

4. **使用 HTTPS**
   - 生产环境必须使用 HTTPS（Nginx + Let's Encrypt）
   - 设置 `WEBUI_URL=https://...`

5. **禁用不必要的功能**
   ```bash
   -e ENABLE_SIGNUP=false  # 禁止公开注册
   -e ENABLE_API_KEY=true  # 启用 API Key 认证
   ```

---

## 性能优化建议

### 1. 数据库优化

- 使用 MySQL 8.0+ 以获得更好性能
- 启用 InnoDB 缓冲池：`innodb_buffer_pool_size = 2G`
- 定期执行 `OPTIMIZE TABLE` 优化表

### 2. 应用优化

```bash
# 增加 Worker 数量（根据 CPU 核心数）
-e UVICORN_WORKERS=4

# 增加数据库连接池
-e DATABASE_POOL_SIZE=20
-e DATABASE_POOL_MAX_OVERFLOW=10
```

### 3. 缓存优化

```bash
# 启用 Redis 缓存（可选）
-e REDIS_URL=redis://redis:6379/0

# 增加 AI 模型缓存
-v /data/open-webui/cache:/root/.cache
```

---

## 联系与支持

- **文档**: 项目 README.md 和 CLAUDE.md
- **问题反馈**: GitHub Issues
- **社区讨论**: GitHub Discussions

---

**最后更新**: 2024-11-14
