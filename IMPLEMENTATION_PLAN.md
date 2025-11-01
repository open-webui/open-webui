# Open WebUI Automation Enhancements - Implementation Plan

**Date**: November 1, 2025
**Project**: Open WebUI Automation Suite
**Features**: N8N Pipeline, Auto Memory, AutoTool Filter

---

## 1. N8N Pipeline Integration (PIPE v2.2.0)

### Overview
External pipeline service that connects Open WebUI to N8N workflows for end-to-end automation.

### Architecture
- **Type**: External Pipeline (OpenAI-compatible proxy)
- **Communication**: HTTP REST API with SSE (Server-Sent Events)
- **Authentication**: API Key + OAuth2 (configurable)
- **Data Flow**: Open WebUI → N8N Webhook → N8N Workflow → Response

### Implementation Components

#### A. Database Model
**File**: `backend/open_webui/models/n8n_config.py`

```python
from sqlalchemy import Column, String, Integer, Boolean, JSON, Text
from open_webui.internal.db import Base
from pydantic import BaseModel

class N8NConfig(Base):
    __tablename__ = "n8n_config"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    n8n_url = Column(String, nullable=False)  # N8N instance URL
    webhook_id = Column(String, nullable=False)  # N8N webhook ID
    api_key = Column(String, nullable=True)  # Optional API key
    is_active = Column(Boolean, default=True)
    is_streaming = Column(Boolean, default=True)
    timeout_seconds = Column(Integer, default=120)
    retry_config = Column(JSON, default={"max_retries": 3, "backoff": 2})
    metadata = Column(JSON, default={})
    created_at = Column(Integer)
    updated_at = Column(Integer)

class N8NWorkflowExecution(Base):
    __tablename__ = "n8n_executions"

    id = Column(String, primary_key=True)
    config_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    prompt = Column(Text)
    response = Column(Text)
    status = Column(String)  # pending, success, failed, timeout
    duration_ms = Column(Integer)
    error_message = Column(Text, nullable=True)
    created_at = Column(Integer)
```

#### B. API Router
**File**: `backend/open_webui/routers/n8n_integration.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.utils.auth import get_verified_user
from open_webui.models.n8n_config import N8NConfig, N8NWorkflowExecution
import httpx
import asyncio
from typing import AsyncGenerator

router = APIRouter()

# Endpoints:
# POST   /api/n8n/config         - Create N8N configuration
# GET    /api/n8n/configs        - List user's N8N configs
# PUT    /api/n8n/config/{id}    - Update configuration
# DELETE /api/n8n/config/{id}    - Delete configuration
# POST   /api/n8n/trigger/{id}   - Trigger workflow (with SSE streaming)
# GET    /api/n8n/executions     - Query execution history

@router.post("/trigger/{config_id}")
async def trigger_n8n_workflow(
    config_id: str,
    payload: dict,
    user=Depends(get_verified_user)
):
    """
    Trigger N8N workflow with Server-Sent Events streaming
    """
    config = N8NConfig.get_by_id(config_id)
    if not config or config.user_id != user.id:
        raise HTTPException(status_code=404, detail="Config not found")

    webhook_url = f"{config.n8n_url}/webhook/{config.webhook_id}"

    async def event_stream() -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                webhook_url,
                json=payload,
                timeout=config.timeout_seconds
            ) as response:
                async for chunk in response.aiter_text():
                    yield f"data: {chunk}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

#### C. Migration Script
**File**: `backend/open_webui/migrations/versions/xxx_add_n8n_integration.py`

```python
def upgrade():
    op.create_table(
        'n8n_config',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('n8n_url', sa.String(), nullable=False),
        sa.Column('webhook_id', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_streaming', sa.Boolean(), default=True),
        sa.Column('timeout_seconds', sa.Integer(), default=120),
        sa.Column('retry_config', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.Integer()),
        sa.Column('updated_at', sa.Integer()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'n8n_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('prompt', sa.Text()),
        sa.Column('response', sa.Text()),
        sa.Column('status', sa.String()),
        sa.Column('duration_ms', sa.Integer()),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Integer()),
        sa.PrimaryKeyConstraint('id')
    )
```

---

## 2. Auto Memory Plugin

### Overview
Outlet filter that automatically extracts facts, preferences, and entities from conversations and stores them in the memory system.

### Architecture
- **Type**: Outlet Filter (Function)
- **Processing**: Named Entity Recognition (NER) with Spacy
- **Storage**: ChromaDB vector embeddings + metadata
- **Activation**: Automatic on every LLM response

### Implementation

**File**: `backend/open_webui/functions/auto_memory.py`

```python
"""
title: Auto Memory
description: Automatically extract and store conversation facts
author: open-webui
version: 1.0.0
requirements: spacy,nltk
"""

from typing import Optional
from pydantic import BaseModel
import spacy
import time
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

class Filter:
    class Valves(BaseModel):
        enabled: bool = True
        min_confidence: float = 0.7
        memory_types: list[str] = ["PERSON", "ORG", "DATE", "PREFERENCE", "FACT"]

    def __init__(self):
        self.valves = self.Valves()
        self.nlp = None

    def _load_nlp(self):
        """Lazy load Spacy model"""
        if self.nlp is None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Auto-download if not installed
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
                self.nlp = spacy.load("en_core_web_sm")

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        Process LLM response and extract memories
        """
        if not self.valves.enabled or not user:
            return body

        self._load_nlp()

        # Extract last assistant message
        messages = body.get("messages", [])
        if not messages or messages[-1].get("role") != "assistant":
            return body

        content = messages[-1].get("content", "")

        # Named Entity Recognition
        doc = self.nlp(content)
        memories = []

        for ent in doc.ents:
            if ent.label_ in self.valves.memory_types:
                memory_text = f"{ent.label_}: {ent.text} (Context: {ent.sent.text})"
                memories.append({
                    "text": memory_text,
                    "type": ent.label_,
                    "entity": ent.text,
                    "confidence": 0.9,  # Spacy confidence
                    "timestamp": int(time.time())
                })

        # Store in ChromaDB
        if memories:
            collection_name = f"user-memory-{user['id']}"

            for memory in memories:
                VECTOR_DB_CLIENT.insert(
                    collection_name=collection_name,
                    documents=[memory["text"]],
                    metadatas=[{
                        "type": memory["type"],
                        "entity": memory["entity"],
                        "source": "auto_memory",
                        "timestamp": memory["timestamp"]
                    }]
                )

        # Add metadata to response
        body["__metadata__"] = body.get("__metadata__", {})
        body["__metadata__"]["auto_memory"] = {
            "extracted": len(memories),
            "types": list(set([m["type"] for m in memories]))
        }

        return body
```

---

## 3. AutoTool Filter

### Overview
Inlet filter that analyzes user queries and automatically suggests/selects the most relevant tools using semantic similarity.

### Architecture
- **Type**: Inlet Filter (Function)
- **Processing**: Sentence embeddings with sentence-transformers
- **Scoring**: Cosine similarity between query and tool descriptions
- **Activation**: Pre-processes every user message

### Implementation

**File**: `backend/open_webui/functions/auto_tool_filter.py`

```python
"""
title: AutoTool Filter
description: Automatically suggest relevant tools for user queries
author: open-webui
version: 1.0.0
requirements: sentence-transformers,numpy,scikit-learn
"""

from typing import Optional
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from open_webui.models.tools import Tools

class Filter:
    class Valves(BaseModel):
        enabled: bool = True
        auto_select: bool = False  # Auto-inject tools or just suggest
        top_k: int = 3
        similarity_threshold: float = 0.5

    def __init__(self):
        self.valves = self.Valves()
        self.model = None
        self.tool_cache = {}

    def _load_model(self):
        """Lazy load embedding model"""
        if self.model is None:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        Analyze query and suggest relevant tools
        """
        if not self.valves.enabled or not user:
            return body

        self._load_model()

        # Extract user query
        messages = body.get("messages", [])
        if not messages or messages[-1].get("role") != "user":
            return body

        query = messages[-1].get("content", "")

        # Get available tools
        user_tools = Tools.get_tools_by_user_id(user["id"])
        global_tools = Tools.get_global_tools()
        all_tools = user_tools + global_tools

        if not all_tools:
            return body

        # Generate embeddings
        query_embedding = self.model.encode([query])

        tool_scores = []
        for tool in all_tools:
            # Cache tool embeddings
            tool_id = tool.id
            if tool_id not in self.tool_cache:
                tool_desc = f"{tool.name}: {tool.meta.get('description', '')}"
                self.tool_cache[tool_id] = self.model.encode([tool_desc])

            tool_embedding = self.tool_cache[tool_id]

            # Cosine similarity
            similarity = cosine_similarity(query_embedding, tool_embedding)[0][0]

            if similarity >= self.valves.similarity_threshold:
                tool_scores.append({
                    "tool_id": tool.id,
                    "name": tool.name,
                    "score": float(similarity),
                    "spec": tool.specs[0] if tool.specs else None
                })

        # Sort by score
        tool_scores.sort(key=lambda x: x["score"], reverse=True)
        top_tools = tool_scores[:self.valves.top_k]

        if self.valves.auto_select and top_tools:
            # Auto-inject tools into request
            body["tools"] = [t["spec"] for t in top_tools if t["spec"]]

        # Add suggestions to metadata
        body["__metadata__"] = body.get("__metadata__", {})
        body["__metadata__"]["tool_suggestions"] = [
            {"name": t["name"], "score": t["score"]}
            for t in top_tools
        ]

        return body
```

---

## Testing Strategy

### Test Files

#### 1. N8N Integration Tests
**File**: `tests/integration/test_n8n_integration.py`

```python
import pytest
import httpx
from open_webui.models.n8n_config import N8NConfig

@pytest.mark.asyncio
async def test_n8n_config_creation(test_user):
    """Test creating N8N configuration"""
    config_data = {
        "name": "Test Workflow",
        "n8n_url": "http://localhost:5678",
        "webhook_id": "test-webhook-123",
        "is_streaming": True
    }

    config = await N8NConfig.create(user_id=test_user.id, **config_data)
    assert config.name == "Test Workflow"
    assert config.is_active is True

@pytest.mark.asyncio
async def test_n8n_workflow_trigger():
    """Test workflow triggering with mock N8N server"""
    # Use respx to mock N8N server
    pass

@pytest.mark.asyncio
async def test_n8n_sse_streaming():
    """Test Server-Sent Events streaming"""
    pass
```

#### 2. Auto Memory Tests
**File**: `tests/test_auto_memory_function.py`

```python
import pytest
from open_webui.functions.auto_memory import Filter

@pytest.fixture
def auto_memory_filter():
    return Filter()

@pytest.mark.asyncio
async def test_entity_extraction(auto_memory_filter):
    """Test NER extraction from conversation"""
    body = {
        "messages": [
            {"role": "assistant", "content": "Nice to meet you, John! I see you work at Google."}
        ]
    }
    user = {"id": "test-user-123"}

    result = await auto_memory_filter.outlet(body, user)

    metadata = result.get("__metadata__", {}).get("auto_memory", {})
    assert metadata["extracted"] >= 2  # Should extract "John" (PERSON) and "Google" (ORG)

@pytest.mark.asyncio
async def test_memory_storage(auto_memory_filter, chroma_db_client):
    """Test ChromaDB storage"""
    # Verify memories are stored with correct metadata
    pass
```

#### 3. AutoTool Filter Tests
**File**: `tests/test_auto_tool_filter.py`

```python
import pytest
from open_webui.functions.auto_tool_filter import Filter

@pytest.fixture
def autotool_filter():
    return Filter()

@pytest.mark.asyncio
async def test_tool_matching(autotool_filter, sample_tools):
    """Test semantic tool matching"""
    body = {
        "messages": [
            {"role": "user", "content": "What's the weather in Paris?"}
        ]
    }
    user = {"id": "test-user-123"}

    result = await autotool_filter.inlet(body, user)

    suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

    # Should suggest weather tool with high score
    assert len(suggestions) > 0
    assert any("weather" in s["name"].lower() for s in suggestions)
    assert suggestions[0]["score"] > 0.5

@pytest.mark.asyncio
async def test_auto_injection(autotool_filter):
    """Test automatic tool injection"""
    autotool_filter.valves.auto_select = True
    # Test that tools are auto-injected into body["tools"]
    pass
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Run all tests: `pytest tests/ -v`
- [ ] Lint code: `black . && ruff check .`
- [ ] Security scan: `bandit -r backend/`
- [ ] Update requirements.txt with new dependencies
- [ ] Create database migration scripts
- [ ] Update environment variables documentation

### Dependencies to Add

```txt
# requirements.txt additions
spacy>=3.7.0
sentence-transformers>=2.2.0
scikit-learn>=1.3.0
nltk>=3.8.0
httpx>=0.25.0
```

### Environment Variables

```bash
# .env additions
N8N_DEFAULT_URL=http://localhost:5678
N8N_API_KEY=your-n8n-api-key
AUTO_MEMORY_ENABLED=true
AUTOTOOL_FILTER_ENABLED=true
```

### Migration Commands

```bash
# Initialize Spacy model
python -m spacy download en_core_web_sm

# Run database migrations
alembic upgrade head

# Download sentence-transformers model (first run)
# Happens automatically on first use
```

---

## Timeline Estimate

**Total Duration**: 4-5 weeks

### Week 1: Foundation
- Set up development environment
- Create database models and migrations
- Write test infrastructure

### Week 2: N8N Integration
- Implement N8N router and models
- Build SSE streaming support
- Write integration tests

### Week 3: Auto Memory + AutoTool
- Implement Auto Memory outlet filter
- Implement AutoTool inlet filter
- Write function tests

### Week 4: Integration & Testing
- End-to-end testing
- Performance optimization
- Documentation

### Week 5: Deployment & Monitoring
- Production deployment
- Monitoring setup
- User training

---

## Success Metrics

### N8N Integration
- [ ] Successfully trigger workflows with <2s latency
- [ ] SSE streaming with 99.9% delivery rate
- [ ] Handle 100+ concurrent workflow executions

### Auto Memory
- [ ] Extract entities with >85% accuracy
- [ ] Store 1000+ memories without performance degradation
- [ ] Memory retrieval latency <100ms

### AutoTool Filter
- [ ] Tool suggestions with >75% user acceptance
- [ ] Similarity scoring <50ms per query
- [ ] Support 100+ tools without performance issues

---

**Plan Complete - Ready for Implementation**
