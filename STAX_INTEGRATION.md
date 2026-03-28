# Open WebUI STAX AI Stack Integration

This document describes how to integrate Open WebUI with the STAX AI infrastructure.

## Overview

Open WebUI has been configured to use STAX AI stack endpoints for LLM inference and vector storage:

- **LiteLLM Gateway**: `https://litellm.spooty.io` - Unified API gateway (OpenAI-compatible)
- **Ollama**: `https://ollama.spooty.io` - Local model serving for open-source models
- **Qdrant**: `https://qdrant.spooty.io` - Vector database for RAG (Retrieval-Augmented Generation)

## Quick Start

### Option 1: Use the STAX Environment File

```bash
# Copy STAX configuration
cp .env.stax .env

# Or merge with existing .env
cat .env.stax >> .env

# Start Open WebUI
docker compose up -d
# OR for development:
cd backend && python -m open_webui serve
```

### Option 2: Manual Configuration

Edit your `.env` file:

```bash
# Ollama
OLLAMA_BASE_URL='https://ollama.spooty.io'

# OpenAI-Compatible (LiteLLM)
OPENAI_API_BASE_URL='https://litellm.spooty.io/v1'
OPENAI_API_KEY='sk-spark-litellm-master-key'

# Qdrant Vector DB
VECTOR_DB='qdrant'
QDRANT_URI='https://qdrant.spooty.io:6333'

# Enable APIs
ENABLE_OLLAMA_API='True'
ENABLE_OPENAI_API='True'
```

## Configuration Details

### Architecture

```
Open WebUI → {
  - Ollama API (https://ollama.spooty.io)
  - OpenAI-Compatible API (https://litellm.spooty.io/v1)
  - Qdrant Vector DB (https://qdrant.spooty.io:6333)
}
```

### Ollama Configuration

**Environment Variables:**
- `OLLAMA_BASE_URL`: Primary Ollama endpoint
- `OLLAMA_BASE_URLS`: Multiple Ollama endpoints (semicolon-separated)

**Example:**
```bash
# Single endpoint
OLLAMA_BASE_URL='https://ollama.spooty.io'

# Multiple endpoints (fallback/load-balancing)
OLLAMA_BASE_URLS='https://ollama.spooty.io;http://localhost:11434'
```

**Available Models:**
Check available models via API:
```bash
curl https://ollama.spooty.io/api/tags
```

Common models:
- `llama3.3:latest` - Llama 3.3 70B
- `qwen2.5-coder:latest` - Qwen 2.5 Coder
- `codestral:latest` - Mistral Codestral
- `mistral:latest` - Mistral 7B

### OpenAI-Compatible Configuration (LiteLLM)

**Environment Variables:**
- `OPENAI_API_BASE_URL`: Primary OpenAI-compatible endpoint
- `OPENAI_API_KEY`: API key for authentication
- `OPENAI_API_BASE_URLS`: Multiple endpoints (semicolon-separated)
- `OPENAI_API_KEYS`: Corresponding keys (semicolon-separated)

**Example:**
```bash
# Single endpoint
OPENAI_API_BASE_URL='https://litellm.spooty.io/v1'
OPENAI_API_KEY='sk-spark-litellm-master-key'

# Multiple endpoints
OPENAI_API_BASE_URLS='https://litellm.spooty.io/v1;https://api.openai.com/v1'
OPENAI_API_KEYS='sk-spark-litellm-master-key;sk-your-openai-key'
```

**Available Models:**
Check available models:
```bash
curl https://litellm.spooty.io/v1/models \
  -H "Authorization: Bearer sk-spark-litellm-master-key"
```

LiteLLM proxies to:
- **OpenAI**: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
- **Anthropic**: claude-sonnet-4, claude-3-5-sonnet-20241022, claude-3-opus-20240229
- **Google**: gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash
- **Meta**: llama-3.1-405b, llama-3.1-70b, llama-3.1-8b
- **Mistral**: mistral-large, mistral-medium, mistral-small
- And many more...

### Qdrant Vector Database

**Environment Variables:**
- `VECTOR_DB`: Set to `qdrant` to use Qdrant
- `QDRANT_URI`: Qdrant HTTP endpoint
- `QDRANT_API_KEY`: Optional API key (if auth enabled)
- `QDRANT_PREFER_GRPC`: Use gRPC instead of HTTP (default: false)
- `QDRANT_GRPC_PORT`: gRPC port (default: 6334)
- `QDRANT_TIMEOUT`: Request timeout in seconds (default: 5)

**Example:**
```bash
VECTOR_DB='qdrant'
QDRANT_URI='https://qdrant.spooty.io:6333'
# QDRANT_API_KEY=''  # Add if authentication is configured
QDRANT_PREFER_GRPC='false'
QDRANT_GRPC_PORT='6334'
QDRANT_TIMEOUT='10'
```

**Storage:**
- Collections are created automatically when you upload documents
- Each knowledge base gets a dedicated collection
- Point payloads include metadata (source, page numbers, etc.)

### RAG (Retrieval-Augmented Generation) Configuration

**Embedding Models via LiteLLM:**
```bash
RAG_EMBEDDING_ENGINE='openai'
RAG_EMBEDDING_MODEL='text-embedding-3-small'
RAG_EMBEDDING_OPENAI_BATCH_SIZE='1'
```

**Alternative: Embedding Models via Ollama:**
```bash
RAG_EMBEDDING_ENGINE='ollama'
RAG_EMBEDDING_MODEL='nomic-embed-text'
RAG_OPENAI_API_BASE_URL='https://ollama.spooty.io'
```

**Important Environment Variables:**
- `RAG_EMBEDDING_ENGINE`: `openai` or `ollama`
- `RAG_EMBEDDING_MODEL`: Model name
- `RAG_EMBEDDING_BATCH_SIZE`: Number of texts to embed in parallel
- `RAG_TOP_K`: Number of chunks to retrieve (default: 5)
- `RAG_RELEVANCE_THRESHOLD`: Minimum similarity score (default: 0.0)

## How Open WebUI Uses STAX Backends

### Model Discovery

1. **On Startup**: Open WebUI queries all configured backends
   - Ollama: `GET /api/tags`
   - OpenAI-compatible: `GET /v1/models`
2. **Model List**: All models are merged and displayed in the UI
3. **User Selection**: Users select models from the combined list

### Chat Completion

When a user sends a message:

1. **Model Routing**: Open WebUI determines the backend based on model ID
   - Ollama models route to Ollama backend
   - Other models route to OpenAI-compatible backend
2. **API Call**: Request forwarded to appropriate backend
3. **Streaming**: Response streamed back to user in real-time

### Document Upload & RAG

When a user uploads a document:

1. **Text Extraction**: Document parsed and split into chunks
2. **Embedding Generation**: Chunks embedded using configured embedding model
   - Via Ollama: `POST https://ollama.spooty.io/api/embeddings`
   - Via LiteLLM: `POST https://litellm.spooty.io/v1/embeddings`
3. **Vector Storage**: Embeddings stored in Qdrant
4. **Retrieval**: During chat, relevant chunks retrieved from Qdrant
5. **Context Injection**: Retrieved chunks added to prompt

## Usage

### Accessing the UI

After starting Open WebUI:
```
http://localhost:8080
```

### Selecting Models

1. Click the model dropdown in the chat interface
2. You'll see models from both Ollama and LiteLLM
3. Select any model to start chatting

### Using RAG

1. Go to **Workspace** → **Knowledge**
2. Click **+ Create Knowledge Base**
3. Upload documents (PDF, TXT, MD, etc.)
4. In chat, click **+** → **Knowledge** → Select your knowledge base
5. Ask questions about your documents

## Testing the Integration

### Test Ollama Connection

```bash
# List models
curl https://ollama.spooty.io/api/tags

# Generate completion
curl -X POST https://ollama.spooty.io/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.3:latest",
    "prompt": "Hello, how are you?",
    "stream": false
  }'
```

### Test LiteLLM Connection

```bash
# List models
curl https://litellm.spooty.io/v1/models \
  -H "Authorization: Bearer sk-spark-litellm-master-key"

# Chat completion
curl -X POST https://litellm.spooty.io/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-spark-litellm-master-key" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'

# Generate embeddings
curl -X POST https://litellm.spooty.io/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-spark-litellm-master-key" \
  -d '{
    "model": "text-embedding-3-small",
    "input": "The quick brown fox"
  }'
```

### Test Qdrant Connection

```bash
# Health check
curl https://qdrant.spooty.io:6333/health

# List collections
curl https://qdrant.spooty.io:6333/collections

# Create test collection
curl -X PUT https://qdrant.spooty.io:6333/collections/test \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    }
  }'
```

## Environment Variable Reference

### Core Settings

```bash
# Ollama
OLLAMA_BASE_URL='https://ollama.spooty.io'
OLLAMA_BASE_URLS='https://ollama.spooty.io'  # Semicolon-separated list
ENABLE_OLLAMA_API='True'

# OpenAI-Compatible (LiteLLM)
OPENAI_API_BASE_URL='https://litellm.spooty.io/v1'
OPENAI_API_KEY='sk-spark-litellm-master-key'
OPENAI_API_BASE_URLS='https://litellm.spooty.io/v1'  # Semicolon-separated list
OPENAI_API_KEYS='sk-spark-litellm-master-key'  # Semicolon-separated list
ENABLE_OPENAI_API='True'

# Vector Database
VECTOR_DB='qdrant'
QDRANT_URI='https://qdrant.spooty.io:6333'
QDRANT_API_KEY=''
QDRANT_PREFER_GRPC='false'
QDRANT_GRPC_PORT='6334'
QDRANT_TIMEOUT='10'

# RAG Configuration
RAG_EMBEDDING_ENGINE='openai'  # or 'ollama'
RAG_EMBEDDING_MODEL='text-embedding-3-small'
RAG_EMBEDDING_BATCH_SIZE='1'
RAG_TOP_K='5'
RAG_RELEVANCE_THRESHOLD='0.0'

# Alternative Ollama embeddings
# RAG_EMBEDDING_ENGINE='ollama'
# RAG_EMBEDDING_MODEL='nomic-embed-text'
# RAG_OPENAI_API_BASE_URL='https://ollama.spooty.io'

# CORS & Telemetry
CORS_ALLOW_ORIGIN='*'
FORWARDED_ALLOW_IPS='*'
SCARF_NO_ANALYTICS='true'
DO_NOT_TRACK='true'
ANONYMIZED_TELEMETRY='false'
```

### Advanced Settings

```bash
# Direct connections (allow clients to connect directly to backends)
ENABLE_DIRECT_CONNECTIONS='false'

# Model caching
ENABLE_BASE_MODELS_CACHE='true'

# RAG Advanced
RAG_FULL_CONTEXT='false'
BYPASS_EMBEDDING_AND_RETRIEVAL='false'
RAG_EMBEDDING_MODEL_AUTO_UPDATE='false'
RAG_RERANKING_ENGINE=''
RAG_RERANKING_MODEL=''
RAG_TOP_K_RERANKER='1'
RAG_HYBRID_BM25_WEIGHT='0.5'

# Thread pool size
THREAD_POOL_SIZE='8'
```

## Docker Compose Configuration

For Docker deployments, you can pass environment variables via `docker-compose.yaml`:

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "8080:8080"
    environment:
      - OLLAMA_BASE_URL=https://ollama.spooty.io
      - OPENAI_API_BASE_URL=https://litellm.spooty.io/v1
      - OPENAI_API_KEY=sk-spark-litellm-master-key
      - VECTOR_DB=qdrant
      - QDRANT_URI=https://qdrant.spooty.io:6333
      - ENABLE_OLLAMA_API=True
      - ENABLE_OPENAI_API=True
    volumes:
      - open-webui:/app/backend/data
    restart: unless-stopped

volumes:
  open-webui:
```

## Troubleshooting

### Models Not Showing Up

1. **Check backend connectivity**:
   ```bash
   curl https://ollama.spooty.io/api/tags
   curl https://litellm.spooty.io/v1/models -H "Authorization: Bearer sk-spark-litellm-master-key"
   ```

2. **Check Open WebUI logs**:
   ```bash
   docker compose logs -f open-webui
   ```

3. **Verify environment variables**:
   ```bash
   docker compose config | grep -A 10 environment
   ```

### RAG Not Working

1. **Check Qdrant connectivity**:
   ```bash
   curl https://qdrant.spooty.io:6333/health
   ```

2. **Verify embedding model**:
   ```bash
   # For OpenAI embeddings
   curl -X POST https://litellm.spooty.io/v1/embeddings \
     -H "Authorization: Bearer sk-spark-litellm-master-key" \
     -H "Content-Type: application/json" \
     -d '{"model":"text-embedding-3-small","input":"test"}'

   # For Ollama embeddings
   curl -X POST https://ollama.spooty.io/api/embeddings \
     -H "Content-Type: application/json" \
     -d '{"model":"nomic-embed-text","prompt":"test"}'
   ```

3. **Check collection creation**:
   ```bash
   curl https://qdrant.spooty.io:6333/collections
   ```

### Connection Timeouts

If you experience timeouts:

1. **Increase timeouts**:
   ```bash
   QDRANT_TIMEOUT='30'
   OLLAMA_REQUEST_TIMEOUT='300'
   OPENAI_REQUEST_TIMEOUT='300'
   ```

2. **Check network connectivity**:
   ```bash
   ping qdrant.spooty.io
   telnet ollama.spooty.io 443
   telnet litellm.spooty.io 443
   ```

### Invalid API Keys

If LiteLLM returns 401 errors:

1. **Verify the API key**:
   ```bash
   echo $OPENAI_API_KEY
   ```

2. **Test authentication**:
   ```bash
   curl https://litellm.spooty.io/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

## Security Considerations

1. **API Key Management**:
   - Store API keys in `.env` file (never commit to git)
   - Use environment variables in production
   - Rotate keys periodically

2. **Network Security**:
   - STAX endpoints use HTTPS/TLS
   - Qdrant supports authentication via `QDRANT_API_KEY` (optional)
   - Consider using VPN or private network for production

3. **CORS Configuration**:
   - `CORS_ALLOW_ORIGIN='*'` is permissive (suitable for development)
   - In production, specify exact origins:
     ```bash
     CORS_ALLOW_ORIGIN='https://chat.example.com'
     ```

## Performance Tuning

### Embedding Generation

```bash
# Increase batch size for faster embedding (if backend supports it)
RAG_EMBEDDING_BATCH_SIZE='10'

# Enable async embedding
ENABLE_ASYNC_EMBEDDING='true'
RAG_EMBEDDING_CONCURRENT_REQUESTS='8'
```

### Qdrant Optimization

```bash
# Use gRPC for better performance (if available)
QDRANT_PREFER_GRPC='true'

# Increase timeout for large documents
QDRANT_TIMEOUT='30'
```

### Model Caching

```bash
# Cache model lists to reduce backend queries
ENABLE_BASE_MODELS_CACHE='true'
```

## Advanced: Multiple Backends

You can configure multiple backends for redundancy or load distribution:

```bash
# Multiple Ollama instances
OLLAMA_BASE_URLS='https://ollama.spooty.io;http://ollama2.internal:11434'

# Multiple OpenAI-compatible endpoints
OPENAI_API_BASE_URLS='https://litellm.spooty.io/v1;https://api.openai.com/v1'
OPENAI_API_KEYS='sk-spark-litellm-master-key;sk-openai-key'
```

Open WebUI will:
1. Query all backends for available models
2. Merge model lists
3. Route requests to the appropriate backend based on model ID

## References

- Open WebUI Documentation: https://docs.openwebui.com/
- Open WebUI GitHub: https://github.com/open-webui/open-webui
- LiteLLM Documentation: https://docs.litellm.ai/
- Ollama API Documentation: https://github.com/ollama/ollama/blob/main/docs/api.md
- Qdrant Documentation: https://qdrant.tech/documentation/
- Environment Variables Reference: https://docs.openwebui.com/getting-started/env-configuration/
