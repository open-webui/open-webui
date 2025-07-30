export CORS_ALLOW_ORIGIN=http://localhost:5173/
PORT="${PORT:-8080}"

# Copiar assets da parceria Alest+GOL
echo "🔄 Copiando assets da parceria Alest+GOL..."
# Logos
cp ../static/Logo-Alest-Branco-240x104-1-1.png open_webui/static/ 2>/dev/null || echo "⚠️  Logo Alest não encontrada"
cp ../static/logo-gol.svg open_webui/static/ 2>/dev/null || echo "⚠️  Logo GOL não encontrada"
# Ícones essenciais
cp ../static/favicon.png open_webui/static/ 2>/dev/null || echo "⚠️  Favicon não encontrado"
cp ../static/user.png open_webui/static/ 2>/dev/null || echo "⚠️  User icon não encontrado"
cp ../static/doge.png open_webui/static/ 2>/dev/null || echo "⚠️  Doge icon não encontrado"
cp ../static/image-placeholder.png open_webui/static/ 2>/dev/null || echo "⚠️  Image placeholder não encontrado"
cp ../static/manifest.json open_webui/static/ 2>/dev/null || echo "⚠️  Manifest não encontrado"
echo "✅ Assets copiados com sucesso!"

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload
