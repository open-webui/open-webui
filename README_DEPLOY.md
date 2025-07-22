# Open WebUI - Deployment Ready

This is a fork of [Open WebUI](https://github.com/open-webui/open-webui) configured for easy deployment.

## Latest Version: 0.6.18

### New Features in Latest Version:
- Enhanced collaboration with prosemirror-collab
- Improved PDF handling with pdfjs-dist
- Better image processing with heic2any
- Advanced charting with chart.js
- Enhanced text editing with TipTap 3.0

## Quick Deploy Options

### Option 1: Render (Recommended - Full Stack)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/blueprint/new?repo=https://github.com/aloewright/open-webui)

### Option 2: Vercel (Frontend Only)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/aloewright/open-webui)

### Option 3: Netlify (Frontend Only)
[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/aloewright/open-webui)

## Local Development

```bash
# Clone the repository
git clone https://github.com/aloewright/open-webui.git
cd open-webui

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Environment Variables

For production deployment, configure these variables:

```env
VITE_API_BASE_URL=https://your-backend-api.com
WEBUI_SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@host:port/dbname
WEBUI_AUTH=true
```

## Deployment Configurations

This repository includes configuration files for:
- ✅ Vercel (`vercel.json`)
- ✅ Netlify (`netlify.toml`)  
- ✅ Render (`render.yaml`)
- ✅ GitHub Actions (`.github/workflows/`)

## Architecture Notes

Open WebUI has two main components:
1. **Frontend**: SvelteKit application (this repository)
2. **Backend**: Python FastAPI server

For platforms like Vercel/Netlify that primarily support frontend deployment, you'll need to deploy the backend separately on a Python-supporting platform like Render, Railway, or similar.

## Sync with Upstream

To keep updated with the latest Open WebUI features:

```bash
git fetch upstream
git merge upstream/main
git push origin main
```

---

**Original Project**: [open-webui/open-webui](https://github.com/open-webui/open-webui)
