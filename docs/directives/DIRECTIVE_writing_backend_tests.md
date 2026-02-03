# Directive: Writing Backend Tests

> **Pattern type:** Quality assurance
> **Complexity:** Low-Medium
> **Files touched:** 1-3

---

## Prerequisites

- `TESTING_STRATEGY.md` — Overall test philosophy
- `ARCHITECTURE_OVERVIEW.md` — Backend structure

---

## Structural Pattern

Backend tests use pytest with these patterns:

1. **Unit tests** for pure functions and utilities
2. **Integration tests** for database operations
3. **API tests** for endpoint behavior
4. **Fixtures** for shared test setup

| Test Type | Location | Dependencies |
|-----------|----------|--------------|
| Unit tests | `tests/unit/` | None or mocked |
| Integration | `tests/integration/` | Test database |
| API tests | `tests/api/` | FastAPI TestClient |

---

## Illustrative Application

### Step 1: Unit Test for Utility Functions

```python
# tests/unit/utils/test_auth.py
import pytest
from open_webui.utils.auth import create_token, decode_token


class TestTokenGeneration:
    """Tests for JWT token utilities."""

    def test_create_token_includes_user_id(self):
        """Token should include the user ID."""
        token = create_token({"id": "user-123"})
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["id"] == "user-123"

    def test_create_token_includes_expiration(self):
        """Token should include expiration time."""
        token = create_token({"id": "user-123"})
        decoded = decode_token(token)

        assert "exp" in decoded

    def test_decode_invalid_token_returns_none(self):
        """Invalid token should return None."""
        result = decode_token("invalid-token")

        assert result is None

    def test_decode_expired_token_returns_none(self):
        """Expired token should return None."""
        from datetime import timedelta
        token = create_token(
            {"id": "user-123"},
            expires_delta=timedelta(seconds=-1)
        )
        result = decode_token(token)

        assert result is None
```

### Step 2: Integration Test with Database

```python
# tests/integration/models/test_users.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from open_webui.internal.db import Base
from open_webui.models.users import User, Users, UserCreate


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


class TestUserModel:
    """Tests for User database operations."""

    def test_insert_user(self, db_session):
        """Should insert a new user."""
        user_data = UserCreate(
            email="test@example.com",
            name="Test User",
            role="user",
        )

        user = Users.insert_user(user_data, db=db_session)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    def test_get_user_by_email(self, db_session):
        """Should retrieve user by email."""
        Users.insert_user(
            UserCreate(email="find@example.com", name="Find Me", role="user"),
            db=db_session,
        )

        user = Users.get_user_by_email("find@example.com", db=db_session)

        assert user is not None
        assert user.name == "Find Me"

    def test_get_user_by_email_not_found(self, db_session):
        """Should return None for non-existent email."""
        user = Users.get_user_by_email("notfound@example.com", db=db_session)

        assert user is None

    def test_update_user(self, db_session):
        """Should update user fields."""
        user = Users.insert_user(
            UserCreate(email="update@example.com", name="Original", role="user"),
            db=db_session,
        )

        updated = Users.update_user(
            user.id,
            {"name": "Updated"},
            db=db_session,
        )

        assert updated.name == "Updated"
```

### Step 3: API Endpoint Test

```python
# tests/api/test_analytics.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from open_webui.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Create admin user token for tests."""
    from open_webui.utils.auth import create_token
    return create_token({"id": "admin-user-id"})


@pytest.fixture
def mock_admin_user():
    """Mock admin user dependency."""
    mock_user = MagicMock()
    mock_user.id = "admin-user-id"
    mock_user.role = "admin"
    return mock_user


class TestAnalyticsEndpoints:
    """Tests for analytics API endpoints."""

    def test_get_summary_requires_admin(self, client):
        """Summary endpoint should require admin role."""
        response = client.get("/api/v1/analytics/summary")

        assert response.status_code == 401

    def test_get_summary_returns_data(
        self, client, admin_token, mock_admin_user
    ):
        """Summary endpoint should return analytics data."""
        with patch(
            "open_webui.routers.analytics.get_admin_user",
            return_value=mock_admin_user
        ):
            response = client.get(
                "/api/v1/analytics/summary",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "total_messages" in data
        assert "total_tokens" in data

    def test_get_models_with_date_filter(
        self, client, admin_token, mock_admin_user
    ):
        """Models endpoint should accept date filters."""
        with patch(
            "open_webui.routers.analytics.get_admin_user",
            return_value=mock_admin_user
        ):
            response = client.get(
                "/api/v1/analytics/models",
                params={
                    "start_date": 1704067200,  # 2024-01-01
                    "end_date": 1706745600,    # 2024-02-01
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 200
```

### Step 4: Test Configuration

```python
# tests/conftest.py
import pytest
import os

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["WEBUI_SECRET_KEY"] = "test-secret-key"


@pytest.fixture(scope="session")
def test_db():
    """Create test database for session."""
    from sqlalchemy import create_engine
    from open_webui.internal.db import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()
```

---

## Transfer Prompt

**When you need to write backend tests:**

1. **For utility functions** (no dependencies):
   ```python
   # tests/unit/utils/test_{module}.py
   def test_function_behavior():
       result = my_function(input)
       assert result == expected
   ```

2. **For database operations** (need session):
   ```python
   # tests/integration/models/test_{model}.py
   @pytest.fixture
   def db_session():
       engine = create_engine("sqlite:///:memory:")
       Base.metadata.create_all(engine)
       session = sessionmaker(bind=engine)()
       yield session
       session.close()

   def test_model_operation(db_session):
       # Test with real database
   ```

3. **For API endpoints** (need client):
   ```python
   # tests/api/test_{router}.py
   from fastapi.testclient import TestClient

   @pytest.fixture
   def client():
       return TestClient(app)

   def test_endpoint(client):
       response = client.get("/api/v1/endpoint")
       assert response.status_code == 200
   ```

4. **Mock external dependencies:**
   ```python
   from unittest.mock import patch, MagicMock

   def test_with_mock():
       with patch("module.external_function") as mock:
           mock.return_value = "mocked"
           result = function_under_test()
   ```

5. **Run tests:**
   ```bash
   # All tests
   pytest

   # Specific file
   pytest tests/unit/utils/test_auth.py

   # With coverage
   pytest --cov=open_webui
   ```

**Test file naming:**
- `test_{module}.py` — Test file
- `Test{Class}` — Test class
- `test_{behavior}` — Test function

**Signals that this pattern applies:**
- Adding new utility function
- Creating new database model
- Adding API endpoint
- Fixing a bug (write regression test)

---

## Related Documents

- `TESTING_STRATEGY.md` — Test philosophy
- `DIRECTIVE_writing_frontend_tests.md` — Frontend tests
- `ADR_010_query_optimization.md` — Testing optimized queries

---

*Last updated: 2026-02-03*
