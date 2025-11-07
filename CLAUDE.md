# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open WebUI 是一个功能丰富的自托管 AI 平台,支持完全离线运行。核心技术栈:
- **前端**: SvelteKit 4 + TypeScript + Vite 5 + Tailwind CSS 4
- **后端**: Python 3.11 + FastAPI + SQLAlchemy
- **部署**: Docker 多阶段构建,生产环境前后端同容器运行

## Common Development Commands

### 前端开发
```bash
npm run dev              # Vite dev server on http://localhost:5173
npm run dev:5050         # Vite dev server on http://localhost:5050
npm run build            # 构建生产版本到 build/
npm run build:watch      # 监听模式构建
```

### 后端开发
```bash
cd backend
python -m uvicorn open_webui.main:app --reload --port 8080
```

### 测试与质量
```bash
npm run test:frontend    # Vitest 单元测试
npm run cy:open          # Cypress E2E 测试
npm run lint             # 前端 + 类型 + 后端检查
npm run format           # Prettier 格式化前端
npm run format:backend   # Black 格式化后端
```

### i18n
```bash
npm run i18n:parse       # 解析翻译字符串并格式化
```

## Architecture Key Points

### 前后端架构分离
- **开发模式**: 前端 Vite Dev Server (5050) + 后端 FastAPI (8080) 分离运行
- **生产模式**: FastAPI (8080) 同时服务 API 和静态文件 (SvelteKit 构建产物)
- **SPA 模式**: 使用 `@sveltejs/adapter-static`,所有路由回退到 `index.html`

### 目录结构要点

#### 前端核心 (`/src`)
- **`routes/`**: SvelteKit 基于文件系统的路由
  - `(app)/`: 需要认证的主应用路由 (聊天、管理、工作区)
  - `auth/`: 认证页面
  - `s/[id]/`: 分享页面
- **`lib/apis/`**: API 客户端模块,按功能拆分 (26+ 模块)
- **`lib/components/`**: Svelte 组件库,按功能组织 (chat/, admin/, workspace/, common/, icons/)
- **`lib/stores/`**: Svelte Stores 全局状态管理
- **`lib/i18n/`**: 国际化,支持 59+ 语言
- **`lib/workers/`**: Web Workers (Pyodide 等)

#### 后端核心 (`/backend/open_webui`)
- **`main.py`**: FastAPI 应用入口
- **`routers/`**: API 路由 (20+ 路由器),按功能模块拆分
  - 认证 (JWT/OAuth/LDAP), 聊天, 模型, 知识库 (RAG), 函数/工具, 文件, 图像/音频等
- **`models/`**: SQLAlchemy 数据模型 (17+ 模型)
- **`utils/`**: 工具模块 (认证, 访问控制, 嵌入, 插件等)
- **`retrieval/`**: RAG 检索系统 (向量数据库, 文档加载器, 检索模型)
- **`socket/`**: Socket.IO 实时通信服务
- **`migrations/`**: Alembic 数据库迁移

### 关键设计模式

1. **API 客户端组织**: 前端 `/src/lib/apis/` 按功能模块拆分,每个模块负责一组相关 API
2. **路由组织**: SvelteKit 使用分组路由 `(app)/` 来区分需要认证的页面
3. **状态管理**: Svelte Stores 集中管理全局状态 (user, config, models, chats, settings)
4. **实时通信**: Socket.IO 用于用户在线状态、模型使用监控、通知
5. **插件系统**: Pipeline 插件框架允许注入自定义 Python 逻辑
6. **RAG 架构**: 内置文档检索增强生成系统,支持多种向量数据库 (ChromaDB/OpenSearch/Qdrant/Milvus)
7. **RBAC**: 基于角色的访问控制 (admin/user/pending) + 用户组权限
8. **多 LLM 支持**: 统一接口支持 Ollama, OpenAI, Claude, Gemini 等

### 数据流
```
用户请求 → SvelteKit 前端
    ↓
API Client ($lib/apis)
    ↓
FastAPI Router (backend/routers)
    ↓
Business Logic (utils, models)
    ↓
Database / Vector DB / Redis
    ↓
LLM Provider / RAG Engine
    ↓
响应 → 前端渲染 / Stream
```

## Development Notes

### 前端开发要点
- 新增页面: 在 `/src/routes` 下创建 `+page.svelte`,SvelteKit 自动生成路由
- 新增 API 调用: 在 `/src/lib/apis/` 对应模块添加函数
- 全局状态: 使用 `/src/lib/stores/index.ts` 中的 Stores
- 组件复用: 优先使用 `/src/lib/components/common/` 中的通用组件
- i18n: 翻译字符串写在组件中,运行 `npm run i18n:parse` 自动提取

### 后端开发要点
- 新增 API: 在 `/backend/open_webui/routers/` 对应路由器添加端点
- 数据库迁移: 修改模型后运行 Alembic 生成迁移脚本
- 权限控制: 使用 `utils/auth.py` 和 `utils/access_control.py` 中的装饰器
- 插件扩展: Pipeline 插件放在独立仓库 `open-webui/pipelines`
- 向量检索: RAG 相关逻辑在 `/backend/open_webui/retrieval/`

### 数据库迁移
```bash
cd backend
# 创建迁移脚本
alembic revision --autogenerate -m "description"
# 执行迁移
alembic upgrade head
```

### Docker 构建
```bash
# 标准镜像
docker build -t open-webui .
# CUDA 支持
docker build --build-arg USE_CUDA=true -t open-webui:cuda .
# Ollama 捆绑
docker build -f Dockerfile.ollama -t open-webui:ollama .
```

## Testing

- **前端单元测试**: Vitest (`npm run test:frontend`)
- **E2E 测试**: Cypress (`npm run cy:open`)
- **后端测试**: 位于 `/backend/test/`

## Important Context

- **环境变量**: 前端使用 Vite 的 `import.meta.env`,后端使用 `/backend/open_webui/env.py` 定义的环境变量
- **静态资源**: 前端构建产物复制到 `/backend/open_webui/static/`,由 FastAPI 在生产模式提供服务
- **WebSocket**: Socket.IO 服务器在 `/backend/open_webui/socket/main.py`,前端在 `/src/routes/+layout.svelte` 初始化连接
- **认证流程**: JWT token 存储在 localStorage,API 请求通过 `/src/lib/apis/index.ts` 自动注入 Authorization header
- **Pyodide**: 浏览器内 Python 运行时,脚本在 `/scripts/prepare-pyodide.js` 中预下载
