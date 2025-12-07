# Open WebUI 本地开发环境搭建指南

本指南提供 Open WebUI 项目的本地开发环境配置和运行步骤。

## 系统要求

- **Node.js**: v22.x 或更高版本
- **Python**: 3.11+ / 3.12.x (推荐使用 pyenv 管理)
- **数据库**: PostgreSQL 15+（必需）
- **npm**: 10.8.2 或更高版本
- **操作系统**: macOS / Linux / Windows

## 技术栈

### 前端
- **框架**: SvelteKit 4 + TypeScript
- **构建工具**: Vite 5
- **样式**: Tailwind CSS 4

### 后端
- **语言**: Python 3.11+ / 3.12
- **框架**: FastAPI
- **数据库**: PostgreSQL 15+
- **ORM**: SQLAlchemy
- **迁移工具**: Alembic

## 环境准备

### 1. 安装 Node.js 22

```bash
# macOS (使用 Homebrew)
brew install node@22

# 或使用 nvm
nvm install 22
nvm use 22

# 验证安装
node --version  # 应显示 v22.x.x
npm --version
```

### 2. 安装 PostgreSQL 15+

```bash
# macOS (使用 Homebrew)
brew install postgresql@15
brew services start postgresql@15

# 创建数据库
createdb openwebui_dev

# 验证安装
psql --version  # 应显示 15.x
```

**或者使用 Docker 运行 PostgreSQL**:
```bash
docker run -d \
  --name postgres-openwebui \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=openwebui_dev \
  -p 5432:5432 \
  postgres:15
```

### 3. 安装 Python 3.11/3.12

```bash
# macOS (使用 Homebrew)
brew install python@3.12

# 或使用 pyenv
pyenv install 3.12
pyenv local 3.12

# 验证安装
python3 --version  # 应显示 3.12.x
```

## 安装依赖

### 前端依赖

```bash
# 在项目根目录执行
npm install
```

### 后端依赖

```bash
# 进入后端目录
cd backend

# 创建 Python 虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

## 配置数据库

创建 `backend/.env` 文件:

```bash
# PostgreSQL 连接（必需）
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/openwebui_dev
```

### 初始化数据库

```bash
cd backend
source venv/bin/activate

# 方式1: 启动应用自动迁移 (推荐)
python -m uvicorn open_webui.main:app --reload --port 8080
# 应用启动时会自动执行 alembic upgrade head

# 方式2: 手动执行迁移
cd open_webui
python -m alembic upgrade head
```

## 运行开发服务器

### 启动后端服务 (端口 8080)

```bash
# 在 backend 目录下,激活虚拟环境后
cd backend
source venv/bin/activate
python -m uvicorn open_webui.main:app --reload --port 8080 --host 0.0.0.0
```

后端服务将运行在: **http://localhost:8080**

后端启动时会自动:
- ✅ 运行数据库迁移 (Alembic upgrade head)
- ✅ 初始化数据库表结构
- ✅ 配置向量数据库 (ChromaDB)

### 启动前端服务 (端口 5050)

```bash
# 在项目根目录
npm run dev:5050
```

前端服务将运行在: **http://localhost:5050**

首次启动时会自动:
- 下载 Pyodide 包 (浏览器内 Python 运行时)
- 预加载常用 Python 包 (numpy, pandas, matplotlib 等)

## 访问应用

打开浏览器访问: **http://localhost:5050**

前端会通过 Vite 代理将 API 请求转发到后端 (8080 端口)。

## 开发工作流

### 目录结构

```
open-webui-next/
├── src/                    # 前端源码
│   ├── routes/            # SvelteKit 路由
│   ├── lib/
│   │   ├── apis/         # API 客户端
│   │   ├── components/   # Svelte 组件
│   │   ├── stores/       # 全局状态管理
│   │   └── i18n/         # 国际化
├── backend/               # 后端源码
│   ├── open_webui/
│   │   ├── main.py       # FastAPI 入口
│   │   ├── routers/      # API 路由
│   │   ├── models/       # 数据模型
│   │   ├── utils/        # 工具函数
│   │   └── migrations/   # 数据库迁移
│   ├── requirements.txt
│   └── venv/             # Python 虚拟环境
└── package.json
```

### 常用开发命令

#### 前端

```bash
npm run dev              # 启动开发服务器 (默认端口 5173)
npm run dev:5050         # 启动开发服务器 (端口 5050)
npm run build            # 构建生产版本
npm run lint             # 代码检查
npm run format           # 代码格式化
npm run test:frontend    # 运行单元测试
npm run i18n:parse       # 解析并更新翻译文件
```

#### 后端

```bash
# 在 backend 目录下,激活虚拟环境后

# 启动开发服务器 (自动重载)
python -m uvicorn open_webui.main:app --reload --port 8080

# 代码格式化
black .

# 数据库迁移 (详见下方"数据库迁移管理"章节)
./scripts/migrate.sh current      # 查看当前版本
./scripts/migrate.sh upgrade      # 升级到最新
./scripts/check-status.sh         # 检查一致性
```

### 热重载

- **前端**: Vite 自动检测文件变化并热重载
- **后端**: uvicorn 的 `--reload` 参数自动检测 Python 代码变化并重启

---

## 数据库迁移管理

### 自动迁移机制

**✅ 应用启动时自动执行迁移**

项目已配置自动迁移机制 (`backend/open_webui/config.py`):
- 每次应用启动自动执行 `alembic upgrade head`
- 开发和生产环境使用相同机制
- 幂等性设计，重复执行安全

**这意味着**:
- ✅ 拉取代码后重启应用即可自动同步数据库
- ✅ 无需手动执行迁移命令
- ✅ 开发环境和生产环境数据库始终一致

### 快速命令

```bash
# 查看当前迁移版本
./scripts/migrate.sh current

# 检查数据库与代码一致性
./scripts/check-status.sh

# 查看迁移历史
./scripts/migrate.sh history

# 手动升级 (通常不需要,应用启动会自动执行)
./scripts/migrate.sh upgrade
```

### 创建新迁移

**场景1: 添加新表或字段**

```bash
cd backend/open_webui

# 1. 创建迁移脚本
python -m alembic revision -m "add_user_credits_table"

# 2. 编辑生成的文件
vim migrations/versions/xxxx_add_user_credits_table.py

# 3. 测试迁移
python -m alembic upgrade head     # 升级
python -m alembic downgrade -1     # 降级测试
python -m alembic upgrade head     # 重新升级

# 4. 提交代码
git add migrations/versions/xxxx_add_user_credits_table.py
git commit -m "feat: add user credits table"
```

**场景2: 修改现有表**

```python
# 迁移脚本示例
def upgrade():
    from sqlalchemy.dialects import postgresql

    op.add_column('user',
        sa.Column('balance', postgresql.NUMERIC(20, 6),
                  server_default='0', nullable=False))

def downgrade():
    op.drop_column('user', 'balance')
```

### 多人协作

**处理迁移冲突**:

```bash
# 发现多个 head
python -m alembic heads
# 输出: abc123 (head), def456 (head)

# 合并迁移
python -m alembic merge -m "merge_branches" heads

# 应用合并
python -m alembic upgrade head
```

### 完整指南

详细的 Alembic 使用攻略请参考:
- **[Alembic 使用攻略](./ALEMBIC_GUIDE.md)** - 开发协作和生产环境迁移
- **[数据库一致性保证指南](./DATABASE_CONSISTENCY_GUIDE.md)** - 完整的方案和最佳实践

## 常见问题

### 1. npm install 失败

**问题**: 依赖版本冲突

**解决方案**:
```bash
npm install --legacy-peer-deps
```

### 2. 后端 Python 版本不兼容

**问题**: `unstructured` 包不支持 Python 3.13+

**解决方案**: 使用 Python 3.12:
```bash
pyenv install 3.12
cd backend
rm -rf venv
/Users/你的用户名/.pyenv/versions/3.12.12/bin/python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 端口被占用

**问题**: 8080 或 5050 端口已被使用

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8080
lsof -i :5050

# 终止进程
kill -9 <PID>

# 或者使用不同端口
# 前端:
npm run dev -- --port 3000

# 后端:
python -m uvicorn open_webui.main:app --reload --port 8000
```

### 4. 前端 Pyodide 下载慢

**问题**: 首次启动下载 Pyodide 包较慢

**解决方案**: 耐心等待,包会缓存在 `node_modules` 中,后续启动会很快。

### 5. 数据库迁移错误

**问题**: Alembic 迁移失败

**解决方案**:
```bash
# 删除数据库并重新创建
dropdb openwebui_dev
createdb openwebui_dev

# 重启应用（自动执行迁移）
python -m uvicorn open_webui.main:app --reload --port 8080
```

### 6. PostgreSQL 连接失败

**问题**: 无法连接到 PostgreSQL

**解决方案**:
```bash
# 检查 PostgreSQL 是否运行
brew services list | grep postgresql

# 启动 PostgreSQL
brew services start postgresql@15

# 测试连接
psql -U postgres -d openwebui_dev

# 检查环境变量
cat backend/.env | grep DATABASE_URL
```

## 环境变量配置

创建 `backend/.env` 文件:

```bash
# 数据库（必需 PostgreSQL）
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/openwebui_dev

# 向量数据库
VECTOR_DB=chroma
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# CORS (开发环境)
CORS_ALLOW_ORIGIN=*

# 日志级别
LOG_LEVEL=INFO

# Redis (可选，用于 Session)
# REDIS_URL=redis://localhost:6379/0
```

## 生产部署

生产环境使用 Docker 部署,详见项目根目录的 `Dockerfile` 和 `docker-compose.yaml`。

```bash
# 构建镜像
docker build -t open-webui .

# 运行容器
docker run -d -p 8080:8080 -v open-webui:/app/backend/data open-webui
```

## 更多资源

### 项目文档
- **[CLAUDE.md](./CLAUDE.md)** - 项目架构和开发指南
- **[ALEMBIC_GUIDE.md](./ALEMBIC_GUIDE.md)** - Alembic 使用攻略
- **[DATABASE_CONSISTENCY_GUIDE.md](./DATABASE_CONSISTENCY_GUIDE.md)** - 数据库一致性保证完整方案

### 在线文档
- **API 文档**: http://localhost:8080/docs (启动后端后访问)
- **Swagger UI**: http://localhost:8080/redoc
- **官方仓库**: https://github.com/open-webui/open-webui

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 快速参考

### 启动开发环境

```bash
# 终端1: 启动后端
cd backend
source venv/bin/activate
python -m uvicorn open_webui.main:app --reload --port 8080

# 终端2: 启动前端
npm run dev:5050

# 浏览器访问
# http://localhost:5050
```

### 数据库操作

```bash
# 查看迁移状态
./scripts/check-status.sh

# 查看当前版本
./scripts/migrate.sh current

# 连接数据库
psql -U postgres -d openwebui_dev
```

### 代码格式化

```bash
# 前端
npm run format

# 后端
cd backend
source venv/bin/activate
black .
```

---

**最后更新**: 2025-12-06
**版本**: v2.0 (Node 22 + PostgreSQL)