# Open WebUI - API Quick Reference

> **Version:** 0.6.34
> **Last Updated:** 2025-11-05
> **Full API Docs:** http://localhost:8080/docs (FastAPI Swagger UI)

---

## Table of Contents

- [1. Authentication](#1-authentication)
- [2. Chat APIs](#2-chat-apis)
- [3. Knowledge & Files](#3-knowledge--files)
- [4. Models](#4-models)
- [5. Functions & Tools](#5-functions--tools)
- [6. User Management](#6-user-management)
- [7. RAG & Retrieval](#7-rag--retrieval)
- [8. WebSocket Events](#8-websocket-events)

---

## Base URL

```
Development: http://localhost:8080/api
Production:  https://your-domain.com/api
```

## Authentication

All API requests (except `/auths/signup` and `/auths/signin`) require a JWT token in the `Authorization` header:

```http
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## 1. Authentication

### Sign Up

```http
POST /api/auths/signup
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "user_123",
    "name": "John Doe",
    "email": "john@example.com",
    "role": "user",
    "created_at": 1699564800
  }
}
```

### Sign In

```http
POST /api/auths/signin
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "secure_password"
}
```

**Response:** Same as Sign Up

### Get Current User

```http
GET /api/auths/
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "id": "user_123",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "user",
  "profile_image_url": "...",
  "last_active_at": 1699564800
}
```

---

## 2. Chat APIs

### List Chats

```http
GET /api/chats/
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
[
  {
    "id": "chat_abc123",
    "user_id": "user_123",
    "title": "My Chat",
    "created_at": 1699564800,
    "updated_at": 1699564900,
    "pinned": false,
    "archived": false
  }
]
```

### Get Chat by ID

```http
GET /api/chats/{chat_id}
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "id": "chat_abc123",
  "user_id": "user_123",
  "title": "My Chat",
  "chat": {
    "messages": [
      {
        "id": "msg_1",
        "role": "user",
        "content": "Hello!",
        "timestamp": 1699564800
      },
      {
        "id": "msg_2",
        "role": "assistant",
        "content": "Hi! How can I help?",
        "timestamp": 1699564801
      }
    ]
  },
  "created_at": 1699564800,
  "updated_at": 1699564900
}
```

### Create Chat

```http
POST /api/chats/new
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "chat": {
    "title": "New Chat",
    "models": ["gpt-4"],
    "messages": []
  }
}
```

### Update Chat

```http
POST /api/chats/{chat_id}
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "chat": {
    "title": "Updated Title",
    "messages": [...]
  }
}
```

### Delete Chat

```http
DELETE /api/chats/{chat_id}
Authorization: Bearer YOUR_TOKEN
```

### Share Chat

```http
POST /api/chats/{chat_id}/share
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "share_id": "abc123def456",
  "url": "https://yourinstance.com/s/abc123def456"
}
```

---

## 3. Knowledge & Files

### List Knowledge Collections

```http
GET /api/knowledge/
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
[
  {
    "id": "knowledge_123",
    "name": "Project Documentation",
    "description": "All project docs",
    "user_id": "user_123",
    "created_at": 1699564800,
    "data": {
      "file_ids": ["file_1", "file_2"]
    }
  }
]
```

### Create Knowledge Collection

```http
POST /api/knowledge/create
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "My Knowledge Base",
  "description": "Collection of important documents"
}
```

### Add File to Knowledge

```http
POST /api/knowledge/{knowledge_id}/file/add
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "file_id": "file_123"
}
```

### Upload File

```http
POST /api/files/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

file: (binary data)
```

**Response:**
```json
{
  "id": "file_123",
  "filename": "document.pdf",
  "user_id": "user_123",
  "created_at": 1699564800
}
```

### List Files

```http
GET /api/files/
Authorization: Bearer YOUR_TOKEN
```

### Delete File

```http
DELETE /api/files/{file_id}
Authorization: Bearer YOUR_TOKEN
```

---

## 4. Models

### List Models

```http
GET /api/models/
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "models": [
    {
      "id": "gpt-4",
      "name": "GPT-4",
      "owned_by": "openai",
      "created": 1687882411
    },
    {
      "id": "llama3.3:70b",
      "name": "Llama 3.3 70B",
      "owned_by": "ollama",
      "created": 1699564800
    }
  ]
}
```

### Pull Model (Ollama)

```http
POST /api/models/pull
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "llama3.3:70b"
}
```

### Create Custom Model

```http
POST /api/models/create
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "my-custom-model",
  "base_model": "llama3.3:70b",
  "params": {
    "system": "You are a helpful assistant specialized in coding.",
    "temperature": 0.7,
    "top_p": 0.9
  }
}
```

---

## 5. Functions & Tools

### List Functions

```http
GET /api/functions/
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
[
  {
    "id": "func_123",
    "name": "get_weather",
    "type": "function",
    "user_id": "user_123",
    "content": "def get_weather(location: str): ...",
    "is_active": true,
    "is_global": false
  }
]
```

### Create Function

```http
POST /api/functions/create
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "my_function",
  "type": "function",
  "content": "def my_function(param: str) -> str:\n    return param.upper()"
}
```

### Update Function

```http
POST /api/functions/update
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "id": "func_123",
  "content": "def my_function(param: str) -> str:\n    return param.lower()"
}
```

### Delete Function

```http
DELETE /api/functions/{function_id}
Authorization: Bearer YOUR_TOKEN
```

### Execute Function (Test)

```http
POST /api/functions/{function_id}/test
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "args": {
    "param": "test"
  }
}
```

---

## 6. User Management

### List Users (Admin Only)

```http
GET /api/users/
Authorization: Bearer ADMIN_TOKEN
```

### Get User by ID

```http
GET /api/users/{user_id}
Authorization: Bearer YOUR_TOKEN
```

### Update User

```http
POST /api/users/{user_id}/update
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "New Name",
  "profile_image_url": "https://..."
}
```

### Update User Role (Admin Only)

```http
POST /api/users/{user_id}/role
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json

{
  "role": "admin"
}
```

### Delete User (Admin Only)

```http
DELETE /api/users/{user_id}
Authorization: Bearer ADMIN_TOKEN
```

---

## 7. RAG & Retrieval

### Query Knowledge

```http
POST /api/retrieval/query
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "query": "What is the project structure?",
  "knowledge_ids": ["knowledge_123"],
  "top_k": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "content": "The project is structured as follows...",
      "score": 0.95,
      "metadata": {
        "file_id": "file_123",
        "filename": "README.md"
      }
    }
  ]
}
```

### Web Search

```http
POST /api/retrieval/web
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "query": "Latest AI news",
  "count": 5
}
```

### Process Document

```http
POST /api/retrieval/process
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "file_id": "file_123",
  "knowledge_id": "knowledge_123"
}
```

---

## 8. WebSocket Events

### Connect

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8080', {
  auth: { token: 'YOUR_JWT_TOKEN' },
  transports: ['websocket', 'polling']
});

socket.on('connect', () => {
  console.log('Connected to WebSocket');
});
```

### Join Chat Room

```javascript
socket.emit('join_chat', { chat_id: 'chat_abc123' });
```

### Send Message

```javascript
socket.emit('message', {
  chat_id: 'chat_abc123',
  message: {
    role: 'user',
    content: 'Hello!'
  }
});
```

### Receive Messages

```javascript
socket.on('message', (data) => {
  console.log('New message:', data);
});
```

### User Joined

```javascript
socket.on('user_join', (data) => {
  console.log('User joined:', data.user_id);
});
```

### User Left

```javascript
socket.on('user_leave', (data) => {
  console.log('User left:', data.user_id);
});
```

---

## OpenAI-Compatible Chat Completions API

Open WebUI provides an OpenAI-compatible endpoint for easy integration:

```http
POST /api/openai/v1/chat/completions
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1699564800,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hi! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

### Streaming

```http
POST /api/openai/v1/chat/completions
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [{"role": "user", "content": "Write a poem"}],
  "stream": true
}
```

**Response:** Server-Sent Events (SSE)
```
data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"Once "}}]}

data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"upon "}}]}

data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"a "}}]}

data: [DONE]
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

---

## Rate Limiting

Rate limits can be configured by admin:

- **Default:** 100 requests per minute per user
- **Admins:** No rate limit (configurable)

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699564860
```

---

## API Keys

Instead of JWT tokens, you can use API keys:

### Create API Key

```http
POST /api/users/api_key
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "name": "My API Key"
}
```

**Response:**
```json
{
  "api_key": "sk-abc123def456...",
  "name": "My API Key",
  "created_at": 1699564800
}
```

### Use API Key

```http
GET /api/chats/
Authorization: Bearer sk-abc123def456...
```

---

## Examples

### cURL Examples

**Create Chat:**
```bash
curl -X POST http://localhost:8080/api/chats/new \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"chat": {"title": "New Chat", "messages": []}}'
```

**Upload File:**
```bash
curl -X POST http://localhost:8080/api/files/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

### Python Example

```python
import requests

BASE_URL = "http://localhost:8080/api"
TOKEN = "your_jwt_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Get chats
response = requests.get(f"{BASE_URL}/chats/", headers=headers)
chats = response.json()

print(f"Found {len(chats)} chats")
```

### JavaScript Example

```javascript
const BASE_URL = 'http://localhost:8080/api';
const TOKEN = 'your_jwt_token';

async function getChats() {
  const response = await fetch(`${BASE_URL}/chats/`, {
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type': 'application/json'
    }
  });

  const chats = await response.json();
  console.log(`Found ${chats.length} chats`);
}

getChats();
```

---

## Full API Documentation

For complete, interactive API documentation with all endpoints, request/response schemas, and the ability to test APIs directly:

**Visit:** http://localhost:8080/docs (FastAPI Swagger UI)

Or: http://localhost:8080/redoc (ReDoc format)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-05
**Maintained by:** Open WebUI Team
