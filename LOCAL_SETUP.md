# Open WebUI 本地开发环境搭建指南

本指南提供 Open WebUI 项目的本地开发环境配置和运行步骤。

## 系统要求

- **Node.js**: v20.19.5 或更高版本
- **Python**: 3.12.x (推荐使用 pyenv 管理)
- **npm**: 10.8.2 或更高版本
- **操作系统**: macOS / Linux / Windows

## 技术栈

### 前端
- **框架**: SvelteKit 4 + TypeScript
- **构建工具**: Vite 5
- **样式**: Tailwind CSS 4

### 后端
- **语言**: Python 3.12
- **框架**: FastAPI
- **数据库**: SQLite (开发环境) / PostgreSQL (生产环境)
- **ORM**: SQLAlchemy + Peewee

## 环境准备

### 1. 安装 pyenv (如果系统 Python 版本不是 3.12)

```bash
# macOS (使用 Homebrew)
brew install pyenv

# 配置 shell 环境变量 (添加到 ~/.zshrc 或 ~/.bash_profile)
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
```

### 2. 安装 Python 3.12

```bash
# 使用 pyenv 安装 Python 3.12
pyenv install 3.12

# 验证安装
pyenv versions
```

## 安装依赖

### 前端依赖

```bash
# 在项目根目录执行
npm install --legacy-peer-deps
```

**注意**: 需要使用 `--legacy-peer-deps` 标志来解决 @tiptap 包的版本冲突问题。

### 后端依赖

```bash
# 进入后端目录
cd backend

# 创建 Python 3.12 虚拟环境
/Users/你的用户名/.pyenv/versions/3.12.12/bin/python3 -m venv venv

# 或者,如果系统 Python 已是 3.12
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
- 运行数据库迁移 (Alembic)
- 初始化 SQLite 数据库
- 配置向量数据库 (ChromaDB)

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

# 数据库迁移
cd backend
alembic revision --autogenerate -m "描述"  # 生成迁移脚本
alembic upgrade head                       # 执行迁移
```

### 热重载

- **前端**: Vite 自动检测文件变化并热重载
- **后端**: uvicorn 的 `--reload` 参数自动检测 Python 代码变化并重启

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
# 删除数据库重新初始化 (仅开发环境)
rm backend/data/webui.db
python -m uvicorn open_webui.main:app --reload --port 8080
```

## 环境变量配置

后端可通过环境变量配置,创建 `backend/.env` 文件:

```bash
# 数据库
DATABASE_URL=sqlite:///data/webui.db

# 向量数据库
VECTOR_DB=chroma
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# CORS (开发环境)
CORS_ALLOW_ORIGIN=*

# 日志级别
LOG_LEVEL=INFO
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

- **项目文档**: [CLAUDE.md](./CLAUDE.md)
- **API 文档**: http://localhost:8080/docs (启动后端后访问)
- **官方仓库**: https://github.com/open-webui/open-webui

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

**最后更新**: 2025-11-08
