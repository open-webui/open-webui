# Directive: Adding a Frontend API Client

> **Pattern type:** Frontend-backend integration
> **Complexity:** Low
> **Files touched:** 1-2

---

## Prerequisites

- `DIRECTIVE_adding_api_router.md` — Backend endpoint exists
- `ARCHITECTURE_OVERVIEW.md` — System design

---

## Structural Pattern

When connecting frontend to backend APIs, create dedicated API client modules:

1. **Create API module** in `src/lib/apis/{feature}/`
2. **Export async functions** for each endpoint
3. **Handle errors consistently** with try/catch pattern
4. **Use authentication token** from user session

| Component | Location | Purpose |
|-----------|----------|---------|
| API module | `src/lib/apis/{feature}/index.ts` | Fetch wrappers |
| Constants | `src/lib/constants.ts` | API base URL |
| Types | `src/lib/types/index.ts` | Shared type definitions |

---

## Illustrative Application

The chats API (`src/lib/apis/chats/index.ts`) demonstrates this pattern:

### Step 1: Create API Module

```typescript
// src/lib/apis/features/index.ts
import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface Feature {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  created_at: number;
}

export interface CreateFeatureRequest {
  name: string;
  description?: string;
}

/**
 * Get all features for the current user.
 */
export const getFeatures = async (token: string): Promise<Feature[]> => {
  let error = null;

  const res = await fetch(`${WEBUI_API_BASE_URL}/features`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err;
      console.error('getFeatures error:', err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
};

/**
 * Get a single feature by ID.
 */
export const getFeatureById = async (
  token: string,
  featureId: string
): Promise<Feature | null> => {
  let error = null;

  const res = await fetch(`${WEBUI_API_BASE_URL}/features/${featureId}`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
    },
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err;
      console.error('getFeatureById error:', err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
};

/**
 * Create a new feature.
 */
export const createFeature = async (
  token: string,
  feature: CreateFeatureRequest
): Promise<Feature> => {
  let error = null;

  const res = await fetch(`${WEBUI_API_BASE_URL}/features`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(feature),
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err;
      console.error('createFeature error:', err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
};

/**
 * Update an existing feature.
 */
export const updateFeature = async (
  token: string,
  featureId: string,
  updates: Partial<Feature>
): Promise<Feature> => {
  let error = null;

  const res = await fetch(`${WEBUI_API_BASE_URL}/features/${featureId}`, {
    method: 'PUT',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(updates),
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err;
      console.error('updateFeature error:', err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
};

/**
 * Delete a feature.
 */
export const deleteFeature = async (
  token: string,
  featureId: string
): Promise<boolean> => {
  let error = null;

  const res = await fetch(`${WEBUI_API_BASE_URL}/features/${featureId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err;
      console.error('deleteFeature error:', err);
      return false;
    });

  if (error) {
    throw error;
  }

  return res?.success ?? true;
};
```

### Step 2: Use in Components

```svelte
<!-- src/lib/components/FeatureManager.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { user } from '$lib/stores';
  import {
    getFeatures,
    createFeature,
    deleteFeature,
    type Feature
  } from '$lib/apis/features';

  let features: Feature[] = [];
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    if ($user) {
      try {
        features = await getFeatures($user.token);
      } catch (e) {
        error = e.message || 'Failed to load features';
      } finally {
        loading = false;
      }
    }
  });

  async function handleCreate() {
    try {
      const newFeature = await createFeature($user.token, {
        name: 'New Feature',
      });
      features = [...features, newFeature];
    } catch (e) {
      error = e.message;
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteFeature($user.token, id);
      features = features.filter(f => f.id !== id);
    } catch (e) {
      error = e.message;
    }
  }
</script>

{#if loading}
  <p>Loading...</p>
{:else if error}
  <p class="error">{error}</p>
{:else}
  <button on:click={handleCreate}>Add Feature</button>
  <ul>
    {#each features as feature}
      <li>
        {feature.name}
        <button on:click={() => handleDelete(feature.id)}>Delete</button>
      </li>
    {/each}
  </ul>
{/if}
```

---

## Transfer Prompt

**When you need to call a backend API from frontend:**

1. **Create API module:** `src/lib/apis/{feature}/index.ts`

2. **Define types** for request/response:
   ```typescript
   export interface MyEntity {
     id: string;
     name: string;
     // ...
   }
   ```

3. **Create fetch function** following the pattern:
   ```typescript
   import { WEBUI_API_BASE_URL } from '$lib/constants';

   export const getEntities = async (token: string): Promise<MyEntity[]> => {
     let error = null;

     const res = await fetch(`${WEBUI_API_BASE_URL}/entities`, {
       method: 'GET',
       headers: {
         Accept: 'application/json',
         Authorization: `Bearer ${token}`,
       },
     })
       .then(async (res) => {
         if (!res.ok) throw await res.json();
         return res.json();
       })
       .catch((err) => {
         error = err;
         console.error(err);
         return null;
       });

     if (error) throw error;
     return res;
   };
   ```

4. **For POST/PUT**, include body:
   ```typescript
   body: JSON.stringify(data),
   ```

5. **Use in components:**
   ```svelte
   import { getEntities } from '$lib/apis/entities';
   import { user } from '$lib/stores';

   const data = await getEntities($user.token);
   ```

**Error handling pattern:**
- Catch errors in the API function
- Log errors for debugging
- Throw to caller for UI handling
- Return null on error if appropriate

**Signals that this pattern applies:**
- Need to fetch data from backend
- Creating CRUD operations for a feature
- Integrating with a new API endpoint

---

## Related Documents

- `DIRECTIVE_adding_api_router.md` — Backend endpoint
- `DIRECTIVE_creating_svelte_store.md` — Storing fetched data
- `src/lib/apis/chats/index.ts` — Reference implementation

---

*Last updated: 2026-02-03*
