# ADR 011: Playground Architecture for AI Capabilities

> **Status:** Accepted
> **Date:** 2026-01 (commit: 94302de)
> **Deciders:** Open WebUI contributors

## Context

Open WebUI is expanding beyond text-based chat to include additional AI capabilities:
- **Image generation:** DALL-E, Stable Diffusion, etc.
- **Audio processing:** Speech-to-text, text-to-speech
- **Model testing:** Parameter experimentation without saving chats

These capabilities need a sandbox environment where users can:
- Experiment without cluttering chat history
- Test different models and parameters
- Access modality-specific interfaces (image prompts, audio controls)

## Decision

Introduce a **playground architecture** with:
1. Dedicated route structure: `/playground/{capability}`
2. Capability-specific components
3. Ephemeral interactions (not saved to chat history by default)
4. Shared layout with capability navigation

Key design:
- **Route-based separation:** Each capability gets its own route
- **Component isolation:** Capability-specific UI in dedicated components
- **Shared utilities:** Common API patterns, model selection
- **Extensible:** Easy to add new playground types

## Consequences

### Positive
- **Clean separation:** Playground doesn't pollute chat history
- **Optimized UX:** Each capability gets tailored interface
- **Experimentation:** Users can test without commitment
- **Extensibility:** Pattern for adding future capabilities

### Negative
- **Code duplication:** Some UI patterns repeated across playgrounds
- **Navigation complexity:** Users need to discover playgrounds
- **State management:** Playground state separate from main app

### Neutral
- Adds new routes to learn
- May want to save playground results to chat later (future feature)

## Implementation

**Route structure:**

```
src/routes/
└── (app)/
    └── playground/
        ├── +layout.svelte      # Shared playground layout
        ├── +page.svelte        # Playground index/selector
        ├── chat/
        │   └── +page.svelte    # Chat playground (model testing)
        └── images/
            └── +page.svelte    # Image generation playground
```

**Playground layout:**

```svelte
<!-- playground/+layout.svelte -->
<script>
  import { page } from '$app/stores';
</script>

<div class="playground-container">
  <nav class="playground-nav">
    <a href="/playground/chat" class:active={$page.url.pathname === '/playground/chat'}>
      Chat
    </a>
    <a href="/playground/images" class:active={$page.url.pathname === '/playground/images'}>
      Images
    </a>
  </nav>

  <main class="playground-content">
    <slot />
  </main>
</div>
```

**Images playground component:**

```svelte
<!-- playground/images/+page.svelte -->
<script lang="ts">
  import { models } from '$lib/stores';
  import { generateImage } from '$lib/apis/images';

  let prompt = '';
  let selectedModel = '';
  let generatedImages = [];
  let generating = false;

  async function generate() {
    generating = true;
    try {
      const result = await generateImage(prompt, selectedModel);
      generatedImages = [...generatedImages, result];
    } finally {
      generating = false;
    }
  }
</script>

<div class="images-playground">
  <div class="prompt-area">
    <textarea bind:value={prompt} placeholder="Describe the image..." />
    <button on:click={generate} disabled={generating}>
      {generating ? 'Generating...' : 'Generate'}
    </button>
  </div>

  <div class="results-grid">
    {#each generatedImages as image}
      <img src={image.url} alt={image.prompt} />
    {/each}
  </div>
</div>
```

**API extension:**

```python
# routers/images.py
@router.post("/api/images/generate")
async def generate_image(
    request: Request,
    body: ImageGenerationRequest,
    user=Depends(get_verified_user),
):
    """Generate image from prompt."""
    # Route to appropriate provider (OpenAI, local SD, etc.)
    provider = get_image_provider(body.model)
    result = await provider.generate(body.prompt, body.options)
    return ImageGenerationResponse(url=result.url, ...)
```

## Future Capabilities

The playground architecture supports future additions:

| Capability | Route | Description |
|------------|-------|-------------|
| Chat | `/playground/chat` | Model testing with parameters |
| Images | `/playground/images` | Image generation |
| Audio | `/playground/audio` | TTS/STT testing |
| Code | `/playground/code` | Code generation/execution |
| Embeddings | `/playground/embeddings` | Embedding visualization |

## Alternatives Considered

### Modal-based playgrounds
- Playgrounds as modals over main UI
- Less screen space
- Harder to compare results
- Rejected for UX limitations

### Separate application
- Standalone playground app
- Code duplication
- Separate deployment
- Rejected for maintenance burden

### Playground in chat
- Add playground mode to existing chat
- Complicates chat component
- State management issues
- Rejected for separation of concerns

## Related Documents

- `ARCHITECTURE_OVERVIEW.md` — System design
- `DIRECTIVE_adding_api_router.md` — Adding new API endpoints
- `ADR_003_multi_provider_llm.md` — Provider abstraction

---

*Last updated: 2026-02-03*
