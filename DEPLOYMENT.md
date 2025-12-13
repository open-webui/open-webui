# VPS Deployment Guide for Open WebUI

This guide covers deploying Open WebUI to a VPS using npm and pip.

## Prerequisites

- Node.js >= 18.13.0 and <= 22.x.x
- npm >= 6.0.0
- Python 3.11+
- pip
- Git

## VPS Setup Steps

### 1. Clone Repository

```bash
cd /opt  # or your desired installation path
git clone https://github.com/open-webui/open-webui.git open-webui
cd open-webui
```

### 2. Frontend Build (npm)

```bash
# Install dependencies
npm ci

# Build frontend (generates ./build directory)
npm run build
```

### 3. Backend Setup (Python)

```bash
# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
```

### 4. Install Georgian Font Support (Critical for PY Photo)

```bash
# Ensure font is committed in repo (scripts/fonts/NotoSansGeorgian-Bold.ttf)
# If missing, download it:
bash scripts/download_noto_georgian.sh

# Verify Pillow has RAQM support (optional, for better text rendering):
pip install harfbuzz fribidi-py
```

### 5. Environment Configuration

```bash
# Copy and edit environment file
cp .env.example .env  # or copy existing .env

# Key settings for production:
# - Set PUBLIC_API_BASE_URL to your domain
# - Set WEBUI_URL to your domain
# - Configure CORS_ALLOW_ORIGIN properly
# - Set strong WEBUI_SECRET_KEY
# - Set up Redis if using voice credits
```

### 6. Run Backend (uvicorn)

```bash
cd backend
export ENV=prod
export PORT=8080

# Run with uvicorn (single process for testing)
uvicorn open_webui.main:app --host 0.0.0.0 --port 8080

# Or use gunicorn for production (install: pip install gunicorn)
# gunicorn -w 4 -k uvicorn.workers.UvicornWorker open_webui.main:app --bind 0.0.0.0:8080
```

### 7. Serve Frontend

```bash
# Option A: Use a simple HTTP server for the built frontend
cd /path/to/build
python3 -m http.server 5173

# Option B: Use Nginx (recommended for production)
# Configure Nginx to serve /path/to/open-webui/build and proxy API to backend
```

### 8. Production Setup with systemd (Optional)

Create `/etc/systemd/system/open-webui-backend.service`:

```ini
[Unit]
Description=Open WebUI Backend
After=network.target

[Service]
Type=simple
User=openwebui
WorkingDirectory=/opt/open-webui/backend
ExecStart=/opt/open-webui/venv/bin/uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
EnvironmentFile=/opt/open-webui/.env
Environment="ENV=prod"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable open-webui-backend
sudo systemctl start open-webui-backend
```

## Troubleshooting

### Georgian Text Renders as Squares

1. Verify font file exists:
   ```bash
   ls -la scripts/fonts/NotoSansGeorgian-Bold.ttf
   ```

2. Check Pillow features:
   ```bash
   python -c "from PIL import features; print('raqm:', features.check('raqm'))"
   ```

3. Check logs for `[PY_PHOTO]` messages showing font path.

### npm Build Fails

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm ci --force
npm run build
```

### Backend Module Not Found

```bash
# Ensure you're in the correct venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

## Verification

Test the deployment:

```bash
# Frontend (should return HTML)
curl http://localhost:5173

# Backend health check
curl http://localhost:8080/api/health

# PY Photo endpoint
curl -X POST http://localhost:8080/api/v1/py_photo/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"გამარჯობა საქართველო"}'
```

## Performance Tuning

For production, consider:

1. Use gunicorn with multiple workers
2. Set up Nginx reverse proxy with caching
3. Configure Redis for session management
4. Enable gzip compression
5. Set appropriate worker timeouts

See `docker-compose.yaml` for reference architecture.
