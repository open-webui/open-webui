# Test/Apps/Webui/Routers Directory

This directory contains integration tests for Open WebUI's API router endpoints. Each test file validates the functionality of corresponding routers in `backend/open_webui/routers/`, ensuring correct behavior of authentication, chat management, user administration, model configuration, and prompt operations.

## Purpose

This directory provides:
- **Authentication Testing**: Signin, signup, password management, profile updates
- **Chat Testing**: CRUD operations, sharing, tagging, archiving
- **User Management Testing**: User creation, updates, role changes, deletion
- **Model Testing**: Model configuration and metadata management
- **Prompt Testing**: Prompt template CRUD operations

## Files

### test_auths.py
**Purpose:** Tests authentication and profile management endpoints.

**Test Coverage:**
- `test_get_session_user()` - GET /api/v1/auths (retrieve current user)
- `test_update_profile()` - POST /api/v1/auths/update/profile (name, image)
- `test_update_password()` - POST /api/v1/auths/update/password (old → new password)
- Password hashing validation
- Profile field updates

**Pattern:**
```python
class TestAuths(AbstractPostgresTest):
    BASE_PATH = "/api/v1/auths"

    def test_get_session_user(self):
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert response.json() == {...}  # Expected user data
```

**Key Assertions:**
- Status codes (200, 400, 401, 403)
- Response JSON structure
- Database state after operations
- Password hash changes

**Used by:** CI/CD pipelines, developers validating auth flows

**Uses:**
- `routers/auths.py` - Authentication router endpoints
- `models/auths.py` - Auth model DAO
- `models/users.py` - User model DAO
- `utils/auth.py` - Password hashing utilities
- `test/util/mock_user.py` - Authentication mocking

### test_chats.py
**Purpose:** Tests chat CRUD operations and sharing functionality.

**Test Coverage:**
- `test_create_chat()` - POST /api/v1/chats/new (new chat creation)
- `test_get_chat_by_id()` - GET /api/v1/chats/{id} (retrieve chat)
- `test_update_chat_by_id()` - POST /api/v1/chats/{id} (update messages/title)
- `test_delete_chat_by_id()` - DELETE /api/v1/chats/{id} (soft delete)
- `test_get_all_user_chats()` - GET /api/v1/chats/ (list user chats)
- `test_archive_chat()` - POST /api/v1/chats/{id}/archive (archive chat)
- `test_share_chat()` - POST /api/v1/chats/{id}/share (create share link)
- Chat tagging operations

**Key Assertions:**
- Chat creation with messages
- Message array updates
- Title generation
- Archive status changes
- Share ID generation (UUID)
- User ownership validation
- Pagination of chat lists

**Used by:** CI/CD pipelines, developers validating chat flows

**Uses:**
- `routers/chats.py` - Chat router endpoints
- `models/chats.py` - Chat model DAO
- `models/tags.py` - Tag model DAO (for chat tagging)
- `test/util/mock_user.py` - User authentication mocking

### test_users.py
**Purpose:** Tests user management and admin operations.

**Test Coverage:**
- `test_get_users()` - GET /api/v1/users/ (list all users, admin only)
- `test_create_user()` - POST /api/v1/users/create (admin create user)
- `test_get_user_by_id()` - GET /api/v1/users/{id} (retrieve user profile)
- `test_update_user_by_id()` - POST /api/v1/users/{id}/update (admin update user)
- `test_update_user_role()` - POST /api/v1/users/{id}/update (role change)
- `test_delete_user_by_id()` - DELETE /api/v1/users/{id} (soft delete)
- Permission validation (admin vs. user)

**Key Assertions:**
- Admin-only access enforcement
- Role changes (user, admin, pending)
- Profile field updates (name, email, image)
- User deletion (soft delete, not hard delete)
- User list pagination
- Permission checks

**Used by:** CI/CD pipelines, developers validating user management

**Uses:**
- `routers/users.py` - User router endpoints
- `models/users.py` - User model DAO
- `models/auths.py` - Auth model DAO
- `test/util/mock_user.py` - User authentication and role mocking

### test_models.py
**Purpose:** Tests model configuration management.

**Test Coverage:**
- `test_get_models()` - GET /api/v1/models/ (list all models)
- `test_create_model()` - POST /api/v1/models/create (add model config)
- `test_get_model_by_id()` - GET /api/v1/models/{id} (retrieve model)
- `test_update_model_by_id()` - POST /api/v1/models/{id}/update (update config)
- `test_delete_model_by_id()` - DELETE /api/v1/models/{id} (remove model)
- Model metadata validation
- Base model ID references

**Key Assertions:**
- Model CRUD operations
- Metadata field updates (name, description, capabilities)
- Base model ID linking
- Model ID format validation
- Model list filtering

**Used by:** CI/CD pipelines, developers validating model management

**Uses:**
- `routers/models.py` - Model router endpoints
- `models/models.py` - Model model DAO (Model configuration, not LLM models)
- `test/util/mock_user.py` - User authentication mocking

### test_prompts.py
**Purpose:** Tests prompt template management.

**Test Coverage:**
- `test_get_prompts()` - GET /api/v1/prompts/ (list all prompts)
- `test_create_prompt()` - POST /api/v1/prompts/create (create prompt template)
- `test_get_prompt_by_command()` - GET /api/v1/prompts/{command} (retrieve by command)
- `test_update_prompt_by_command()` - POST /api/v1/prompts/{command}/update (update)
- `test_delete_prompt_by_command()` - DELETE /api/v1/prompts/{command} (delete)
- Command name validation
- Prompt content updates

**Key Assertions:**
- Prompt CRUD operations
- Command uniqueness
- Prompt content validation
- User ownership
- Prompt list retrieval

**Used by:** CI/CD pipelines, developers validating prompt management

**Uses:**
- `routers/prompts.py` - Prompt router endpoints
- `models/prompts.py` - Prompt model DAO
- `test/util/mock_user.py` - User authentication mocking

## Architecture & Patterns

### Test Class Structure
All test files follow the same pattern:

```python
class Test{Entity}(AbstractPostgresTest):
    BASE_PATH = "/api/v1/{entity}"

    @classmethod
    def setup_class(cls):
        super().setup_class()
        from open_webui.models.{entity} import {Entity}Model
        cls.entity_model = {Entity}Model
        # Store model reference for direct database access

    def test_operation(self):
        # Setup: Create test data (if needed)
        # Execute: Call API endpoint
        # Assert: Verify response and database state
```

### Authentication Pattern
All tests use `mock_webui_user()` context manager:

```python
def test_admin_operation(self):
    with mock_webui_user(role="admin"):
        response = self.fast_api_client.post(...)
    # Endpoint receives admin user

def test_user_operation(self):
    with mock_webui_user(id="user1", role="user"):
        response = self.fast_api_client.get(...)
    # Endpoint receives regular user
```

### Assertion Pattern
Tests validate both API response and database state:

```python
def test_update_user(self):
    # Create test data
    user = self.auths.insert_new_auth(...)

    # Execute API call
    with mock_webui_user(id=user.id):
        response = self.fast_api_client.post(
            self.create_url(f"/{user.id}/update"),
            json={"name": "New Name"}
        )

    # Assert response
    assert response.status_code == 200

    # Assert database state
    db_user = self.users.get_user_by_id(user.id)
    assert db_user.name == "New Name"
```

### URL Building Pattern
Tests use `create_url()` from `AbstractIntegrationTest`:

```python
BASE_PATH = "/api/v1/chats"

self.create_url("")                    # → /api/v1/chats
self.create_url("/123")                # → /api/v1/chats/123
self.create_url("/123/share")          # → /api/v1/chats/123/share
self.create_url("/", {"page": 1})      # → /api/v1/chats?page=1
```

### Test Data Setup Pattern
Tests create minimal data directly via models:

```python
def test_something(self):
    # Direct model access (bypasses API)
    user = self.auths.insert_new_auth(
        email="test@example.com",
        password=get_password_hash("password"),
        name="Test User",
    )

    # Now test API with this user
    with mock_webui_user(id=user.id):
        response = self.fast_api_client.post(...)
```

## Integration Points

### test/apps/webui/routers/ → routers/
**Primary Integration:** Each test file validates corresponding router.

**Mapping:**
- `test_auths.py` → `routers/auths.py`
- `test_chats.py` → `routers/chats.py`
- `test_users.py` → `routers/users.py`
- `test_models.py` → `routers/models.py`
- `test_prompts.py` → `routers/prompts.py`

**Example:**
```python
# In test_chats.py
response = self.fast_api_client.post("/api/v1/chats/new", json={...})

# Calls routers/chats.py
@router.post("/new")
async def create_new_chat(form_data: ChatForm, user=Depends(get_current_user)):
    # Executes with mocked user
```

### test/apps/webui/routers/ → models/
**Database Validation:** Tests access models directly for assertion.

```python
# In test_users.py
response = self.fast_api_client.post("/api/v1/users/123/update", ...)

# Verify database state
db_user = self.users.get_user_by_id("123")
assert db_user.name == "Updated Name"
# Uses models/users.py directly
```

### test/apps/webui/routers/ → test/util/
**Test Infrastructure:** All tests inherit from `AbstractPostgresTest`.

```python
# In test_auths.py
class TestAuths(AbstractPostgresTest):
    # Inherits:
    # - PostgreSQL Docker container
    # - FastAPI TestClient
    # - Table truncation
    # - URL building
```

**Authentication Mocking:**
```python
from test.util.mock_user import mock_webui_user

with mock_webui_user(role="admin"):
    response = self.fast_api_client.get(...)
# Bypasses JWT validation
```

### test/apps/webui/routers/ → utils/
**Utilities:** Tests import shared utilities for operations.

```python
# In test_auths.py
from open_webui.utils.auth import get_password_hash

password_hash = get_password_hash("plaintext_password")
user = self.auths.insert_new_auth(password=password_hash, ...)
```

## Key Workflows

### Authentication Test Workflow
```
test_update_password()
  ↓
Setup:
  1. Create user with old password hash
  2. Store user in database
  ↓
Execute:
  1. Mock authentication with user ID
  2. POST /api/v1/auths/update/password
     JSON: {"password": "old_pass", "new_password": "new_pass"}
  3. routers/auths.py validates old password
  4. Updates password hash in database
  ↓
Assert:
  1. Response status == 200
  2. Query user from database
  3. Verify new password hash != old hash
  4. Verify new hash validates with new password
```

### Chat CRUD Test Workflow
```
test_create_chat()
  ↓
Setup:
  1. Mock user authentication
  ↓
Execute:
  1. POST /api/v1/chats/new
     JSON: {
       "chat": {
         "title": "New Chat",
         "messages": [...]
       }
     }
  2. routers/chats.py creates chat in database
  3. Returns chat object with ID
  ↓
Assert:
  1. Response status == 200
  2. Response JSON contains chat.id
  3. Query chat from database
  4. Verify title, messages, user_id match
```

### Admin Operation Test Workflow
```
test_update_user_role()
  ↓
Setup:
  1. Create regular user in database
  ↓
Execute:
  1. Mock authentication with admin role
  2. POST /api/v1/users/{user_id}/update
     JSON: {"role": "admin"}
  3. routers/users.py checks requester is admin
  4. Updates user role in database
  ↓
Assert:
  1. Response status == 200
  2. Query user from database
  3. Verify user.role == "admin"
  ↓
Negative test:
  1. Mock authentication with user role (not admin)
  2. POST same endpoint
  3. Assert response status == 403 (Forbidden)
```

### Sharing Test Workflow
```
test_share_chat()
  ↓
Setup:
  1. Create chat owned by user
  2. Store in database
  ↓
Execute:
  1. Mock authentication with owner user
  2. POST /api/v1/chats/{chat_id}/share
  3. routers/chats.py generates UUID share_id
  4. Updates chat.share_id in database
  5. Returns share link
  ↓
Assert:
  1. Response status == 200
  2. Response JSON contains share_id (UUID format)
  3. Query chat from database
  4. Verify chat.share_id matches response
  5. Verify share link format: /s/{share_id}
```

## Important Notes

### Critical Dependencies
- **pytest**: Test framework and assertions
- **FastAPI TestClient**: HTTP client for endpoint testing
- **AbstractPostgresTest**: Database-backed test infrastructure
- **mock_webui_user**: Authentication bypass utility
- **SQLAlchemy**: Database queries for validation

### Test Isolation
**Between Test Methods:**
- `teardown_method()` truncates all tables
- Each test starts with clean database
- No test data leakage

**Within Test Methods:**
- Unique identifiers (user IDs, chat IDs)
- No shared state between assertions
- Independent API calls

### Performance Considerations
- **Database overhead:** Each test truncates 9 tables (~50ms)
- **API latency:** TestClient adds minimal overhead (<1ms)
- **Container shared:** All tests in class use same PostgreSQL container
- **Sequential execution:** Tests run serially within class

**Optimization:**
- Group related tests in same file (share setup_class)
- Minimize test data creation
- Use simple assertions (avoid complex queries)

### Common Patterns

**Creating Test Data:**
```python
# Direct model access (fast)
user = self.auths.insert_new_auth(...)
chat = self.chats.insert_new_chat(...)

# Not via API (slower, unnecessary)
```

**Testing Admin Operations:**
```python
# Admin should succeed
with mock_webui_user(role="admin"):
    response = self.fast_api_client.post(...)
    assert response.status_code == 200

# User should fail
with mock_webui_user(role="user"):
    response = self.fast_api_client.post(...)
    assert response.status_code == 403
```

**Testing Ownership:**
```python
# Owner should access
with mock_webui_user(id=chat.user_id):
    response = self.fast_api_client.get(f"/api/v1/chats/{chat.id}")
    assert response.status_code == 200

# Non-owner should not access
with mock_webui_user(id="other_user"):
    response = self.fast_api_client.get(f"/api/v1/chats/{chat.id}")
    assert response.status_code == 404  # Or 403
```

### Troubleshooting

**Test Fails with 401 Unauthorized:**
- Missing `mock_webui_user()` context manager
- Context manager exited before API call
- Check app.dependency_overrides not cleared

**Test Fails with 404 Not Found:**
- URL path incorrect (check `create_url()` usage)
- BASE_PATH not set correctly
- Resource ID mismatch

**Database State Assertion Fails:**
- Query executed before API call completes
- Database session not committed
- Check model method returns correct object

**Tests Pass Individually, Fail Together:**
- Table truncation not working (check teardown_method)
- Shared state in class attributes
- Database connection not reset

### Coverage Gaps
**Currently Tested:**
- ✅ Basic CRUD operations
- ✅ Authentication flows
- ✅ Admin permission checks
- ✅ Profile updates
- ✅ Chat sharing

**Not Tested:**
- ❌ File upload endpoints (multipart/form-data)
- ❌ WebSocket events
- ❌ Rate limiting
- ❌ Token expiration
- ❌ Concurrent operations
- ❌ Large payload handling
- ❌ Invalid input edge cases

### Future Improvements
Potential enhancements:
- **Parameterized tests**: Test same operation with multiple inputs
- **Fixture factories**: Reusable test data generators
- **Negative test cases**: More invalid input testing
- **Concurrent operations**: Test race conditions
- **Performance benchmarks**: Track endpoint response times
- **Snapshot testing**: Compare full API responses
- **WebSocket testing**: Socket.IO event validation
- **File upload testing**: Multipart form data handling
- **Integration scenarios**: Multi-step workflows (signup → chat → share)
