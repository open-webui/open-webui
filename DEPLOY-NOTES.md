# 生产部署说明 — Postgres + Redis + 安全硬化

本目录新增 3 个文件(均不影响原有 `docker-compose.yaml`):

| 文件 | 作用 |
|---|---|
| `.env` | 密钥与部署参数(已被 `.gitignore` 忽略,**请单独备份**) |
| `docker-compose.prod.yaml` | postgres + redis + 硬化后的 open-webui |
| `DEPLOY-NOTES.md` | 本文件 |

---

## 启动

```bash
docker compose -f docker-compose.prod.yaml up -d --build
# 看日志确认起来了
docker compose -f docker-compose.prod.yaml logs -f open-webui
```

> 首次会从本地 fork 源码构建镜像(前端+后端),较慢。若你没改代码、想直接拉官方预构建镜像:
> 把 `docker-compose.prod.yaml` 里 open-webui 的 `build:` 三行注释掉,保留 `image:` 即可,然后 `up -d`(去掉 `--build`)。

---

## ⚠️ 三个"硬化副作用",先知道再部署

### 1. 必须走 HTTPS,否则登录不了
已设 `WEBUI_*_COOKIE_SECURE=true` + `SAME_SITE=strict`。浏览器只会在 **https** 下回传 cookie,**用 `http://IP:3000` 直接访问会登录失败**。而且容器端口只绑定在 `127.0.0.1`,公网根本访问不到——这是故意的:**前面必须挂一个 TLS 反向代理**。

最省事用 Caddy(自动签 Let's Encrypt 证书,自动处理 WebSocket):

```caddyfile
# /etc/caddy/Caddyfile
chat.yourdomain.com {
    reverse_proxy 127.0.0.1:3000
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

用 nginx 的话记得加 WebSocket 升级头:
```nginx
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### 2. 这些开关只在"全新数据库首次启动"时按 .env 生效
`ENABLE_SIGNUP` / `DEFAULT_USER_ROLE` / `JWT_EXPIRES_IN` 在代码里是 **PersistentConfig**:首次启动读 env 写入 DB,之后 **env 改了也不生效**,要去 **后台 Admin Settings** 改。
- 我们是全新 postgres,所以首次启动这些值会正确生效(注册关闭、JWT 8h)。
- 想以后"每次重启都强制按 .env 重置"(配置即代码,防漂移):在 compose 里给 open-webui 加
  `ENABLE_PERSISTENT_CONFIG: "false"`。**代价**:后台 UI 里配的模型/连接等也会变成不持久,得全部用 env 管。普通运营不建议开。

### 3. 管理员靠 .env 自动创建,不是靠注册
因为注册已关,首次启动会用 `WEBUI_ADMIN_EMAIL` / `WEBUI_ADMIN_PASSWORD` 自动建管理员。
**部署前先把 `.env` 里的 `WEBUI_ADMIN_EMAIL` 改成你的真实邮箱**,登录后到后台改密码,然后可以把那两行删掉。

---

## 验证 postgres/redis 真的在用

```bash
# 1) 表建在 postgres 里(能列出一堆 open-webui 的表 = 成功)
docker compose -f docker-compose.prod.yaml exec postgres \
  psql -U openwebui -d openwebui -c "\dt" | head

# 2) 数据卷里不应再出现 SQLite 的 webui.db
docker compose -f docker-compose.prod.yaml exec open-webui ls -la /app/backend/data

# 3) Redis 有连接进来(client list 非空 = 令牌吊销/ws 在走 redis)
docker compose -f docker-compose.prod.yaml exec redis \
  redis-cli -a "$REDIS_PASSWORD" client list | head
```

---

## AWS 上的网络收口

安全组只放行 **443**(和你管理用的 22),**不要**对公网开 `3000 / 5432 / 6379`。
本编排已经做到:postgres/redis 不发布端口,open-webui 只绑 `127.0.0.1` —— 公网只能经反向代理(443)进来。

---

## 备份(务必)

```bash
# 数据库
docker compose -f docker-compose.prod.yaml exec postgres \
  pg_dump -U openwebui openwebui | gzip > owui-$(date +%F).sql.gz
```
另外**单独离线备份 `.env`**:`WEBUI_SECRET_KEY` 丢了 = 全员登录态失效、OAuth/加密数据无法解密。

---

## 已有 SQLite 数据要迁移?
本 fork 是全新的,默认直接用 postgres 起即可。若你之前在别处跑过、有 `webui.db` 要保留,迁移不是简单复制(SQLite→Postgres 字段类型不同),需用社区迁移脚本;数据不多时,重建账号 + 重配最稳。
