# OpenWebUI with Token Usage Tracking & Reasoning Effort

This is your extended OpenWebUI with **token usage tracking by groups** and **reasoning effort selection** features. All original functionality is preserved while adding powerful new capabilities for monitoring and controlling token usage.

## 🚀 Quick Start

1. **Start the Modified Version:**
   ```bash
   ./start_modified.sh
   ```
   
2. **Access the Interface:**
   - **Web Interface**: http://localhost:8081/
   - **API Docs**: http://localhost:8081/docs

3. **Login**: Use your existing OpenWebUI credentials

## ✨ New Features

### 🔢 Token Usage Tracking by Groups

**Create token groups** to track usage across multiple models:

#### Create a Group via API:
```bash
curl -X POST "http://localhost:8081/api/usage/groups" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "gpt-4-group", 
       "models": ["gpt-4", "gpt-4o"], 
       "limit": 1000000
     }'
```

#### View All Groups and Usage:
```bash
curl "http://localhost:8081/api/usage/groups" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

#### Live Usage Display:
- Appears **above the chat input** when using models in tracked groups
- Shows: `1,234 IN · 5,678 OUT · 6,912 TOTAL / 10,000,000`
- Updates every 3 seconds automatically
- **IN** = prompt tokens
- **OUT** = completion tokens + reasoning tokens  
- **TOTAL** = IN + OUT

### 🧠 Reasoning Effort Selection

**Dropdown control** for reasoning-capable models:

- **Location**: Left of the Web Search button in chat interface
- **Options**: Low | Medium | High (defaults to Medium)
- **Storage**: Per-model preferences saved in localStorage
- **API Integration**: Passes `reasoning: { effort: "<level>" }` in requests

## 📊 Usage Scenarios

### Example 1: OpenAI Usage Tracking
```bash
# Create group for OpenAI models
curl -X POST "http://localhost:8081/api/usage/groups" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "openai-models",
       "models": ["gpt-4o", "gpt-4o-mini", "o1-preview"], 
       "limit": 5000000
     }'
```

### Example 2: Budget Management
```bash  
# Create different groups for different use cases
curl -X POST "http://localhost:8081/api/usage/groups" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "production-models",
       "models": ["gpt-4o"], 
       "limit": 2000000
     }'

curl -X POST "http://localhost:8081/api/usage/groups" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "development-models", 
       "models": ["gpt-4o-mini"],
       "limit": 500000
     }'
```

## 🔧 API Reference

### GET /api/usage/groups
Returns all token groups with current usage statistics.

**Response:**
```json
{
  "groups": {
    "gpt-4-group": {
      "models": ["gpt-4", "gpt-4o"],
      "limit": 1000000,
      "usage": {
        "in": 1234,
        "out": 5678, 
        "total": 6912
      }
    }
  }
}
```

### POST /api/usage/groups  
Create a new token group.

**Request:**
```json
{
  "name": "group-name",
  "models": ["model1", "model2"], 
  "limit": 1000000
}
```

### PUT /api/usage/groups/{name}
Update an existing group.

**Request:**
```json
{
  "models": ["updated-models"],
  "limit": 2000000  
}
```

### DELETE /api/usage/groups/{name}
Delete a token group.

## 🛠️ Technical Details

### Architecture
- **Backend**: Token tracking via Redis/in-memory data structures
- **Socket Events**: Real-time usage updates via WebSocket "usage" events  
- **Middleware**: Automatically enables `stream_options.include_usage`
- **Frontend**: Live polling every 3 seconds + localStorage persistence

### Token Calculation  
- **IN**: `prompt_tokens`
- **OUT**: `completion_tokens + completion_tokens_details.reasoning_tokens`
- **TOTAL**: `IN + OUT`
- **Audio tokens**: Ignored (treated as 0)
- **Missing fields**: Default to 0 (no errors)

### Data Storage
- **Groups**: Stored in Redis (if configured) or in-memory
- **Usage**: Aggregated globally across all users per group
- **Persistence**: Uses same database as your original OpenWebUI
- **Settings**: Reasoning effort preferences in browser localStorage

## 🔒 Security & Compatibility

- ✅ **Same Authentication**: Uses your existing OpenWebUI auth system
- ✅ **Same Database**: No data migration needed
- ✅ **Same Settings**: All your existing configuration preserved  
- ✅ **API Security**: All new endpoints require proper authentication
- ✅ **Original Features**: 100% backward compatible

## 🧪 Testing

Run the test suite to verify everything works:

```bash
python3 test_complete_functionality.py
```

## 🚨 Troubleshooting

### Issue: "Not authenticated" errors
**Solution**: Get your auth token from the web interface and use it in API calls.

### Issue: Usage stats not updating
**Solution**: Ensure models are added to groups and streaming is enabled.

### Issue: Database connection issues  
**Solution**: Verify the original OpenWebUI database exists at:
`/home/tennisbowling/.local/lib/python3.12/site-packages/open_webui/data/webui.db`

## 📝 Development Notes

### Key Files Modified:
- `backend/open_webui/socket/main.py` - Socket event handling & data structures
- `backend/open_webui/utils/middleware.py` - Stream options enablement  
- `backend/open_webui/main.py` - REST API endpoints
- `src/lib/components/chat/Chat.svelte` - Live usage display
- `src/lib/components/chat/MessageInput.svelte` - Reasoning effort dropdown

### Environment Variables:
```bash
DATA_DIR="/home/tennisbowling/.local/lib/python3.12/site-packages/open_webui/data"
PYTHONPATH="/home/tennisbowling/open-webui/backend" 
```

---

🎉 **Enjoy your enhanced OpenWebUI with powerful token usage tracking!**