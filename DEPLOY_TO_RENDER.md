# Deploy Open WebUI to Render

This guide will help you deploy Open WebUI to Render with managed PostgreSQL and email authentication configured for a private instance.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Your Open WebUI code should be in a GitHub repository
3. **Admin Email**: Set manually in Render dashboard (see Post-Deployment Setup)

## Quick Deploy

### Option 1: One-Click Deploy (Recommended)

1. **Fork or Push** this repository to your GitHub account
2. **Connect to Render**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository containing this Open WebUI code
3. **Deploy**:
   - Render will automatically detect the `render.yaml` file
   - Review the configuration and click "Apply"
   - Wait for deployment (usually 10-15 minutes)

### Option 2: Manual Setup

If you prefer manual configuration:

1. **Create PostgreSQL Database**:
   - Go to Render Dashboard → "New" → "PostgreSQL"
   - Name: `openwebui-postgres`
   - Plan: Starter ($7/month)
   - Database Name: `openwebui`
   - User: `openwebui`

2. **Create Web Service**:
   - Go to Render Dashboard → "New" → "Web Service"
   - Connect your GitHub repository
   - Runtime: Docker
   - Plan: Starter ($7/month)
   - Add environment variables (see Configuration section below)

## Configuration

### Core Environment Variables

The following are automatically configured in `render.yaml`:

**Database & Security:**
```bash
DATABASE_URL=<automatically set from managed Postgres>
WEBUI_SECRET_KEY=<automatically generated>
WEBUI_AUTH=True
ENABLE_SIGNUP=False
ENABLE_INITIAL_ADMIN_SIGNUP=True
```

**Authentication (Private Instance):**
```bash
DEFAULT_USER_ROLE=pending
WEBUI_SESSION_COOKIE_SECURE=true
WEBUI_AUTH_COOKIE_SECURE=true
```

**Web Search:**
```bash
ENABLE_WEB_SEARCH=True
WEB_SEARCH_ENGINE=duckduckgo
WEB_SEARCH_RESULT_COUNT=5
```

### Optional: Enhanced Search Engines

After deployment, you can add API keys for better search engines through the admin interface:

**Brave Search (Recommended):**
- Get API key from [brave.com/search/api](https://brave.com/search/api)
- Add `BRAVE_SEARCH_API_KEY` environment variable
- Change `WEB_SEARCH_ENGINE` to `brave`

**Serper (Google-powered):**
- Get API key from [serper.dev](https://serper.dev)
- Add `SERPER_API_KEY` environment variable
- Change `WEB_SEARCH_ENGINE` to `serper`

## Post-Deployment Setup

### 1. Access Your Instance

Your instance will be available at: `https://openwebui.onrender.com`

### 2. Set Admin Email (Important!)

Before creating your admin account, you need to set your admin email:
1. Go to Render Dashboard → Your Service → Environment
2. Click "Add Environment Variable"
3. Add: `ADMIN_EMAIL` = `your-email@example.com`
4. Click "Save Changes" (service will restart automatically)

### 3. Create Admin Account

1. Visit your deployed URL (after the restart completes)
2. Click "Sign up" (only available for the first admin account)
3. Use the same email you set in the ADMIN_EMAIL variable
4. Create a secure password
5. Complete registration

### 3. Disable Initial Signup (Security)

After creating your admin account:
1. Go to Admin Panel → Settings → Authentication
2. Ensure "Enable Signup" is disabled
3. This prevents others from creating accounts

### 4. Test Web Search

1. Start a new chat
2. Ask a question like "What's the weather in London today?"
3. The system should automatically search the web and provide current information

## Managing Users

Since this is a private instance:

1. **Add Users**: Only you (admin) can create new user accounts
2. **User Approval**: New users default to "pending" status
3. **Access Control**: You control who can access your instance

To add a new user:
1. Admin Panel → Users → Add User
2. Set their role (user/admin)
3. They can then log in with their credentials

## Monitoring & Maintenance

### Health Checks

Render automatically monitors your service health at `/health` endpoint.

### Logs

View application logs:
- Render Dashboard → Your Service → Logs
- Real-time log streaming available

### Database Backups

Render automatically backs up your PostgreSQL database:
- Daily backups for Starter plan
- Access via Render Dashboard → Database → Backups

### Updates

To update Open WebUI:
1. Pull latest changes to your repository
2. Push to GitHub
3. Render will automatically redeploy (if auto-deploy is enabled)

## Cost Breakdown

**Monthly Costs (Render Starter Plan):**
- Web Service: $7/month
- PostgreSQL Database: $7/month
- **Total: $14/month**

## Troubleshooting

### Common Issues

1. **Build Fails**:
   - Check build logs in Render Dashboard
   - Ensure Dockerfile is present and valid
   - Verify environment variables are set correctly

2. **Database Connection Issues**:
   - Verify DATABASE_URL is properly set
   - Check database service is running
   - Review connection pool settings

3. **Authentication Issues**:
   - Ensure WEBUI_SECRET_KEY is set
   - Check cookie security settings
   - Verify HTTPS is enabled

4. **Web Search Not Working**:
   - Check ENABLE_WEB_SEARCH=True
   - Verify search engine configuration
   - Review logs for API errors

### Getting Help

1. **Render Support**: [render.com/docs](https://render.com/docs)
2. **Open WebUI Docs**: [docs.openwebui.com](https://docs.openwebui.com)
3. **GitHub Issues**: [github.com/open-webui/open-webui](https://github.com/open-webui/open-webui)

## Security Best Practices

1. **Use Strong Passwords**: For your admin account
2. **Regular Updates**: Keep Open WebUI updated
3. **Monitor Access**: Review user accounts regularly
4. **Backup Data**: Render handles database backups
5. **Environment Variables**: Keep API keys secure

## Features Enabled

✅ **Included in this deployment:**
- Email/password authentication
- Private instance (no public signup)
- Web search integration
- PostgreSQL database with connection pooling
- HTTPS security
- Automatic health checks
- Compression middleware

❌ **Disabled for starter setup:**
- Ollama integration (can be enabled later)
- Image generation (can be enabled later)
- Code execution (can be enabled later)
- OAuth providers (can be configured later)

Your Open WebUI instance is now ready for private use with web search capabilities!
