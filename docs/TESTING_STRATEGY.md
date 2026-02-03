# Testing Strategy

> **Purpose:** Unified test philosophy, architecture, and coverage targets
> **Audience:** Developers writing tests, CI/CD maintainers
> **Usage:** Reference for test patterns and organizational decisions

---

## Prerequisites

- `ARCHITECTURE_OVERVIEW.md` — System structure understanding

---

## Test Philosophy

### Core Principles

1. **Tests are documentation:** Tests describe expected behavior
2. **Fast feedback:** Unit tests run quickly, catch issues early
3. **Confidence in deployment:** E2E tests verify user journeys
4. **Isolated by default:** Tests don't depend on external services
5. **Deterministic:** Same inputs always produce same results

### Test Pyramid

```
                    ┌───────────┐
                    │    E2E    │  ← Few, slow, high confidence
                    │ (Playwright│
                    │  Cypress) │
                   ┌┴───────────┴┐
                   │ Integration │  ← Some, medium speed
                   │   (pytest)  │
                  ┌┴─────────────┴┐
                  │     Unit      │  ← Many, fast, focused
                  │(pytest/Vitest)│
                 ┌┴───────────────┴┐
                 │   Static Typing │  ← TypeScript, mypy
                 │     & Linting   │
                └──────────────────┘
```

---

## Test Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              E2E TESTS (Playwright)                              │
│                                                                                  │
│                    Browser → Frontend → Backend → Database                       │
│                                                                                  │
│  • User journey validation                                                       │
│  • Cross-stack integration                                                       │
│  • Visual regression (optional)                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┴──────────────────────────────┐
        ▼                                                             ▼
┌───────────────────────────────────┐       ┌───────────────────────────────────┐
│        FRONTEND TESTS             │       │        BACKEND TESTS              │
│          (Vitest)                 │       │          (pytest)                 │
│                                   │       │                                   │
│  ┌─────────────────────────────┐ │       │ ┌─────────────────────────────┐   │
│  │     Component Tests         │ │       │ │       API Tests             │   │
│  │  • Render verification      │ │       │ │  • Endpoint behavior        │   │
│  │  • Event handling           │ │       │ │  • Auth verification        │   │
│  │  • Props validation         │ │       │ │  • Response format          │   │
│  └─────────────────────────────┘ │       │ └─────────────────────────────┘   │
│                                   │       │                                   │
│  ┌─────────────────────────────┐ │       │ ┌─────────────────────────────┐   │
│  │      Store Tests            │ │       │ │      Model Tests            │   │
│  │  • State mutations          │ │       │ │  • CRUD operations          │   │
│  │  • Derived values           │ │       │ │  • Relationships            │   │
│  │  • Subscriptions            │ │       │ │  • Constraints              │   │
│  └─────────────────────────────┘ │       │ └─────────────────────────────┘   │
│                                   │       │                                   │
│  ┌─────────────────────────────┐ │       │ ┌─────────────────────────────┐   │
│  │      Utility Tests          │ │       │ │      Utility Tests          │   │
│  │  • Pure functions           │ │       │ │  • Pure functions           │   │
│  │  • Formatting               │ │       │ │  • Auth helpers             │   │
│  │  • Validation               │ │       │ │  • Transformations          │   │
│  └─────────────────────────────┘ │       │ └─────────────────────────────┘   │
└───────────────────────────────────┘       └───────────────────────────────────┘
```

---

## Coverage Targets

| Layer | Target | Rationale |
|-------|--------|-----------|
| Backend utilities | 90% | Pure functions, easy to test |
| Backend routers | 80% | API contract stability |
| Backend models | 80% | Data integrity |
| Frontend stores | 90% | State logic criticality |
| Frontend utilities | 90% | Pure functions |
| Frontend components | 70% | UI behavior |
| E2E critical paths | 100% | User journey protection |

---

## Test Organization

### Backend Tests

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── utils/
│   │   ├── test_auth.py          # JWT utilities
│   │   ├── test_middleware.py    # Request transformation
│   │   └── test_access_control.py
│   └── models/
│       ├── test_users.py         # User CRUD
│       ├── test_chats.py         # Chat operations
│       └── test_knowledge.py     # Knowledge base
├── integration/
│   ├── test_chat_flow.py         # Full chat flow
│   └── test_rag_pipeline.py      # Document processing
└── api/
    ├── test_auths.py             # Auth endpoints
    ├── test_chats.py             # Chat endpoints
    └── test_analytics.py         # Analytics endpoints
```

### Frontend Tests

```
tests/
├── setup.ts                       # Test configuration
├── unit/
│   ├── stores/
│   │   ├── user.test.ts          # User store
│   │   └── features.test.ts      # Feature stores
│   ├── utils/
│   │   ├── formatting.test.ts    # Format utilities
│   │   └── validation.test.ts    # Input validation
│   └── components/
│       ├── Chat.test.ts          # Chat component
│       └── Settings.test.ts      # Settings component
└── e2e/
    ├── auth.spec.ts              # Login/logout flows
    ├── chat.spec.ts              # Chat functionality
    └── admin.spec.ts             # Admin features
```

---

## Integration Boundaries

### What Gets Mocked

| Boundary | Mock Strategy |
|----------|---------------|
| LLM Providers | Mock HTTP responses |
| Vector Database | Use in-memory ChromaDB |
| File Storage | Use temp directory |
| Redis | Skip or use fakeredis |
| External APIs | Mock HTTP client |

### What Runs Real

| Component | Why Real |
|-----------|----------|
| SQLite (in-memory) | Fast, accurate SQL testing |
| FastAPI TestClient | Full request pipeline |
| Svelte components | Actual component behavior |
| Pydantic validation | Real validation rules |

---

## Test Patterns

### Backend: Fixture Pattern

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from open_webui.internal.db import Base

@pytest.fixture
def db_session():
    """Create isolated database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.rollback()
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    from open_webui.models.users import Users, UserCreate

    user = Users.insert_user(
        UserCreate(
            email="test@example.com",
            name="Test User",
            role="user",
        ),
        db=db_session,
    )
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin user."""
    from open_webui.models.users import Users, UserCreate

    user = Users.insert_user(
        UserCreate(
            email="admin@example.com",
            name="Admin User",
            role="admin",
        ),
        db=db_session,
    )
    return user
```

### Backend: API Test Pattern

```python
# test_chats.py
from fastapi.testclient import TestClient
from unittest.mock import patch

def test_create_chat_requires_auth(client: TestClient):
    """Creating a chat should require authentication."""
    response = client.post("/api/v1/chats", json={"title": "Test"})
    assert response.status_code == 401


def test_create_chat_success(client: TestClient, auth_token: str):
    """Authenticated user can create a chat."""
    response = client.post(
        "/api/v1/chats",
        json={"title": "Test Chat"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Chat"
    assert "id" in data
```

### Frontend: Store Test Pattern

```typescript
// stores.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { chats, addChat, removeChat } from '$lib/stores';

describe('chats store', () => {
  beforeEach(() => {
    chats.set([]);  // Reset before each test
  });

  it('should add a chat', () => {
    const chat = { id: '1', title: 'Test' };
    addChat(chat);

    expect(get(chats)).toContainEqual(chat);
  });

  it('should remove a chat by id', () => {
    chats.set([
      { id: '1', title: 'Keep' },
      { id: '2', title: 'Remove' },
    ]);

    removeChat('2');

    const value = get(chats);
    expect(value).toHaveLength(1);
    expect(value[0].id).toBe('1');
  });
});
```

### Frontend: Component Test Pattern

```typescript
// Component.test.ts
import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import Button from '$lib/components/Button.svelte';

describe('Button', () => {
  it('renders with label', () => {
    const { getByText } = render(Button, {
      props: { label: 'Click me' }
    });

    expect(getByText('Click me')).toBeTruthy();
  });

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    const { getByRole } = render(Button, {
      props: { label: 'Click', onClick }
    });

    await fireEvent.click(getByRole('button'));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when loading', () => {
    const { getByRole } = render(Button, {
      props: { label: 'Submit', loading: true }
    });

    expect(getByRole('button')).toBeDisabled();
  });
});
```

### E2E: User Journey Pattern

```typescript
// chat.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Chat functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/auth');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'password');
    await page.click('[data-testid="login"]');
    await page.waitForURL('/');
  });

  test('user can send a message and receive response', async ({ page }) => {
    // Type message
    await page.fill('[data-testid="message-input"]', 'Hello, AI!');
    await page.click('[data-testid="send-button"]');

    // Wait for response
    await page.waitForSelector('[data-testid="assistant-message"]');

    // Verify response appeared
    const response = page.locator('[data-testid="assistant-message"]');
    await expect(response).toBeVisible();
  });

  test('user can create a new chat', async ({ page }) => {
    await page.click('[data-testid="new-chat"]');

    // Verify new chat created
    const chatList = page.locator('[data-testid="chat-list"]');
    const chatCount = await chatList.locator('[data-testid="chat-item"]').count();
    expect(chatCount).toBeGreaterThan(0);
  });
});
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=open_webui --cov-report=xml

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: npm ci
      - run: npm run test:unit

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install
      - run: npm run test:e2e
```

---

## Running Tests

### Backend

```bash
# All tests
pytest

# With coverage
pytest --cov=open_webui

# Specific file
pytest tests/unit/utils/test_auth.py

# Specific test
pytest tests/unit/utils/test_auth.py::test_create_token

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Frontend

```bash
# Unit tests
npm run test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage

# E2E tests
npm run test:e2e

# E2E with UI
npm run test:e2e:ui
```

---

## Stack-Specific Guidance

For detailed test implementation patterns:

- **Backend (pytest):** See `DIRECTIVE_writing_backend_tests.md`
- **Frontend (Vitest/Playwright):** See `DIRECTIVE_writing_frontend_tests.md`

---

## Related Documents

- `DIRECTIVE_writing_backend_tests.md` — pytest patterns
- `DIRECTIVE_writing_frontend_tests.md` — Vitest/Playwright patterns
- `ARCHITECTURE_OVERVIEW.md` — System structure

---

*Last updated: 2026-02-03*
