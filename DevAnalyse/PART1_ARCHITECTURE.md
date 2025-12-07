# PART 1: Chat-Architektur & API-Endpoints

**Analyse-Datum:** 2025-12-07 11:53:45  
**Themen:** TOP 1 (Chat Page/Panel Aufbau) + TOP 2 (API-Endpoints)

---

## TOP 1: Chat Page/Panel Aufbau

### Komponenten-Hierarchie

#### Hauptkomponente  
**Datei:** `src/lib/components/chat/Chat.svelte` (2600+ Zeilen)

Diese Komponente orchestriert:
- Message History Management
- Multi-Model Support
- File Handling
- WebSocket/SSE Streaming
- Gesamten Chat-Lifecycle

#### Routing-Struktur

**Root Chat Route:** `src/routes/(app)/+page.svelte`
```svelte
<script lang="ts">
	import Chat from '$lib/components/chat/Chat.svelte';
</script>

<Chat />
```

**Chat mit ID:** `src/routes/(app)/c/[id]/+page.svelte`
```svelte
<script lang="ts">
	import { page } from '$app/stores';
	import Chat from '$lib/components/chat/Chat.svelte';
</script>

<Chat chatIdProp={$page.params.id} />
```

#### Komponenten-Baum

```
src/routes/(app)/+page.svelte (Root)
└── Chat.svelte (Main Orchestrator)
    ├── Navbar.svelte (Top Navigation)
    │   ├── ModelSelector.svelte
    │   ├── Menu.svelte
    │   └── ShareChatModal.svelte
    │
    ├── PaneGroup (from paneforge)
    │   ├── Pane (Messages Area)
    │   │   ├── Messages.svelte (Container)
    │   │   │   ├── Loader.svelte (Pagination)
    │   │   │   └── Message.svelte (Loop)
    │   │   │       ├── UserMessage.svelte
    │   │   │       └── ResponseMessage.svelte
    │   │   │           ├── ProfileImage.svelte
    │   │   │           ├── Name.svelte
    │   │   │           ├── ContentRenderer.svelte
    │   │   │           │   ├── Markdown.svelte
    │   │   │           │   ├── CodeBlock.svelte
    │   │   │           │   └── Image.svelte
    │   │   │           ├── Citations.svelte
    │   │   │           ├── CodeExecutions.svelte
    │   │   │           └── Action Buttons
    │   │   │               ├── Regenerate
    │   │   │               ├── Copy
    │   │   │               ├── TTS
    │   │   │               └── Generate Image
    │   │   │
    │   │   └── MessageInput.svelte
    │   │       ├── Input Field
    │   │       ├── File Upload
    │   │       └── IntegrationsMenu.svelte
    │   │           ├── Tools
    │   │           ├── Web Search Toggle
    │   │           ├── Image Generation Toggle
    │   │           └── Code Interpreter Toggle
    │   │
    │   ├── PaneResizer
    │   │
    │   └── Pane (ChatControls - Optional)
    │       └── ChatControls.svelte
    │           ├── Model Parameters
    │           ├── System Prompt
    │           └── Advanced Settings
    │
    └── Event Handlers
        ├── submitPrompt()
        ├── stopResponse()
        ├── regenerateResponse()
        └── saveMessage()
```

### UI-Framework und Bibliotheken

#### Core Framework
- **Svelte:** 5.0.0 (mit Runes-System)
- **SvelteKit:** 2.5.27 (Routing + SSR)
- **TypeScript:** 5.5.4

#### UI-Komponentenbibliotheken

| Library | Version | Verwendung | Typ |
|---------|---------|------------|-----|
| **bits-ui** | 0.21.15 | Tooltips, Dropdowns, Modals | Library |
| **paneforge** | 0.0.6 | Resizable Panel System | Library |
| **svelte-sonner** | 0.3.19 | Toast Notifications | Library |
| **TailwindCSS** | 4.0.0 | Utility-First CSS | Library |
| **marked** | 9.1.0 | Markdown → HTML | Library |
| **highlight.js** | 11.9.0 | Code Syntax Highlighting | Library |
| **mermaid** | 11.10.1 | Diagramm-Rendering | Library |
| **katex** | 0.16.22 | LaTeX Math Rendering | Library |
| **dompurify** | 3.2.6 | XSS Protection | Library |
| **tippy.js** | 6.3.7 | Tooltip Engine | Library |

#### Custom vs. Library Components

**Library-basierte UI-Elemente:**

```svelte
<!-- Tooltip (bits-ui) -->
<Tooltip content="Click to copy">
  <button>Copy</button>
</Tooltip>

<!-- Resizable Panels (paneforge) -->
<PaneGroup direction="horizontal">
  <Pane defaultSize={75}>
    <Messages />
  </Pane>
  <PaneResizer />
  <Pane defaultSize={25}>
    <ChatControls />
  </Pane>
</PaneGroup>

<!-- Toast (svelte-sonner) -->
<script>
  import { toast } from 'svelte-sonner';
  toast.success('Message sent!');
</script>
```

**Custom-Komponenten:**

| Komponente | Pfad | Funktion |
|------------|------|----------|
| Chat.svelte | `src/lib/components/chat/` | Haupt-Orchestrator |
| Messages.svelte | `src/lib/components/chat/` | Message List Container |
| MessageInput.svelte | `src/lib/components/chat/` | Input mit Features |
| ResponseMessage.svelte | `src/lib/components/chat/Messages/` | AI Response Rendering |
| ContentRenderer.svelte | `src/lib/components/chat/` | Markdown/Code/Media |
| ModelSelector.svelte | `src/lib/components/chat/` | Multi-Model Picker |
| Navbar.svelte | `src/lib/components/chat/` | Top Navigation |

**Beispiel: MessageInput mit Features**

```svelte
<!-- src/lib/components/chat/MessageInput.svelte -->
<script>
  export let prompt = '';
  export let files = [];
  export let selectedToolIds = [];
  export let imageGenerationEnabled = false;
  export let webSearchEnabled = false;
  
  // Capability-Check
  $: imageGenCapable = selectedModels.every(id => {
    const model = $models.find(m => m.id === id);
    return model?.info?.meta?.capabilities?.image_generation ?? true;
  });
</script>

<div class="relative">
  <!-- File Upload -->
  <input type="file" bind:files />
  
  <!-- Text Input -->
  <textarea bind:value={prompt} />
  
  <!-- Integrations Menu -->
  <IntegrationsMenu
    bind:selectedToolIds
    bind:imageGenerationEnabled
    bind:webSearchEnabled
  />
  
  <!-- Submit Button -->
  <button on:click={submitPrompt}>
    Send
  </button>
</div>
```

### State Management

**Svelte Stores** (`src/lib/stores/index.ts`):

```typescript
import { writable } from 'svelte/store';

// Chat State
export const chatId = writable<string | null>(null);
export const chats = writable<Chat[]>([]);
export const models = writable<Model[]>([]);
export const settings = writable<Settings>({});
export const user = writable<User | null>(null);
export const config = writable<Config>({});

// UI State
export const showSidebar = writable(true);
export const showControls = writable(false);
export const mobile = writable(false);
export const temporaryChatEnabled = writable(false);

// Features
export const audioQueue = writable([]);
export const showCallOverlay = writable(false);
```

**Message History Structure:**

```typescript
interface History {
  messages: Record<string, Message>;
  currentId: string;
}

interface Message {
  id: string;
  parentId: string | null;
  childrenIds: string[];
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  timestamp: number;
  files?: File[];
  done: boolean;
}
```

**State Management in Chat.svelte:**

```svelte
<script>
  let history: History = {
    messages: {},
    currentId: null
  };
  
  // Reactive: Bei Änderungen automatisch speichern
  $: if (history && $chatId) {
    updateChatById(localStorage.token, $chatId, {
      history: history
    });
  }
  
  // Message hinzufügen
  const addMessage = (message: Message) => {
    history.messages[message.id] = message;
    history.currentId = message.id;
    history = history; // Trigger Reactivity
  };
  
  // Message aktualisieren
  const updateMessage = (id: string, updates: Partial<Message>) => {
    history.messages[id] = {
      ...history.messages[id],
      ...updates
    };
    history = history;
  };
</script>
```

### Styling-Ansatz

**TailwindCSS 4.0 Configuration:**

```javascript
// tailwind.config.js
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        gray: {
          50: '#f9fafb',
          // ... custom gray scale
          900: '#111827'
        }
      }
    }
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/container-queries')
  ]
}
```

**Dark Mode Implementation:**

```svelte
<!-- Automatic dark mode basierend auf System-Präferenz -->
<div class="bg-white dark:bg-gray-900 text-black dark:text-white">
  <p class="text-gray-700 dark:text-gray-300">
    Content
  </p>
</div>
```

**Responsive Design:**

```svelte
<script>
  import { mobile } from '$lib/stores';
</script>

<!-- Conditional Rendering -->
{#if $mobile}
  <MobileLayout />
{:else}
  <DesktopLayout />
{/if}

<!-- Responsive Classes -->
<div class="px-4 md:px-8 lg:px-20 max-w-6xl mx-auto">
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <!-- Content -->
  </div>
</div>
```

---

## TOP 2: API-Endpoints für Text-Streaming

### Endpoint-Identifikation

**Haupt-Chat-Endpoint:**
```
POST /api/chat/completions
```

**Datei:** `backend/open_webui/routers/openai.py` (Zeile 922-953)

**Alternative Routen:**
- `POST /api/v1/chat/completions` (OpenAI-kompatibel)
- `POST /ollama/api/chat` (Ollama-native)

**Weitere relevante Endpoints:**
- `GET /api/models` - Liste aller Modelle
- `GET /api/chats` - Chat-History
- `POST /api/chats` - Neuen Chat erstellen
- `PUT /api/chats/{id}` - Chat aktualisieren

### Backend-Implementierung

**Framework:** FastAPI (Python)

**Endpoint-Definition:**

```python
# backend/open_webui/routers/openai.py

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user: UserModel = Depends(get_verified_user)
):
    # Model-Lookup
    model_id = form_data.get("model")
    stream = form_data.get("stream", False)
    
    # Request an Backend forwarden
    r = await session.request(
        method="POST",
        url=request_url,
        data=payload,
        headers=headers
    )
    
    # SSE-Streaming-Response
    if "text/event-stream" in r.headers.get("Content-Type", ""):
        return StreamingResponse(
            stream_chunks_handler(r.content),
            status_code=r.status,
            headers=dict(r.headers),
            media_type="text/event-stream"
        )
    else:
        # Non-Streaming Response
        return await r.json()
```

**Streaming-Generator:**

```python
# backend/open_webui/utils/chat.py

async def generate_direct_chat_completion(
    request: Request,
    form_data: dict,
    user: Any,
    models: dict
):
    if form_data.get("stream"):
        q = asyncio.Queue()
        
        async def event_generator():
            try:
                while True:
                    data = await q.get()
                    
                    if isinstance(data, dict):
                        if "done" in data and data["done"]:
                            break
                        yield f"data: {json.dumps(data)}\n\n"
                    elif isinstance(data, str):
                        yield f"data: {data}\n\n"
                        
            except Exception as e:
                log.error(f"Error in event generator: {e}")
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
```

### Request/Response Format

**Request (OpenAI-kompatibel):**

```json
{
  "model": "llama3.2:latest",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 2048,
  "top_p": 1.0,
  "frequency_penalty": 0,
  "presence_penalty": 0,
  "chat_id": "abc-123",
  "session_id": "xyz-789"
}
```

**Response (SSE Stream):**

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1701234567,"model":"llama3.2","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1701234567,"model":"llama3.2","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1701234567,"model":"llama3.2","choices":[{"index":0,"delta":{"content":" How"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1701234567,"model":"llama3.2","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Streaming-Protokoll

**Protokoll:** Server-Sent Events (SSE)

**HTTP-Headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**Chunk-Format:**
- Prefix: `data: `
- JSON-Payload: OpenAI-kompatibles Chunk-Objekt
- Separator: `\n\n` (doppelter Zeilenumbruch)
- Stream-Ende: `data: [DONE]\n\n`

**WebSocket-Integration (Parallel):**

```python
# backend/open_webui/socket/main.py

from socketio import AsyncServer

sio = AsyncServer(
    cors_allowed_origins="*",
    async_mode="asgi"
)

# Event-Emitter für Status-Updates
@sio.event
async def connect(sid, environ):
    await sio.emit('connected', {'status': 'ok'}, room=sid)

# Channel-basierte Kommunikation
channel = f"{user_id}:{session_id}:{request_id}"

await sio.emit('message', {
    'type': 'status',
    'data': {'description': 'Processing...', 'done': False}
}, room=channel)
```

### Integration mit AI-Backends

**Unterstützte Backends:**
- **Ollama** - Lokale LLM-Inferenz
- **OpenAI** - GPT-3.5/4
- **OpenAI-kompatible APIs** - LiteLLM, vLLM, LocalAI, etc.

**Pass-Through-Streaming:**

```python
# Ollama-Response direkt durchreichen

async def stream_chunks_handler(response_stream):
    async for chunk in response_stream:
        # Optional: Ollama → OpenAI Format konvertieren
        transformed_chunk = convert_ollama_to_openai(chunk)
        yield transformed_chunk
```

**Payload-Konvertierung:**

```python
# backend/open_webui/utils/payload.py

def convert_payload_openai_to_ollama(form_data: dict) -> dict:
    return {
        "model": form_data["model"],
        "messages": form_data["messages"],
        "stream": form_data.get("stream", False),
        "options": {
            "temperature": form_data.get("temperature"),
            "num_predict": form_data.get("max_tokens"),
            "top_p": form_data.get("top_p"),
            "top_k": form_data.get("top_k")
        }
    }
```

**Response-Konvertierung:**

```python
# backend/open_webui/utils/response.py

async def convert_streaming_response_ollama_to_openai(ollama_stream):
    async for data in ollama_stream.body_iterator:
        data = json.loads(data)
        
        # Ollama Format → OpenAI Format
        openai_chunk = {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": data.get("model"),
            "choices": [{
                "index": 0,
                "delta": {
                    "content": data.get("message", {}).get("content")
                },
                "finish_reason": "stop" if data.get("done") else None
            }]
        }
        
        yield f"data: {json.dumps(openai_chunk)}\n\n"
    
    yield "data: [DONE]\n\n"
```

### Error Handling

**Stream-Error-Handling:**

```python
async def event_generator():
    try:
        while True:
            data = await q.get()
            
            # Error-Check
            if isinstance(data, dict) and data.get("error"):
                yield f"data: {json.dumps({'error': data['error']})}\n\n"
                break
                
            yield f"data: {json.dumps(data)}\n\n"
            
    except asyncio.CancelledError:
        log.warning("Stream cancelled by client")
        # Cleanup
        
    except Exception as e:
        log.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
    finally:
        # Resource-Cleanup
        await cleanup_resources()
```

**Timeout-Configuration:**

```python
# aiohttp mit Timeout
session = aiohttp.ClientSession(
    timeout=aiohttp.ClientTimeout(
        total=600,      # 10 Minuten Gesamt-Timeout
        connect=10,     # 10 Sekunden Connect-Timeout
        sock_read=30    # 30 Sekunden Read-Timeout
    )
)
```

**Client-Side Error-Handling:**

```typescript
// src/lib/apis/openai/index.ts

try {
  const reader = res.body
    .pipeThrough(new TextDecoderStream())
    .pipeThrough(splitStream('\n'))
    .getReader();
    
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    
    const data = JSON.parse(value.replace('data: ', ''));
    
    // Error-Check
    if (data.error) {
      toast.error(data.error.message || 'An error occurred');
      break;
    }
    
    // Process chunk
    processChunk(data);
  }
  
} catch (error) {
  console.error('Streaming error:', error);
  toast.error('Connection lost. Please try again.');
  
  // Cleanup
  controller.abort();
}
```

---

## Dateiverzeichnis

### Frontend (Svelte)
```
src/
├── routes/
│   └── (app)/
│       ├── +page.svelte                    # Root Chat Page
│       └── c/[id]/+page.svelte             # Chat mit ID
│       
├── lib/
│   ├── components/
│   │   └── chat/
│   │       ├── Chat.svelte                 # 🔥 Hauptkomponente
│   │       ├── Messages.svelte
│   │       ├── MessageInput.svelte
│   │       ├── Navbar.svelte
│   │       └── ChatControls.svelte
│   │       
│   ├── apis/
│   │   └── openai/
│   │       └── index.ts                    # chatCompletion()
│   │       
│   └── stores/
│       └── index.ts                        # Svelte Stores
```

### Backend (Python)
```
backend/open_webui/
├── routers/
│   ├── openai.py                           # 🔥 /api/chat/completions
│   └── chats.py                            # Chat CRUD
│   
└── utils/
    ├── chat.py                             # Stream Generator
    ├── payload.py                          # Payload Conversion
    └── response.py                         # Response Conversion
```

---

**Weiter mit:** [PART2_PERFORMANCE.md](./PART2_PERFORMANCE.md) (Stream-Performance-Optimierungen)