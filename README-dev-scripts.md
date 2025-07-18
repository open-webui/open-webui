# 🚀 mAI Development Scripts

Two convenient scripts to manage your development servers:

## 📁 Scripts Overview

### 1. `start-dev.sh` - Start Development Servers
**Use this at the beginning of your work**
- Starts both backend and frontend servers
- Checks for proper environment setup
- Shows server URLs and status
- Handles cleanup on exit

### 2. `refresh-dev.sh` - Refresh Development Servers  
**Use this to see changes after code modifications**
- Stops existing servers cleanly
- Restarts both backend and frontend
- Shows server URLs and status
- Reminds you to refresh browser

## 🔧 Usage

### Starting Development (Beginning of work):
```bash
./start-dev.sh
```

### Refreshing Servers (After making changes):
```bash
./refresh-dev.sh
```

## 📋 What Each Script Does

### start-dev.sh:
1. ✅ Checks if you're in the right directory
2. ✅ Verifies backend virtual environment exists
3. 🔧 Starts backend server (port 8080)
4. 🎨 Starts frontend server (port 5173)
5. 📝 Shows server URLs and instructions
6. 🛑 Handles cleanup when you press Ctrl+C

### refresh-dev.sh:
1. 🛑 Stops all existing development servers
2. ⏳ Waits for clean shutdown
3. 🔧 Restarts backend server
4. 🎨 Restarts frontend server
5. 💡 Reminds you to refresh browser
6. 🛑 Handles cleanup when you press Ctrl+C

## 🌐 Server URLs

After running either script, you'll have:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

## 💡 Tips

1. **Use Firefox** for testing (as recommended in project_info.md)
2. **Hard refresh browser** after using refresh-dev.sh: `Ctrl+Shift+R` (or `Cmd+Shift+R`)
3. **Press Ctrl+C** to stop servers cleanly
4. **Check console output** for any errors or status messages

## 🛠️ Troubleshooting

If scripts don't work:
1. Make sure you're in the mAI project root directory
2. Check that backend/.venv exists
3. Verify scripts are executable: `chmod +x start-dev.sh refresh-dev.sh`
4. Check for any running processes: `ps aux | grep -E "(npm|uvicorn)"`