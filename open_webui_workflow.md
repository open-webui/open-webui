# 🚀 Open WebUI – Fork, Develop & Deploy Workflow

## Übersicht

```
[Open WebUI GitHub] ──fork──► [Dein GitHub Repo]
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
               [Windows (Entwicklung)]    [Ubuntu Server]
               Lokales Coding,            156.67.26.249
               Tools entwickeln           Zieht vom GitHub Repo
                          │               und läuft Docker
                          └──push──►──pull──┘
```

---

## Schritt 1: Open WebUI auf GitHub forken

1. Gehe zu: **https://github.com/open-webui/open-webui**
2. Klicke oben rechts auf **"Fork"**
3. Konfiguriere den Fork:
   - **Owner**: Dein GitHub Account
   - **Repository name**: z.B. `open-webui` (oder `my-open-webui`)
   - ✅ **"Copy the `main` branch only"** – NUR main Branch kopieren reicht
4. Klicke **"Create fork"**

> [!IMPORTANT]
> Du hast jetzt `github.com/DEIN-USERNAME/open-webui` als deinen eigenen Fork.

---

## Schritt 2: Upstream-Sync einrichten (Updates von Open WebUI bekommen)

Damit du immer die neuesten Updates von Open WebUI bekommst, richtest du **GitHub's automatische Sync-Funktion** ein:

### Option A: Manuell via GitHub UI (einfach)
- In deinem Fork auf GitHub: Klicke **"Sync fork"** → **"Update branch"**
- Das kannst du machen, wann immer Open WebUI ein Update veröffentlicht.

### Option B: Automatisch per GitHub Action (empfohlen)
Erstelle in deinem Fork die Datei `.github/workflows/sync-upstream.yml`:

```yaml
name: Sync Fork with Upstream

on:
  schedule:
    - cron: '0 6 * * *'  # Täglich um 6 Uhr morgens
  workflow_dispatch:       # Manuell auslösbar

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Sync fork
        uses: aormsby/Fork-Sync-With-Upstream-action@v3.4
        with:
          upstream_sync_repo: open-webui/open-webui
          upstream_sync_branch: main
          target_sync_branch: main
          target_repo_token: ${{ secrets.GITHUB_TOKEN }}
```

> [!TIP]
> Mit Option B bekommst du täglich automatisch alle Upstream-Updates, ohne manuell einzugreifen.

---

## Schritt 3: Lokale Entwicklung auf Windows einrichten

### 3.1 Prerequisites installieren (Windows)
- [Git for Windows](https://git-scm.com/download/win)
- [Docker Desktop für Windows](https://www.docker.com/products/docker-desktop/) (für lokale Tests)
- [Node.js](https://nodejs.org/) (für Frontend-Entwicklung)
- [Python 3.11+](https://www.python.org/) (für Backend-Entwicklung)
- [VS Code](https://code.visualstudio.com/) (empfohlen)

### 3.2 Repo klonen (Windows Terminal / Git Bash)

```bash
# Deinen Fork klonen
git clone https://github.com/DEIN-USERNAME/open-webui.git
cd open-webui

# Upstream als Remote hinzufügen (für manuelle Updates)
git remote add upstream https://github.com/open-webui/open-webui.git

# Prüfen:
git remote -v
# origin    https://github.com/DEIN-USERNAME/open-webui.git (fetch)
# upstream  https://github.com/open-webui/open-webui.git (fetch)
```

### 3.3 Eigenen Development-Branch erstellen

```bash
# Entwickle NIEMALS direkt auf main!
git checkout -b dev/meine-tools
```

### 3.4 Lokales Testen mit Docker

```bash
docker compose up -d
# → http://localhost:3000
```

---

## Schritt 4: Eigene Tools entwickeln

### Wo du deine Tools hinlegst:
```
open-webui/
├── backend/
│   ├── open_webui/
│   │   ├── tools/           ← Deine Custom Tools hier
│   │   ├── functions/       ← Custom Functions
│   │   └── pipelines/       ← Pipelines
├── src/                     ← Frontend (SvelteKit)
└── .github/
    └── workflows/           ← CI/CD
```

### Workflow beim Entwickeln:

```bash
# Änderungen stagen
git add .

# Commit mit beschreibender Message
git commit -m "feat: Add custom tool XY"

# Zu deinem GitHub Fork pushen
git push origin dev/meine-tools
```

---

## Schritt 5: Ubuntu Server einrichten (156.67.26.249)

### 5.1 SSH-Verbindung zum Server

```bash
ssh user@156.67.26.249
```

### 5.2 Docker & Docker Compose auf Ubuntu installieren

```bash
# Docker installieren
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Prüfen:
docker --version
docker compose version
```

### 5.3 Deployment-Verzeichnis einrichten

```bash
# Verzeichnis anlegen
sudo mkdir -p /opt/open-webui
sudo chown $USER:$USER /opt/open-webui
cd /opt/open-webui

# Deinen Fork klonen
git clone https://github.com/fischerkev7/open-webui.git .
```

### 5.4 `docker-compose.yml` für Production erstellen

Erstelle `/opt/open-webui/docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  open-webui:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: open-webui
    restart: unless-stopped
    ports:
      - "3000:8080"  # Port 3000 nach außen
    volumes:
      - open-webui-data:/app/backend/data
    environment:
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  open-webui-data:
```

### 5.5 Umgebungsvariablen konfigurieren

```bash
# .env Datei erstellen
cat > /opt/open-webui/.env << 'EOF'
WEBUI_SECRET_KEY=dein-sehr-sicherer-geheimer-schlüssel-hier
OLLAMA_BASE_URL=http://localhost:11434
EOF

# Sicher machen
chmod 600 /opt/open-webui/.env
```

### 5.6 Ersten Build starten

```bash
cd /opt/open-webui
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Schritt 6: Automatisches Deployment per GitHub Actions (CI/CD)

Wenn du auf `main` pushst, soll der Server automatisch das Update ziehen und neu starten.

### 6.1 Deploy-Script auf dem Ubuntu Server erstellen

```bash
cat > /opt/open-webui/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "🔄 Pulling latest changes..."
cd /opt/open-webui
git pull origin main

echo "🏗️ Building Docker image..."
docker compose -f docker-compose.prod.yml up -d --build

echo "🧹 Cleaning up old images..."
docker image prune -f

echo "✅ Deployment complete!"
EOF

chmod +x /opt/open-webui/deploy.sh
```

### 6.2 GitHub Actions Workflow für Auto-Deployment

Erstelle in deinem Fork: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Ubuntu Server

on:
  push:
    branches:
      - main  # Nur wenn auf main gepusht wird

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: 156.67.26.249
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            /opt/open-webui/deploy.sh
```

### 6.3 GitHub Secrets einrichten

In deinem GitHub Repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Wert |
|-------------|------|
| `SERVER_USER` | Dein Ubuntu-Username (z.B. `ubuntu` oder `root`) |
| `SERVER_SSH_KEY` | Inhalt deines **privaten** SSH-Keys |

### 6.4 SSH-Key für GitHub Actions generieren (auf Ubuntu Server)

```bash
# Neues SSH-Key-Paar generieren
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# Public Key zu authorized_keys hinzufügen
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys

# Private Key anzeigen → dieser kommt als Secret in GitHub
cat ~/.ssh/github_deploy
```

> [!CAUTION]
> Kopiere den **privaten Key** (`github_deploy`, OHNE `.pub`) als `SERVER_SSH_KEY` Secret in GitHub. Niemals diesen Key öffentlich teilen!

---

## Schritt 7: Nginx Reverse Proxy (optional, aber empfohlen)

Damit dein Open WebUI unter Port 80/443 (Standard HTTP/HTTPS) erreichbar ist:

```bash
# Nginx installieren
sudo apt install nginx -y

# Konfiguration erstellen
sudo nano /etc/nginx/sites-available/open-webui
```

```nginx
server {
    listen 80;
    server_name 156.67.26.249;  # oder deine Domain

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/open-webui /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Schritt 8: Täglicher Entwicklungs-Workflow (Zusammenfassung)

```
1. Windows: git pull origin main          ← Neuesten Stand holen
2. Windows: git checkout -b dev/feature   ← Feature-Branch erstellen
3. Windows: [Code schreiben & testen]     ← Entwickeln
4. Windows: git push origin dev/feature   ← Push zum Fork
5. GitHub:  Pull Request: dev → main      ← PR erstellen & mergen
6. GitHub Actions: Automatisch deployen   ← CI/CD
7. Ubuntu:  Läuft automatisch aktuell     ← Server updated sich selbst
```

---

## Upstream Updates einspielen (Open WebUI Updates)

```bash
# Lokal auf Windows:
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
# → GitHub Action deployt automatisch auf den Server!
```

---

## Erreichbarkeit für andere

Nach dem Setup ist Open WebUI erreichbar unter:
- **http://156.67.26.249:3000** (oder Port 80 mit Nginx)
- Andere können sich dort registrieren/anmelden

> [!NOTE]
> Denke an **Firewall-Regeln**: Port 3000 (oder 80/443) muss in der UFW/Cloud-Firewall des Servers freigegeben sein:
> ```bash
> sudo ufw allow 3000/tcp
> sudo ufw allow 80/tcp
> sudo ufw allow 443/tcp
> ```
