# Test/Util Directory

This directory contains shared test infrastructure and utilities for Open WebUI's integration test suite. It provides abstract base classes for database-backed testing, user authentication mocking, and Redis session management tests.

## Purpose

This directory provides:
- **Test Base Classes**: `AbstractIntegrationTest` and `AbstractPostgresTest` for standardized test structure
- **Authentication Mocking**: FastAPI dependency override utilities for bypassing JWT validation
- **Database Lifecycle**: Automated PostgreSQL Docker container management
- **Connection Management**: Database health checks and retry logic
- **Test Isolation**: Table truncation between test methods

## Files

### abstract_integration_test.py
**Purpose:** Provides abstract base classes for integration tests with database backing.

**Key Classes:**

#### AbstractIntegrationTest
**Purpose:** Base class for all integration tests with URL building utilities.

**Features:**
- `BASE_PATH` - Class attribute defining API endpoint prefix (e.g., "/api/v1/auths")
- `create_url(path, query_params)` - URL builder for endpoint paths
- Lifecycle hooks: `setup_class()`, `teardown_class()`, `setup_method()`, `teardown_method()`

**Usage Pattern:**
```python
class TestAuths(AbstractIntegrationTest):
    BASE_PATH = "/api/v1/auths"

    def test_something(self):
        url = self.create_url("/signin", query_params={"redirect": "/"})
        # url == "/api/v1/auths/signin?redirect=/"
```

#### AbstractPostgresTest
**Purpose:** PostgreSQL-backed integration test class with Docker container management.

**Inherits:** `AbstractIntegrationTest`

**Features:**
- Automatic PostgreSQL 16.2 Docker container lifecycle
- Database URL construction with Docker networking
- Migration execution on startup
- FastAPI TestClient initialization
- Connection health checks with 10 retries
- Table truncation in `teardown_method()`
- Container cleanup in `teardown_class()`

**Container Configuration:**
- Image: `postgres:16.2`
- Container name: `postgres-test-container-will-get-deleted` (unique identifier)
- Port mapping: 5432 (container) → 8081 (host)
- Environment: `POSTGRES_USER=user`, `POSTGRES_PASSWORD=example`, `POSTGRES_DB=openwebui`
- Logging: `log_statement=all` (full SQL logging for debugging)

**Database Connection:**
- URL format: `postgresql://user:example@{docker_ip}:8081/openwebui`
- Docker IP resolved via `get_docker_ip()` from pytest-docker
- Connection pooling with `pool_pre_ping=True`

**setup_class() Workflow:**
```
1. Initialize Docker client (docker.from_env())
2. Start PostgreSQL container with configuration
3. Wait 0.5 seconds for container initialization
4. Construct DATABASE_URL
5. Set DATABASE_URL environment variable
6. Retry database connection (10 attempts with 3s intervals)
7. Import main app (triggers migrations)
8. Create FastAPI TestClient
9. Store client in cls.fast_api_client
```

**setup_method() Workflow:**
```
1. Call parent setup_method()
2. Execute _check_db_connection()
   - Retry SELECT 1 query (10 attempts)
   - Commit or rollback based on result
```

**teardown_method() Workflow:**
```
1. Commit pending transactions
2. Truncate tables in order:
   - auth
   - chat
   - chatidtag
   - document
   - memory
   - model
   - prompt
   - tag
   - "user" (quoted, PostgreSQL reserved keyword)
3. Commit truncation
```

**teardown_class() Workflow:**
```
1. Call parent teardown_class()
2. Get container by name
3. Force remove container (remove(force=True))
```

**Used by:**
- `test/apps/webui/routers/test_*.py` - All router integration tests
- Any test requiring real database

**Uses:**
- `open_webui.internal.db.Session` - Database session for truncation
- `open_webui.config.OPEN_WEBUI_DIR` - Configuration import (triggers migrations)
- `main.app` - FastAPI application instance

### mock_user.py
**Purpose:** Provides user authentication mocking utilities for FastAPI dependency injection.

**Key Functions:**

#### mock_webui_user(**kwargs)
**Purpose:** Context manager for mocking authenticated user in WebUI app.

**Usage:**
```python
with mock_webui_user(id="user123", role="admin"):
    response = client.get("/api/v1/auths")
    # get_current_user() returns mocked user
```

**Parameters (kwargs):**
- `id` - User ID (default: "1")
- `name` - User name (default: "John Doe")
- `email` - User email (default: "john.doe@openwebui.com")
- `role` - User role (default: "user", options: "user", "admin", "pending")
- `profile_image_url` - Profile image path (default: "/user.png")
- Other User model fields

**Behavior:**
- Imports WebUI app from `open_webui.routers.webui`
- Delegates to `mock_user(app, **kwargs)`
- Automatically cleans up overrides on context exit

#### mock_user(app, **kwargs)
**Purpose:** Generic context manager for mocking user in any FastAPI app.

**Overridden Dependencies:**
1. `get_current_user` - Standard authenticated user
2. `get_verified_user` - Email-verified user
3. `get_admin_user` - Admin role validation
4. `get_current_user_by_api_key` - API key authentication

**Implementation:**
```python
def create_user():
    return User(
        id="1",
        name="John Doe",
        email="john.doe@openwebui.com",
        role="user",
        profile_image_url="/user.png",
        last_active_at=1627351200,
        updated_at=1627351200,
        created_at=162735120,
        **kwargs  # Override defaults
    )

app.dependency_overrides = {
    get_current_user: create_user,
    # ... other dependencies
}
```

**Used by:**
- `test/apps/webui/routers/test_*.py` - All router tests requiring authentication
- Any test needing to bypass JWT validation

**Uses:**
- `open_webui.utils.auth` - Auth dependency functions
- `open_webui.models.users.User` - User model for mock data

### test_redis.py
**Purpose:** Integration tests for Redis session management and caching.

**File Size:** 29,476 bytes (comprehensive test suite)

**Test Coverage:**
- Redis connection establishment
- Session storage and retrieval
- WebSocket session pooling (SESSION_POOL, USER_POOL)
- Key expiration and TTL
- Connection pool behavior
- Error handling and reconnection

**Used by:**
- CI/CD pipelines testing Redis integration
- Developers validating Redis configuration

**Uses:**
- `open_webui.utils.redis` - Redis client utilities
- `redis` library - Python Redis client

**Configuration:**
- Requires `REDIS_URL` environment variable
- Tests skipped if Redis not available (pytest markers)

## Architecture & Patterns

### Abstract Base Class Pattern
**Purpose:** Provide consistent interface for integration tests.

**Hierarchy:**
```
AbstractIntegrationTest (base)
  ├─ URL building utilities
  ├─ Lifecycle hooks
  └─ BASE_PATH configuration

AbstractPostgresTest (extends)
  ├─ Docker container management
  ├─ Database initialization
  ├─ TestClient creation
  └─ Table truncation
```

**Benefits:**
- DRY principle (no repeated container setup)
- Standardized test structure
- Easy to add new test classes

### Context Manager Pattern
**Purpose:** Ensure proper cleanup of dependency overrides.

**Implementation:**
```python
@contextmanager
def mock_webui_user(**kwargs):
    # Setup: Override dependencies
    app.dependency_overrides = {...}

    yield  # Test executes here

    # Teardown: Clear overrides (even if exception)
    app.dependency_overrides = {}
```

**Benefits:**
- Automatic cleanup on exception
- Clean syntax with `with` statement
- No leaked state between tests

### Retry Pattern
**Purpose:** Handle timing issues with external services (PostgreSQL, Docker).

**Implementation in `_check_db_connection()`:**
```python
retries = 10
while retries > 0:
    try:
        Session.execute(text("SELECT 1"))
        Session.commit()
        break  # Success
    except Exception as e:
        Session.rollback()
        log.warning(e)
        time.sleep(3)
        retries -= 1
```

**Used for:**
- Database connection establishment
- Docker container readiness
- Service availability checks

### Dependency Injection Override Pattern
**Purpose:** Replace authentication dependencies with test doubles.

**FastAPI Mechanism:**
```python
# Production
@app.get("/endpoint")
def handler(user: User = Depends(get_current_user)):
    # user comes from JWT token validation
    pass

# Test
app.dependency_overrides = {get_current_user: lambda: mock_user}
# Now handler receives mock_user directly
```

## Integration Points

### test/util/ → routers/
**Authentication Bypass:** All router tests use `mock_webui_user()`.

```python
# In test_auths.py
with mock_webui_user(id="user1", role="admin"):
    response = self.fast_api_client.post("/api/v1/auths/update/profile", ...)
# routers/auths.py receives mocked user from get_current_user()
```

### test/util/ → internal/db.py
**Database Session:** `AbstractPostgresTest` uses Session for truncation.

```python
# In abstract_integration_test.py teardown_method()
from open_webui.internal.db import Session

Session.execute(text("TRUNCATE TABLE auth"))
Session.commit()
# Clears data between tests
```

### test/util/ → main.py
**Application Import:** `get_fast_api_client()` imports app to create TestClient.

```python
from main import app

with TestClient(app) as c:
    # App startup runs:
    # 1. Database migrations
    # 2. Router registration
    # 3. Middleware setup
```

### test/util/ → Docker Daemon
**Container Lifecycle:** `AbstractPostgresTest` manages PostgreSQL via Docker API.

```
docker.from_env()
  ↓
containers.run("postgres:16.2", ...)
  ↓
Container runs on host
  ↓
Tests execute
  ↓
containers.get("postgres-test-container-will-get-deleted").remove(force=True)
```

### test/util/ → pytest
**Test Framework Integration:** Lifecycle methods integrate with pytest.

```
pytest discovers test class
  ↓
Calls setup_class() (once per class)
  ↓
For each test method:
    setup_method()
    test_method()
    teardown_method()
  ↓
Calls teardown_class() (once per class)
```

## Key Workflows

### PostgreSQL Test Lifecycle
```
Test class starts
  ↓
setup_class():
  1. Start Docker container
  2. Wait for PostgreSQL ready
  3. Set DATABASE_URL environment
  4. Import app (runs migrations)
  5. Create TestClient
  ↓
First test method:
  setup_method(): Check DB connection
  Execute test
  teardown_method(): TRUNCATE tables
  ↓
Subsequent test methods:
  (Repeat setup_method → test → teardown_method)
  ↓
All tests complete
  ↓
teardown_class(): Remove Docker container
```

### Authentication Mocking Workflow
```
Test starts
  ↓
with mock_webui_user(role="admin"):
  1. Import auth dependencies
  2. Create User instance with specified parameters
  3. Override app.dependency_overrides
  ↓
Test makes API call
  ↓
FastAPI dependency resolution:
  - get_current_user() → Returns mock User
  - No JWT validation
  ↓
Endpoint executes with mock user
  ↓
Context exits
  ↓
app.dependency_overrides cleared
```

### Database Connection Retry Workflow
```
setup_class() or setup_method()
  ↓
_check_db_connection():
  retries = 10
  ↓
Attempt SELECT 1:
  Success? → Break loop
  Failure? →
    1. Rollback session
    2. Log warning
    3. Sleep 3 seconds
    4. Decrement retries
    5. Retry
  ↓
retries == 0? → Test fails (database unavailable)
retries > 0? → Test continues
```

## Important Notes

### Critical Dependencies
- **docker**: Docker Python SDK for container management
- **pytest-docker**: pytest integration for Docker utilities (get_docker_ip)
- **FastAPI TestClient**: Starlette-based test client
- **SQLAlchemy**: Database session and text() for raw SQL
- **time**: sleep() for retry delays

### Configuration
Environment variables:
- `DATABASE_URL` - Set dynamically by `AbstractPostgresTest`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - Container configuration
- `REDIS_URL` - Required for Redis tests (if enabled)

### Docker Requirements
- **Docker daemon must be running** before tests execute
- **Port 8081 must be available** on host (or change in `_create_db_url()`)
- **Container naming** uses hardcoded name for predictable cleanup
- **Network access** to Docker socket (Unix: `/var/run/docker.sock`, Windows: named pipe)

**Linux-Specific:**
- User must be in `docker` group or tests run as root
- Socket permissions: `chmod 666 /var/run/docker.sock` (not recommended for production)

### Performance Considerations
- **Container startup overhead:** ~2-3 seconds per test class
- **Migration overhead:** Alembic migrations run on each app import (~1 second)
- **Truncation overhead:** ~50ms per table per test method
- **Retry delays:** 3 seconds × retry count (max 30 seconds for 10 retries)

**Optimization Strategies:**
- Group related tests in same class (share container)
- Minimize test data creation (use minimal fixtures)
- Reduce retry count in stable environments
- Use class-scoped fixtures for expensive setup

### Troubleshooting

**Container Already Exists:**
```bash
# Error: container name already in use
docker rm -f postgres-test-container-will-get-deleted
# Caused by interrupted test run or cleanup failure
```

**Port Conflict:**
```bash
# Error: port 8081 already in use
# Change port in _create_db_url() or stop conflicting service
lsof -ti:8081 | xargs kill  # Kill process using port
```

**Database Connection Timeout:**
- Check Docker daemon running: `docker ps`
- Increase retry count from 10 to 20
- Check container logs: `docker logs postgres-test-container-will-get-deleted`
- Verify network connectivity to Docker

**Migration Failures:**
- Check Alembic migration scripts in `migrations/versions/`
- Verify DATABASE_URL format matches PostgreSQL expectations
- Review PostgreSQL logs (enable `log_statement=all`)
- Check for schema conflicts (previous test data)

**Mock Not Applied:**
- Ensure `mock_webui_user()` context manager used
- Verify context not exited prematurely
- Check app.dependency_overrides not cleared elsewhere
- Confirm correct app instance (webui vs. main)

### Security Considerations
- **Hardcoded credentials** (`user`/`example`) acceptable for ephemeral test containers
- **Port exposure** (0.0.0.0) only for local development
- **No TLS** required for local Docker connections
- **Test data sanitization** - no production data should reach test database
- **Container cleanup** essential to prevent resource leaks

### Best Practices

**When Writing New Tests:**
1. Inherit from `AbstractPostgresTest` for database-backed tests
2. Use `mock_webui_user()` for authenticated endpoint tests
3. Set `BASE_PATH` class attribute for URL building
4. Access models via class attributes (e.g., `self.users`, `self.auths`)
5. Truncate tables automatically via `teardown_method()` - no manual cleanup needed

**When Debugging:**
1. Check Docker container running: `docker ps`
2. Inspect container logs: `docker logs postgres-test-container-will-get-deleted`
3. Connect to database: `psql postgresql://user:example@localhost:8081/openwebui`
4. Enable SQL logging: `log_statement=all` (already configured)
5. Use `pytest -v` for verbose output
6. Use `pytest -s` to show print statements

**CI/CD Integration:**
- Ensure Docker-in-Docker or Docker socket available
- Set appropriate timeouts for container startup
- Clean up orphaned containers: `docker rm -f $(docker ps -aq --filter name=postgres-test-container)`
- Consider unique container names per build: `postgres-test-{BUILD_ID}`
- Parallelize test classes with `pytest -n auto` (unique container names required)

### Future Improvements
Potential enhancements:
- Parameterized container names for parallel execution
- Connection pool configuration for performance testing
- Database seeding fixtures for common test data
- Snapshot testing utilities for complex API responses
- Automatic log collection on test failure
- Docker Compose integration for multi-service tests (Redis + PostgreSQL)
- Test database schema validation (compare to production)
- Performance metrics collection (query duration tracking)
