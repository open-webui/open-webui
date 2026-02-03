# Directive: Adding a New API Router

> **Pattern type:** Backend feature addition
> **Complexity:** Low-Medium
> **Files touched:** 2-3

---

## Prerequisites

- `ARCHITECTURE_OVERVIEW.md` — Understanding of backend structure
- `ADR_001_fastapi_backend.md` — FastAPI patterns

---

## Structural Pattern

When adding new API functionality to Open WebUI, create a dedicated router module that:

1. **Defines its own `APIRouter`** with a logical prefix
2. **Uses dependency injection** for authentication and database access
3. **Defines Pydantic models** for request/response validation
4. **Registers with the main application** in `main.py`

| Component | Location | Purpose |
|-----------|----------|---------|
| Router module | `backend/open_webui/routers/{feature}.py` | API endpoints |
| Registration | `backend/open_webui/main.py` | Mount router to app |
| Models (optional) | `backend/open_webui/models/{feature}.py` | Database entities |

This separation enables:
- **Testability:** Routers can be tested in isolation
- **Maintainability:** Feature code is contained
- **Documentation:** Auto-generated OpenAPI docs per router

---

## Illustrative Application

The analytics router (`backend/open_webui/routers/analytics.py`) demonstrates this pattern:

### Step 1: Create Router Module

```python
# backend/open_webui/routers/analytics.py
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from open_webui.utils.auth import get_admin_user
from open_webui.internal.db import get_session
from open_webui.models.users import UserModel

router = APIRouter()


# Response models
class SummaryResponse(BaseModel):
    total_messages: int
    total_tokens: int
    active_users: int


class ModelAnalytics(BaseModel):
    model_id: str
    message_count: int
    token_count: int


class ModelAnalyticsResponse(BaseModel):
    models: List[ModelAnalytics]


# Endpoints
@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    start_date: Optional[int] = Query(None, description="Start timestamp"),
    end_date: Optional[int] = Query(None, description="End timestamp"),
    user: UserModel = Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """
    Get aggregate analytics summary.

    Requires admin role.
    """
    # Implementation
    return SummaryResponse(
        total_messages=100,
        total_tokens=50000,
        active_users=10,
    )


@router.get("/models", response_model=ModelAnalyticsResponse)
async def get_model_analytics(
    start_date: Optional[int] = Query(None),
    end_date: Optional[int] = Query(None),
    user: UserModel = Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get per-model analytics."""
    # Implementation
    return ModelAnalyticsResponse(models=[])
```

### Step 2: Register Router in Main

```python
# backend/open_webui/main.py

from open_webui.routers import analytics  # Add import

# ... existing code ...

# Register router (around line 1437)
app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["analytics"]
)
```

### Step 3: Verify Registration

After adding the router:

1. Start the development server
2. Navigate to `/docs` (Swagger UI)
3. Find your new endpoints under the "analytics" tag
4. Test endpoints directly in Swagger

---

## Transfer Prompt

**When you need to add new API endpoints:**

1. **Create router file:** `backend/open_webui/routers/{feature_name}.py`

   ```python
   from fastapi import APIRouter, Depends
   from open_webui.utils.auth import get_verified_user  # or get_admin_user
   from open_webui.internal.db import get_session

   router = APIRouter()

   @router.get("/endpoint")
   async def my_endpoint(user=Depends(get_verified_user)):
       return {"message": "success"}
   ```

2. **Define response models** above endpoints using Pydantic `BaseModel`

3. **Choose authentication dependency:**
   - `get_current_user` — Optional auth (returns None if not logged in)
   - `get_verified_user` — Required auth (401 if not logged in)
   - `get_admin_user` — Admin only (403 if not admin)

4. **Add database access** if needed:
   ```python
   from open_webui.internal.db import get_session
   from sqlalchemy.orm import Session

   @router.get("/data")
   async def get_data(db: Session = Depends(get_session)):
       # Use db for queries
   ```

5. **Register in main.py:**
   ```python
   from open_webui.routers import {feature_name}

   app.include_router(
       {feature_name}.router,
       prefix="/api/v1/{feature_name}",
       tags=["{feature_name}"]
   )
   ```

6. **Test via Swagger** at `/docs`

**Signals that this pattern applies:**
- Need new backend functionality
- Adding CRUD operations for a feature
- Creating admin-only endpoints
- Exposing new data to the frontend

---

## Related Documents

- `ADR_001_fastapi_backend.md` — Why FastAPI
- `DIRECTIVE_database_migration.md` — If you need new tables
- `DIRECTIVE_adding_frontend_api.md` — Frontend client for your API

---

*Last updated: 2026-02-03*
