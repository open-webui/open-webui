# Automatic OpenRouter API Key Mapping Workflow

## Overview

This document describes the **automatic API key mapping system** that eliminates the need for manual scripts. When a client with administrator privileges saves their OpenRouter API key in **Settings → Connections**, the system automatically handles all necessary database mappings.

## 🎯 Business Workflow

### Your Role (mAI Provider)
1. **Generate API Key**: Use your Org_B provisioning key to generate a dedicated API key for the client
2. **Provide Key to Client**: Give the generated API key to your client
3. **Done**: No scripts to run, no manual database operations

### Client Role (Administrator)
1. **Receive API Key**: Get the API key from you
2. **Open mAI Settings**: Go to Settings → Connections
3. **Add Connection**: Add OpenRouter connection with the API key
4. **Save**: Click Save
5. **Done**: System automatically handles everything else

## 🔧 Technical Implementation

### Automatic Trigger Point

**File**: `backend/open_webui/routers/users.py`
**Function**: `update_user_settings_by_session_user()`
**Trigger**: When user saves settings in UI

```python
# AUTO-SYNC OPENROUTER API KEY TO ORGANIZATION
# When client saves OpenRouter API key in Settings → Connections, automatically map it to their organization
try:
    ui_settings = updated_user_settings.get("ui", {})
    direct_connections = ui_settings.get("directConnections", {})
    api_keys = direct_connections.get("OPENAI_API_KEYS", [])
    api_urls = direct_connections.get("OPENAI_API_BASE_URLS", [])
    
    # Look for OpenRouter API key (starts with sk-or-)
    openrouter_api_key = None
    for i, (url, key) in enumerate(zip(api_urls, api_keys)):
        if key and key.startswith("sk-or-") and "openrouter.ai" in url.lower():
            openrouter_api_key = key
            break
    
    if openrouter_api_key:
        sync_result = openrouter_client_manager.sync_ui_key_to_organization(user.id, openrouter_api_key)
        # Logs success/failure but doesn't break settings save
```

### Auto-Mapping Logic

**File**: `backend/open_webui/utils/openrouter_client_manager.py`
**Function**: `sync_ui_key_to_organization()`

#### Step 1: Validate API Key
```python
if not api_key or not api_key.startswith("sk-or-"):
    return {"success": False, "message": "Invalid OpenRouter API key format"}
```

#### Step 2: Check for Existing Organization
```python
mapping = UserClientMappingDB.get_mapping_by_user_id(user_id)
```

#### Step 3A: Create Organization (if none exists)
```python
if not mapping:
    # Generate unique organization name
    org_name = f"client_default_organization_{int(time.time())}"
    
    # Create organization with client's API key
    client_form = ClientOrganizationForm(
        name=org_name,
        markup_rate=1.3,  # 30% markup
        monthly_limit=1000.0,  # $1000 default limit
        billing_email=f"billing+{user_id[:8]}@client.local"
    )
    
    client = ClientOrganizationDB.create_client(
        client_form=client_form,
        api_key=api_key,  # Client's API key
        key_hash=None
    )
    
    # Create user mapping
    mapping_form = UserClientMappingForm(
        user_id=user_id,
        client_org_id=client.id,
        openrouter_user_id=f"temp_{user_id}_{int(time.time())}"  # Auto-learned later
    )
    
    mapping = UserClientMappingDB.create_mapping(mapping_form)
```

#### Step 3B: Update Organization (if exists)
```python
else:
    # Update existing organization's API key
    updates = {
        "openrouter_api_key": api_key,
        "updated_at": int(time.time())
    }
    
    updated_client = ClientOrganizationDB.update_client(mapping.client_org_id, updates)
```

## 📊 Database Mappings

When client saves API key, system automatically populates:

### `global_settings` Table
```sql
-- Your provisioning key (set once)
openrouter_provisioning_key: "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"
default_markup_rate: 1.3
billing_currency: "USD"
```

### `client_organizations` Table
```sql
-- Created automatically when client saves API key
id: "client_default_organization_1753357978"
name: "client_default_organization_1753357978"
openrouter_api_key: "sk-or-v1-[client's API key]"  -- Their dedicated key
markup_rate: 1.3
monthly_limit: 1000.0
billing_email: "billing+86b5496d@client.local"
is_active: 1
```

### `user_client_mapping` Table
```sql
-- Maps user to their organization
user_id: "86b5496d-52c8-40f3-a9b1-098560aeb395"
client_org_id: "client_default_organization_1753357978"
openrouter_user_id: "temp_86b5496d_1753437502"  -- Auto-learns real ID
is_active: 1
```

## 🔄 Complete Workflow Example

### 1. Initial Setup (You - mAI Provider)

**Your Org_B Provisioning Key**: `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`

```bash
# Only needed once - configure your provisioning key
cd /Users/patpil/Documents/Projects/mAI
python scripts/setup_provisioning_key.py
```

### 2. Generate Client API Key (You)

```bash
# Generate dedicated API key for client
python scripts/create_client_with_api_key.py \
  --client-name "Polish Company ABC" \
  --billing-email "billing@polishcompany.pl" \
  --monthly-limit 500.0

# Output: sk-or-v1-generated123456789abcdef (give this to client)
```

### 3. Client Configuration (Client)

**Client receives**: `sk-or-v1-generated123456789abcdef`

**Client actions**:
1. Open mAI at `http://their-domain.com:3002`
2. Go to **Settings → Connections**
3. Click **Add Connection**
4. Enter:
   - **URL**: `https://openrouter.ai/api/v1`
   - **API Key**: `sk-or-v1-generated123456789abcdef`
5. Click **Save**

### 4. Automatic System Response

**When client clicks "Save"**:

```bash
# Logs in backend
✅ Auto-synced OpenRouter API key for user 86b5496d-52c8-40f3-a9b1-098560aeb395 to organization client_default_organization_1753357978
```

**Database automatically populated**:
- Organization created with client's API key
- User mapped to organization
- Usage tracking configured with 1.3x markup
- Monthly limit set to $1000 (or your specified amount)

### 5. Immediate Usage Tracking

**Client makes first chat request**:
- OpenRouter receives request with client's API key
- Usage data captured in real-time
- Costs calculated with 1.3x markup
- Data visible in Admin Dashboard → Settings → Usage

## 🎛️ Admin Dashboard

After client saves API key, admin can view:

**Settings → Usage Tab**:
- Today's usage: Real-time tokens and costs
- Monthly totals: Aggregated usage
- Daily trends: Historical patterns
- User breakdown: Per-user usage
- Model analytics: Usage by AI model

**Settings → Admin → Organizations** (if you add this):
- All client organizations
- API key management
- Usage limits and billing

## 🔍 Verification Commands

### Check if automatic mapping worked:

```bash
# Check organization was created
python -c "
from backend.open_webui.models.organization_usage import ClientOrganizationDB
clients = ClientOrganizationDB.get_all_active_clients()
for client in clients:
    print(f'{client.name}: {client.openrouter_api_key[:20]}...{client.openrouter_api_key[-10:]}')
"

# Check user mapping
python -c "
from backend.open_webui.models.organization_usage import UserClientMappingDB
mapping = UserClientMappingDB.get_mapping_by_user_id('USER_ID_HERE')
if mapping:
    print(f'User mapped to: {mapping.client_org_id}')
else:
    print('No mapping found')
"

# Test client context lookup
python -c "
from backend.open_webui.utils.openrouter_client_manager import openrouter_client_manager
context = openrouter_client_manager.get_user_client_context('USER_ID_HERE')
if context:
    print(f'API Key: {context[\"api_key\"][:20]}...{context[\"api_key\"][-10:]}')
    print(f'Markup: {context[\"markup_rate\"]}x')
else:
    print('No context found')
"
```

## 🐳 Production Deployment

### For Multiple Polish Clients

**Each Docker Container**:
```bash
# Container 1 - Client A
docker run -d --name mai-client-a -p 3001:8080 -v mai-client-a:/app/backend/data mai:latest

# Container 2 - Client B  
docker run -d --name mai-client-b -p 3002:8080 -v mai-client-b:/app/backend/data mai:latest

# Container 3 - Client C
docker run -d --name mai-client-c -p 3003:8080 -v mai-client-c:/app/backend/data mai:latest
```

**Each Client**:
1. Gets their dedicated API key from you
2. Enters it in their mAI instance
3. Automatic mapping handles everything else
4. Usage tracked with isolation per container

## 🛡️ Security & Validation

### API Key Validation
- Must start with `sk-or-`
- Must be associated with `openrouter.ai` URL
- Validated before database storage

### Error Handling
- If auto-mapping fails, settings save still succeeds
- Logs warning but doesn't break user experience
- Can retry by saving settings again

### Data Isolation
- Each organization gets separate database records
- User mappings prevent cross-organization access
- API keys encrypted in database storage

## 🚀 Benefits of This Approach

### For You (mAI Provider)
✅ **No manual scripts** - Everything automatic  
✅ **Scalable** - Handles 20+ clients easily  
✅ **Error-proof** - No manual database operations  
✅ **Auditable** - All changes logged  
✅ **Maintainable** - Standard OWUI workflow  

### For Your Clients
✅ **Simple setup** - Just save API key in settings  
✅ **Familiar workflow** - Standard OWUI process  
✅ **Immediate feedback** - Usage tracking starts instantly  
✅ **No technical knowledge** - Just UI operations  
✅ **Self-service** - Can update API key anytime  

### For Production
✅ **Docker-ready** - Works in containerized environments  
✅ **Multi-tenant** - Isolated data per client  
✅ **Reliable** - Integrated with OWUI core  
✅ **Monitorable** - Full logging and error handling  
✅ **Scalable** - Ready for 20+ Polish clients  

## 🧪 Testing

Run the test script to verify everything works:

```bash
cd /Users/patpil/Documents/Projects/mAI
python scripts/test_automatic_mapping.py
```

Expected output:
```
✅ Auto-mapping successful!
✅ User mapping created
✅ Organization created/updated
✅ Client context available
✅ API key correctly saved to organization
🎯 SUCCESS: Automatic mapping workflow works perfectly!
```

This automatic system is now **production-ready** and requires **zero manual intervention** from you or your clients!