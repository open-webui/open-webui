# Automatic Database Initialization Implementation

## 🎯 Implementation Complete: Option 1 - Container Startup Hook

### **What Was Implemented:**

1. **Created `usage_tracking_init.py`** (`backend/open_webui/utils/usage_tracking_init.py`)
   - `initialize_usage_tracking_from_environment()` - Main initialization function
   - `ensure_usage_tracking_tables()` - Creates tables if missing
   - Idempotent operations (safe to run multiple times)
   - Proper error handling and logging

2. **Updated `main.py`** (`backend/open_webui/main.py`)
   - Added imports for `OPENROUTER_EXTERNAL_USER` and `ORGANIZATION_NAME`
   - Added initialization hook in `lifespan()` async context manager
   - Runs automatically on every container startup
   - Only runs if environment variables are present

### **How It Works:**

```python
# In main.py lifespan function:
if OPENROUTER_EXTERNAL_USER and ORGANIZATION_NAME:
    try:
        from open_webui.utils.usage_tracking_init import initialize_usage_tracking_from_environment
        init_result = await initialize_usage_tracking_from_environment()
        if init_result:
            log.info(f"✅ Usage tracking initialized for {ORGANIZATION_NAME}")
```

### **Database Operations:**

1. **Checks if client organization exists**
   - If yes: Updates API key and name (in case they changed)
   - If no: Creates new client organization record

2. **Ensures all tables exist**
   - `client_organizations`
   - `client_user_daily_usage`
   - `client_model_daily_usage`
   - Creates indexes for performance

3. **Idempotent Design**
   - Uses `CREATE TABLE IF NOT EXISTS`
   - Uses `INSERT OR UPDATE` logic
   - Safe to run on every startup

### **Production Benefits:**

✅ **Automatic**: No manual database setup required  
✅ **Self-healing**: Recreates missing tables if needed  
✅ **Environment-driven**: Configuration from .env file  
✅ **Error tolerant**: Won't crash app if initialization fails  
✅ **Logged**: Clear log messages for debugging  

### **Testing the Implementation:**

#### **Production Environment:**
1. **Restart Docker Container:**
   ```bash
   docker-compose -f docker-compose-customization.yaml down
   docker-compose -f docker-compose-customization.yaml up -d
   ```

2. **Check Logs:**
   ```bash
   docker logs open-webui-customization 2>&1 | grep "Usage tracking"
   ```

#### **Development Environment:**
1. **Restart Development Containers:**
   ```bash
   ./dev-hot-reload.sh restart
   ```

2. **Check Development Logs:**
   ```bash
   ./dev-hot-reload.sh logs-be | grep "Usage tracking"
   # or
   docker logs mai-backend-dev 2>&1 | grep "Usage tracking"
   ```

3. **Expected Log:**
   ```
   ✅ Usage tracking initialized for Company_A
   ```

4. **Verify Database:**
   
   **Production:**
   ```bash
   docker exec open-webui-customization sqlite3 /app/backend/data/webui.db "SELECT name FROM client_organizations;"
   ```
   
   **Development:**
   ```bash
   docker exec mai-backend-dev sqlite3 /app/backend/data/webui.db "SELECT name FROM client_organizations;"
   ```
   
   Expected results:
   - Client organization created/updated
   - Usage tracking tables exist
   - Data ready for Usage Settings UI

### **Multi-Client Deployment:**

Each mAI instance will:
1. Read its own `.env` file (production) or `.env.dev` file (development)
2. Auto-initialize its own database
3. Track usage independently
4. No manual intervention needed

#### **Environment-Specific Behavior:**
- **Production**: Uses single-container architecture with isolated volumes
- **Development**: Uses two-container architecture with `mai_backend_dev_data` volume
- **Both**: Automatic database initialization on container startup

### **Next Steps:**

The automatic initialization is now production-ready. Every time a container starts:
- ✅ Reads environment variables (`.env` or `.env.dev`)
- ✅ Creates/updates database records
- ✅ Ensures schema is correct
- ✅ Ready for usage tracking

#### **Environment-Specific Access:**

**Production Access:**
- Container: `open-webui-customization`
- URL: http://localhost:3001
- Configuration: `.env`

**Development Access:**
- Containers: `mai-frontend-dev` + `mai-backend-dev`
- URL: http://localhost:5173 (frontend) + http://localhost:8080 (backend)
- Configuration: `.env.dev`
- Hot Reload: Instant updates for development

**No more manual database initialization required for either environment!**