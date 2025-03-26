#!/bin/bash

set -e  # Exit on error

echo "🔄 Pulling latest changes from GitHub..."
cd /opt/open-webui
git pull origin main

echo "📦 Updating backend Python dependencies..."
cd backend
source venv/bin/activate
pip install -r requirements.txt

echo "🛠 Building frontend..."
cd /opt/open-webui
npm install
npm run build

echo "🚀 Restarting OpenWebUI service..."
systemctl restart openwebui

echo "✅ Update complete!"
