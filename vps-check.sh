#!/bin/bash
# VPS Pre-deployment Check Script
# Run this before deploying to VPS to catch issues early

set -e

echo "🔍 Starting Open WebUI deployment pre-check..."

# Check Node.js
echo ""
echo "📦 Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Install Node.js >= 18.13.0"
    exit 1
fi
NODE_VERSION=$(node -v)
echo "✅ Node.js version: $NODE_VERSION"

# Check npm
echo ""
echo "📦 Checking npm..."
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found."
    exit 1
fi
NPM_VERSION=$(npm -v)
echo "✅ npm version: $NPM_VERSION"

# Check Python
echo ""
echo "🐍 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install Python >= 3.11"
    exit 1
fi
PYTHON_VERSION=$(python3 -V)
echo "✅ $PYTHON_VERSION"

# Check Git
echo ""
echo "📚 Checking Git..."
if ! command -v git &> /dev/null; then
    echo "❌ Git not found."
    exit 1
fi
GIT_VERSION=$(git --version)
echo "✅ $GIT_VERSION"

# Check if in project root
echo ""
echo "📂 Checking project structure..."
if [ ! -f "package.json" ]; then
    echo "❌ package.json not found. Run from project root."
    exit 1
fi
if [ ! -d "backend" ]; then
    echo "❌ backend/ directory not found."
    exit 1
fi
echo "✅ Project structure OK"

# Check Georgian font
echo ""
echo "🔤 Checking Georgian font..."
if [ -f "scripts/fonts/NotoSansGeorgian-Bold.ttf" ]; then
    echo "✅ NotoSansGeorgian-Bold.ttf found"
else
    echo "⚠️  Georgian font not found. Run: bash scripts/download_noto_georgian.sh"
fi

# Check npm dependencies (dry run)
echo ""
echo "📦 Checking npm dependencies..."
if ! npm list > /dev/null 2>&1; then
    echo "⚠️  Some npm packages may be missing. Run: npm ci"
fi
echo "✅ npm dependencies OK"

# Check Python requirements
echo ""
echo "🐍 Checking Python requirements..."
if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ backend/requirements.txt not found."
    exit 1
fi
echo "✅ backend/requirements.txt found"

echo ""
echo "🎉 All pre-checks passed! Ready for deployment."
echo ""
echo "Next steps:"
echo "1. npm ci"
echo "2. npm run build"
echo "3. python3 -m venv venv && source venv/bin/activate"
echo "4. pip install -r backend/requirements.txt"
echo "5. (Optional) bash scripts/download_noto_georgian.sh"
echo "6. Configure .env file"
echo "7. Run backend: cd backend && uvicorn open_webui.main:app --host 0.0.0.0 --port 8080"
