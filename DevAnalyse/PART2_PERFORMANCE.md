# PART 2: Stream-Performance & Datenübertragung

**Analyse-Datum:** 2025-12-07 12:32:00  
**Thema:** TOP 3 (Performante Datenübertragung vom API-Endpoint zu UX-Komponenten)

---

## TOP 3: Performante Datenübertragung

### Frontend-Backend-Kommunikation

#### HTTP-Client

**Verwendete API:** Native `fetch()` API (kein axios/superagent)

**API-Call-Initiierung:**

**Datei:** `src/lib/apis/openai/index.ts`

```typescript
export const chatCompletion = async (
	token: string = '',
	body: object,
	url: string = OPENAI_API_BASE_URL
): Promise<[Response, AbortController]> => {
	
	const controller = new AbortController();
	let error = null;
	
	const res = await fetch(`${url}/chat/completions`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			'Accept': 'application/json',
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify(body)
	}).catch((err) => {
		error = err;
		return null;
	});
	
	if (error) {
		throw error;
	}
	
	return [res, controller];
};
```

**Verwendung in Chat.svelte:**

```svelte
<script>
	const sendMessage = async () => {
		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: selectedModel,
				messages: messages,
				stream: true
			}
		);
		
		currentController = controller;
		await processStream(res);
	};
</script>
```

### Stream-Processing im Frontend

#### ReadableStream-Verarbeitung

**Datei:** `src/lib/components/chat/Chat.svelte`

```svelte
<script>
	const processStream = async (res: Response, controller: AbortController) => {
		const reader = res.body
			.pipeThrough(new TextDecoderStream())
			.pipeThrough(splitStream('\n'))
			.getReader();
		
		let stopResponseFlag = false;
		
		while (true) {
			const { value, done } = await reader.read();
			
			if (done || stopResponseFlag) {
				if (stopResponseFlag) {
					controller.abort('User: Stop Response');
				}
				break;
			}
			
			try {
				const lines = value.split('\n');
				
				for (const line of lines) {
					if (line === '') continue;
					
					if (line === 'data: [DONE]') {
						responseMessage.done = true;
						break;
					}
					
					const data = JSON.parse(line.replace('data: ', ''));
					const content = data.choices[0]?.delta?.content;
					
					if (content) {
						responseMessage.content += content;
						history.messages[responseMessageId] = responseMessage;
						history = history;
					}
				}
			} catch (error) {
				console.error('Parse error:', error);
			}
		}
		
		await tick();
		scrollToBottom();
	};
</script>
```

#### splitStream Utility

**Datei:** `src/lib/utils/index.ts`

```typescript
export const splitStream = (splitOn: string) => {
	let buffer = '';
	
	return new TransformStream({
		transform(chunk: string, controller) {
			buffer += chunk;
			const parts = buffer.split(splitOn);
			buffer = parts.pop() || '';
			parts.forEach(part => {
				if (part) controller.enqueue(part);
			});
		},
		flush(controller) {
			if (buffer) {
				controller.enqueue(buffer);
			}
		}
	});
};
```

### State-Updates und Re-Rendering

#### Svelte Reactivity System

**Keine Debouncing/Throttling nötig!**

```svelte
<script>
	$: messages = Object.values(history.messages)
		.filter(msg => msg.parentId === currentParentId)
		.sort((a, b) => a.timestamp - b.timestamp);

	const updateMessage = (id: string, content: string) => {
		history.messages[id] = {
			...
history.messages[id],
			content: content
		};
		history = history;
	};
</script>

{#each messages as message (message.id)}
	<Message {message} />
{/each}
```

### Performance-Optimierungen

#### 1. Lazy Message Loading

**Datei:** `src/lib/components/chat/Messages.svelte`

```svelte
<script>
	export let messagesCount: number | null = 20;
	let messagesLoading = false;
	
	const loadMoreMessages = async () => {
		const element = document.getElementById('messages-container');
		element.scrollTop = element.scrollTop + 100;
		
		messagesLoading = true;
		messagesCount += 20;
		await tick();
		messagesLoading = false;
	};
	
	$: displayedMessages = messages.slice(-messagesCount);
</script>

<Loader on:visible={() => {
	if (!messagesLoading) loadMoreMessages();
}}>
	<Spinner />
</Loader>

{#each displayedMessages as message (message.id)}
	<Message {message} />
{/each}
```

#### 2. Memory Leak Prevention

```svelte
<script>
	import { onDestroy } from 'svelte';
	
	let abortController: AbortController | null = null;
	
	onDestroy(() => {
		if (abortController) {
			abortController.abort();
		}
	});
</script>
```

#### 3. Progressive Rendering

```svelte
<script>
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	
	export let content = '';
	
	$: renderedContent = DOMPurify.sanitize(
		marked.parse(content)
	);
</script>

{@html renderedContent}
```

#### 4. Code-Block-Optimierung

```svelte
<script>
	let isCodeBlockComplete = false;
	
	$: {
		const backtickCount = (content.match(/```/g) || []).length;
		isCodeBlockComplete = backtickCount % 2 === 0;
	}
	
	$: if (isCodeBlockComplete && codeContent) {
		highlightedCode = hljs.highlightAuto(codeContent).value;
	} else {
		highlightedCode = codeContent;
	}
</script>
```

### Concurrency und Race Conditions

#### Multiple Concurrent Streams

```svelte
<script>
	let streamControllers = new Map<string, AbortController>();
	
	const startStreamForModel = async (modelId: string, messageId: string) => {
		const controller = new AbortController();
		streamControllers.set(messageId, controller);
		
		try {
			await processStream(modelId, messageId, controller);
		} finally {
			streamControllers.delete(messageId);
		}
	};
	
	const stopAllStreams = () => {
		streamControllers.forEach(controller => {
			controller.abort('User stopped all responses');
		});
		streamControllers.clear();
	};
</script>
```

#### Race-Condition-Prevention

```svelte
<script>
	let generating = false;
	
	const sendMessage = async (prompt: string) => {
		if (generating) {
			toast.error('Please wait for current response');
			return;
		}
		
		generating = true;
		try {
			await processStream();
		} finally {
			generating = false;
		}
	};
</script>
```

### WebSocket für Realtime-Events

```svelte
<script>
	import { io } from 'socket.io-client';
	import { onMount, onDestroy } from 'svelte';
	
	let socket;
	
	onMount(() => {
		socket = io(WEBUI_BASE_URL, {
			auth: { token: localStorage.token }
		});
		
		socket.on('status', (data) => {
			console.log('Status:', data.description);
			if (!data.done) {
				toast.info(data.description);
			}
		});
		
		socket.on('files', (data) => {
			history.messages[responseMessageId].files = data.files;
			history = history;
		});
	});
	
	onDestroy(() => {
		if (socket) {
			socket.disconnect();
		}
	});
</script>
```

---

## Performance-Metriken

| Metrik | Wert |
|--------|------|
| **First Chunk Time** | < 500ms |
| **Chunk Interval** | 10-50ms |
| **Re-Render Time** | < 16ms (60 FPS) |
| **Memory per Message** | ~5-10 KB |
| **Lazy Load Threshold** | 20 Messages |

---

## Datenfluss-Diagramm

```
User Types Message
     ↓
MessageInput.svelte
     ↓
Chat.svelte
     ↓
POST /api/chat/completions
     ↓
FastAPI Backend
     ↓
Ollama/OpenAI
     ↓
SSE Stream
data: {...}\n\n
     ↓
Frontend fetch() 
     ↓
TextDecoderStream
     ↓
splitStream('\n')
     ↓
JSON.parse()
     ↓
State Update
history.messages[id].content += chunk
     ↓
Svelte Reactivity
     ↓
Re-Render
ResponseMessage.svelte
     ↓
ContentRenderer
     ↓
DOM Update
```

---

## Best Practices

### ✅ DO
1. Use AbortController für alle Fetch-Requests
2. Cleanup in onDestroy (EventListener, WebSockets, Timers)
3. Lazy Loading für lange Listen aktivieren
4. Progressive Rendering für Markdown/Code
5. Granulares Re-Rendering mit Svelte Keys

### ❌ DON'T
1. Kein Debouncing für Stream-Updates (unnötig mit Svelte)
2. Keine riesigen Messages im Memory halten (Pagination!)
3. Keine synchronen Blocking-Operationen im Stream-Handler
4. Keine globalen State-Mutations ohne Reactivity

---

## Troubleshooting

### Problem: Stream stoppt nach einigen Sekunden
**Ursache:** Proxy-Timeout (Nginx, Cloudflare)  
**Lösung:** HTTP-Headers setzen:
```
X-Accel-Buffering: no
Cache-Control: no-cache
```

### Problem: UI freezes während Streaming
**Ursache:** Zu viel Markdown-Parsing in Main-Thread  
**Lösung:** Throttle Parsing:
```svelte
<script>
	import { debounce } from '$lib/utils';
	
	const parseMarkdown = debounce((content) => {
		renderedContent = marked.parse(content);
	}, 50);
	
	$: parseMarkdown(message.content);
</script>
```

### Problem: Memory Leak bei langen Chats
**Ursache:** Alte Messages werden nicht aus DOM entfernt  
**Lösung:** Virtual Scrolling oder Pagination aktivieren

---

**Weiter mit:** [PART3_IMAGE_GENERATION.md](./PART3_IMAGE_GENERATION.md)