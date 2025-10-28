# Activate virtual environment (in backend directory)
$venvPath = Join-Path $PSScriptRoot ".venv" "Scripts" "Activate.ps1"

if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & $venvPath
} else {
    Write-Host "WARNING: Virtual environment not found at $venvPath" -ForegroundColor Yellow
    Write-Host "Please run 'uv sync' from the backend directory first!" -ForegroundColor Yellow
    exit 1
}

# Set CORS allow origin for development
$env:CORS_ALLOW_ORIGIN = "http://localhost:5173;http://localhost:8080"

# Set default port if not already set
if (-not $env:PORT) {
    $env:PORT = "8080"
}

# Start uvicorn server with hot reload
Write-Host "Starting Open WebUI backend on port $env:PORT..." -ForegroundColor Cyan
uvicorn open_webui.main:app --port $env:PORT --host 0.0.0.0 --forwarded-allow-ips "'*'" --reload

