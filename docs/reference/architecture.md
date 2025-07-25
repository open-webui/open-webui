# Technical Architecture

## Stack Overview

### Frontend (SvelteKit)
- **Framework**: SvelteKit with TypeScript
- **Styling**: TailwindCSS with custom themes
- **Build Tool**: Vite
- **Key Dependencies**:
  - TipTap v3 for rich text editing
  - Chart.js for data visualization
  - Pyodide for Python code execution
  - Socket.io for real-time communication
  - i18n support (20+ languages)

### Backend (FastAPI)
- **Framework**: FastAPI with Python 3.11-3.12
- **Database**: SQLAlchemy with Alembic migrations
- **Supported DBs**: PostgreSQL, MySQL, SQLite
- **Vector DBs**: ChromaDB, Qdrant, Milvus, Pinecone, OpenSearch, ElasticSearch
- **Authentication**: JWT with OAuth support
- **AI Integration**: OpenAI, Anthropic, Google Gemini APIs
- **Usage Tracking**: OpenRouter API integration with background sync service

## Deployment Architecture

### Multi-Instance Model (Production)
**mAI is deployed as 20 separate Docker instances on Hetzner Cloud:**

- **One instance per client organization** (5-20 employees each)
- **Isolated databases** (SQLite per client)
- **Dedicated servers** on Hetzner Cloud (Nuremberg datacenter)
- **Independent usage tracking** per client organization
- **Single admin per instance** managing company users

#### Instance Specifications (Per Client)
- **Server**: Hetzner Cloud VPS (2-4 vCPU, 4-8GB RAM, 40-80GB SSD)
- **Container**: Single Docker container per client
- **Database**: SQLite (isolated per client)
- **Users**: 1 admin + 5-20 company employees
- **API Key**: One OpenRouter API key per client organization
## Architecture Patterns

### Backend Patterns
- **Dependency Injection**: FastAPI's dependency system for database sessions, auth
- **Repository Pattern**: Models in `backend/open_webui/models/` with separate business logic
- **Router Organization**: Feature-based routing in `routers/` directory (includes usage_tracking.py)
- **Background Services**: Async background tasks for data synchronization
- **Middleware Chain**: Authentication, CORS, compression middleware
- **Database Abstraction**: SQLAlchemy ORM with Alembic migrations

### Frontend Patterns
- **Component Architecture**: Feature-based component organization
- **Store Pattern**: Svelte stores for global state management
- **API Client Pattern**: Centralized API functions in `src/lib/apis/`
- **Layout Hierarchy**: Nested layouts in SvelteKit route structure
- **Reactive Programming**: Svelte's reactive declarations and stores

### Single-Tenant Isolation
Each client instance maintains complete isolation:

#### Database Isolation
```
Client A (Hetzner Server 1)
└── SQLite Database A
    ├── Users (1 admin + employees)
    ├── Chat history
    ├── Usage tracking
    └── Organization settings

Client B (Hetzner Server 2)  
└── SQLite Database B
    ├── Users (1 admin + employees)
    ├── Chat history
    ├── Usage tracking
    └── Organization settings
```

#### Usage Tracking per Instance ✅ PRODUCTION IMPLEMENTATION
- **API Key Isolation**: Each client has unique OpenRouter API key
- **External User Learning**: Auto-learned per client organization
- **Live Counters**: Real-time usage tracking per instance
- **Historical Data**: Client-specific usage summaries and analytics
- **Background Sync Service**: Automatic OpenRouter API polling every 10 minutes
- **Database Tools**: Production-ready initialization and cleanup tools
- **Currency Precision**: Fixed formatting for accurate cost display (6 decimal places)
- **Error Recovery**: Robust error handling for container restarts and API failures
## Data Flow

### Authentication
- **JWT tokens** with refresh mechanism
- **Admin-first model**: First registered user becomes admin
- **User management**: Admin creates accounts for company employees

### Real-time Features
- **Socket.io**: Live chat and notifications
- **Usage Dashboard**: 30-second refresh cycles for live usage data
- **File Upload**: Chunked uploads with progress tracking

### AI Integration Flow
- **RAG Pipeline**: Document ingestion → Vector embedding → Retrieval → Generation
- **Multi-model Support**: Abstracted model interface supporting various LLM providers
- **OpenRouter Integration**: Automatic usage tracking with 1.3x markup pricing

### Usage Tracking Data Flow (Per Instance) - UPDATED IMPLEMENTATION
```
Client Admin → Settings → Connections → Enter API Key
                ↓
        Auto-sync to Database
                ↓
        Chat Request Made
                ↓
    OpenRouter Streaming Response (SSE)
                ↓
     Background Sync (Every 10 min)
                ↓
    Poll OpenRouter /generation API
                ↓
    Fetch Actual Usage Data
                ↓
    External User Auto-Learned
                ↓
    Database Recording with Aggregation
                ↓
     Admin Dashboard Updates (Live)
```
LLM Integration Architecture
Model Abstraction
Unified Interface: Common API for different LLM providers
Provider Support: OpenAI, Anthropic, Google, Ollama, custom APIs
Model Management: Dynamic model loading and configuration
Streaming Support: Real-time response streaming
RAG Implementation
Document Processing: Multi-format document ingestion (Unstructured, PyPDF, python-pptx, docx2txt)
Vector Storage: Multiple vector database backends
Retrieval Strategies: Various search and ranking algorithms
Context Management: Intelligent context window management
Security Features
Authentication: JWT with configurable expiration
Authorization: Role-based access control (RBAC)
Input Validation: Pydantic models for request validation
CORS: Configurable cross-origin resource sharing
Rate Limiting: Built-in API rate limiting
File Upload Security: Type validation and size limits
Performance Considerations
Frontend Optimization
Code Splitting: Dynamic imports for route-based splitting
Asset Optimization: Vite's built-in optimization
Service Worker: PWA capabilities for offline access
Lazy Loading: Virtual scrolling for large lists
Backend Optimization
Database Indexing: Proper indexes on frequently queried fields
Connection Pooling: SQLAlchemy connection management
Caching: Redis integration for session and data caching
Async Operations: FastAPI's async capabilities for I/O operations
Background Tasks: OpenRouter usage sync service with automatic startup/shutdown
Customization Framework
Theme System
CSS Variables: Theme-based styling system in static/themes/
Asset Replacement: Logo and favicon customization
Brand Colors: Configurable color schemes
Layout Customization: Flexible UI component arrangement
Internationalization
i18next: Full i18n support with 20+ languages
Dynamic Loading: Lazy-loaded translation files in src/lib/i18n/locales/
RTL Support: Right-to-left language support
Pluralization: Advanced plural form handling
Environment Configuration
Key Environment Variables
bash
# Core
PORT=8080                    # Backend server port
ENV=dev|prod                # Environment mode
WEBUI_NAME=mAI              # Application name
WEBUI_URL=http://localhost   # Application URL

# AI Integration
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=sk-...
HF_HUB_OFFLINE=1            # Offline mode

# Database
DATABASE_URL=sqlite:///./webui.db
Audio & Media Processing
FFmpeg: Full audio processing support (installed)
Faster-whisper: Speech transcription
Audio Upload: Chunked uploads with progress tracking
Format Support: Multiple audio/video formats
