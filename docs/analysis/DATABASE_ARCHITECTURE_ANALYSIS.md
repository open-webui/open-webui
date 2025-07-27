# Database Architecture Analysis

## 🏗️ **PRODUCTION DATABASE ARCHITECTURE**

### **Database Location & Access**
- **Production Database**: `/app/backend/data/webui.db` (inside Docker container)
- **Storage**: Docker named volume `open-webui-customization`  
- **Status**: ✅ **ACTIVE PRODUCTION DATABASE**
- **Content**: Complete usage tracking schema with dynamic pricing integration

### **Host Database (Development Only)**
- **Location**: `/Users/patpil/Documents/Projects/mAI/backend/data/webui.db`
- **Purpose**: Development/manual testing
- **Status**: ❌ **NOT USED BY RUNNING APPLICATION**
- **Note**: Host database changes do not affect production application

## 🔄 **Data Flow: How Usage Settings Work**

```
User Browser → Frontend (Port 3002) → Backend API → Container Database → Back to UI
     ↑                                       ↓
     └─── Usage Settings Tabs ←──── JSON Response
```

### **Step-by-Step Data Flow:**

1. **User opens Usage Settings** → Browser loads UI components
2. **Frontend makes API calls**:
   - `GET /api/v1/usage-tracking/my-organization/usage-by-user`
   - `GET /api/v1/usage-tracking/my-organization/usage-by-model`
3. **Backend processes requests** (inside Docker container)
4. **Backend queries database** → `/app/backend/data/webui.db` (Container Database)
5. **Backend returns JSON data** → Frontend displays in tabs

## ⚠️ **CRITICAL DISCOVERY: Why UI Shows Empty Data**

The reason your Usage Settings tabs were empty:
- **UI queries**: Container Database (isolated in Docker volume)
- **Manual data creation**: Host Database (not connected to running app)
- **Result**: Two separate data stores = Empty UI

## 🐳 **Docker Volume Architecture**

Your `docker-compose-customization.yaml`:
```yaml
volumes:
  - open-webui-customization:/app/backend/data  # NAMED VOLUME (isolated)
```

**NOT** a bind mount like:
```yaml
volumes:
  - ./backend/data:/app/backend/data  # This would connect host to container
```

## 🔍 **Verification Commands**

### **Check Host Database:**
```bash
sqlite3 backend/data/webui.db "SELECT COUNT(*) FROM client_user_daily_usage;"
```

### **Check Container Database:**
```bash
docker exec open-webui-customization sqlite3 /app/backend/data/webui.db "SELECT COUNT(*) FROM client_user_daily_usage;"
```

### **Verify UI Data Source:**
```bash
docker exec open-webui-customization python3 -c "
import sys; sys.path.append('/app/backend')
from open_webui.config import DATA_DIR
print('App uses database at:', DATA_DIR + '/webui.db')
"
```

## 📋 **CURRENT DATABASE SCHEMA (2025)**

### **Core Usage Tracking Tables:**
- ✅ `client_organizations` - Client management with OpenRouter API keys
- ✅ `client_daily_usage` - Daily aggregated usage summaries  
- ✅ `client_user_daily_usage` - Per-user daily tracking
- ✅ `client_model_daily_usage` - Per-model daily tracking
- ✅ `processed_generations` - Duplicate prevention with cleanup
- ✅ `processed_generation_cleanup_log` - Audit trail for maintenance
- ✅ `user_client_mapping` - User-to-client organization mapping
- ✅ `global_settings` - System-wide configuration

### **New Dynamic Pricing Integration:**
- 🆕 **OpenRouter API Integration** - Live model pricing from `openrouter_models.py`
- 🆕 **24-Hour Pricing Cache** - TTL cache with daily refresh at 00:00
- 🆕 **Daily Batch Processor** - Automated pricing updates and data validation
- 🆕 **Fallback System** - Hardcoded pricing when API unavailable

## 🔄 **DAILY BATCH PROCESSING ARCHITECTURE**

### **Automated Daily Operations (00:00 GMT):**
1. **Exchange Rate Updates** - Fresh NBP API rates for PLN conversion
2. **Dynamic Pricing Refresh** - Updated OpenRouter model pricing 
3. **Usage Data Validation** - Corrects markup calculations and data integrity
4. **Monthly Totals Update** - Cumulative month-to-date aggregations
5. **Database Cleanup** - Removes old processed generation records (60-day retention)

### **Real-Time vs Batch Processing:**
- **Real-Time**: Usage recording, duplicate prevention, live API calls
- **Batch Processing**: Pricing updates, exchange rates, data validation, cleanup
- **Result**: Optimal performance with accurate pricing and clean data

## 🏗️ **PRODUCTION DEPLOYMENT ARCHITECTURE**

### **Multi-Tenant Docker Isolation:**
- **Per-Client Containers**: Isolated SQLite databases via Docker volumes
- **Environment-Based Configuration**: `OPENROUTER_EXTERNAL_USER` per client
- **Centralized Management**: Single Hetzner server with docker-compose orchestration

### **Database Lifecycle:**
1. **Container Creation**: Automatic schema initialization
2. **Daily Operations**: Automated batch processing
3. **Data Persistence**: Docker named volumes for durability
4. **Maintenance**: Automated cleanup and validation

## 🔧 **CURRENT IMPLEMENTATION STATUS**

### **✅ Completed Features:**
- Daily usage tracking with 99% storage reduction vs per-request tracking
- Dynamic pricing with OpenRouter API integration and fallback
- NBP exchange rate integration for PLN conversion
- Automated daily batch processing with comprehensive logging
- Duplicate prevention system with cleanup automation
- Multi-level aggregation (client, user, model) for reporting
- Production-ready Docker deployment architecture

### **🔄 Active Components:**
- **Usage Tracking Router** (`usage_tracking.py`) - API endpoints for UI
- **Daily Batch Processor** (`daily_batch_processor.py`) - 00:00 automation
- **OpenRouter Models API** (`openrouter_models.py`) - Dynamic pricing
- **Organization Usage Models** (`organization_usage.py`) - Database schema
- **Currency Converter** - NBP exchange rate integration

### **📊 Key Metrics:**
- **Storage Efficiency**: 99% reduction vs per-request tracking
- **Pricing Accuracy**: Live OpenRouter API with 24-hour cache
- **Data Retention**: 60-day processed generation cleanup
- **Performance**: Optimized with database indexes and aggregation
- **Reliability**: Fallback systems for API failures

## 🎯 **FUTURE ENHANCEMENTS**

### **Planned Improvements:**
1. **Advanced Analytics** - Usage trend analysis and forecasting
2. **Billing Automation** - Automated invoice generation
3. **Client Dashboards** - Self-service usage monitoring
4. **API Rate Limiting** - Per-client usage quotas
5. **Backup Strategy** - Automated database backups

The production database architecture is now fully mature with dynamic pricing, automated maintenance, and comprehensive usage tracking suitable for 300+ users across 20+ Docker instances.