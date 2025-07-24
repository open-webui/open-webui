# Client Organization Deployment Guide

This guide explains how to create API keys for client organizations and deploy their mAI instances. The process is now **fully automated** with no manual database configuration required.

## Step-by-Step Process

### Step 1: Get Your OpenRouter Provisioning Key

1. Go to https://openrouter.ai/keys
2. Click "Create New Key" 
3. Select "Provisioning API Key"
4. Copy the key (starts with `sk-or-prov-`)

### Step 2: Create API Key for Client Organization

Run the client key creation script:

```bash
cd /Users/patpil/Documents/Projects/mAI
python3 create_client_key_option1.py
```

**Example Session:**
```
🚀 Option 1: Simple Client API Key Creator & Usage Checker
============================================================
Select mode:
1. Create new API key
2. Check usage of existing API key
Enter choice (1 or 2): 1

Enter your OpenRouter provisioning key: sk-or-prov-your-key-here
Enter client organization name: Company ABC
Enter monthly spending limit (USD, or press Enter to skip): 500

🔑 Creating API key for client: Company ABC
📡 Response status: 201
✅ API key created successfully!

📋 CLIENT DATABASE ENTRY:
{
  "client_name": "Company ABC",
  "api_key": "sk-or-v1-abc123def456789...",
  "key_id": "12345",
  "monthly_limit": 500.0,
  "created_at": "2025-07-24T16:00:00",
  "usage_tracking": "Option 1 - Daily summaries + live counters"
}

🎯 MANUAL SETUP INSTRUCTIONS:
1. Give API key to client administrator: sk-or-v1-abc123def456789...
2. Client enters key in Settings → Connections
3. System automatically configures organization and usage tracking
4. External user ID is auto-learned on first API call

✅ Zero manual database configuration required!
```

### Step 3: Client Setup (Automated)

**🎉 This step is now fully automated!** Simply give the API key to the client administrator:

1. **Send API key** to client: `sk-or-v1-abc123def456789...`
2. **Client login** to their mAI instance 
3. **Client navigates** to Settings → Connections
4. **Client enters** the API key in OpenAI API Key field
5. **System automatically**:
   - Syncs API key to organization database
   - Configures usage tracking
   - Learns external_user on first API call
   - Starts recording usage immediately

**No manual database configuration needed!**

### Step 4: Deploy Client's mAI Instance

For each client organization, create a separate mAI deployment:

#### Option A: Docker Deployment
```bash
# Create client-specific deployment
mkdir mai-client-companyabc
cd mai-client-companyabc

# Create docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.8'
services:
  mai-companyabc:
    image: mai-production:latest
    environment:
      - WEBUI_NAME=mAI - Company ABC
      - ENABLE_SIGNUP=false
    ports:
      - "8081:8080"  # Different port per client
    volumes:
      - ./data:/app/backend/data
    restart: unless-stopped
EOF

docker-compose up -d
```

**Note**: API keys are now configured through the web UI, not environment variables.

#### Option B: Single Instance (Recommended)
For production, use a single mAI instance that handles multiple organizations:

```bash
# Single deployment for all clients
docker run -d \
  --name mai-production \
  -p 3000:8080 \
  -v mai-data:/app/backend/data \
  -e WEBUI_NAME=mAI \
  -e ENABLE_SIGNUP=false \
  --restart unless-stopped \
  mai-production:latest
```

Each client uses the same instance but with their own API key entered through Settings.

## ✅ Automated Features

### API Key Sync
- When client enters API key in UI, it automatically syncs to database
- No manual database configuration required
- Organization record created/updated automatically

### External User Learning
- System automatically learns OpenRouter's external_user on first API call
- No need to manually configure external_user mappings
- Usage tracking starts immediately after first API call

### Usage Tracking
- Real-time usage recording with 1.3x markup
- Admin dashboard with live updates every 30 seconds
- Historical data and analytics automatically maintained

## Client Access & Management

### For Clients
1. **Access mAI**: Use provided URL (e.g., `https://mai.yourdomain.com`)
2. **Login**: Use provided credentials  
3. **Configure API**: Settings → Connections → Enter OpenRouter API key
4. **Monitor Usage**: Admin can view usage in Settings → Usage tab

### For You (Service Provider)
- **Monitor all clients**: OpenRouter dashboard shows aggregate usage
- **Check client usage**: Each client's admin can see their organization usage
- **Update limits**: Use OpenRouter dashboard to adjust spending limits
- **Create new clients**: Run `create_client_key_option1.py` script

## Management Commands

### Create New Client
```bash
python3 create_client_key_option1.py
# Choose mode 1 (Create new API key)
```

### Check Client Usage  
```bash
python3 create_client_key_option1.py  
# Choose mode 2 (Check usage of existing API key)
```

## Best Practices

1. **Keep provisioning key secure** - only you should have it
2. **Set reasonable spending limits** when creating API keys
3. **Monitor usage** through OpenRouter dashboard and client admin panels
4. **Use single instance deployment** for easier management
5. **Test client setup** by making API calls and checking usage appears
6. **Document client API keys** for future reference

## Troubleshooting

### API Key Creation Fails
- Check provisioning key is correct
- Verify you have credits in OpenRouter account
- Ensure client name doesn't contain special characters

### Client Can't Access Models
- Verify OpenAI API Base URL is set to `https://openrouter.ai/api/v1`
- Check API key is correctly entered in Settings → Connections
- Confirm spending limit hasn't been exceeded

### Usage Not Tracking
- ✅ **This is now automated!** Usage tracking starts automatically
- If still issues: Check Docker logs for auto-learning messages
- Verify client has made at least one API call after entering key
- Check Settings → Usage tab for real-time usage display

### Auto-Learning Not Working
- Check Docker logs: `docker logs [container] | grep "Auto-learning"`
- Verify API key is correctly entered in UI
- Ensure user has admin permissions to see usage tracking
- Try logging out and back in to refresh authentication

## Migration from Manual Setup

If you have existing clients with manual database configuration:

1. **API keys sync automatically** when updated in UI
2. **External user learning** will update on next API call
3. **No database changes needed** - system is backward compatible
4. **Existing usage data** is preserved