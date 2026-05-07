# Fluxo de uma Conversa End-to-End

> Mapeado a partir de: `Chat.svelte`, `main.py`, `utils/middleware.py`, `utils/chat.py`, `socket/main.py`  
> Data: 2026-05-06

---

## Visão geral (sequência)

```
USUÁRIO
  │
  ▼ digita mensagem
MessageInput.svelte
  │
  ▼ submitPrompt() [Chat.svelte:1247]
  │   cria user message, adiciona ao history
  │   monta payload com model, messages, files, tools, features
  │
  ├──▶ WebSocket /ws/socket.io  ←────────────────────────────────────┐
  │        recebe status events durante todo o fluxo                  │
  │                                                                    │
  ▼ sendPromptSocket() → generateOpenAIChatCompletion()               │
POST /api/chat/completions                                            │
  │                                                                    │
  ▼ [main.py:1068]                                                    │
  1. get_verified_user()  — valida JWT                                │
  2. verifica acesso ao model                                          │
  3. monta metadata {chat_id, message_id, session_id, tool_ids...}    │
  │                                                                    │
  ▼ process_chat_payload() [middleware.py:685]                        │
  │   A. apply_params_to_form_data()                                  │
  │   B. se model tem knowledge:                                       │
  │      └─▶ emit "knowledge_search" status ───────────────────────▶ WS
  │          appenda arquivos de knowledge ao form_data               │
  │   C. process_pipeline_inlet_filter()  — pipelines externos        │
  │   D. process_filter_functions(inlet) — funções de filtro custom   │
  │   E. features:                                                     │
  │      ├─ web_search  ──▶ chat_web_search_handler()                 │
  │      │                    emit "web_search" status ─────────────▶ WS
  │      │                    busca na web, adiciona docs ao form_data │
  │      ├─ image_generation ▶ chat_image_generation_handler()        │
  │      └─ code_interpreter ▶ injeta prompt de code interpreter      │
  │   F. tools:                                                        │
  │      ├─ tool_ids  ──▶ get_tools()  (server-side tools)            │
  │      ├─ tool_servers  (client-side/MCP tools)                     │
  │      └─ se não native function calling:                            │
  │           chat_completion_tools_handler()                          │
  │              └─▶ LLM seleciona tools → executa → injeta resultado  │
  │   G. chat_completion_files_handler()  — RAG                       │
  │      └─▶ busca em vector store → monta context_string             │
  │          injeta via rag_template() no system prompt               │
  │   retorna (form_data enriquecido, metadata, events)               │
  │                                                                    │
  ▼ generate_chat_completion() [utils/chat.py:158]                   │
  │   roteamento por tipo de modelo:                                   │
  │   ┌─ direct connection ──▶ generate_direct_chat_completion()      │
  │   │     usa WebSocket p/ stream (emit "request:chat:completion")   │
  │   ├─ function/pipeline ──▶ generate_function_chat_completion()    │
  │   ├─ Ollama ─────────────▶ convert payload (OpenAI→Ollama format) │
  │   │                         generate_ollama_chat_completion()      │
  │   │                         convert response (Ollama→OpenAI format)│
  │   └─ OpenAI/compatible ──▶ generate_openai_chat_completion()      │
  │                                                                    │
  ▼ SSE stream de tokens ─────────────────────────────────────────▶ FE
  │                                                                    │
  ▼ process_chat_response() [middleware.py:954]                       │
  │   - stream passa pelo outlet filters                               │
  │   - process_pipeline_outlet_filter()                               │
  │   - process_filter_functions(outlet)                               │
  │   - background_tasks_handler() (async, após completion):           │
  │       ├─ generate_title() → Chats.update_chat_title_by_id()       │
  │       │   emit "chat:title" ──────────────────────────────────▶ WS │
  │       └─ generate_chat_tags() → Chats.update_chat_tags_by_id()    │
  │           emit "chat:tags" ───────────────────────────────────▶ WS │
  │                                                                    │
FRONTEND recebe SSE stream                                            │
  ├─ parseia chunks → atualiza responseMessage.content em tempo real   │
  ├─ WebSocket recebe "chat-events" ──▶ chatCompletionEventHandler()  │
  │   └─ processa: status, sources, tool calls, title, tags            │
  └─ ao fim do stream → saveChatHandler() → POST /api/v1/chats/{id}
```

---

## Detalhamento por fase

### Fase 1 — Frontend: preparação do payload

**Arquivo:** `src/lib/components/chat/Chat.svelte:1247`

```
submitPrompt(userPrompt)
  └─ cria userMessage {id, role:"user", content, files, timestamp}
  └─ adiciona ao history (Svelte store)
  └─ cria responseMessage {id, role:"assistant", content:""}
  └─ sendPromptSocket(_history, model, responseMessageId, chatId)
       └─ monta messages[] com system prompt + histórico
       └─ generateOpenAIChatCompletion(token, {
            model, messages, stream,
            files, tool_ids, tool_servers,
            features: {web_search, image_generation, code_interpreter},
            session_id, chat_id, id,
            background_tasks: {title_generation, tags_generation},
            model_item
          })
          └─ POST /api/chat/completions
```

### Fase 2 — Backend: entrada e controle de acesso

**Arquivo:** `backend/open_webui/main.py:1068`

| Passo | O que acontece |
|-------|----------------|
| Auth | `get_verified_user()` valida Bearer JWT |
| Model | Busca model em `app.state.MODELS` |
| ACL | `check_model_access(user, model)` se não for admin |
| Metadata | Extrai chat_id, message_id, session_id, tool_ids, files, features do payload |

### Fase 3 — Middleware: enriquecimento do payload (inlet)

**Arquivo:** `backend/open_webui/utils/middleware.py:685`

```
process_chat_payload(request, form_data, user, metadata, model)
  │
  ├─ [A] apply model params (temperature, top_p, etc.)
  ├─ [B] Knowledge injection
  │     → vector search nas coleções do modelo
  │     → appenda docs aos files
  ├─ [C] Pipeline inlet filter (plugins externos)
  ├─ [D] Function filters inlet (funções Python customizadas)
  ├─ [E] Features:
  │     web_search → busca + injeta docs
  │     image_generation → gera imagem, retorna URL
  │     code_interpreter → injeta system prompt
  ├─ [F] Tools:
  │     server-side → get_tools() → carrega callables Python
  │     client-side → specs de tool servers (MCP)
  │     execução não-nativa → LLM escolhe tool → executa → injeta resultado
  └─ [G] RAG files:
        get_sources_from_files() → busca no vector store
        rag_template() → injeta contexto no system/user message
```

### Fase 4 — Roteamento para o LLM

**Arquivo:** `backend/open_webui/utils/chat.py:158`

```
generate_chat_completion(request, form_data, user)
  │
  ├─ direct?  → generate_direct_chat_completion()
  │              stream via WebSocket (socket.io)
  ├─ function/pipeline? → generate_function_chat_completion()
  ├─ owned_by "ollama"? → convert_payload_openai_to_ollama()
  │                        generate_ollama_chat_completion()
  │                        convert_streaming_response_ollama_to_openai()
  └─ OpenAI compatible → generate_openai_chat_completion()
```

### Fase 5 — Stream e pós-processamento (outlet)

**Arquivo:** `backend/open_webui/utils/middleware.py:954`

```
process_chat_response(request, response, ...)
  │
  ├─ outlet filters (pipeline e functions) — podem modificar a resposta
  ├─ stream SSE → frontend (tokens em tempo real)
  └─ background_tasks_handler() [async, não bloqueia o stream]:
       ├─ generate_title()     → salva título no DB → emit "chat:title" via WS
       └─ generate_chat_tags() → salva tags no DB   → emit "chat:tags" via WS
```

### Fase 6 — Frontend: recepção e persistência

```
generateOpenAIChatCompletion retorna SSE stream
  ├─ cada chunk → responseMessage.content += chunk  (reatividade Svelte)
  ├─ WebSocket "chat-events" → chatCompletionEventHandler()
  │   tipos de evento:
  │   ├─ "status"   → mostra loading/progress (ex: "Searching web...")
  │   ├─ "sources"  → exibe citações/fontes
  │   ├─ "chat:title" → atualiza título do chat na sidebar
  │   └─ "chat:tags"  → atualiza tags
  └─ stream finalizado → saveChatHandler()
       └─ POST /api/v1/chats/{id}  (persiste histórico completo)
```

---

## WebSocket: canal de eventos paralelo

O WebSocket não carrega tokens de resposta — ele é usado exclusivamente para **eventos de status e metadados** durante o processamento.

**Arquivo:** `backend/open_webui/socket/main.py`

| Evento emitido | Quando | Dados |
|---------------|--------|-------|
| `chat-events / status` | Durante knowledge search, web search, tool execution | `{action, description, done}` |
| `chat-events / sources` | Ao finalizar RAG | lista de fontes citadas |
| `chat:title` | Após completion, async | string do título gerado |
| `chat:tags` | Após completion, async | lista de tags |
| `usage` | Periódico | modelos em uso |

O `get_event_emitter()` cria um closure que emite via `sio.emit("chat-events", room=session_id)` e opcionalmente persiste no DB se `ENABLE_REALTIME_CHAT_SAVE=true`.

---

## Pontos de intervenção para customização

| Onde intervir | Arquivo | Efeito |
|---------------|---------|--------|
| Antes de qualquer processamento | `utils/middleware.py` → `process_filter_functions(inlet)` | Modificar/validar payload antes do LLM |
| Após resposta do LLM | `utils/middleware.py` → `process_filter_functions(outlet)` | Pós-processar ou filtrar resposta |
| Novo tipo de feature | `process_chat_payload()` → bloco `features` | Adicionar feature ativável pelo frontend |
| Nova fonte de contexto (RAG) | `retrieval/loaders/` + `chat_completion_files_handler()` | Novo tipo de documento/busca |
| Novo provider de LLM | `utils/chat.py` → `generate_chat_completion()` | Suporte a outro backend de inferência |
| Eventos extras para o frontend | `socket/main.py` → `get_event_emitter()` | Novos tipos de status/evento |
| Tarefas pós-resposta | `process_chat_response()` → `background_tasks_handler()` | Análise, logging, ações automáticas |
