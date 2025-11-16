# CLAUDE.md - Open WebUI Codebase Guide for AI Assistants

**Version**: 0.6.36  
**Last Updated**: 2025-11-16

This document provides comprehensive information about the Open WebUI codebase architecture, conventions, and patterns to help AI assistants understand and work with the code effectively.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Backend Architecture](#2-backend-architecture)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Development Workflows](#4-development-workflows)
5. [Key Conventions](#5-key-conventions)
6. [Configuration Management](#6-configuration-management)
7. [Integration Points](#7-integration-points)
8. [Testing](#8-testing)
9. [Deployment](#9-deployment)

---

## 1. Project Overview

Open WebUI is a **self-hosted AI platform** that operates entirely offline, supporting various LLM runners like Ollama and OpenAI-compatible APIs with built-in RAG capabilities.

### Tech Stack

**Frontend:**
- SvelteKit 2.5.27 (Svelte 5.0.0)
- TypeScript 5.5.4
- Vite 5.4.14
- TailwindCSS 4.0.0
- Socket.IO Client 4.2.0

**Backend:**
- FastAPI 0.118.0
- Python 3.11-3.12
- SQLAlchemy 2.0.38 + Peewee 3.18.1 (dual ORM)
- Alembic 1.14.0 (migrations)
- Python-SocketIO 5.13.0
- Redis (optional, for distributed sessions)

**Database:**
- SQLite (default)
- PostgreSQL (supported)
- MySQL (supported)

**Key Dependencies:**
- ChromaDB 1.0.20 (vector storage)
- LangChain 0.3.27 (RAG)
- Sentence Transformers 5.1.1 (embeddings)
- Faster Whisper 1.1.1 (STT)

### Directory Structure

```
open-webui/
├── backend/
│   └── open_webui/
│       ├── main.py                 # FastAPI application entry
│       ├── config.py               # Configuration management
│       ├── constants.py            # Error messages, constants
│       ├── routers/                # API route handlers
│       ├── models/                 # Database models (SQLAlchemy + Peewee)
│       ├── utils/                  # Utility functions
│       ├── socket/                 # WebSocket handlers
│       ├── retrieval/              # RAG implementation
│       ├── internal/               # Internal modules
│       │   ├── db.py              # Database connection
│       │   └── migrations/        # Peewee migrations
│       ├── migrations/            # Alembic migrations
│       └── test/                  # Backend tests
├── src/
│   ├── routes/                    # SvelteKit routes
│   │   ├── (app)/                # Authenticated routes
│   │   └── auth/                 # Authentication routes
│   ├── lib/
│   │   ├── apis/                 # API client functions
│   │   ├── components/           # Svelte components
│   │   ├── stores/               # Svelte stores (state)
│   │   ├── utils/                # Frontend utilities
│   │   └── i18n/                 # Internationalization
│   └── app.d.ts                  # TypeScript declarations
├── cypress/                       # E2E tests
├── static/                        # Static assets
├── package.json                   # Frontend dependencies
├── pyproject.toml                # Backend dependencies
├── svelte.config.js              # SvelteKit config
├── vite.config.ts                # Vite config
├── Dockerfile                    # Container image
└── docker-compose.yaml           # Container orchestration
```

---

## 2. Backend Architecture

### 2.1 FastAPI Application Structure

**Main Application**: `/backend/open_webui/main.py`

The application uses a lifespan context manager for startup/shutdown:

```python
# Lines 1-100+
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    yield
    # Shutdown logic

app = FastAPI(lifespan=lifespan)
```

**CORS Configuration** (main.py, ~line 42):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Middleware Stack** (main.py):
1. `CompressMiddleware` - Response compression
2. `CORSMiddleware` - CORS handling
3. `SessionMiddleware` / `StarSessionsMiddleware` - Session management
4. `AuditLoggingMiddleware` - Request auditing
5. Custom middleware for security headers

### 2.2 Router Organization

Routers are imported and mounted in `main.py` (lines 70-96):

```python
from open_webui.routers import (
    audio,
    images,
    ollama,
    openai,
    retrieval,
    pipelines,
    tasks,
    auths,
    channels,
    chats,
    notes,
    folders,
    configs,
    groups,
    files,
    functions,
    memories,
    models,
    knowledge,
    prompts,
    evaluations,
    tools,
    users,
    utils,
    scim,
)
```

**Router Pattern**: `/backend/open_webui/routers/`

Example from `auths.py` (lines 1-66):
```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.models.auths import (
    SigninForm,
    SignupForm,
    UpdatePasswordForm,
)

router = APIRouter()

@router.get("/", response_model=SessionUserInfoResponse)
async def get_session_user(
    request: Request, 
    response: Response, 
    user=Depends(get_current_user)
):
    # Implementation
```

### 2.3 Database Models and ORM

**Dual ORM Approach:**
- **SQLAlchemy** for new models and migrations
- **Peewee** for legacy compatibility

**SQLAlchemy Models**: `/backend/open_webui/models/users.py` (lines 24-50)

```python
from sqlalchemy import Column, String, Text, Date, BigInteger
from open_webui.internal.db import Base, JSONField

class User(Base):
    __tablename__ = "user"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    username = Column(String(50), nullable=True)
    role = Column(String)
    profile_image_url = Column(Text)
    bio = Column(Text, nullable=True)
    gender = Column(Text, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    info = Column(JSONField, nullable=True)
    settings = Column(JSONField, nullable=True)
    api_key = Column(String, nullable=True, unique=True)
    oauth_sub = Column(Text, unique=True)
    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)
```

**Pydantic Models** (same file, lines 58-83):
```python
from pydantic import BaseModel, ConfigDict

class UserModel(BaseModel):
    id: str
    name: str
    email: str
    username: Optional[str] = None
    role: str = "pending"
    profile_image_url: str
    bio: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None
    info: Optional[dict] = None
    settings: Optional[UserSettings] = None
    api_key: Optional[str] = None
    oauth_sub: Optional[str] = None
    last_active_at: int
    updated_at: int
    created_at: int
    
    model_config = ConfigDict(from_attributes=True)
```

**Table Classes** (users.py, lines 153-200):
```python
class UsersTable:
    def insert_new_user(
        self,
        id: str,
        name: str,
        email: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,
    ) -> Optional[UserModel]:
        with get_db() as db:
            user = UserModel(**{...})
            result = User(**user.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return user if result else None
    
    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        with get_db() as db:
            user = db.query(User).filter_by(id=id).first()
            return UserModel.model_validate(user)
```

**Database Connection**: `/backend/open_webui/internal/db.py` (lines 1-165)

```python
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Database URL from environment
SQLALCHEMY_DATABASE_URL = DATABASE_URL

# SQLite configuration
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    def on_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        if DATABASE_ENABLE_SQLITE_WAL:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    
    event.listen(engine, "connect", on_connect)
# PostgreSQL/MySQL configuration
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=DATABASE_POOL_SIZE,
        max_overflow=DATABASE_POOL_MAX_OVERFLOW,
        pool_timeout=DATABASE_POOL_TIMEOUT,
        pool_recycle=DATABASE_POOL_RECYCLE,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Session = scoped_session(SessionLocal)
Base = declarative_base()

@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

get_db = contextmanager(get_session)
```

### 2.4 Authentication and Authorization

**Authentication Utils**: `/backend/open_webui/utils/auth.py` (lines 1-200)

```python
import jwt
import bcrypt
from datetime import datetime, timedelta

# Password hashing (lines 157-172)
def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(
        password.encode("utf-8"), 
        bcrypt.gensalt()
    ).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    ) if hashed_password else None

# JWT tokens (lines 174-191)
def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    payload = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        payload.update({"exp": expire})
    encoded_jwt = jwt.encode(payload, SESSION_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, SESSION_SECRET, algorithms=[ALGORITHM])
        return decoded
    except Exception:
        return None

# API keys (lines 197-200)
def create_api_key():
    key = str(uuid.uuid4()).replace("-", "")
    return f"sk-{key}"
```

**Auth Dependencies** (auth.py):
```python
from fastapi.security import HTTPBearer

bearer_security = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    cred: HTTPAuthorizationCredentials = Depends(bearer_security)
):
    token = cred.credentials
    data = decode_token(token)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN
        )
    user = Users.get_user_by_id(data.get("id"))
    return user
```

**OAuth Support** (routers/auths.py):
- Google OAuth
- Microsoft OAuth (Azure AD)
- GitHub OAuth
- Generic OIDC

**LDAP Authentication** (routers/auths.py, lines 186-200):
```python
@router.post("/ldap", response_model=SessionUserResponse)
async def ldap_auth(request: Request, response: Response, form_data: LdapForm):
    ENABLE_LDAP = request.app.state.config.ENABLE_LDAP
    # LDAP configuration from app state
    # Connection and authentication logic
```

### 2.5 API Structure

**Base URL**: `/api/v1/`

**Key Endpoints:**

- `/api/v1/auths/` - Authentication
- `/api/v1/users/` - User management
- `/api/v1/chats/` - Chat operations
- `/api/v1/models/` - Model management
- `/api/v1/prompts/` - Prompt templates
- `/api/v1/knowledge/` - Knowledge bases (RAG)
- `/api/v1/tools/` - Tool management
- `/api/v1/functions/` - Function calling
- `/api/v1/files/` - File operations
- `/api/v1/audio/` - Audio processing (STT/TTS)
- `/api/v1/images/` - Image generation
- `/ollama/` - Ollama proxy
- `/openai/` - OpenAI-compatible API

**Common Patterns:**

1. **List resources**: `GET /api/v1/{resource}/`
2. **Get single**: `GET /api/v1/{resource}/{id}`
3. **Create**: `POST /api/v1/{resource}/create`
4. **Update**: `POST /api/v1/{resource}/{id}/update`
5. **Delete**: `DELETE /api/v1/{resource}/{id}/delete`

### 2.6 Key Backend Utilities

**Error Messages**: `/backend/open_webui/constants.py` (lines 1-100)

```python
class ERROR_MESSAGES(str, Enum):
    DEFAULT = lambda err="": f'{"Something went wrong" if err == "" else f"[ERROR: {err}]"}'
    INVALID_TOKEN = "Your session has expired or the token is invalid."
    INVALID_CRED = "The email or password provided is incorrect."
    UNAUTHORIZED = "401 Unauthorized"
    ACCESS_PROHIBITED = "You do not have permission to access this resource."
    NOT_FOUND = "We could not find what you're looking for :/"
    MODEL_NOT_FOUND = lambda name="": f"Model '{name}' was not found"
```

**Logging**: `/backend/open_webui/utils/logger.py`

Uses `loguru` for structured logging with environment-based log levels.

**Middleware**: `/backend/open_webui/utils/middleware.py`

Custom middleware for:
- Request timing
- Security headers
- Audit logging

**Access Control**: `/backend/open_webui/utils/access_control.py`

Role-based permissions system with granular controls.

---

## 3. Frontend Architecture

### 3.1 SvelteKit Routing

**File-Based Routing**: `/src/routes/`

```
routes/
├── +layout.svelte              # Root layout
├── +error.svelte              # Error page
├── auth/
│   └── +page.svelte           # Login/signup page
├── (app)/                     # Authenticated routes group
│   ├── +layout.svelte         # App layout with sidebar
│   ├── +page.svelte           # Redirect to /home
│   ├── home/
│   │   └── +page.svelte       # Home/dashboard
│   ├── c/
│   │   └── [id]/
│   │       └── +page.svelte   # Chat page
│   ├── workspace/
│   │   ├── +page.svelte       # Workspace overview
│   │   ├── models/
│   │   ├── prompts/
│   │   ├── knowledge/
│   │   └── tools/
│   ├── admin/
│   │   ├── +page.svelte
│   │   ├── settings/
│   │   │   └── [tab]/
│   │   │       └── +page.svelte
│   │   └── users/
│   └── notes/
└── s/
    └── [id]/
        └── +page.svelte       # Shared chat view
```

**Route Groups**: Parentheses `(app)` create a layout group without affecting the URL.

**Dynamic Routes**: Square brackets `[id]` create dynamic segments.

### 3.2 Component Organization

**Component Structure**: `/src/lib/components/`

```
components/
├── chat/
│   ├── Chat.svelte
│   ├── Messages.svelte
│   ├── MessageInput.svelte
│   ├── Navbar.svelte
│   ├── ModelSelector.svelte
│   ├── SettingsModal.svelte
│   └── ...
├── common/
│   ├── Modal.svelte
│   ├── Button.svelte
│   ├── Dropdown.svelte
│   ├── Tooltip.svelte
│   ├── Spinner.svelte
│   └── ...
├── layout/
│   ├── Sidebar.svelte
│   ├── SearchModal.svelte
│   └── ...
├── workspace/
│   ├── Models.svelte
│   ├── Prompts.svelte
│   ├── Knowledge.svelte
│   └── Tools.svelte
├── admin/
│   ├── Settings.svelte
│   ├── Users.svelte
│   └── ...
└── icons/
    └── ...
```

**Component Pattern Example**: Typical Svelte component structure

```svelte
<script lang="ts">
    import { onMount, getContext } from 'svelte';
    import { goto } from '$app/navigation';
    import { user, settings } from '$lib/stores';
    import { getModels } from '$lib/apis';
    
    const i18n = getContext('i18n');
    
    // Props
    export let title: string = '';
    export let onClose: () => void;
    
    // State
    let loading = false;
    let data = [];
    
    // Lifecycle
    onMount(async () => {
        await loadData();
    });
    
    // Methods
    const loadData = async () => {
        loading = true;
        try {
            data = await getModels(localStorage.token);
        } catch (error) {
            console.error(error);
        } finally {
            loading = false;
        }
    };
</script>

<div class="modal">
    {#if loading}
        <Spinner />
    {:else}
        <div class="content">
            {#each data as item}
                <div>{item.name}</div>
            {/each}
        </div>
    {/if}
</div>

<style>
    .modal {
        /* Styles */
    }
</style>
```

### 3.3 State Management (Svelte Stores)

**Central Store**: `/src/lib/stores/index.ts` (lines 1-296)

```typescript
import { writable } from 'svelte/store';
import type { Writable } from 'svelte/store';

// Backend config and user
export const config: Writable<Config | undefined> = writable(undefined);
export const user: Writable<SessionUser | undefined> = writable(undefined);

// UI state
export const mobile = writable(false);
export const showSidebar = writable(false);
export const showSettings = writable(false);
export const showSearch = writable(false);

// Data stores
export const models: Writable<Model[]> = writable([]);
export const prompts: Writable<Prompt[] | null> = writable(null);
export const knowledge: Writable<Document[] | null> = writable(null);
export const tools = writable(null);
export const functions = writable(null);
export const chats = writable(null);
export const tags = writable([]);
export const folders = writable([]);

// Settings
export const settings: Writable<Settings> = writable({});

// Socket.IO
export const socket: Writable<null | Socket> = writable(null);

// Types
export type SessionUser = {
    id: string;
    email: string;
    name: string;
    role: string;
    profile_image_url: string;
    permissions: any;
};
```

**Store Usage Pattern**:

```typescript
import { user, settings } from '$lib/stores';

// Subscribe
$: if ($user) {
    console.log($user.name);
}

// Update
user.set(newUser);
settings.update(s => ({ ...s, theme: 'dark' }));
```

### 3.4 API Integration Patterns

**API Client**: `/src/lib/apis/index.ts` (lines 1-200+)

```typescript
import { WEBUI_BASE_URL } from '$lib/constants';

export const getModels = async (
    token: string = '',
    connections: object | null = null,
    base: boolean = false,
    refresh: boolean = false
) => {
    const searchParams = new URLSearchParams();
    if (refresh) {
        searchParams.append('refresh', 'true');
    }
    
    let error = null;
    const res = await fetch(
        `${WEBUI_BASE_URL}/api/models${base ? '/base' : ''}?${searchParams.toString()}`,
        {
            method: 'GET',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                ...(token && { authorization: `Bearer ${token}` })
            }
        }
    )
    .then(async (res) => {
        if (!res.ok) throw await res.json();
        return res.json();
    })
    .catch((err) => {
        error = err;
        console.error(err);
        return null;
    });
    
    if (error) {
        throw error;
    }
    
    return res?.data ?? [];
};
```

**Module-Based APIs**: `/src/lib/apis/`

- `auths/index.ts` - Authentication APIs
- `users/index.ts` - User management
- `chats/index.ts` - Chat operations
- `models/index.ts` - Model management
- `streaming/index.ts` - Server-Sent Events handling

**Example**: `/src/lib/apis/auths/index.ts` (lines 85-111)

```typescript
export const getSessionUser = async (token: string) => {
    let error = null;
    
    const res = await fetch(`${WEBUI_API_BASE_URL}/auths/`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        credentials: 'include'
    })
    .then(async (res) => {
        if (!res.ok) throw await res.json();
        return res.json();
    })
    .catch((err) => {
        console.error(err);
        error = err.detail;
        return null;
    });
    
    if (error) {
        throw error;
    }
    
    return res;
};
```

### 3.5 Streaming Implementation

**SSE Streaming**: `/src/lib/apis/streaming/index.ts` (lines 1-143)

```typescript
import { EventSourceParserStream } from 'eventsource-parser/stream';

type TextStreamUpdate = {
    done: boolean;
    value: string;
    sources?: any;
    selectedModelId?: any;
    error?: any;
    usage?: ResponseUsage;
};

export async function createOpenAITextStream(
    responseBody: ReadableStream<Uint8Array>,
    splitLargeDeltas: boolean
): Promise<AsyncGenerator<TextStreamUpdate>> {
    const eventStream = responseBody
        .pipeThrough(new TextDecoderStream())
        .pipeThrough(new EventSourceParserStream())
        .getReader();
    
    let iterator = openAIStreamToIterator(eventStream);
    if (splitLargeDeltas) {
        iterator = streamLargeDeltasAsRandomChunks(iterator);
    }
    return iterator;
}

async function* openAIStreamToIterator(
    reader: ReadableStreamDefaultReader<ParsedEvent>
): AsyncGenerator<TextStreamUpdate> {
    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            yield { done: true, value: '' };
            break;
        }
        
        const data = value.data;
        if (data.startsWith('[DONE]')) {
            yield { done: true, value: '' };
            break;
        }
        
        try {
            const parsedData = JSON.parse(data);
            
            if (parsedData.error) {
                yield { done: true, value: '', error: parsedData.error };
                break;
            }
            
            yield {
                done: false,
                value: parsedData.choices?.[0]?.delta?.content ?? ''
            };
        } catch (e) {
            console.error('Error extracting delta from SSE event:', e);
        }
    }
}
```

### 3.6 Key Frontend Utilities

**Utils**: `/src/lib/utils/index.ts` (lines 1-200)

```typescript
import { v4 as uuidv4 } from 'uuid';
import sha256 from 'js-sha256';
import dayjs from 'dayjs';

// Helper functions
export const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Token replacement for chat messages
export const replaceTokens = (content, sourceIds, char, user) => {
    const tokens = [
        { regex: /{{char}}/gi, replacement: char },
        { regex: /{{user}}/gi, replacement: user },
        {
            regex: /{{VIDEO_FILE_ID_([a-f0-9-]+)}}/gi,
            replacement: (_, fileId) =>
                `<video src="${WEBUI_BASE_URL}/api/v1/files/${fileId}/content" controls></video>`
        },
    ];
    
    // Apply replacements outside code blocks
    return processOutsideCodeBlocks(content, (segment) => {
        tokens.forEach(({ regex, replacement }) => {
            if (replacement !== undefined && replacement !== null) {
                segment = segment.replace(regex, replacement);
            }
        });
        return segment;
    });
};

// Response sanitization
export const sanitizeResponseContent = (content: string) => {
    return content
        .replace(/<\|[a-z]*$/, '')
        .replace(/<\|[a-z]+\|$/, '')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .trim();
};
```

**Constants**: `/src/lib/constants.ts` (lines 1-104)

```typescript
import { browser, dev } from '$app/environment';

export const APP_NAME = 'Open WebUI';

export const WEBUI_HOSTNAME = browser ? (dev ? `${location.hostname}:8080` : ``) : '';
export const WEBUI_BASE_URL = browser ? (dev ? `http://${WEBUI_HOSTNAME}` : ``) : ``;
export const WEBUI_API_BASE_URL = `${WEBUI_BASE_URL}/api/v1`;

export const OLLAMA_API_BASE_URL = `${WEBUI_BASE_URL}/ollama`;
export const OPENAI_API_BASE_URL = `${WEBUI_BASE_URL}/openai`;

export const SUPPORTED_FILE_EXTENSIONS = [
    'md', 'rst', 'go', 'py', 'java', 'sh', 'js', 'ts',
    'css', 'cpp', 'c', 'html', 'sql', 'doc', 'docx',
    'pdf', 'csv', 'txt', 'xlsx', 'ppt', 'pptx'
];
```

---

## 4. Development Workflows

### 4.1 Build Processes

**NPM Scripts**: `package.json` (lines 5-22)

```json
{
  "scripts": {
    "dev": "npm run pyodide:fetch && vite dev --host",
    "dev:5050": "npm run pyodide:fetch && vite dev --port 5050",
    "build": "npm run pyodide:fetch && vite build",
    "build:watch": "npm run pyodide:fetch && vite build --watch",
    "preview": "vite preview",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
    "check:watch": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json --watch",
    "lint": "npm run lint:frontend ; npm run lint:types ; npm run lint:backend",
    "lint:frontend": "eslint . --fix",
    "lint:types": "npm run check",
    "lint:backend": "pylint backend/",
    "format": "prettier --plugin-search-dir --write \"**/*.{js,ts,svelte,css,md,html,json}\"",
    "format:backend": "black . --exclude \".venv/|/venv/\"",
    "i18n:parse": "i18next --config i18next-parser.config.ts && prettier --write \"src/lib/i18n/**/*.{js,json}\"",
    "cy:open": "cypress open",
    "test:frontend": "vitest --passWithNoTests",
    "pyodide:fetch": "node scripts/prepare-pyodide.js"
  }
}
```

**SvelteKit Config**: `svelte.config.js` (lines 1-57)

```javascript
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const config = {
    preprocess: vitePreprocess(),
    kit: {
        adapter: adapter({
            pages: 'build',
            assets: 'build',
            fallback: 'index.html'  // SPA mode
        }),
        version: {
            name: (() => {
                try {
                    return child_process.execSync('git rev-parse HEAD')
                        .toString().trim();
                } catch {
                    return Date.now().toString();
                }
            })(),
            pollInterval: 60000  // Check for updates every 60s
        }
    }
};

export default config;
```

**Vite Config**: `vite.config.ts` (lines 1-32)

```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
    plugins: [
        sveltekit(),
        viteStaticCopy({
            targets: [
                {
                    src: 'node_modules/onnxruntime-web/dist/*.jsep.*',
                    dest: 'wasm'
                }
            ]
        })
    ],
    define: {
        APP_VERSION: JSON.stringify(process.env.npm_package_version),
        APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
    },
    build: {
        sourcemap: true
    },
    worker: {
        format: 'es'
    },
    esbuild: {
        pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug']
    }
});
```

### 4.2 Testing Setup

**Cypress (E2E)**: `cypress.config.ts`

```typescript
import { defineConfig } from 'cypress';

export default defineConfig({
    e2e: {
        baseUrl: 'http://localhost:8080'
    },
    video: true
});
```

**Vitest (Unit Tests)**:

Frontend unit tests using Vitest (configured in `package.json`):
```json
{
  "scripts": {
    "test:frontend": "vitest --passWithNoTests"
  }
}
```

**Pytest (Backend Tests)**: `/backend/open_webui/test/`

Example test: `test_users.py` (lines 1-150)

```python
from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user

class TestUsers(AbstractPostgresTest):
    BASE_PATH = "/api/v1/users"
    
    def setup_class(cls):
        super().setup_class()
        from open_webui.models.users import Users
        cls.users = Users
    
    def test_users(self):
        # Get all users
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert len(response.json()) == 2
        
        # Update role
        with mock_webui_user(id="3"):
            response = self.fast_api_client.post(
                self.create_url("/update/role"),
                json={"id": "2", "role": "admin"}
            )
        assert response.status_code == 200
```

### 4.3 Linting and Formatting

**ESLint**: `.eslintrc.cjs`

```javascript
module.exports = {
    root: true,
    extends: [
        'eslint:recommended',
        'plugin:@typescript-eslint/recommended',
        'plugin:svelte/recommended',
        'plugin:cypress/recommended',
        'prettier'
    ],
    parser: '@typescript-eslint/parser',
    plugins: ['@typescript-eslint'],
    parserOptions: {
        sourceType: 'module',
        ecmaVersion: 2020,
        extraFileExtensions: ['.svelte']
    },
    overrides: [
        {
            files: ['*.svelte'],
            parser: 'svelte-eslint-parser',
            parserOptions: {
                parser: '@typescript-eslint/parser'
            }
        }
    ]
};
```

**Prettier**: `.prettierrc`

```json
{
    "useTabs": true,
    "singleQuote": true,
    "trailingComma": "none",
    "printWidth": 100,
    "plugins": ["prettier-plugin-svelte"],
    "endOfLine": "lf"
}
```

**Black (Python)**: `pyproject.toml`

```toml
[tool.black]
line-length = 88
target-version = ['py311']
```

### 4.4 Docker Setup

**Dockerfile**: Multi-stage build (lines 1-192)

```dockerfile
# Frontend build stage
FROM node:22-alpine3.20 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --force
COPY . .
RUN npm run build

# Backend stage
FROM python:3.11-slim-bookworm AS base

# Environment variables
ENV ENV=prod \
    PORT=8080 \
    OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git build-essential pandoc gcc netcat-openbsd curl jq \
    python3-dev ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./backend/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir uv && \
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    uv pip install --system -r requirements.txt --no-cache-dir

# Copy built frontend and backend
COPY --from=build /app/build /app/build
COPY ./backend .

EXPOSE 8080
HEALTHCHECK CMD curl --silent --fail http://localhost:8080/health || exit 1

CMD ["bash", "start.sh"]
```

**Docker Compose**: `docker-compose.yaml`

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    ports:
      - "3000:8080"
    volumes:
      - open-webui:/app/backend/data
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    restart: always

volumes:
  open-webui:
```

---

## 5. Key Conventions

### 5.1 Code Organization Patterns

**Backend Patterns:**

1. **Router → Model → Database** flow
2. Each feature has its own router module
3. Pydantic models for validation
4. Table classes for database operations
5. Dependency injection for authentication

**Frontend Patterns:**

1. **Routes → Components → APIs** flow
2. File-based routing in `/src/routes`
3. Reusable components in `/src/lib/components`
4. Centralized state in `/src/lib/stores`
5. API functions in `/src/lib/apis`

### 5.2 Naming Conventions

**Files:**
- Backend: `snake_case.py`
- Frontend: `PascalCase.svelte` for components, `camelCase.ts` for utilities
- Routes: `+page.svelte`, `+layout.svelte`, `+server.ts`

**Variables:**
- Python: `snake_case`
- TypeScript/JavaScript: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Types/Interfaces: `PascalCase`

**Functions:**
- Python: `snake_case_function()`
- TypeScript: `camelCaseFunction()`
- API endpoints: `get_resource_by_id()`, `update_resource()`

**Database:**
- Tables: `snake_case`
- Columns: `snake_case`
- Primary keys: `id` (string UUID or integer)
- Timestamps: `created_at`, `updated_at` (BigInteger, epoch seconds)

### 5.3 Import/Export Patterns

**Backend Imports:**

```python
# Standard library
import os
import json
from typing import Optional, List

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# Local
from open_webui.models.users import Users
from open_webui.utils.auth import get_current_user
from open_webui.constants import ERROR_MESSAGES
```

**Frontend Imports:**

```typescript
// Svelte
import { onMount, getContext } from 'svelte';
import { writable } from 'svelte/store';

// SvelteKit
import { goto } from '$app/navigation';
import { page } from '$app/stores';

// Local
import { user, settings } from '$lib/stores';
import { getModels } from '$lib/apis';
import Modal from '$lib/components/common/Modal.svelte';
```

**Path Aliases:**
- `$lib` → `/src/lib`
- `$app` → SvelteKit app module

### 5.4 Error Handling Patterns

**Backend:**

```python
# Using ERROR_MESSAGES enum
from open_webui.constants import ERROR_MESSAGES

@router.get("/{id}")
async def get_resource(id: str, user=Depends(get_current_user)):
    resource = Resources.get_by_id(id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND
        )
    return resource

# Try-except pattern
try:
    result = await some_operation()
except Exception as e:
    log.error(f"Operation failed: {e}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ERROR_MESSAGES.DEFAULT(str(e))
    )
```

**Frontend:**

```typescript
// API call pattern
const loadData = async () => {
    loading = true;
    try {
        data = await getModels(localStorage.token);
    } catch (error) {
        console.error('Failed to load models:', error);
        toast.error($i18n.t('Failed to load models'));
    } finally {
        loading = false;
    }
};

// Error propagation
import { toast } from 'svelte-sonner';

if (error) {
    throw error;  // Let caller handle
}
```

### 5.5 Type Safety Approaches

**TypeScript Usage:**

```typescript
// Interfaces for API responses
interface Model {
    id: string;
    name: string;
    owned_by: 'ollama' | 'openai';
    details?: ModelDetails;
}

interface SessionUser {
    id: string;
    email: string;
    name: string;
    role: string;
    profile_image_url: string;
    permissions: any;
}

// Type guards
function isOllamaModel(model: Model): model is OllamaModel {
    return model.owned_by === 'ollama';
}

// Generic types
type Writable<T> = import('svelte/store').Writable<T>;

export const models: Writable<Model[]> = writable([]);
```

**Pydantic in Backend:**

```python
from pydantic import BaseModel, ConfigDict, validator
from typing import Optional

class UserUpdateForm(BaseModel):
    name: str
    email: str
    role: str
    password: Optional[str] = None
    
    @validator('email')
    def validate_email(cls, v):
        if not '@' in v:
            raise ValueError('Invalid email format')
        return v
    
    model_config = ConfigDict(from_attributes=True)
```

---

## 6. Configuration Management

### 6.1 Environment Variables

**Backend Environment**: `.env.example`

```bash
# Core URLs
OLLAMA_BASE_URL='http://localhost:11434'
OPENAI_API_BASE_URL=''
OPENAI_API_KEY=''

# CORS
CORS_ALLOW_ORIGIN='*'
FORWARDED_ALLOW_IPS='*'

# Security
WEBUI_SECRET_KEY=''

# Telemetry
SCARF_NO_ANALYTICS=true
DO_NOT_TRACK=true
ANONYMIZED_TELEMETRY=false

# Database
DATABASE_URL='sqlite:///./data/webui.db'

# Redis (optional)
REDIS_URL=''

# RAG
RAG_EMBEDDING_MODEL='sentence-transformers/all-MiniLM-L6-v2'
CHUNK_SIZE=1500
CHUNK_OVERLAP=100

# Whisper
WHISPER_MODEL='base'

# Features
ENABLE_SIGNUP=true
ENABLE_IMAGE_GENERATION=false
ENABLE_COMMUNITY_SHARING=true
```

**Config System**: `/backend/open_webui/config.py`

Uses `PersistentConfig` class for runtime-updatable configuration:

```python
class PersistentConfig(Generic[T]):
    def __init__(self, env_name: str, config_path: str, env_value: T):
        self.env_name = env_name
        self.config_path = config_path
        self.env_value = env_value
        self.config_value = get_config_value(config_path)
        
        if self.config_value is not None and ENABLE_PERSISTENT_CONFIG:
            self.value = self.config_value
        else:
            self.value = env_value
        
        PERSISTENT_CONFIG_REGISTRY.append(self)
    
    def save(self):
        # Save to database
        path_parts = self.config_path.split(".")
        sub_config = CONFIG_DATA
        for key in path_parts[:-1]:
            if key not in sub_config:
                sub_config[key] = {}
            sub_config = sub_config[key]
        sub_config[path_parts[-1]] = self.value
        save_to_db(CONFIG_DATA)

# Usage
JWT_EXPIRES_IN = PersistentConfig(
    "JWT_EXPIRES_IN",
    "auth.jwt_expiry",
    os.environ.get("JWT_EXPIRES_IN", "4w")
)
```

### 6.2 Feature Flags

Configuration stored in database and accessible via API:

```python
# Backend: config table
class Config(Base):
    __tablename__ = "config"
    
    id = Column(Integer, primary_key=True)
    data = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
```

Features controlled via admin panel:
- `ENABLE_SIGNUP`
- `ENABLE_IMAGE_GENERATION`
- `ENABLE_COMMUNITY_SHARING`
- `ENABLE_WEB_SEARCH`
- `ENABLE_OAUTH_SIGNUP`
- `ENABLE_LDAP`

### 6.3 Database Migrations

**Alembic (SQLAlchemy)**: `/backend/open_webui/migrations/`

```python
# Migration file example: migrations/versions/7e5b5dc7342b_init.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        # ... more columns
    )

def downgrade():
    op.drop_table('user')
```

**Running Migrations:**

Migrations run automatically on startup:

```python
# config.py, lines 52-68
def run_migrations():
    log.info("Running migrations")
    try:
        from alembic import command
        from alembic.config import Config
        
        alembic_cfg = Config(OPEN_WEBUI_DIR / "alembic.ini")
        migrations_path = OPEN_WEBUI_DIR / "migrations"
        alembic_cfg.set_main_option("script_location", str(migrations_path))
        
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        log.exception(f"Error running migrations: {e}")

run_migrations()
```

**Peewee Migrations**: `/backend/open_webui/internal/migrations/`

Legacy migration system still supported for backward compatibility.

---

## 7. Integration Points

### 7.1 Frontend-Backend Communication

**REST API:**

Frontend makes API calls via fetch:

```typescript
// src/lib/apis/chats/index.ts
export const getChatById = async (token: string, id: string) => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    });
    
    if (!res.ok) throw await res.json();
    return res.json();
};
```

**Authentication:**

JWT tokens stored in localStorage and sent with every request:

```typescript
// Store token after login
localStorage.token = response.token;

// Include in API calls
headers: {
    Authorization: `Bearer ${localStorage.token}`
}
```

### 7.2 WebSocket/Socket.IO Usage

**Backend Socket Server**: `/backend/open_webui/socket/main.py` (lines 1-200)

```python
import socketio

# Configure Socket.IO server
if WEBSOCKET_MANAGER == "redis":
    mgr = socketio.AsyncRedisManager(WEBSOCKET_REDIS_URL)
    sio = socketio.AsyncServer(
        cors_allowed_origins=SOCKETIO_CORS_ORIGINS,
        async_mode="asgi",
        client_manager=mgr,
    )
else:
    sio = socketio.AsyncServer(
        cors_allowed_origins=SOCKETIO_CORS_ORIGINS,
        async_mode="asgi",
    )

app = socketio.ASGIApp(sio)

# Event handlers
@sio.event
async def connect(sid, environ, auth):
    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])
        if data and "id" in data:
            user = Users.get_user_by_id(data["id"])
    
    if user:
        SESSION_POOL[sid] = user.id
        await sio.emit("user-count", {"count": len(SESSION_POOL)})

@sio.event
async def disconnect(sid):
    if sid in SESSION_POOL:
        del SESSION_POOL[sid]
        await sio.emit("user-count", {"count": len(SESSION_POOL)})
```

**Frontend Socket Client**: Component usage

```typescript
import { io } from 'socket.io-client';
import { socket } from '$lib/stores';

onMount(() => {
    const socketConnection = io(WEBUI_BASE_URL, {
        path: '/ws/socket.io',
        auth: { token: localStorage.token }
    });
    
    socketConnection.on('connect', () => {
        console.log('Connected to socket');
    });
    
    socketConnection.on('usage', (data) => {
        USAGE_POOL.set(data);
    });
    
    socket.set(socketConnection);
    
    return () => {
        socketConnection.disconnect();
    };
});
```

### 7.3 External API Integrations

**Ollama**: `/backend/open_webui/routers/ollama.py`

Proxies requests to Ollama server:

```python
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    target_url = f"{app.state.config.OLLAMA_BASE_URLS[url_idx]}/{path}"
    
    # Forward request to Ollama
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=body
        ) as response:
            # Stream response back to client
            return StreamingResponse(
                response.content.iter_any(),
                status_code=response.status,
                headers=dict(response.headers)
            )
```

**OpenAI-Compatible API**: `/backend/open_webui/routers/openai.py`

Implements OpenAI API spec for compatibility:

```python
@router.post("/chat/completions")
async def chat_completions(
    form_data: dict,
    user=Depends(get_verified_user)
):
    # Transform request to internal format
    # Route to appropriate backend (Ollama, OpenAI, etc.)
    # Stream response
```

### 7.4 RAG and Document Processing

**Document Processing**: `/backend/open_webui/retrieval/loaders/`

Supports multiple document types:
- PDF (pypdf, unstructured)
- DOCX (docx2txt, python-docx)
- PPTX (python-pptx)
- Excel (pandas, openpyxl)
- Markdown, text, code files
- Audio (Whisper transcription)
- Images (OCR with RapidOCR)

**Vector Storage**: `/backend/open_webui/retrieval/vector/dbs/`

Supported vector databases:
- ChromaDB (default)
- OpenSearch
- Qdrant
- Milvus
- Pinecone

**Embedding Generation**: `/backend/open_webui/routers/retrieval.py`

```python
from sentence_transformers import SentenceTransformer

def get_embedding_function():
    if RAG_EMBEDDING_ENGINE == "openai":
        return OpenAIEmbeddingFunction(api_key=RAG_OPENAI_API_KEY)
    elif RAG_EMBEDDING_ENGINE == "ollama":
        return OllamaEmbeddingFunction(
            url=RAG_OLLAMA_BASE_URL,
            model=RAG_EMBEDDING_MODEL
        )
    else:
        # Local sentence transformers
        return SentenceTransformerEmbeddingFunction(
            model_name=RAG_EMBEDDING_MODEL,
            device='cpu'
        )
```

**Retrieval Flow:**

1. User uploads document → `/api/v1/files/`
2. Document processed → chunks extracted
3. Chunks embedded → stored in vector DB
4. Query → embedded → similarity search
5. Top-K chunks retrieved → added to context
6. LLM generates response with context

---

## 8. Testing

### 8.1 Backend Testing

**Test Structure**: `/backend/open_webui/test/`

```
test/
├── apps/
│   └── webui/
│       ├── routers/
│       │   ├── test_users.py
│       │   ├── test_chats.py
│       │   ├── test_models.py
│       │   └── test_auths.py
│       └── storage/
│           └── test_provider.py
└── util/
    ├── mock_user.py
    ├── abstract_integration_test.py
    └── test_redis.py
```

**Test Base Class**: `abstract_integration_test.py`

```python
class AbstractPostgresTest:
    @classmethod
    def setup_class(cls):
        # Set up test database
        cls.engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.fast_api_client = TestClient(app)
    
    def setup_method(self):
        # Clear data before each test
        with get_db() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()
    
    def create_url(self, path: str) -> str:
        return f"{self.BASE_PATH}{path}"
```

**Mock User Pattern**: `mock_user.py`

```python
from contextlib import contextmanager

@contextmanager
def mock_webui_user(id: str, role: str = "admin"):
    """Mock authenticated user for testing"""
    original_dep = app.dependency_overrides.get(get_current_user)
    
    def override_get_current_user():
        return UserModel(
            id=id,
            role=role,
            name=f"Test User {id}",
            email=f"user{id}@test.com"
        )
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        yield
    finally:
        if original_dep:
            app.dependency_overrides[get_current_user] = original_dep
        else:
            del app.dependency_overrides[get_current_user]
```

**Running Tests:**

```bash
# All backend tests
pytest backend/

# Specific test file
pytest backend/open_webui/test/apps/webui/routers/test_users.py

# With coverage
pytest --cov=backend/open_webui backend/
```

### 8.2 Frontend Testing

**Cypress E2E**: `/cypress/e2e/`

Configuration: `cypress.config.ts`

```typescript
export default defineConfig({
    e2e: {
        baseUrl: 'http://localhost:8080'
    },
    video: true
});
```

**Vitest Unit Tests**:

```bash
npm run test:frontend
```

---

## 9. Deployment

### 9.1 Production Build

**Frontend:**

```bash
npm run build
# Outputs to /build directory
```

**Backend:**

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run with uvicorn
cd backend
uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

### 9.2 Docker Deployment

**Build Image:**

```bash
docker build -t open-webui:latest .

# With CUDA support
docker build --build-arg USE_CUDA=true --build-arg USE_CUDA_VER=cu128 -t open-webui:cuda .

# With bundled Ollama
docker build --build-arg USE_OLLAMA=true -t open-webui:ollama .
```

**Run Container:**

```bash
docker run -d \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --name open-webui \
  --restart always \
  open-webui:latest
```

**Docker Compose:**

```bash
docker-compose up -d
```

### 9.3 Environment-Specific Configs

**Development:**
- Frontend dev server: `http://localhost:5173`
- Backend dev server: `http://localhost:8080`
- Hot reload enabled

**Production:**
- Static build served by FastAPI
- Single port (8080)
- Optimized builds
- Console logging stripped

---

## Appendix: Quick Reference

### Common File Paths

**Backend:**
- Main app: `/backend/open_webui/main.py`
- Config: `/backend/open_webui/config.py`
- Database: `/backend/open_webui/internal/db.py`
- Models: `/backend/open_webui/models/`
- Routers: `/backend/open_webui/routers/`
- Utils: `/backend/open_webui/utils/`

**Frontend:**
- Routes: `/src/routes/`
- Components: `/src/lib/components/`
- Stores: `/src/lib/stores/index.ts`
- APIs: `/src/lib/apis/`
- Utils: `/src/lib/utils/`
- Constants: `/src/lib/constants.ts`
- i18n: `/src/lib/i18n/`

### Key Dependencies

**Backend:**
- `fastapi==0.118.0` - Web framework
- `sqlalchemy==2.0.38` - ORM
- `alembic==1.14.0` - Migrations
- `python-socketio==5.13.0` - WebSockets
- `chromadb==1.0.20` - Vector DB
- `langchain==0.3.27` - RAG framework
- `sentence-transformers==5.1.1` - Embeddings

**Frontend:**
- `svelte@5.0.0` - UI framework
- `@sveltejs/kit@2.5.27` - Meta-framework
- `vite@5.4.14` - Build tool
- `typescript@5.5.4` - Type safety
- `socket.io-client@4.2.0` - WebSockets
- `marked@9.1.0` - Markdown rendering

### Development Commands

```bash
# Frontend
npm run dev           # Start dev server
npm run build         # Production build
npm run lint          # Lint all code
npm run format        # Format all code

# Backend
cd backend
python -m uvicorn open_webui.main:app --reload  # Dev server
pytest                                           # Run tests
black .                                         # Format code
pylint open_webui/                              # Lint code

# Docker
docker-compose up -d                  # Start services
docker-compose logs -f open-webui    # View logs
docker-compose down                   # Stop services
```

---

**End of CLAUDE.md**

This document should be updated as the codebase evolves. For the latest information, refer to the source code and official documentation at https://docs.openwebui.com/
