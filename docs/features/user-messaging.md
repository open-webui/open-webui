# User-to-User Messaging and File Sharing

## Overview

The User-to-User Messaging feature enables direct communication between registered users within Open WebUI. This feature includes real-time messaging, file sharing, and conversation management capabilities.

## Features

### 🔄 Real-Time Messaging
- Instant message delivery using WebSocket connections
- Message read/unread status tracking
- Typing indicators and online status
- Message history and threading

### 📁 File Sharing
- Share documents, images, and other files in conversations
- Secure file upload with validation and scanning
- File download with proper access controls
- Support for multiple file formats

### 👥 User Management
- Search and discover other users on the instance
- Start new conversations with any registered user
- Manage conversation lists and contacts
- Block/unblock users for privacy control

### 🔒 Security & Privacy
- End-to-end message encryption
- File access restricted to conversation participants
- Rate limiting to prevent spam
- Audit logging for administrative oversight

## Getting Started

### Prerequisites
- Open WebUI instance with user registration enabled
- WebSocket support configured
- File storage properly set up

### Accessing Messaging
1. **Login** to your Open WebUI account
2. **Navigate** to the messaging section (chat icon in sidebar)
3. **Start a conversation** by searching for users or selecting from existing conversations

## User Interface

### Main Messaging Interface
```
┌─────────────────────────────────────────────────────────┐
│ Open WebUI - Messages                          [Settings]│
├─────────────────┬───────────────────────────────────────┤
│ Conversations   │ Chat with John Doe                    │
│ ├ John Doe      │ ┌─────────────────────────────────────┐ │
│ ├ Alice Smith   │ │ John: Hey, how's the project going? │ │
│ └ Bob Wilson    │ │                              2:30 PM │ │
│                 │ └─────────────────────────────────────┘ │
│ [New Message]   │ ┌─────────────────────────────────────┐ │
│                 │ │ You: Great! Just finished the docs. │ │
│                 │ │                              2:32 PM │ │
│                 │ └─────────────────────────────────────┘ │
│                 │ ┌─────────────────────────────────────┐ │
│                 │ │ [📎] shared_file.pdf                │ │
│                 │ │                              2:33 PM │ │
│                 │ └─────────────────────────────────────┘ │
│                 │ ┌───────────────────────────────┐     │
│                 │ │ Type your message...          │ [📎] │
│                 │ │                               │ [➤] │
│                 │ └───────────────────────────────┘     │
└─────────────────┴───────────────────────────────────────┘
```

### Starting a New Conversation
1. Click **"New Message"** button
2. Search for users by name or email
3. Select a user from the search results
4. Type your first message and press Enter

### Sharing Files
1. Click the **attachment icon** (📎) in the message input
2. Select files from your device (up to 10MB per file)
3. Add an optional message describing the file
4. Click **Send** to share the file

## API Documentation

### Authentication
All messaging API endpoints require user authentication via JWT token:
```http
Authorization: Bearer <jwt_token>
```

### Endpoints

#### Send Message
```http
POST /api/v1/messages/send
Content-Type: application/json

{
  "recipient_id": "user_123",
  "content": "Hello, how are you?",
  "message_type": "text"
}
```

**Response:**
```json
{
  "id": "msg_456",
  "conversation_id": "conv_789",
  "sender_id": "user_current",
  "recipient_id": "user_123",
  "content": "Hello, how are you?",
  "message_type": "text",
  "timestamp": "2025-10-08T14:30:00Z",
  "read": false
}
```

#### Get Conversations
```http
GET /api/v1/messages/conversations?limit=20&offset=0
```

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv_789",
      "participants": [
        {"id": "user_current", "name": "Current User"},
        {"id": "user_123", "name": "John Doe"}
      ],
      "last_message": {
        "content": "Hello, how are you?",
        "timestamp": "2025-10-08T14:30:00Z",
        "sender_name": "Current User"
      },
      "unread_count": 0
    }
  ],
  "total": 1,
  "has_more": false
}
```

#### Get Conversation Messages
```http
GET /api/v1/messages/conversation/conv_789?limit=50&offset=0
```

**Response:**
```json
{
  "messages": [
    {
      "id": "msg_456",
      "sender_id": "user_current",
      "sender_name": "Current User",
      "content": "Hello, how are you?",
      "message_type": "text",
      "timestamp": "2025-10-08T14:30:00Z",
      "read": true
    }
  ],
  "total": 1,
  "has_more": false
}
```

#### Share File
```http
POST /api/v1/messages/conversation/conv_789/share-file
Content-Type: multipart/form-data

file=<file_data>
message=Optional description of the file
```

**Response:**
```json
{
  "id": "msg_789",
  "conversation_id": "conv_789",
  "sender_id": "user_current",
  "content": "shared_file.pdf",
  "message_type": "file",
  "file_info": {
    "filename": "shared_file.pdf",
    "size": 2048576,
    "mime_type": "application/pdf",
    "download_url": "/api/v1/files/download/file_abc123"
  },
  "timestamp": "2025-10-08T14:35:00Z"
}
```

#### Search Users
```http
GET /api/v1/users/search?query=john&limit=10
```

**Response:**
```json
{
  "users": [
    {
      "id": "user_123",
      "name": "John Doe",
      "email": "john@example.com",
      "avatar_url": "/api/v1/users/user_123/avatar",
      "online": true
    }
  ]
}
```

## WebSocket Events

### Connection
Connect to the WebSocket endpoint:
```
ws://localhost:8080/ws/messages
```

### Event Types

#### Message Received
```json
{
  "type": "message_received",
  "data": {
    "id": "msg_456",
    "conversation_id": "conv_789",
    "sender_id": "user_123",
    "sender_name": "John Doe",
    "content": "Hello!",
    "message_type": "text",
    "timestamp": "2025-10-08T14:30:00Z"
  }
}
```

#### User Typing
```json
{
  "type": "user_typing",
  "data": {
    "conversation_id": "conv_789",
    "user_id": "user_123",
    "user_name": "John Doe",
    "is_typing": true
  }
}
```

#### User Status
```json
{
  "type": "user_status",
  "data": {
    "user_id": "user_123",
    "status": "online"
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `WEBUI_MESSAGING_ENABLED` | Enable messaging feature | `true` | No |
| `WEBUI_MAX_FILE_SIZE` | Maximum file size for sharing (bytes) | `10485760` (10MB) | No |
| `WEBUI_MESSAGE_RATE_LIMIT` | Messages per minute per user | `60` | No |
| `WEBUI_FILE_STORAGE_PATH` | Path for storing shared files | `./data/shared_files` | No |
| `WEBUI_MESSAGE_ENCRYPTION` | Enable message encryption | `true` | No |

### Database Configuration
The messaging feature requires these additional database tables:
- `conversations`
- `conversation_participants`
- `messages`
- `message_files`
- `user_blocks`

These are automatically created during the migration process.

## Troubleshooting

### Common Issues

#### Messages Not Appearing
1. **Check WebSocket connection** - Verify browser dev tools show active WebSocket
2. **Verify permissions** - Ensure user has messaging permissions
3. **Check database** - Confirm message was saved to database

#### File Upload Failures
1. **File size** - Ensure file is under the configured size limit
2. **File type** - Check if file type is allowed
3. **Storage permissions** - Verify write permissions on storage directory
4. **Disk space** - Ensure sufficient storage space available

#### Performance Issues
1. **Message pagination** - Large conversations are paginated automatically
2. **File caching** - Files are cached for faster access
3. **Database indexing** - Ensure proper indexes on message tables

### Logs and Debugging

Enable debug logging for messaging:
```python
# In your environment or config
WEBUI_LOG_LEVEL=DEBUG
```

Common log locations:
- **Backend logs:** `/var/log/open-webui/messaging.log`
- **WebSocket logs:** `/var/log/open-webui/websocket.log`
- **File operations:** `/var/log/open-webui/files.log`

## Privacy and Security

### Data Encryption
- Messages are encrypted at rest using AES-256
- File contents are encrypted before storage
- Encryption keys are managed per conversation

### Access Control
- Users can only access their own conversations
- File downloads require conversation membership
- Admin users can view conversation metadata for moderation

### Data Retention
- Messages are retained indefinitely by default
- Administrators can configure automatic cleanup policies
- Users can delete their own messages (with configurable limits)

## Admin Guide

### Moderation Tools
- View conversation statistics
- Search messages for policy violations
- Block users from messaging
- Export conversation data for investigations

### Performance Monitoring
- Track message volume and patterns
- Monitor file storage usage
- WebSocket connection statistics
- Database performance metrics

### Backup and Recovery
- Include message tables in regular database backups
- Back up shared file storage directory
- Test message restoration procedures

## Development

### Adding Custom Message Types
```python
# In your custom message handler
class CustomMessageHandler:
    def handle_poll_message(self, message_data):
        # Custom logic for poll messages
        pass
    
    def handle_location_message(self, message_data):
        # Custom logic for location sharing
        pass
```

### Extending the API
```python
# In routers/messages.py
@router.post("/conversation/{conversation_id}/custom-action")
async def custom_message_action(
    conversation_id: str,
    action_data: CustomActionModel,
    user=Depends(get_current_user)
):
    # Custom message functionality
    pass
```

### Frontend Customization
```javascript
// In your Svelte component
import { MessageComponent } from '$lib/components/messaging';

// Extend with custom message types
const customMessageRenderer = {
  poll: PollMessageComponent,
  location: LocationMessageComponent
};
```