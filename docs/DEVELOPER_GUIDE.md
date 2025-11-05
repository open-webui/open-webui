# Open WebUI - Developer Guide

> **Version:** 0.6.34
> **Last Updated:** 2025-11-05
> **Audience:** Contributors, Plugin Developers, Integration Partners

---

## Table of Contents

- [1. Development Setup](#1-development-setup)
- [2. Project Structure](#2-project-structure)
- [3. Development Workflow](#3-development-workflow)
- [4. Building Custom Functions](#4-building-custom-functions)
- [5. Creating Pipelines](#5-creating-pipelines)
- [6. Frontend Development](#6-frontend-development)
- [7. Backend Development](#7-backend-development)
- [8. Testing](#8-testing)
- [9. Contributing](#9-contributing)

---

## 1. Development Setup

### 1.1 Prerequisites

**Required:**
- **Node.js**: >= 18.13.0, <= 22.x
- **npm**: >= 6.0.0
- **Python**: 3.11 or 3.12
- **Git**: Latest version

**Optional:**
- **Docker**: For containerized development
- **PostgreSQL**: For production-like DB testing
- **Redis**: For WebSocket/session testing

### 1.2 Clone Repository

```bash
git clone https://github.com/open-webui/open-webui.git
cd open-webui
```

### 1.3 Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Or use specific requirements
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -m open_webui.internal.db --migrate

# Run backend server
python -m open_webui serve
# Or use uvicorn directly
uvicorn open_webui.main:app --reload --host 0.0.0.0 --port 8080
```

### 1.4 Frontend Setup

```bash
# Install dependencies
npm install

# Fetch Pyodide (Python runtime for browser)
npm run pyodide:fetch

# Run development server
npm run dev

# Frontend will be available at http://localhost:5173
```

### 1.5 Full Stack Development

**Terminal 1 (Backend):**
```bash
source venv/bin/activate
uvicorn open_webui.main:app --reload --host 0.0.0.0 --port 8080
```

**Terminal 2 (Frontend):**
```bash
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8080/api
- API Docs: http://localhost:8080/docs

### 1.6 Docker Development

```bash
# Build development image
docker build -t open-webui-dev .

# Run with hot reload (mount source)
docker run -it --rm \
  -p 3000:8080 \
  -v $(pwd):/app \
  -e ENV=dev \
  open-webui-dev
```

### 1.7 Environment Variables

**Key Variables:**

```bash
# .env

# Database
DATABASE_URL=sqlite:///./data/webui.db
# DATABASE_URL=postgresql://user:pass@localhost/webui

# LLM Backends
OLLAMA_BASE_URLS=http://localhost:11434
OPENAI_API_BASE_URLS=https://api.openai.com/v1
OPENAI_API_KEYS=sk-...

# Authentication
WEBUI_SECRET_KEY=your-secret-key-here
ENABLE_OAUTH_SIGNUP=true
ENABLE_LDAP=false

# RAG
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_DB=chroma
CHROMA_DATA_PATH=./data/chroma

# Features
ENABLE_SIGNUP=true
ENABLE_WEB_SEARCH=true
ENABLE_CODE_EXECUTION=true

# Storage
STORAGE_PROVIDER=local
UPLOAD_DIR=./data/uploads

# Development
ENV=dev
WEBUI_AUTH=false  # Disable auth for testing
```

---

## 2. Project Structure

### 2.1 Directory Overview

```
open-webui/
├── src/                      # Frontend (SvelteKit)
│   ├── lib/
│   │   ├── apis/            # API clients
│   │   ├── components/      # UI components
│   │   ├── stores/          # Svelte stores
│   │   ├── types/           # TypeScript types
│   │   └── utils/           # Utilities
│   └── routes/              # Pages
│       ├── (app)/          # Protected routes
│       ├── auth/           # Auth pages
│       └── +layout.svelte  # Root layout
│
├── backend/                 # Backend (FastAPI)
│   └── open_webui/
│       ├── main.py         # App entry point
│       ├── config.py       # Configuration
│       ├── models/         # Database models
│       ├── routers/        # API endpoints
│       ├── utils/          # Utilities
│       ├── retrieval/      # RAG system
│       ├── socket/         # WebSocket
│       └── storage/        # File storage
│
├── static/                 # Static assets
├── docs/                   # Documentation
├── tests/                  # Tests
├── pyproject.toml          # Python config
├── package.json            # Node config
├── svelte.config.js        # Svelte config
├── vite.config.ts          # Vite config
├── tailwind.config.ts      # Tailwind config
└── tsconfig.json           # TypeScript config
```

### 2.2 Key Files

| File | Purpose |
|------|---------|
| `backend/open_webui/main.py` | FastAPI app initialization |
| `backend/open_webui/config.py` | Configuration management |
| `src/routes/+layout.svelte` | Root layout, auth check |
| `src/lib/stores/index.ts` | Global state management |
| `src/lib/apis/` | TypeScript API clients |

---

## 3. Development Workflow

### 3.1 Creating a New Feature

**1. Create Feature Branch:**
```bash
git checkout -b feature/your-feature-name
```

**2. Develop:**
- Frontend: Add components in `src/lib/components/`
- Backend: Add router in `backend/routers/`
- Database: Add model in `backend/models/`

**3. Test:**
```bash
# Frontend tests
npm run test

# Backend tests
pytest

# E2E tests
npm run cy:open
```

**4. Commit:**
```bash
git add .
git commit -m "feat: Add your feature description"
```

**5. Push and Create PR:**
```bash
git push origin feature/your-feature-name
# Create pull request on GitHub
```

### 3.2 Code Style

**Python (Backend):**
```bash
# Format code
black .

# Lint code
pylint backend/

# Type checking
mypy backend/
```

**TypeScript (Frontend):**
```bash
# Format code
npm run format

# Lint code
npm run lint

# Type checking
npm run check
```

### 3.3 Database Migrations

**Create Migration:**
```bash
cd backend
alembic revision --autogenerate -m "Add new table"
```

**Apply Migrations:**
```bash
alembic upgrade head
```

**Rollback:**
```bash
alembic downgrade -1
```

---

## 4. Building Custom Functions

### 4.1 Function Structure

```python
def my_custom_function(param1: str, param2: int = 10) -> dict:
    """
    Brief description of what this function does.

    This docstring is important! The LLM reads it to understand
    when and how to call your function.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)

    Returns:
        Dictionary with results

    Example:
        result = my_custom_function("test", 5)
    """

    # Your code here
    result = {"status": "success", "data": param1 * param2}

    return result
```

### 4.2 Function Types

**Tool Function (LLM can call):**
```python
def search_wikipedia(query: str, limit: int = 3) -> list:
    """Search Wikipedia for articles matching query."""
    import wikipedia

    results = wikipedia.search(query, results=limit)
    summaries = []

    for title in results:
        try:
            page = wikipedia.page(title)
            summaries.append({
                "title": page.title,
                "summary": page.summary[:500],
                "url": page.url
            })
        except:
            pass

    return summaries
```

**Filter Function (Pre-process input):**
```python
def content_filter(messages: list) -> dict:
    """Filter inappropriate content from messages."""

    for message in messages:
        content = message["content"]

        # Check for inappropriate words
        if any(word in content.lower() for word in BLOCKED_WORDS):
            message["content"] = "[Content filtered]"

    return {"messages": messages}
```

**Action Function (Post-process output):**
```python
def log_response(response: str, user_id: str) -> dict:
    """Log AI responses for analytics."""

    import logging

    logging.info(f"User {user_id} received response: {response[:100]}...")

    # Return response unchanged
    return {"response": response}
```

### 4.3 Using External Libraries

**Allowed by Default:**
- `requests`, `httpx` - HTTP requests
- `json`, `yaml` - Data formats
- `datetime`, `time` - Time utilities
- `re` - Regular expressions
- `math`, `random` - Math utilities

**Request Additional Libraries:**
Ask admin to whitelist in RestrictedPython configuration.

### 4.4 Function Configuration (Valves)

```python
class Valves(BaseModel):
    """Configuration for the function"""
    api_key: str = ""
    base_url: str = "https://api.example.com"
    timeout: int = 30

def my_function(__valves__: Valves, query: str) -> dict:
    """Function with configuration."""

    # Access configuration
    api_key = __valves__.api_key
    base_url = __valves__.base_url

    # Use configuration
    response = requests.get(
        f"{base_url}/search",
        params={"q": query},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=__valves__.timeout
    )

    return response.json()
```

### 4.5 Testing Functions

```python
# Test in Python REPL
from backend.utils.plugin import execute_function

code = """
def add(a: int, b: int) -> int:
    return a + b
"""

result = execute_function(code, "add", {"a": 5, "b": 3})
print(result)  # 8
```

---

## 5. Creating Pipelines

### 5.1 Pipeline Server Setup

**Create Pipeline Service:**
```python
# pipeline_service.py

from fastapi import FastAPI, Request
import asyncio

app = FastAPI()

@app.post("/filter")
async def filter_inlet(request: Request):
    """Pre-process requests before sending to LLM."""

    data = await request.json()
    messages = data.get("messages", [])

    # Example: Add system message
    system_msg = {
        "role": "system",
        "content": "You are a helpful assistant. Be concise."
    }
    messages.insert(0, system_msg)

    return {"messages": messages}

@app.post("/outlet")
async def filter_outlet(request: Request):
    """Post-process LLM responses."""

    data = await request.json()
    response = data.get("response", "")

    # Example: Translate response
    translated = translate_to_spanish(response)

    return {"response": translated}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9099)
```

**Run Pipeline:**
```bash
python pipeline_service.py
```

**Configure in Open WebUI:**
```bash
# .env
PIPELINES_URL=http://localhost:9099
```

### 5.2 Pipeline Examples

**Rate Limiting:**
```python
from collections import defaultdict
from time import time

request_counts = defaultdict(list)
RATE_LIMIT = 10  # requests per minute

@app.post("/filter")
async def rate_limit_filter(request: Request):
    data = await request.json()
    user_id = data.get("user_id")

    # Clean old requests
    now = time()
    request_counts[user_id] = [
        t for t in request_counts[user_id]
        if now - t < 60
    ]

    # Check rate limit
    if len(request_counts[user_id]) >= RATE_LIMIT:
        raise HTTPException(429, "Rate limit exceeded")

    # Record request
    request_counts[user_id].append(now)

    return data
```

**Content Moderation:**
```python
@app.post("/filter")
async def content_moderation(request: Request):
    data = await request.json()
    messages = data.get("messages", [])

    for msg in messages:
        if is_toxic(msg["content"]):
            msg["content"] = "[Content moderated]"

    return {"messages": messages}

def is_toxic(text: str) -> bool:
    # Use moderation API
    # ...
    return False
```

---

## 6. Frontend Development

### 6.1 Creating Components

**Svelte Component:**
```svelte
<!-- src/lib/components/MyComponent.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';

  export let title: string;
  export let data: any[] = [];

  let loading = false;

  onMount(async () => {
    loading = true;
    // Fetch data
    const response = await fetch('/api/data');
    data = await response.json();
    loading = false;
  });

  function handleClick() {
    console.log('Clicked!');
  }
</script>

<div class="my-component">
  <h2>{title}</h2>

  {#if loading}
    <p>Loading...</p>
  {:else}
    <ul>
      {#each data as item}
        <li on:click={handleClick}>{item.name}</li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .my-component {
    padding: 1rem;
    border-radius: 0.5rem;
    background: white;
  }
</style>
```

### 6.2 Using Stores

```typescript
// src/lib/stores/myStore.ts
import { writable } from 'svelte/store';

export const myData = writable<string[]>([]);

export const addItem = (item: string) => {
  myData.update(data => [...data, item]);
};
```

**In Component:**
```svelte
<script lang="ts">
  import { myData, addItem } from '$lib/stores/myStore';

  function handleAdd() {
    addItem('New item');
  }
</script>

<div>
  <p>Items: {$myData.length}</p>
  <button on:click={handleAdd}>Add Item</button>

  {#each $myData as item}
    <div>{item}</div>
  {/each}
</div>
```

### 6.3 API Calls

```typescript
// src/lib/apis/myApi.ts
const WEBUI_API_BASE_URL = '/api';

export const getItems = async (token: string) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/items`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });

  if (!res.ok) throw new Error('Failed to fetch items');
  return res.json();
};

export const createItem = async (token: string, data: any) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/items`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(data)
  });

  if (!res.ok) throw new Error('Failed to create item');
  return res.json();
};
```

### 6.4 Routing

**Create New Page:**
```svelte
<!-- src/routes/(app)/mypage/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import type { PageData } from './$types';

  export let data: PageData;

  onMount(() => {
    console.log('Page mounted');
  });
</script>

<svelte:head>
  <title>My Page - Open WebUI</title>
</svelte:head>

<div class="container">
  <h1>My Page</h1>
  <p>Welcome to my custom page!</p>
</div>
```

---

## 7. Backend Development

### 7.1 Creating Routers

```python
# backend/routers/myrouter.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from open_webui.utils.auth import get_current_user
from open_webui.models.users import Users

router = APIRouter()

class ItemCreate(BaseModel):
    name: str
    description: str

class ItemResponse(BaseModel):
    id: str
    name: str
    description: str
    user_id: str

@router.get("/items", response_model=List[ItemResponse])
async def get_items(user: Users = Depends(get_current_user)):
    """Get all items for current user."""

    items = Items.get_items_by_user_id(user.id)
    return items

@router.post("/items", response_model=ItemResponse)
async def create_item(
    form: ItemCreate,
    user: Users = Depends(get_current_user)
):
    """Create new item."""

    item = Items.insert_new_item(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=form.name,
        description=form.description
    )

    return item

@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    user: Users = Depends(get_current_user)
):
    """Delete item."""

    item = Items.get_item_by_id(item_id)

    if not item:
        raise HTTPException(404, "Item not found")

    if item.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "Not authorized")

    Items.delete_item_by_id(item_id)

    return {"success": True}
```

**Register Router:**
```python
# backend/main.py

from backend.routers import myrouter

app.include_router(myrouter.router, prefix="/api", tags=["items"])
```

### 7.2 Database Models

```python
# backend/models/items.py

from sqlalchemy import Column, String, Text, Integer, Boolean
from open_webui.internal.db import Base, get_db

class Item(Base):
    __tablename__ = "item"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    name = Column(String)
    description = Column(Text)
    created_at = Column(Integer)
    updated_at = Column(Integer)
    is_active = Column(Boolean, default=True)

class ItemsTable:
    def get_items_by_user_id(self, user_id: str):
        with get_db() as db:
            return db.query(Item).filter(Item.user_id == user_id).all()

    def insert_new_item(self, **kwargs):
        with get_db() as db:
            item = Item(**kwargs)
            db.add(item)
            db.commit()
            db.refresh(item)
            return item

    def delete_item_by_id(self, item_id: str):
        with get_db() as db:
            db.query(Item).filter(Item.id == item_id).delete()
            db.commit()

Items = ItemsTable()
```

### 7.3 Async Operations

```python
import asyncio
import aiohttp

@router.get("/external-data")
async def fetch_external_data():
    """Fetch data from external API asynchronously."""

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_api(session, "https://api1.example.com"),
            fetch_api(session, "https://api2.example.com"),
            fetch_api(session, "https://api3.example.com")
        ]

        results = await asyncio.gather(*tasks)

    return {"data": results}

async def fetch_api(session, url):
    async with session.get(url) as resp:
        return await resp.json()
```

---

## 8. Testing

### 8.1 Frontend Tests (Vitest)

```typescript
// tests/unit/MyComponent.test.ts
import { render, fireEvent } from '@testing-library/svelte';
import MyComponent from '$lib/components/MyComponent.svelte';

describe('MyComponent', () => {
  it('renders with title', () => {
    const { getByText } = render(MyComponent, {
      props: { title: 'Test Title' }
    });

    expect(getByText('Test Title')).toBeInTheDocument();
  });

  it('handles click events', async () => {
    const { getByRole } = render(MyComponent, {
      props: { title: 'Test' }
    });

    const button = getByRole('button');
    await fireEvent.click(button);

    // Assert button click behavior
  });
});
```

**Run Tests:**
```bash
npm run test
```

### 8.2 Backend Tests (pytest)

```python
# tests/test_routers.py

import pytest
from fastapi.testclient import TestClient
from open_webui.main import app

client = TestClient(app)

def test_get_items():
    # Create auth token
    token = create_test_token()

    response = client.get(
        "/api/items",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_item():
    token = create_test_token()

    response = client.post(
        "/api/items",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Item", "description": "Test"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"
```

**Run Tests:**
```bash
pytest
pytest -v  # Verbose
pytest tests/test_routers.py  # Specific file
```

### 8.3 E2E Tests (Cypress)

```typescript
// cypress/e2e/chat.cy.ts

describe('Chat Functionality', () => {
  beforeEach(() => {
    cy.visit('/');
    cy.login('test@example.com', 'password');
  });

  it('creates new chat', () => {
    cy.get('[data-testid="new-chat-button"]').click();
    cy.url().should('include', '/c/');
  });

  it('sends message and receives response', () => {
    cy.get('[data-testid="new-chat-button"]').click();

    cy.get('[data-testid="chat-input"]')
      .type('Hello, AI!{enter}');

    cy.contains('Hello, AI!', { timeout: 2000 });

    // Wait for AI response
    cy.get('[data-testid="assistant-message"]', { timeout: 10000 })
      .should('exist');
  });
});
```

**Run E2E Tests:**
```bash
npm run cy:open  # Interactive
npx cypress run  # Headless
```

---

## 9. Contributing

### 9.1 Contribution Guidelines

1. **Fork the repository**
2. **Create a feature branch** from `dev`
3. **Make your changes** with clear commits
4. **Write tests** for new features
5. **Update documentation**
6. **Submit pull request** to `dev` branch

### 9.2 Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, missing semi-colons, etc.
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(chat): Add voice input support

Implemented speech-to-text functionality using Whisper.
Users can now click microphone icon to input via voice.

Closes #123
```

```
fix(auth): Fix JWT token expiration issue

Tokens were expiring too quickly due to incorrect time calculation.
Changed from seconds to milliseconds.

Fixes #456
```

### 9.3 Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added for new features
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] Screenshots added (if UI changes)

### 9.4 Code Review Process

1. **Submit PR** with clear description
2. **Automated checks** must pass (linting, tests)
3. **Maintainer review** (may request changes)
4. **Address feedback** and update PR
5. **Approval & merge** by maintainer

### 9.5 Getting Help

**Questions?**
- Discord: https://discord.gg/5rJgQTnV4s
- GitHub Discussions: https://github.com/open-webui/open-webui/discussions
- Documentation: https://docs.openwebui.com

**Report Bugs:**
- GitHub Issues: https://github.com/open-webui/open-webui/issues

**Request Features:**
- GitHub Discussions: Feature Requests category

---

## Appendix

### A. Useful Commands

```bash
# Backend
python -m open_webui serve              # Run server
alembic upgrade head                     # Apply migrations
alembic revision --autogenerate -m "Msg" # Create migration
pytest                                   # Run tests
black .                                  # Format code
pylint backend/                          # Lint code

# Frontend
npm run dev                             # Dev server
npm run build                           # Production build
npm run preview                         # Preview build
npm run test                            # Run tests
npm run lint                            # Lint code
npm run format                          # Format code
npm run check                           # Type check

# Docker
docker build -t open-webui .            # Build image
docker run -p 3000:8080 open-webui      # Run container
docker-compose up                       # Run with compose
```

### B. Debug Tips

**Enable Debug Logging:**
```python
# backend/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend Debug:**
```typescript
// Add in component
console.log('Debug data:', data);
```

**Database Debug:**
```python
# View SQL queries
engine = create_engine(DATABASE_URL, echo=True)
```

### C. Performance Optimization

**Backend:**
- Use async functions for I/O operations
- Add database indexes on frequently queried columns
- Enable caching (Redis or aiocache)
- Use connection pooling

**Frontend:**
- Lazy load components
- Use virtual scrolling for long lists
- Debounce search inputs
- Code splitting with Vite

---

**Document Version:** 1.0
**Last Updated:** 2025-11-05
**Maintained by:** Open WebUI Team

**Happy Coding! 🚀**
