$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvActivate = Join-Path $scriptDir ".venv\Scripts\Activate.ps1"
$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"

if (-not (Test-Path $venvActivate)) {
    Write-Host "Creating backend virtual environment (.venv)..." -ForegroundColor Yellow
    py -3.11 -m venv .venv
}

. $venvActivate

if (-not (Test-Path $venvPython)) {
    throw "Venv python not found at $venvPython"
}

if (-not $env:PORT) {
    $env:PORT = "8080"
}

# Ensure Socket.IO uses true WebSocket transport (not polling fallback)
$env:ENABLE_WEBSOCKET_SUPPORT = "True"

$env:CORS_ALLOW_ORIGIN = "http://localhost:5173;http://127.0.0.1:5173;http://localhost:5174;http://127.0.0.1:5174;http://localhost:8080;http://127.0.0.1:8080"

Write-Host "Using Python: $(& $venvPython -c 'import sys; print(sys.executable)')" -ForegroundColor Green
$uvicornArgs = @(
    "-m",
    "uvicorn",
    "open_webui.main:app",
    "--port",
    $env:PORT,
    "--host",
    "0.0.0.0",
    "--reload"
)

& $venvPython @uvicornArgs
