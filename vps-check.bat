@echo off
REM VPS Pre-deployment Check Script (Windows)
REM Run this before deploying to VPS to catch issues early

setlocal enabledelayedexpansion

echo 🔍 Starting Open WebUI deployment pre-check...

REM Check Node.js
echo.
echo 📦 Checking Node.js...
where node >nul 2>nul
if errorlevel 1 (
    echo ❌ Node.js not found. Install Node.js ^>= 18.13.0
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
echo ✅ Node.js version: %NODE_VERSION%

REM Check npm
echo.
echo 📦 Checking npm...
where npm >nul 2>nul
if errorlevel 1 (
    echo ❌ npm not found.
    exit /b 1
)
for /f "tokens=*" %%i in ('npm -v') do set NPM_VERSION=%%i
echo ✅ npm version: %NPM_VERSION%

REM Check Python
echo.
echo 🐍 Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python not found. Install Python ^>= 3.11
    exit /b 1
)
for /f "tokens=*" %%i in ('python -V') do set PYTHON_VERSION=%%i
echo ✅ %PYTHON_VERSION%

REM Check Git
echo.
echo 📚 Checking Git...
where git >nul 2>nul
if errorlevel 1 (
    echo ❌ Git not found.
    exit /b 1
)
for /f "tokens=*" %%i in ('git --version') do set GIT_VERSION=%%i
echo ✅ %GIT_VERSION%

REM Check if in project root
echo.
echo 📂 Checking project structure...
if not exist "package.json" (
    echo ❌ package.json not found. Run from project root.
    exit /b 1
)
if not exist "backend" (
    echo ❌ backend\ directory not found.
    exit /b 1
)
echo ✅ Project structure OK

REM Check Georgian font
echo.
echo 🔤 Checking Georgian font...
if exist "scripts\fonts\NotoSansGeorgian-Bold.ttf" (
    echo ✅ NotoSansGeorgian-Bold.ttf found
) else (
    echo ⚠️  Georgian font not found. Run: bash scripts/download_noto_georgian.sh
)

REM Check Python requirements
echo.
echo 🐍 Checking Python requirements...
if not exist "backend\requirements.txt" (
    echo ❌ backend\requirements.txt not found.
    exit /b 1
)
echo ✅ backend\requirements.txt found

echo.
echo 🎉 All pre-checks passed! Ready for deployment.
echo.
echo Next steps:
echo 1. npm ci
echo 2. npm run build
echo 3. python -m venv venv ^&^& venv\Scripts\activate
echo 4. pip install -r backend\requirements.txt
echo 5. (Optional) bash scripts/download_noto_georgian.sh
echo 6. Configure .env file
echo 7. Run backend: cd backend ^&^& uvicorn open_webui.main:app --host 0.0.0.0 --port 8080

endlocal
