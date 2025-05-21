# Step 1: Copy raux.env to build/.env
Write-Host "Copying raux.env to build/.env..."
$envSource = Join-Path $PSScriptRoot 'raux-hybrid.env'
$envDest = Join-Path $PSScriptRoot 'build/.env'
Copy-Item -Path $envSource -Destination $envDest -Force

# Step 2: Change directory to raux-electron
$electronDir = Join-Path $PSScriptRoot 'raux-electron'
Set-Location $electronDir

# Step 3: Read version from ../package.json
$packageJsonPath = Join-Path $PSScriptRoot 'package.json'
$packageJson = Get-Content $packageJsonPath | Out-String | ConvertFrom-Json
$version = $packageJson.version
Write-Host "Detected RAUX version: $version"

# Step 4: Set RAUX_PROD_VERSION and run npm run make
$env:RAUX_PROD_VERSION = $version
Write-Host "Running 'npm run make' with RAUX_PROD_VERSION=$version..."

npm run make
$exitCode = $LASTEXITCODE

# Step 5: Exit with the same code as npm run make
exit $exitCode 