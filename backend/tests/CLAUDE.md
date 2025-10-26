# Backend Tests Directory

This directory contains pytest-based test suites for Open WebUI's backend, covering API endpoints, database models, authentication, RAG pipeline, vector database operations, and integration scenarios. Tests use fixtures, mocking, and test databases to ensure comprehensive coverage without affecting production data.

## Directory Structure

### conftest.py
Central pytest configuration and shared fixtures.

**Key Fixtures:**
- `client` - FastAPI TestClient for API endpoint testing
- `db` - Test database session with automatic rollback
- `test_user` - Authenticated user with JWT token
- `admin_user` - Admin user with elevated permissions
- `mock_llm_response` - Mocked LLM API responses
- `mock_vector_db` - Mocked vector database client
- `temp_file` - Temporary file for upload testing

**Used by:**
- All test files via pytest's fixture discovery

**Setup/Teardown:**
```python
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Create test database schema
    # Run migrations
    yield
    # Drop test database
```

### test_auth.py
Authentication and authorization endpoint tests.

**Test Coverage:**
- User signup with email/password
- User signin with valid credentials
- Signin with invalid credentials (401 error)
- JWT token generation and validation
- Token expiration handling
- Password hashing and verification
- API key generation and deletion
- Session user retrieval
- Password update with old password verification
- Admin-only endpoint access control

**Key Tests:**
- `test_signup_new_user()` - POST /api/auths/signup
- `test_signin_valid_credentials()` - POST /api/auths/signin
- `test_signin_invalid_password()` - 401 error handling
- `test_get_session_user()` - GET /api/auths/
- `test_generate_api_key()` - POST /api/auths/api_key
- `test_admin_only_endpoint()` - Permission checks

**Uses:**
- `conftest.py` - client, test_user fixtures
- `models/users.py` - User model for assertions
- `utils/auth.py` - verify_password(), decode_token()

### test_chats.py
Chat CRUD and management endpoint tests.

**Test Coverage:**
- Create new chat
- Get chat by ID
- Update chat (title, messages, metadata)
- Delete chat
- List user's chats with pagination
- Search chats by name/content
- Archive/unarchive chat
- Pin/unpin chat
- Share chat (generate share link)
- Delete shared chat
- Get chat by share ID
- Add/remove tags
- Clone chat

**Key Tests:**
- `test_create_chat()` - POST /api/chats/new
- `test_get_chat_by_id()` - GET /api/chats/{id}
- `test_update_chat_title()` - POST /api/chats/{id}
- `test_delete_chat()` - DELETE /api/chats/{id}
- `test_search_chats()` - GET /api/chats/search
- `test_share_chat()` - POST /api/chats/{id}/share
- `test_tag_management()` - POST/DELETE /api/chats/{id}/tags

**Uses:**
- `conftest.py` - client, test_user fixtures
- `models/chats.py` - Chats model for assertions
- `routers/chats.py` - Endpoint implementations

### test_models.py (Model Management)
Model CRUD endpoint tests.

**Test Coverage:**
- List available models
- Get model by ID
- Create custom model
- Update model configuration
- Delete model
- Toggle model enable/disable
- Get/update model valves (configuration)
- Access control for model visibility
- Model metadata validation

**Key Tests:**
- `test_get_models()` - GET /api/models
- `test_create_custom_model()` - POST /api/models/create
- `test_toggle_model()` - POST /api/models/id/{id}/toggle
- `test_update_model_valves()` - POST /api/models/{id}/valves/update
- `test_model_access_control()` - Permission filtering

**Uses:**
- `conftest.py` - client, test_user, admin_user fixtures
- `models/models.py` - Models model

### test_files.py
File upload, processing, and retrieval tests.

**Test Coverage:**
- File upload (multipart/form-data)
- File download by ID
- File metadata retrieval
- File deletion with vector DB cleanup
- File processing pipeline
- Supported file type validation
- File size limit enforcement
- Access control for private files

**Key Tests:**
- `test_upload_file()` - POST /api/files
- `test_get_file_by_id()` - GET /api/files/{id}
- `test_download_file()` - GET /api/files/{id}/content
- `test_delete_file()` - DELETE /api/files/{id}
- `test_file_size_limit()` - 413 error for large files
- `test_unsupported_file_type()` - Extension validation

**Uses:**
- `conftest.py` - client, test_user, temp_file fixtures
- `models/files.py` - Files model
- `storage/provider.py` - Storage operations (mocked)

### test_retrieval.py
RAG pipeline and vector search tests.

**Test Coverage:**
- Document processing and chunking
- Embedding generation
- Vector database insertion
- Semantic search queries
- Hybrid search (BM25 + vector)
- Collection management
- Reranking pipeline
- Web search integration
- RAG configuration updates

**Key Tests:**
- `test_process_file()` - POST /api/retrieval/process/file
- `test_query_doc()` - POST /api/retrieval/query/doc
- `test_query_collection()` - POST /api/retrieval/query/collection
- `test_hybrid_search()` - BM25 + vector ensemble
- `test_web_search()` - POST /api/retrieval/web/search
- `test_embedding_generation()` - Different embedding engines
- `test_vector_db_operations()` - Insert, search, delete

**Uses:**
- `conftest.py` - client, test_user, mock_vector_db fixtures
- `retrieval/loaders/main.py` - Loader (mocked)
- `retrieval/vector/factory.py` - VECTOR_DB_CLIENT (mocked)
- `retrieval/utils.py` - query_doc(), get_embedding_function()

**Mocking Strategy:**
```python
@pytest.fixture
def mock_vector_db(monkeypatch):
    mock = MagicMock()
    mock.search.return_value = [SearchResult(...)]
    monkeypatch.setattr('retrieval.vector.factory.VECTOR_DB_CLIENT', mock)
    return mock
```

### test_knowledge.py
Knowledge base management tests.

**Test Coverage:**
- Create knowledge base
- List knowledge bases
- Get knowledge base by ID
- Update knowledge base metadata
- Delete knowledge base
- Add file to knowledge base
- Remove file from knowledge base
- Reindex knowledge files
- Access control for knowledge bases

**Key Tests:**
- `test_create_knowledge()` - POST /api/knowledge
- `test_get_knowledge_bases()` - GET /api/knowledge
- `test_add_file_to_knowledge()` - POST /api/knowledge/{id}/file/add
- `test_remove_file()` - POST /api/knowledge/{id}/file/remove
- `test_reindex_knowledge()` - POST /api/knowledge/{id}/reindex
- `test_knowledge_access_control()` - Permission checks

**Uses:**
- `conftest.py` - client, test_user fixtures
- `models/knowledge.py` - Knowledge model
- `routers/retrieval.py` - process_file() for reindexing

### test_tools.py
Tool and function management tests.

**Test Coverage:**
- List tools
- Create new tool
- Update tool code
- Delete tool
- Get/update tool valves (global config)
- Get/update user valves (per-user overrides)
- Tool execution with parameters
- Tool validation and sandboxing

**Key Tests:**
- `test_get_tools()` - GET /api/tools
- `test_create_tool()` - POST /api/tools/create
- `test_update_tool()` - POST /api/tools/{id}/update
- `test_execute_tool()` - Tool invocation
- `test_valve_management()` - Config updates
- `test_user_valve_override()` - Per-user settings

**Uses:**
- `conftest.py` - client, test_user fixtures
- `models/tools.py` - Tools model
- `utils/plugin.py` - load_tool_module_by_id()

### test_users.py
User management endpoint tests.

**Test Coverage:**
- List users (admin only)
- Get user by ID
- Update user profile
- Update user role (admin only)
- Delete user
- User settings CRUD
- Permission management
- User search and filtering

**Key Tests:**
- `test_get_users()` - GET /api/users
- `test_update_user()` - POST /api/users/{id}/update
- `test_delete_user()` - DELETE /api/users/{id}
- `test_update_user_settings()` - POST /api/users/user/settings/update
- `test_admin_cannot_delete_self()` - Primary admin protection
- `test_user_permissions()` - Permission checks

**Uses:**
- `conftest.py` - client, test_user, admin_user fixtures
- `models/users.py` - Users model

### test_socket.py
WebSocket communication tests.

**Test Coverage:**
- Socket connection with JWT auth
- Session management (SESSION_POOL, USER_POOL)
- Chat event emission
- Collaborative editing (Yjs) events
- Channel event broadcasting
- Token usage tracking
- Disconnect cleanup

**Key Tests:**
- `test_socket_connect()` - Connection with valid token
- `test_socket_auth_failure()` - Invalid token rejection
- `test_chat_event_emission()` - Real-time message updates
- `test_ydoc_collaboration()` - Document editing sync
- `test_channel_broadcast()` - Channel message delivery
- `test_usage_tracking()` - Token usage updates

**Uses:**
- `socketio.AsyncClient` - Test client for WebSocket
- `conftest.py` - test_user fixture for token
- `socket/main.py` - Socket handlers

**Pattern:**
```python
async def test_socket_connect():
    sio = socketio.AsyncClient()
    await sio.connect('http://localhost:8000/ws', auth={'token': token})
    assert sio.connected
    await sio.disconnect()
```

### test_integration.py
End-to-end integration tests covering full workflows.

**Test Scenarios:**
- **Complete Chat Workflow:**
  - User signup → signin → create chat → send message → receive completion
- **File Upload + RAG Workflow:**
  - Upload file → process file → query doc → chat with context
- **Knowledge Base Workflow:**
  - Create KB → add files → query collection → chat with KB
- **Admin Configuration Workflow:**
  - Admin update config → user sees changes → features enabled/disabled
- **Share Chat Workflow:**
  - User creates chat → shares chat → public access → view shared chat

**Key Tests:**
- `test_full_chat_workflow()` - Signup to completion
- `test_rag_pipeline()` - Upload to retrieval
- `test_knowledge_base_integration()` - KB creation to usage
- `test_admin_config_propagation()` - Config updates
- `test_chat_sharing()` - Share link generation to access

**Uses:**
- All API modules
- All models
- Socket client for real-time tests
- Temporary files and databases

## Architecture & Patterns

### Fixture-Based Testing
```python
# conftest.py
@pytest.fixture
def test_user(client):
    response = client.post('/api/auths/signup', json={
        'email': 'test@example.com',
        'password': 'password123',
        'name': 'Test User'
    })
    return response.json()

# test_chats.py
def test_create_chat(client, test_user):
    response = client.post('/api/chats/new',
        headers={'Authorization': f"Bearer {test_user['token']}"},
        json={'messages': [...]})
    assert response.status_code == 200
```

### Database Isolation Pattern
```python
@pytest.fixture(scope="function")
def db():
    # Create fresh database for each test
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    yield db

    db.close()
    Base.metadata.drop_all(engine)
```

### Mocking External Services
```python
@pytest.fixture
def mock_openai(monkeypatch):
    async def mock_completion(*args, **kwargs):
        return {
            'choices': [{'message': {'content': 'Mocked response'}}]
        }

    monkeypatch.setattr(
        'routers.openai.generateCompletion',
        mock_completion
    )
```

### Parametrized Testing
```python
@pytest.mark.parametrize("file_type,expected_status", [
    ("application/pdf", 200),
    ("image/png", 200),
    ("text/plain", 200),
    ("application/exe", 400),  # Unsupported
])
def test_file_upload_types(client, test_user, file_type, expected_status):
    # Test multiple file types in one test
    pass
```

## Integration Points

### Tests → API Routers
Tests call endpoints via FastAPI TestClient:
```python
response = client.post('/api/chats/new', json=payload)
```

Equivalent to HTTP request but in-process (no network).

### Tests → Database Models
Tests verify database state via ORM:
```python
def test_chat_creation(client, test_user, db):
    client.post('/api/chats/new', ...)

    # Verify database state
    chat = db.query(Chat).filter_by(user_id=test_user['id']).first()
    assert chat is not None
    assert chat.title == 'New Chat'
```

### Tests → Vector DB (Mocked)
RAG tests mock vector database operations:
```python
mock_vector_db.search.return_value = [
    SearchResult(id='1', distance=0.8, document='...'),
]

response = client.post('/api/retrieval/query/doc', json={...})
assert response.json()['results'][0]['document'] == '...'
```

### Tests → WebSocket
Socket tests use async client:
```python
async def test_chat_events():
    sio = socketio.AsyncClient()
    await sio.connect(SERVER_URL, auth={'token': token})

    events = []
    @sio.on('chat-events')
    def handler(data):
        events.append(data)

    # Trigger event
    await client.post('/api/chats/new', ...)

    await asyncio.sleep(0.1)  # Wait for event
    assert len(events) > 0
```

## Key Workflows

### Test Execution Flow
```
pytest discovers tests/
  ↓
conftest.py fixtures load
  ↓
Test database created
  ↓
Test functions execute
  ↓
Assertions verify behavior
  ↓
Database rolled back
  ↓
Teardown cleans up
```

### API Endpoint Test Pattern
```
1. Create test user (fixture)
2. Get authentication token
3. Make API request with token
4. Verify HTTP status code
5. Verify response JSON structure
6. Verify database state (if applicable)
7. Clean up (automatic via fixture teardown)
```

### RAG Pipeline Test Pattern
```
1. Mock vector database
2. Mock embedding function
3. Upload test file
4. Process file (chunking + embedding)
5. Verify vector DB insert called
6. Query document with test query
7. Verify search results
8. Check response contains expected content
```

### Integration Test Pattern
```
1. Setup: Create user, upload files, configure system
2. Execute: Perform complete workflow
3. Verify: Check all steps succeeded and state is correct
4. Teardown: Clean up all created resources
```

## Important Notes

### Critical Dependencies
- pytest 7.x+ for async test support
- FastAPI TestClient for endpoint testing
- pytest-asyncio for WebSocket tests
- SQLite in-memory database for fast tests
- Mocking libraries: unittest.mock, pytest-mock

### Test Database Configuration
- Uses separate `TEST_DATABASE_URL` (typically SQLite in-memory)
- Migrations run before test suite
- Each test function gets isolated database (rollback after)
- No test pollution between tests

### Mocking Strategy
- External APIs (OpenAI, Ollama) always mocked
- Vector databases mocked for unit tests, real for integration tests
- File storage mocked with temporary directories
- WebSocket server runs in-process for testing

### Performance Considerations
- Parallel test execution via `pytest -n auto` (pytest-xdist)
- Database isolation slows tests; use session scope for read-only fixtures
- Mocking external services critical for fast tests
- Integration tests slower; separate with markers: `@pytest.mark.integration`

### Coverage Tracking
- Run with `pytest --cov=open_webui --cov-report=html`
- Target: >80% coverage for critical paths
- Exclude: migrations, generated code, third-party integrations

### Running Tests
```bash
# All tests
pytest backend/tests/

# Specific test file
pytest backend/tests/test_chats.py

# Specific test function
pytest backend/tests/test_chats.py::test_create_chat

# With coverage
pytest --cov=open_webui --cov-report=html

# Parallel execution
pytest -n auto

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### CI/CD Integration
- Tests run on every commit (GitHub Actions)
- Separate jobs for unit tests and integration tests
- Code coverage reports uploaded to Codecov
- Tests must pass before merge

### Debugging Failed Tests
- Use `pytest -v` for verbose output
- Use `pytest -s` to see print statements
- Use `pytest --pdb` to drop into debugger on failure
- Check test logs in `pytest_log.txt`

### Security Testing
- Tests verify authentication required for protected endpoints
- Tests check authorization (admin-only endpoints)
- Tests validate input sanitization (XSS, SQL injection prevention)
- Tests ensure file upload restrictions enforced
