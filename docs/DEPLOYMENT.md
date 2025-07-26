# Emohaa Open WebUI 部署指南

本文档介绍两种部署方法：
1. **方法一**：直接在服务器上构建部署（推荐网络好的情况）
2. **方法二**：本地构建后导出镜像部署（推荐网络受限的情况）

## 目录

- [前置要求](#前置要求)
- [方法一：直接在服务器部署](#方法一直接在服务器部署)
- [方法二：本地构建后部署](#方法二本地构建后部署)
  - [本地构建](#本地构建)
  - [导出镜像](#导出镜像)
  - [传输到服务器](#传输到服务器)
  - [服务器部署](#服务器部署)
- [端口配置](#端口配置)
- [常见问题](#常见问题)

## 前置要求

### 本地环境
- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用磁盘空间

### 服务器环境
- Docker 20.10+
- Docker Compose 2.0+（方法一需要）
- 至少 2GB 可用内存
- 开放端口 3000（或自定义端口）

## 方法一：直接在服务器部署

适用场景：
- 服务器网络状况良好
- 可以直接访问 Docker Hub 和 GitHub
- 希望简化部署流程

### 1. 登录服务器并克隆仓库
```bash
ssh user@your-server-ip
git clone https://github.com/yourusername/emohaa-open-webui.git
cd emohaa-open-webui
```

### 2. 运行构建脚本
```bash
chmod +x run-compose.sh
./run-compose.sh
```

### 3. 验证部署
```bash
# 查看容器状态
docker ps

# 查看日志
docker logs -f emohaa-open-webui

# 访问服务
curl http://localhost:3000
```

服务将在 `http://your-server-ip:3000` 可访问。

## 方法二：本地构建后部署

适用场景：
- 服务器网络受限或无法访问外网
- 需要在多台服务器部署相同镜像
- 希望减少服务器构建时间

### 本地构建

#### 1. 克隆仓库
```bash
git clone https://github.com/yourusername/emohaa-open-webui.git
cd emohaa-open-webui
```

#### 2. 构建镜像

**选项 A：直接使用 Docker build（推荐）**
```bash
# 构建镜像（使用本地 Dockerfile）
docker build -t emohaa-open-webui:latest .

# 或者为了与 run_docker.sh 兼容，使用官方镜像名
docker build -t emohaa-open-webui:main .
```

**选项 B：使用 Docker Compose（如果直接 build 失败）**
```bash
# Docker Compose 提供了更好的网络处理和依赖管理
# 注意：这会同时启动容器
./run-compose.sh

# 如果只想构建不启动，使用：
docker-compose build
```

> **说明**：Docker Compose 在处理网络代理、镜像拉取重试等方面更加稳定。如果直接 `docker build` 遇到网络问题，建议使用 Docker Compose。

#### 3. 验证镜像
```bash
# 查看构建的镜像
docker images | grep open-webui
```

## 导出镜像

### 使用导出脚本（推荐）

**步骤：**
1. **确保脚本有执行权限**
```bash
chmod +x export_image.sh
```

2. **运行导出脚本**
```bash
./export_image.sh
```

**脚本功能：**
- 自动检查镜像 `emohaa-open-webui:main` 是否存在
- 导出并压缩镜像为 `emohaa-open-webui.tar.gz`
- 显示文件大小和后续步骤提示

### 手动导出（可选）
```bash
# 查看镜像
docker images | grep open-webui

# 导出镜像
docker save emohaa-open-webui:main | gzip > emohaa-open-webui.tar.gz
```

## 传输到服务器

### 1. 使用 SCP 传输
```bash
scp emohaa-open-webui.tar.gz user@your-server-ip:/home/user/
```

### 2. 使用 rsync（大文件推荐）
```bash
rsync -avz --progress emohaa-open-webui.tar.gz user@your-server-ip:/home/user/
```

### 3. 分片传输（网络不稳定时）
```bash
# 分片
split -b 100M emohaa-open-webui.tar.gz emohaa-open-webui.tar.gz.part

# 传输
scp emohaa-open-webui.tar.gz.part* user@your-server-ip:/home/user/

# 在服务器上合并
ssh user@your-server-ip
cat emohaa-open-webui.tar.gz.part* > emohaa-open-webui.tar.gz
rm emohaa-open-webui.tar.gz.part*
```

## 服务器部署

### 1. 登录服务器
```bash
ssh user@your-server-ip
```

### 2. 加载镜像
```bash
docker load < emohaa-open-webui.tar.gz
```

### 3. 传输运行脚本到服务器
```bash
scp run_docker.sh user@your-server-ip:/home/user/
```

### 4. 使用脚本运行容器（推荐）

**步骤：**
1. **确保脚本有执行权限**
```bash
chmod +x run_docker.sh
```

2. **运行部署脚本**
```bash
./run_docker.sh
```

**脚本功能：**
- 自动检查镜像 `emohaa-open-webui:main` 是否存在
- 处理已存在的容器（提示是否删除重建）
- 启动容器并显示访问信息
- 提供常用管理命令提示

### 5. 手动运行容器（可选）
```bash
docker run -d \
  --name emohaa-open-webui \
  -p 3000:8080 \
  -v emohaa-open-webui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  --restart always \
  emohaa-open-webui:main
```

## 端口配置

#### 修改端口
编辑 `run_docker.sh` 文件，找到以下行：
```bash
PORT="3000:8080"
```

修改为你需要的端口，例如：
- `PORT="80:8080"` - 使用80端口访问
- `PORT="8888:8080"` - 使用8888端口访问
- `PORT="0.0.0.0:3000:8080"` - 监听所有网络接口的3000端口

**端口格式说明**：
- 格式：`[主机IP:]主机端口:容器端口`
- 左边是主机端口（访问端口）
- 右边是容器内部端口（固定为8080，不要修改）

**示例**：
```bash
# 修改为使用 8080 端口访问
PORT="8080:8080"

# 只监听本地访问
PORT="127.0.0.1:3000:8080"

# 监听所有IP的 80 端口
PORT="0.0.0.0:80:8080"
```

#### 其他配置
- `CONTAINER_NAME`: 修改容器名称
- `VOLUME_NAME`: 修改数据卷名称

## 配置反向代理（推荐）

### Nginx 配置示例
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 常见问题

### Q: 如何修改访问端口？
A: 有两种方法：

**方法1：修改 run_docker.sh（推荐）**
```bash
# 编辑脚本
vi run_docker.sh

# 找到 PORT 配置行
PORT="3000:8080"

# 修改为你需要的端口，例如：
PORT="8888:8080"
```

**方法2：直接运行 docker 命令**
```bash
docker run -d \
  --name emohaa-open-webui \
  -p 8888:8080 \  # 这里修改端口
  -v emohaa-open-webui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  --restart always \
  emohaa-open-webui:main
```

**注意事项**：
- 确保新端口未被占用：`sudo netstat -tlnp | grep 8888`
- 防火墙需要开放对应端口：`sudo ufw allow 8888`
- 如果使用云服务器，需要在安全组中开放端口

### Q: 镜像导出文件太大怎么办？
A: 可以使用更高的压缩级别或分片传输：
```bash
# 最高压缩
docker save emohaa-open-webui:main | gzip -9 > emohaa-open-webui.tar.gz

# 使用 xz 压缩（更小但更慢）
docker save emohaa-open-webui:main | xz -9 > emohaa-open-webui.tar.xz
```

### Q: 该选择哪种部署方法？
A: 根据你的情况选择：

**选择方法一（直接服务器部署）如果：**
- 服务器可以正常访问 GitHub 和 Docker Hub
- 只需要部署到一台服务器
- 希望获取最新的镜像版本

**选择方法二（本地构建后部署）如果：**
- 服务器网络受限或在内网环境
- 需要部署到多台服务器
- 已经在本地测试过镜像
- 想要节省服务器带宽

### Q: 容器启动失败？
A: 检查以下项目：
1. 端口是否被占用：`sudo netstat -tlnp | grep 3000`
2. Docker 日志：`docker logs emohaa-open-webui`
3. 磁盘空间：`df -h`
4. 内存使用：`free -h`

### Q: 如何备份数据？
A: 备份数据卷：
```bash
# 备份
docker run --rm -v emohaa-open-webui:/data -v $(pwd):/backup alpine tar czf /backup/webui-backup.tar.gz -C /data .

# 恢复
docker run --rm -v emohaa-open-webui:/data -v $(pwd):/backup alpine tar xzf /backup/webui-backup.tar.gz -C /data
```

### Q: 如何更新镜像？
A: 在本地重新构建并导出：
```bash
# 本地更新
git pull
./run-compose.sh
./export_image.sh

# 服务器更新
docker stop emohaa-open-webui
docker rm emohaa-open-webui
docker load < emohaa-open-webui.tar.gz
./run_docker.sh
```

### Q: 如何查看容器日志？
A: 使用以下命令：
```bash
# 实时查看
docker logs -f emohaa-open-webui

# 查看最后100行
docker logs --tail 100 emohaa-open-webui

# 查看特定时间段
docker logs --since 1h emohaa-open-webui
```

## 安全建议

1. **使用 HTTPS**: 在生产环境配置 SSL 证书
2. **限制访问**: 使用防火墙限制访问来源
3. **定期备份**: 设置自动备份脚本
4. **监控资源**: 使用监控工具跟踪资源使用
5. **更新镜像**: 定期更新到最新版本

## 技术支持

如遇到问题，请：
1. 查看容器日志：`docker logs emohaa-open-webui`
2. 检查 [GitHub Issues](https://github.com/yourusername/emohaa-open-webui/issues)
3. 提交新的 Issue，包含错误日志和环境信息