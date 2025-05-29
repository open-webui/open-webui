# Backend PRD - Open WebUI
# 後端產品需求文檔 - Open WebUI

## Overview
## 概述
The backend of Open WebUI is built with Python and the FastAPI framework. It utilizes SQLAlchemy for ORM interactions and provides a robust API layer for managing AI model interactions, user authentication, file handling, and various AI-related features. The system supports multiple AI providers including Ollama, OpenAI-compatible APIs, and custom model integration.
Open WebUI 的後端使用 Python 和 FastAPI 框架構建。它利用 SQLAlchemy 進行 ORM 交互，並提供了一個強大的 API 層來管理 AI 模型交互、用戶認證、文件處理和各種 AI 相關功能。系統支持多個 AI 提供商，包括 Ollama、OpenAI 兼容的 API 以及自定義模型集成。

## Key Features (from `main.py` and observed modules)
## 關鍵功能 (來自 `main.py` 及觀察到的模組)
```python
# AI Model Integration AI模型集成
ENABLE_OLLAMA_API          # Ollama integration Ollama集成
ENABLE_OPENAI_API         # OpenAI and compatible APIs OpenAI及兼容API
ENABLE_DIRECT_CONNECTIONS # Direct model connections 直接模型連接

# Core Features 核心功能
ENABLE_CODE_EXECUTION     # Code execution support 代碼執行支持
ENABLE_CODE_INTERPRETER   # Code interpreter functionality 代碼解釋器功能
ENABLE_IMAGE_GENERATION   # Image generation capabilities 圖像生成能力
ENABLE_IMAGE_PROMPT_GENERATION # Image prompt generation 圖像提示詞生成
ENABLE_WEB_SEARCH        # Web search integration 網絡搜索集成
ENABLE_RAG_HYBRID_SEARCH # Hybrid search for RAG RAG混合搜索
ENABLE_WEBSOCKET_SUPPORT # Real-time communication via Socket.IO 透過Socket.IO的實時通信
AUDIO_STT_ENGINE         # Speech-to-Text engine 語音轉文字引擎
AUDIO_TTS_ENGINE         # Text-to-Speech engine 文字轉語音引擎

# Data and Feature Management 數據與功能管理
ENABLE_CHANNELS          # Channels feature 通道功能
ENABLE_NOTES             # Notes feature 筆記功能
ENABLE_COMMUNITY_SHARING # Community sharing feature 社區分享功能
ENABLE_MESSAGE_RATING    # Message rating feature 訊息評分功能
ENABLE_USER_WEBHOOKS     # User-specific webhooks 用戶網鉤
ENABLE_KNOWLEDGE_BASES   # Knowledge base integration (implied by routers/knowledge.py) 知識庫集成 (由routers/knowledge.py推斷)
ENABLE_PROMPTS           # Prompt management (implied by routers/prompts.py) 提示詞管理 (由routers/prompts.py推斷)
ENABLE_TOOLS             # Tool integration (implied by routers/tools.py) 工具集成 (由routers/tools.py推斷)
ENABLE_FOLDERS           # Folder organization (implied by routers/folders.py) 文件夾組織 (由routers/folders.py推斷)
ENABLE_GROUPS            # Group management (implied by routers/groups.py) 群組管理 (由routers/groups.py推斷)
ENABLE_EVALUATIONS       # Evaluation features (implied by routers/evaluations.py) 評估功能 (由routers/evaluations.py推斷)

# Authentication 認證
WEBUI_AUTH               # Auth system configuration 認證系統配置
ENABLE_OAUTH_ROLE_MANAGEMENT # OAuth role management OAuth角色管理
ENABLE_LDAP              # LDAP integration LDAP集成
ENABLE_API_KEY          # API key authentication API密鑰認證
ENABLE_SIGNUP            # User signup enablement 用戶註冊啟用
ENABLE_LOGIN_FORM        # Traditional login form enablement 傳統登錄表單啟用
```

## Architecture
## 架構

### Code Structure
### 代碼結構
```
backend/
├── requirements.txt     # Python dependencies Python依賴
├── open_webui/
│   ├── __init__.py
│   ├── main.py              # FastAPI application setup FastAPI應用設置
│   ├── config.py            # Configuration management 配置管理
│   ├── constants.py         # System constants 系統常量
│   ├── env.py               # Environment variable loading 環境變數加載
│   ├── tasks.py             # Background tasks 後台任務
│   ├── models/              # SQLAlchemy ORM models / Pydantic models SQLAlchemy ORM模型 / Pydantic模型
│   │   ├── users.py         # User model 用戶模型
│   │   ├── chats.py         # Chat model 聊天模型
│   │   ├── files.py         # File model 文件模型
│   │   ├── models.py        # AI Models (configurations) AI模型(配置)
│   │   ├── tools.py         # Tool models 工具模型
│   │   ├── knowledge.py     # Knowledge base models 知識庫模型
│   │   ├── prompts.py       # Prompt models 提示詞模型
│   │   └── ... (other models like folders, groups etc.) ... (其他模型如文件夾、群組等)
│   ├── routers/             # API routes API路由
│   │   ├── auths.py         # Auth endpoints 認證端點
│   │   ├── chats.py         # Chat endpoints 聊天端點
│   │   ├── models.py        # AI Model (configuration) endpoints AI模型(配置)端點
│   │   ├── files.py         # File management endpoints 文件管理端點
│   │   ├── tools.py         # Tool endpoints 工具端點
│   │   ├── knowledge.py     # Knowledge base endpoints 知識庫端點
│   │   ├── prompts.py       # Prompt endpoints 提示詞端點
│   │   ├── audio.py         # Audio processing endpoints 音頻處理端點
│   │   ├── images.py        # Image generation endpoints 圖像生成端點
│   │   ├── retrieval.py     # RAG and retrieval endpoints RAG與檢索端點
│   │   ├── pipelines.py     # Pipeline endpoints 管道端點
│   │   └── ... (other routers like folders, groups, evaluations etc.) ... (其他路由如文件夾、群組、評估等)
│   ├── internal/            # Internal utilities 內部工具
│   │   ├── db.py            # Database setup (SQLAlchemy) 數據庫設置 (SQLAlchemy)
│   │   └── wrappers.py      # Function wrappers 函數包裝器
│   ├── socket/              # WebSocket (Socket.IO) handling WebSocket (Socket.IO) 處理
│   │   └── main.py          # Socket.IO app setup Socket.IO應用設置
│   └── utils/               # Utility functions and classes 工具函數和類
│       ├── auth.py          # Authentication utilities 認證工具
│       ├── tools.py         # Tool utilities (e.g. spec generation) 工具相關工具函式 (例如: spec產生)
│       ├── telemetry/       # OpenTelemetry setup OpenTelemetry設置
│       └── ...
└── ...
```

### Key Classes and Functions
### 關鍵類和函數

#### Main Application (`main.py`)
#### 主應用程序
```python
# FastAPI application setup FastAPI應用設置
app = FastAPI(
    title="Open WebUI",
    docs_url="/docs" if ENV == "dev" else None,
    openapi_url="/openapi.json" if ENV == "dev" else None,
    redoc_url=None,
    lifespan=lifespan, # Handles startup and shutdown events 處理啟動和關閉事件
)

# Mounts Socket.IO application 掛載Socket.IO應用
app.mount("/ws", socket_app)

# Includes various routers for modularized API endpoints 包含多個路由以實現模塊化的API端點
app.include_router(ollama.router, ...)
app.include_router(openai.router, ...)
app.include_router(auths.router, ...)
app.include_router(users.router, ...)
app.include_router(chats.router, ...)
# ... and many other routers for different features ... 以及許多其他功能的路由

# Chat completion endpoint 聊天完成端點
@app.post("/api/chat/completions")
async def chat_completion(request: Request, form_data: dict, user=Depends(get_verified_user))

# Model listing endpoint 模型列表端點
@app.get("/api/models")
async def get_models(request: Request, user=Depends(get_verified_user))
```

#### User Model (`models/users.py`)
#### 用戶模型
```python
# SQLAlchemy model SQLAlchemy模型
class User(Base):
    __tablename__ = "user"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String) # Typically unique 通常唯一
    role = Column(String) # e.g., "admin", "user", "pending" 例如 "admin", "user", "pending"
    profile_image_url = Column(Text)
    api_key = Column(String, nullable=True, unique=True)
    settings = Column(JSONField, nullable=True) # Stores user-specific UI settings etc. 儲存用戶特定的UI設定等
    info = Column(JSONField, nullable=True)     # Additional user information 額外用戶資訊
    oauth_sub = Column(Text, unique=True)       # Subject claim from OAuth provider 來自OAuth提供者的Subject聲明
    # Timestamps like last_active_at, updated_at, created_at (BigInteger) 時間戳如 last_active_at, updated_at, created_at (BigInteger)

# Pydantic model for API responses Pydantic模型用於API回應
class UserModel(BaseModel): ...

# Table operations class (e.g., UsersTable) 表操作類 (例如 UsersTable)
class UsersTable:
    def get_user_by_id(self, id: str) -> Optional[UserModel]: ...
    def insert_new_user(self, ...) -> Optional[UserModel]: ...
    def get_user_by_email(self, email: str) -> Optional[UserModel]: ...
    # ... other CRUD methods ... 其他CRUD方法
```

#### Chat Model (`models/chats.py`)
#### 聊天模型
```python
# SQLAlchemy model SQLAlchemy模型
class Chat(Base):
    __tablename__ = "chat"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(Text)
    chat = Column(JSON) # Stores chat history, messages, etc. 儲存聊天歷史、訊息等
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    share_id = Column(Text, unique=True, nullable=True) # For shared chats 用於共享聊天
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False, nullable=True)
    meta = Column(JSON, server_default="{}") # Stores tags, etc. 儲存標籤等
    folder_id = Column(Text, nullable=True)

# Pydantic model for API responses Pydantic模型用於API回應
class ChatModel(BaseModel): ...

# Table operations class 表操作類
class ChatTable:
    def insert_new_chat(self, user_id: str, form_data: ChatForm) -> Optional[ChatModel]: ...
    def get_chat_by_id(self, id: str) -> Optional[ChatModel]: ...
    def update_chat_by_id(self, id: str, chat: dict) -> Optional[ChatModel]: ...
    # ... other CRUD methods for chat management ... 其他聊天管理的CRUD方法
```

#### File Model (`models/files.py`)
#### 文件模型
```python
# SQLAlchemy model SQLAlchemy模型
class File(Base):
    __tablename__ = "file"
    id = Column(String, primary_key=True)
    user_id = Column(String)
    hash = Column(Text, nullable=True) # Hash of the file content 文件內容的哈希值
    filename = Column(Text)            # Original filename 原始文件名
    path = Column(Text, nullable=True) # Storage path 儲存路徑
    data = Column(JSON, nullable=True) # Extracted content or other data 提取的內容或其他數據
    meta = Column(JSON, nullable=True) # Content type, size, etc. 內容類型、大小等
    access_control = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

# Pydantic model for API responses Pydantic模型用於API回應
class FileModel(BaseModel): ...

# Table operations class 表操作類
class FilesTable:
    def insert_new_file(self, user_id: str, form_data: FileForm) -> Optional[FileModel]: ...
    def get_file_by_id(self, id: str) -> Optional[FileModel]: ...
    # ... other CRUD methods for file management ... 其他文件管理的CRUD方法
```

#### Tool Model (`models/tools.py`)
#### 工具模型
```python
# SQLAlchemy model SQLAlchemy模型
class Tool(Base):
    __tablename__ = "tool"
    id = Column(String, primary_key=True)         # Tool ID (must be a valid Python identifier) 工具ID (必須是有效的Python標識符)
    user_id = Column(String)                      # ID of the user who created the tool 創建工具的用戶ID
    name = Column(Text)                           # Display name of the tool 工具的顯示名稱
    content = Column(Text)                        # Python code defining the tool 定義工具的Python代碼
    specs = Column(JSONField)                     # OpenAPI specifications for the tool's functions 工具函數的OpenAPI規範
    meta = Column(JSONField)                      # Metadata like description, manifest 元數據，如描述、清單
    valves = Column(JSONField, nullable=True)     # Global configurations for the tool 工具的全局配置
    access_control = Column(JSON, nullable=True)  # Access control rules 訪問控制規則
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

# Pydantic models for API requests/responses Pydantic模型用於API請求/回應
class ToolModel(BaseModel): ...   # Full tool model 完整的工具模型
class ToolForm(BaseModel): ...    # For creating/updating tools 用於創建/更新工具
class ToolResponse(BaseModel): ... # Basic tool response 基本工具回應

# Table operations class 表操作類
class ToolsTable:
    def insert_new_tool(self, user_id: str, form_data: ToolForm, specs: list[dict]) -> Optional[ToolModel]: ...
    def get_tool_by_id(self, id: str) -> Optional[ToolModel]: ...
    def update_tool_by_id(self, id: str, updated: dict) -> Optional[ToolModel]: ...
    def delete_tool_by_id(self, id: str) -> bool: ...
    # ... methods for managing tool valves (configurations) ... 管理工具閥門(配置)的方法
```

## Technical Implementation
## 技術實現

### Database Schema (Illustrative based on models)
### 數據庫模式 (基於模型的示例)

#### Users & Authentication
#### 用戶和認證
```sql
-- Users table structure (Illustrative) 用戶表結構 (示例)
CREATE TABLE "user" ( -- Note: table name is "user", not "users"
    id VARCHAR PRIMARY KEY,
    name VARCHAR,
    email VARCHAR, -- Typically unique 通常唯一
    role VARCHAR,
    profile_image_url TEXT,
    last_active_at BIGINT,
    updated_at BIGINT,
    created_at BIGINT,
    api_key VARCHAR UNIQUE,
    settings JSONB,
    info JSONB,
    oauth_sub TEXT UNIQUE
);
-- Authentication details (like password hashes) are likely managed in a separate 'auths' table or mechanism.
-- 認證細節 (如密碼哈希) 可能在單獨的 'auths' 表或機制中管理。
```

#### Chats & Messages
#### 聊天和消息
```sql
-- Chat sessions (Illustrative) 聊天會話 (示例)
CREATE TABLE chat (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    title TEXT,
    chat JSONB, -- Contains messages and history 包含訊息和歷史記錄
    created_at BIGINT,
    updated_at BIGINT,
    share_id TEXT UNIQUE,
    archived BOOLEAN DEFAULT FALSE,
    pinned BOOLEAN DEFAULT FALSE,
    meta JSONB DEFAULT '{}', -- For tags, etc. 用於標籤等
    folder_id TEXT
);
-- Individual messages are stored within the 'chat' JSONB field.
-- 單條訊息儲存在 'chat' JSONB 字段中。
```

#### Files
#### 文件
```sql
-- Files table structure (Illustrative) 文件表結構 (示例)
CREATE TABLE file (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    hash TEXT,
    filename TEXT,
    path TEXT,
    data JSONB,
    meta JSONB,
    access_control JSONB,
    created_at BIGINT,
    updated_at BIGINT
);
```

#### Tools
#### 工具
```sql
-- Tools table structure (Illustrative) 工具表結構 (示例)
CREATE TABLE tool (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    name TEXT,
    content TEXT, -- Python code for the tool 工具的Python代碼
    specs JSONB,  -- OpenAPI specifications for the tool 工具的OpenAPI規範
    meta JSONB,   -- Description, manifest, etc. 描述、清單等
    valves JSONB, -- Tool-specific configurations 工具特定配置
    access_control JSONB,
    updated_at BIGINT,
    created_at BIGINT
);
```

### API Routes (Key Examples)
### API路由 (關鍵示例)

Base path for most new APIs: `/api/v1/`
大多數新API的基礎路徑: `/api/v1/`

#### Authentication (`routers/auths.py`)
#### 認證
- `GET /api/v1/auths/`: Get current session user. 獲取當前會話用戶。
- `POST /api/v1/auths/signin`: User login. 用戶登錄。
- `POST /api/v1/auths/signup`: User registration. 用戶註冊。
- `GET /api/v1/auths/signout`: User logout. 用戶登出。
- `POST /api/v1/auths/update/profile`: Update user profile. 更新用戶資料。
- `POST /api/v1/auths/update/password`: Update user password. 更新用戶密碼。
- `POST /api/v1/auths/ldap`: LDAP authentication. LDAP認證。
- `POST /api/v1/auths/api_key`: Generate API key. 生成API密鑰。
- `DELETE /api/v1/auths/api_key`: Delete API key. 刪除API密鑰。
- `GET /api/v1/auths/api_key`: Get API key. 獲取API密鑰。
- `GET /oauth/{provider}/login` & `GET /oauth/{provider}/callback`: OAuth routes. OAuth路由。

#### Chat Operations (`routers/chats.py`)
#### 聊天操作
- `GET /api/v1/chats/` or `/api/v1/chats/list`: Get user's chat list. 獲取用戶聊天列表。
- `POST /api/v1/chats/new`: Create a new chat. 創建新聊天。
- `POST /api/v1/chats/import`: Import a chat. 導入聊天。
- `GET /api/v1/chats/search?text={text}`: Search chats. 搜索聊天。
- `GET /api/v1/chats/{id}`: Get chat by ID. 按ID獲取聊天。
- `POST /api/v1/chats/{id}`: Update chat by ID. 按ID更新聊天。
- `DELETE /api/v1/chats/{id}`: Delete chat by ID. 按ID刪除聊天。
- `POST /api/v1/chats/{id}/share`: Share a chat. 分享聊天。
- `DELETE /api/v1/chats/{id}/share`: Unshare a chat. 取消分享聊天。
- `POST /api/v1/chats/{id}/clone`: Clone a chat. 克隆聊天。
- `POST /api/v1/chats/{id}/archive`: Archive/unarchive a chat. 歸檔/取消歸檔聊天。
- `POST /api/v1/chats/{id}/pin`: Pin/unpin a chat. 置頂/取消置頂聊天。
- `POST /api/v1/chats/{id}/tags`: Add a tag to a chat. 為聊天添加標籤。
- `DELETE /api/v1/chats/{id}/tags`: Remove a tag from a chat. 從聊天中移除標籤。
- Legacy chat completion: `POST /api/chat/completions` (still active in `main.py`) 舊版聊天完成接口 (仍在 `main.py` 中活躍)

#### File Management (`routers/files.py`)
#### 文件管理
- `POST /api/v1/files/`: Upload a file. 上傳文件。
- `GET /api/v1/files/`: List files for the user. 列出用戶文件。
- `GET /api/v1/files/search?filename={pattern}`: Search files by filename pattern. 按文件名模式搜索文件。
- `GET /api/v1/files/{id}`: Get file metadata by ID. 按ID獲取文件元數據。
- `GET /api/v1/files/{id}/content`: Get file content by ID. 按ID獲取文件內容。
- `DELETE /api/v1/files/{id}`: Delete file by ID. 按ID刪除文件。

#### Model Management (`routers/models.py`) - For AI model configurations
#### 模型管理 (AI模型配置)
- `GET /api/v1/models/`: Get list of configured AI models. 獲取已配置AI模型列表。
- `POST /api/v1/models/create`: Create/register a new AI model configuration. 創建/註冊新的AI模型配置。
- `GET /api/v1/models/model?id={model_id}`: Get AI model configuration by ID. 按ID獲取AI模型配置。
- `POST /api/v1/models/model/update?id={model_id}`: Update AI model configuration. 更新AI模型配置。
- `DELETE /api/v1/models/model/delete?id={model_id}`: Delete AI model configuration. 刪除AI模型配置。
- Legacy model listing: `GET /api/models` (still active in `main.py`) 舊版模型列表接口 (仍在 `main.py` 中活躍)

#### Tool Management (`routers/tools.py`)
#### 工具管理
- `GET /api/v1/tools/`: Get list of available tools (considers user access and tool servers). 獲取可用工具列表 (考慮用戶訪問權限和工具服務器)。
- `GET /api/v1/tools/list`: Get tool list (admin sees all, user sees own/accessible). 獲取工具列表 (管理員可見所有，用戶可見自己的/可訪問的)。
- `GET /api/v1/tools/export`: Export all tools (admin only). 導出所有工具 (僅管理員)。
- `POST /api/v1/tools/create`: Create a new tool. 創建新工具。
- `GET /api/v1/tools/id/{id}`: Get tool by ID. 按ID獲取工具。
- `POST /api/v1/tools/id/{id}/update`: Update tool by ID. 按ID更新工具。
- `DELETE /api/v1/tools/id/{id}/delete`: Delete tool by ID. 按ID刪除工具。
- `GET /api/v1/tools/id/{id}/valves`: Get tool's global valves (configurations). 獲取工具的全局閥門 (配置)。
- `GET /api/v1/tools/id/{id}/valves/spec`: Get schema for tool's global valves. 獲取工具全局閥門的模式。
- `POST /api/v1/tools/id/{id}/valves/update`: Update tool's global valves. 更新工具的全局閥門。
- `GET /api/v1/tools/id/{id}/valves/user`: Get tool's user-specific valves. 獲取工具的用戶特定閥門。
- `GET /api/v1/tools/id/{id}/valves/user/spec`: Get schema for tool's user-specific valves. 獲取工具用戶特定閥門的模式。
- `POST /api/v1/tools/id/{id}/valves/user/update`: Update tool's user-specific valves. 更新工具的用戶特定閥門。

### WebSocket Events (via `open_webui.socket.main`)
### WebSocket事件 (通過 `open_webui.socket.main`)
The system uses Socket.IO for real-time communication. Key events are managed within the `socket` module.
系統使用 Socket.IO 進行實時通信。關鍵事件在 `socket` 模塊中管理。
- Example from `routers/chats.py`: `chat:message` event emitted on message updates.
- 來自 `routers/chats.py` 的示例：在訊息更新時發出 `chat:message` 事件。
- Other events likely include typing indicators, completion chunks, system notifications, etc.
- 其他事件可能包括輸入指示器、完成片段、系統通知等。

## Security Considerations
## 安全考慮
(This section from the original PRD is largely accurate and refers to correct utility modules)
(原PRD中的此部分基本準確，並引用了正確的工具模塊)
### Authentication & Authorization
### 認證和授權
```python
# JWT and session handling JWT和會話處理
/open_webui/utils/auth.py                # Auth utilities 認證工具
/open_webui/utils/security_headers.py    # Security headers 安全標頭
/open_webui/utils/access_control.py      # Access control 訪問控制

# Rate limiting and API key verification (Assumed, specific files not listed in original PRD)
# 速率限制和API密鑰驗證 (假設，原PRD未列出特定文件)
# Example: API key logic in /open_webui/routers/auths.py
# 示例: API密鑰邏輯在 /open_webui/routers/auths.py
```

## Performance Optimization
## 性能優化
(This section from the original PRD is largely accurate)
(原PRD中的此部分基本準確)
### Caching Strategy
### 緩存策略
- Utilizes `aiocache` (from `requirements.txt` and `main.py`).
- 使用 `aiocache` (來自 `requirements.txt` 和 `main.py`)。
- Redis can be configured (`REDIS_URL` in `env.py`).
- 可以配置 Redis (`REDIS_URL` 在 `env.py` 中)。
```python
# Cache configurations (example from original PRD, actual values in env.py)
# 緩存配置 (原PRD示例，實際值在 env.py 中)
# REDIS_URL = "redis://localhost:6379"
```

### Database Optimization
### 數據庫優化
- SQLAlchemy is used for database interactions.
- 使用 SQLAlchemy 進行數據庫交互。
- Connection pooling is typically handled by SQLAlchemy's engine.
- 連接池通常由 SQLAlchemy 的引擎處理。
```python
# Database utilities 數據庫工具
/open_webui/internal/db.py            # Database setup (SQLAlchemy) 數據庫設置 (SQLAlchemy)
```

## Monitoring & Logging
## 監控和日誌
(This section from the original PRD is largely accurate)
(原PRD中的此部分基本準確)
### System Health
### 系統健康
- Health check endpoints: `/health` and `/health/db` (from `main.py`).
- 健康檢查端點: `/health` 和 `/health/db` (來自 `main.py`)。
```python
# Performance tracking 性能追踪
# OpenTelemetry is configured if ENABLE_OTEL=True (main.py)
# 如果 ENABLE_OTEL=True，則配置 OpenTelemetry (main.py)
# Relevant packages: opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi etc. (from requirements.txt)
# 相關套件: opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi 等 (來自 requirements.txt)
```

### Logging
### 日誌
- Standard Python logging is used, configured in `main.py` and `utils/logger.py`.
- 使用標準 Python 日誌，在 `main.py` 和 `utils/logger.py` 中配置。
- `loguru` is also a dependency.
- `loguru` 也是一個依賴項。

## Deployment Considerations
## 部署考慮
(This section from the original PRD is a good general guide)
(原PRD中的此部分是一個很好的通用指南)
### Environment Configuration
### 環境配置
- Extensive use of environment variables for configuration (see `env.py` and `config.py`).
- 廣泛使用環境變數進行配置 (參見 `env.py` 和 `config.py`)。
- Feature flags control various functionalities.
- 功能標記控制各種功能。

### Scalability
### 可擴展性
- FastAPI is an ASGI framework, suitable for asynchronous workloads and scaling with ASGI servers like Uvicorn.
- FastAPI 是一個 ASGI 框架，適用於異步工作負載並可與 Uvicorn 等 ASGI 服務器一起擴展。
- Load balancing and multiple instances can be used.
- 可以使用負載均衡和多個實例。

### Maintenance
### 維護
- Database migrations likely handled by Alembic (`alembic` in `requirements.txt`).
- 數據庫遷移可能由 Alembic 處理 (`alembic` 在 `requirements.txt` 中)。
- Standard backup procedures for the database and persistent storage (if used for files).
- 數據庫和持久儲存 (如果用於文件) 的標準備份程序。
