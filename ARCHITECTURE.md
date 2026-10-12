# TracexGPT (Open WebUI Fork) — Architecture & Feature Documentation

## 1. Project Overview

TracexGPT is a customized fork of Open WebUI with additional enterprise features:
- **Spending Tracking & Budget Enforcement** — per-user monthly limits with IST billing
- **Client Management** — simplified sub-accounts with fixed models, locked system prompts, and KB restrictions
- **AI Presentation Generation (PPT/PDF)** — integration with Presenton microservice
- **Enhanced Model Catalog** — latest OpenAI models with tiered pricing

**Stack:**
- Frontend: SvelteKit + Vite + TailwindCSS
- Backend: FastAPI + SQLAlchemy + Redis
- External: Presenton (PPT generation microservice)

---

## 2. Backend Architecture

### 2.1 Entry Point — `backend/open_webui/main.py`

The main FastAPI application (`app`). Key responsibilities:
- Imports and registers all API routers (`app.include_router(...)`)
- Exposes `/api/config` — public config endpoint consumed by frontend on load
- Exposes `/api/version` — deployment/version tracking
- Middleware stack: CORS, compression, sessions, audit logging
- Startup/shutdown lifecycle management

**Router Registration Pattern (line ~1431-1461):**
```python
app.include_router(spending.router, prefix='/api/v1/spending', tags=['spending'])
app.include_router(presentations.router, prefix='/api/v1/presentations', tags=['presentations'])
```

**Config Response (`/api/config`, line ~2376):**
Returns features, permissions, integrations, UI settings. Added `integrations.presentations.public_url` for Presenton Studio link.

### 2.2 Routers (`backend/open_webui/routers/`)

Each router is an `APIRouter` instance, imported in `main.py` and mounted with a prefix.

| Router | Prefix | Purpose |
|--------|--------|---------|
| `spending.py` | `/api/v1/spending` | Spending dashboard, model costs, client creation |
| `presentations.py` | `/api/v1/presentations` | PPT/PDF generation via Presenton API |
| `openai.py` | `/api/openai` | Chat completions, client-user restrictions enforced here |
| `users.py` | `/api/v1/users` | User CRUD, roles |
| `auths.py` | `/api/v1/auths` | Login, signup, token validation |
| `chats.py` | `/api/v1/chats` | Chat history, messages |
| `knowledge.py` | `/api/v1/knowledge` | Knowledge bases, collections |
| `models.py` | `/api/v1/models` | Model registry, capabilities |
| `tools.py` | `/api/v1/tools` | Custom tool management |
| `files.py` | `/api/v1/files` | File upload, storage, TTL |

**Spending Router (`spending.py`):**
- `GET /` — admin view of all users' spending by month
- `GET /me` — current user's spending
- `PUT /{user_id}` — admin sets monthly limit
- `GET /models` — model pricing catalog
- `POST /clients` — admin creates a client user

**Presentations Router (`presentations.py`):**
- `POST /generate` — calls Presenton API, streams file back as `StreamingResponse`

**OpenAI Router (`openai.py`) — Critical for Client Users:**
Line ~1106-1132: After `check_budget_before_request`, enforces client restrictions:
- Locks `payload['model']` to `fixed_model_id`
- Injects/overwrites system message with `fixed_system_prompt`
- Filters `metadata['knowledge']` to only assigned KBs

### 2.3 Models (`backend/open_webui/models/`)

SQLAlchemy models for database tables. Key ones:
- `users.py` — `Users` table with `info` JSON column (stores client config, spending)
- `chats.py` — `Chats` table for conversation history
- `files.py` — `Files` table with TTL metadata
- `knowledges.py` — Knowledge base definitions

**The `info` JSON Column Pattern:**
Used extensively to avoid schema migrations. Structure:
```python
user.info = {
    'user_type': 'client',
    'fixed_model_id': 'gpt-4o-mini',
    'fixed_system_prompt': '...',
    'assigned_kb_ids': ['kb-1'],
    'kb_rag_query': 'company policies',
    'monthly_limit_usd': 20.0,
    'spending': {'2025-06': {'spent': 1.23, 'limit': 5.0}},
}
```

### 2.4 Tools System (`backend/open_webui/tools/`)

**`builtin.py`** — Functions that become LLM-native tools when `function_calling='native'`:
- `generate_ppt(...)` — calls Presenton, saves file, attaches to chat
- `get_current_timestamp()`, `calculate_timestamp()` — time utilities
- `search_web()`, `fetch_url()` — web search
- `generate_image()`, `edit_image()` — image generation
- `execute_code()` — code interpreter
- `kb_exec()`, `query_knowledge_files()` — knowledge base access
- `search_chats()`, `view_chat()` — chat history
- `add_memory()`, `search_memories()` — memory system
- Many more...

**How Tools Become Available to LLM:**
1. `utils/tools.py::get_builtin_tools()` imports functions from `builtin.py`
2. Filters by `is_builtin_tool_enabled(category)` and user permissions
3. Converts function signature to OpenAI function spec via Pydantic
4. Injected into `form_data['tools']` in `middleware.py`

**Presentation Tool Registration (`utils/tools.py` line ~623):**
```python
if is_builtin_tool_enabled('presentations'):
    builtin_functions.append(generate_ppt)
```

### 2.5 Middleware (`backend/open_webui/utils/middleware.py`)

The core chat processing pipeline (~5273 lines). Key flow:

1. `process_chat_payload()` — prepares messages, applies system prompts, processes files
2. Pipeline inlet filters — custom function hooks
3. Tool resolution — MCP servers, builtin tools
4. Budget check — `check_budget_before_request()`
5. Client restrictions — enforced in `openai.py` router (post-middleware)
6. Streaming response handling

### 2.6 Cost Tracker (`backend/open_webui/utils/cost_tracker.py`)

- `calculate_cost()` — token-based pricing per 1M tokens
- `calculate_image_cost()`, `calculate_tts_cost()`, `calculate_stt_cost()` — non-token pricing
- `record_spend()` — updates `user.info['spending'][month]` after each request
- `check_budget_before_request()` — raises HTTP 402 if over limit
- `get_all_user_spending()` — admin dashboard data

---

## 3. Frontend Architecture

### 3.1 Routes (`src/routes/(app)/`)

SvelteKit file-based routing. `(app)` = authenticated app shell.

| Route | Files | Purpose |
|-------|-------|---------|
| `+layout.svelte` | Root app layout — sidebar, WebSocket, theme | |
| `+page.svelte` | Home/chat redirect | |
| `admin/+layout.svelte` | Admin nav tabs (Users, Analytics, Spending, Clients, Settings) | |
| `admin/spending/+page.svelte` | Spending dashboard | |
| `admin/clients/+page.svelte` | Client management | |
| `account/spending/+page.svelte` | My spending page | |
| `workspace/+layout.svelte` | Workspace nav (Models, Knowledge, Prompts, Skills, Tools, PPT Generator) | |
| `workspace/ppt-generator/+page.svelte` | AI Presentation Generator form | |

### 3.2 Components (`src/lib/components/`)

| Directory | Contents |
|-----------|----------|
| `admin/` | `Spending.svelte`, `Clients.svelte`, settings sub-components |
| `account/` | `Spending.svelte` (user spending view) |
| `chat/` | `MessageInput.svelte`, `Chat.svelte`, message components |
| `workspace/Tools/` | `PPTGenerator.svelte` |
| `icons/` | `Presentation.svelte` (new icon) |
| `common/` | Reusable UI (Tooltip, Dropdown, Modal, etc.) |

### 3.3 Stores (`src/lib/stores/index.ts`)

Global Svelte writable stores:
- `user` — current session user
- `config` — backend config from `/api/config`
- `models` — available LLM models
- `knowledge` — knowledge bases
- `showSidebar`, `mobile`, `theme` — UI state

### 3.4 API Layer (`src/lib/apis/`)

- `index.ts` — `getBackendConfig()`, `getModels()`, etc.
- `auths.ts` — login, session
- `chats.ts` — chat history
- Frontend fetches directly using `localStorage.token` as Bearer auth

---

## 4. Feature Deep Dives

### 4.1 Spending & Budget System

**Backend:**
- Data stored in `user.info['spending'][YYYY-MM] = {spent, limit}`
- `cost_tracker.py` calculates cost per request (tokens, images, audio)
- `check_budget_before_request()` blocks at 100%, warns at 80%
- Admins bypass all limits

**Frontend:**
- `admin/Spending.svelte` — table of all users, month picker, limit editor
- `account/Spending.svelte` — user's own spending card
- Model pricing catalog from `/api/v1/spending/models`

**API Endpoints:**
```
GET  /api/v1/spending/?month=2025-06
GET  /api/v1/spending/me
PUT  /api/v1/spending/{user_id}
GET  /api/v1/spending/models
```

### 4.2 Client Management

**Backend (`spending.py` line ~187-260):**
- `POST /api/v1/spending/clients` creates a user with `role='user'`
- Stores client config in `user.info`:
  - `user_type: 'client'`
  - `fixed_model_id` — locked model
  - `fixed_system_prompt` — injected into every chat
  - `assigned_kb_ids` — allowed knowledge bases
  - `kb_rag_query` — query for KB context retrieval
  - `monthly_limit_usd` — spending cap
- Returns temp password for admin to share

**Frontend (`admin/Clients.svelte`):**
- Create form with: email, name, model dropdown (latest OpenAI), system prompt, KB RAG query, KB checkbox list, monthly limit
- Displays temp password on creation
- Info box explaining client restrictions

**Enforcement (`openai.py` line ~1106-1132):**
```python
client_info = (user.info or {}) if user else {}
if client_info.get('user_type') == 'client':
    payload['model'] = fixed_model
    messages[0]['content'] = fixed_prompt
    metadata['knowledge'] = filter_to_assigned_kbs(...)
```

### 4.3 AI Presentation Generation

**Two Entry Points:**

**A. Chat Tool (Native Function Calling)**
- User says "make a presentation about AI"
- LLM sees `generate_ppt` in available tools
- Calls tool with topic, slide_count, tone, etc.
- `builtin.py::generate_ppt()`:
  1. Optional KB enrichment via `knowledge_query`
  2. Upload source files to Presenton
  3. Call Presenton API (`POST /api/v1/ppt/presentation/generate`)
  4. Download generated file
  5. Save to Open WebUI file system with TTL metadata
  6. Attach file to chat message
  7. Emit `chat:message:files` event for UI
  8. Return download URL + edit URL

**B. Workspace Form (Direct UI)**
- User navigates to `/workspace/ppt-generator`
- Fills form: topic, slides, tone, format, TOC, web search
- Calls `POST /api/v1/presentations/generate`
- `presentations.py`:
  1. Calls Presenton API
  2. Downloads file bytes
  3. Returns `StreamingResponse` with `Content-Disposition: attachment`
- Frontend auto-triggers browser download from blob
- Shows "Edit Presentation" link if `X-Edit-Path` header present

**Environment Variables:**
```bash
PRESENTON_URL=http://localhost:5000      # Internal API URL
PRESENTON_USER=admin
PRESENTON_PASS=changeme
PRESENTON_PUBLIC_URL=http://localhost:5000  # External URL for edit links
FILE_TTL_DAYS=120
```

**Presenton Studio Link:**
- Backend exposes `PRESENTON_PUBLIC_URL` via `/api/config` → `integrations.presentations.public_url`
- Frontend workspace nav conditionally shows "Presenton Studio" link opening in new tab

---

## 5. Data Flow Diagrams

### 5.1 Chat Request Flow

```
User types message → Frontend POST /api/chat/completions
  → middleware.py::process_chat_payload()
    → Apply system prompts, process files, load chat history
    → Pipeline inlet filters
    → Resolve tools (MCP, builtin)
    → openai.py router
      → check_budget_before_request() → may block with 402
      → IF client user: enforce fixed model, fixed prompt, filter KBs
      → Call LLM API (OpenAI, etc.)
      → Stream response back
    → record_spend() → update user.info['spending']
```

### 5.2 PPT Generation Flow (Chat Tool)

```
User: "make a presentation about X"
  → LLM calls generate_ppt(topic="X", ...)
  → builtin.py::generate_ppt()
    → Optional: query KB with knowledge_query
    → POST Presenton /api/v1/ppt/presentation/generate
    → GET Presenton /download/{id}
    → Save to Open WebUI Files DB
    → Attach to chat message
    → Emit chat:message:files event
  → UI shows file card with download link
```

### 5.3 Client Creation Flow

```
Admin fills form in admin/clients
  → POST /api/v1/spending/clients
    → spending.py::create_client_user()
      → Create auth record (bcrypt password)
      → Store client config in user.info
      → Set monthly limit
      → Return temp password
  → Frontend displays password for admin to share
```

---

## 6. File Relationships

### 6.1 Spending Feature
```
backend/open_webui/utils/cost_tracker.py        ← core logic
backend/open_webui/routers/spending.py          ← API endpoints
backend/open_webui/routers/openai.py          ← budget enforcement (line ~1103)
src/lib/components/admin/Spending.svelte        ← admin dashboard
src/lib/components/account/Spending.svelte      ← user view
src/routes/(app)/admin/+layout.svelte           ← nav tab
```

### 6.2 Client Management Feature
```
backend/open_webui/routers/spending.py          ← POST /clients
backend/open_webui/routers/openai.py            ← enforcement (line ~1106)
src/lib/components/admin/Clients.svelte         ← create form
src/routes/(app)/admin/+layout.svelte           ← nav tab
```

### 6.3 PPT Generation Feature
```
backend/open_webui/tools/builtin.py             ← generate_ppt() tool
backend/open_webui/utils/tools.py               ← tool registration
backend/open_webui/routers/presentations.py     ← direct API
backend/open_webui/main.py                      ← router registration
src/lib/components/workspace/Tools/PPTGenerator.svelte  ← workspace form
src/lib/components/chat/MessageInput.svelte   ← chat button (line ~1727)
src/lib/components/icons/Presentation.svelte    ← icon
src/routes/(app)/workspace/+layout.svelte       ← nav links
```

---

## 7. Key Integration Points

### 7.1 Adding a New Router
1. Create `backend/open_webui/routers/{name}.py`
2. Import in `backend/open_webui/main.py` (line ~480)
3. Register with `app.include_router(...)` (line ~1450)
4. Create frontend route at `src/routes/(app)/{path}/+page.svelte`
5. Add nav link in appropriate `+layout.svelte`

### 7.2 Adding a New Builtin Tool
1. Define async function in `backend/open_webui/tools/builtin.py`
2. Add pydantic-style docstring with `:param` annotations
3. Import in `backend/open_webui/utils/tools.py`
4. Append to `builtin_functions` in `get_builtin_tools()`
5. Optionally add capability check in model metadata

### 7.3 Adding Frontend Nav Links
- Admin nav: `src/routes/(app)/admin/+layout.svelte`
- Workspace nav: `src/routes/(app)/workspace/+layout.svelte`
- Sidebar: `src/lib/components/layout/Sidebar.svelte` (or similar)

### 7.4 Exposing Backend Config to Frontend
1. Add value to `/api/config` response in `main.py` (line ~2408)
2. Frontend reads via `$config` store (populated on app init in `+layout.svelte`)

---

## 8. Development Notes

### 8.1 Running Locally
```bash
# Terminal 1: Backend
cd backend && conda activate tracexgpt
export ENV=dev
export OPENAI_API_KEY="sk-..."
export PRESENTON_URL="http://localhost:5000"
uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2: Presenton (if running locally)
# docker run -p 5000:80 presenton-image

# Terminal 3: Frontend
cd root && nvm use 20
npx vite dev --host
```

### 8.2 Common Issues
- **Stale `.svelte-kit` cache**: Delete `.svelte-kit/` and restart dev server
- **Backend not seeing changes**: Ensure `--reload` flag on uvicorn
- **API 404s**: Check trailing slashes match router definitions
- **Tools not appearing in chat**: Verify model has `builtin_tools` capability enabled

### 8.3 Testing Checklist
- [ ] Admin spending dashboard loads data
- [ ] Client creation succeeds with KB assignment
- [ ] Client user is locked to fixed model
- [ ] Client user's KB access is restricted
- [ ] Budget blocks requests at 100%
- [ ] PPT generates from chat tool call
- [ ] PPT generates from workspace form
- [ ] Edit link appears when PRESENTON_PUBLIC_URL is set
- [ ] File auto-downloads with correct extension
