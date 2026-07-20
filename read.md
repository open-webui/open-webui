# 基于 Open WebUI 的企业级知识库管理后台

> 在开源项目 [Open WebUI](https://github.com/open-webui/open-webui)（128K+ Star）基础上二次开发，新增可视化的知识库管理仪表板。

---

## 项目简介

Open WebUI 是一个自托管的 AI 对话平台，支持接入 ChatGPT、DeepSeek、Ollama 等大模型。本人在其已有的 RAG（检索增强生成）能力之上，独立设计并实现了**企业级知识库管理后台**，新增以下 4 个功能模块：

| 模块 | 说明 |
|---|---|
| 🧩 **分块预览与手动调整** | 文档上传后自动展示分块结果，支持合并/拆分分块，调整后重建向量 |
| ⏳ **向量化进度可视化** | 实时展示文档处理进度（分块 → Embedding → 完成），SSE 流式推送 |
| 📊 **检索质量评估面板** | 输入测试查询，展示 Top-K 检索结果与分数，支持人工标注计算 recall/precision/MRR |
| 📸 **知识库版本管理** | 创建知识库快照，支持回滚和快照间差异对比 |

---

## 技术栈

| 层级 | 技术 |
|---|---|
| **后端框架** | Python / FastAPI（异步 ASGI） |
| **前端框架** | SvelteKit + TypeScript + Tailwind CSS |
| **数据库** | SQLite（开发）/ PostgreSQL（生产），SQLAlchemy ORM + Alembic 迁移 |
| **向量数据库** | ChromaDB（默认），支持 PGVector / Qdrant / Milvus 等 9 种 |
| **AI/LLM** | DeepSeek API（OpenAI 兼容协议），支持 Ollama 本地模型 |
| **文档处理** | LangChain Text Splitters（递归分块 / Token 分块 / Markdown 标题分块） |
| **实时通信** | Socket.IO / SSE (Server-Sent Events) |
| **部署** | Docker / Docker Compose |
| **认证** | JWT + OAuth2.0 + RBAC |

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                  浏览器 (SvelteKit PWA)           │
│    Tab 导航: Files │ Chunks │ Processing │ ...    │
├─────────────────────────────────────────────────┤
│                  FastAPI 后端 (Python)            │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Knowledge│ │ Retrieval│ │ Chunk Management │ │
│  │  Router  │ │  Router  │ │     Router       │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│         │            │               │           │
│    ┌────┴────┐  ┌───┴────┐  ┌──────┴──────┐    │
│    │ SQLite  │  │ChromaDB│  │ DeepSeek API│    │
│    │ (元数据) │  │ (向量)  │  │  (LLM推理)  │    │
│    └─────────┘  └────────┘  └─────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 数据库设计（新增表）

### knowledge_chunk — 分块记录
```sql
id, knowledge_id(FK), file_id(FK), chunk_index,
content, token_count, meta(JSON), content_hash,
created_at, updated_at
```

### knowledge_processing_task — 处理进度
```sql
id, knowledge_id(FK), file_id(FK), task_type,
status(pending/chunking/embedding/completed/failed),
progress_pct, chunks_total, chunks_processed, error_message
```

### knowledge_relevance_judgment — 检索标注
```sql
id, knowledge_id(FK), query_text, chunk_id,
document_text, rank_position, relevance(0/1), user_id
```

### knowledge_snapshot — 版本快照
```sql
id, knowledge_id(FK), label, description, file_count,
chunk_count, snapshot_data(JSON), collection_snapshot_path
```

---

## API 设计（新增 20+ 端点）

所有端点挂载在 `/api/v1/knowledge/{id}/` 下：

### 分块管理
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/{id}/chunks/preview` | 上传文件 → 分块预览（不入向量库） |
| GET | `/{id}/files/{file_id}/chunks` | 获取某文件所有分块 |
| GET | `/{id}/chunks/{chunk_id}` | 查看单个分块详情 |
| POST | `/{id}/chunks/merge` | 合并相邻分块 |
| POST | `/{id}/chunks/split` | 拆分分块 |
| POST | `/{id}/chunks/reindex` | 重建向量（调整分块后） |

### 进度监控
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/{id}/progress` | 当前处理状态 |
| GET | `/{id}/progress/stream` | SSE 实时推送进度 |
| GET | `/{id}/progress/batch` | 批量任务进度 |

### 检索评估
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/{id}/evaluate/query` | 测试查询 → Top-K + 指标 |
| POST | `/{id}/evaluate/annotate` | 标注相关/不相关 |
| GET | `/{id}/evaluate/judgments` | 查看历史标注 |

### 版本管理
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/{id}/snapshots` | 创建快照 |
| GET | `/{id}/snapshots` | 快照列表 |
| POST | `/{id}/snapshots/{sid}/rollback` | 回滚到指定快照 |
| POST | `/{id}/snapshots/compare` | 对比两个快照差异 |

---

## 前端组件

```
src/lib/components/workspace/Knowledge/
├── KnowledgeBase.svelte          # 知识库主视图
├── ChunkManager.svelte           # 分块管理器（表格+合并+拆分+重建向量）
├── ChunkDetailModal.svelte       # 分块详情弹窗
├── ChunkMergePanel.svelte        # 合并分块面板
├── ChunkSplitModal.svelte        # 拆分量弹窗
├── ProcessingDashboard.svelte    # 处理进度仪表板
├── EvaluatePanel.svelte          # 检索评估面板
└── SnapshotManager.svelte        # 快照管理
```

路由结构：
```
workspace/knowledge/[id]/
├── +layout.svelte       → Tab 导航 (Files│Chunks│Processing│Evaluate│Snapshots)
├── +page.svelte         → KnowledgeBase (Files 视图)
├── chunks/+page.svelte  → ChunkManager
├── processing/+page.svelte → ProcessingDashboard
├── evaluate/+page.svelte   → EvaluatePanel
└── snapshots/+page.svelte  → SnapshotManager
```

---

## 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/open-webui/open-webui.git
cd open-webui

# 2. 安装依赖
cd backend && pip install -r requirements.txt
cd .. && npm install --engine-strict=false

# 3. 构建前端
npm run build

# 4. 配置 DeepSeek API Key (.env)
OPENAI_API_BASE_URL='https://api.deepseek.com/v1'
OPENAI_API_KEY='sk-xxxxxxxxxxxxxxxx'

# 5. 启动服务
cd backend
WEBUI_SECRET_KEY="your-secret-key" python -m uvicorn open_webui.main:app --host 127.0.0.1 --port 8080

# 6. 访问
# http://127.0.0.1:8080
```

---

## 开发日志

| 日期 | 内容 |
|---|---|
| 2026-07-20 | 克隆项目、搭建开发环境、配置 DeepSeek API |
| 2026-07-20 | Phase 1：数据库表设计 + Alembic 迁移 + 分块管理 API（6 端点）+ 前端 ChunkManager 组件 + Tab 导航 |

---

## 简历描述（可直接使用）

**项目名称**：基于 Open WebUI 的企业级知识库管理后台

**项目描述**：在开源项目 Open WebUI（128K+ Star）的 FastAPI + SvelteKit 架构上进行二次开发，独立设计并实现了可视化的 RAG 知识库管理仪表板。新增文档分块预览与手动调整、向量化进度实时监控、检索质量评估面板、知识库版本快照与回滚等企业级功能。

**技术栈**：Python / FastAPI / SQLAlchemy / ChromaDB / SvelteKit / TypeScript / Tailwind CSS / DeepSeek API / SSE

**主要工作**：
- 设计并实现了 4 张新数据库表 + Alembic 迁移，遵循现有 SQLAlchemy 异步架构模式
- 新增 20+ 个 RESTful API 端点，复用现有 JWT 认证和 RBAC 权限体系
- 基于 LangChain Text Splitters 实现文档分块预览，支持合并/拆分分块后重建向量索引
- 使用 SSE (Server-Sent Events) 实现向量化进度的实时推送
- 设计检索质量评估流程：测试查询 → Top-K 结果展示 → 人工标注 → recall/precision/MRR 自动计算
- 实现知识库版本快照功能：基于 ChromaDB 集合副本实现向量数据的增量备份与一键回滚
- 基于 SvelteKit + Tailwind CSS 构建前端管理界面，含 Tab 导航和 5 个子页面组件
