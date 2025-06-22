# Code Structure and Organization

## Backend Structure (`backend/open_webui/`)

- **`main.py`**: Main FastAPI application entry point
- **`config.py`**: Configuration management and environment variables
- **`env.py`**: Environment setup and constants
- **`constants.py`**: Application constants and message templates
- **`functions.py`**: Function execution and management
- **`tasks.py`**: Background task management

## Router Organization (`backend/open_webui/routers/`)

Each router handles a specific domain:

- **`auths.py`**: Authentication and authorization
- **`users.py`**: User management
- **`chats.py`**: Chat conversations
- **`models.py`**: AI model management
- **`prompts.py`**: Prompt templates
- **`tools.py`**: Tool management
- **`functions.py`**: Function management
- **`files.py`**: File upload/management
- **`images.py`**: Image generation
- **`audio.py`**: Speech-to-text and text-to-speech
- **`retrieval.py`**: RAG and document processing
- **`memories.py`**: Memory management
- **`knowledge.py`**: Knowledge base management
- **`ollama.py`**: Ollama integration
- **`openai.py`**: OpenAI API integration
- **`pipelines.py`**: Pipeline management
- **`configs.py`**: Configuration management

## Database Models (`backend/open_webui/models/`)

- **`users.py`**: User model and settings
- **`chats.py`**: Chat conversations
- **`models.py`**: AI model definitions
- **`files.py`**: File metadata
- **`auths.py`**: Authentication data
- **`prompts.py`**: Prompt templates
- **`tools.py`**: Tool definitions
- **`functions.py`**: Function definitions
- **`memories.py`**: Memory storage
- **`knowledge.py`**: Knowledge base
- **`channels.py`**: Communication channels
- **`folders.py`**: Organization folders
- **`feedbacks.py`**: User feedback

## Frontend Structure (`src/`)

- **`app.html`**: Main HTML template
- **`app.css`**: Global styles
- **`lib/`**: Reusable components and utilities
- **`routes/`**: SvelteKit page routes

## Utilities (`backend/open_webui/utils/`)

- **`auth.py`**: Authentication utilities
- **`misc.py`**: General utilities
- **`models.py`**: Model utilities
- **`chat.py`**: Chat processing
- **`middleware.py`**: Request/response processing
- **`tools.py`**: Tool execution
- **`embeddings.py`**: Embedding generation
- **`code_interpreter.py`**: Code execution
- **`filter.py`**: Content filtering
- **`plugin.py`**: Plugin management
