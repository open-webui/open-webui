# Get the directory of the script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$KeyFile = ".webui_secret_key"

# Default port
$Port = if ($env:PORT) { $env:PORT } else { 8080 }

if (-not ($env:WEBUI_SECRET_KEY -and $env:WEBUI_JWT_SECRET_KEY)) {
    Write-Host "No WEBUI_SECRET_KEY provided"

    if (-not (Test-Path $KeyFile)) {
        Write-Host "Generating WEBUI_SECRET_KEY"
        # Generate a random value to use as a WEBUI_SECRET_KEY in case the user didn't provide one.
        $Key = [Convert]::ToBase64String((Get-Random -Count 9 -InputObject (0..255)))
        $Key | Out-File $KeyFile -Encoding ASCII
    }

    Write-Host "Loading WEBUI_SECRET_KEY from $KeyFile"
    $env:WEBUI_SECRET_KEY = Get-Content $KeyFile -Raw
}

$env:WEBUI_SECRET_KEY = $env:WEBUI_SECRET_KEY
Start-Process -NoNewWindow "uvicorn" "main:app --host 0.0.0.0 --port $Port --forwarded-allow-ips '*'" 