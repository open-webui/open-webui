<div align="center">

# 🚀 Open WebUI

### Extensible, Feature-Rich, Self-Hosted AI Platform

**Open WebUI is a comprehensive, enterprise-grade AI deployment solution designed to operate entirely offline. It provides a unified interface for various LLM providers while offering advanced features like RAG, image generation, collaborative tools, and extensive customization options.**

---

[![GitHub Stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)](https://github.com/open-webui/open-webui/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)](https://github.com/open-webui/open-webui/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/open-webui/open-webui)](https://github.com/open-webui/open-webui/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/open-webui/open-webui)](https://github.com/open-webui/open-webui/pulls)
[![License](https://img.shields.io/github/license/open-webui/open-webui)](./LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)

[**📚 Documentation**](https://docs.openwebui.com) • [**🌟 Features**](#-key-features) • [**🚀 Quick Start**](#-quick-start) • [**💼 Enterprise**](https://docs.openwebui.com/enterprise) • [**👥 Community**](https://discord.gg/5rJgQTnV4s)

</div>

---

![Open WebUI Demo](./demo.gif)

## 📖 Table of Contents

- [Overview](#-overview)
- [Why Open WebUI?](#-why-open-webui)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation Methods](#-installation-methods)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Contributing](#-contributing)
- [Security](#-security)
- [Support](#-support)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🌟 Overview

**Open WebUI** is a self-hosted, extensible web interface that brings together the best of modern AI capabilities into a single, unified platform. Whether you're running local models with Ollama, connecting to OpenAI, Anthropic, Google Gemini, or any OpenAI-compatible API, Open WebUI provides a seamless, feature-rich experience.

### What Makes It Special?

- **🔒 Privacy-First**: Operates entirely offline with no external dependencies
- **🎯 Unified Interface**: Single UI for all your LLM providers (Ollama, OpenAI, Claude, Gemini, etc.)
- **🧩 Extensible**: Plugin system, custom Python functions, pipeline middleware
- **🏢 Enterprise-Ready**: SCIM 2.0, LDAP, RBAC, audit logging, multi-tenancy
- **📚 Production-Grade RAG**: 11 vector databases, hybrid search, advanced document processing
- **👥 Collaboration**: Built-in team channels, real-time collaborative notes
- **🎨 Rich Media**: Image generation, voice/video calls, speech-to-text, text-to-speech
- **🌐 Fully Internationalized**: Support for 30+ languages

> [!TIP]
> **Looking for an [Enterprise Plan](https://docs.openwebui.com/enterprise)?** Get enhanced capabilities including custom theming, SLA support, LTS versions, and more. **[Contact Sales →](https://docs.openwebui.com/enterprise)**

> [!NOTE]
> **Passionate about open-source AI?** We're hiring! [Join our team →](https://careers.openwebui.com/)

---

## 🎯 Why Open WebUI?

### Compared to Other Solutions

| Feature | Open WebUI | ChatGPT UI | LibreChat | Other OSS |
|---------|-----------|------------|-----------|-----------|
| **Offline-First** | ✅ Complete | ⚠️ Partial | ⚠️ Partial | ❌ No |
| **Production RAG** | ✅ 11 Vector DBs | ❌ Basic | ⚠️ Limited | ⚠️ Limited |
| **Enterprise Auth** | ✅ SCIM + LDAP | ❌ No | ⚠️ Basic | ❌ No |
| **Collaboration** | ✅ Channels + Notes | ❌ No | ❌ No | ❌ No |
| **Plugin System** | ✅ Pipelines + MCP | ❌ No | ⚠️ Limited | ❌ No |
| **Image Generation** | ✅ Multiple Engines | ❌ No | ⚠️ Limited | ❌ No |
| **Code Execution** | ✅ Pyodide + Jupyter | ❌ No | ❌ No | ❌ No |
| **Multi-Tenancy** | ✅ Full Support | ❌ No | ❌ No | ❌ No |
| **Web Search** | ✅ 24 Providers | ❌ No | ⚠️ Limited | ⚠️ Limited |

---

## ✨ Key Features

### 🤖 Multi-Model Support

<details>
<summary><b>Unified Interface for All LLM Providers</b></summary>

- **Native Ollama Integration**: Automatic model discovery, pull, create, and manage
- **OpenAI-Compatible APIs**: OpenAI, Azure OpenAI, Anthropic Claude, Google Gemini
- **Custom Endpoints**: LMStudio, GroqCloud, Mistral, OpenRouter, Together AI, and more
- **Multi-Model Conversations**: Query multiple models simultaneously
- **Arena Mode**: Side-by-side model comparison
- **Model Builder**: Create custom Ollama models via the UI
- **Pipeline Middleware**: Transform requests/responses with custom logic

</details>

### 📚 Production-Grade RAG (Retrieval Augmented Generation)

<details>
<summary><b>Advanced Document Intelligence & Vector Search</b></summary>

#### Vector Database Support (11 Options)
- **ChromaDB** (default)
- **Qdrant** (with multi-tenancy)
- **Milvus** (with multi-tenancy)
- **Pinecone**
- **OpenSearch**
- **Elasticsearch**
- **PostgreSQL with pgvector**
- **Oracle 23ai Vector**
- **S3Vector**
- **MongoDB**
- **In-Memory Vector Store**

#### Document Processing
- **Document Loaders**:
  - PDF (PyPDF, MinerU, Mistral OCR, Azure Document Intelligence, Tika, Marker, Docling)
  - Office Files (DOCX, PPTX, XLSX, XLS, RTF)
  - Text Formats (MD, TXT, CSV, JSON, YAML)
  - YouTube Transcripts (automatic extraction)
  - Web Pages (external document loader, Firecrawl)
  - Images with OCR (RapidOCR, Tesseract)
  - Audio/Video (Whisper transcription)

- **Advanced Features**:
  - **Hybrid Search**: BM25 + vector search with configurable weights
  - **Reranking Models**: Improve retrieval quality with dedicated reranking
  - **Knowledge Bases**: Organized collections with file management
  - **Query Augmentation**: Automatic query expansion and refinement
  - **Citation Support**: Source attribution with confidence scores
  - **Chunk Management**: Customizable chunking strategies

</details>

### 🔐 Enterprise Authentication & Authorization

<details>
<summary><b>Comprehensive Security & Access Control</b></summary>

#### Authentication Methods
- **Email/Password**: Bcrypt + Argon2 hashing
- **OAuth 2.0/OIDC**: Google, Microsoft, GitHub, custom providers
- **LDAP/Active Directory**: Full integration with group sync
- **Trusted Header Authentication**: Reverse proxy integration
- **API Keys**: With optional endpoint restrictions

#### Authorization & Access Control
- **Role-Based Access Control (RBAC)**:
  - Admin, User, Pending roles
  - Granular permissions system
  - Custom role creation
- **User Groups**: Team organization with group-based permissions
- **SCIM 2.0 Provisioning**: Enterprise-grade user lifecycle management
  - Okta integration
  - Azure AD sync
  - Google Workspace integration
- **Session Management**: JWT tokens with configurable expiration
- **API Security**: Rate limiting, IP whitelisting, audit logging

</details>

### 🎨 Image Generation

<details>
<summary><b>Multiple Engines & Advanced Editing</b></summary>

#### Supported Engines
- **AUTOMATIC1111** (Stable Diffusion)
  - Customizable parameters via JSON
  - Full control over sampling, steps, CFG scale
- **ComfyUI**
  - Custom workflow support with visual editor
  - Advanced node-based image generation
- **OpenAI DALL-E**
  - DALL-E 2 and DALL-E 3
  - Quality and size options
- **Google Gemini**
  - Gemini 2.5 Flash Image (Nano Banana)
  - Integrated with Gemini models

#### Features
- **Image Editing**: Modify existing images with text prompts
- **Prompt Generation**: AI-assisted prompt enhancement
- **In-Chat Generation**: Generate images directly in conversations
- **Custom Parameters**: Per-engine configuration options
- **Workflow Management**: Save and reuse generation workflows

</details>

### 🎤 Voice & Audio Features

<details>
<summary><b>Speech Recognition & Synthesis</b></summary>

#### Speech-to-Text (STT)
- **OpenAI Whisper** (local via faster-whisper)
- **Azure Speech Services**
- **Mistral API** (Voxtral models)
- **OpenAI API**
- **Web Speech API** (browser-based)

#### Text-to-Speech (TTS)
- **OpenAI TTS**: Multiple voice options
- **Azure Speech Services**: Neural voices
- **ElevenLabs**: High-quality voice synthesis
- **Kokoro.js**: Local browser-based TTS
- **Mistral Voxtral**: voxtral-small, voxtral-mini

#### Advanced Audio
- **Voice/Video Calls**: WebRTC integration for hands-free conversations
- **Global Audio Queue**: Prevent overlapping playback
- **Auto-Send**: Instant submission after transcription
- **Format Support**: Multiple audio formats via PyDub

</details>

### 🛠️ Tools & Functions System

<details>
<summary><b>Native Python Functions & External Tool Integration</b></summary>

#### Native Python Functions
- **Built-in Code Editor**: CodeMirror with Python syntax highlighting
- **Live Editing**: Real-time function development and testing
- **User & System Valves**: Per-function configuration with user overrides
- **GitHub Integration**: Load functions directly from repositories
- **Bring Your Own Function (BYOF)**: Pure Python functions with LLM integration

#### Tool Server Integration
- **Model Context Protocol (MCP)**: Standardized tool integration
- **OpenAPI Servers**: Connect to any OpenAPI-compliant service
- **OAuth 2.1 Support**: Secure authentication for external tools
- **Tool Discovery**: Automatic tool enumeration and documentation
- **Streaming Support**: Real-time tool execution feedback

#### Pre-built Tools
- Web search (24 providers)
- Weather information
- Calculations and conversions
- File operations
- Database queries
- Custom integrations

</details>

### 🔍 Web Search Integration

<details>
<summary><b>24 Search Providers for Enhanced RAG</b></summary>

- **SearXNG** (self-hosted meta-search)
- **Google Programmable Search Engine**
- **Brave Search**
- **DuckDuckGo**
- **Bing**
- **Kagi**
- **Mojeek**
- **Serper**
- **Serpstack**
- **Serply**
- **SerpAPI**
- **SearchAPI**
- **Tavily**
- **Perplexity**
- **Exa**
- **Firecrawl**
- **Jina Search**
- **Ollama** (local model search)
- **YaCy**
- **Sougou**
- **Bocha**
- **Custom Providers** (extensible)

**Features**:
- Inject search results directly into chat
- Configure per-user or global search providers
- SSL verification and proxy support
- Rate limiting and caching
- Asynchronous search execution

</details>

### 👥 Collaboration Features

<details>
<summary><b>Team Channels & Real-Time Collaboration</b></summary>

#### Channels (Team Chat)
- **Slack-like Interface**: Familiar team communication
- **@Mentions**: Tag users and models
- **Threading**: Organized conversations
- **Real-time Updates**: WebSocket-based live sync
- **Permissions**: Channel-level access control
- **File Sharing**: Share documents within channels

#### Collaborative Notes
- **Real-time Editing**: CRDT-based (Y.js) conflict-free collaboration
- **Markdown Support**: Rich formatting with preview
- **Version History**: Track changes and rollback
- **Sharing Controls**: Public, private, or user-specific
- **PDF Export**: Export notes with dark mode support
- **Search Integration**: Full-text search across all notes

#### Shared Conversations
- **Share Chats**: Grant access to specific users or groups
- **Permissions**: Read-only or edit access
- **Link Sharing**: Generate shareable links
- **Community Sharing**: Share to openwebui.com (optional)

</details>

### 💻 Code Execution

<details>
<summary><b>In-Browser Python & Jupyter Integration</b></summary>

#### Pyodide (Browser-based Python)
- **Zero Server Setup**: Runs entirely in the browser
- **NumPy, Pandas, Matplotlib**: Pre-loaded scientific libraries
- **Sandboxed Environment**: Secure execution
- **Persistent State**: Maintain variables across executions

#### Jupyter Kernel Integration
- **Connect to Jupyter Servers**: Local or remote kernels
- **Multi-language Support**: Python, R, Julia, and more
- **Rich Output**: Plots, tables, interactive visualizations
- **Notebook-like Experience**: Cell-based execution

#### Code Interpreter
- **Automatic Code Generation**: LLM generates and executes code
- **Error Handling**: Automatic retry with error context
- **Output Capture**: Display results inline in chat
- **Security**: Restricted Python with RestrictedPython

</details>

### 🏢 Enterprise Features

<details>
<summary><b>Production-Ready Deployment & Management</b></summary>

#### User Management
- **SCIM 2.0 Provisioning**: Automated user lifecycle management
  - Create, update, deactivate users
  - Group synchronization
  - Identity provider integration (Okta, Azure AD, Google Workspace)
- **LDAP/Active Directory**:
  - User authentication
  - Group mapping
  - Nested group support
  - Configurable search filters
- **Bulk Operations**: Import/export users, batch role assignments

#### Monitoring & Analytics
- **Audit Logging**: Comprehensive request/response logging
- **Usage Analytics**:
  - Model performance metrics
  - User activity tracking
  - Token consumption monitoring
  - Cost attribution
- **OpenTelemetry Integration**:
  - Distributed tracing
  - Metrics export
  - Log aggregation
  - Grafana/Prometheus compatible

#### High Availability
- **Redis Clustering**: Distributed state management
- **Horizontal Scaling**: Multi-instance deployment
- **Load Balancing**: Session affinity support
- **Database Options**: PostgreSQL, MySQL for production
- **Storage Backends**: S3, Google Cloud Storage, Azure Blob Storage

#### Customization
- **Custom Theming**: Enterprise branding (Enterprise Plan)
- **White-labeling**: Remove "Open WebUI" branding (Enterprise Plan)
- **Custom Domain**: Full control over deployment URL
- **Custom Login Page**: Branded authentication flows

</details>

### 🌐 Additional Features

<details>
<summary><b>More Capabilities</b></summary>

- **Responsive Design**: Desktop, laptop, tablet, mobile support
- **Progressive Web App (PWA)**: Install as native app, offline support
- **Full Markdown & LaTeX**: Rich text rendering with KaTeX
- **Syntax Highlighting**: 100+ languages via highlight.js
- **Mermaid Diagrams**: Flowcharts, sequence diagrams, Gantt charts
- **Vega & Vega-Lite**: Data visualizations and charts
- **Chart.js Integration**: Interactive analytics dashboards
- **Multilingual**: 30+ languages with i18n support
- **Dark Mode**: System-aware theme switching
- **Keyboard Shortcuts**: International layout support
- **Accessibility**: Screen reader support, ARIA labels
- **Folder Organization**: Hierarchical chat organization
- **Tag System**: Auto-tagging and manual tags
- **Export Options**: JSON, PDF, text formats
- **Import Chats**: From other platforms (ChatGPT, etc.)

</details>

---

## 🏗️ Architecture

### Technology Stack

#### Frontend
```
- Framework: SvelteKit 2.x with Svelte 5.0
- Language: TypeScript
- Styling: TailwindCSS 4.0
- State: Svelte Stores + IndexedDB
- Real-time: Socket.IO Client
- Rich Text: TipTap, ProseMirror
- Code Editor: CodeMirror 6
- Charts: Chart.js, Vega-Lite
- Diagrams: Mermaid
- Build: Vite 5.x
```

#### Backend
```
- Framework: FastAPI 0.118
- Server: Uvicorn (async)
- Language: Python 3.11-3.12
- ORM: SQLAlchemy 2.0 + Peewee
- Migrations: Alembic
- Real-time: Socket.IO Server
- Auth: JWT, OAuth 2.0, LDAP
- Task Queue: APScheduler
```

#### Database Support
```
- Primary: SQLite, PostgreSQL, MySQL
- Vector: Chroma, Qdrant, Milvus, Pinecone, OpenSearch,
         Elasticsearch, PGVector, Oracle 23ai, S3Vector
- Cache: Redis (optional)
- Storage: Local, S3, GCS, Azure Blob
```

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Browser   │  │  Mobile PWA  │  │  Desktop App     │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
└─────────┼────────────────┼───────────────────┼──────────────┘
          │                │                   │
          └────────────────┴───────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │     SvelteKit Frontend          │
          │   (Static or Node Adapter)      │
          └────────────────┬────────────────┘
                           │
┌──────────────────────────┴─────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Auth    │  │   Chat    │  │   RAG    │  │  Admin   │  │
│  │ Router   │  │  Router   │  │ Router   │  │ Router   │  │
│  └────┬─────┘  └─────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │             │         │
│  ┌────┴──────────────┴──────────────┴─────────────┴─────┐  │
│  │              Core Application Layer                   │  │
│  │  - Request Validation  - Business Logic              │  │
│  │  - Pipeline Middleware - Error Handling              │  │
│  └────┬──────────────┬──────────────┬─────────────┬─────┘  │
└───────┼──────────────┼──────────────┼─────────────┼────────┘
        │              │              │             │
┌───────┴────┐  ┌──────┴──────┐  ┌───┴────┐  ┌────┴────────┐
│  Database  │  │   Vector    │  │ Redis  │  │  External   │
│  (SQL)     │  │   Database  │  │ Cache  │  │  Services   │
│            │  │             │  │        │  │             │
│ SQLite/    │  │ Chroma/     │  │ (opt.) │  │ - Ollama    │
│ PostgreSQL │  │ Qdrant/etc  │  │        │  │ - OpenAI    │
└────────────┘  └─────────────┘  └────────┘  │ - S3/GCS    │
                                              │ - LDAP/SSO  │
                                              └─────────────┘
```

### Communication Flow

```
User Request → SvelteKit → FastAPI → Pipelines → LLM Provider
                              ↓
                         Vector DB (for RAG)
                              ↓
                         Response Processing
                              ↓
                         Pipeline Filters
                              ↓
                         WebSocket/SSE
                              ↓
                         Client Update
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** (recommended) OR
- **Python 3.11+** for pip installation
- **Node.js 18.13+** for development

### Fastest Setup (Docker with Ollama)

```bash
# Run Open WebUI with bundled Ollama (GPU support)
docker run -d \
  -p 3000:8080 \
  --gpus=all \
  -v ollama:/root/.ollama \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:ollama
```

**Access**: http://localhost:3000

### Alternative: Docker with Existing Ollama

```bash
# If Ollama is already running on your machine
docker run -d \
  -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

### Python pip Installation

```bash
# Install
pip install open-webui

# Run
open-webui serve
```

**Access**: http://localhost:8080

### First-Time Setup

1. **Create Admin Account**: On first launch, the signup page will appear
2. **Configure Model**: Add Ollama or OpenAI API credentials in Settings
3. **Start Chatting**: Select a model and begin your conversation

---

## 📦 Installation Methods

### Docker Installations

<details>
<summary><b>Docker with GPU Support (NVIDIA)</b></summary>

**Prerequisites**: Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

```bash
docker run -d \
  -p 3000:8080 \
  --gpus all \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:cuda
```

</details>

<details>
<summary><b>Docker with AMD GPU Support</b></summary>

```bash
docker run -d \
  -p 3000:8080 \
  --device /dev/kfd \
  --device /dev/dri \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

</details>

<details>
<summary><b>Docker with Remote Ollama</b></summary>

```bash
docker run -d \
  -p 3000:8080 \
  -e OLLAMA_BASE_URL=https://example.com \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

</details>

<details>
<summary><b>Docker with OpenAI Only</b></summary>

```bash
docker run -d \
  -p 3000:8080 \
  -e OPENAI_API_KEY=your_secret_key \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

</details>

<details>
<summary><b>Docker Compose</b></summary>

Create `docker-compose.yaml`:

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    ports:
      - "3000:8080"
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
    volumes:
      - open-webui:/app/backend/data
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: always

volumes:
  open-webui:
```

Run: `docker-compose up -d`

</details>

### Kubernetes Deployments

<details>
<summary><b>Kubernetes with kubectl (CPU only)</b></summary>

```bash
kubectl apply -f ./kubernetes/manifest/base
```

</details>

<details>
<summary><b>Kubernetes with Kustomize (GPU support)</b></summary>

```bash
kubectl apply -k ./kubernetes/manifest
```

</details>

<details>
<summary><b>Helm Chart</b></summary>

```bash
# Package chart
helm package ./kubernetes/helm/

# Install (CPU only)
helm install open-webui ./open-webui-*.tgz

# Install (with GPU)
helm install open-webui ./open-webui-*.tgz \
  --set ollama.resources.limits.nvidia.com/gpu="1"

# Custom values
helm install open-webui ./open-webui-*.tgz \
  -f custom-values.yaml
```

See `kubernetes/helm/values.yaml` for all configuration options.

</details>

### Python pip Installation

<details>
<summary><b>Standard Installation</b></summary>

```bash
# Ensure Python 3.11
python --version

# Install
pip install open-webui

# Run
open-webui serve

# Optional: Specify host and port
open-webui serve --host 0.0.0.0 --port 8080
```

</details>

<details>
<summary><b>PostgreSQL Support</b></summary>

```bash
pip install open-webui[postgres]

# Set environment variable
export DATABASE_URL=postgresql://user:password@localhost/openwebui

open-webui serve
```

</details>

### Development Installation

<details>
<summary><b>Local Development Setup</b></summary>

```bash
# Clone repository
git clone https://github.com/open-webui/open-webui.git
cd open-webui

# Frontend setup
npm install
npm run dev  # Runs on http://localhost:5173

# Backend setup (separate terminal)
cd backend
pip install -r requirements.txt
bash dev.sh  # Runs on http://localhost:8080
```

See [Development Guide](https://docs.openwebui.com/getting-started/advanced-topics/development) for details.

</details>

### Updating Open WebUI

<details>
<summary><b>Docker Update Methods</b></summary>

**Manual Update:**
```bash
docker stop open-webui
docker rm open-webui
docker pull ghcr.io/open-webui/open-webui:main
# Run your original docker run command again
```

**Watchtower (Automatic):**
```bash
docker run --rm \
  --volume /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --run-once open-webui
```

</details>

<details>
<summary><b>Pip Update</b></summary>

```bash
pip install --upgrade open-webui
```

</details>

---

## ⚙️ Configuration

### Environment Variables

Open WebUI supports **200+ environment variables** for extensive customization. Below are the most commonly used:

<details>
<summary><b>Core Configuration</b></summary>

```bash
# Database
DATABASE_URL=sqlite:///data/webui.db
# or PostgreSQL: postgresql://user:pass@localhost/openwebui
# or MySQL: mysql://user:pass@localhost/openwebui

# Security
WEBUI_SECRET_KEY=your-secret-key-min-12-chars
CORS_ALLOW_ORIGIN=*
FORWARDED_ALLOW_IPS=*

# Data Directory
DATA_DIR=/app/backend/data

# Redis (optional, for distributed deployments)
REDIS_URL=redis://localhost:6379/0

# Server
HOST=0.0.0.0
PORT=8080
```

</details>

<details>
<summary><b>LLM Provider Configuration</b></summary>

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
# Multiple Ollama instances:
OLLAMA_BASE_URLS=http://ollama1:11434;http://ollama2:11434
ENABLE_OLLAMA_API=true

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_API_BASE_URL=https://api.openai.com/v1
# Multiple OpenAI endpoints:
OPENAI_API_BASE_URLS=https://api.openai.com/v1;https://custom.api/v1
OPENAI_API_KEYS=sk-key1;sk-key2
ENABLE_OPENAI_API=true

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GOOGLE_API_KEY=...

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

</details>

<details>
<summary><b>RAG Configuration</b></summary>

```bash
# Vector Database
VECTOR_DB=chroma  # chroma|qdrant|milvus|pinecone|opensearch|pgvector|oracle23ai
CHROMA_TENANT=default
CHROMA_DATABASE=default
CHROMA_HTTP_HOST=localhost
CHROMA_HTTP_PORT=8000

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...
ENABLE_QDRANT_MULTI_TENANCY=false

# Milvus
MILVUS_URI=http://localhost:19530
ENABLE_MILVUS_MULTI_TENANCY=false

# Embeddings
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE=false

# Reranking
RAG_RERANKING_MODEL=

# Search Configuration
RAG_TOP_K=5
RAG_RELEVANCE_THRESHOLD=0.0
ENABLE_RAG_HYBRID_SEARCH=false
RAG_HYBRID_SEARCH_ALPHA=0.5  # 0=BM25, 1=vector

# File Upload
RAG_FILE_MAX_SIZE=10  # MB
RAG_FILE_MAX_COUNT=10

# Document Processing
PDF_EXTRACT_IMAGES=false
CONTENT_EXTRACTION_ENGINE=tika  # tika|unstructured|default
TIKA_SERVER_URL=http://localhost:9998
```

</details>

<details>
<summary><b>Authentication Configuration</b></summary>

```bash
# General Auth
ENABLE_SIGNUP=true
ENABLE_LOGIN_FORM=true
DEFAULT_USER_ROLE=pending  # admin|user|pending
ENABLE_OAUTH_SIGNUP=true
ENABLE_API_KEY=true

# OAuth/OIDC
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=false
ENABLE_OAUTH_ROLE_MANAGEMENT=false
OAUTH_ALLOWED_ROLES=user,admin
OAUTH_ADMIN_ROLES=admin
OAUTH_ROLES_CLAIM=roles
OAUTH_ROLES_SEPARATOR=,

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_OAUTH_SCOPE=openid email profile

# Microsoft OAuth
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_CLIENT_TENANT_ID=...

# Generic OIDC
OPENID_PROVIDER_URL=https://auth.example.com
OAUTH_CLIENT_ID=...
OAUTH_CLIENT_SECRET=...
OAUTH_SCOPES=openid email profile

# LDAP
ENABLE_LDAP=false
LDAP_SERVER_LABEL=LDAP
LDAP_SERVER_HOST=localhost
LDAP_SERVER_PORT=389
LDAP_USE_TLS=true
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=...
LDAP_USER_BASE=ou=users,dc=example,dc=com
LDAP_USER_FILTER=(objectClass=inetOrgPerson)

# SCIM 2.0
SCIM_ENABLED=false
SCIM_TOKEN=your-scim-bearer-token
```

</details>

<details>
<summary><b>Image Generation Configuration</b></summary>

```bash
# Engine Selection
IMAGE_GENERATION_ENGINE=automatic1111  # automatic1111|comfyui|openai

# AUTOMATIC1111
AUTOMATIC1111_BASE_URL=http://localhost:7860
AUTOMATIC1111_PARAMS={"sampler":"DPM++ 2M Karras","steps":30}

# ComfyUI
COMFYUI_BASE_URL=http://localhost:8188
COMFYUI_WORKFLOW={}  # JSON workflow

# OpenAI DALL-E
IMAGE_GENERATION_MODEL=dall-e-3
IMAGES_OPENAI_API_BASE_URL=https://api.openai.com/v1
IMAGES_OPENAI_API_KEY=sk-...

# General
IMAGE_SIZE=512x512
IMAGE_STEPS=50
ENABLE_IMAGE_GENERATION=true
```

</details>

<details>
<summary><b>Audio Configuration</b></summary>

```bash
# Speech-to-Text
AUDIO_STT_ENGINE=openai  # openai|web|azure|mistral
AUDIO_STT_MODEL=whisper-1
OPENAI_API_KEY=sk-...
AUDIO_STT_OPENAI_API_BASE_URL=https://api.openai.com/v1

# Azure STT
AUDIO_STT_AZURE_SPEECH_REGION=...
AUDIO_STT_AZURE_SPEECH_KEY=...

# Text-to-Speech
AUDIO_TTS_ENGINE=openai  # openai|azure|kokoro
AUDIO_TTS_MODEL=tts-1
AUDIO_TTS_VOICE=alloy
AUDIO_TTS_OPENAI_API_BASE_URL=https://api.openai.com/v1

# Azure TTS
AUDIO_TTS_AZURE_SPEECH_REGION=...
AUDIO_TTS_AZURE_SPEECH_KEY=...

# ElevenLabs
ELEVENLABS_API_KEY=...
ELEVENLABS_API_BASE_URL=https://api.elevenlabs.io/v1
```

</details>

<details>
<summary><b>Web Search Configuration</b></summary>

```bash
# Enable Web Search
ENABLE_RAG_WEB_SEARCH=true

# Provider Selection
RAG_WEB_SEARCH_ENGINE=searxng  # See full list in features

# SearXNG
SEARXNG_QUERY_URL=http://localhost:8080/search?q=<query>

# Google PSE
GOOGLE_PSE_API_KEY=...
GOOGLE_PSE_ENGINE_ID=...

# Brave Search
BRAVE_SEARCH_API_KEY=...

# Serper
SERPER_API_KEY=...

# Tavily
TAVILY_API_KEY=...

# General
RAG_WEB_SEARCH_RESULT_COUNT=3
RAG_WEB_SEARCH_CONCURRENT_REQUESTS=10
WEB_SEARCH_TRUST_ENV=true  # Use HTTP proxy
```

</details>

<details>
<summary><b>Feature Flags</b></summary>

```bash
# Features
ENABLE_WEBSOCKET_SUPPORT=true
ENABLE_CHANNELS=true
ENABLE_NOTES=true
ENABLE_CODE_EXECUTION=false
ENABLE_COMMUNITY_SHARING=true
ENABLE_MESSAGE_RATING=true

# UI Features
ENABLE_MODEL_FILTER=true
ENABLE_MESSAGE_DELETION=true
ENABLE_MESSAGE_EDITING=true
ENABLE_IMAGE_GENERATION=true

# Admin Controls
USER_PERMISSIONS_CHAT_DELETION=true
USER_PERMISSIONS_CHAT_EDITING=true
USER_PERMISSIONS_CHAT_TEMPORARY=true

# Telemetry
SCARF_NO_ANALYTICS=true
DO_NOT_TRACK=true
ANONYMIZED_TELEMETRY=false
```

</details>

<details>
<summary><b>Storage Configuration</b></summary>

```bash
# Storage Provider
STORAGE_PROVIDER=local  # local|s3|gcs|azure

# S3
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=open-webui
S3_REGION_NAME=us-east-1
S3_ENDPOINT_URL=  # For S3-compatible services

# Google Cloud Storage
GCS_CREDENTIALS_PATH=/path/to/credentials.json
GCS_BUCKET_NAME=open-webui

# Azure Blob Storage
AZURE_STORAGE_ACCOUNT_NAME=...
AZURE_STORAGE_ACCOUNT_KEY=...
AZURE_CONTAINER_NAME=open-webui
```

</details>

<details>
<summary><b>Monitoring & Logging</b></summary>

```bash
# Logging
GLOBAL_LOG_LEVEL=INFO  # DEBUG|INFO|WARNING|ERROR
LOG_REQUESTS=false

# OpenTelemetry
ENABLE_OPENTELEMETRY=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=open-webui

# Audit Logging
AUDIT_LOG_DIR=/app/backend/data/audit
```

</details>

### Configuration File

Alternatively, create a `.env` file in the data directory:

```bash
# Copy example
cp .env.example .env

# Edit with your values
nano .env
```

For a complete list of environment variables, see the [Configuration Documentation](https://docs.openwebui.com/getting-started/env-configuration).

---

## 📁 Project Structure

```
open-webui/
├── backend/                    # Python FastAPI backend
│   ├── open_webui/
│   │   ├── main.py            # FastAPI application entry
│   │   ├── config.py          # Configuration management
│   │   ├── env.py             # Environment variable handling
│   │   ├── routers/           # API endpoint routers
│   │   │   ├── auths.py       # Authentication endpoints
│   │   │   ├── chats.py       # Chat management
│   │   │   ├── channels.py    # Team channels
│   │   │   ├── notes.py       # Collaborative notes
│   │   │   ├── retrieval.py   # RAG operations
│   │   │   ├── ollama.py      # Ollama proxy
│   │   │   ├── openai.py      # OpenAI-compatible API
│   │   │   ├── pipelines.py   # Pipeline middleware
│   │   │   ├── functions.py   # Python functions
│   │   │   ├── tools.py       # Tool management
│   │   │   ├── knowledge.py   # Knowledge bases
│   │   │   ├── images.py      # Image generation
│   │   │   ├── audio.py       # STT/TTS
│   │   │   ├── scim.py        # SCIM provisioning
│   │   │   └── ...
│   │   ├── models/            # Database models (SQLAlchemy/Peewee)
│   │   ├── retrieval/         # RAG implementation
│   │   │   ├── loaders/       # Document loaders (PDF, DOCX, etc.)
│   │   │   ├── vector/        # Vector database clients
│   │   │   │   └── dbs/       # 11 vector DB implementations
│   │   │   └── web/           # Web search providers (24+)
│   │   ├── socket/            # WebSocket handlers
│   │   ├── utils/             # Utility functions
│   │   │   ├── mcp/           # Model Context Protocol
│   │   │   ├── auth.py        # Auth utilities
│   │   │   └── ...
│   │   ├── storage/           # Storage providers (S3, GCS, Azure)
│   │   ├── migrations/        # Database migrations (Alembic)
│   │   └── test/              # Backend tests
│   ├── requirements.txt       # Python dependencies
│   └── data/                  # Runtime data (database, uploads)
│
├── src/                       # SvelteKit frontend
│   ├── lib/
│   │   ├── apis/              # API client functions
│   │   ├── components/        # Svelte components
│   │   │   ├── chat/          # Chat interface components
│   │   │   ├── admin/         # Admin panel components
│   │   │   ├── workspace/     # Workspace (models, tools, knowledge)
│   │   │   ├── channel/       # Channel UI components
│   │   │   ├── notes/         # Collaborative notes editor
│   │   │   ├── common/        # Shared components
│   │   │   └── ...
│   │   ├── stores/            # Svelte stores (state management)
│   │   ├── i18n/              # Internationalization (30+ languages)
│   │   │   └── locales/       # Translation files
│   │   └── utils/             # Frontend utilities
│   ├── routes/                # SvelteKit routes
│   │   ├── (app)/             # Protected routes (requires auth)
│   │   │   ├── admin/         # Admin dashboard
│   │   │   ├── workspace/     # Workspace pages
│   │   │   ├── channels/      # Team channels
│   │   │   ├── notes/         # Notes editor
│   │   │   ├── playground/    # Model playground
│   │   │   └── +page.svelte   # Main chat interface
│   │   ├── auth/              # Authentication pages
│   │   │   ├── signin/
│   │   │   └── signup/
│   │   └── +layout.svelte     # Root layout
│   ├── app.html               # HTML template
│   └── app.css                # Global styles
│
├── static/                    # Static assets
│   ├── favicon.png
│   └── ...
│
├── kubernetes/                # Kubernetes manifests
│   ├── manifest/              # kubectl/kustomize
│   └── helm/                  # Helm chart
│
├── cypress/                   # E2E tests
├── test/                      # Integration tests
├── docs/                      # Documentation
│   ├── CONTRIBUTING.md
│   ├── SECURITY.md
│   └── ...
│
├── docker-compose.yaml        # Docker Compose setup
├── Dockerfile                 # Multi-stage Docker build
├── package.json               # Frontend dependencies
├── pyproject.toml             # Backend package config
├── vite.config.ts             # Vite build config
├── svelte.config.js           # SvelteKit config
├── tailwind.config.js         # TailwindCSS config
├── tsconfig.json              # TypeScript config
├── .env.example               # Environment variable template
├── CHANGELOG.md               # Version history
├── LICENSE                    # License information
└── README.md                  # This file
```

---

## 🔌 API Documentation

### RESTful API Endpoints

Open WebUI provides a comprehensive REST API for programmatic access:

```
Base URL: http://localhost:8080/api
```

#### Authentication
- `POST /api/auths/signin` - Sign in user
- `POST /api/auths/signup` - Register new user
- `POST /api/auths/signout` - Sign out user
- `GET /api/auths/` - Get current user info
- `POST /api/auths/api-key` - Generate API key
- `GET /api/auths/api-key` - Get API keys

#### Chat Management
- `GET /api/chats/` - List all chats
- `GET /api/chats/{id}` - Get chat by ID
- `POST /api/chats/new` - Create new chat
- `POST /api/chats/{id}` - Update chat
- `DELETE /api/chats/{id}` - Delete chat
- `POST /api/chats/{id}/clone` - Clone chat
- `POST /api/chats/{id}/share` - Share chat
- `GET /api/chats/search` - Search chats
- `GET /api/chats/tags` - Get all tags

#### Models
- `GET /api/models/` - List available models
- `POST /api/models/add` - Add custom model
- `POST /api/models/update` - Update model config
- `DELETE /api/models/{id}` - Delete model

#### RAG & Knowledge
- `GET /api/knowledge/` - List knowledge bases
- `POST /api/knowledge/create` - Create knowledge base
- `POST /api/retrieval/query` - Query documents
- `POST /api/retrieval/upload` - Upload documents
- `POST /api/retrieval/process` - Process documents
- `DELETE /api/knowledge/{id}` - Delete knowledge base

#### Functions & Tools
- `GET /api/functions/` - List functions
- `POST /api/functions/create` - Create function
- `POST /api/functions/update` - Update function
- `GET /api/tools/` - List tool servers
- `POST /api/tools/create` - Add tool server

#### Admin
- `GET /api/users/` - List all users
- `POST /api/users/create` - Create user
- `POST /api/users/{id}/update` - Update user
- `DELETE /api/users/{id}` - Delete user
- `GET /api/groups/` - List groups
- `POST /api/groups/create` - Create group
- `GET /api/configs/` - Get system config
- `POST /api/configs/update` - Update config

#### SCIM 2.0 (Enterprise)
- `GET /api/scim/v2/Users` - List users
- `POST /api/scim/v2/Users` - Create user
- `GET /api/scim/v2/Users/{id}` - Get user
- `PUT /api/scim/v2/Users/{id}` - Update user
- `PATCH /api/scim/v2/Users/{id}` - Partial update
- `DELETE /api/scim/v2/Users/{id}` - Delete user
- `GET /api/scim/v2/Groups` - List groups
- `POST /api/scim/v2/Groups` - Create group

### WebSocket Events

Real-time features use Socket.IO:

```javascript
// Connect to WebSocket
const socket = io('http://localhost:8080', {
  auth: { token: 'your-jwt-token' }
});

// Channel events
socket.emit('channel:join', { channel_id: '...' });
socket.on('channel:message', (data) => { ... });

// Notes events (collaborative editing)
socket.emit('note:connect', { note_id: '...' });
socket.on('note:update', (update) => { ... });

// Notification events
socket.on('notification', (notification) => { ... });
```

### OpenAI-Compatible API

Open WebUI exposes an OpenAI-compatible endpoint:

```bash
# Use with OpenAI SDK
curl http://localhost:8080/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "llama3.1",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

Compatible with:
- OpenAI Python SDK
- LangChain
- LlamaIndex
- Any OpenAI-compatible client

### API Documentation (OpenAPI/Swagger)

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

---

## 🛠️ Development

### Local Development Setup

<details>
<summary><b>Complete Development Environment</b></summary>

```bash
# 1. Clone repository
git clone https://github.com/open-webui/open-webui.git
cd open-webui

# 2. Frontend development
npm install
npm run dev  # Starts on http://localhost:5173

# 3. Backend development (new terminal)
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backend
bash dev.sh  # Starts on http://localhost:8080

# Or manually:
cd open_webui
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

**Development URLs:**
- Frontend (Vite): http://localhost:5173
- Backend (FastAPI): http://localhost:8080
- API Docs: http://localhost:8080/docs

</details>

### Code Structure Guidelines

<details>
<summary><b>Frontend (SvelteKit)</b></summary>

```typescript
// Component structure
src/lib/components/
  ├── chat/           // Chat-specific components
  ├── admin/          // Admin panel components
  ├── workspace/      // Workspace components
  └── common/         // Shared components

// API calls
src/lib/apis/
  ├── chats/          // Chat API functions
  ├── models/         // Model API functions
  └── ...

// State management
src/lib/stores/
  ├── user.ts         // User state
  ├── models.ts       // Models state
  └── ...

// Routing
src/routes/
  ├── (app)/          // Protected routes
  └── auth/           // Public auth routes
```

**Best Practices:**
- Use TypeScript for type safety
- Follow Svelte 5 runes (`$state`, `$derived`, `$effect`)
- Keep components small and focused
- Use stores for cross-component state
- Implement proper error handling

</details>

<details>
<summary><b>Backend (FastAPI)</b></summary>

```python
# Router structure
backend/open_webui/routers/
  ├── auths.py        # Authentication logic
  ├── chats.py        # Chat operations
  └── ...

# Database models
backend/open_webui/models/
  ├── users.py        # User model
  ├── chats.py        # Chat model
  └── ...

# Utilities
backend/open_webui/utils/
  ├── auth.py         # Auth utilities
  └── ...
```

**Best Practices:**
- Use async/await for I/O operations
- Implement proper dependency injection
- Add type hints for all functions
- Use Pydantic for request/response validation
- Write unit tests for business logic
- Document endpoints with docstrings

</details>

### Testing

<details>
<summary><b>Frontend Tests</b></summary>

```bash
# Unit tests (Vitest)
npm run test:frontend

# E2E tests (Cypress)
npm run cy:open
```

</details>

<details>
<summary><b>Backend Tests</b></summary>

```bash
cd backend
pytest

# With coverage
pytest --cov=open_webui --cov-report=html
```

</details>

### Code Quality

<details>
<summary><b>Linting & Formatting</b></summary>

```bash
# Frontend
npm run lint           # ESLint
npm run format         # Prettier

# Backend
npm run lint:backend   # Pylint
npm run format:backend # Black

# All
npm run lint
```

</details>

### Building for Production

<details>
<summary><b>Production Build</b></summary>

```bash
# Frontend build
npm run build

# Backend is packaged with frontend
# The built frontend is served by FastAPI

# Create Python package
pip install build
python -m build

# Docker build
docker build -t open-webui:local .
```

</details>

### Database Migrations

<details>
<summary><b>Alembic Migrations</b></summary>

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

</details>

---

## 🤝 Contributing

We welcome contributions from the community! Open WebUI is built by developers like you.

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Run tests**: `npm run test:frontend && pytest`
5. **Format code**: `npm run format`
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Contribution Guidelines

<details>
<summary><b>Code Contributions</b></summary>

- **Discuss first**: Open an issue or discussion before major changes
- **Follow conventions**: Adhere to existing code style and patterns
- **Write tests**: Include tests for new features
- **Update docs**: Document new features and changes
- **Clear commits**: Write descriptive commit messages
- **Timely completion**: Complete PRs within a reasonable timeframe

</details>

<details>
<summary><b>Documentation</b></summary>

Help improve our documentation:
- Fix typos and clarifications
- Add tutorials and guides
- Improve setup instructions
- Translate documentation

Submit docs PRs to: [open-webui/docs](https://github.com/open-webui/docs)

</details>

<details>
<summary><b>Translations</b></summary>

Add or improve translations:

1. Create language directory: `src/lib/i18n/locales/[language-code]/`
2. Copy `en-US` files and translate
3. Add language to `src/lib/i18n/locales/languages.json`
4. Submit PR with translations only (separate from features)

See [ISO 639 Language Codes](http://www.lingoes.net/en/translator/langcode.htm)

</details>

<details>
<summary><b>Bug Reports</b></summary>

Found a bug? Please open an issue with:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, version, deployment method)
- Relevant logs or screenshots

**Important**: Follow the issue template or your issue may be closed.

</details>

<details>
<summary><b>Feature Requests</b></summary>

Have an idea? Open a discussion:
- Describe the use case
- Explain the benefit
- Provide examples
- Consider implementation approach

</details>

### Code of Conduct

Be respectful, inclusive, and constructive. See [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).

### Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes
- Community spotlights

---

## 🔒 Security

### Reporting Vulnerabilities

**DO NOT** report security vulnerabilities through public issues.

Instead, use [GitHub Security Advisories](https://github.com/open-webui/open-webui/security) to responsibly disclose vulnerabilities.

We take security seriously and will respond promptly to valid reports.

### Security Features

- **Authentication**: Bcrypt + Argon2 password hashing
- **Authorization**: JWT with expiration, RBAC
- **Input Validation**: Pydantic models, DOMPurify sanitization
- **CORS Protection**: Configurable origins
- **Rate Limiting**: API key rate limits
- **Audit Logging**: Track all sensitive operations
- **Secrets Management**: Environment variables, no hardcoded secrets
- **SQL Injection**: Protected via SQLAlchemy ORM
- **XSS Prevention**: Content Security Policy, HTML sanitization
- **CSRF Protection**: Token-based validation

### Security Best Practices

<details>
<summary><b>Deployment Security</b></summary>

- Use strong `WEBUI_SECRET_KEY` (minimum 12 characters)
- Enable HTTPS in production (reverse proxy)
- Set `CORS_ALLOW_ORIGIN` to specific domains
- Restrict `FORWARDED_ALLOW_IPS` to trusted proxies
- Use PostgreSQL/MySQL instead of SQLite in production
- Enable Redis for distributed session management
- Regularly update to latest version
- Monitor audit logs
- Use environment variables for secrets (never commit `.env`)

</details>

<details>
<summary><b>Network Security</b></summary>

```nginx
# Example Nginx reverse proxy with SSL
server {
    listen 443 ssl http2;
    server_name openwebui.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /socket.io {
        proxy_pass http://localhost:8080/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

</details>

For more details, see [docs/SECURITY.md](./docs/SECURITY.md).

---

## 💬 Support

### Community Support

- **Discord**: [Join our server](https://discord.gg/5rJgQTnV4s) - Most active support channel
- **GitHub Discussions**: [Ask questions](https://github.com/open-webui/open-webui/discussions)
- **GitHub Issues**: [Report bugs](https://github.com/open-webui/open-webui/issues)

### Documentation

- **Official Docs**: https://docs.openwebui.com
- **Troubleshooting**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Installation Guide**: [INSTALLATION.md](./INSTALLATION.md)
- **API Reference**: http://localhost:8080/docs (when running)

### Enterprise Support

Need SLA-backed support? Check our [Enterprise Plan](https://docs.openwebui.com/enterprise):
- **Priority Support**: Direct access to core team
- **Custom Development**: Tailored features for your organization
- **Training & Onboarding**: Comprehensive team training
- **Long-Term Support (LTS)**: Stable versions with extended support
- **Custom Theming**: White-label branding options

[**Contact Sales →**](https://docs.openwebui.com/enterprise)

### Frequently Asked Questions

<details>
<summary><b>Can I use Open WebUI without Ollama?</b></summary>

Yes! Open WebUI supports any OpenAI-compatible API. You can use OpenAI, Anthropic, Google Gemini, or any other compatible service.

</details>

<details>
<summary><b>How do I update Open WebUI?</b></summary>

**Docker:**
```bash
docker pull ghcr.io/open-webui/open-webui:main
docker stop open-webui
docker rm open-webui
# Run your original docker run command
```

**Pip:**
```bash
pip install --upgrade open-webui
```

</details>

<details>
<summary><b>Can I use my own models?</b></summary>

Yes! You can:
- Run local models with Ollama
- Create custom Ollama models via the Model Builder
- Connect to custom OpenAI-compatible endpoints
- Use any model supported by your LLM provider

</details>

<details>
<summary><b>Is my data private?</b></summary>

Yes! Open WebUI can operate entirely offline:
- All data stored locally (or your own database)
- No telemetry by default (`DO_NOT_TRACK=true`)
- No external API calls required (when using local models)
- Full control over your deployment

</details>

<details>
<summary><b>Can I deploy Open WebUI for my team?</b></summary>

Absolutely! Open WebUI is designed for team deployments:
- User management with RBAC
- LDAP/SCIM integration for enterprise
- Team channels for collaboration
- Shared knowledge bases
- Group permissions

</details>

<details>
<summary><b>How do I enable RAG?</b></summary>

RAG is built-in:
1. Configure vector database (default: ChromaDB)
2. Upload documents in Settings → Knowledge
3. Use `#` in chat to reference documents
4. Or attach files directly to messages

See [RAG Documentation](https://docs.openwebui.com/features/rag) for details.

</details>

---

## 🗺️ Roadmap

### Current Focus (Q1-Q2 2025)

- [ ] **Enhanced Collaboration**
  - [ ] Threaded conversations in channels
  - [ ] @model mentions with context
  - [ ] Shared workspaces

- [ ] **Advanced RAG**
  - [ ] Graph-based RAG
  - [ ] Multi-hop reasoning
  - [ ] Automatic knowledge base updates

- [ ] **Improved Pipelines**
  - [ ] Visual pipeline builder
  - [ ] More pre-built pipelines
  - [ ] Marketplace for community pipelines

- [ ] **Mobile Experience**
  - [ ] Native mobile apps (iOS/Android)
  - [ ] Improved PWA features
  - [ ] Offline-first sync

- [ ] **Agent Framework**
  - [ ] Multi-agent conversations
  - [ ] Agent orchestration
  - [ ] Custom agent templates

### Future Considerations

- Advanced analytics and insights
- Multi-modal capabilities expansion
- Enhanced enterprise features
- Performance optimizations
- Plugin ecosystem expansion

See [full roadmap](https://docs.openwebui.com/roadmap) for details and vote on features!

### Recent Releases

**v0.6.36** (November 2025)
- OAuth group parsing with configurable separators
- ComfyUI workflow editor improvements
- Tool calling fixes
- Enhanced error handling

**v0.6.35** (November 2025)
- Image generation overhaul with editing support
- Gemini 2.5 Flash Image integration
- CORS validation for WebSockets
- Global audio queue for TTS
- Mistral Voxtral TTS support
- Enhanced keyboard shortcuts

See [CHANGELOG.md](./CHANGELOG.md) for complete version history.

---

## 📄 License

This project contains code under multiple licenses:

- **Current Code**: Open WebUI License (with branding requirements)
- **Historical Code**: See [LICENSE_HISTORY](./LICENSE_HISTORY) for details

**Important**: The current license requires preserving "Open WebUI" branding in the user interface. For white-labeling options, see our [Enterprise Plan](https://docs.openwebui.com/enterprise).

For complete licensing information:
- [LICENSE](./LICENSE) - Current license
- [LICENSE_HISTORY](./LICENSE_HISTORY) - Historical license changes
- [LICENSE_NOTICE](./LICENSE_NOTICE) - License notices

---

## 🙏 Acknowledgments

### Creator

Created by [Timothy Jaeryang Baek](https://github.com/tjbck)

### Contributors

Open WebUI is made possible by amazing contributors:

[![Contributors](https://contrib.rocks/image?repo=open-webui/open-webui)](https://github.com/open-webui/open-webui/graphs/contributors)

### Sponsors

Special thanks to our sponsors who make Open WebUI development sustainable:

[![Sponsor](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/tjbck)

### Technology Stack

Built with amazing open-source technologies:
- [SvelteKit](https://kit.svelte.dev/) - Frontend framework
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Ollama](https://ollama.com/) - Local LLM runner
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [TailwindCSS](https://tailwindcss.com/) - Styling
- And many more...

### Community

Thank you to our vibrant community:
- 50,000+ Discord members
- 500+ contributors
- Thousands of deployments worldwide

---

## 🌟 Star History

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

---

<div align="center">

**[⬆ Back to Top](#-open-webui)**

Made with ❤️ by the Open WebUI community

[Website](https://openwebui.com) • [Documentation](https://docs.openwebui.com) • [Discord](https://discord.gg/5rJgQTnV4s) • [Twitter](https://twitter.com/OpenWebUI)

</div>
