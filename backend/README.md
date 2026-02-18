# Open WebUI Backend

This directory contains the backend implementation of Open WebUI, built with **FastAPI** and Python. The backend provides a comprehensive REST API for managing AI conversations, user authentication, file handling, and integrations with various LLM providers.

## 🏗️ Architecture Overview

The Open WebUI backend follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Routers   │  │  Middleware  │  │  Authentication  │  │
│  │   (API)     │  │  (CORS, etc) │  │   (JWT, OAuth)   │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Models    │  │    Utils     │  │    Services      │  │
│  │ (Database)  │  │  (Helpers)   │  │  (Business       │  │
│  │             │  │              │  │   Logic)         │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Database   │  │    Redis     │  │   File Storage   │  │
│  │ SQLAlchemy  │  │   (Cache)    │  │     (Local/      │  │
│  │   Peewee    │  │              │  │      Cloud)      │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
backend/
├── open_webui/              # Main application package
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management & environment variables
│   ├── constants.py         # Application constants
│   ├── env.py               # Environment variable loading
│   ├── functions.py         # Python function tools system
│   ├── tasks.py             # Background task definitions
│   │
│   ├── routers/             # API route handlers
│   │   ├── auths.py         # Authentication & authorization
│   │   ├── chats.py         # Chat management
│   │   ├── users.py         # User management
│   │   ├── models.py        # LLM model management
│   │   ├── ollama.py        # Ollama integration
│   │   ├── openai.py        # OpenAI-compatible API
│   │   ├── files.py         # File upload & management
│   │   ├── knowledge.py     # Knowledge base / RAG
│   │   ├── retrieval.py     # Document retrieval
│   │   ├── images.py        # Image generation (DALL-E, ComfyUI)
│   │   ├── audio.py         # Speech-to-text & text-to-speech
│   │   ├── functions.py     # Custom function tools
│   │   ├── tools.py         # Tool management
│   │   ├── skills.py        # Skill system
│   │   ├── prompts.py       # Prompt templates
│   │   ├── memories.py      # Conversation memory
│   │   ├── notes.py         # User notes
│   │   ├── folders.py       # Folder organization
│   │   ├── groups.py        # User groups & permissions
│   │   ├── configs.py       # System configuration
│   │   ├── channels.py      # Communication channels
│   │   ├── evaluations.py   # Model evaluations
│   │   ├── analytics.py     # Usage analytics
│   │   ├── pipelines.py     # Pipeline integrations
│   │   ├── scim.py          # SCIM 2.0 provisioning
│   │   └── tasks.py         # Task management
│   │
│   ├── models/              # Database models (ORM)
│   │   ├── auths.py         # Authentication models
│   │   ├── users.py         # User models
│   │   ├── chats.py         # Chat models
│   │   ├── chat_messages.py # Message models
│   │   ├── files.py         # File models
│   │   ├── functions.py     # Function models
│   │   ├── tools.py         # Tool models
│   │   ├── prompts.py       # Prompt models
│   │   ├── knowledge.py     # Knowledge base models
│   │   ├── memories.py      # Memory models
│   │   ├── groups.py        # Group models
│   │   └── ...              # Other domain models
│   │
│   ├── utils/               # Utility functions & helpers
│   │   ├── auth.py          # Authentication utilities
│   │   ├── access_control.py # Permission checking
│   │   ├── middleware.py    # Custom middleware
│   │   ├── rate_limit.py    # Rate limiting
│   │   ├── embeddings.py    # Text embeddings
│   │   ├── chat.py          # Chat utilities
│   │   ├── files.py         # File handling utilities
│   │   ├── webhook.py       # Webhook utilities
│   │   ├── redis.py         # Redis utilities
│   │   ├── logger.py        # Logging utilities
│   │   ├── security_headers.py # Security headers
│   │   ├── telemetry/       # OpenTelemetry integration
│   │   ├── mcp/             # Model Context Protocol
│   │   └── images/          # Image processing utilities
│   │
│   ├── retrieval/           # RAG (Retrieval Augmented Generation)
│   │   ├── vector/          # Vector database integrations
│   │   ├── loaders/         # Document loaders
│   │   └── web/             # Web search integrations
│   │
│   ├── storage/             # Storage backends
│   │   ├── local.py         # Local file storage
│   │   ├── s3.py            # S3-compatible storage
│   │   └── ...              # Other cloud storage providers
│   │
│   ├── socket/              # WebSocket handlers
│   │   └── main.py          # Real-time communication
│   │
│   ├── internal/            # Internal modules
│   │   └── db.py            # Database connection & session management
│   │
│   ├── migrations/          # Alembic database migrations
│   │   └── versions/        # Migration scripts
│   │
│   └── test/                # Test suite
│       └── ...              # Unit and integration tests
│
├── requirements.txt         # Python dependencies
├── start.sh                 # Linux/Mac startup script
├── start_windows.bat        # Windows startup script
└── dev.sh                   # Development mode startup
```

> **Note:** `alembic.ini` is located inside `open_webui/` directory, not at the backend root.

## 🔑 Key Components

### 1. **FastAPI Application** (`main.py`)
The core application bootstraps:
- CORS middleware for frontend communication
- API routers for all endpoints
- Static file serving for the frontend
- WebSocket support for real-time features
- Database initialization and migrations
- Background task scheduling

### 2. **Routers** (`routers/`)
Each router handles a specific domain:
- **Authentication** (`auths.py`): User registration, login, JWT tokens, OAuth
- **LLM Integration** (`ollama.py`, `openai.py`): Proxy to LLM providers
- **Chat Management** (`chats.py`): Conversation history and management
- **RAG System** (`knowledge.py`, `retrieval.py`): Document upload, embedding, and retrieval
- **File Handling** (`files.py`): Upload, storage, and retrieval
- **User Management** (`users.py`, `groups.py`): Users, roles, permissions

### 3. **Database Models** (`models/`)
Uses **SQLAlchemy** and **Peewee** for ORM:
- Schema definitions for all entities
- Relationships between models
- Database migrations via Alembic

### 4. **Configuration** (`config.py`)
Centralized configuration management:
- Environment variable loading
- Database connection settings
- LLM provider configurations
- Feature flags and system settings
- Redis connection for caching and sessions

### 5. **Utilities** (`utils/`)
Reusable helper functions:
- Authentication & authorization helpers
- Rate limiting and security
- File processing
- Embeddings generation
- Webhook handling

### 6. **RAG System** (`retrieval/`)
Retrieval Augmented Generation features:
- **Vector Databases**: ChromaDB, PGVector, Qdrant, Milvus, etc.
- **Document Loaders**: PDF, Word, text, web pages
- **Embedding Models**: Sentence transformers, OpenAI embeddings
- **Web Search**: Integration with multiple search providers

## 🚀 Development Setup

### Prerequisites
- **Python 3.11+** (Python 3.13 recommended)
- **pip** or **uv** for package management
- **Redis** (optional, for caching and sessions)
- **PostgreSQL** or **SQLite** for database

### Installation

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the project root (not in backend/):
   ```env
   # Database
   DATABASE_URL=sqlite:///backend/data/webui.db
   
   # Ollama Integration
   OLLAMA_BASE_URL=http://localhost:11434
   
   # OpenAI API (optional)
   OPENAI_API_KEY=your_api_key_here
   
   # CORS
   CORS_ALLOW_ORIGIN=http://localhost:5173
   ```

5. **Run database migrations:**
   ```bash
   # Migrations run automatically on first startup
   # Or run manually from the backend directory:
   cd open_webui
   alembic upgrade head
   ```

6. **Start the development server:**
   ```bash
   # Linux/Mac
   ./dev.sh
   
   # Windows
   start_windows.bat
   
   # Or manually
   uvicorn open_webui.main:app --reload --host 0.0.0.0 --port 8080
   ```

The backend API will be available at `http://localhost:8080`

### Development Mode

For development with hot-reload:
```bash
# Set CORS for local frontend development
export CORS_ALLOW_ORIGIN="http://localhost:5173"
export PORT=8080

# Run with reload
uvicorn open_webui.main:app --reload --host 0.0.0.0 --port 8080
```

## 🧪 Testing

Run the test suite:
```bash
pytest open_webui/test/
```

Run with coverage:
```bash
pytest --cov=open_webui --cov-report=html
```

## 📡 API Documentation

Once the server is running, interactive API documentation is available:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

## 🔐 Authentication & Authorization

The backend implements:
- **JWT tokens** for stateless authentication
- **OAuth 2.0** for third-party authentication (Google, GitHub, etc.)
- **Role-Based Access Control (RBAC)** for permissions
- **Group-based permissions** for team management
- **SCIM 2.0** for enterprise user provisioning

## 🗄️ Database

The backend supports multiple database backends:
- **SQLite** (default, for development and single-user)
- **PostgreSQL** (recommended for production)
- **MySQL/MariaDB** (supported)

Migrations are managed with **Alembic**.

## 📦 Dependencies

Key dependencies include:
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM for database operations
- **Peewee** - Alternative ORM for some models
- **Pydantic** - Data validation
- **LangChain** - LLM orchestration and RAG
- **ChromaDB** - Vector database for embeddings
- **Sentence Transformers** - Text embeddings
- **OpenAI** - OpenAI API client
- **Redis** - Caching and session management

See `requirements.txt` for the complete list.

## 🌐 Environment Variables

Key environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./backend/data/webui.db` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `WEBUI_AUTH` | Enable authentication | `True` |
| `CORS_ALLOW_ORIGIN` | Allowed CORS origins | `*` |
| `REDIS_URL` | Redis connection URL | - |
| `PORT` | Server port | `8080` |

See [`config.py`](open_webui/config.py) for the complete list.

## 🔌 LLM Provider Integrations

The backend supports multiple LLM providers:
- **Ollama** - Local LLM runtime
- **OpenAI** - GPT models
- **Anthropic** - Claude models
- **Google** - Gemini models
- **Any OpenAI-compatible API** (LMStudio, LocalAI, etc.)

## 📝 Adding New Features

### Adding a New Router

1. Create a new file in `routers/`:
   ```python
   from fastapi import APIRouter, Depends
   from open_webui.utils.auth import get_current_user
   
   router = APIRouter()
   
   @router.get("/my-endpoint")
   async def my_endpoint(user=Depends(get_current_user)):
       return {"message": "Hello from my endpoint"}
   ```

2. Register the router in `main.py`:
   ```python
   from open_webui.routers import my_router
   
   app.include_router(my_router.router, prefix="/api/my-feature", tags=["my-feature"])
   ```

### Adding a New Database Model

1. Create a model in `models/`:
   ```python
   from sqlalchemy import Column, String, Integer
   from open_webui.internal.db import Base
   
   class MyModel(Base):
       __tablename__ = "my_table"
       
       id = Column(Integer, primary_key=True)
       name = Column(String)
   ```

2. Create a migration:
   ```bash
   # From backend/open_webui directory:
   cd open_webui
   alembic revision --autogenerate -m "Add my_table"
   alembic upgrade head
   ```

## 🤝 Contributing

Please read the [Contributing Guide](../docs/CONTRIBUTING.md) before submitting pull requests.

Key guidelines:
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Ensure all tests pass
- Target the `dev` branch for PRs

## 📄 License

See the [LICENSE](../LICENSE) file for details.

## 🆘 Support

- **Documentation**: https://docs.openwebui.com
- **Discord**: https://discord.gg/5rJgQTnV4s
- **Issues**: https://github.com/open-webui/open-webui/issues
