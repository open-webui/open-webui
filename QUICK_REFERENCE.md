# VPS Deployment Quick Reference

## One-Command Deployment (Linux/macOS)

```bash
git clone <repo> open-webui && cd open-webui && bash deploy-vps.sh
```

## Manual Steps (All Platforms)

### 1. Frontend Build
```bash
npm ci
npm run build
# Output: ./build directory ready to serve
```

### 2. Backend Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Run Backend
```bash
cd backend
export ENV=prod PORT=8080  # Linux/macOS
# OR set ENV=prod & set PORT=8080  (Windows CMD)

uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

### 4. Serve Frontend (separate terminal)
```bash
cd build
python -m http.server 5173
```

## Verification Tests

```bash
# Health check
curl http://localhost:8080/api/health

# Georgian text test
curl -X POST http://localhost:8080/api/v1/py_photo/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"გამარჯობა"}'
```

## Production Setup (with systemd)

### Backend Service
```ini
# /etc/systemd/system/open-webui-backend.service
[Unit]
Description=Open WebUI Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/open-webui/backend
ExecStart=/opt/open-webui/venv/bin/uvicorn \
  open_webui.main:app --host 0.0.0.0 --port 8080
EnvironmentFile=/opt/open-webui/.env
Environment="ENV=prod"
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable open-webui-backend
sudo systemctl start open-webui-backend
sudo systemctl status open-webui-backend
```

### Nginx Configuration (Frontend + API Proxy)
```nginx
upstream backend {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /opt/open-webui/build;
        try_files $uri /index.html;
    }

    # API Proxy
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Socket.IO
    location /socket.io {
        proxy_pass http://backend/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

## Common Issues

| Issue | Solution |
|-------|----------|
| `npm: command not found` | Install Node.js >= 18.13.0 |
| `python3: command not found` | Install Python >= 3.11 |
| Georgian renders as squares | Font file must exist: `scripts/fonts/NotoSansGeorgian-Bold.ttf` |
| `ModuleNotFoundError` | Activate venv and run `pip install -r backend/requirements.txt` |
| Port 8080 in use | Change port: `--port 8081` |

## Environment Variables (.env)

Required for production:
```env
PUBLIC_API_BASE_URL=https://yourdomain.com
WEBUI_URL=https://yourdomain.com
WEBUI_SECRET_KEY=<generate-random-secret>
CORS_ALLOW_ORIGIN=https://yourdomain.com
ENV=prod
```

## Performance Tips

- Use gunicorn: `pip install gunicorn && gunicorn -w 4 -k uvicorn.workers.UvicornWorker open_webui.main:app`
- Enable Nginx gzip compression
- Use Redis for session management
- Configure CDN for static assets
- Set appropriate worker timeouts

## Documentation Files

- `DEPLOYMENT.md` — Full deployment guide
- `VPS_DEPLOYMENT_SUMMARY.md` — Overview
- `deploy-vps.sh` — Automated script (Linux/macOS)
- `vps-check.sh` — Validation script (Linux/macOS)
- `vps-check.bat` — Validation script (Windows)

## Support Resources

- GitHub: https://github.com/open-webui/open-webui
- Docs: https://docs.openwebui.com
- Issues: GitHub Issues
