# Open WebUI API Documentation for Raycast Extension

This document provides complete API documentation for building a Raycast extension that integrates with Open WebUI. All API requests must be authenticated, and chat history will automatically sync between the Raycast extension and the web frontend.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Core Endpoints](#core-endpoints)
  - [Authentication Endpoints](#authentication-endpoints)
  - [Chat Management Endpoints](#chat-management-endpoints)
  - [AI Interaction Endpoints](#ai-interaction-endpoints)
  - [Model Endpoints](#model-endpoints)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Example Usage](#example-usage)

---

## Base URL

All API endpoints are relative to your Open WebUI instance:

```
https://your-openwebui-instance.com/api/v1
```

For example, if your Open WebUI is hosted at `https://chat.example.com`, the base URL would be:
```
https://chat.example.com/api/v1
```

---

## Authentication

### Overview

Open WebUI supports two authentication methods for third-party integrations:

1. **JWT Token** - Session-based authentication (requires re-authentication)
2. **API Key** - Long-lived authentication (recommended for Raycast)

### API Key Authentication (Recommended)

API keys are the recommended method for third-party integrations like Raycast extensions.

#### Generating an API Key

Users must first generate an API key through the Open WebUI web interface or API:

**Endpoint:** `POST /api/v1/auths/api_key`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Response:**
```json
{
  "api_key": "sk-a1b2c3d4e5f6789..."
}
```

#### Using the API Key

Once generated, include the API key in all requests:

**Header:**
```
Authorization: sk-a1b2c3d4e5f6789...
```

Or alternatively:
```
Authorization: Bearer sk-a1b2c3d4e5f6789...
```

The system automatically detects the `sk-` prefix and validates it as an API key.

#### Managing API Keys

**Get Current API Key:**
```
GET /api/v1/auths/api_key
Authorization: Bearer {jwt_token}
```

**Delete API Key:**
```
DELETE /api/v1/auths/api_key
Authorization: Bearer {jwt_token}
```

---

## Core Endpoints

### Authentication Endpoints

#### Get Current User Info

Verify your connection and retrieve user information.

**Endpoint:** `GET /api/v1/auths/`

**Headers:**
```
Authorization: {api_key}
```

**Response:**
```json
{
  "token": "jwt_token_here",
  "token_type": "Bearer",
  "expires_at": 1700000000,
  "id": "user-uuid",
  "email": "user@example.com",
  "name": "User Name",
  "role": "user",
  "profile_image_url": "/user.png",
  "permissions": {
    "chat": {
      "delete": true,
      "edit": true
    }
  }
}
```

#### Sign In (For JWT Token)

Only needed if you want to use JWT instead of API keys.

**Endpoint:** `POST /api/v1/auths/signin`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_at": 1700000000,
  "id": "user-uuid",
  "email": "user@example.com",
  "name": "User Name",
  "role": "user",
  "profile_image_url": "/user.png",
  "permissions": {}
}
```

---

### Chat Management Endpoints

#### List Chats

Retrieve a paginated list of the user's chats.

**Endpoint:** `GET /api/v1/chats/` or `GET /api/v1/chats/list`

**Headers:**
```
Authorization: {api_key}
```

**Query Parameters:**
- `page` (optional): Page number (default: returns all chats)
- `include_pinned` (optional): Include pinned chats (default: false)
- `include_folders` (optional): Include chats in folders (default: false)

**Example Request:**
```
GET /api/v1/chats/list?page=1
Authorization: sk-abc123...
```

**Response:**
```json
[
  {
    "id": "chat-uuid-1",
    "title": "My First Chat",
    "updated_at": 1700000000,
    "created_at": 1699999000
  },
  {
    "id": "chat-uuid-2",
    "title": "Another Conversation",
    "updated_at": 1700000100,
    "created_at": 1699999100
  }
]
```

**Notes:**
- Default page size is 60 chats
- Results are ordered by `updated_at` descending (most recent first)

#### Get Specific Chat

Retrieve full details of a specific chat by ID.

**Endpoint:** `GET /api/v1/chats/{id}`

**Headers:**
```
Authorization: {api_key}
```

**Response:**
```json
{
  "id": "chat-uuid",
  "user_id": "user-uuid",
  "title": "My Chat",
  "chat": {
    "title": "My Chat",
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      },
      {
        "role": "assistant",
        "content": "Hi there! How can I help you?"
      }
    ],
    "history": {
      "currentId": "msg-uuid",
      "messages": {
        "msg-uuid": {
          "role": "assistant",
          "content": "Hi there! How can I help you?"
        }
      }
    }
  },
  "created_at": 1699999000,
  "updated_at": 1700000000,
  "share_id": null,
  "archived": false,
  "pinned": false,
  "meta": {},
  "folder_id": null
}
```

#### Create New Chat

Create a new chat/conversation.

**Endpoint:** `POST /api/v1/chats/new`

**Headers:**
```
Authorization: {api_key}
Content-Type: application/json
```

**Request Body (Recommended Structure):**
```json
{
  "chat": {
    "title": "My Chat Title",
    "models": ["gpt-4"],
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      },
      {
        "role": "assistant",
        "content": "Hi there!"
      }
    ],
    "history": {
      "messages": {
        "msg-uuid-1": {
          "id": "msg-uuid-1",
          "role": "user",
          "content": "Hello!",
          "parentId": null,
          "childrenIds": ["msg-uuid-2"]
        },
        "msg-uuid-2": {
          "id": "msg-uuid-2",
          "role": "assistant",
          "content": "Hi there!",
          "parentId": "msg-uuid-1",
          "childrenIds": []
        }
      },
      "currentId": "msg-uuid-2"
    },
    "params": {},
    "timestamp": 1700000000
  },
  "folder_id": null
}
```

**⚠️ IMPORTANT: The `models` field is REQUIRED for chat continuation in the web UI.**

If you don't include `models`, the chat will show "undefined" as the model name and users won't be able to continue the conversation in the web interface.

**Simplified Request (with models):**
```json
{
  "chat": {
    "title": "Quick Chat",
    "models": ["gpt-4"],
    "messages": [
      {
        "role": "user",
        "content": "Hello"
      },
      {
        "role": "assistant",
        "content": "Hi!"
      }
    ]
  }
}
```

**Chat Object Structure:**
- `title` (string): Chat title (first 50 chars of user's first message is common)
- `models` (string[]): **REQUIRED** - Array of model IDs used in the chat (e.g., `["gpt-4"]`)
- `messages` (array): Linear array of messages (fallback if history not provided)
- `history` (object, optional but recommended): Message tree structure for branching conversations
  - `messages` (object): Map of message ID to message object
    - Each message has: `id`, `role`, `content`, `parentId`, `childrenIds`
  - `currentId` (string): ID of the most recent message in the conversation
- `params` (object, optional): Model parameters like `temperature`, `max_tokens`, etc.
- `timestamp` (number, optional): Unix timestamp in milliseconds

**Response:**
```json
{
  "id": "new-chat-uuid",
  "user_id": "user-uuid",
  "title": "My Chat Title",
  "chat": {
    "title": "My Chat Title",
    "models": ["gpt-4"],
    "messages": [...],
    "history": {...}
  },
  "created_at": 1700000000,
  "updated_at": 1700000000,
  "share_id": null,
  "archived": false,
  "pinned": false,
  "meta": {},
  "folder_id": null
}
```

#### Update Chat

Update an existing chat's content.

**Endpoint:** `POST /api/v1/chats/{id}`

**Headers:**
```
Authorization: {api_key}
Content-Type: application/json
```

**Request Body:**
```json
{
  "chat": {
    "title": "Updated Title",
    "models": ["gpt-4"],
    "messages": [
      {
        "role": "user",
        "content": "First message"
      },
      {
        "role": "assistant",
        "content": "First response"
      },
      {
        "role": "user",
        "content": "New message"
      },
      {
        "role": "assistant",
        "content": "New response"
      }
    ],
    "history": {
      "messages": {
        "msg-1": {...},
        "msg-2": {...},
        "msg-3": {...},
        "msg-4": {...}
      },
      "currentId": "msg-4"
    },
    "params": {}
  }
}
```

**⚠️ IMPORTANT:** Always include the `models` array when updating, even if it hasn't changed. The update replaces the entire `chat` object.

**Response:**
```json
{
  "id": "chat-uuid",
  "user_id": "user-uuid",
  "title": "Updated Title",
  "chat": {
    "title": "Updated Title",
    "models": ["gpt-4"],
    "messages": [...],
    "history": {...}
  },
  "created_at": 1699999000,
  "updated_at": 1700000100,
  "share_id": null,
  "archived": false,
  "pinned": false,
  "meta": {},
  "folder_id": null
}
```

**Note:** The backend replaces the entire `chat` object with what you provide, so include all fields you want to preserve (especially `models`).

#### Delete Chat

Delete a specific chat.

**Endpoint:** `DELETE /api/v1/chats/{id}`

**Headers:**
```
Authorization: {api_key}
```

**Response:**
```json
true
```

#### Search Chats

Search through chats by text, tags, or filters.

**Endpoint:** `GET /api/v1/chats/search`

**Headers:**
```
Authorization: {api_key}
```

**Query Parameters:**
- `text` (required): Search query
- `page` (optional): Page number (default: 1)

**Example Request:**
```
GET /api/v1/chats/search?text=python&page=1
Authorization: sk-abc123...
```

**Advanced Search:**
```
GET /api/v1/chats/search?text=tag:important pinned:true
```

**Search Filters:**
- `tag:{tag_name}` - Filter by tag
- `folder:{folder_name}` - Filter by folder
- `pinned:true` or `pinned:false` - Filter by pinned status
- `archived:true` or `archived:false` - Filter by archived status
- `shared:true` or `shared:false` - Filter by shared status

**Response:**
```json
[
  {
    "id": "chat-uuid",
    "title": "Python Tutorial",
    "updated_at": 1700000000,
    "created_at": 1699999000
  }
]
```

#### Get All Chats

Retrieve all chats (full details, not paginated).

**Endpoint:** `GET /api/v1/chats/all`

**Headers:**
```
Authorization: {api_key}
```

**Response:**
```json
[
  {
    "id": "chat-uuid-1",
    "user_id": "user-uuid",
    "title": "Chat 1",
    "chat": {...},
    "created_at": 1699999000,
    "updated_at": 1700000000,
    "share_id": null,
    "archived": false,
    "pinned": false,
    "meta": {},
    "folder_id": null
  }
]
```

#### Get Pinned Chats

Retrieve only pinned chats.

**Endpoint:** `GET /api/v1/chats/pinned`

**Headers:**
```
Authorization: {api_key}
```

**Response:**
```json
[
  {
    "id": "pinned-chat-uuid",
    "title": "Important Chat",
    "updated_at": 1700000000,
    "created_at": 1699999000
  }
]
```

#### Pin/Unpin Chat

Toggle the pinned status of a chat.

**Endpoint:** `POST /api/v1/chats/{id}/pin`

**Headers:**
```
Authorization: {api_key}
```

**Response:**
```json
{
  "id": "chat-uuid",
  "user_id": "user-uuid",
  "title": "Chat Title",
  "chat": {...},
  "created_at": 1699999000,
  "updated_at": 1700000100,
  "share_id": null,
  "archived": false,
  "pinned": true,
  "meta": {},
  "folder_id": null
}
```

#### Archive/Unarchive Chat

Toggle the archived status of a chat.

**Endpoint:** `POST /api/v1/chats/{id}/archive`

**Headers:**
```
Authorization: {api_key}
```

**Response:**
```json
{
  "id": "chat-uuid",
  "archived": true,
  ...
}
```

#### Clone Chat

Create a copy of an existing chat.

**Endpoint:** `POST /api/v1/chats/{id}/clone`

**Headers:**
```
Authorization: {api_key}
Content-Type: application/json
```

**Request Body (optional):**
```json
{
  "title": "Custom Clone Title"
}
```

**Response:**
```json
{
  "id": "new-cloned-chat-uuid",
  "title": "Clone of Original Chat",
  ...
}
```

---

### AI Interaction Endpoints

#### Chat Completions

Send messages to AI models and receive responses.

**Endpoint:** `POST /api/v1/chat/completions`

**Headers:**
```
Authorization: {api_key}
Content-Type: application/json
```

**Request Body:**
```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "stream": false
}
```

**Full Request Example:**
```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What is the capital of France?"
    }
  ],
  "chat_id": "existing-chat-uuid",
  "stream": true,
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 1000,
  "reasoning_effort": "medium"
}
```

**Request Parameters:**
- `model` (required): Model ID to use
- `messages` (required): Array of message objects
- `chat_id` (optional): Existing chat ID to associate with
- `stream` (optional): Enable streaming responses (default: false)
- `temperature` (optional): Randomness (0-2, default: 0.7)
- `top_p` (optional): Nucleus sampling (0-1)
- `max_tokens` (optional): Maximum tokens to generate
- `reasoning_effort` (optional): Control reasoning depth for reasoning models. Accepts: `"low"`, `"medium"`, or `"high"`. Only applicable to reasoning models that support this parameter (e.g., OpenAI o1 models). Default varies by model.

**Response (Non-Streaming):**
```json
{
  "id": "chatcmpl-uuid",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  }
}
```

**Response (Streaming):**

When `stream: true`, the response is a stream of Server-Sent Events (SSE):

```
data: {"id":"chatcmpl-uuid","object":"chat.completion.chunk","created":1700000000,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"role":"assistant","content":"The"},"finish_reason":null}]}

data: {"id":"chatcmpl-uuid","object":"chat.completion.chunk","created":1700000000,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"content":" capital"},"finish_reason":null}]}

data: {"id":"chatcmpl-uuid","object":"chat.completion.chunk","created":1700000000,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"content":" of"},"finish_reason":null}]}

data: [DONE]
```

**Notes:**
- Streaming responses are recommended for better UX
- The `chat_id` parameter automatically saves the conversation
- If no `chat_id` is provided, you must manually save the conversation using the chat endpoints

---

### Model Endpoints

#### List Available Models

Get all models available to the current user. **This is the same endpoint used by the frontend's model selector/picker.**

**Endpoint:** `GET /api/v1/models/` or `GET /api/models` (both work identically)

**Headers:**
```
Authorization: {api_key}
```

**Query Parameters:**
- `refresh` (optional): Set to `true` to force refresh models from providers (default: false)

**Example Request:**
```
GET /api/v1/models/
Authorization: sk-abc123...
```

**Response:**
```json
{
  "data": [
    {
      "id": "gpt-3.5-turbo",
      "name": "GPT-3.5 Turbo",
      "object": "model",
      "created": 1699999000,
      "owned_by": "openai",
      "tags": [
        {
          "name": "OpenAI"
        },
        {
          "name": "Fast"
        }
      ],
      "info": {
        "meta": {
          "description": "Fast and efficient model for most tasks",
          "profile_image_url": "/static/favicon.png",
          "capabilities": {
            "vision": false,
            "usage": true
          },
          "tags": [
            {
              "name": "OpenAI"
            }
          ]
        },
        "params": {}
      }
    },
    {
      "id": "gpt-4",
      "name": "GPT-4",
      "object": "model",
      "created": 1699999000,
      "owned_by": "openai",
      "tags": [
        {
          "name": "OpenAI"
        },
        {
          "name": "Advanced"
        }
      ],
      "info": {
        "meta": {
          "description": "Most capable model for complex tasks",
          "profile_image_url": "/static/favicon.png",
          "capabilities": {
            "vision": true,
            "usage": true
          },
          "tags": [
            {
              "name": "OpenAI"
            }
          ]
        },
        "params": {}
      }
    },
    {
      "id": "llama3:latest",
      "name": "Llama 3",
      "object": "model",
      "created": 1699999000,
      "owned_by": "meta",
      "tags": [
        {
          "name": "Local"
        },
        {
          "name": "Open Source"
        }
      ],
      "info": {
        "meta": {
          "description": "Meta's open source language model",
          "capabilities": {
            "vision": false,
            "usage": true
          }
        }
      }
    }
  ]
}
```

**Response Structure:**
- `data`: Array of model objects
  - `id`: Unique model identifier (use this for API calls)
  - `name`: Human-readable model name (display this in UI)
  - `object`: Always "model"
  - `created`: Unix timestamp when model was added
  - `owned_by`: Model provider (e.g., "openai", "meta", "anthropic")
  - `tags`: Array of tag objects with `name` property (for categorization/filtering)
  - `info`: Additional model metadata
    - `meta.description`: Model description
    - `meta.profile_image_url`: Model icon/avatar
    - `meta.capabilities`: Object describing model capabilities
      - `vision`: Boolean - supports image input
      - `usage`: Boolean - tracks token usage
    - `meta.tags`: Tags defined in model metadata
    - `params`: Model-specific parameters

**Notes:**
- ✅ **This endpoint returns exactly what the frontend model picker uses**
- Only returns models the user has access to (filtered by permissions)
- Admin users with bypass enabled see all models
- Filter pipelines are automatically excluded from results
- Models are sorted according to `MODEL_ORDER_LIST` config if defined
- Tags are combined from both model metadata and model-level tags
- The `id` field is what you pass to `/api/v1/chat/completions` in the `model` parameter

---

## Data Models

### Chat Object

```typescript
interface Chat {
  id: string;
  user_id: string;
  title: string;
  chat: {
    title: string;
    messages?: Message[];
    history?: {
      currentId: string;
      messages: Record<string, Message>;
    };
    // Other custom fields
  };
  created_at: number;  // Unix timestamp
  updated_at: number;  // Unix timestamp
  share_id: string | null;
  archived: boolean;
  pinned: boolean;
  meta: {
    tags?: string[];
    // Other metadata
  };
  folder_id: string | null;
}
```

### Chat List Item

```typescript
interface ChatListItem {
  id: string;
  title: string;
  updated_at: number;
  created_at: number;
}
```

### Message Object

```typescript
interface Message {
  role: "system" | "user" | "assistant";
  content: string;
  // Optional fields
  name?: string;
  timestamp?: number;
}
```

### User Object

```typescript
interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "user" | "pending";
  profile_image_url: string;
  permissions: {
    chat?: {
      delete?: boolean;
      edit?: boolean;
      share?: boolean;
    };
    // Other permissions
  };
}
```

### Model Object

```typescript
interface Model {
  id: string;                    // Model ID to use in API calls
  name: string;                  // Display name
  object: "model";
  created: number;               // Unix timestamp
  owned_by: string;              // Provider (e.g., "openai", "meta")
  tags?: ModelTag[];             // Category tags
  info?: {
    meta?: {
      description?: string;
      profile_image_url?: string;
      capabilities?: {
        vision?: boolean;        // Supports image input
        usage?: boolean;         // Tracks token usage
      };
      tags?: ModelTag[];
    };
    params?: Record<string, any>;
  };
}

interface ModelTag {
  name: string;
}

interface ModelsResponse {
  data: Model[];
}
```

---

## Error Handling

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Invalid or missing authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**Invalid API Key:**
```json
{
  "detail": "Invalid token"
}
```

**Chat Not Found:**
```json
{
  "detail": "Not found"
}
```

**Permission Denied:**
```json
{
  "detail": "Access prohibited"
}
```

---

## Example Usage

### Complete Raycast Extension Flow

#### 1. Initial Setup

User generates an API key in Open WebUI and adds it to Raycast preferences.

#### 2. Verify Connection

```javascript
const response = await fetch('https://chat.example.com/api/v1/auths/', {
  headers: {
    'Authorization': 'sk-abc123...'
  }
});

const user = await response.json();
console.log(`Connected as: ${user.name}`);
```

#### 3. Get Available Models

```javascript
const response = await fetch('https://chat.example.com/api/v1/models/', {
  headers: {
    'Authorization': 'sk-abc123...'
  }
});

const modelsData = await response.json();
const models = modelsData.data;

// Display models in Raycast dropdown/picker
models.forEach(model => {
  console.log(`${model.name} (${model.id})`);
  // Example output: "GPT-4 (gpt-4)"
  //                 "Llama 3 (llama3:latest)"
});

// Get the selected model ID for later use
const selectedModelId = models[0].id; // e.g., "gpt-4"
```

#### 4. List Recent Chats

```javascript
const response = await fetch('https://chat.example.com/api/v1/chats/list?page=1', {
  headers: {
    'Authorization': 'sk-abc123...'
  }
});

const chats = await response.json();
// Display in Raycast list
```

#### 5. Create New Chat

```javascript
const response = await fetch('https://chat.example.com/api/v1/chats/new', {
  method: 'POST',
  headers: {
    'Authorization': 'sk-abc123...',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    chat: {
      title: 'Quick Question from Raycast',
      models: [selectedModelId],  // IMPORTANT: Include the model ID!
      messages: [],
      timestamp: Date.now()
    }
  })
});

const newChat = await response.json();
const chatId = newChat.id;
```

#### 6. Send Message to AI

```javascript
const response = await fetch('https://chat.example.com/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': 'sk-abc123...',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: selectedModelId, // Use the model ID from step 3
    messages: [
      {
        role: 'user',
        content: 'What is the weather like today?'
      }
    ],
    chat_id: chatId,
    stream: false
  })
});

const completion = await response.json();
const aiResponse = completion.choices[0].message.content;
```

#### 7. Update Chat with Conversation

```javascript
const response = await fetch(`https://chat.example.com/api/v1/chats/${chatId}`, {
  method: 'POST',
  headers: {
    'Authorization': 'sk-abc123...',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    chat: {
      title: 'Weather Question',
      models: [selectedModelId],  // IMPORTANT: Always include models!
      messages: [
        {
          role: 'user',
          content: 'What is the weather like today?'
        },
        {
          role: 'assistant',
          content: aiResponse
        }
      ],
      timestamp: Date.now()
    }
  })
});
```

#### 8. Verify Sync

The chat is now visible in the web frontend! Open `https://chat.example.com` and the conversation will appear in the chat history.

### Streaming Example

```javascript
const response = await fetch('https://chat.example.com/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': 'sk-abc123...',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'gpt-3.5-turbo',
    messages: [
      { role: 'user', content: 'Tell me a story' }
    ],
    stream: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') break;

      try {
        const parsed = JSON.parse(data);
        const content = parsed.choices[0]?.delta?.content;
        if (content) {
          // Display content chunk in Raycast
          console.log(content);
        }
      } catch (e) {
        // Skip invalid JSON
      }
    }
  }
}
```

---

## Configuration Notes

### API Key Restrictions (Optional)

Administrators can optionally restrict API keys to specific endpoints:

**Environment Variables:**
```bash
ENABLE_API_KEY=true
ENABLE_API_KEY_ENDPOINT_RESTRICTIONS=true
API_KEY_ALLOWED_ENDPOINTS=/api/v1/chats,/api/v1/models,/api/v1/chat/completions
```

If restrictions are enabled and your API key is denied access, contact your administrator.

### Rate Limiting

Open WebUI does not implement built-in rate limiting at the application level. However:
- Underlying model providers (OpenAI, etc.) have their own rate limits
- Network/infrastructure may impose limits
- Implement client-side throttling to be respectful

### CORS

If building a browser-based extension, ensure your Open WebUI instance has CORS properly configured. API keys should work across origins.

---

## Support and Additional Resources

- **Swagger Documentation:** Available at `https://your-instance.com/docs` (development mode)
- **OpenAPI Spec:** Available at `https://your-instance.com/openapi.json` (development mode)
- **GitHub:** [https://github.com/open-webui/open-webui](https://github.com/open-webui/open-webui)

---

## Summary

This API provides everything needed to build a fully-featured Raycast extension:

✅ **Authentication** via long-lived API keys
✅ **Chat Management** (create, read, update, delete)
✅ **AI Interactions** with streaming support
✅ **Automatic Sync** - chats appear instantly in the web frontend
✅ **Full Feature Parity** - all web features available via API

The backend uses a shared database, so any chats created through your Raycast extension will immediately appear in the web UI, and vice versa.
