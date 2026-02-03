# ADR 002: SvelteKit Frontend Framework

> **Status:** Accepted
> **Date:** Foundational decision
> **Deciders:** Open WebUI core team

## Context

Open WebUI requires a frontend framework to:
- Build a responsive, interactive chat interface
- Handle real-time message streaming
- Manage complex application state (models, chats, settings)
- Support server-side rendering for SEO and initial load performance
- Enable static deployment option

The UI involves significant interactivity: real-time typing indicators, streaming message content, drag-and-drop file uploads, and complex form management.

## Decision

Use **SvelteKit** as the frontend meta-framework with **Svelte 5** as the component framework.

Key characteristics leveraged:
- Compiler-based approach (smaller runtime, better performance)
- Native reactivity without virtual DOM overhead
- Built-in stores for state management
- File-based routing
- Static adapter for deployment flexibility

## Consequences

### Positive
- **Performance:** No virtual DOM means faster updates during message streaming
- **Bundle size:** Compiled output is smaller than React/Vue equivalents
- **Simplicity:** Less boilerplate than React (no useEffect/useState ceremony)
- **Reactivity:** `$:` reactive declarations are intuitive
- **SSR/SSG:** SvelteKit handles both server and static rendering

### Negative
- **Ecosystem size:** Smaller component library ecosystem than React
- **Hiring pool:** Fewer developers familiar with Svelte than React/Vue
- **Breaking changes:** Svelte 5 runes introduced significant API changes
- **IDE support:** Less mature tooling than React ecosystem

### Neutral
- TypeScript integration requires explicit configuration
- Component testing requires Svelte-specific tooling

## Implementation

**Configuration:** `svelte.config.js`

```javascript
import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({
      fallback: 'index.html'
    }),
    alias: {
      $lib: './src/lib'
    }
  }
};
```

**Component pattern:**

```svelte
<script lang="ts">
  import { user, models } from '$lib/stores';

  let message = '';

  async function sendMessage() {
    // Handle send
  }
</script>

<div class="chat-container">
  <input bind:value={message} />
  <button on:click={sendMessage}>Send</button>
</div>

<style>
  .chat-container {
    /* Scoped styles */
  }
</style>
```

**State management:** Native Svelte stores in `src/lib/stores/index.ts`

```typescript
import { writable } from 'svelte/store';

export const user = writable(undefined);
export const models = writable([]);
export const chatId = writable('');
```

## Alternatives Considered

### React (Next.js)
- Larger ecosystem and component libraries
- More complex state management (Redux/Zustand needed)
- Larger bundle size and runtime overhead
- Rejected due to performance overhead for streaming UI

### Vue (Nuxt)
- Similar reactivity model to Svelte
- Larger runtime than Svelte
- Options API vs Composition API complexity
- Rejected as Svelte offers simpler mental model

### Plain JavaScript
- Maximum control
- Significant development overhead
- No built-in reactivity or routing
- Rejected due to development velocity requirements

### Solid.js
- Similar compiled approach to Svelte
- Smaller ecosystem
- Less mature meta-framework (SolidStart)
- Rejected due to ecosystem maturity

## Related Documents

- `ARCHITECTURE_OVERVIEW.md` — System design overview
- `DIRECTIVE_creating_svelte_store.md` — How to add frontend state
- `DIRECTIVE_adding_frontend_api.md` — How to add API clients

---

*Last updated: 2026-02-03*
