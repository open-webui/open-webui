# ✅ STORYWEAVER : TEST CHECKLIST

**Format:** Chaque Milestone a sa checklist  
**Niveau:** Unit Tests + Integration Tests + Manual Tests  
**Exécution:** ✓ OK, ✗ FAIL, ⊘ SKIP (expliquer pourquoi)

---

# PHASE 1 : CORE INFRASTRUCTURE

## MILESTONE 1.0 : Setup & Fork Initial

### Task 1.0.1 : Fork OpenWebUI et Setup Git

#### Unit Tests
```
[ ] Git repo exists locally
[ ] Git remote origin points to fork
[ ] .gitignore includes *.pyc, __pycache__, node_modules, .env
[ ] feature/storyweaver-core branch exists
[ ] Branch is checked out (git branch shows *)
```

#### Manual Tests
```
[ ] Can do: git log (shows OpenWebUI commits)
[ ] Can do: git remote -v (shows fork URL)
[ ] Can do: git status (clean working tree)
[ ] DEVELOPMENT.md file exists in repo root
```

#### Test Data
```
Repo URL: https://github.com/YOUR_USERNAME/open-webui.git
Branch: feature/storyweaver-core
Initial commit count: >100 (from OpenWebUI)
```

**Acceptance Criteria:** 
- ✓ Repo fully cloned, branched, ready for development
- ✓ No uncommitted changes
- ✓ Git history intact

---

### Task 1.0.2 : Setup Environnement Dev Local

#### Unit Tests (Backend)
```
[ ] Python version >= 3.10
[ ] poetry --version works (returns version)
[ ] poetry show poetry returns Python 3.10+
[ ] cd backend && poetry install succeeds
[ ] Can import fastapi, sqlalchemy, pydantic
[ ] poetry run python --version shows 3.10+
```

#### Unit Tests (Frontend)
```
[ ] Node.js version >= 18
[ ] npm --version works
[ ] cd frontend && npm install succeeds (no errors)
[ ] Can import svelte, vite
```

#### Integration Tests
```
# Backend
[ ] poetry run python main.py starts without error
[ ] Server listens on http://localhost:8000
[ ] curl http://localhost:8000/api/models returns JSON
[ ] curl http://localhost:8000/health returns 200 OK

# Frontend
[ ] npm run dev starts dev server
[ ] Server listens on http://localhost:5173
[ ] http://localhost:5173 in browser loads OpenWebUI
[ ] No console errors in browser dev tools
[ ] Can interact with chat UI (type message, send)
```

#### Manual Tests
```
[ ] Backend dependencies in poetry.lock (no conflicts)
[ ] Frontend node_modules folder exists and is reasonable size
[ ] .env.local contains valid test values
[ ] Both servers can run simultaneously in separate terminals
[ ] Can kill servers with Ctrl+C cleanly
```

#### Test Data
```
Backend test:
  POST http://localhost:8000/api/models
  Expected response:
  {
    "data": [
      { "name": "mistral", ... }
    ]
  }

Frontend test:
  GET http://localhost:5173/
  Expected: HTML with "OpenWebUI" in page title
```

**Acceptance Criteria:**
- ✓ Both backend and frontend launch successfully
- ✓ Can make API request from browser
- ✓ No dependency conflicts
- ✓ Environment documented in DEVELOPMENT.md

---

### Task 1.0.3 : Analyser Structure OpenWebUI Existante

#### Documentation Tests
```
[ ] ARCHITECTURE_EXISTING.md file created
[ ] File includes section: "Backend Routes"
[ ] File includes section: "Frontend Components"
[ ] File includes section: "Database Schema"
[ ] File includes at least 3 ASCII diagrams
[ ] File is readable and organized
```

#### Content Tests
```
[ ] Identifies all routes starting with /api/
[ ] Lists main Frontend components (Chat, Settings, etc.)
[ ] Documents SQLAlchemy models (User, Chat, Message, etc.)
[ ] Explains authentication mechanism
[ ] Documents how tools/functions are registered
[ ] Shows where middleware is applied
```

#### Manual Tests
```
[ ] Can locate routes/chat.py in backend
[ ] Can locate chat UI component in frontend
[ ] Can trace a message from frontend input to LLM call
[ ] Can identify where models are stored/loaded
[ ] Can find database initialization code
[ ] Can locate user authentication logic
```

#### Test Artifacts
```
// Sample OpenWebUI Chat Route
GET /api/chat/messages?chat_id={id}
  ↓
backend/routes/chat.py:list_chat_messages()
  ↓
SQLAlchemy query: Message.query.filter(Message.chat_id == id)
  ↓
Returns: {"messages": [...]}

// Should document similar patterns for at least 5 routes
```

**Acceptance Criteria:**
- ✓ Can explain how OpenWebUI chat works end-to-end
- ✓ Documentation includes code locations
- ✓ Architecture understood well enough to extend

---

## MILESTONE 1.1 : Database Extensions

### Task 1.1.1 : Créer Models Pydantic (Backend)

#### Unit Tests
```
[ ] File backend/database/models_storyweaver.py exists
[ ] All models import without errors:
    - Novel
    - KnowledgeBase
    - Manuscript
    - Conversation
    - Version
[ ] All models are SQLAlchemy Base subclasses
[ ] Each model has id (PK), created_at, updated_at fields
```

#### Tests for Novel Model
```
[ ] Novel has columns: id, user_id, title, description, status
[ ] Novel.status defaults to "draft"
[ ] Novel has relationships:
    - knowledge_base (1:1)
    - manuscript (1:1)
    - conversations (1:N)
    - versions (1:N)
[ ] Can create: novel = Novel(user_id="user1", title="Test")
[ ] Can convert to dict: novel.dict()
```

#### Tests for KnowledgeBase Model
```
[ ] KnowledgeBase has columns:
    - id, novel_id, universe_docs, characters, locations, objects
[ ] universe_docs column type is JSON
[ ] characters, locations, objects are JSON arrays
[ ] Relationship to Novel works: kb.novel
```

#### Tests for Manuscript Model
```
[ ] Manuscript has: id, novel_id, content, chapter_structure, word_count
[ ] content is Text (not limited)
[ ] chapter_structure is JSON
[ ] word_count defaults to 0
```

#### Tests for Version Model
```
[ ] Version has: id, novel_id, entity_type, entity_id, old_data, new_data,
                 change_type, version_number, timestamp
[ ] version_number is Integer
[ ] timestamp defaults to datetime.utcnow
[ ] change_type is one of: created, updated, deleted, reverted
[ ] old_data and new_data are JSON (allow null for old_data on create)
```

#### Tests for Conversation Model
```
[ ] Conversation has: id, chat_id, novel_id, tags, context_level, linked_entities
[ ] tags is JSON array of strings
[ ] context_level is one of: full, minimal, none
[ ] linked_entities is JSON dict
```

#### Pydantic Schema Tests
```
[ ] Can create NovelCreate schema with title, description
[ ] Can create NovelResponse with all fields + relationships
[ ] Can create CharacterInput with required fields
[ ] ValidationError raised if required field missing
[ ] ValidationError raised if status not in enum
```

#### Integration Tests
```
from backend.database.models_storyweaver import *

[ ] Can instantiate all models:
    novel = Novel(user_id="1", title="Test", status="draft")
    kb = KnowledgeBase(novel_id=novel.id, universe_docs={})
    manuscript = Manuscript(novel_id=novel.id, content="", chapter_structure={})
    version = Version(novel_id=novel.id, entity_type="character", ...)
    
[ ] All models are valid SQLAlchemy declarative base instances
[ ] Relationships are defined correctly
```

**Acceptance Criteria:**
- ✓ All 5 models fully defined
- ✓ All relationships correctly mapped
- ✓ Models import without errors
- ✓ Pydantic schemas work for API requests/responses

---

### Task 1.1.2 : Créer Migration DB (Alembic)

#### Pre-Migration Tests
```
[ ] poetry run alembic current shows latest migration
[ ] poetry run alembic history shows all previous migrations
[ ] No uncommitted alembic script files
```

#### Migration Generation Tests
```
[ ] poetry run alembic revision --autogenerate -m "Add novel tables"
    succeeds without error
[ ] New file created in alembic/versions/
[ ] File named with pattern: *_add_novel_tables.py
[ ] File contains create_table() ops for:
    - novels
    - knowledge_bases
    - manuscripts
    - versions
    - conversations
```

#### Migration Content Tests (inspect generated file)
```
[ ] Each table creation includes:
    - Column definitions (name, type, nullable, default)
    - Primary key constraint
    - Foreign key constraints
    - Index definitions (added manually for PK fields)

Specifically check:
  • op.create_table('novels', ...)
    ├─ sa.Column('id', ...)
    ├─ sa.Column('user_id', ...)
    ├─ sa.Column('title', ...)
    ├─ sa.Column('status', ...)
    ├─ sa.ForeignKeyConstraint(['user_id'], ['user.id'])
    └─ sa.PrimaryKeyConstraint('id')

  • op.create_index('idx_novels_user_id', 'novels', ['user_id'])
  • op.create_index('idx_versions_entity_id', 'versions', ['entity_id'])
  (at least 4 indexes created)

[ ] Foreign key constraints properly defined:
    - knowledge_bases.novel_id → novels.id
    - manuscripts.novel_id → novels.id
    - versions.novel_id → novels.id
    - conversations.novel_id → novels.id
    - conversations.chat_id → chat.id (existing OpenWebUI)
```

#### Upgrade Tests
```
[ ] poetry run alembic upgrade head succeeds
    (or alembic upgrade +1 for just this migration)
[ ] Command output shows: "Running upgrade ..."
[ ] No errors or warnings in output
[ ] No SQL errors
```

#### Database Verification Tests
```
# After upgrade, verify in DB:
SQLite: sqlite3 db.sqlite3
  > .tables
  Should show: novels, knowledge_bases, manuscripts, versions, conversations

PostgreSQL: psql -d storyweaver_db
  > \dt
  Should list all new tables

[ ] Each table exists and has correct columns:
    SELECT * FROM novels LIMIT 0;  -- returns empty result
    SELECT * FROM knowledge_bases LIMIT 0;
    SELECT * FROM manuscripts LIMIT 0;
    SELECT * FROM versions LIMIT 0;
    SELECT * FROM conversations LIMIT 0;

[ ] Indexes are created:
    PostgreSQL: \di (list indexes)
    SQLite: PRAGMA index_list(table_name);
    
    Should show: idx_novels_user_id, idx_versions_entity_id, etc.
```

#### Downgrade Tests
```
[ ] poetry run alembic downgrade -1 succeeds
[ ] Tables are deleted:
    SELECT * FROM novels;  -- returns ERROR: table doesn't exist (expected)

[ ] poetry run alembic upgrade head succeeds again
[ ] Tables are recreated
[ ] Both upgrade and downgrade are idempotent
```

#### Test Data Insertion
```
[ ] After upgrade, can insert test data:
    INSERT INTO novels (id, user_id, title, status)
    VALUES ('uuid-1', 'user-1', 'Test Novel', 'draft');
    
    INSERT INTO knowledge_bases (id, novel_id, universe_docs, characters, locations, objects)
    VALUES ('kb-1', 'uuid-1', '{}', '[]', '[]', '[]');

[ ] Data persists across SELECT queries
[ ] Foreign key constraints enforced:
    INSERT into versions (novel_id, ...) 
    VALUES ('nonexistent-id', ...)
    -- Should fail with FK constraint error
```

**Acceptance Criteria:**
- ✓ Migration generated and contains all 5 new tables
- ✓ Upgrade succeeds with no errors
- ✓ Database schema matches expected (inspect with SQL)
- ✓ Downgrade works (idempotent)
- ✓ Can insert and retrieve test data
- ✓ Foreign key constraints enforced

---

### Task 1.1.3 : Ajouter DAOs (Data Access Objects)

#### Unit Tests for NovelDAO

```
@pytest.fixture
def db_session():
    # Return SQLite in-memory test DB session
    ...

def test_novel_create(db_session):
    [ ] NovelDAO.create(db_session, "user1", "My Novel")
        returns Novel instance
    [ ] novel.id is UUID
    [ ] novel.user_id == "user1"
    [ ] novel.title == "My Novel"
    [ ] novel.status == "draft"
    [ ] novel.created_at is not None

def test_novel_list(db_session):
    [ ] Create 3 novels for user1, 2 for user2
    [ ] NovelDAO.list_by_user(db_session, "user1") returns 3 items
    [ ] NovelDAO.list_by_user(db_session, "user2") returns 2 items
    [ ] NovelDAO.list_by_user(db_session, "user3") returns []

def test_novel_get_by_id(db_session):
    [ ] Create novel, get ID
    [ ] NovelDAO.get_by_id(db_session, id) returns that novel
    [ ] NovelDAO.get_by_id(db_session, "wrong-id") returns None

def test_novel_update(db_session):
    [ ] Create novel
    [ ] NovelDAO.update(db_session, id, title="Updated")
    [ ] Novel.title is now "Updated"
    [ ] Novel.updated_at changed
    [ ] Can update multiple fields at once

def test_novel_delete(db_session):
    [ ] Create novel
    [ ] NovelDAO.delete(db_session, id)
    [ ] NovelDAO.get_by_id(db_session, id) returns None
```

#### Unit Tests for KnowledgeBaseDAO

```
def test_kb_get_by_novel(db_session):
    [ ] Create novel + KB
    [ ] KnowledgeBaseDAO.get_by_novel_id(novel_id) returns KB
    [ ] KB.universe_docs is dict
    [ ] KB.characters is list (initially [])

def test_kb_update_universe(db_session):
    [ ] Create KB
    [ ] KnowledgeBaseDAO.update_universe(id, {"magic": "..."})
    [ ] KB.universe_docs contains new data

def test_kb_add_character(db_session):
    [ ] Create KB
    [ ] KnowledgeBaseDAO.add_character(id, character_dict)
    [ ] character_dict in kb.characters
    [ ] Can query: KnowledgeBaseDAO.get_character(id, char_id)
```

#### Unit Tests for VersionDAO

```
def test_version_create(db_session):
    [ ] VersionDAO.create(db_session, novel_id, "character", "char_1",
                          {"old": "data"}, {"new": "data"}, "updated")
        returns Version
    [ ] version.version_number == 1
    [ ] version.change_type == "updated"

def test_version_numbering(db_session):
    [ ] Create 3 versions for same entity_id
    [ ] version_number increments: 1, 2, 3
    [ ] version_number is auto-calculated, not provided

def test_version_history(db_session):
    [ ] Create 5 versions for entity_id
    [ ] VersionDAO.get_history(db_session, entity_id)
        returns list of 5, ordered by version_number DESC
    [ ] VersionDAO.get_history(..., limit=2) returns only 2 most recent
```

#### Integration Tests (DAO interactions)

```
def test_create_novel_with_kb(db_session):
    [ ] Create novel
    [ ] Verify KB automatically created (1:1 relationship)
    [ ] Can call novel.knowledge_base to access KB

def test_version_on_novel_update(db_session):
    [ ] Create novel
    [ ] Update novel title
    [ ] VersionDAO.get_history("novel", novel_id) returns 1 version
    [ ] version.old_data = original title
    [ ] version.new_data = updated title
```

#### DAO API Tests (mock DB calls)

```
[ ] All DAO methods return correct types:
    - create() → Model instance
    - get_*() → Model instance or None
    - list_*() → list[Model]
    - update() → Model instance
    - delete() → bool

[ ] DAO methods don't raise exceptions on valid input
[ ] DAO methods raise ValueError on invalid input (e.g., UUID format)
```

**Acceptance Criteria:**
- ✓ All CRUD operations working for each table
- ✓ Versioning logic auto-increments version_number
- ✓ All DAOs can be imported without errors
- ✓ Unit tests for each DAO pass >95%

---

## MILESTONE 1.2 : API Routes Core

### Task 1.2.1 : Créer Router Novels (CRUD)

#### Unit Tests

```
@pytest.fixture
def client():
    # FastAPI TestClient with test DB
    ...

def test_create_novel(client):
    [ ] POST /api/novels/ with {"title": "Test"}
        returns 200
    [ ] Response contains:
        - id (UUID string)
        - title: "Test"
        - status: "draft"
        - created_at (ISO datetime)
    [ ] Novel is in DB (verify with SELECT)

def test_create_novel_missing_title(client):
    [ ] POST /api/novels/ with {} (no title)
        returns 422 (validation error)
    [ ] Error message indicates "title" is required

def test_list_novels(client):
    [ ] Create 3 novels for current_user
    [ ] GET /api/novels/ returns 200
    [ ] Response is list with 3 items
    [ ] Each item has: id, title, status, created_at

def test_get_novel(client):
    [ ] Create novel, get its ID
    [ ] GET /api/novels/{id} returns 200
    [ ] Response contains full novel data

def test_get_novel_not_found(client):
    [ ] GET /api/novels/invalid-id returns 404
    [ ] Error message: "Novel not found"

def test_get_novel_not_owned(client):
    [ ] Create novel as user1
    [ ] Login as user2
    [ ] GET /api/novels/{user1's_novel_id} returns 404
    [ ] (Permission check)

def test_update_novel(client):
    [ ] Create novel
    [ ] PUT /api/novels/{id} with {"title": "Updated"}
        returns 200
    [ ] Response shows: title: "Updated"
    [ ] updated_at has changed
    [ ] In DB, novel.title == "Updated"

def test_update_novel_creates_version(client):
    [ ] Create novel
    [ ] Update novel title
    [ ] Check versions table:
        SELECT * FROM versions WHERE entity_id = novel_id
    [ ] Should have 1 version with:
        - entity_type: "novel"
        - change_type: "updated"
        - old_data: {old title}
        - new_data: {new title}

def test_delete_novel(client):
    [ ] Create novel
    [ ] DELETE /api/novels/{id} returns 200
    [ ] Response: {"status": "deleted"}
    [ ] Novel no longer in DB
    [ ] Version created with change_type: "deleted"
```

#### Integration Tests

```
def test_create_and_list_workflow(client):
    [ ] Create 5 novels
    [ ] List novels
    [ ] All 5 appear in list
    [ ] Each has unique ID

def test_create_update_delete_workflow(client):
    [ ] Create novel "Original"
    [ ] Update to "Updated"
    [ ] Get by ID, verify title
    [ ] Delete
    [ ] Verify deleted (get returns 404)

def test_authorization_workflow(client):
    [ ] Create novel as user1
    [ ] Try to update as user2 → 404
    [ ] Try to delete as user2 → 404
    [ ] Update as user1 → 200
```

#### API Contract Tests (Swagger/OpenAPI)

```
[ ] POST /api/novels/ documented in OpenAPI schema
[ ] GET /api/novels/ documented
[ ] GET /api/novels/{id} documented
[ ] PUT /api/novels/{id} documented
[ ] DELETE /api/novels/{id} documented
[ ] Each endpoint has correct request/response schemas
```

**Acceptance Criteria:**
- ✓ All 5 endpoints (create, list, get, update, delete) working
- ✓ Authorization checks enforced
- ✓ Validation errors return 422
- ✓ Versions created on update/delete
- ✓ API contract documented

---

### Task 1.2.2 : Créer Router Knowledge Base (CRUD)

#### Unit Tests

```
def test_get_kb(client):
    [ ] Create novel + KB
    [ ] GET /api/novels/{id}/kb/ returns 200
    [ ] Response contains:
        - id
        - universe_docs (dict)
        - characters (list)
        - locations (list)
        - objects (list)

def test_update_universe(client):
    [ ] Create KB
    [ ] PUT /api/novels/{id}/kb/universe
        with {"magic_system": "desc", "world_rules": "desc"}
        returns 200
    [ ] KB.universe_docs updated
    [ ] Version created (entity_type: "kb_universe")

def test_add_character(client):
    [ ] Create KB
    [ ] POST /api/novels/{id}/kb/characters
        with valid character JSON
        returns 200
    [ ] Character added to kb.characters
    [ ] Character has: id, name, age, personality, etc.
    [ ] Version created (entity_type: "character", change_type: "created")

def test_add_character_missing_fields(client):
    [ ] POST with incomplete character
    [ ] Returns 422 (validation error)

def test_update_character(client):
    [ ] Create KB with character
    [ ] PUT /api/novels/{id}/kb/characters/{char_id}
        with updated data
        returns 200
    [ ] Character updated in KB
    [ ] Version created with change_type: "updated"
    [ ] old_data and new_data populated correctly

def test_delete_character(client):
    [ ] Create KB with character
    [ ] DELETE /api/novels/{id}/kb/characters/{char_id}
        returns 200
    [ ] Character removed from kb.characters
    [ ] Version created with change_type: "deleted"

def test_add_location(client):
    [ ] Similar to test_add_character but for locations
    [ ] POST /api/novels/{id}/kb/locations

def test_add_object(client):
    [ ] Similar to test_add_character but for objects
    [ ] POST /api/novels/{id}/kb/objects

def test_kb_authorization(client):
    [ ] Create KB as user1
    [ ] Try to update as user2 → 404
    [ ] Try to update as user1 → 200
```

#### Integration Tests

```
def test_complete_kb_workflow(client):
    [ ] Create novel
    [ ] Update universe doc
    [ ] Add 3 characters
    [ ] Add 2 locations
    [ ] Add 1 object
    [ ] GET /kb returns all data
    [ ] Verify all entities present

def test_kb_with_relationships(client):
    [ ] Add character A
    [ ] Add character B
    [ ] Update A with relationship to B:
        {"relationships": [{"character_id": "B", "type": "ally"}]}
    [ ] Verify A.relationships contains B
```

**Acceptance Criteria:**
- ✓ Universe, Characters, Locations, Objects all CRUD working
- ✓ Versions created for each operation
- ✓ Authorization enforced
- ✓ Relationships can be stored and retrieved

---

### Task 1.2.3 : Ajouter Session Management pour Novel Courant

#### Unit Tests

```
def test_select_novel(client):
    [ ] Create novel
    [ ] POST /api/novels/{id}/select returns 200
    [ ] Response: {"current_novel_id": "uuid"}
    [ ] In DB, user.current_novel_id updated

def test_select_novel_wrong_owner(client):
    [ ] Create novel as user1
    [ ] Login as user2
    [ ] POST /api/novels/{user1_novel_id}/select
        returns 404 (not found)
    [ ] user2.current_novel_id remains unchanged

def test_get_current_novel_dependency(client):
    [ ] Create endpoint that uses get_current_novel() dependency
    [ ] Call with no novel selected → 400 (no novel selected)
    [ ] Select a novel
    [ ] Call again → 200 (returns that novel)
```

#### Integration Tests

```
def test_session_persistence(client):
    [ ] Select novel A
    [ ] Make API call (should use novel A)
    [ ] Select novel B
    [ ] Make API call (should use novel B)
    [ ] Select novel A again
    [ ] Make API call (should use novel A)

def test_novel_selection_in_chat(client):
    [ ] Select novel A
    [ ] POST /api/chat/completions (chat message)
    [ ] Verify context uses novel A's KB
    [ ] (Will be fully tested in Task 1.3.2)
```

**Acceptance Criteria:**
- ✓ Novel selection persisted per user
- ✓ get_current_novel() dependency works
- ✓ Prevents selecting other users' novels
- ✓ Can switch between novels

---

## MILESTONE 1.3 : Context Injection System

### Task 1.3.1 : Créer Prompt Builder

#### Unit Tests

```
from backend.utils.prompt_builder import PromptBuilder

def test_base_system_prompt(client):
    [ ] PromptBuilder.BASE_SYSTEM_PROMPT is not empty
    [ ] Contains "assistant créatif"
    [ ] Contains "cohérence narrative"

def test_format_universe(client):
    [ ] universe_docs = {"magic": "...", "rules": "..."}
    [ ] result = PromptBuilder.format_universe(universe_docs)
    [ ] Result contains "**magic:**"
    [ ] Result contains "**rules:**"

def test_format_universe_empty(client):
    [ ] universe_docs = {}
    [ ] result = PromptBuilder.format_universe({})
    [ ] Result == "Aucun document univers défini."

def test_format_characters(client):
    [ ] characters = [
        {"id": "c1", "name": "Alice", "role": "protagonist"},
        {"id": "c2", "name": "Bob", "role": "antagonist"}
    ]
    [ ] result = PromptBuilder.format_characters(characters, limit=5)
    [ ] Result contains "Alice"
    [ ] Result contains "Bob"
    [ ] Result contains "protagonist"

def test_format_characters_limit(client):
    [ ] characters = [10 character dicts]
    [ ] result = PromptBuilder.format_characters(characters, limit=3)
    [ ] Result contains exactly 3 characters (not 10)

def test_format_recent_scenes(client):
    [ ] manuscript = "Scene 1\nScene 2\nScene 3" * 100
    [ ] result = PromptBuilder.format_recent_scenes(manuscript, limit_lines=500)
    [ ] len(result) <= 500

def test_format_conversation_history(client):
    [ ] messages = [
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Answer 1"},
        {"role": "user", "content": "Question 2"}
    ]
    [ ] result = PromptBuilder.format_conversation_history(messages, limit=8)
    [ ] Result contains "user"
    [ ] Result contains "Question 1"

def test_build_full_prompt_no_context(client):
    [ ] context_level = "none"
    [ ] result = PromptBuilder.build_full_prompt(novel_id, db, 
                                                  context_level="none")
    [ ] result == PromptBuilder.BASE_SYSTEM_PROMPT
    [ ] No universe section
    [ ] No characters section

def test_build_full_prompt_minimal(client):
    [ ] Create novel with KB
    [ ] context_level = "minimal"
    [ ] result = PromptBuilder.build_full_prompt(novel_id, db, 
                                                  context_level="minimal")
    [ ] Result contains BASE_SYSTEM_PROMPT
    [ ] Result contains "### UNIVERS"
    [ ] Result contains "### PERSONNAGES"
    [ ] Result does NOT contain "### PASSAGES RÉCENTS"

def test_build_full_prompt_full(client):
    [ ] Create novel with KB + manuscript
    [ ] context_level = "full"
    [ ] result = PromptBuilder.build_full_prompt(novel_id, db,
                                                  context_level="full")
    [ ] Result contains universe section
    [ ] Result contains characters section
    [ ] Result contains "### PASSAGES RÉCENTS"
    [ ] Result contains "### HISTORIQUE CONVERSATION"

def test_build_full_prompt_uses_db(client):
    [ ] Create novel with:
        - universe_docs: {"magic": "Fire magic"}
        - 3 characters
        - manuscript with content
    [ ] result = PromptBuilder.build_full_prompt(novel_id, db)
    [ ] Result string contains "Fire magic"
    [ ] Result contains names of 3 characters
```

#### Integration Tests

```
def test_context_assembly_from_db(client):
    [ ] Create complete novel:
        - Universe docs
        - 5 characters
        - Manuscript
        - Chat history
    [ ] build_full_prompt() loads all data correctly
    [ ] Prompt is well-formatted
    [ ] No data loss or truncation issues
```

**Acceptance Criteria:**
- ✓ PromptBuilder formats all sections correctly
- ✓ Respects context_level parameter
- ✓ Handles missing data gracefully
- ✓ Truncates appropriately (no token overflow)

---

### Task 1.3.2 : Intégrer Context Injection dans Route Chat

#### Unit Tests

```
def test_chat_with_novel_context(client):
    [ ] Create novel with KB
    [ ] Select novel
    [ ] POST /api/chat/completions
        with {"messages": [{"role": "user", "content": "Tell me about the magic"}]}
    [ ] Returns 200
    [ ] Response contains answer related to the universe

def test_chat_without_novel_selected(client):
    [ ] Don't select a novel
    [ ] POST /api/chat/completions
    [ ] Routes to normal OpenWebUI chat (no context injection)
    [ ] Returns 200

def test_context_not_in_user_message(client):
    [ ] Create novel
    [ ] Select it
    [ ] POST chat message
    [ ] User message content is unchanged
    [ ] (context is in system prompt, not visible to user)

def test_context_snapshot_created(client):
    [ ] Create novel
    [ ] Select it
    [ ] POST chat message
    [ ] Check context_snapshots table:
        SELECT * FROM context_snapshots
        WHERE chat_id = ?
    [ ] Should have 1 snapshot
    [ ] snapshot.injected_context contains full prompt
    [ ] snapshot.kb_snapshot contains KB state
```

#### Integration Tests

```
def test_multi_turn_conversation_with_context(client):
    [ ] Create novel "Fantasy World" with:
        - Universe: magic system, characters
        - Characters: Hero, Villain
    [ ] Select novel
    [ ] Message 1: "Describe the magic"
        → Response uses universe context
    [ ] Message 2: "What does Hero want?"
        → Response uses character context
    [ ] Message 3: "Create a scene"
        → Response uses all context + conversation history
    [ ] All 3 snapshots created

def test_context_switches_on_novel_change(client):
    [ ] Create novel A and B (different KBs)
    [ ] Select novel A, chat message
        → Uses A's context
    [ ] Select novel B, chat message
        → Uses B's context (different characters, universe)
```

#### Prompt Injection Tests

```
def test_injected_prompt_structure(client):
    [ ] Create novel + select it
    [ ] POST chat message
    [ ] Retrieve context_snapshot
    [ ] Parse injected_context
    [ ] Verify structure:
        ├─ BASE_SYSTEM_PROMPT
        ├─ ### UNIVERS
        ├─ ### PERSONNAGES
        ├─ ### PASSAGES RÉCENTS
        └─ ### HISTORIQUE CONVERSATION
```

**Acceptance Criteria:**
- ✓ Context injected into system prompt
- ✓ Context snapshots created for each message
- ✓ Works with both selected and unselected novels
- ✓ Persists across multiple messages

---

## MILESTONE 1.4 : Frontend Integration (Novel Manager)

### Task 1.4.1 : Créer Composant Novel Selector (Svelte)

#### Unit Tests (Component Tests with Vitest)

```
import { render, screen } from '@testing-library/svelte';
import NovelSelector from './NovelSelector.svelte';

describe('NovelSelector', () => {
  test('renders novel selector button', () => {
    [ ] Component mounts without error
    [ ] Button visible with text containing "Novel"
    [ ] Button is clickable
  });

  test('dropdown opens on button click', async () => {
    [ ] Click button
    [ ] Dropdown menu appears
    [ ] Menu contains "Your Novels" header
  });

  test('displays list of novels', async () => {
    [ ] Mock novels store with 3 items
    [ ] Dropdown shows all 3 novels
    [ ] Each novel shows: name, status badge
  });

  test('selects novel on click', async () => {
    [ ] Click on a novel in dropdown
    [ ] POST /api/novels/{id}/select called
    [ ] Dropdown closes
    [ ] Button text changes to selected novel name
  });

  test('creates new novel', async () => {
    [ ] Click "+ New Novel" button
    [ ] Prompt appears for novel name
    [ ] Enter "New Novel"
    [ ] POST /api/novels/ called
    [ ] New novel appears in list
  });

  test('shows loading state', async () => {
    [ ] Before novels load
    [ ] "Loading..." text visible
    [ ] After loaded, novels list visible
  });

  test('handles API errors gracefully', async () => {
    [ ] Mock API error (500)
    [ ] Error message displayed (optional)
    [ ] UI doesn't crash
  });
});
```

#### Integration Tests

```
def test_novel_selector_in_chat(client):
    # Start frontend
    [ ] Open http://localhost:5173 in browser
    [ ] NovelSelector button visible
    [ ] Create new novel via selector
    [ ] Verify POST /api/novels/ succeeded
    [ ] Verify novel appears in dropdown
    [ ] Select novel
    [ ] Verify current_novel_id updated in backend
    [ ] Verify chat context header shows novel name

def test_novel_switch_flow(client):
    [ ] Create 2 novels via selector
    [ ] Select novel 1 → button shows "Novel 1"
    [ ] Select novel 2 → button shows "Novel 2"
    [ ] Select novel 1 again → button shows "Novel 1"
```

#### Manual E2E Tests

```
Browser: http://localhost:5173
[ ] Novel selector button visible in header
[ ] Click button → dropdown with current novels
[ ] Create new novel:
    - Click "+ New Novel"
    - Type "Test Novel"
    - Confirm
    - Novel appears in list
[ ] Select novel:
    - Click novel in dropdown
    - Button shows novel name
    - Dropdown closes
[ ] Styling looks good (no CSS errors)
```

**Acceptance Criteria:**
- ✓ Component renders without errors
- ✓ Can create novels
- ✓ Can select/switch novels
- ✓ Dropdown UI functional
- ✓ API calls working

---

### Task 1.4.2 : Modifier Chat UI pour Afficher Contexte Novel

#### Manual Tests

```
Browser: http://localhost:5173
[ ] With novel selected:
    - Above chat area, badge shows "📖 Novel Name"
    - Shows character count (if KB has characters)
    - Shows last modified date
[ ] Context header disappears when no novel selected
[ ] Context header updates when switching novels
```

#### CSS Tests

```
[ ] Badge has reasonable padding/margin
[ ] Text is readable (good contrast)
[ ] No overflow (text doesn't extend beyond container)
[ ] Responsive on mobile
```

**Acceptance Criteria:**
- ✓ Context header displays when novel selected
- ✓ Updates on novel change
- ✓ Styling looks good

---

### Task 1.4.3 : Créer Stub pour Knowledge Base Panel

#### Manual Tests

```
Browser: http://localhost:5173
[ ] KB panel visible on right side of screen
[ ] Tabs visible: Universe, Characters, Locations, Objects, Timeline
[ ] Tab buttons functional (can click)
[ ] Placeholder text: "Knowledge Base UI coming soon..."
[ ] With novel selected, panel shows novel data (placeholder)
[ ] Without novel selected, shows "Select a novel first"
```

**Acceptance Criteria:**
- ✓ Panel structure in place
- ✓ Tabs created
- ✓ Placeholder content visible
- ✓ Ready for Task 2.1.1 implementation

---

## MILESTONE 1.5 : Testing & Polish

### Task 1.5.1 : Écrire Tests Unitaires DAOs

#### Test Execution

```
Poetry run pytest backend/tests/test_daos.py -v

Expected output:
  test_novel_create PASSED
  test_novel_list PASSED
  test_novel_get_by_id PASSED
  test_novel_update PASSED
  test_novel_delete PASSED
  test_kb_get_by_novel PASSED
  test_kb_update_universe PASSED
  test_kb_add_character PASSED
  test_version_create PASSED
  test_version_numbering PASSED
  test_version_history PASSED
  
  ============= 11 passed in X.XXs =============

[ ] All tests PASS
[ ] Code coverage > 90% for DAOs
[ ] No warnings or errors
```

**Acceptance Criteria:**
- ✓ All DAO tests passing
- ✓ >90% coverage
- ✓ No flaky tests

---

### Task 1.5.2 : Écrire Tests API Endpoints

#### Test Execution

```
Poetry run pytest backend/tests/test_api_*.py -v

Expected:
  test_create_novel PASSED
  test_list_novels PASSED
  test_get_novel PASSED
  test_get_novel_not_found PASSED
  test_update_novel PASSED
  test_delete_novel PASSED
  test_get_kb PASSED
  test_update_universe PASSED
  test_add_character PASSED
  test_select_novel PASSED
  test_chat_with_context PASSED
  ... (more tests)
  
  ============= 20+ passed in X.XXs =============

[ ] All endpoint tests PASS
[ ] Happy paths tested
[ ] Error cases tested (404, 422, 400)
[ ] Authorization tested
```

**Acceptance Criteria:**
- ✓ All API tests passing
- ✓ >80% code coverage for routes
- ✓ Error handling tested

---

### Task 1.5.3 : Documentation Backend

#### Manual Review

```
[ ] File backend/STORYWEAVER_API.md exists
[ ] Documents all endpoints:
    - POST /api/novels/
    - GET /api/novels/
    - GET /api/novels/{id}
    - PUT /api/novels/{id}
    - DELETE /api/novels/{id}
    - GET /api/novels/{id}/kb/
    - PUT /api/novels/{id}/kb/universe
    - POST /api/novels/{id}/kb/characters
    - PUT /api/novels/{id}/kb/characters/{id}
    - DELETE /api/novels/{id}/kb/characters/{id}
    - POST /api/novels/{id}/select
    - POST /api/chat/completions (modified)

[ ] Each endpoint documented with:
    - HTTP method
    - Path
    - Request body (if applicable)
    - Response (200 example)
    - Error cases (404, 422, etc.)
    - Example curl command

[ ] Authentication documented (JWT, current_user)
[ ] Error handling documented
[ ] Context injection explained
```

**Acceptance Criteria:**
- ✓ All endpoints documented
- ✓ Examples provided
- ✓ Errors explained

---

### Task 1.5.4 : Manual Testing & QA Phase 1

#### End-to-End Test Plan

```
Test Case 1: Create & Select Novel
[ ] Open frontend (http://localhost:5173)
[ ] Click Novel Selector button
[ ] Click "+ New Novel"
[ ] Enter "Fantasy World"
[ ] Novel appears in selector
[ ] Click novel to select
[ ] Button shows "📖 Fantasy World"
[ ] Context header visible

Test Case 2: Create KB for Novel
[ ] With "Fantasy World" selected
[ ] Open KB Panel (right sidebar)
[ ] Click "Universe" tab
[ ] Add universe rules (JSON/text)
[ ] Save
[ ] Refresh page
[ ] Rules still there

Test Case 3: Add Characters to KB
[ ] In KB Panel, "Characters" tab
[ ] Click "+ Add Character"
[ ] Form: Name="Hero", Role="protagonist"
[ ] Save
[ ] Character appears in list
[ ] Click to edit, change age
[ ] Save, verify updated

Test Case 4: Chat with Novel Context
[ ] Select "Fantasy World"
[ ] In chat, ask "Describe the magic"
[ ] Response should mention the universe rules
[ ] Ask "Who is the Hero?"
[ ] Response should include character details

Test Case 5: Versioning
[ ] Edit universe rules
[ ] In Universe tab, click "Version History"
[ ] Should show original version and update
[ ] Click [View] on original
[ ] Should show diff
[ ] Click [Revert] on original
[ ] Universe reverts
[ ] New version created

Test Case 6: Multi-Project
[ ] Create novel "Sci-Fi Story"
[ ] Select it
[ ] Context switches (header shows "Sci-Fi Story")
[ ] Add different characters (unique to this novel)
[ ] Switch back to "Fantasy World"
[ ] Characters are different
[ ] Switch to "Sci-Fi Story"
[ ] Original characters back

Test Case 7: Error Handling
[ ] Try to select someone else's novel
   (use browser dev tools to modify API call)
[ ] Should get 404 error
[ ] UI stays functional
[ ] Current novel unchanged

Test Case 8: Data Persistence
[ ] Create novel, add KB data
[ ] Close browser tab
[ ] Open http://localhost:5173 again
[ ] Refresh backend
[ ] Data still there
```

#### Bug Tracking

```
Format for any bugs found:
  [ ] Bug ID: [P1-001]
  [ ] Title: [Title]
  [ ] Severity: [Critical/Major/Minor]
  [ ] Steps to Reproduce: [Steps]
  [ ] Expected: [Expected behavior]
  [ ] Actual: [What actually happens]
  [ ] Workaround: [If any]
```

**Acceptance Criteria:**
- ✓ All 8 test cases pass
- ✓ No critical bugs found (or all resolved)
- ✓ Data persists
- ✓ UI is responsive
- ✓ No console errors in browser

---

## MILESTONE 1.6 : Deployment & Documentation

### Task 1.6.1 : Préparer Deployment sur VPS

#### Local Docker Test

```
[ ] docker-compose up succeeds (no build errors)
[ ] All 3 services start:
    - storyweaver container (ports 8000)
    - ollama container (ports 11434)
    - db container (ports 5432)
[ ] Can access http://localhost:8000 (frontend)
[ ] Can access http://localhost:5173 (dev frontend)
[ ] Database migrations run automatically
[ ] No container restart loops
```

#### Environment Configuration

```
.env.production file contains:
[ ] OLLAMA_URL=http://ollama:11434
[ ] DATABASE_URL=postgresql://user:pass@db:5432/storyweaver
[ ] SECRET_KEY=[generated random string]
[ ] DEBUG=false
[ ] LOG_LEVEL=info
```

**Acceptance Criteria:**
- ✓ Docker compose file valid
- ✓ All services start and communicate
- ✓ Database migrations automatic
- ✓ Environment configured

---

### Task 1.6.2 : Créer Documentation Setup pour Développeur

#### File Review

```
[ ] DEVELOPMENT.md exists with sections:
    - Quick Start
    - Prerequisites
    - Setup Steps
    - Running Dev Server
    - Database Migrations
    - Running Tests
    - Troubleshooting

[ ] Follow DEVELOPMENT.md exactly:
    - Can complete setup from scratch
    - All commands work
    - No missing steps
    - All references accurate

[ ] DEPLOYMENT.md exists with sections:
    - Server Requirements
    - Installation Steps
    - Docker Setup
    - Database Setup
    - Environment Variables
    - Health Checks
    - Monitoring

[ ] ARCHITECTURE_EXISTING.md well-organized
[ ] STORYWEAVER_API.md complete
```

**Acceptance Criteria:**
- ✓ Documentation complete
- ✓ Can follow docs end-to-end
- ✓ No missing information

---

### Task 1.6.3 : Commit & Push Phase 1

#### Git Commit Checklist

```
[ ] All files staged: git add .
[ ] Commit message descriptive:
    "feat: Phase 1 - Core infrastructure
    
    - Novel multi-project management (CRUD)
    - Knowledge Base storage (characters, universe, etc.)
    - Context injection into LLM prompts
    - Versioning system for tracking changes
    - Session management for novel selection
    - Frontend Novel Selector component
    - API endpoints fully tested
    - Documentation complete"

[ ] Commit succeeds: git commit -m "..."
[ ] Push succeeds: git push origin feature/storyweaver-core
[ ] Branch visible on GitHub
[ ] No merge conflicts
```

**Acceptance Criteria:**
- ✓ Phase 1 code committed
- ✓ Branch pushed to GitHub
- ✓ Ready for PR/review

---

# PHASE 2 : KNOWLEDGE BASE EDITOR

## MILESTONE 2.1 : KB UI Components

### Task 2.1.1 : Créer KnowledgeBaseEditor.svelte Principal

#### Manual Tests

```
Browser: http://localhost:5173

[ ] With novel selected:
    - KB Panel shows editor interface
    - Tabs visible: Universe, Characters, Locations, Objects, Timeline
    - Content area changes when clicking tabs
    - Save button visible and clickable

[ ] Universe Tab:
    - Text editor visible (Markdown or JSON)
    - Can type and edit
    - "Unsaved Changes" indicator appears
    - Click Save → request sent
    - Toast: "Universe saved ✓"
    - Indicator disappears

[ ] Characters Tab:
    - List of characters visible (if any)
    - [Add Character] button visible
    - Can click character to edit
    - Form opens with fields

[ ] UI Responsive:
    - Works on desktop
    - KB Panel can be hidden/shown
    - Text readable
```

**Acceptance Criteria:**
- ✓ KB Editor component renders
- ✓ All tabs functional
- ✓ Save/Cancel buttons work
- ✓ API calls succeed

---

### Task 2.1.2 : Créer UniverseEditor Sub-Component

#### Manual Tests

```
[ ] Universe Tab selected:
    - Editor shows current universe_docs
    - Can edit text/JSON
    - Preview pane shows formatted version
    - Save button sends PUT request
    - Data persists

[ ] Format support:
    - Can handle JSON format
    - Can handle Markdown format
    - Can handle plain text
    - Validation errors shown if invalid JSON
```

**Acceptance Criteria:**
- ✓ Editor functional
- ✓ Preview shows content
- ✓ Saves to DB

---

### Task 2.1.3 : Créer CharacterManager Sub-Component

#### Manual Tests

```
[ ] Characters Tab:
    - List of current characters displayed
    - Search box works (search by name)
    - [+ Add Character] button
    - Click to add form opens
    - Form has fields: name, age, appearance, personality, arc, relationships

[ ] Add Character:
    - Fill form
    - Click Save
    - Character added to list
    - Success toast
    - Form closes

[ ] Edit Character:
    - Click character in list
    - Form opens with current data
    - Modify fields
    - Click Save
    - Character updated in list
    - Version created

[ ] Delete Character:
    - Click character
    - [Delete] button appears
    - Confirm dialog
    - Character removed from list
    - Version created

[ ] Relationships:
    - When adding/editing character
    - "Relationships" field shows multi-select
    - Can select other characters
    - Relationships saved and retrieved
```

**Acceptance Criteria:**
- ✓ Add character working
- ✓ Edit character working
- ✓ Delete character working
- ✓ Relationships functional

---

### Task 2.1.4 : Créer LocationManager & ObjectManager

#### Manual Tests

```
[ ] Locations Tab:
    - Similar flow to Characters
    - Add, edit, delete locations
    - Fields: name, description, type, importance

[ ] Objects Tab:
    - Similar flow to Characters
    - Add, edit, delete objects
    - Fields: name, description, significance

[ ] Both:
    - Save to DB
    - Versions created
    - Can search
```

**Acceptance Criteria:**
- ✓ Locations CRUD working
- ✓ Objects CRUD working

---

## MILESTONE 2.2 : Versioning Frontend

### Task 2.2.1 : Créer VersionHistory Component

#### Manual Tests

```
[ ] In any editor (character, universe, etc.):
    - [Version History] button visible
    - Click opens modal with timeline
    - Timeline shows:
      - Timestamp of each change
      - Type (created/updated/deleted)
      - [View] button
      - [Revert] button (if not current)

[ ] View Version:
    - Click [View]
    - Shows old and new data
    - Diff highlighting
    - Can compare two versions side-by-side

[ ] Revert Version:
    - Click [Revert]
    - Confirmation dialog
    - Confirm
    - Entity reverted to that version
    - New "reverted" version created
    - Timeline updated
```

**Acceptance Criteria:**
- ✓ Version history displays
- ✓ Revert works
- ✓ New version created on revert

---

### Task 2.2.2 : Ajouter Endpoint Versioning Backend

#### Tests

```
[ ] GET /api/novels/{id}/versions/{entity_id}
    returns list of versions
    
[ ] POST /api/novels/{id}/versions/{entity_id}/{vnum}/revert
    reverts to that version
    creates new "reverted" version
```

**Acceptance Criteria:**
- ✓ Versioning endpoints working

---

## MILESTONE 2.3 : Search & Linking

### Task 2.3.1 : Implémenter Full-Text Search KB

#### Manual Tests

```
[ ] In KB Panel:
    - Search box at top
    - Type character name
    - Results show matching characters
    - Type location name
    - Results show matching locations

[ ] Search functionality:
    - Case-insensitive
    - Finds partial matches
    - Fast response
```

**Acceptance Criteria:**
- ✓ Search working across KB

---

### Task 2.3.2 : Créer Auto-Linking

#### Manual Tests

```
[ ] When editing character:
    - Relationships field
    - Multi-select other characters
    - Can link to locations, objects
    - Links saved and retrieved
    - Can follow links (click to open related entity)
```

**Acceptance Criteria:**
- ✓ Relationships working
- ✓ Can link entities

---

## MILESTONE 2.4 : Testing Phase 2

### Task 2.4.1 : Tests KB API & UI

#### Test Checklist

```
[ ] Create novel
[ ] Add universe doc
[ ] Add 3 characters with relationships
[ ] Add 2 locations
[ ] Add 1 object
[ ] Edit each entity
[ ] Delete one character
[ ] Verify versions created
[ ] Search for characters
[ ] View version history
[ ] Revert a character
[ ] Verify all data correct
```

**Acceptance Criteria:**
- ✓ All KB operations working
- ✓ Data consistent
- ✓ Versions track all changes

---

### Task 2.4.2 : Commit Phase 2

```
git add .
git commit -m "feat: Phase 2 - Knowledge Base Editor..."
git push origin feature/storyweaver-core
```

**Acceptance Criteria:**
- ✓ Phase 2 committed

---

# PHASE 3 : CUSTOM TOOLS & MODULES

## MILESTONE 3.1-3.3 : Tools Implementation & Testing

### Core Tests for Each Tool

#### Brainstorm Tool

```
[ ] /brainstorm prompt generates 5 ideas
[ ] Ideas are relevant to the prompt
[ ] Ideas use universe/character context
[ ] Output is well-formatted list
[ ] Can be reused/stored
```

#### Coherence Checker

```
[ ] /analyze passage detects incohérences
[ ] Finds timeline conflicts
[ ] Finds character inconsistencies
[ ] Finds rule violations
[ ] Provides score
```

#### Dialogue Generator

```
[ ] /dialogue character1 character2 generates dialogue
[ ] Dialogue is character-appropriate
[ ] Dialogue advances narrative
[ ] Format is readable
```

#### Outline Generator

```
[ ] /outline 3-act generates 3-act structure
[ ] /outline 5-act generates 5-act structure
[ ] Outlines are detailed
[ ] Include chapter summaries
[ ] Include key narrative points
```

---

# PHASE 4 : MANUSCRIPT EDITOR & FINAL POLISH

## Core Tests

#### Manuscript Editor

```
[ ] Can open manuscript
[ ] Can edit chapters/scenes
[ ] Word count updates
[ ] Status selector works
[ ] Auto-save triggers
[ ] Keyboard shortcuts work
[ ] Markdown highlighting works
```

#### Quick Actions

```
[ ] [Analyze] button works
[ ] [Continue] button works
[ ] [Dialogue] button works
[ ] Results display in chat
```

#### Export

```
[ ] Export to Markdown works
[ ] Export to PDF works
[ ] Export to text works
[ ] Formatting preserved
```

#### Multi-Project

```
[ ] Archive novel
[ ] Restore archived novel
[ ] Access archived projects
[ ] Switch between current and archived
```

---

## 📊 TEST EXECUTION SUMMARY

### Phase 1 Totals
```
Unit Tests:       40+ tests (DAOs + API)
Integration Tests: 15+ tests
Manual Tests:     8 end-to-end scenarios
Total:            ~60+ assertions

Expected Coverage: >85%
Expected Pass Rate: 100%
```

### Phase 2 Totals
```
Component Tests:   20+ (Svelte components)
API Tests:         10+ (KB operations)
Manual Tests:      10 scenarios
Total:            ~40+ assertions

Expected Coverage: >80%
```

### Phase 3 Totals
```
Tool Tests:       25+ (1 per tool variant)
Integration:      5+ (tool combinations)
Total:            ~30+ assertions
```

### Phase 4 Totals
```
Editor Tests:     15+ (editor functionality)
Export Tests:     5+ (formats)
Manual Tests:     5 scenarios
Total:            ~25+ assertions
```

---

## ✅ HOW TO RUN ALL TESTS

```bash
# Unit tests
poetry run pytest backend/tests/ -v

# Frontend tests
npm run test

# Manual testing checklist
# (see E2E test plan above)

# Generate coverage report
poetry run pytest --cov=backend backend/tests/
```

---

**This checklist should be followed milestone by milestone, not all at once!**
