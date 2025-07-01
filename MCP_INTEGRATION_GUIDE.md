# Open WebUI MCP Integration Guide

This guide explains how to set up and use MCP (Model Context Protocol) servers with Open WebUI through the mcpo proxy.

## Quick Start

1. **Start MCP Proxies**:
   ```bash
   ./start_mcp_proxies.sh
   ```

2. **Start Open WebUI**:
   ```bash
   ./start_openwebui.sh
   ```

3. **Access Open WebUI**: http://localhost:5173

## MCP Services Available

### 1. Filesystem Access (Port 8001)
- **Endpoint**: `http://localhost:8001`
- **API Key**: `openwebui-filesystem`
- **Description**: Access and manage files in `/Users/gwyn`
- **Tools**: read_file, write_file, list_directory, create_directory

### 2. Memory Management (Port 8002)
- **Endpoint**: `http://localhost:8002`
- **API Key**: `openwebui-memory`
- **Description**: Store and retrieve memories using OpenMemory
- **Tools**: add_memory, search_memories, list_memories

### 3. Browser Automation (Port 8003)
- **Endpoint**: `http://localhost:8003`
- **API Key**: `openwebui-browser`
- **Description**: Web scraping and browser automation
- **Tools**: screenshot, navigate, extract_content

## Configuring Open WebUI

### Adding MCP Services as OpenAPI Tools

1. Go to **Admin Panel** → **Settings** → **Tools**
2. Add each MCP service as an OpenAPI tool:

#### Filesystem Service
```json
{
  "name": "filesystem",
  "url": "http://localhost:8001",
  "headers": {
    "Authorization": "Bearer openwebui-filesystem"
  }
}
```

#### Memory Service
```json
{
  "name": "memory",
  "url": "http://localhost:8002",
  "headers": {
    "Authorization": "Bearer openwebui-memory"
  }
}
```

#### Browser Service
```json
{
  "name": "browser",
  "url": "http://localhost:8003",
  "headers": {
    "Authorization": "Bearer openwebui-browser"
  }
}
```

### OpenRouter Configuration

Your OpenRouter API key is already configured in the `.env` file:
- **API Key**: `sk-or-v1-REALLY CLAUDE?`
- **Base URL**: `https://openrouter.ai/api/v1`

## Testing the Integration

### Test MCP Proxies
```bash
# Test filesystem proxy
curl -H "Authorization: Bearer openwebui-filesystem" http://localhost:8001/docs

# Test memory proxy  
curl -H "Authorization: Bearer openwebui-memory" http://localhost:8002/docs

# Test browser proxy
curl -H "Authorization: Bearer openwebui-browser" http://localhost:8003/docs
```

### Interactive API Documentation
- Filesystem: http://localhost:8001/docs
- Memory: http://localhost:8002/docs
- Browser: http://localhost:8003/docs

## Troubleshooting

### MCP Proxies Not Starting
```bash
# Kill existing processes
pkill -f mcpo

# Check if required tools are installed
npm list -g @modelcontextprotocol/server-filesystem
npm list -g openmemory
npm list -g @modelcontextprotocol/server-puppeteer

# Install missing tools
npm install -g @modelcontextprotocol/server-filesystem
npm install -g openmemory  
npm install -g @modelcontextprotocol/server-puppeteer
```

### Open WebUI Connection Issues
1. Ensure backend is running on port 8080
2. Check that frontend can reach backend
3. Verify .env configuration is correct

### API Key Issues
- MCP proxy API keys are for securing the proxy endpoints
- OpenRouter API key is for LLM access
- Make sure headers include `Authorization: Bearer <api-key>`

## Advanced Configuration

### Custom MCP Servers
To add your own MCP servers from the Claude Desktop config:

1. **Audio Analyzer**:
   ```bash
   GOOGLE_GEMINI_API_KEY="AIzaSyCf-yd0nrvR-hVHVKrtZP5w8tLL4p3roRc" \
   mcpo --port 8004 --api-key "openwebui-audio" -- \
   /opt/homebrew/Caskroom/miniconda/base/bin/python3 \
   /Users/gwyn/projects/MCPs/audio-analyzer-mcp/server.py
   ```

2. **Sydney MCP**:
   ```bash
   OPENROUTER_API_KEY="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" \
   OPENPIPE_API_KEY="opk_7f4ff91c5e73fc82de28fcf108a0b78c196cced128" \
   mcpo --port 8005 --api-key "openwebui-sydney" -- \
   node /Users/gwyn/projects/sydney-ng/mcp/index.js
   ```

## Security Notes

- MCP proxy API keys are for internal security
- Never expose these endpoints publicly without proper authentication
- Keep your OpenRouter API key secure
- Consider using environment variables for sensitive data

## Stopping Services

```bash
# Stop all services
pkill -f 'npm run dev'
pkill -f 'uvicorn' 
pkill -f mcpo

# Or use the provided stop script (if created)
./stop_all.sh
```