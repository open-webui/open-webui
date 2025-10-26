# Utils Directory

This directory contains shared utility modules providing cross-cutting functionality used throughout the Open WebUI backend. These utilities handle authentication, request middleware, plugin loading, chat processing, access control, webhooks, telemetry, and various helper functions that support the core application logic.

## Files in This Directory

### auth.py
**Purpose:** Authentication and authorization utilities for JWT token management, user verification, and security operations.

**Key Functions:**
- `create_token(data, expires_delta)` - Generate JWT tokens with expiration
- `decode_token(token)` - Verify and decode JWT tokens
- `get_current_user(token)` - Extract user from JWT, validate session
- `get_admin_user(user)` - Verify admin role, raise 403 if not admin
- `get_verified_user(user)` - Check user verification status
- `hash_password(password)` - Bcrypt password hashing
- `verify_password(plain, hashed)` - Password verification
- `create_api_key()` - Generate API keys for programmatic access
- `verify_trusted_header(request)` - Trusted email header authentication

**Used by:**
- `routers/auths.py` - Sign in, sign up, session management
- `routers/users.py` - User CRUD operations
- ALL router files for authentication via `Depends(get_current_user)`

**Uses:**
- `models/users.py` - Users.get_user_by_email(), Users.get_user_by_id()
- `passlib.context.CryptContext` - Password hashing
- `jwt` - Token encoding/decoding
- `env.py` - WEBUI_SECRET_KEY, JWT_EXPIRES_IN

**Integration Pattern:**
```python
# In routers
from open_webui.utils.auth import get_current_user

@app.get("/api/protected")
async def protected_route(user=Depends(get_current_user)):
    # user is verified User object
    return {"user_id": user.id}
```

### middleware.py
**Purpose:** Core request/response middleware for chat completions, orchestrating the entire LLM interaction pipeline including RAG, tool calling, memory injection, and filtering.

**Key Functions:**
- `chat_completion(body, user)` - Main chat completion orchestrator
- `process_chat_payload(form_data, user, metadata)` - Preprocess chat request
- `inject_user_memory(messages, user_id)` - Add user memories to context
- `apply_model_params_to_body(body, user)` - Inject model-specific parameters
- `apply_model_system_prompt_to_body(body, user)` - Inject custom system prompts
- `apply_tags_to_chat(chat_id, user)` - Auto-tag conversations
- `execute_tool_calls(messages, tools, user)` - Handle function calling
- `generate_title_in_background(chat_id, user_id, messages)` - Async title generation

**Used by:**
- `routers/openai.py` - POST /api/chat/completions
- `routers/ollama.py` - POST /ollama/api/chat

**Uses:**
- `routers/retrieval.py` - process_web_search() for web search
- `routers/tasks.py` - generate_title(), generate_follow_ups(), generate_queries()
- `routers/images.py` - image_generations() for DALL-E/Stable Diffusion
- `routers/memories.py` - query_memory() for long-term memory
- `routers/pipelines.py` - process_pipeline_inlet_filter(), process_pipeline_outlet_filter()
- `utils/chat.py` - generate_chat_completion() for actual LLM calls
- `utils/tools.py` - get_tools() for tool discovery
- `utils/plugin.py` - load_function_module_by_id() for function execution
- `utils/filter.py` - process_filter_functions() for content filtering
- `retrieval/utils.py` - get_sources_from_items() for RAG
- `models/chats.py` - Chats.insert_new_chat(), Chats.update_chat_by_id()
- `models/functions.py` - Functions model for custom functions
- `models/models.py` - Models model for model configuration
- `socket/main.py` - get_event_emitter() for real-time updates

**Critical Pipeline:**
```
1. Receive chat request → process_chat_payload()
2. Apply access control → check model permissions
3. Inject memories → query_memory()
4. Apply filters (inlet) → process_pipeline_inlet_filter()
5. RAG processing → get_sources_from_items()
6. Tool calling → execute_tool_calls()
7. Generate completion → generate_chat_completion()
8. Apply filters (outlet) → process_pipeline_outlet_filter()
9. Stream response → Socket.IO events
10. Background tasks → title generation, tagging, follow-ups
```

### plugin.py
**Purpose:** Dynamic plugin/function loading system for tools and custom functions with dependency management.

**Key Functions:**
- `load_function_module_by_id(function_id)` - Load Python module from database
- `load_tool_module_by_id(tool_id)` - Load tool module from database
- `extract_frontmatter(content)` - Parse function metadata (requirements, etc.)
- `install_requirements(requirements)` - Install Python dependencies via pip
- `create_module_from_string(module_name, code)` - Dynamic module creation

**Used by:**
- `utils/middleware.py` - Loads functions for execution during chat
- `utils/tools.py` - Loads tools for tool calling
- `routers/tools.py` - Tool validation and execution
- `routers/functions.py` - Function validation

**Uses:**
- `models/functions.py` - Functions.get_function_by_id()
- `models/tools.py` - Tools.get_tool_by_id()
- `importlib.util` - Dynamic module loading
- `subprocess` - pip install for requirements

**Security Considerations:**
- Executes arbitrary code from database (sandboxing recommended)
- pip install runs with PIP_OPTIONS from environment
- No execution timeout (potential DoS)

### access_control.py
**Purpose:** Permission checking and access control utilities for models, chats, and resources.

**Key Functions:**
- `has_access(user_id, type, id, access_control)` - Check resource access
- `has_permission(user_id, permission, permission_obj)` - Permission validation
- `get_permissions(user_id, default_permissions)` - Resolve user permissions
- `get_user_permissions(user_id)` - Get user's full permission set

**Used by:**
- `routers/chats.py` - Chat access validation
- `routers/models.py` - Model visibility and access
- `routers/files.py` - File access control
- `utils/middleware.py` - Model permission checking before completion

**Uses:**
- `models/users.py` - Users.get_user_by_id()

### chat.py
**Purpose:** Chat completion execution utilities for calling LLM providers (OpenAI, Ollama).

**Key Functions:**
- `generate_chat_completion(form_data, user)` - Execute chat completion request
- `get_model_path(model_id)` - Resolve model ID to provider endpoint
- `stream_message_template(model, message)` - Format SSE chunks
- `generate_openai_completion(form_data)` - Call OpenAI API
- `generate_ollama_completion(form_data)` - Call Ollama API

**Used by:**
- `utils/middleware.py` - Main completion execution
- `routers/openai.py` - Direct OpenAI proxy
- `routers/ollama.py` - Direct Ollama proxy

**Uses:**
- `models/models.py` - Models.get_model_by_id()
- `requests` library for HTTP calls to LLM providers
- Streaming via SSE (Server-Sent Events)

### tools.py
**Purpose:** Tool discovery, validation, and execution for function calling.

**Key Functions:**
- `get_tools(models, user, extra_params)` - Discover available tools for user
- `get_tool_specs(tools)` - Convert tools to OpenAI function calling format
- `get_tools_specs(function_calling_type)` - Get tool specs by type
- `get_tool_function_path(tools_specs, name)` - Resolve tool function path
- `apply_tool_call_schema(tool_call, tools_specs)` - Validate tool call against schema

**Used by:**
- `utils/middleware.py` - Tool discovery and execution during chat
- `routers/tools.py` - Tool management

**Uses:**
- `models/tools.py` - Tools.get_tools()
- `models/functions.py` - Functions.get_functions()
- `utils/plugin.py` - load_tool_module_by_id()

### task.py
**Purpose:** Background task utilities for async operations (title generation, tagging, etc.).

**Key Functions:**
- `get_task_model_id(default_model_id)` - Get model ID for background tasks
- `rag_template(template, context, query)` - Format RAG prompt template
- `tools_function_calling_generation_template(tools_specs, user_message, generation_template)` - Format tool calling prompts
- `title_generation_template(content, template)` - Format title generation prompt

**Used by:**
- `utils/middleware.py` - Background task orchestration
- `routers/tasks.py` - Task execution

**Uses:**
- `env.py` - TASK_MODEL, TASK_MODEL_EXTERNAL

### filter.py
**Purpose:** Content filtering pipeline for inlet/outlet filters on chat messages.

**Key Functions:**
- `get_sorted_filter_ids(model_id, user_id)` - Get filter order for model/user
- `process_filter_functions(functions, body, user, extra_params)` - Execute filter chain
- `apply_filter_function(function, body, user, extra_params)` - Apply single filter

**Used by:**
- `utils/middleware.py` - Inlet/outlet filtering during chat completion

**Uses:**
- `models/functions.py` - Functions.get_functions()
- `utils/plugin.py` - load_function_module_by_id()

### code_interpreter.py
**Purpose:** Code execution sandbox for interpreting and running user/LLM-generated code.

**Key Functions:**
- `execute_code_jupyter(code, kernel_id)` - Execute Python code in Jupyter kernel
- `create_kernel()` - Create new Jupyter kernel instance
- `shutdown_kernel(kernel_id)` - Clean up kernel

**Used by:**
- `utils/middleware.py` - Code interpreter tool execution

**Uses:**
- `jupyter_client` - Kernel management
- Runs in isolated kernel (but not fully sandboxed)

### embeddings.py
**Purpose:** Embedding generation utilities for semantic search.

**Key Functions:**
- `generate_embeddings(texts, model)` - Generate embeddings for text list
- `get_embedding_function(model)` - Get embedding function by model name

**Used by:**
- `retrieval/utils.py` - Document and query embedding
- `routers/retrieval.py` - Embedding API endpoints

**Uses:**
- `sentence_transformers` - Local embedding models
- OpenAI API for `text-embedding-ada-002` and similar

### oauth.py
**Purpose:** OAuth 2.0 authentication integration (Google, Microsoft, GitHub, OIDC).

**Key Functions:**
- `oauth_manager()` - Get OAuth provider manager
- `get_oauth_provider(provider_name)` - Get provider configuration
- `oauth_callback(provider, code, state)` - Handle OAuth callback
- `verify_id_token(provider, token)` - Verify OAuth ID token

**Used by:**
- `routers/auths.py` - OAuth login endpoints

**Uses:**
- `authlib.integrations.starlette_client` - OAuth client
- `models/auths.py` - Auths.authenticate_user_by_trusted_header()

### payload.py
**Purpose:** Request/response payload transformation and validation utilities.

**Key Functions:**
- `apply_model_params(params, user_settings, model_params)` - Merge model parameters
- `apply_model_system_prompt(messages, model_system_prompt)` - Inject system prompts
- `convert_params_to_ollama_format(params)` - Convert OpenAI params to Ollama
- `convert_params_to_openai_format(params)` - Normalize parameters

**Used by:**
- `utils/middleware.py` - Parameter transformation
- `routers/openai.py` - Request preprocessing
- `routers/ollama.py` - Request preprocessing

**Uses:**
- `models/models.py` - Models configuration

### misc.py
**Purpose:** Miscellaneous helper functions for message manipulation, formatting, and utilities.

**Key Functions:**
- `get_message_list(messages)` - Extract flat message list
- `add_or_update_system_message(content, messages)` - Inject/update system message
- `add_or_update_user_message(content, messages)` - Inject/update user message
- `get_last_user_message(messages)` - Get last user message
- `get_last_assistant_message(messages)` - Get last assistant message
- `prepend_to_first_user_message_content(content, messages)` - Prepend to user message
- `convert_logit_bias_input_to_json(logit_bias)` - Parse logit bias parameter
- `deep_update(dict1, dict2)` - Recursive dictionary merge

**Used by:**
- `utils/middleware.py` - Message manipulation during chat processing
- `utils/payload.py` - Message formatting
- `routers/tasks.py` - Message extraction

### models.py
**Purpose:** Model configuration and metadata management utilities.

**Key Functions:**
- `get_all_models()` - Fetch all models from OpenAI/Ollama
- `get_model_info(model_id)` - Get model metadata
- `get_model_info_with_ollama(model_id)` - Get Ollama model info
- `update_model_info(model_id, info)` - Update model metadata

**Used by:**
- `routers/models.py` - Model discovery and management
- `utils/middleware.py` - Model resolution

**Uses:**
- `models/models.py` - Models database table
- OpenAI/Ollama API for model listings

### audit.py
**Purpose:** Audit logging for sensitive operations and security events.

**Key Functions:**
- `log_event(user_id, event_type, event_data)` - Log audit event
- `get_audit_logs(filters)` - Query audit logs
- `cleanup_old_logs(days)` - Delete old audit entries

**Used by:**
- `routers/auths.py` - Login/logout events
- `routers/users.py` - User modifications
- `routers/chats.py` - Chat sharing events

**Uses:**
- Logging to database or file (configurable)

### webhook.py
**Purpose:** Webhook notification system for external integrations.

**Key Functions:**
- `post_webhook(url, event, data)` - Send webhook POST request
- `webhook_post_message(chat_id, message_id)` - Notify on new message
- `webhook_post_chat_completion(chat_id, completion)` - Notify on completion

**Used by:**
- `utils/middleware.py` - Webhook triggers during chat processing
- `routers/chats.py` - Chat event notifications

**Uses:**
- `requests` library for HTTP POST

### redis.py
**Purpose:** Redis client utilities for distributed session management and caching.

**Key Functions:**
- `get_redis_client()` - Get Redis connection
- `set_session(session_id, data, ttl)` - Store session data
- `get_session(session_id)` - Retrieve session data
- `delete_session(session_id)` - Remove session

**Used by:**
- `socket/main.py` - Distributed WebSocket session management
- `utils/middleware.py` - Rate limiting and caching

**Uses:**
- `redis` Python library
- `env.py` - REDIS_URL configuration

### response.py
**Purpose:** Response formatting utilities for consistent API responses.

**Key Functions:**
- `success_response(data, message)` - Format success response
- `error_response(message, code, details)` - Format error response
- `paginated_response(items, page, total)` - Format paginated response

**Used by:**
- All router files for consistent response formatting

### security_headers.py
**Purpose:** Security header middleware for HTTP responses.

**Key Functions:**
- `add_security_headers(response)` - Add CSP, HSTS, X-Frame-Options, etc.
- `SecurityHeadersMiddleware` - FastAPI middleware class

**Used by:**
- `main.py` - Applied globally to all responses

### logger.py
**Purpose:** Structured logging configuration and utilities.

**Key Functions:**
- `setup_logger(name, level)` - Configure logger with formatting
- `log_request(request)` - Log HTTP request details
- `log_response(response, duration)` - Log HTTP response details

**Used by:**
- All modules for consistent logging

**Uses:**
- `env.py` - SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

### pdf_generator.py
**Purpose:** PDF generation utilities for chat exports.

**Key Functions:**
- `generate_chat_pdf(chat_id)` - Export chat as PDF
- `format_messages_for_pdf(messages)` - Format messages for PDF layout

**Used by:**
- `routers/chats.py` - PDF export endpoint

**Uses:**
- `reportlab` or `weasyprint` for PDF generation

## Subdirectories

### images/
Image processing utilities.

**Contains:**
- `comfyui.py` - ComfyUI integration for image generation workflows

**Used by:**
- `routers/images.py` - Image generation endpoints
- `utils/middleware.py` - Image generation during chat

**See:** `images/CLAUDE.md` for detailed documentation

### telemetry/
OpenTelemetry instrumentation and metrics.

**Contains:**
- `setup.py` - Initialize telemetry
- `instrumentors.py` - Auto-instrumentation for FastAPI, SQLAlchemy, Redis
- `exporters.py` - Export traces/metrics to backends (OTLP, Jaeger, Zipkin)
- `metrics.py` - Custom metrics (request counts, latencies, token usage)
- `constants.py` - Telemetry configuration constants

**Used by:**
- `main.py` - Initialize telemetry on app startup
- All modules automatically instrumented

**See:** `telemetry/CLAUDE.md` for detailed documentation

## Architecture & Patterns

### Dependency Injection Pattern
Utilities use FastAPI's dependency injection:
```python
from fastapi import Depends
from open_webui.utils.auth import get_current_user

@app.get("/api/resource")
async def get_resource(user=Depends(get_current_user)):
    # user is injected and validated
    pass
```

### Middleware Chain Pattern
Request processing flows through multiple middleware layers:
```
Request
  ↓
process_chat_payload()
  ↓
inject_user_memory()
  ↓
apply_model_params()
  ↓
process_pipeline_inlet_filter()
  ↓
execute_tool_calls()
  ↓
generate_chat_completion()
  ↓
process_pipeline_outlet_filter()
  ↓
Response
```

### Plugin Loading Pattern
Dynamic code loading with dependency management:
```python
# Extract requirements from frontmatter
frontmatter = extract_frontmatter(function_code)
requirements = frontmatter.get("requirements", [])

# Install dependencies
install_requirements(requirements)

# Load module
module = create_module_from_string("custom_function", function_code)

# Execute
result = module.execute(params)
```

### Tool Calling Pattern
Tools discovered and executed dynamically:
```python
# Discover tools
tools = get_tools(models, user, extra_params)

# Convert to OpenAI format
tools_specs = get_tool_specs(tools)

# Execute tool calls from LLM
results = execute_tool_calls(messages, tools_specs, user)
```

## Integration Points

### Utils → Routers
All routers depend on utils for cross-cutting concerns:
- Authentication via `get_current_user()`
- Middleware via `chat_completion()`
- Plugin loading via `load_function_module_by_id()`

### Utils → Models
Utils access database via ORM models:
- `auth.py` → `models/users.py`
- `middleware.py` → `models/chats.py`, `models/functions.py`, `models/models.py`
- `plugin.py` → `models/functions.py`, `models/tools.py`

### Utils → Utils
Utils have internal dependencies:
- `middleware.py` → `chat.py`, `tools.py`, `filter.py`, `plugin.py`, `misc.py`, `task.py`
- `tools.py` → `plugin.py`
- `filter.py` → `plugin.py`

### Utils → External Services
Utils integrate with external services:
- `chat.py` → OpenAI API, Ollama API
- `embeddings.py` → OpenAI Embeddings API, Sentence Transformers
- `oauth.py` → Google OAuth, Microsoft OAuth, GitHub OAuth, OIDC
- `webhook.py` → External webhook URLs
- `redis.py` → Redis server
- `telemetry/` → OTLP collectors, Jaeger, Zipkin

## Key Workflows

### Chat Completion Workflow
```
1. Router receives POST /api/chat/completions
2. Auth: get_current_user() validates JWT
3. Middleware: chat_completion(body, user)
4. Process payload: process_chat_payload()
5. Inject memories: inject_user_memory()
6. Apply filters: process_filter_functions() [inlet]
7. RAG: get_sources_from_items() if files/knowledge
8. Tool calling: execute_tool_calls() if tools enabled
9. Execute: generate_chat_completion() [OpenAI/Ollama]
10. Apply filters: process_filter_functions() [outlet]
11. Stream: Socket.IO emits chunks to frontend
12. Background: generate_title(), apply_tags_to_chat()
13. Return: Streaming response complete
```

### Plugin Loading Workflow
```
1. Request needs custom function (tool or filter)
2. Load: load_function_module_by_id(function_id)
3. Extract frontmatter: extract_frontmatter(code)
4. Install requirements: install_requirements()
5. Create module: create_module_from_string()
6. Execute: module.execute(params)
7. Return: Result to caller
```

### OAuth Authentication Workflow
```
1. User clicks "Sign in with Google"
2. Frontend redirects to /api/oauth/google
3. Backend: oauth.get_oauth_provider("google")
4. Redirect to Google OAuth consent screen
5. User approves
6. Google redirects to /api/oauth/google/callback
7. Backend: oauth_callback("google", code, state)
8. Verify token: verify_id_token()
9. Create or get user: Users.get_user_by_email()
10. Generate JWT: create_token()
11. Redirect to frontend with token
```

### RAG Query Workflow
```
1. User sends message with file attached
2. Middleware: get_sources_from_items([file_id], query)
3. Retrieval: Generate query embedding
4. Vector DB: Search top-k chunks
5. Task: rag_template(template, chunks, query)
6. Middleware: Prepend chunks to system message
7. Chat: generate_chat_completion() with RAG context
8. Return: LLM response with grounded information
```

## Important Notes

### Critical Dependencies
- All routers depend on `auth.py` for authentication
- `middleware.py` is the orchestrator for all chat completions
- `plugin.py` enables extensibility but has security risks
- `telemetry/` requires OpenTelemetry SDK

### Security Considerations
- **Plugin Execution:** Arbitrary code from database (needs sandboxing)
- **OAuth:** Verify all ID tokens, validate redirect URIs
- **JWT:** Tokens in localStorage (XSS risk), no refresh tokens
- **Code Interpreter:** Limited sandboxing, potential RCE
- **Webhook:** Validate URLs, prevent SSRF

### Performance Considerations
- `middleware.py` is on critical path for all chat requests
- Plugin loading is synchronous (consider caching)
- Redis used for distributed session management (high throughput)
- Telemetry overhead (disable in production if needed)

### Configuration
- Environment variables in `env.py` control all util behavior
- `SRC_LOG_LEVELS` dict controls per-module logging
- `PIP_OPTIONS` controls plugin dependency installation
- `REDIS_URL` enables distributed session management
- `WEBUI_AUTH_TRUSTED_EMAIL_HEADER` for proxy authentication

### Testing Considerations
- Mock external services (OpenAI, Ollama, Redis)
- Test plugin loading with sample functions
- Test middleware pipeline with various payloads
- Test OAuth with mock providers
- Test telemetry with test exporters
