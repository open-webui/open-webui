# Complete Workflow: Generate Client API Key from Org_B Provisioning Key

## Your Scenario:
- **Provisioning Key**: `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`
- **Organization**: Org_B
- **Goal**: Generate dedicated API key for a client

## Step 1: Configure Provisioning Key

```bash
cd /Users/patpil/Documents/Projects/mAI
python scripts/setup_provisioning_key.py
```

**Expected Output:**
```
🔑 Setting up OpenRouter Provisioning Key for Org_B...
✅ Provisioning key configured successfully!
   Organization: Org_B
   Key: sk-or-v1-0844a324c669...aaaf0e
   Markup Rate: 1.3x
   Currency: USD
✅ OpenRouter Client Manager is now configured and ready to generate client API keys!
```

## Step 2: Generate Client API Key

```bash
# Example: Create client for "Polish Company ABC"
python scripts/create_client_with_api_key.py \
  --client-name "Polish Company ABC" \
  --billing-email "billing@polishcompany.pl" \
  --monthly-limit 500.0 \
  --user-id "some-user-id-123"
```

**Expected Output:**
```
🏢 Creating client organization: Polish Company ABC
📞 Calling OpenRouter API to generate dedicated API key...
✅ Client organization created successfully!

📋 Client Details:
   ID: client_org_abc123
   Name: Polish Company ABC
   Markup Rate: 1.3x
   Monthly Limit: $500.0
   Billing Email: billing@polishcompany.pl

🔑 Generated API Key Details:
   API Key: sk-or-v1-generated...client123
   Key Hash: hash_from_openrouter
   OpenRouter Name: Client: Polish Company ABC
   Limit: $500.0

👤 Mapping user some-user-id-123 to organization...
✅ User mapping created successfully!

🎯 Next Steps:
1. Give this API key to your client: sk-or-v1-generated...client123
2. Client should configure it in mAI Settings → Connections → OpenRouter API Key
3. Usage will be automatically tracked with 1.3x markup
4. View usage in Admin Dashboard → Settings → Usage tab
```

## Step 3: Client Configuration

**What happens next:**
1. **Give the generated API key** to your client: `sk-or-v1-generated...client123`
2. **Client configures it** in their mAI instance: Settings → Connections → OpenRouter API Key
3. **Usage tracking starts** automatically with 1.3x markup
4. **View analytics** in Admin Dashboard → Settings → Usage tab

## Business Logic Flow:

```
Your Org_B Provisioning Key 
         ↓
OpenRouter generates dedicated client API key
         ↓
Client uses their dedicated API key in mAI
         ↓
All usage tracked with 1.3x markup
         ↓
You see profit margins in admin dashboard
```

## Database Structure:

```
global_settings:
├── openrouter_provisioning_key: "sk-or-v1-0844a324c669..." (Your Org_B key)
└── default_markup_rate: 1.3

client_organizations:
├── name: "Polish Company ABC"
├── openrouter_api_key: "sk-or-v1-generated...client123" (Generated for client)
├── markup_rate: 1.3
└── monthly_limit: 500.0

user_client_mapping:
├── user_id: "some-user-id-123"
├── client_org_id: "client_org_abc123"
└── openrouter_user_id: "temp_..." (auto-learns real ID)
```

## Verify Setup:

```bash
# Check if provisioning key is configured
python -c "
from backend.open_webui.utils.openrouter_client_manager import openrouter_client_manager
print('Configured:', openrouter_client_manager.is_configured())
print('Key preview:', openrouter_client_manager.provisioning_key[:20] if openrouter_client_manager.provisioning_key else 'None')
"

# List all client organizations
python -c "
from backend.open_webui.models.organization_usage import ClientOrganizationDB
clients = ClientOrganizationDB.get_all_active_clients()
for client in clients:
    print(f'{client.name}: {client.openrouter_api_key[:20]}...{client.openrouter_api_key[-10:]}')
"
```

## Production Deployment:

For your 20+ Polish clients on Hetzner Cloud:
1. **Run setup once** per Docker container
2. **Generate one API key** per client company
3. **Each container** gets isolated client data
4. **Usage tracking** works automatically with production system
5. **Billing data** aggregated for your reseller model