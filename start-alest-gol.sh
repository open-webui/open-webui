#!/bin/bash

echo "🚀 Iniciando Open WebUI com tema Alest+GOL..."

# Copiar todos os assets estáticos necessários
echo "🔄 Garantindo que todos os assets estão disponíveis..."
mkdir -p backend/open_webui/static/

# Logos da parceria
cp static/Logo-Alest-Branco-240x104-1-1.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Logo Alest não encontrada"
cp static/logo-gol.svg backend/open_webui/static/ 2>/dev/null || echo "⚠️  Logo GOL não encontrada"

# Ícones e favicons
cp static/favicon.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Favicon não encontrado"
cp static/static/favicon.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Favicon (static) não encontrado"
cp static/static/favicon-96x96.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Favicon 96x96 não encontrado"
cp static/static/favicon.ico backend/open_webui/static/ 2>/dev/null || echo "⚠️  Favicon ICO não encontrado"
cp static/static/favicon.svg backend/open_webui/static/ 2>/dev/null || echo "⚠️  Favicon SVG não encontrado"
cp static/static/apple-touch-icon.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Apple touch icon não encontrado"
cp static/user.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  User icon não encontrado"
cp static/doge.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Doge icon não encontrado"
cp static/image-placeholder.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Image placeholder não encontrado"

# Outros arquivos necessários
cp static/manifest.json backend/open_webui/static/ 2>/dev/null || echo "⚠️  Manifest não encontrado"
cp static/marker-icon.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Marker icon não encontrado"
cp static/marker-shadow.png backend/open_webui/static/ 2>/dev/null || echo "⚠️  Marker shadow não encontrado"

# Verificar se as logos foram copiadas
if [ -f "backend/open_webui/static/Logo-Alest-Branco-240x104-1-1.png" ] && [ -f "backend/open_webui/static/logo-gol.svg" ]; then
    echo "✅ Logos Alest+GOL disponíveis!"
else
    echo "❌ Erro: Logos não encontradas!"
fi

# Definir variáveis de ambiente do Gemini
export GEMINI_API_KEY="AIzaSyDrqEFhXHRauPLVk4qUpvS0VSQSHh4LKKI"
export GEMINI_API_BASE_URL="https://generativelanguage.googleapis.com/v1beta"

echo "🔑 Gemini API configurado"
echo "🎨 Tema Alest+GOL ativo"

# Iniciar o backend
cd backend
python3 -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload