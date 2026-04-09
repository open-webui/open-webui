# ✅ TEST CHECKLIST : StoryWeaver

**Format:** Chaque test est indépendant et répétable.  
**Exécution:** 1 test = 5-15 minutes  
**Outils:** Postman/curl, browser DevTools, pytest  

---

## PHASE 1 : CORE INFRASTRUCTURE TESTING

### Milestone 1.0 : Setup & Fork Initial

#### Test 1.0.1 : Git Setup Validation
**Test ID:** SETUP-001  
**Duration:** 5 min  

**Preconditions:**
- Task 1.0.1 completed
- Access to GitHub repo

**Test Steps:**
1. Open terminal, navigate to project
2. Run: `git log --oneline | head -5`
   - **Expected:** Shows original OpenWebUI commits
3. Run: `git branch -a`
   - **Expected:** Shows `feature/storyweaver-core` as current branch
4. Run: `git remote -v`
   - **Expected:** Shows origin pointing to your fork
5. Create test commit: `git commit --allow-empty -m "test commit"`
6. Run: `git log --oneline | head -1`
   - **Expected:** Shows "test commit"
7. Run: `git reset HEAD~1`
   - **Expected:** Removes test commit

**Pass Criteria:** All git commands work, branch exists, remote correct

---

#### Test 1.0.2 : Backend Environment Setup
**Test ID:** SETUP-002  
**Duration:** 10 min  

**Preconditions:**
- Task 1.0.2 completed
- Python 3.10+ installed
- Node.js 18+ installed

**Test Steps - Backend:**
1. Navigate to `backend/` directory
2. Run: `poetry --version`
   - **Expected:** Shows Poetry version >= 1.2
3. Run: `poetry install`
   - **Expected:** Installs without errors, shows "lock file not found"
4. Run: `poetry env list`
   - **Expected:** Shows virtual environment created
5. Run: `poetry run python --version`
   - **Expected:** Shows Python 3.10+
6. Run: `poetry run python main.py`
   - **Expected:** Server starts, shows "Uvicorn running on http://0.0.0.0:8000"
7. In another terminal: `curl http://localhost:8000/api/models`
   - **Expected:** Returns JSON array (may be empty, but valid JSON)
8. Press Ctrl+C to stop server

**Test Steps - Frontend:**
1. Navigate to `frontend/` directory
2. Run: `node --version`
   - **Expected:** Shows Node.js 18+
3. Run: `npm install`
   - **Expected:** Installs dependencies, shows "added X packages"
4. Run: `npm run dev`
   - **Expected:** Dev server starts, shows "Local: http://localhost:5173"
5. Open browser, navigate to `http://localhost:5173`
   - **Expected:** OpenWebUI loads, chat interface visible
6. Press Ctrl+C to stop dev server

**Pass Criteria:** Both backend and frontend start without errors

---

#### Test 1.0.3 : Architecture Understanding
**Test ID:** SETUP-003  
**Duration:** 15 min  

**Preconditions:**
- Task 1.0.3 completed
- ARCHITECTURE_EXISTING.md created

**Test Steps:**
1. Read `ARCHITECTURE_EXISTING.md`
2. Draw ASCII diagram on paper:
   - Frontend components
   - Backend routes
   - Database connection
3. Answer questions:
   - **Q1:** Where is User model defined?
     - **Expected:** Can locate in `backend/database/`
   - **Q2:** How does chat message flow from frontend to Ollama?
     - **Expected:** Can trace complete path
   - **Q3:** What stores manage state on frontend?
     - **Expected:** Can list them (maybe svelte stores)
4. Run: `grep -r "async def.*chat" backend/`
   - **Expected:** Finds chat endpoints
5. Verify 3+ database models are documented

**Pass Criteria:** Can explain full architecture in writing

---

### Milestone 1.1 : Database Extensions

#### Test 1.1.1 : Models Import and Validation
**Test ID:** DB-001  
**Duration:** 10 min  

**Preconditions:**
- Task 1.1.1 completed
- models_storyweaver.py exists

**Test Steps:**
1. Run: `poetry run python`
2. In Python REPL:
   ```python
   from backend.database.models_storyweaver import Novel, KnowledgeBase, Manuscript, Version, Conversation
   print("All models imported successfully")
   ```
   - **Expected:** No ImportError
3. Check each model has required fields:
   ```python
   novel_fields = [c.name for c in Novel.__table__.columns]
   assert 'id' in novel_fields
   assert 'user_id' in novel_fields
   assert 'title' in novel_fields
   assert 'status' in novel_fields
   ```
   - **Expected:** All assertions pass
4. Check relationships:
   ```python
   assert hasattr(Novel, 'knowledge_base')
   assert hasattr(Novel, 'manuscript')
   ```
   - **Expected:** Relationships defined
5. Exit REPL: `exit()`

**Pass Criteria:** All models import and have correct fields

---

#### Test 1.1.2 : Migration Generation and Execution
**Test ID:** DB-002  
**Duration:** 15 min  

**Preconditions:**
- Task 1.1.2 completed
- Alembic migration file created

**Test Steps:**
1. Navigate to backend directory
2. Run: `alembic current`
   - **Expected:** Shows current revision (if any)
3. Check migration file exists: `ls alembic/versions/*.py`
   - **Expected:** Shows new migration file with timestamp
4. Run: `alembic upgrade head`
   - **Expected:** Shows "Running upgrade ... -> [hash]"
5. Verify tables created:
   ```bash
   poetry run python -c "
   from backend.database.database import engine
   from sqlalchemy import inspect
   inspector = inspect(engine)
   tables = inspector.get_table_names()
   required = ['novels', 'knowledge_bases', 'manuscripts', 'conversations', 'versions']
   for table in required:
       assert table in tables, f'{table} not found'
   print('All tables created!')
   "
   ```
   - **Expected:** "All tables created!"
6. Run: `alembic downgrade -1`
   - **Expected:** Shows downgrade successful
7. Run: `alembic upgrade head`
   - **Expected:** Can re-apply migration

**Pass Criteria:** Migration creates all 5 new tables

---

#### Test 1.1.3 : DAO CRUD Operations
**Test ID:** DB-003  
**Duration:** 15 min  

**Preconditions:**
- Task 1.1.3 completed
- DAOs.py implemented
- Test database available

**Test Steps - Create Comprehensive Test File:**

Create `backend/tests/test_daos.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from backend.database.models_storyweaver import Base, Novel, KnowledgeBase
from backend.database.daos import NovelDAO, KnowledgeBaseDAO, VersionDAO

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

class TestNovelDAO:
    
    def test_create_novel(self, db):
        """Test creating a novel"""
        novel = NovelDAO.create(db, "user_123", "My Novel", "A test novel")
        assert novel.title == "My Novel"
        assert novel.user_id == "user_123"
        assert novel.status == "draft"
        assert novel.id is not None
    
    def test_get_novel_by_id(self, db):
        """Test retrieving novel by ID"""
        created = NovelDAO.create(db, "user_123", "Novel1")
        retrieved = NovelDAO.get_by_id(db, created.id)
        assert retrieved.id == created.id
        assert retrieved.title == "Novel1"
    
    def test_list_novels_by_user(self, db):
        """Test listing all novels for a user"""
        NovelDAO.create(db, "user_123", "Novel1")
        NovelDAO.create(db, "user_123", "Novel2")
        NovelDAO.create(db, "user_456", "Novel3")  # Different user
        
        user_123_novels = NovelDAO.list_by_user(db, "user_123")
        assert len(user_123_novels) == 2
        assert all(n.user_id == "user_123" for n in user_123_novels)
    
    def test_update_novel(self, db):
        """Test updating novel"""
        novel = NovelDAO.create(db, "user_123", "Old Title")
        updated = NovelDAO.update(db, novel.id, title="New Title", status="in_progress")
        assert updated.title == "New Title"
        assert updated.status == "in_progress"
    
    def test_delete_novel(self, db):
        """Test deleting novel"""
        novel = NovelDAO.create(db, "user_123", "ToDelete")
        NovelDAO.delete(db, novel.id)
        result = NovelDAO.get_by_id(db, novel.id)
        assert result is None

class TestVersionDAO:
    
    def test_create_version(self, db):
        """Test creating version record"""
        version = VersionDAO.create(
            db,
            novel_id=uuid4(),
            entity_type="character",
            entity_id="char_001",
            old_data={"name": "Old Name"},
            new_data={"name": "New Name"},
            change_type="updated"
        )
        assert version.version_number == 1
        assert version.change_type == "updated"
    
    def test_version_numbering(self, db):
        """Test version numbers increment"""
        novel_id = uuid4()
        v1 = VersionDAO.create(db, novel_id, "char", "char_001", {}, {"v": 1}, "created")
        v2 = VersionDAO.create(db, novel_id, "char", "char_001", {"v": 1}, {"v": 2}, "updated")
        assert v1.version_number == 1
        assert v2.version_number == 2
    
    def test_get_history(self, db):
        """Test retrieving version history"""
        novel_id = uuid4()
        for i in range(5):
            VersionDAO.create(db, novel_id, "char", "char_001", {}, {"v": i}, "updated")
        
        history = VersionDAO.get_history(db, "char_001")
        assert len(history) == 5
        assert history[0].version_number == 5  # Latest first
```

Run:
```bash
poetry run pytest backend/tests/test_daos.py -v
```

**Expected Output:**
```
test_create_novel PASSED
test_get_novel_by_id PASSED
test_list_novels_by_user PASSED
test_update_novel PASSED
test_delete_novel PASSED
test_create_version PASSED
test_version_numbering PASSED
test_get_history PASSED
============= 8 passed in 0.12s =============
```

**Pass Criteria:** All 8 tests pass

---

### Milestone 1.2 : API Routes Core

#### Test 1.2.1 : Novel CRUD Endpoints
**Test ID:** API-001  
**Duration:** 20 min  

**Preconditions:**
- Task 1.2.1 completed
- Backend running: `poetry run python main.py`

**Test Steps Using Postman/Curl:**

**1. CREATE Novel (POST /api/novels/)**
```bash
curl -X POST http://localhost:8000/api/novels/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Fantasy Novel", "description": "A test novel"}'
```
**Expected:**
```json
{
  "id": "uuid-here",
  "title": "Test Fantasy Novel",
  "description": "A test novel",
  "status": "draft",
  "created_at": "2024-04-01T10:00:00",
  "user_id": "..."
}
```
**Note:** Save the returned `id` for next tests.

**2. LIST Novels (GET /api/novels/)**
```bash
curl http://localhost:8000/api/novels/
```
**Expected:**
```json
[
  {
    "id": "uuid-from-previous",
    "title": "Test Fantasy Novel",
    "status": "draft",
    ...
  }
]
```

**3. GET Single Novel (GET /api/novels/{id})**
```bash
curl http://localhost:8000/api/novels/uuid-from-previous
```
**Expected:**
```json
{
  "id": "uuid-from-previous",
  "title": "Test Fantasy Novel",
  ...
}
```

**4. UPDATE Novel (PUT /api/novels/{id})**
```bash
curl -X PUT http://localhost:8000/api/novels/uuid-from-previous \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "status": "in_progress"}'
```
**Expected:**
```json
{
  "id": "uuid-from-previous",
  "title": "Updated Title",
  "status": "in_progress",
  ...
}
```

**5. DELETE Novel (DELETE /api/novels/{id})**
```bash
curl -X DELETE http://localhost:8000/api/novels/uuid-from-previous
```
**Expected:**
```json
{"status": "deleted"}
```

**6. Verify Deletion (GET deleted novel)**
```bash
curl http://localhost:8000/api/novels/uuid-from-previous
```
**Expected:**
```
HTTP 404 Not Found
```

**Pass Criteria:** All 6 operations succeed with correct responses

---

#### Test 1.2.2 : Knowledge Base Endpoints
**Test ID:** API-002  
**Duration:** 20 min  

**Preconditions:**
- Test 1.2.1 passed
- Have valid novel_id from previous test
- Create new novel for this test

**Test Steps:**

**1. GET empty KB (GET /api/novels/{id}/kb/)**
```bash
# First, create a novel
curl -X POST http://localhost:8000/api/novels/ \
  -H "Content-Type: application/json" \
  -d '{"title": "KB Test Novel"}'
# Save returned id as KB_NOVEL_ID

# Get KB
curl http://localhost:8000/api/novels/$KB_NOVEL_ID/kb/
```
**Expected:**
```json
{
  "id": "uuid",
  "novel_id": "KB_NOVEL_ID",
  "universe_docs": {},
  "characters": [],
  "locations": [],
  "objects": [],
  "updated_at": "..."
}
```

**2. UPDATE Universe (PUT /api/novels/{id}/kb/universe)**
```bash
curl -X PUT http://localhost:8000/api/novels/$KB_NOVEL_ID/kb/universe \
  -H "Content-Type: application/json" \
  -d '{
    "universe_docs": {
      "magic_system": "Three tiers of elemental magic",
      "world_tech": "Medieval with steampunk elements"
    }
  }'
```
**Expected:** Updated KB with universe_docs

**3. ADD Character (POST /api/novels/{id}/kb/characters)**
```bash
curl -X POST http://localhost:8000/api/novels/$KB_NOVEL_ID/kb/characters \
  -H "Content-Type: application/json" \
  -d '{
    "id": "char_001",
    "name": "Kaelith",
    "age": 27,
    "appearance": "Black hair, gray eyes",
    "personality": ["ambitious", "impulsive"],
    "arc_narrative": "Discovers her powers",
    "role": "protagonist"
  }'
```
**Expected:** Character added to KB

**4. LIST Characters (GET /api/novels/{id}/kb/)**
```bash
curl http://localhost:8000/api/novels/$KB_NOVEL_ID/kb/
```
**Expected:** KB includes character in array

**5. UPDATE Character (PUT /api/novels/{id}/kb/characters/char_001)**
```bash
curl -X PUT http://localhost:8000/api/novels/$KB_NOVEL_ID/kb/characters/char_001 \
  -H "Content-Type: application/json" \
  -d '{
    "id": "char_001",
    "name": "Kaelith",
    "age": 28,
    "appearance": "Black hair, gray eyes with golden flecks",
    "personality": ["ambitious", "impulsive", "compassionate"],
    "arc_narrative": "Masters her powers and saves the realm",
    "role": "protagonist"
  }'
```
**Expected:** Character updated

**6. DELETE Character (DELETE /api/novels/{id}/kb/characters/char_001)**
```bash
curl -X DELETE http://localhost:8000/api/novels/$KB_NOVEL_ID/kb/characters/char_001
```
**Expected:** Character removed from KB

**Pass Criteria:** All KB operations work correctly

---

#### Test 1.2.3 : Session Management
**Test ID:** API-003  
**Duration:** 10 min  

**Preconditions:**
- Test 1.2.1 and 1.2.2 passed
- Have valid novel_id

**Test Steps:**

**1. SELECT Novel as Current (POST /api/novels/{id}/select)**
```bash
curl -X POST http://localhost:8000/api/novels/$KB_NOVEL_ID/select
```
**Expected:**
```json
{"current_novel_id": "KB_NOVEL_ID"}
```

**2. Verify in User Profile (GET /api/users/me)**
```bash
curl http://localhost:8000/api/users/me
```
**Expected:**
```json
{
  "id": "...",
  "username": "...",
  "current_novel_id": "KB_NOVEL_ID",
  ...
}
```

**3. Switch to Different Novel**
```bash
# Create another novel
curl -X POST http://localhost:8000/api/novels/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Second Novel"}'
# Save id as NOVEL_2_ID

# Switch to it
curl -X POST http://localhost:8000/api/novels/$NOVEL_2_ID/select
```
**Expected:** current_novel_id updates to NOVEL_2_ID

**Pass Criteria:** Can select and switch novels

---

### Milestone 1.3 : Context Injection System

#### Test 1.3.1 : Prompt Builder Functionality
**Test ID:** CTX-001  
**Duration:** 10 min  

**Preconditions:**
- Task 1.3.1 completed
- prompt_builder.py exists

**Test Steps:**

Create test file `backend/tests/test_prompt_builder.py`:

```python
from backend.utils.prompt_builder import PromptBuilder
from backend.database.models_storyweaver import KnowledgeBase, Novel

def test_format_universe():
    """Test universe formatting"""
    universe_docs = {
        "magic": "Three tiers",
        "tech": "Medieval"
    }
    formatted = PromptBuilder.format_universe(universe_docs)
    assert "**magic:**" in formatted.lower()
    assert "Three tiers" in formatted
    assert "**tech:**" in formatted.lower()

def test_format_characters():
    """Test character formatting"""
    characters = [
        {
            "id": "char_001",
            "name": "Kaelith",
            "age": 27,
            "role": "protagonist",
            "personality": ["ambitious", "impulsive"],
            "arc_narrative": "Discovery arc",
            "relationships": []
        },
        {
            "id": "char_002",
            "name": "Malachai",
            "age": 45,
            "role": "mentor",
            "personality": ["wise"],
            "arc_narrative": "Guides protagonist",
            "relationships": []
        }
    ]
    formatted = PromptBuilder.format_characters(characters, limit=5)
    assert "Kaelith" in formatted
    assert "Malachai" in formatted
    assert "protagonist" in formatted.lower()
    assert "mentor" in formatted.lower()

def test_build_full_prompt_minimal():
    """Test building prompt without context"""
    prompt = PromptBuilder.build_full_prompt(
        context_level="none"
    )
    assert "assistant créatif" in prompt.lower()
    assert "UNIVERS" not in prompt  # No universe section

def test_build_full_prompt_minimal_level():
    """Test building prompt with minimal context"""
    # Mock data
    universe = {"magic": "Three tiers"}
    characters = [{"name": "Kaelith"}]
    
    prompt = PromptBuilder.build_full_prompt(
        universe=universe,
        characters=characters,
        context_level="minimal"
    )
    assert "UNIVERS" in prompt
    assert "PERSONNAGES" in prompt
    # But NOT recent scenes
    assert "PASSAGES RÉCENTS" not in prompt

def test_prompt_builder_output_length():
    """Test that prompt is reasonable length"""
    prompt = PromptBuilder.build_full_prompt(context_level="none")
    assert len(prompt) > 100  # Has content
    assert len(prompt) < 10000  # Not huge
```

Run:
```bash
poetry run pytest backend/tests/test_prompt_builder.py -v
```

**Expected:** All tests pass

**Pass Criteria:** Prompt builder correctly formats all sections

---

#### Test 1.3.2 : Context Injection in Chat Route
**Test ID:** CTX-002  
**Duration:** 20 min  

**Preconditions:**
- Task 1.3.2 completed
- Backend running
- Valid novel with KB data

**Setup:**
```bash
# Create a novel with some KB data
# Store novel_id as TEST_NOVEL_ID

# Add characters
curl -X POST http://localhost:8000/api/novels/$TEST_NOVEL_ID/kb/characters \
  -H "Content-Type: application/json" \
  -d '{
    "id": "char_001",
    "name": "Kaelith",
    "age": 27,
    "appearance": "Black hair",
    "personality": ["ambitious"],
    "arc_narrative": "Power discovery",
    "role": "protagonist"
  }'

# Select novel
curl -X POST http://localhost:8000/api/novels/$TEST_NOVEL_ID/select
```

**Test Steps:**

**1. Chat WITHOUT context (no novel selected)**
```bash
# First, deselect novel (or use different user)
# Make chat request
curl -X POST http://localhost:8000/api/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      {"role": "user", "content": "Hello, tell me about Kaelith"}
    ]
  }'
```
**Expected:** Response does NOT mention KB context (generic response)

**2. Chat WITH context (novel selected)**
```bash
# Ensure novel is selected
curl -X POST http://localhost:8000/api/novels/$TEST_NOVEL_ID/select

# Make chat request
curl -X POST http://localhost:8000/api/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      {"role": "user", "content": "Tell me about Kaelith"}
    ]
  }'
```
**Expected:** Response references context (mentions Kaelith's traits from KB)

**3. Verify Context Snapshot Saved**
```bash
# Query context_snapshots table
poetry run python << 'EOF'
from backend.database.database import SessionLocal
from backend.database.models_storyweaver import ContextSnapshot
db = SessionLocal()
snapshots = db.query(ContextSnapshot).all()
print(f"Found {len(snapshots)} snapshots")
if snapshots:
    latest = snapshots[-1]
    print(f"Latest snapshot: chat_id={latest.chat_id}, novel_id={latest.novel_id}")
    print(f"Context keys: {list(latest.injected_context.keys())}")
EOF
```
**Expected:** At least one snapshot exists with injected_context data

**Pass Criteria:** Context properly injected and saved

---

### Milestone 1.4 : Frontend Integration

#### Test 1.4.1 : Novel Selector Component
**Test ID:** FE-001  
**Duration:** 15 min  

**Preconditions:**
- Task 1.4.1 completed
- Frontend dev server running: `npm run dev`
- Backend running with test novels

**Test Steps:**

1. Open browser to `http://localhost:5173`
2. Look for Novel Selector in header
   - **Expected:** Button showing "📖 Select Novel" or similar
3. Click the button
   - **Expected:** Dropdown menu appears
4. Look for "+  New Novel" button
   - **Expected:** Button visible at bottom
5. Click "+ New Novel"
   - **Expected:** Prompt asks for novel title
6. Type: "Test Novel Frontend"
   - **Expected:** Input accepted
7. Click OK/Confirm
   - **Expected:** Novel created, appears in list
8. Click the created novel
   - **Expected:** Selected, button text updates to "📖 Test Novel Frontend"
9. Refresh page (Ctrl+R)
   - **Expected:** Selection persists (stored in backend)
10. Open dropdown again
    - **Expected:** Created novel still in list
    - **Expected:** Shows status badge (e.g., "draft")

**Pass Criteria:** Create, select, and persist novel selection

---

#### Test 1.4.2 : Chat UI Integration
**Test ID:** FE-002  
**Duration:** 10 min  

**Preconditions:**
- Test 1.4.1 passed
- Novel selected

**Test Steps:**

1. Look for chat interface on screen
   - **Expected:** Message list and input visible
2. Look for info about selected novel
   - **Expected:** Maybe shows novel title near chat
3. Type message in chat: "Hi"
4. Press Enter or click Send
   - **Expected:** Message sent, appears in list as "user" message
5. Wait for response
   - **Expected:** Assistant response appears
6. Look for context indicator
   - **Expected:** Maybe shows "(🔗 Context injected)" if context was injected
7. Verify response is sensible
   - **Expected:** Response makes sense given the novel context

**Pass Criteria:** Chat UI works, messages display correctly

---

#### Test 1.4.3 : Knowledge Base Panel Placeholder
**Test ID:** FE-003  
**Duration:** 5 min  

**Preconditions:**
- Frontend dev server running
- Novel selected

**Test Steps:**

1. Look for right panel or KB section
   - **Expected:** Visible (or togglable)
2. Look for tabs: Universe, Characters, Locations, Objects
   - **Expected:** Tabs visible
3. Click each tab
   - **Expected:** Tab content changes (shows placeholder)
4. Look for text: "Knowledge Base UI coming soon" or similar
   - **Expected:** Placeholder message visible

**Pass Criteria:** KB Panel structure visible

---

### Milestone 1.5 : Testing & Polish

#### Test 1.5.1 : Unit Tests DAO
**Test ID:** TEST-001  
**Duration:** 10 min  

**Already Covered in Test 1.1.3**  
**Pass Criteria:** All 8+ DAO tests pass

---

#### Test 1.5.2 : API Integration Tests
**Test ID:** TEST-002  
**Duration:** 20 min  

**Test Steps:**

Create `backend/tests/test_api_integration.py`:

```python
from fastapi.testclient import TestClient
from backend.main import app
from uuid import uuid4

client = TestClient(app)

class TestNovelAPI:
    
    def test_create_and_list_novels(self):
        """Test creating and listing novels"""
        # Create
        response = client.post(
            "/api/novels/",
            json={"title": "Integration Test Novel"}
        )
        assert response.status_code == 200
        novel_id = response.json()["id"]
        
        # List
        response = client.get("/api/novels/")
        assert response.status_code == 200
        novels = response.json()
        assert any(n["id"] == novel_id for n in novels)
    
    def test_novel_crud_cycle(self):
        """Test full CRUD cycle"""
        # Create
        create_resp = client.post(
            "/api/novels/",
            json={"title": "CRUD Test"}
        )
        assert create_resp.status_code == 200
        novel_id = create_resp.json()["id"]
        
        # Read
        read_resp = client.get(f"/api/novels/{novel_id}")
        assert read_resp.status_code == 200
        assert read_resp.json()["title"] == "CRUD Test"
        
        # Update
        update_resp = client.put(
            f"/api/novels/{novel_id}",
            json={"title": "Updated CRUD Test"}
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "Updated CRUD Test"
        
        # Delete
        delete_resp = client.delete(f"/api/novels/{novel_id}")
        assert delete_resp.status_code == 200
        
        # Verify deleted
        get_deleted = client.get(f"/api/novels/{novel_id}")
        assert get_deleted.status_code == 404

class TestKBAPI:
    
    def test_kb_operations(self):
        """Test KB CRUD"""
        # Create novel first
        novel_resp = client.post(
            "/api/novels/",
            json={"title": "KB Test"}
        )
        novel_id = novel_resp.json()["id"]
        
        # Get KB
        kb_resp = client.get(f"/api/novels/{novel_id}/kb/")
        assert kb_resp.status_code == 200
        kb = kb_resp.json()
        assert kb["novel_id"] == novel_id
        
        # Update universe
        update_resp = client.put(
            f"/api/novels/{novel_id}/kb/universe",
            json={"universe_docs": {"magic": "Three tiers"}}
        )
        assert update_resp.status_code == 200

```

Run:
```bash
poetry run pytest backend/tests/test_api_integration.py -v
```

**Expected:** All tests pass

**Pass Criteria:** Integration tests validate full API

---

#### Test 1.5.3 : Manual QA Checklist
**Test ID:** TEST-003  
**Duration:** 30 min  

**Preconditions:**
- Backend and frontend running
- All previous tests passed

**Checklist:**

- [ ] Can create novel
- [ ] Can select novel
- [ ] Can add universe rules to KB
- [ ] Can add characters to KB
- [ ] Can update character details
- [ ] Can delete character
- [ ] Can view KB data in interface
- [ ] Chat works with novel context
- [ ] Novel selector shows created novels
- [ ] Novel status displays correctly
- [ ] Can type and send chat message
- [ ] Chat response appears
- [ ] No JavaScript errors in console
- [ ] No backend 500 errors in logs
- [ ] Database state is correct (verify with SQL if needed)
- [ ] No data loss after refresh

**Pass Criteria:** All checkboxes completed

---

### Milestone 1.6 : Deployment & Documentation

#### Test 1.6.1 : Docker Setup
**Test ID:** DEPLOY-001  
**Duration:** 20 min  

**Preconditions:**
- Docker installed
- docker-compose.yml created
- Dockerfile created

**Test Steps:**

1. Navigate to project root
2. Run: `docker-compose build`
   - **Expected:** All images build successfully
3. Run: `docker-compose up -d`
   - **Expected:** Shows "Creating container..." for each service
4. Wait 30 seconds for services to start
5. Run: `docker-compose ps`
   - **Expected:** Shows 3 containers all "Up" (storyweaver, ollama, db)
6. Test backend:
   ```bash
   curl http://localhost:8000/api/models
   ```
   - **Expected:** Returns JSON (may be empty)
7. Test frontend:
   ```bash
   curl http://localhost:5173
   ```
   - **Expected:** Returns HTML (OpenWebUI page)
8. Check logs:
   ```bash
   docker-compose logs storyweaver
   ```
   - **Expected:** Shows application startup, no major errors
9. Run: `docker-compose down`
   - **Expected:** Containers stopped and removed

**Pass Criteria:** Docker setup works end-to-end

---

#### Test 1.6.2 : Documentation
**Test ID:** DEPLOY-002  
**Duration:** 10 min  

**Preconditions:**
- DEVELOPMENT.md created
- DEPLOYMENT.md created
- API.md created

**Test Steps:**

1. Read `DEVELOPMENT.md`
   - [ ] Has "Quick Start" section
   - [ ] Has database setup instructions
   - [ ] Has testing instructions
   - [ ] Has deployment instructions
2. Read `DEPLOYMENT.md`
   - [ ] Has VPS setup steps
   - [ ] Has environment variable list
   - [ ] Has troubleshooting section
3. Try following "Quick Start" from scratch
   - [ ] Can clone repo
   - [ ] Can install dependencies
   - [ ] Can start backend
   - [ ] Can start frontend
4. Check API.md
   - [ ] Documents all endpoints
   - [ ] Has request/response examples
   - [ ] Has error codes

**Pass Criteria:** Documentation is clear and comprehensive

---

## PHASE 2 : KNOWLEDGE BASE EDITOR TESTING

### Milestone 2.1 : KB UI Components

#### Test 2.1.1 : Universe Editor
**Test ID:** KB-UI-001  
**Duration:** 15 min  

**Preconditions:**
- Phase 1 complete
- Task 2.1.1 completed
- Frontend running

**Test Steps:**

1. Create novel via UI
2. Select novel
3. Look for Knowledge Base panel (right side or separate)
4. Click "Universe" tab
5. In editor, add JSON:
```json
{
  "magic_system": "Three tiers of elemental magic: Air, Water, Earth",
  "technology": "Medieval with some steampunk",
  "world_rules": "Magic users are rare and feared"
}
```
6. Click "Save" button
   - **Expected:** Data saved, no errors
7. Refresh page
   - **Expected:** Universe data persists
8. Edit and change magic_system value
9. Click Save
10. Verify in backend:
```bash
curl http://localhost:8000/api/novels/$NOVEL_ID/kb/ | jq '.universe_docs'
```
   - **Expected:** Shows updated value

**Pass Criteria:** Universe editor saves and persists data

---

#### Test 2.1.2 : Character Manager
**Test ID:** KB-UI-002  
**Duration:** 20 min  

**Preconditions:**
- Test 2.1.1 passed
- Novel selected

**Test Steps:**

1. Click "Characters" tab in KB panel
2. Look for character list (empty initially)
3. Click "+ Add Character" button
4. Fill in form:
   - Name: "Kaelith"
   - Age: "27"
   - Appearance: "Black hair, gray eyes"
   - Personality: Select "ambitious", "impulsive", "loyal"
   - Arc: "Discovers magical powers and learns to control them"
   - Role: "protagonist"
5. Click "Save"
   - **Expected:** Character appears in list
6. Click character in list
   - **Expected:** Form populates with saved data
7. Change age to "28"
8. Click "Save"
   - **Expected:** Character updates
9. Click "Delete"
   - **Expected:** Character removed
10. Add character again
11. Verify in backend:
```bash
curl http://localhost:8000/api/novels/$NOVEL_ID/kb/ | jq '.characters'
```
   - **Expected:** Shows character array

**Pass Criteria:** Full character CRUD in UI

---

#### Test 2.1.3 : Location Manager
**Test ID:** KB-UI-003  
**Duration:** 15 min  

**Preconditions:**
- Test 2.1.2 passed

**Test Steps:**

1. Click "Locations" tab
2. Click "+ Add Location"
3. Fill form (similar to characters):
   - Name: "Crystalholm"
   - Description: "Ancient city of crystal towers"
   - Significance: "High"
4. Save
   - **Expected:** Appears in list
5. Add 2 more locations
6. Verify list shows all 3
7. Update one
8. Delete one
   - **Expected:** List shows 2 remaining

**Pass Criteria:** Location CRUD works

---

#### Test 2.1.4 : Object Manager
**Test ID:** KB-UI-004  
**Duration:** 15 min  

**Preconditions:**
- Test 2.1.3 passed

**Test Steps:**

1. Click "Objects" tab
2. Add objects (similar pattern):
   - Amulet of Power
   - Ancient Tome
   - Crystal Orb
3. Verify all saved and listable
4. Update and delete work

**Pass Criteria:** Object CRUD works

---

### Milestone 2.2 : Versioning

#### Test 2.2.1 : Version History Display
**Test ID:** VER-001  
**Duration:** 15 min  

**Preconditions:**
- Test 2.1.2 passed (character created and updated)

**Test Steps:**

1. In Character Manager, select a character
2. Look for "Version History" button or link
3. Click it
   - **Expected:** Modal/panel shows version timeline
4. Verify timeline shows:
   - [ ] "created" version (initial)
   - [ ] "updated" version (if edited)
   - [ ] Timestamps for each
5. Click on a version
   - **Expected:** Shows old data vs new data
6. If "revert" option exists, click it for non-current version
   - **Expected:** Character reverts to that version, new version record created

**Pass Criteria:** Version history is visible and revertible

---

### Milestone 2.3 : Search

#### Test 2.3.1 : Full-Text Search KB
**Test ID:** SEARCH-001  
**Duration:** 10 min  

**Preconditions:**
- 3+ characters, locations, objects added
- Novel with KB data

**Test Steps:**

1. In KB panel, look for search box
2. Type search query: "crystal"
   - **Expected:** Results show items with "crystal" in name/description
3. Search for character name: "kaelith"
   - **Expected:** Character appears in results
4. Search for non-existent: "xyz123"
   - **Expected:** No results

**Pass Criteria:** Search works correctly

---

## PHASE 3 : CUSTOM TOOLS TESTING

### Milestone 3.1 : Tools Implementation

#### Test 3.1.1 : Brainstorm Tool
**Test ID:** TOOL-001  
**Duration:** 15 min  

**Preconditions:**
- Phase 2 complete
- Novel with KB data
- Backend running

**Test Steps:**

1. In chat, look for Tools toolbar (buttons)
2. Click "💭 Brainstorm" button
   - **Expected:** Inserts "/brainstorm " in chat input
3. Complete: "/brainstorm dark twist in plot"
4. Send
   - **Expected:** Response shows 3-5 creative ideas
5. Verify ideas are:
   - [ ] Related to the theme ("dark twist")
   - [ ] Consider the novel's universe
   - [ ] Consider main characters

**Pass Criteria:** Brainstorm generates relevant ideas

---

#### Test 3.1.2 : Analyze Tool
**Test ID:** TOOL-002  
**Duration:** 15 min  

**Preconditions:**
- Test 3.1.1 passed
- Manuscript content available

**Test Steps:**

1. Type/paste a passage in manuscript editor
2. Click "Check Coherence" or use "/analyze"
3. Provide some text with potential issues:
   - Wrong character name
   - Timeline inconsistency
4. Send
   - **Expected:** Response lists issues found
   - **Expected:** Coherence score shown

**Pass Criteria:** Analyze detects inconsistencies

---

#### Test 3.1.3 : Dialogue Generator
**Test ID:** TOOL-003  
**Duration:** 10 min  

**Preconditions:**
- 2+ characters in KB

**Test Steps:**

1. Use "/dialogue Kaelith Malachai discussing the prophecy"
2. Send
   - **Expected:** Dialogue appears
   - **Expected:** Follows character voices from KB

**Pass Criteria:** Dialogue generated coherently

---

#### Test 3.1.4 : Outline Generator
**Test ID:** TOOL-004  
**Duration:** 15 min  

**Preconditions:**
- Novel with KB (universe, characters)

**Test Steps:**

1. Use "/outline three-act"
2. Send
   - **Expected:** Shows 3-act structure
   - **Expected:** Chapters with narrative keys
3. Try "/outline five-act"
   - **Expected:** 5-act structure

**Pass Criteria:** Outline generation works

---

## PHASE 4 : MANUSCRIPT EDITOR TESTING

### Milestone 4.1 : Manuscript Editor

#### Test 4.1.1 : Manuscript Editing
**Test ID:** MANU-001  
**Duration:** 20 min  

**Preconditions:**
- Phase 3 complete
- Novel selected

**Test Steps:**

1. Look for Manuscript Editor (center panel)
2. Verify empty initially
3. Type opening passage:
```
The morning mist clung to the valley as Kaelith approached the ancient 
ruins. She had waited seven years for this moment, ever since the 
prophecy spoke her name.
```
4. Verify word count updates
   - **Expected:** Shows "~35 words" or similar
5. Look for Chapter selector
6. Select or create "Chapter 1"
7. Look for Status selector (draft/editing/final)
8. Select "draft"
   - **Expected:** Status saved
9. Refresh page
   - **Expected:** Content persists
10. Verify in backend:
```bash
curl http://localhost:8000/api/novels/$NOVEL_ID/manuscript
```
   - **Expected:** Content matches what you typed

**Pass Criteria:** Manuscript editor stores content

---

#### Test 4.1.2 : Quick Action Buttons
**Test ID:** MANU-002  
**Duration:** 15 min  

**Preconditions:**
- Test 4.1.1 passed
- Manuscript with content

**Test Steps:**

1. Select text in editor
2. Right-click or look for quick action buttons
3. Click "Analyze This Passage"
   - **Expected:** Chat opens with analysis
4. Click "Continue Scene"
   - **Expected:** Chat suggests continuations
5. Click "Generate Dialogue"
   - **Expected:** Chat generates dialogue

**Pass Criteria:** Quick actions work and launch tools

---

### Milestone 4.3 : Export

#### Test 4.3.1 : Export Formats
**Test ID:** EXPORT-001  
**Duration:** 15 min  

**Preconditions:**
- Manuscript with content

**Test Steps:**

1. Look for "Export" button/menu
2. Click Export -> Markdown
   - **Expected:** File downloads (.md)
   - **Expected:** Verify content is correct
3. Click Export -> PDF
   - **Expected:** File downloads (.pdf)
   - **Expected:** PDF is readable
4. Click Export -> Text
   - **Expected:** File downloads (.txt)

**Pass Criteria:** Export works for all formats

---

## FINAL VALIDATION

### Test FINAL-001 : Complete End-to-End Workflow
**Test ID:** FINAL-001  
**Duration:** 60 min  

**Preconditions:**
- Entire system running

**Scenario:** Create a complete novel from scratch

**Steps:**

1. **Setup**
   - [ ] Create new novel "Quest for the Crystal"
   - [ ] Select it as current

2. **Build Univers**
   - [ ] Add universe rules (magic system, world tech)
   - [ ] Add locations (3+)

3. **Create Characters**
   - [ ] Add protagonist Kaelith
   - [ ] Add mentor Malachai
   - [ ] Add antagonist Sulfros
   - [ ] Link relationships

4. **Write Manuscript**
   - [ ] Write opening (2-3 paragraphs)
   - [ ] Write scene 1 (3-4 paragraphs)
   - [ ] Use quick actions to analyze

5. **Use Tools**
   - [ ] Brainstorm next plot point
   - [ ] Generate dialogue between characters
   - [ ] Create outline (3-act)
   - [ ] Check coherence

6. **Polish**
   - [ ] Review KB data
   - [ ] Check version history
   - [ ] Export to PDF
   - [ ] Verify PDF content

7. **Verify Data Integrity**
   - [ ] Stop backend
   - [ ] Start backend
   - [ ] Novel still exists
   - [ ] Content still there
   - [ ] All KB data intact

**Pass Criteria:** Complete novel workflow successful end-to-end

---

## TEST EXECUTION MATRIX

| Phase | # Tests | Duration | Pass/Fail |
|-------|---------|----------|-----------|
| Phase 1 | 15+ | 3 hrs | ___/___  |
| Phase 2 | 8+ | 2 hrs | ___/___  |
| Phase 3 | 5+ | 1 hr | ___/___  |
| Phase 4 | 5+ | 1.5 hrs | ___/___  |
| **TOTAL** | **33+** | **7.5 hrs** | ___/___  |

---

## HOW TO USE THIS CHECKLIST

1. **Print or digital copy** - Use as you code
2. **Check off each test** - As you complete
3. **Log failures** - Note bugs and fixes
4. **Prioritize P1** - Critical path tests first
5. **Parallel testing** - Can test UI while backend code
6. **Automated testing** - Add to CI/CD pipeline

---

**Next: Start Phase 1, Test 1.0.1 ! ✅**
