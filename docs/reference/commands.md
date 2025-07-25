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
- **Usage Tracking**: OpenRouter background sync service
Architecture Patterns
Backend Patterns
Dependency Injection: FastAPI's dependency system for database sessions, auth
Repository Pattern: Models in backend/open_webui/models/ with separate business logic
Router Organization: Feature-based routing in routers/ directory
Middleware Chain: Authentication, CORS, compression middleware
Database Abstraction: SQLAlchemy ORM with Alembic migrations
Frontend Patterns
Component Architecture: Feature-based component organization
Store Pattern: Svelte stores for global state management
API Client Pattern: Centralized API functions in src/lib/apis/
Layout Hierarchy: Nested layouts in SvelteKit route structure
Reactive Programming: Svelte's reactive declarations and stores
Data Flow
Authentication: JWT tokens with refresh mechanism
Real-time Updates: Socket.io for live chat and notifications
File Upload: Chunked uploads with progress tracking
RAG Pipeline: Document ingestion → Vector embedding → Retrieval → Generation
Multi-model Support: Abstracted model interface supporting various LLM providers
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

# Usage Tracking
OPENROUTER_USAGE_SYNC_INTERVAL=600  # Background sync interval (10 minutes)
OPENROUTER_USAGE_SYNC_DAYS_BACK=1   # Days to sync backwards
LOG_LEVEL=INFO                      # Logging level for background sync
Audio & Media Processing
FFmpeg: Full audio processing support (installed)
Faster-whisper: Speech transcription
Audio Upload: Chunked uploads with progress tracking
Format Support: Multiple audio/video formats

## Usage Tracking API Endpoints

### Background Sync Service
```bash
# Manual sync trigger (Admin only)
curl -X POST "http://localhost:3000/api/v1/usage-tracking/sync/openrouter-usage" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"days_back": 1}'

# Check real-time usage
curl "http://localhost:3000/api/v1/usage-tracking/usage/real-time/{client_org_id}" \
  -H "Authorization: Bearer {token}"

# Manual usage recording (Testing)
curl -X POST "http://localhost:3000/api/v1/usage-tracking/usage/manual-record" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-ai/deepseek-v3", "tokens": 1000, "cost": 0.002}'
```

### Database Management Tools
```bash
# Initialize database with sample data
python create_tables.py

# Clean usage data safely (preserves configuration)
python clean_usage_database.py

# Complete database reset (use with caution)
python complete_usage_reset.py
```

### Container Health Checks
```bash
# Check background sync status
docker logs mai-container | grep -i "background sync"

# Verify usage data recording
docker exec mai-container python -c "
from datetime import date
import sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM client_live_counters WHERE current_date = ?', (date.today(),))
result = cursor.fetchone()
if result: print(f'Usage: {result[2]} tokens, ${result[5]:.6f}')
else: print('No usage data')
conn.close()
"

# Test OpenRouter API connectivity
curl -H "Authorization: Bearer sk-or-v1-your-key" \
  "https://openrouter.ai/api/v1/generation?limit=1"
```
