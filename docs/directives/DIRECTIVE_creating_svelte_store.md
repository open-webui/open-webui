# Directive: Creating a Svelte Store

> **Pattern type:** Frontend state management
> **Complexity:** Low
> **Files touched:** 1-2

---

## Prerequisites

- `ADR_002_sveltekit_frontend.md` — Frontend architecture
- `ARCHITECTURE_OVERVIEW.md` — System design

---

## Structural Pattern

When adding reactive state to the frontend, use Svelte's native stores:

1. **Define writable stores** in the central store file
2. **Export stores and types** for component access
3. **Initialize with appropriate defaults**
4. **Access via `$` prefix** in Svelte components

| Component | Location | Purpose |
|-----------|----------|---------|
| Store definition | `src/lib/stores/index.ts` | State containers |
| Type definitions | `src/lib/stores/index.ts` | TypeScript types |
| Component usage | `src/lib/components/*.svelte` | Reactive access |

**Store types:**
- `writable` — Read/write store for mutable state
- `readable` — Read-only store for derived/external state
- `derived` — Computed store from other stores

---

## Illustrative Application

The stores file (`src/lib/stores/index.ts`) demonstrates this pattern:

### Step 1: Define Store and Types

```typescript
// src/lib/stores/index.ts
import { writable, type Writable } from 'svelte/store';

// Type definitions
export interface Feature {
  id: string;
  name: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

export interface FeatureState {
  features: Feature[];
  loading: boolean;
  error: string | null;
}

// Store definition
export const featureState: Writable<FeatureState> = writable({
  features: [],
  loading: false,
  error: null,
});

// Convenience stores for common access patterns
export const features: Writable<Feature[]> = writable([]);
export const selectedFeatureId: Writable<string | null> = writable(null);
```

### Step 2: Use in Components

```svelte
<!-- src/lib/components/FeatureList.svelte -->
<script lang="ts">
  import { features, selectedFeatureId } from '$lib/stores';
  import type { Feature } from '$lib/stores';

  // Reactive access with $ prefix
  $: featureList = $features;
  $: selected = $selectedFeatureId;

  function selectFeature(id: string) {
    selectedFeatureId.set(id);
  }

  function addFeature(feature: Feature) {
    features.update(current => [...current, feature]);
  }
</script>

<ul>
  {#each featureList as feature}
    <li
      class:selected={feature.id === selected}
      on:click={() => selectFeature(feature.id)}
    >
      {feature.name}
    </li>
  {/each}
</ul>
```

### Step 3: Initialize from API

```typescript
// src/lib/apis/features/index.ts
import { WEBUI_API_BASE_URL } from '$lib/constants';
import { features } from '$lib/stores';

export const loadFeatures = async (token: string): Promise<void> => {
  const response = await fetch(`${WEBUI_API_BASE_URL}/features`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (response.ok) {
    const data = await response.json();
    features.set(data);
  }
};
```

```svelte
<!-- src/routes/(app)/+layout.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { loadFeatures } from '$lib/apis/features';
  import { user } from '$lib/stores';

  onMount(async () => {
    if ($user) {
      await loadFeatures($user.token);
    }
  });
</script>
```

---

## Transfer Prompt

**When you need to add frontend state:**

1. **Define types** for your state:
   ```typescript
   // src/lib/stores/index.ts
   export interface MyFeature {
     id: string;
     name: string;
     // ... other fields
   }
   ```

2. **Create writable store:**
   ```typescript
   import { writable, type Writable } from 'svelte/store';

   export const myFeatures: Writable<MyFeature[]> = writable([]);
   ```

3. **Use in components:**
   ```svelte
   <script>
     import { myFeatures } from '$lib/stores';

     // Read with $ prefix (reactive)
     $: items = $myFeatures;

     // Write with .set() or .update()
     function add(item) {
       myFeatures.update(current => [...current, item]);
     }

     function reset() {
       myFeatures.set([]);
     }
   </script>
   ```

4. **For complex state**, use a single object store:
   ```typescript
   export const myState: Writable<{
     items: Item[];
     loading: boolean;
     error: string | null;
   }> = writable({
     items: [],
     loading: false,
     error: null,
   });

   // Update specific fields
   myState.update(s => ({ ...s, loading: true }));
   ```

5. **For derived state**, use `derived`:
   ```typescript
   import { derived } from 'svelte/store';

   export const activeFeatures = derived(
     myFeatures,
     $features => $features.filter(f => f.enabled)
   );
   ```

**Store patterns:**
- Use `writable` for user-modifiable state
- Use `derived` for computed values
- Keep stores flat when possible
- Initialize with sensible defaults
- Export types alongside stores

**Signals that this pattern applies:**
- Need to share state across components
- State needs to survive component unmount
- Multiple components need to react to same data
- Global application state (user, settings, etc.)

---

## Related Documents

- `ADR_002_sveltekit_frontend.md` — Frontend architecture
- `DIRECTIVE_adding_frontend_api.md` — Loading store data from API
- `src/lib/stores/index.ts` — Existing store definitions

---

*Last updated: 2026-02-03*
