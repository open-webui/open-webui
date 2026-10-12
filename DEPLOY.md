# TracexGPT Deployment Guide

## Your Current Setup (Local)

You have:
- `docs-site/ai/docker-compose.yml` — running Open WebUI with RAG
- `open-webui-data` Docker volume — holds all data (chats, embeddings, users)
- Product docs mounted for RAG
- Custom branding via CSS/JS injection

## What Happens to Your Data

| Data Type | Where It Is | Migrates to Server? | Action |
|-----------|-------------|---------------------|--------|
| **RAG Config** (top-k, threshold, etc.) | docker-compose env vars | ✅ Yes — just copy the file | No change needed |
| **Document Embeddings** | `open-webui-data` volume (ChromaDB) | ❌ No — local files | Re-embed on server |
| **Chat History** | `open-webui-data` volume (SQLite) | ❌ No | Create fresh on server |
| **User Accounts** | `open-webui-data` volume (SQLite) | ❌ No | Create new admin on server |
| **Uploaded Files** | `open-webui-data` volume | ❌ No | Re-upload if needed |
| **Knowledge Base Config** | `open-webui-data` volume | ❌ No | Recreate on server |

## Why Re-embedding Is Better Than Migration

1. **Cost**: $0.16 to re-embed entire docs (negligible)
2. **Reliability**: No ChromaDB version mismatch issues
3. **Clean Slate**: Server starts fresh, no legacy data conflicts
4. **Updates**: You probably want latest docs anyway before deploying

## Deploy Steps

### Step 1: Build Image on Your Machine

```bash
cd /Users/apple/Documents/foodsign/trace-open-webui
docker build -t tracexgpt:latest .
```

### Step 2: Save Image to File (Transfer to Server)

```bash
# Save the image as a tar file
docker save tracexgpt:latest | gzip > tracexgpt-image.tar.gz

# Copy to your server (scp, rsync, or upload)
scp tracexgpt-image.tar.gz user@your-server:/home/deploy/
```

### Step 3: On the Server

```bash
# Load the image
ssh user@your-server
docker load < tracexgpt-image.tar.gz

# Create docs folder and copy your documentation
mkdir -p /home/deploy/tracexgpt-docs
cp -r /path/to/your/docs/* /home/deploy/tracexgpt-docs/

# Set environment variables
export OPENAI_API_KEY="sk-your-key"
export WEBUI_SECRET_KEY="a-random-secret-string"
export HF_TOKEN="your-huggingface-token"
export PRESENTON_USER="admin"
export PRESENTON_PASS="your-secure-password"

# Run
cd /home/deploy
docker-compose -f docker-compose.prod.yml up -d

# Note: First run will download ~2GB Presenton image. Be patient.
```

### Step 4: First-Time Setup on Server

1. Open `http://your-server:3000`
2. Create admin account (first signup = admin since `ENABLE_SIGNUP=false` is... wait, that blocks signup)

**IMPORTANT**: If `ENABLE_SIGNUP=false`, you need to set `WEBUI_AUTH=true` and create the admin via environment:

```yaml
# Add to docker-compose.prod.yml environment:
- ENABLE_SIGNUP=true   # temporarily to create admin
```

Create admin, then set `ENABLE_SIGNUP=false` and restart.

### Step 5: Upload Documents for RAG

1. Go to Workspace → Knowledge
2. Create "FoodSign Complete" knowledge base
3. Upload all your docs from `/home/deploy/tracexgpt-docs`
4. Attach the knowledge base to your model

## Upgrading Later (New Code Changes)

```bash
# On your Mac — rebuild after code changes
docker build -t tracexgpt:latest .
docker save tracexgpt:latest | gzip > tracexgpt-image.tar.gz
scp tracexgpt-image.tar.gz user@your-server:/home/deploy/

# On server
ssh user@your-server
docker load < tracexgpt-image.tar.gz
docker-compose -f docker-compose.prod.yml up -d  # restarts with new image, data stays
```

**Data survives** because the volume `tracexgpt-data` is separate from the image.

## Rollback (If Something Breaks)

```bash
# On server
docker pull ghcr.io/open-webui/open-webui:main  # fallback to original
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## Cost Tracking & Monthly Limits (Built In)

TracexGPT now has **per-user monthly spending limits** with automatic cost tracking.

### How It Works

- **Default limit**: $5 USD per user per month (IST timezone)
- **Billing cycle**: Resets on 1st of every month at 00:00 IST (UTC+5:30)
- **Enforcement**: API calls are blocked with HTTP 402 when limit is reached
- **Admins**: Unlimited (no budget check)
- **Tracking**: Automatically records spend from every chat completion's token usage

### Admin APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/spending/` | GET | View all users' spending |
| `/api/v1/spending/me` | GET | Current user's spending |
| `/api/v1/spending/{user_id}` | PUT | Set a user's monthly limit |
| `/api/v1/spending/models` | GET | Curated model list with pricing |

### Adjust a User's Limit

```bash
# Set user limit to $20/month
curl -X PUT http://localhost:3000/api/v1/spending/user-uuid-here \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{"monthly_limit_usd": 20.0}'
```

### Environment Variable

```yaml
# In docker-compose.prod.yml
- DEFAULT_MONTHLY_LIMIT_USD=5.0   # Default for new users
```

## Curated Model List (All Model Types)

TracexGPT includes pricing for ALL model types Open WebUI supports. Legacy/duplicate models are hidden.

### Categories

| Tier | Models | Price Range | Use For |
|------|--------|-------------|---------|
| **Nano** | gpt-4o-mini, gemini-2.0-flash, llama-3.3-70b-groq | $0.10-$0.79/M | Quick answers, high volume |
| **Medium** | gpt-5.4-mini, claude-haiku-3.5, gemini-1.5-flash | $0.25-$4.50/M | Daily tasks, coding |
| **Standard** | gpt-4o, claude-sonnet-3.5, gemini-1.5-pro | $2.50-$15/M | Complex queries, RAG |
| **Reasoning** | o3, o4-mini | $1.10-$8/M | Math, logic, planning |
| **Flagship** | gpt-5.5, claude-opus-4-5, gemini-3.1-pro | $5-$75/M | Deep research, coding |
| **Vision** | gpt-4o-vision, gemini-1.5-pro-vision | $2.50-$10.50/M | Image description |
| **Image** | dall-e-3, dall-e-2 | $0.02-$0.04/img | Image generation |

### Hidden (Useless) Models

These are filtered out: gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4-32k, text-davinci, code-davinci, babbage, ada, curie, davinci, whisper-1, tts-1, tts-1-hd, o1-preview, o1-mini, o3-mini

### Default Chat Model

`gpt-4o-mini` — fast, cheap, good enough for most team queries.

## Client Users (Simplified UI)

Your team gets the full TracexGPT UI. External clients get a **simplified, locked-down experience**.

### What Clients See

- **No model selector** — locked to one model you choose
- **No folders** — flat chat list only
- **No settings, controls, or admin links**
- **Fixed system prompt** injected into every chat
- **Pre-assigned knowledge bases** only
- **Simple welcome screen** — just "Hello, Name" and a message box

### Creating a Client User

Only admins can create client accounts. Public signup is completely blocked.

```bash
# Admin API call to create a client user
curl -X POST http://your-server/api/v1/spending/clients \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "client@company.com",
    "name": "Acme Corp",
    "fixed_model_id": "gpt-4o-mini",
    "fixed_system_prompt": "You are an expert procurement assistant for TracexGPT. Always answer in a professional tone.",
    "assigned_kb_ids": ["kb-procurement-docs"],
    "monthly_limit_usd": 10.0
  }'
```

Response:
```json
{
  "user_id": "...",
  "email": "client@company.com",
  "temp_password": "abc123...",
  "message": "Client user created. Share the temporary password securely..."
}
```

**Share the temp password with the client via your secure channel (email/Slack).**

### How It Works

| Feature | Team (Admin/CS) | Client |
|---------|----------------|--------|
| Create accounts | Self + Admin API | **Admin only** |
| Model picker | Yes | **No (locked)** |
| Folders | Yes | **No** |
| Settings | Yes | **No** |
| System prompt | Configurable | **Fixed by admin** |
| Knowledge bases | Any they own | **Assigned only** |
| Cost limit | Configurable | **Set at creation** |

### Public Signup is Blocked

The `/api/auths/signup` endpoint hard-rejects all requests once the first admin exists. Only the very first admin can self-register. Everyone else must be created by an admin.

## Quick Checklist

- [ ] `OPENAI_API_KEY` set
- [ ] `WEBUI_SECRET_KEY` set (random string)
- [ ] `HF_TOKEN` set (for reranker download)
- [ ] `DEFAULT_MONTHLY_LIMIT_USD` set (default $5)
- [ ] `PRESENTON_USER` / `PRESENTON_PASS` set (for PPT generation)
- [ ] Docs copied to server (`/home/deploy/tracexgpt-docs`)
- [ ] Image built and transferred
- [ ] Admin account created (first signup)
- [ ] Knowledge base created and docs uploaded
- [ ] `ENABLE_SIGNUP=false` after admin created
