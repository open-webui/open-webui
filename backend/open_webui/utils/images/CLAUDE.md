# Utils/Images Directory

This directory contains image processing and generation utilities, specifically for integrating with ComfyUI, a powerful node-based image generation workflow system. It provides the bridge between Open WebUI's chat interface and ComfyUI's advanced image generation capabilities.

## Files in This Directory

### comfyui.py
**Purpose:** ComfyUI integration for advanced image generation workflows with node-based composition.

**Key Components:**

#### Core Functions
- `queue_prompt(prompt, client_id, base_url, api_key)` - Submit workflow to ComfyUI server
- `get_image(filename, subfolder, folder_type, base_url, api_key)` - Download generated image bytes
- `get_image_url(filename, subfolder, folder_type, base_url)` - Get image URL for frontend access
- `get_history(prompt_id, base_url, api_key)` - Retrieve execution history and outputs
- `get_images(ws, prompt, client_id, base_url, api_key)` - Monitor WebSocket for completion, retrieve all images
- `comfyui_generate_image(model, payload, client_id, base_url, api_key)` - Main async image generation orchestrator

#### Data Models
- `ComfyUINodeInput` - Node configuration (type, node_ids, key, value)
- `ComfyUIWorkflow` - Workflow definition with nodes list
- `ComfyUIGenerateImageForm` - Complete generation request payload

**Integration Pattern:**
```python
# ComfyUI workflow execution
1. Parse workflow JSON
2. Inject user parameters (prompt, size, model, etc.) into workflow nodes
3. Connect to ComfyUI WebSocket (wss://comfyui-server/ws)
4. Queue prompt via HTTP POST /prompt
5. Listen on WebSocket for execution updates
6. When "executing" message with node=None received, workflow complete
7. Fetch history to get output filenames
8. Generate image URLs for frontend
```

**Used by:**
- `routers/images.py` - Image generation endpoints
- `utils/middleware.py` - Image generation during chat (when user requests image)

**Uses:**
- `websocket` library - WebSocket client for real-time updates
- `urllib.request` - HTTP requests to ComfyUI API
- `env.py` - COMFYUI_BASE_URL, COMFYUI_API_KEY (configured per instance)

**Key Workflows:**

#### Workflow Parameter Injection
ComfyUI workflows are node graphs with inputs. This utility injects parameters:

**Supported Node Types:**
- `model` - Model selection (e.g., "Stable Diffusion XL")
- `prompt` - Positive prompt text
- `negative_prompt` - Negative prompt text
- `width` - Image width in pixels
- `height` - Image height in pixels
- `n` - Batch size (number of images)
- `steps` - Sampling steps
- `seed` - Random seed (generated if not provided)

**Injection Logic:**
```python
workflow = json.loads(payload.workflow.workflow)

for node in payload.workflow.nodes:
    if node.type == "prompt":
        for node_id in node.node_ids:
            workflow[node_id]["inputs"][node.key] = payload.prompt
```

Each node type maps to specific workflow nodes by ID, allowing flexible workflow templates.

#### Image Generation Flow
```
1. User sends chat message: "Generate an image of a sunset"
2. Middleware detects image generation intent
3. Calls comfyui_generate_image() with parameters
4. Function parses workflow template
5. Injects parameters into workflow nodes
6. Connects to ComfyUI WebSocket
7. Queues workflow via HTTP POST
8. Monitors WebSocket for "executing" messages
9. When complete, fetches history
10. Extracts image filenames from outputs
11. Returns image URLs
12. Frontend displays images in chat
```

#### WebSocket Protocol
ComfyUI uses WebSocket for real-time execution updates:

**Message Types:**
- `{"type": "status", "data": {...}}` - Queue status updates
- `{"type": "execution_start", "data": {"prompt_id": "..."}}` - Execution started
- `{"type": "executing", "data": {"node": "node_id", "prompt_id": "..."}}` - Node executing
- `{"type": "executing", "data": {"node": null, "prompt_id": "..."}}` - **Execution complete**
- `{"type": "executed", "data": {"node": "node_id", "output": {...}}}` - Node output

**Completion Detection:**
```python
while True:
    out = ws.recv()
    message = json.loads(out)
    if message["type"] == "executing":
        data = message["data"]
        if data["node"] is None and data["prompt_id"] == prompt_id:
            break  # Done!
```

## Architecture & Patterns

### Async Execution Pattern
Image generation is long-running, so uses async:
```python
async def comfyui_generate_image(...):
    # Connect synchronously
    ws = websocket.WebSocket()
    ws.connect(ws_url)

    # Offload blocking WebSocket recv to thread pool
    images = await asyncio.to_thread(
        get_images, ws, workflow, client_id, base_url, api_key
    )

    ws.close()
    return images
```

This prevents blocking FastAPI's async event loop during image generation.

### Node-Based Parameter Injection
ComfyUI workflows are flexible node graphs. This utility maps high-level parameters to specific nodes:

**Example Workflow:**
```json
{
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "seed": 12345,
      "steps": 20,
      ...
    }
  },
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "A sunset over mountains"
    }
  }
}
```

**Parameter Mapping:**
```python
nodes = [
    {"type": "seed", "node_ids": ["3"], "key": "seed"},
    {"type": "prompt", "node_ids": ["6"], "key": "text"},
]
```

This allows reusable workflow templates with dynamic parameter injection.

### Image URL Generation
Generated images stored on ComfyUI server, accessed via URLs:

```python
url = f"{base_url}/view?filename={filename}&subfolder={subfolder}&type={folder_type}"
```

Frontend fetches images directly from ComfyUI (or proxied through Open WebUI backend).

## Integration Points

### utils/images/ → ComfyUI Server
Direct HTTP and WebSocket communication:
- **HTTP POST** `/prompt` - Queue workflow
- **HTTP GET** `/history/{prompt_id}` - Get execution history
- **HTTP GET** `/view?filename=...` - Download image
- **WebSocket** `/ws?clientId={id}` - Real-time execution updates

### routers/images.py → utils/images/comfyui.py
Image router calls ComfyUI functions:
```python
# In routers/images.py
from open_webui.utils.images.comfyui import comfyui_generate_image

@app.post("/api/images/generations")
async def generate_image(form: ImageGenerationForm):
    if form.engine == "comfyui":
        result = await comfyui_generate_image(
            model=form.model,
            payload=form.comfyui,
            client_id=str(uuid.uuid4()),
            base_url=COMFYUI_BASE_URL,
            api_key=COMFYUI_API_KEY
        )
        return result
```

### utils/middleware.py → utils/images/comfyui.py
Middleware triggers image generation during chat:
```python
# In utils/middleware.py
if detect_image_generation_intent(message):
    images = await comfyui_generate_image(...)
    inject_images_into_response(images)
```

### Frontend → ComfyUI Image URLs
Generated images accessible via URLs in chat:
```svelte
<!-- In frontend Messages.svelte -->
{#each message.images as image}
  <img src={image.url} alt="Generated image" />
{/each}
```

## Key Workflows

### Basic Image Generation
```
1. User: "Generate a sunset image"
2. Middleware detects intent
3. Load workflow template from config
4. Inject parameters:
   - prompt: "A sunset over mountains"
   - width: 1024
   - height: 1024
   - steps: 30
   - seed: random
5. Connect WebSocket
6. Queue prompt
7. Monitor execution
8. Retrieve images
9. Return URLs to frontend
```

### Advanced Workflow Customization
```
1. Admin configures custom workflow in settings
2. Workflow has nodes for:
   - CLIP text encoding (prompt)
   - Model loader (checkpoint)
   - KSampler (generation)
   - VAE decode (image output)
3. Node mappings configured:
   - prompt → node "6" key "text"
   - model → node "4" key "ckpt_name"
   - steps → node "3" key "steps"
4. User requests image
5. Workflow loaded, parameters injected
6. Custom pipeline executes
7. Images returned
```

### Batch Generation
```
1. User requests 4 variations
2. Set n=4 in payload
3. Inject into batch_size node
4. ComfyUI generates 4 images in single workflow
5. All images returned in outputs
6. Frontend displays grid
```

## Important Notes

### Critical Dependencies
- ComfyUI server must be running and accessible
- `COMFYUI_BASE_URL` environment variable required
- `COMFYUI_API_KEY` for authentication (optional)
- `websocket-client` Python package required

### Configuration
- **COMFYUI_BASE_URL**: ComfyUI server URL (e.g., `http://localhost:8188`)
- **COMFYUI_API_KEY**: Optional API key for authentication
- Workflow templates stored in database or config files

### Performance Considerations
- Image generation is CPU/GPU intensive (10-60 seconds)
- WebSocket connection held open during generation
- Multiple concurrent generations can overwhelm server
- Consider rate limiting or queue management

### Error Handling
- WebSocket connection failures raise exceptions
- Timeout handling not implemented (can hang indefinitely)
- No retry logic for failed generations
- Errors logged but not always propagated to user

### Security Considerations
- WebSocket connection uses authentication header
- No input validation on workflow JSON (potential injection)
- Image URLs may expose internal paths
- Consider proxying images through Open WebUI backend

### Alternative Image Engines
This directory currently only contains ComfyUI integration, but could expand to:
- Stable Diffusion WebUI (AUTOMATIC1111)
- DALL-E API (via OpenAI)
- Midjourney API
- Custom diffusion models

Each would be a separate file with similar interface:
```python
async def engine_generate_image(model, payload, **kwargs):
    # Engine-specific implementation
    return {"data": [{"url": "..."}]}
```

### Testing Considerations
- Mock WebSocket connections for unit tests
- Test workflow parameter injection separately
- Integration tests require running ComfyUI server
- Consider Docker Compose for test environment
