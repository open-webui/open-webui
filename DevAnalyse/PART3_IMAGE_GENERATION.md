# PART 3: Image Generation Mode Integration

**Analyse-Datum:** 2025-12-07 12:15:30  
**Thema:** TOP 4 (Image Generation Mode Integration im Chat Panel)

---

## TOP 4: Image Generation Mode Integration

### UI-Integration

#### Feature-Toggle im MessageInput

**Datei:** `src/lib/components/chat/MessageInput.svelte` (Zeile 1566-1582)

**Toggle-Implementierung:**

```svelte
<script>
	export let imageGenerationEnabled = false;
	
	// Capability-Check: Nur Modelle mit image_generation capability
	let imageGenerationCapableModels = [];
	$: imageGenerationCapableModels = (
		atSelectedModel?.id ? [atSelectedModel.id] : selectedModels
	).filter(
		(model) =>
			$models.find((m) => m.id === model)
				?.info?.meta?.capabilities?.image_generation ?? true
	);
	
	// Button nur anzeigen wenn:
	// 1. Alle ausgewählten Modelle image_generation können
	// 2. Feature global aktiviert ist
	// 3. User hat Permission
	let showImageGenerationButton = false;
	$: showImageGenerationButton =
		selectedModels.length === imageGenerationCapableModels.length &&
		$config?.features?.enable_image_generation &&
		($_user.role === 'admin' || $_user?.permissions?.features?.image_generation);
</script>

{#if showImageGenerationButton}
	<Tooltip content={$i18n.t('Image')} placement="top">
		<button
			on:click={() => imageGenerationEnabled = !imageGenerationEnabled}
			type="button"
			class="p-[7px] flex gap-1.5 items-center rounded-full transition {imageGenerationEnabled
				? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white'
				: 'bg-transparent text-gray-600 dark:text-gray-300'}"
		>
			<Photo className="size-4" strokeWidth="1.75" />
		</button>
	</Tooltip>
{/if}
```

**Visueller Indikator:**

```svelte
<!-- IntegrationsMenu.svelte -->
<button class="flex w-full justify-between gap-2 items-center px-3 py-1.5">
	<div class="flex gap-2 items-center">
		<Photo className="size-4" />
		<div>{$i18n.t('Image')}</div>
	</div>
	
	<!-- Switch-Toggle -->
	<Switch
		state={imageGenerationEnabled}
		on:change={(e) => {
			imageGenerationEnabled = e.detail === 'checked';
		}}
	/>
</button>
```

### Komponenten-Unterschiede

**Wichtig:** Text- und Image-Mode nutzen **dieselbe Chat.svelte Komponente!**

Der Unterschied liegt nur im **Backend-Verhalten** basierend auf `features.image_generation`.

#### Image-Response-Rendering

**Datei:** `src/lib/components/chat/Messages/ResponseMessage.svelte` (Zeile 394-433)

```svelte
<script>
	let generatingImage = false;
	
	const generateImage = async (message) => {
		generatingImage = true;
		
		try {
			const res = await imageGenerations(
				localStorage.token,
				message.content
			);
			
			if (res) {
				// Map API-Response zu File-Objects
				const files = res.map((image) => ({
					type: 'image',
					url: image.url
				}));
				
				// Message mit Image-Files updaten
				saveMessage(message.id, {
					...
					message,
					files: files
				});
			}
		} catch (error) {
			toast.error(`Image generation failed: ${error}`);
		} finally {
			generatingImage = false;
		};
	};
</script>

<!-- Generate Image Button -->
{#if $config?.features.enable_image_generation && 
	 ($user?.role === 'admin' || $user?.permissions?.features?.image_generation) &&
	 !readOnly}
	<Tooltip content={$i18n.t('Generate Image')} placement="bottom">
		<button
			aria-label={$i18n.t('Generate Image')}
			on:click={() => {
				if (!generatingImage) {
					generateImage(message);
				}
			}}
		>
			{#if generatingImage}
				<Spinner className="size-4" />
			{:else}
				<Photo className="size-4" />
			{/if}
		</button>
	</Tooltip>
{/if}

<!-- Image Display -->
{#if message.files}
	{#each message.files as file}
		{#if file.type === 'image'}
			<button on:click={() => openImageModal(file.url)}>
				<img
				src={file.url}
				alt="Generated image"
				class="rounded-lg max-w-md cursor-pointer hover:opacity-90 transition"
				/>
			</button>
		{/if}
	{/each}
{/if}
```

### API-Integration

#### Frontend API-Call

**Datei:** `src/lib/apis/images/index.ts` (Zeile 173-213)

```typescript
export const imageGenerations = async (
	token: string = '',
	prompt: string
): Promise<ImageResponse[]> => {
	let error = null;
	
	const res = await fetch(`${IMAGES_API_BASE_URL}/generations`, {
		method: 'POST',
		headers: {
			'Accept': 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			prompt: prompt
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || 'Server connection failed';
			return null;
		});
	
	if (error) {
		throw error;
	}
	
	return res;
};
```

#### Backend-Endpoint

**Endpoint:** `POST /api/images/generations`

**Datei:** `backend/open_webui/routers/images.py` (Zeile 523-716)

```python
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

router = APIRouter()

class ImageGenerateForm(BaseModel):
	prompt: str
	model: Optional[str] = None
	size: Optional[str] = None
	n: int = 1
	negative_prompt: Optional[str] = None

@router.post("/generations")
async def image_generations(
	request: Request,
	form_data: ImageGenerateForm,
	user: UserModel = Depends(get_verified_user)
):
	# Engine-Selection
	engine = request.app.state.config.IMAGE_GENERATION_ENGINE
	
	if engine == "openai":
		return await openai_image_generation(request, form_data, user)
	elif engine == "comfyui":
		return await comfyui_image_generation(request, form_data, user)
	elif engine == "automatic1111":
		return await automatic1111_image_generation(request, form_data, user)
	elif engine == "gemini":
		return await gemini_image_generation(request, form_data, user)
	else:
		raise HTTPException(
			status_code=400,
			detail=f"Unsupported engine: {engine}"
	)
```

**Request-Format:**

```json
{
  "prompt": "A beautiful sunset over mountains",
  "model": "dall-e-3",
  "size": "1024x1024",
  "n": 1,
  "negative_prompt": "blurry, low quality"
}
```

**Response-Format:**

```json
[
  {
    "url": "https://example.com/uploads/generated-image-123.png"
  }
]
```

#### Unterstützte Engines

| Engine | Backend | Image-Return-Format | Upload |
|--------|---------|---------------------|--------|
| **OpenAI** | DALL-E 2/3 | Base64 oder URL | Ja (wenn Base64) |
| **ComfyUI** | ComfyUI Workflow | URL (ComfyUI Server) | Ja (download → upload) |
| **Automatic1111** | Stable Diffusion WebUI | Base64 | Ja → URL |
| **Gemini** | Google Imagen | Base64 | Ja → URL |

**OpenAI-Implementierung:**

```python
# backend/open_webui/routers/images.py (Zeile 546-571)

async def openai_image_generation(request, form_data, user):
	headers = {
		"Authorization": f"Bearer {request.app.state.config.IMAGES_OPENAI_API_KEY}",
		"Content-Type": "application/json"
	}
	
	url = f"{request.app.state.config.IMAGES_OPENAI_API_BASE_URL}/images/generations"
	
	data = {
		"model": form_data.model or request.app.state.config.IMAGE_GENERATION_MODEL,
		"prompt": form_data.prompt,
		"n": form_data.n,
		"size": form_data.size or request.app.state.config.IMAGE_SIZE,
		"response_format": "b64_json"  # oder "url"
	}
	
	response = await session.post(url, json=data, headers=headers)
	response_data = await response.json()
	
	images = []
	for item in response_data["data"]:
		if "b64_json" in item:
			# Base64 → Upload → URL
			image_data = base64.b64decode(item["b64_json"])
			url = upload_image(request, image_data, "image/png", data, user)
		else:
			# URL direkt
			url = item["url"]
			
		images.append({"url": url})
	
	return images
```

### Datenfluss

**Image Generation Flow:**

```
1. User aktiviert imageGenerationEnabled Toggle
     ↓
2. User sendet Message
     ↓
3. Chat.svelte: getFeatures() → { image_generation: true }
     ↓
4. POST /api/chat/completions mit features
     ↓
5. Backend Middleware (utils/middleware.py)
     ↓
6. Auto-Prompt-Enhancement (optional)
     ↓
7. POST /api/images/generations
     ↓
8. Engine-spezifische Generation
   - OpenAI: API-Call → Base64/URL
   - ComfyUI: Workflow-Trigger → Poll → Download
   - A1111: API-Call → Base64
   - Gemini: API-Call → Base64
     ↓
9. Image Upload zu Object Storage
     ↓
10. Return Image URL
     ↓
11. WebSocket Event: emit('files', {files: [{type:'image', url:'...'}]})
     ↓
12. Frontend: Update message.files
     ↓
13. ResponseMessage.svelte: Render <img>
```

**Backend-Middleware-Integration:**

**Datei:** `backend/open_webui/utils/middleware.py` (Zeile 771-902)

```python
async def handle_image_generation_filter(
	request, form_data, user, extra_params
):
	metadata = extra_params.get("__metadata__", {})
	chat_id = metadata.get("chat_id", None)
	
	if not chat_id:
		return form_data
	
	chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
	__event_emitter__ = extra_params["__event_emitter__"]
	
	# Status-Update
	await __event_emitter__({
		"type": "status",
		"data": {"description": "Creating image", "done": False}
	})
	
	# Extract user message
	messages_map = chat.chat.get("history", {}).get("messages", {})
	message_id = chat.chat.get("history", {}).get("currentId")
	message_list = get_message_list(messages_map, message_id)
	user_message = get_last_user_message(message_list)
	
	prompt = user_message
	
	# Optional: Prompt-Enhancement
	if request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION:
		enhanced_prompt = await generate_image_prompt(
			request,
			{"model": form_data["model"], "messages": form_data["messages"]},
			user
		)
		prompt = enhanced_prompt["choices"][0]["message"]["content"]
	
	# Generate Image
	try:
		images = await image_generations(
			request=request,
			form_data=CreateImageForm(prompt=prompt),
			user=user
		)
		
		await __event_emitter__({
			"type": "status",
			"data": {"description": "Image created", "done": True}
		})
		
		# Emit Images zu Frontend
		await __event_emitter__({
			"type": "files",
			"data": {
				"files": [
					{"type": "image", "url": img["url"]}
					for img in images
				]
				}
			}
		)
		
	except Exception as e:
		await __event_emitter__({
			"type": "status",
			"data": {
				"description": f"Image generation failed: {e}",
				"done": True
			}
		})
	
	return form_data
```

**Kein Progressive Loading:** Images werden als vollständige URLs zurückgegeben.

**Image-Caching:**
- Images werden in `/static/uploads/` oder Object Storage gespeichert
- URLs sind persistent

### User Experience

#### Loading-States

```svelte
<script>
	// Status von WebSocket-Event
	let statusMessage = '';
	let statusDone = true;
	
	eventTarget.addEventListener('status', (e) => {
		statusMessage = e.detail.description;
		statusDone = e.detail.done;
		
		if (!statusDone) {
			toast.info(statusMessage);
		}
	});
</script>

{#if !statusDone}
	<div class="flex items-center gap-2 text-sm text-gray-600">
		<Spinner className="size-4" />
		<span>{statusMessage}</span>
	</div>
{/if}
```

#### Image-Display mit Modal

```svelte
<script>
	let showImageModal = false;
	let selectedImageUrl = '';
	
	const openImageModal = (url: string) => {
		selectedImageUrl = url;
		showImageModal = true;
	};
</script>

<!-- Thumbnail -->
{#each message.files as file}
	{#if file.type === 'image'}
		<button on:click={() => openImageModal(file.url)}>
			<img
				src={file.url}
				alt="Generated"
				class="rounded-lg max-w-md cursor-pointer hover:opacity-90"
			/>
			</button>
		{/if}
	{/each}

<!-- Full-Size Modal -->
{#if showImageModal}
	<Modal bind:show={showImageModal}>
		<img src={selectedImageUrl} alt="Full size" class="max-w-full" />
		<button on:click={() => downloadImage(selectedImageUrl)}>
			Download
		</button>
	</Modal>
{/if}
```

#### Download-Funktionalität

```svelte
<script>
	import { saveAs } from 'file-saver';
	
	const downloadImage = async (url: string) => {
		const response = await fetch(url);
		const blob = await response.blob();
		const filename = url.split('/').pop() || 'generated-image.png';
		saveAs(blob, filename);
	};
</script>
```

### Shared Logic

#### Feature-Detection

**Datei:** `src/lib/components/chat/Chat.svelte` (Zeile 1736-1828)

```typescript
const getFeatures = () => {
	let features = {};
	
	if ($config?.features) {
		features = {
			image_generation:
				$config?.features?.enable_image_generation &&
					($user?.role === 'admin' || 
					 $user?.permissions?.features?.image_generation)
						? imageGenerationEnabled
						: false,
				web_search: webSearchEnabled,
				code_interpreter: codeInterpreterEnabled,
				voice: $showCallOverlay
			};
	}
	
	// Check Model Capabilities
	const currentModels = atSelectedModel?.id 
		? [atSelectedModel.id] 
		: selectedModels;
		
	if (currentModels.every(id => {
		const model = $models.find(m => m.id === id);
		return model?.info?.meta?.capabilities?.web_search ?? true;
	})) {
		if ($settings?.webSearch === 'always') {
			features.web_search = true;
		}
	}
	
	return features;
};
```

#### Model-Capability-Check

```typescript
// Prüfe ob alle ausgewählten Modelle eine Capability haben
const checkCapability = (capability: string): boolean => {
	const models = atSelectedModel?.id 
		? [atSelectedModel.id] 
		: selectedModels;
		
	return models.every(modelId => {
		const model = $models.find(m => m.id === modelId);
		return model?.info?.meta?.capabilities?.[capability] ?? true;
	});
};

// Verwendung
$: imageGenerationCapable = checkCapability('image_generation');
$: webSearchCapable = checkCapability('web_search');
$: visionCapable = checkCapability('vision');
```

#### Multi-Modal-Architektur

**Shared Message-Processing:**

```svelte
<script>
	// Text- und Image-Messages nutzen dieselbe Speicherung
	const saveMessage = async (messageId: string, message: Message) => {
		// Update local state
		history.messages[messageId] = message;
		history = history;
		
		// Sync to backend
		await updateChatById(localStorage.token, $chatId, {
			history: history
		});
	};
	
	// File-Rendering basierend auf file.type
	const renderFile = (file: File) => {
		switch (file.type) {
			case 'image':
				return `<img src="${file.url}" />`;
			case 'video':
				return `<video src="${file.url}" controls />`;
			case 'audio':
				return `<audio src="${file.url}" controls />`;
			default:
				return `<a href="${file.url}">${file.name}</a>`;
			}
	};
</script>
```

**Feature-Flow-Architektur:**

```
Chat.svelte
    ↓
features = getFeatures()
    ↓
{
  image_generation: boolean,
  web_search: boolean,
  code_interpreter: boolean,
  vision: boolean
}
    ↓
POST /api/chat/completions { features }
    ↓
Backend Middleware wertet features aus
    ↓
├─ image_generation → handle_image_generation_filter()
├─ web_search       → handle_web_search_filter()
└─ code_interpreter → handle_code_interpreter_filter()
    ↓
Response mit type-spezifischen Files
    ↓
Frontend: message.files = [{type, url}]
    ↓
Render basierend auf file.type
```

---

## Zusammenfassung

### Key Points

✅ **Nahtlose Integration** - Kein separater "Image Mode", nur Feature-Toggle  
✅ **Multi-Engine-Support** - OpenAI, ComfyUI, A1111, Gemini  
✅ **Capability-basiert** - UI passt sich an Model-Capabilities an  
✅ **Event-driven** - WebSocket für Status-Updates & File-Delivery  
✅ **Persistent Storage** - Images in Object Storage, URLs in Message  
✅ **User-Friendly** - Loading-States, Modals, Download-Funktion  

### Text vs. Image Mode Vergleich

| Aspekt | Text Mode | Image Mode |
|--------|-----------|------------|
| **Komponenten** | Chat.svelte | Chat.svelte (gleiche!) |
| **API** | /api/chat/completions | /api/images/generations |
| **Streaming** | SSE (text/event-stream) | Kein Streaming (JSON) |
| **Response** | Inkrementelle Chunks | Vollständige URL |
| **Event-Emitter** | Optional | Für Status-Updates |
| **File-Type** | - | message.files[{type:'image'}] |
| **Rendering** | Markdown/Code | <img src="..." /> |

---

**Ende der Analyse** ✅