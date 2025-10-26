# Test Directory

This directory contains the integration test suite for Open WebUI's backend. It provides test infrastructure for testing API endpoints, database operations, and storage providers using real database backends (PostgreSQL via Docker) rather than mocks. The test suite ensures backward compatibility and validates critical workflows across the application.

## Purpose

This directory provides:
- **Integration Tests**: End-to-end API endpoint testing with real database
- **Test Infrastructure**: Abstract base classes for PostgreSQL-backed tests
- **Mocking Utilities**: User authentication mocking for dependency injection
- **Router Coverage**: Tests for authentication, chats, users, models, prompts
- **Storage Testing**: Provider abstraction validation with mock cloud services

## Directory Structure

### util/ - Test Utilities
Contains shared test infrastructure and helpers:
- `abstract_integration_test.py` - Base classes for integration tests
- `mock_user.py` - FastAPI dependency override for authentication
- `test_redis.py` - Redis session management tests

### apps/webui/routers/ - Router Tests
Tests for API endpoint functionality:
- `test_auths.py` - Authentication endpoints (signin, signup, password change)
- `test_chats.py` - Chat CRUD operations and sharing
- `test_users.py` - User management and admin operations
- `test_models.py` - Model configuration and management
- `test_prompts.py` - Prompt CRUD operations

### apps/webui/storage/ - Storage Tests
Tests for storage provider abstraction:
- `test_provider.py` - All storage backend implementations (Local, S3, GCS, Azure)

## Architecture & Patterns

### Integration Test Pattern
All tests inherit from `AbstractPostgresTest` which provides:
1. Docker container lifecycle management (PostgreSQL 16.2)
2. Database initialization with migrations
3. FastAPI TestClient setup
4. Table truncation between tests
5. Connection health checks with retries

**Test Lifecycle:**
```
setup_class()
  ↓
Start PostgreSQL Docker container
  ↓
Wait for database readiness (10 retries with 3s intervals)
  ↓
Set DATABASE_URL environment variable
  ↓
Import main app (triggers migrations)
  ↓
Create FastAPI TestClient
  ↓
Run test methods
  ↓
teardown_method(): Truncate all tables
  ↓
teardown_class(): Remove Docker container
```

### Dependency Override Pattern
Tests use `mock_webui_user()` context manager to bypass authentication:
```python
with mock_webui_user(id="user123", role="admin"):
    response = client.get("/api/v1/auths")
# All auth dependencies (get_current_user, get_verified_user, etc.) return mock user
```

**Overridden Dependencies:**
- `get_current_user` - Standard authenticated user
- `get_verified_user` - Email-verified user
- `get_admin_user` - Admin role validation
- `get_current_user_by_api_key` - API key authentication

### Docker-Based Testing
Uses `pytest-docker` and Docker Python SDK to:
- Spin up PostgreSQL containers on demand
- Map container port 5432 to host port 8081
- Configure PostgreSQL with test credentials
- Enable full SQL logging for debugging
- Force-remove containers after tests

### Table Truncation Strategy
Between test methods, truncates tables in specific order:
1. `auth` - Authentication records
2. `chat` - Conversations
3. `chatidtag` - Chat-tag associations
4. `document` - RAG documents
5. `memory` - User memories
6. `model` - Model configurations
7. `prompt` - Prompt templates
8. `tag` - Tags
9. `"user"` - User accounts (quoted, reserved keyword)

**Purpose:** Maintain isolated test state without full database recreation.

### Mock Service Pattern (Storage Tests)
Storage tests use mocking libraries for cloud services:
- **S3**: `moto` library with `@mock_aws` decorator
- **GCS**: `gcp_storage_emulator` server
- **Azure**: `unittest.mock.MagicMock` for BlobServiceClient

**Benefits:**
- No cloud credentials required
- Fast test execution
- Deterministic behavior
- No cost for API calls

## Integration Points

### test/ → routers/
**Primary Integration:** Tests validate router endpoint behavior.

```python
# In test_auths.py
response = self.fast_api_client.post(
    "/api/v1/auths/update/password",
    json={"password": "new_pass", "new_password": "updated_pass"}
)
# Calls routers/auths.py update_password() endpoint
```

### test/util/ → routers/
**Authentication Mocking:** Overrides FastAPI dependency injection.

```python
# In mock_user.py
app.dependency_overrides = {
    get_current_user: create_user,
    # ... other auth dependencies
}
# Tests bypass JWT validation
```

### test/ → models/
**Database Access:** Tests interact with model DAOs for validation.

```python
# In test_auths.py
user = self.auths.insert_new_auth(
    email="test@example.com",
    password=get_password_hash("password"),
    name="Test User",
)
# Direct model access to setup test data
```

### test/ → storage/provider.py
**Storage Testing:** Validates all provider implementations.

```python
# In test_provider.py
from open_webui.storage import provider

Storage = provider.get_storage_provider("s3")
Storage.upload_file(file_path, file_id)
# Tests provider abstraction interface
```

### test/ → main.py
**Application Import:** TestClient imports app to trigger initialization.

```python
from main import app
with TestClient(app) as c:
    # App startup runs migrations, registers routers
```

### Docker → PostgreSQL
**Container Management:** Tests control PostgreSQL lifecycle via Docker API.

```
docker.from_env()
  ↓
containers.run("postgres:16.2")
  ↓
Port mapping: 5432 → 8081
  ↓
Health check: SELECT 1
  ↓
Tests execute
  ↓
containers.get().remove(force=True)
```

## Key Workflows

### Running All Tests
```bash
# From backend/ directory
pytest open_webui/test/

# Workflow:
1. pytest discovers test_*.py files
2. For each test class:
   a. setup_class() starts PostgreSQL container
   b. Database initialized with migrations
   c. Test methods execute sequentially
   d. teardown_method() truncates tables
   e. teardown_class() removes container
3. Test report generated
```

### Single Router Test Workflow
```
test_auths.py::test_update_profile
  ↓
setup_class(): Start PostgreSQL, create TestClient
  ↓
setup_method(): Check database connection
  ↓
Test execution:
  1. Create user via auths.insert_new_auth()
  2. Mock authentication with mock_webui_user()
  3. POST /api/v1/auths/update/profile
  4. Verify response.status_code == 200
  5. Query database to confirm update
  ↓
teardown_method(): TRUNCATE all tables
  ↓
Next test or teardown_class()
```

### Storage Provider Test Workflow
```
test_provider.py::test_s3_upload
  ↓
@mock_aws decorator activates moto mocking
  ↓
Test execution:
  1. Create mock S3 bucket
  2. Get S3StorageProvider
  3. Upload file via provider.upload_file()
  4. Verify file exists in mock S3
  5. Download and verify content
  ↓
Mocking automatically tears down
```

### Redis Test Workflow
```
test_redis.py::test_redis_connection
  ↓
Requires REDIS_URL environment variable
  ↓
Test execution:
  1. Connect to Redis via get_redis_client()
  2. Perform operations (set, get, delete)
  3. Verify behavior
  ↓
No special teardown (Redis external service)
```

## Important Notes

### Critical Dependencies
- **Docker**: Required for PostgreSQL container management
- **pytest**: Test framework with fixtures and assertions
- **pytest-docker**: Docker integration for pytest
- **moto**: AWS service mocking (S3 tests)
- **gcp-storage-emulator**: GCS mocking
- **TestClient**: FastAPI's test client (built on Starlette)

### Configuration
Tests configure via environment variables:
- `DATABASE_URL` - Set dynamically to PostgreSQL container URL
- `REDIS_URL` - Required for Redis tests (if enabled)
- Test-specific: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

### Docker Requirements
Tests expect:
- Docker daemon running
- Permission to create/destroy containers
- Network access to Docker daemon
- Available port 8081 for PostgreSQL

**Docker-Specific Issues:**
- Port conflicts if 8081 already in use
- Container cleanup failures require manual `docker rm -f postgres-test-container-will-get-deleted`
- Docker socket permission errors on Linux (add user to docker group)

### Performance Considerations
- **Slow Startup**: PostgreSQL container creation ~2-3 seconds per test class
- **Migration Overhead**: Alembic migrations run on each app import
- **Sequential Execution**: Tests run serially within class (shared database)
- **Parallelization**: Can run multiple test classes in parallel with `pytest -n auto` (separate containers)

**Optimization Strategies:**
- Group related tests in same class (share container)
- Minimize test data creation
- Use table truncation instead of DROP/CREATE
- Consider class-scoped fixtures for expensive setup

### Test Isolation
**Between Test Methods:**
- Table truncation ensures clean state
- No CASCADE deletes (foreign keys preserved in schema)
- Session rollback before truncation

**Between Test Classes:**
- Separate PostgreSQL containers (if parallel)
- Fresh migrations on each app import
- Independent database state

### Debugging Failed Tests
**Common Issues:**
1. **Container already exists:**
   - Manual cleanup: `docker rm -f postgres-test-container-will-get-deleted`
   - Caused by interrupted test run

2. **Database connection timeout:**
   - Check Docker daemon status
   - Increase retry count in `setup_class()`
   - Review Docker logs: `docker logs postgres-test-container-will-get-deleted`

3. **Migration failures:**
   - Check Alembic migration scripts
   - Verify DATABASE_URL format
   - Review PostgreSQL logs (log_statement=all)

4. **Authentication failures:**
   - Verify `mock_webui_user()` context manager used
   - Check dependency overrides not cleared prematurely
   - Ensure role matches endpoint requirements

### Security Considerations
- Test database credentials hardcoded (user/example) - OK for ephemeral containers
- No production data should ever touch test infrastructure
- Docker containers expose port to host (0.0.0.0) - local development only
- API keys in tests should be dummy/invalid values

### CI/CD Integration
**Requirements for Automation:**
- Docker-in-Docker or Docker socket mount
- Sufficient permissions for container management
- Cleanup of orphaned containers (setup retry logic)
- Parallel test execution with unique container names

**GitHub Actions Example:**
```yaml
- name: Run integration tests
  run: |
    docker ps  # Verify Docker available
    pytest backend/open_webui/test/ -v
  env:
    DATABASE_URL: postgresql://user:example@localhost:8081/openwebui
```

### Coverage Gaps
Current test suite covers:
- ✅ Authentication endpoints
- ✅ Chat CRUD
- ✅ User management
- ✅ Model management
- ✅ Prompt management
- ✅ Storage providers
- ✅ Redis operations (optional)

Not covered:
- ❌ File upload/download endpoints
- ❌ RAG processing workflows
- ❌ WebSocket events
- ❌ LLM proxy endpoints
- ❌ Tool/function execution
- ❌ Collaborative editing (Yjs)

### Future Improvements
Potential enhancements:
- Factory fixtures for common test data (users, chats)
- Snapshot testing for complex API responses
- Performance benchmarks (response time tracking)
- Mock LLM providers for completion endpoint tests
- WebSocket test client for socket events
- Parameterized tests for multiple database backends
- Test coverage reporting integration
- Automated test database seeding with realistic data
