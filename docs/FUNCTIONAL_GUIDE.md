# Open WebUI - Functional Guide

> **Version:** 0.6.34
> **Last Updated:** 2025-11-05
> **Audience:** End Users, Power Users, Administrators

---

## Table of Contents

- [1. Getting Started](#1-getting-started)
- [2. Chat Interface](#2-chat-interface)
- [3. Workspace Features](#3-workspace-features)
- [4. Knowledge Base](#4-knowledge-base)
- [5. RAG (Retrieval Augmented Generation)](#5-rag-retrieval-augmented-generation)
- [6. Custom Functions & Tools](#6-custom-functions--tools)
- [7. Collaborative Notes](#7-collaborative-notes)
- [8. Admin Panel](#8-admin-panel)
- [9. Advanced Features](#9-advanced-features)
- [10. Tips & Best Practices](#10-tips--best-practices)

---

## 1. Getting Started

### 1.1 First Login

1. Navigate to your Open WebUI instance (e.g., `http://localhost:3000`)
2. **Sign up** with email and password, or use OAuth (Google, GitHub, etc.)
3. If admin approval is required, wait for admin to approve your account
4. Once approved, log in and explore the interface

### 1.2 User Interface Overview

```
┌─────────────────────────────────────────────────────────┐
│  [☰] Open WebUI              [⚙️] Settings  [👤] Profile │
├─────────────────────────────────────────────────────────┤
│  Sidebar          │  Main Content Area                   │
│                   │                                      │
│  📝 New Chat      │  💬 Chat Interface                   │
│  📂 Chats         │  or                                  │
│  📚 Workspace     │  📋 Workspace View                   │
│    - Models       │  or                                  │
│    - Prompts      │  🗒️ Notes Editor                     │
│    - Functions    │  or                                  │
│    - Knowledge    │  ⚙️ Admin Panel                      │
│  🗒️ Notes         │                                      │
│  ⚙️ Admin (admin) │                                      │
│                   │                                      │
└───────────────────┴──────────────────────────────────────┘
```

### 1.3 Quick Start: Your First Chat

1. Click **"New Chat"** or press `Ctrl+N`
2. Select a model from the dropdown (e.g., GPT-4, Claude, or local Ollama model)
3. Type your message in the input box
4. Press `Enter` or click Send
5. Watch the AI respond in real-time!

**Tip:** You can select multiple models at once for parallel responses!

---

## 2. Chat Interface

### 2.1 Basic Chat Features

**Creating Chats:**
- Click "New Chat" to start fresh
- Name chats by clicking the title
- Chats auto-save as you type

**Model Selection:**
- Click model dropdown to choose AI model
- Select multiple models for comparison
- Switch models mid-conversation

**Message Actions:**
- **Edit**: Click edit icon to revise your message
- **Copy**: Copy message text
- **Regenerate**: Get a new response
- **Continue**: Ask the model to continue
- **Delete**: Remove message from conversation

### 2.2 Advanced Chat Commands

**Slash Commands:**
```
/help           - Show help
/clear          - Clear chat history
/search         - Search messages
/export         - Export chat
```

**Referencing Context:**
```
#file-name      - Reference knowledge base file
#url            - Inject web page content
@model-name     - Mention specific model
@function-name  - Call custom function
```

**Examples:**
```
Tell me about #product-docs
Summarize #https://example.com
@gpt-4 What do you think?
```

### 2.3 File Uploads

**Supported Types:**
- **Documents**: PDF, DOCX, PPTX, TXT, MD, CSV
- **Images**: PNG, JPG, GIF, WEBP (vision models)
- **Code**: Any text-based code files

**How to Upload:**
1. Click the 📎 paperclip icon
2. Select file(s) from your computer
3. Files are processed and added to context
4. Ask questions about the uploaded content

**Vision Models:**
Upload images and ask:
```
"What's in this image?"
"Extract text from this screenshot"
"Describe the UI elements"
```

### 2.4 Voice & Video

**Text-to-Speech (TTS):**
- Click the 🔊 speaker icon on any message
- Hear AI responses read aloud
- Adjust voice settings in user preferences

**Speech-to-Text (STT):**
- Click the 🎤 microphone icon
- Speak your message
- Automatic transcription

**Video Call:**
- Click the 📹 video icon (if enabled)
- Start hands-free voice/video conversation

### 2.5 Chat Management

**Organizing Chats:**
- **Pin**: Keep important chats at the top
- **Archive**: Hide old chats from main view
- **Tag**: Categorize with custom tags
- **Folder**: Organize into folders

**Sharing Chats:**
1. Click share icon
2. Generate shareable link
3. Share with others (read-only)
4. Revoke access anytime

**Exporting Chats:**
- Export as JSON
- Export as Markdown
- Export as PDF (with formatting)

---

## 3. Workspace Features

The Workspace is your hub for managing AI resources.

### 3.1 Models

**View Available Models:**
- Navigate to **Workspace → Models**
- See all configured LLM models
- Test models in playground

**Pull New Models (Ollama):**
1. Click "Pull Model"
2. Enter model name (e.g., `llama3.3:70b`)
3. Wait for download
4. Model appears in dropdown

**Create Custom Models:**
1. Click "Create Model"
2. Choose base model
3. Set system prompt
4. Configure parameters (temperature, top-p, etc.)
5. Save and use in chats

### 3.2 Prompts

**Browse Prompts:**
- Pre-built prompt templates
- Community-shared prompts
- Your custom prompts

**Create Custom Prompts:**
1. Go to **Workspace → Prompts**
2. Click "New Prompt"
3. Enter command (e.g., `/explain`)
4. Write prompt template with variables
5. Save

**Use Prompts:**
```
/explain {code}
/summarize {document}
/translate {text} to Spanish
```

### 3.3 Functions

**What are Functions?**
Custom Python code that LLMs can call as tools.

**Browse Functions:**
- Navigate to **Workspace → Functions**
- See available functions
- Test function execution

**Create Custom Function:**
```python
def get_weather(location: str) -> dict:
    """Get current weather for a location"""
    import requests
    # Your code here
    return {"temperature": 72, "condition": "Sunny"}
```

**Function Calling:**
LLMs automatically call functions when needed:
```
User: What's the weather in San Francisco?
AI: [calls get_weather("San Francisco")]
AI: It's 72°F and sunny in San Francisco!
```

### 3.4 Knowledge Base

**Create Knowledge Collection:**
1. Go to **Workspace → Knowledge**
2. Click "New Knowledge"
3. Upload documents (PDF, DOCX, web pages, etc.)
4. Name your knowledge collection
5. Set access permissions (private, shared, public)

**Reference in Chats:**
```
Tell me about #project-documentation
Summarize findings from #research-papers
```

---

## 4. Knowledge Base

### 4.1 Adding Documents

**Upload Files:**
1. Navigate to **Workspace → Knowledge → [Collection]**
2. Click "Add Files"
3. Select documents from your computer
4. Files are processed and embedded automatically

**Add Web Pages:**
1. Click "Add URL"
2. Paste webpage URL
3. Content is scraped and indexed

**Add YouTube Videos:**
1. Click "Add YouTube"
2. Paste video URL
3. Transcript is extracted and indexed

### 4.2 Document Processing

**Automatic Processing:**
- Text extraction (PDF, DOCX, PPTX)
- OCR for images (if enabled)
- Chunking for optimal retrieval
- Embedding generation
- Vector storage

**Processing Status:**
- ⏳ Processing...
- ✅ Ready
- ❌ Failed (check logs)

### 4.3 Access Control

**Permission Levels:**
- **Private**: Only you can access
- **Shared**: Share with specific users/groups
- **Public**: Everyone can access

**Fine-Grained Control:**
```json
{
  "read": {
    "user_ids": ["user1", "user2"],
    "group_ids": ["team-a"]
  },
  "write": {
    "user_ids": ["user1"]
  }
}
```

### 4.4 Knowledge Management

**Updating Documents:**
- Re-upload to replace
- Delete outdated files
- Version history (if enabled)

**Searching Knowledge:**
- Full-text search
- Semantic search
- Hybrid search (best results)

---

## 5. RAG (Retrieval Augmented Generation)

### 5.1 What is RAG?

RAG enhances AI responses by retrieving relevant context from your documents before generating answers.

**How it Works:**
```
Your Question
    ↓
Knowledge Base Search (finds relevant chunks)
    ↓
Context + Question → LLM
    ↓
Enhanced, Accurate Response
```

### 5.2 Using RAG in Chats

**Method 1: Reference Knowledge**
```
#my-knowledge Tell me about X
```

**Method 2: Upload File**
```
[Upload document.pdf]
Summarize this document
```

**Method 3: Web Search**
```
#https://example.com/article
Explain the main points
```

### 5.3 RAG Settings

**Configure in Admin Panel:**
- **Embedding Model**: Choose embedding model (local or external)
- **Chunk Size**: Adjust for optimal retrieval (default: 500)
- **Top K Results**: Number of chunks to retrieve (default: 5)
- **Reranking**: Enable for better results
- **Web Search**: Enable web search providers

**Vector Database Options:**
- ChromaDB (default, local)
- Qdrant (scalable)
- Milvus (enterprise)
- PgVector (PostgreSQL)
- And 6 more options

### 5.4 Web Search Integration

**Enable Web Search:**
1. Admin Panel → Settings → RAG
2. Choose web search provider (DuckDuckGo, Brave, Google, etc.)
3. Enter API key (if required)
4. Enable "Web Search"

**Using Web Search:**
```
Search the web for latest news on AI
What's happening with #websearch:OpenAI
```

---

## 6. Custom Functions & Tools

### 6.1 Understanding Functions

**Functions** are custom Python code that:
- Extend LLM capabilities
- Integrate external APIs
- Perform computations
- Access databases
- Automate workflows

### 6.2 Creating Functions

**Steps:**
1. Go to **Workspace → Functions**
2. Click "New Function"
3. Write Python code in editor
4. Define function signature with type hints
5. Add docstring (LLM uses this to understand function)
6. Test function
7. Save and activate

**Example Function:**
```python
def search_database(query: str, table: str = "users") -> list:
    """
    Search database for records matching query.

    Args:
        query: Search query
        table: Database table to search (default: users)

    Returns:
        List of matching records
    """
    import sqlite3

    conn = sqlite3.connect("/data/mydb.db")
    cursor = conn.execute(f"SELECT * FROM {table} WHERE name LIKE ?", (f"%{query}%",))
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]
```

### 6.3 Function Types

**1. Filter Functions:**
Pre-process user input before sending to LLM.

**2. Action Functions:**
Execute actions based on LLM response.

**3. Tool Functions:**
LLM can call as tools via function calling.

### 6.4 Function Security

**Sandbox:**
- RestrictedPython sandbox for safety
- Limited imports (whitelist-based)
- No file system access by default
- Network requests allowed (configurable)

**Best Practices:**
- Validate all inputs
- Handle errors gracefully
- Use type hints
- Add clear docstrings
- Test thoroughly before activating

---

## 7. Collaborative Notes

### 7.1 Creating Notes

**New Note:**
1. Navigate to **Notes**
2. Click "New Note"
3. Start writing in the rich text editor

**Features:**
- Rich text formatting (bold, italic, headers)
- Code blocks with syntax highlighting
- Images and embeds
- Tables
- Markdown shortcuts

### 7.2 Real-Time Collaboration

**Invite Collaborators:**
1. Open note
2. Click "Share"
3. Add users or generate link
4. Collaborators see changes in real-time!

**Collaboration Features:**
- Live cursors (see who's editing where)
- Instant updates (no refresh needed)
- Conflict-free editing (CRDT-based)
- Presence indicators

### 7.3 Note Organization

**Folders:**
- Organize notes into folders
- Nested folders supported
- Drag and drop to move

**Tags:**
- Add tags for categorization
- Search by tags
- Filter notes by tags

**Favorites:**
- Star important notes
- Quick access from sidebar

---

## 8. Admin Panel

### 8.1 User Management

**View Users:**
- Navigate to **Admin → Users**
- See all registered users
- User stats (last active, chat count, etc.)

**Manage Users:**
- **Approve**: Approve pending signups
- **Promote**: Grant admin role
- **Suspend**: Disable user account
- **Delete**: Remove user permanently

**User Roles:**
- **Admin**: Full access to all features and settings
- **User**: Standard access
- **Pending**: Awaiting approval

### 8.2 System Settings

**General:**
- Site name and branding
- Default language
- Signup settings (open, approval required, disabled)
- OAuth providers

**LLM Settings:**
- Ollama base URL
- OpenAI API keys
- Model defaults
- Timeout settings

**RAG Configuration:**
- Embedding model
- Vector database
- Chunk size and overlap
- Top K results
- Reranking settings
- Web search providers

**Storage:**
- Storage backend (local, S3, Azure, GCP)
- Upload limits
- Allowed file types

**Security:**
- JWT secret
- Session timeout
- Password requirements
- API rate limits

### 8.3 Knowledge Management

**Global Knowledge:**
- Create knowledge available to all users
- Upload company-wide documents
- Manage permissions

**File Management:**
- View all uploaded files
- Delete orphaned files
- Storage usage statistics

### 8.4 Model Configuration

**Configure Models:**
- Set model availability
- Default models for new users
- Model-specific settings
- Usage limits per user/group

**Pull Models:**
- Pull Ollama models for all users
- Schedule automatic updates
- Manage model versions

### 8.5 Analytics

**Usage Statistics:**
- Total chats created
- Messages sent
- Active users
- Popular models
- Storage usage

**Model Performance:**
- Average response time
- Token usage
- Error rates
- User satisfaction (if feedback enabled)

---

## 9. Advanced Features

### 9.1 Multi-Model Conversations

**Using Multiple Models:**
1. In chat, click model selector
2. Select multiple models (e.g., GPT-4 + Claude)
3. Send message
4. Get responses from all selected models side-by-side

**Use Cases:**
- Compare model outputs
- Get diverse perspectives
- Fact-checking
- Creative brainstorming

### 9.2 Pipelines

**What are Pipelines?**
External services that process requests/responses:
- Rate limiting
- Content filtering
- Translation
- Monitoring
- Custom logic

**Using Pipelines:**
1. Admin configures pipeline URL
2. Pipeline runs automatically on all requests
3. Pre-processing (inlet) and post-processing (outlet)

### 9.3 SCIM Provisioning (Enterprise)

**Automated User Management:**
- Integrate with Okta, Azure AD, Google Workspace
- Automatic user creation/updates
- Group synchronization
- Deprovisioning

**Setup:**
1. Admin → Settings → SCIM
2. Enable SCIM
3. Copy SCIM endpoint and token
4. Configure in identity provider
5. Users sync automatically

### 9.4 API Keys

**Generate API Key:**
1. User Settings → API Keys
2. Click "Create API Key"
3. Name the key
4. Copy key (shown only once!)
5. Use in API requests

**Using API Keys:**
```bash
curl https://yourinstance.com/api/chats \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 9.5 Integrations

**Ollama:**
- Local LLM inference
- Pull models directly from Open WebUI
- Full model management

**OpenAI-Compatible APIs:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Local (LM Studio, Text Generation WebUI)

**Image Generation:**
- DALL-E 3 (OpenAI)
- Stable Diffusion (AUTOMATIC1111)
- ComfyUI

**Speech:**
- Whisper (speech-to-text)
- TTS (text-to-speech)

---

## 10. Tips & Best Practices

### 10.1 Chat Best Practices

**Get Better Responses:**
- Be specific and clear
- Provide context
- Use examples
- Break complex tasks into steps
- Iterate and refine

**Optimize Performance:**
- Keep conversations focused
- Start new chats for different topics
- Archive old chats regularly
- Use appropriate model for task (fast model for simple tasks, powerful model for complex ones)

### 10.2 Knowledge Base Best Practices

**Document Organization:**
- Create focused knowledge collections (don't mix unrelated topics)
- Use descriptive names
- Add descriptions to collections
- Regular maintenance (remove outdated docs)

**Optimal Chunking:**
- Default chunk size (500) works for most cases
- Increase for longer context (e.g., legal documents)
- Decrease for precise retrieval (e.g., FAQs)

### 10.3 Function Development

**Best Practices:**
- Write clear, self-documenting code
- Handle errors gracefully
- Use type hints
- Test with various inputs
- Start with simple functions
- Add logging for debugging

**Security:**
- Never hardcode secrets (use environment variables)
- Validate all user inputs
- Use safe libraries
- Limit network access if possible
- Request admin approval for global functions

### 10.4 Performance Tips

**Speed Up Responses:**
- Use faster models for simple queries
- Enable streaming for long responses
- Optimize knowledge base (remove duplicates)
- Use local embeddings (faster than external APIs)

**Reduce Costs:**
- Use local models (Ollama) when possible
- Set token limits
- Cache frequently used prompts
- Use cheaper models for simple tasks

### 10.5 Collaboration Tips

**Team Usage:**
- Create shared knowledge for common resources
- Use groups for access control
- Establish naming conventions
- Regular knowledge base reviews
- Share useful prompts and functions

**Best Practices:**
- Communicate changes in shared resources
- Use descriptive chat titles
- Tag important conversations
- Regular backups

---

## Appendix

### A. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New chat |
| `Ctrl+/` | Toggle sidebar |
| `Ctrl+K` | Search chats |
| `Ctrl+S` | Save note |
| `Enter` | Send message |
| `Shift+Enter` | New line in message |
| `Ctrl+↑` | Edit last message |

### B. Supported File Types

**Documents:**
- PDF, DOCX, PPTX, TXT, MD, CSV, XLSX

**Images:**
- PNG, JPG, JPEG, GIF, WEBP, HEIC

**Code:**
- All text-based code files

**Maximum File Size:** Configurable by admin (default: 100MB)

### C. Model Comparison

| Model | Best For | Speed | Cost |
|-------|----------|-------|------|
| **GPT-4** | Complex reasoning, code | Slow | $$$ |
| **GPT-3.5 Turbo** | General tasks | Fast | $ |
| **Claude Sonnet** | Analysis, writing | Medium | $$ |
| **Llama 3.3 70B** | Local, private | Medium | Free |
| **Mistral** | Fast, efficient | Fast | $ |

### D. Troubleshooting

**Chat not responding:**
- Check model availability
- Verify API keys (Admin Panel)
- Check network connection
- Try different model

**Upload failed:**
- Check file size limit
- Verify file type is supported
- Check storage quota
- Try smaller file

**RAG not working:**
- Verify knowledge is processed (✅ status)
- Check embedding model is configured
- Ensure proper `#reference` syntax
- Try re-uploading document

**Can't create function:**
- Check if you have permission
- Verify Python syntax
- Test function in isolation
- Check for restricted imports

---

## Support

**Need Help?**
- Documentation: https://docs.openwebui.com
- Discord: https://discord.gg/5rJgQTnV4s
- GitHub Issues: https://github.com/open-webui/open-webui/issues

**Feature Requests:**
- Submit on GitHub
- Vote on existing requests
- Join community discussions

---

**Document Version:** 1.0
**Last Updated:** 2025-11-05
**Maintained by:** Open WebUI Team
