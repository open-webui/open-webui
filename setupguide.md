# 🚀 CerebraUI Setup Guide

> **CS59 Capstone Project - Open Source AI Interface**

---

## ⚡ Quick Start
- **📋 Prerequisite**: Docker Desktop installed and running
- **📁 Clone and enter folder**:
```bash
git clone <your-repo-url>
cd "[your_folder]/cerebra-ui"
```
- **🚀 Pull & start services**: 
```bash
OPEN_WEBUI_PORT=3000 docker compose pull && OPEN_WEBUI_PORT=3000 docker compose up -d
```
- **⏳ Wait for startup** (5-10 mins on first run - downloading embedding models):
```bash
# Check container health
docker ps --format "{{.Names}}\t{{.Status}}" | grep open-webui

# Monitor progress
docker logs -f open-webui | grep -E "(Fetching|files)"
```

### ✅ Success Indicators
- Container shows "Up X minutes (healthy)"
- Logs show "Fetching 30 files: 100%"
- `curl -I http://localhost:3000` returns "HTTP/1.1 200 OK"

- **🌐 Open the app**: http://localhost:3000 (only after container shows "healthy")

### 🤖 Pull a Model (Ollama)
```bash
docker exec -it ollama ollama pull llama3.1:8b
```

---

## 🔧 Daily Commands
```bash
# Status
docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" | egrep "^(open-webui|ollama|redis)\b"

# Redis CLI to check if Redis is running
docker exec -it redis redis-cli PING

# Run Redis CLI 
docker exec -it redis redis-cli

# Logs
docker logs -f open-webui | cat

# Update images & restart
docker compose pull && docker compose up -d

# Stop
docker compose down

# Reset (removes data volumes)
docker compose down -v
```


-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### 📝 Notes
- Compose includes `ollama`, `open-webui`, and `redis`. No extra setup needed.
- If port 3000 or 6380 is in use, change `OPEN_WEBUI_PORT` (start command) or edit `docker-compose.yaml` port mappings.

---

## 🚨 Troubleshooting

### ❌ *Error Case 1: Container Name Conflict*
```
Error response from daemon: Conflict. The container name "/ollama" is already in use
Error response from daemon: Conflict. The container name "/redis" is already in use
```

**🔧 Solution:**
Reset: Remove all containers and volumes (if error occurs)
    ```bash
    cd "/Users/abhishektomar/Desktop/capstone project/cerebra-ui"
    docker rm -f redis open-webui ollama || true
    OPEN_WEBUI_PORT=3000 docker compose up -d
    ```

### ❌ *Error Case 2: 500 Internal Error (Embedding Download)*
```
- Browser shows "500: Internal Error" when accessing http://localhost:3000
- Container shows "Up X minutes (unhealthy)" status  
- Logs show "Fetching 30 files: 0%" stuck at 0% for a long time
```

**🔧 Solution:**
The app is downloading embedding models (30 files, several GB). This can be slow or stuck on slow connections.

**⚠️ Note**: Disabling embeddings is *not recommended* as they're needed for:
- AI agent workflow integration
- Enhanced web search & document processing  
- RAG capabilities for document upload/querying

**⚡ Quick fix** - Disable embeddings to start faster for checking functionality *(NOT RECOMMENDED FOR CS59 PROJECT)*:
```bash
# Stop containers
docker compose down

# Edit docker-compose.yaml and add this line under open-webui environment:
# - ENABLE_EMBEDDING=false

# Restart
OPEN_WEBUI_PORT=3000 docker compose up -d

# Wait 1-2 minutes, then check:
docker ps --format "{{.Names}}\t{{.Status}}" | grep open-webui
# Should show "healthy" instead of "unhealthy"
```

**✅ Recommended approach** - Wait for download to complete (can take 10-30 minutes):
```bash
# Monitor progress
docker logs -f open-webui | grep -E "(Fetching|files)"

# Wait until you see "Fetching 30 files: 100%" then test:
curl -I http://localhost:3000
# Should return "HTTP/1.1 200 OK"

# Verify full functionality
docker ps --format "{{.Names}}\t{{.Status}}" | grep open-webui
# Should show "healthy" status
```

**✅ Verified working** - Full CerebraUI functionality with embeddings enabled for CS59 project requirements.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 🔄 *Complete Restart & Verification*

### 🧹 Step 1: Clean Shutdown
```bash
docker compose down -v
```
**✅ Removes all containers and volumes for fresh start**

### 🚀 Step 2: Fresh Start
```bash
OPEN_WEBUI_PORT=3000 docker compose pull && OPEN_WEBUI_PORT=3000 docker compose up -d
```
**✅ Updates images and starts all services**

### ⏳ Step 3: Wait for Startup
```bash
sleep 30  # Wait for containers to initialize
```

### 📊 Step 4: Check Container Status
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(open-webui|ollama|redis)"
```
**✅ Should show all 3 containers running**

### 🔍 Step 5: Monitor Embedding Download
```bash
docker logs open-webui 2>&1 | grep -E "(Fetching|files)" | tail -3
```
**✅ Shows embedding download progress**

### 🧪 Step 6: Test Redis Connection
```bash
docker exec -it redis redis-cli PING
```
**✅ Should return "PONG"**

### 🌐 Step 7: Test Web Interface
```bash
curl -I http://localhost:3000 2>/dev/null | head -1
```
**✅ Should return HTTP status when ready**

### 🤖 Step 8: Test Ollama Connection
```bash
docker exec -it ollama ollama list
```
**✅ Should show available models (empty initially)**

### 📈 Monitor Progress (Optional)
```bash
# Check container health
docker ps --format "{{.Names}}\t{{.Status}}" | grep open-webui

# Monitor embedding progress
docker logs -f open-webui | grep -E "(Fetching|files)"
```

**⏰ Expected Timeline:**
- **Worst case: 20-30 minutes** for embedding download to complete
- **Web interface** will be accessible at http://localhost:3000 once healthy


-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 👥 Team Development Workflow (CS59)

### 🌿 Feature Branch Names
Each team member should create their feature branch from `pin/0.6.5v`:

```bash
# Frontend & UI
feat/jiayi-frontend-components

# Authentication & Security  
feat/sadman-betterauth-integration
feat/tasnim-auth-hardening

# AI & Workflows
feat/matthew-langflow-integration
feat/perry-comfyui-deployment

# Search & Engines
feat/tongfangzhu-search-apis

# Infrastructure & Caching
feat/abhishek-redis-sessions
```

### 🔄 Git Workflow Commands
```bash
# 1. Clone and setup
git clone <your-repo-url>
cd "capstone project/cerebra-ui"

# 2. Switch to stable base branch
git checkout pin/0.6.5v
git pull origin pin/0.6.5v

# 3. Create your feature branch
git checkout -b feat/[your-name]-[feature]
# Example: git checkout -b feat/sadman-betterauth-integration

# 4. Start development
OPEN_WEBUI_PORT=3000 docker compose up -d
# Wait for embeddings, then start coding

# 5. Commit and push your work
git add .
git commit -m "feat: [brief description of your feature]"
git push origin feat/[your-name]-[feature]

# 6. Create Pull Request to pin/0.6.5v when ready
```



