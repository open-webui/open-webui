# Directive: Adding Admin Features

> **Pattern type:** Administrative functionality
> **Complexity:** Medium
> **Files touched:** 3-5

---

## Prerequisites

- `DIRECTIVE_adding_api_router.md` — Basic router pattern
- `DOMAIN_GLOSSARY.md` — Role, Access Control terms

---

## Structural Pattern

When adding admin-only functionality:

1. **Protect backend routes** with `get_admin_user` dependency
2. **Add configuration endpoints** for admin settings
3. **Create admin UI components** in admin routes
4. **Check role in frontend** before showing UI

| Component | Location | Purpose |
|-----------|----------|---------|
| Backend routes | `backend/open_webui/routers/{feature}.py` | Admin endpoints |
| Admin check | `backend/open_webui/utils/auth.py` | `get_admin_user` |
| Frontend routes | `src/routes/(app)/admin/` | Admin pages |
| Role check | `src/lib/stores/index.ts` | User role state |

---

## Illustrative Application

The analytics admin feature demonstrates this pattern:

### Step 1: Create Admin-Protected Endpoints

```python
# backend/open_webui/routers/admin_feature.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from open_webui.utils.auth import get_admin_user
from open_webui.internal.db import get_session
from open_webui.models.users import UserModel

router = APIRouter()


class FeatureConfig(BaseModel):
    enabled: bool
    max_items: int
    allowed_domains: list[str]


class FeatureStats(BaseModel):
    total_usage: int
    active_users: int
    items_created: int


# Admin-only endpoint
@router.get("/config", response_model=FeatureConfig)
async def get_feature_config(
    request: Request,
    user: UserModel = Depends(get_admin_user),  # Admin required
):
    """Get feature configuration (admin only)."""
    return FeatureConfig(
        enabled=request.app.state.config.FEATURE_ENABLED,
        max_items=request.app.state.config.FEATURE_MAX_ITEMS,
        allowed_domains=request.app.state.config.FEATURE_DOMAINS,
    )


@router.post("/config", response_model=FeatureConfig)
async def update_feature_config(
    request: Request,
    body: FeatureConfig,
    user: UserModel = Depends(get_admin_user),
):
    """Update feature configuration (admin only)."""
    # Update runtime config
    request.app.state.config.FEATURE_ENABLED = body.enabled
    request.app.state.config.FEATURE_MAX_ITEMS = body.max_items
    request.app.state.config.FEATURE_DOMAINS = body.allowed_domains

    # Optionally persist to database
    # save_config_to_db(body)

    return body


@router.get("/stats", response_model=FeatureStats)
async def get_feature_stats(
    user: UserModel = Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get feature usage statistics (admin only)."""
    return FeatureStats(
        total_usage=1000,
        active_users=50,
        items_created=500,
    )


# Admin action on user resources
@router.delete("/users/{user_id}/data")
async def delete_user_feature_data(
    user_id: str,
    admin: UserModel = Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Delete a user's feature data (admin only)."""
    # Check user exists
    target_user = Users.get_user_by_id(user_id, db=db)
    if not target_user:
        raise HTTPException(404, "User not found")

    # Delete data
    Features.delete_by_user(user_id, db=db)

    return {"status": "deleted", "user_id": user_id}
```

### Step 2: Register Router

```python
# backend/open_webui/main.py
from open_webui.routers import admin_feature

app.include_router(
    admin_feature.router,
    prefix="/api/v1/admin/feature",
    tags=["admin:feature"]
)
```

### Step 3: Create Admin UI Route

```svelte
<!-- src/routes/(app)/admin/feature/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { user } from '$lib/stores';
  import { goto } from '$app/navigation';

  interface FeatureConfig {
    enabled: boolean;
    max_items: number;
    allowed_domains: string[];
  }

  interface FeatureStats {
    total_usage: number;
    active_users: number;
    items_created: number;
  }

  let config: FeatureConfig | null = null;
  let stats: FeatureStats | null = null;
  let loading = true;
  let saving = false;

  onMount(async () => {
    // Check admin access
    if ($user?.role !== 'admin') {
      goto('/');
      return;
    }

    await loadData();
  });

  async function loadData() {
    loading = true;
    try {
      const [configRes, statsRes] = await Promise.all([
        fetch('/api/v1/admin/feature/config', {
          headers: { Authorization: `Bearer ${$user.token}` }
        }),
        fetch('/api/v1/admin/feature/stats', {
          headers: { Authorization: `Bearer ${$user.token}` }
        })
      ]);

      config = await configRes.json();
      stats = await statsRes.json();
    } catch (e) {
      console.error('Failed to load admin data:', e);
    } finally {
      loading = false;
    }
  }

  async function saveConfig() {
    saving = true;
    try {
      await fetch('/api/v1/admin/feature/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${$user.token}`
        },
        body: JSON.stringify(config)
      });
    } catch (e) {
      console.error('Failed to save config:', e);
    } finally {
      saving = false;
    }
  }
</script>

<div class="admin-page">
  <h1>Feature Administration</h1>

  {#if loading}
    <p>Loading...</p>
  {:else}
    <!-- Stats Section -->
    <section class="stats">
      <h2>Statistics</h2>
      <div class="stat-grid">
        <div class="stat">
          <span class="value">{stats?.total_usage ?? 0}</span>
          <span class="label">Total Usage</span>
        </div>
        <div class="stat">
          <span class="value">{stats?.active_users ?? 0}</span>
          <span class="label">Active Users</span>
        </div>
        <div class="stat">
          <span class="value">{stats?.items_created ?? 0}</span>
          <span class="label">Items Created</span>
        </div>
      </div>
    </section>

    <!-- Config Section -->
    <section class="config">
      <h2>Configuration</h2>

      <label>
        <input type="checkbox" bind:checked={config.enabled} />
        Feature Enabled
      </label>

      <label>
        Max Items
        <input type="number" bind:value={config.max_items} />
      </label>

      <label>
        Allowed Domains (comma-separated)
        <input
          type="text"
          value={config.allowed_domains.join(', ')}
          on:change={(e) => {
            config.allowed_domains = e.target.value.split(',').map(d => d.trim());
          }}
        />
      </label>

      <button on:click={saveConfig} disabled={saving}>
        {saving ? 'Saving...' : 'Save Configuration'}
      </button>
    </section>
  {/if}
</div>
```

### Step 4: Add Admin Navigation

```svelte
<!-- src/lib/components/admin/AdminSidebar.svelte -->
<script>
  import { user } from '$lib/stores';
</script>

{#if $user?.role === 'admin'}
  <nav class="admin-nav">
    <a href="/admin">Dashboard</a>
    <a href="/admin/users">Users</a>
    <a href="/admin/feature">Feature Settings</a>
    <!-- Add new admin link -->
  </nav>
{/if}
```

---

## Transfer Prompt

**When you need to add admin functionality:**

1. **Create admin-protected endpoints:**
   ```python
   from open_webui.utils.auth import get_admin_user

   @router.get("/admin/endpoint")
   async def admin_endpoint(user=Depends(get_admin_user)):
       # Only admins can reach here
       pass
   ```

2. **Use proper prefix** for admin routes:
   ```python
   app.include_router(
       router,
       prefix="/api/v1/admin/{feature}",
       tags=["admin:{feature}"]
   )
   ```

3. **Create admin UI** in `src/routes/(app)/admin/{feature}/`:
   ```svelte
   <script>
     import { user } from '$lib/stores';
     import { goto } from '$app/navigation';

     onMount(() => {
       if ($user?.role !== 'admin') {
         goto('/');
       }
     });
   </script>
   ```

4. **Check role in frontend** before showing admin features:
   ```svelte
   {#if $user?.role === 'admin'}
     <AdminFeature />
   {/if}
   ```

5. **Add to admin navigation** in sidebar

**Admin endpoint patterns:**
- `GET /admin/{feature}/config` — Get settings
- `POST /admin/{feature}/config` — Update settings
- `GET /admin/{feature}/stats` — Get statistics
- `DELETE /admin/users/{id}/{resource}` — Delete user data

**Signals that this pattern applies:**
- System-wide configuration
- Usage statistics and analytics
- User management operations
- Feature flags and toggles

---

## Related Documents

- `DIRECTIVE_adding_api_router.md` — Basic router pattern
- `ADR_007_auth_strategy.md` — Role-based access
- `backend/open_webui/routers/auths.py` — Admin endpoint examples

---

*Last updated: 2026-02-03*
