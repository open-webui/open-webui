# Manual Client Organization Deployment Guide

This guide explains how to manually create API keys for client organizations and deploy their mAI instances.

## Step-by-Step Process

### Step 1: Get Your OpenRouter Provisioning Key

1. Go to https://openrouter.ai/keys
2. Click "Create New Key" 
3. Select "Provisioning API Key"
4. Copy the key (starts with `sk-or-prov-`)

### Step 2: Create API Key for Client Organization

Run the interactive script:

```bash
cd /Users/patpil/Documents/Projects/mAI
python manual_client_setup.py
```

**Example Session:**
```
🔑 Manual Client API Key Creation
==================================================
Enter your OpenRouter provisioning key: sk-or-prov-your-key-here

🎯 What would you like to do?
1. Create API key for new client organization
2. List all existing client keys
3. Get information about specific key
4. Update key spending limit
5. Disable client key
6. Exit

Enter your choice (1-6): 1

📋 Creating new client API key...
Client organization name: Company ABC
Monthly spending limit in USD (or press Enter for no limit): 500
Custom label (or press Enter for 'client-company-abc'): 

🔄 Creating API key for 'Company ABC'...
✅ API key created successfully!

============================================================
📋 DEPLOYMENT INSTRUCTIONS FOR: Company ABC
============================================================
1. Deploy new mAI instance for: Company ABC
2. Set OpenAI API Base URL to: https://openrouter.ai/api/v1
3. Set OpenAI API Key to: sk-or-v1-abc123def456789...
4. Monthly spending limit: $500.0
5. Key hash for management: xyz789hash

📝 Save this information:
   Client: Company ABC
   API Key: sk-or-v1-abc123def456789...
   Key Hash: xyz789hash
   Limit: $500.0
============================================================
```

### Step 3: Deploy Client's mAI Instance

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
    image: your-mai-image:latest
    environment:
      - OPENAI_API_BASE_URL=https://openrouter.ai/api/v1
      - OPENAI_API_KEY=sk-or-v1-abc123def456789...
      - CLIENT_ORG_NAME=Company ABC
      - MONTHLY_LIMIT=500
    ports:
      - "8081:8080"  # Different port per client
    volumes:
      - ./data:/app/backend/data
EOF

docker-compose up -d
```

#### Option B: Environment Configuration
```bash
# Set environment variables for client's deployment
export OPENAI_API_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_API_KEY="sk-or-v1-abc123def456789..."
export CLIENT_ORG_NAME="Company ABC"
export MONTHLY_LIMIT="500"

# Start client's mAI instance
./start-mai-instance.sh
```

### Step 4: Configure Client's Database

Each client needs their own database with their organization record:

```sql
-- Insert client organization record
INSERT INTO client_organizations (
    id, name, openrouter_api_key, markup_rate, monthly_limit, 
    billing_email, is_active, created_at, updated_at
) VALUES (
    'company-abc-001',
    'Company ABC', 
    'sk-or-v1-abc123def456789...',
    1.3,
    500.0,
    'billing@companyabc.com',
    1,
    EXTRACT(EPOCH FROM NOW()) * 1000,
    EXTRACT(EPOCH FROM NOW()) * 1000
);
```

### Step 5: Client Access

1. **Company ABC employees** access their mAI at: `https://mai-companyabc.yourdomain.com`
2. **Admin logs in** and sees "My Organization Usage" interface
3. **Usage is tracked** automatically with 1.3x markup applied
4. **You monitor** all clients via OpenRouter dashboard

## Management Commands

### List All Client Keys
```python
python manual_client_setup.py
# Choose option 2
```

### Update Client Spending Limit
```python
python manual_client_setup.py
# Choose option 4
# Enter key hash and new limit
```

### Disable Client Key
```python
python manual_client_setup.py
# Choose option 5
# Enter key hash to disable
```

## File Structure

```
/Users/patpil/Documents/Projects/mAI/
├── manual_client_setup.py           # Interactive key creation
├── deployments/
│   ├── client-company-abc/          # Company ABC deployment
│   ├── client-company-xyz/          # Company XYZ deployment
│   └── client-company-def/          # Company DEF deployment
└── docs/
    └── manual-client-deployment.md  # This guide
```

## Best Practices

1. **Keep provisioning key secure** - only you should have it
2. **Document each client's API key hash** for management
3. **Set reasonable spending limits** to prevent overuse
4. **Monitor usage** through OpenRouter dashboard
5. **Deploy clients on separate domains/ports** for isolation
6. **Backup client databases** separately
7. **Test each deployment** before handing over to client

## Troubleshooting

### API Key Creation Fails
- Check provisioning key is correct
- Verify you have credits in OpenRouter account
- Ensure client name doesn't contain special characters

### Client Can't Access Models
- Verify OpenAI API Base URL is set to OpenRouter
- Check API key is correctly configured
- Confirm spending limit hasn't been exceeded

### Usage Not Tracking
- Ensure user mapping is configured in client's database
- Verify OpenRouter user parameter is being sent
- Check client organization record exists in database