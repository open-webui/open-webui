$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendScript = Join-Path $root "backend\dev.ps1"

if (-not (Test-Path $backendScript)) {
    throw "Backend launcher not found: $backendScript"
}

$backendCmd = "Set-Location '$root\backend'; powershell -ExecutionPolicy Bypass -File '.\dev.ps1'"
$frontendCmd = "Set-Location '$root'; npm run dev"

Start-Process powershell -ArgumentList @('-NoExit', '-Command', $backendCmd) -WindowStyle Normal
Start-Sleep -Milliseconds 600
Start-Process powershell -ArgumentList @('-NoExit', '-Command', $frontendCmd) -WindowStyle Normal

Write-Host "Started backend and frontend in separate terminals." -ForegroundColor Green
Write-Host "Backend terminal: backend\dev.ps1 (http://localhost:8080)"
Write-Host "Frontend terminal: npm run dev (usually http://localhost:5173 or 5174)"
