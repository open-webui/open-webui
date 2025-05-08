param(
    [Parameter(Mandatory=$false)][switch]$solution_version,
    [Parameter(Mandatory=$false)][switch]$build_frontend,
    [Parameter(Mandatory=$false)][switch]$build_backend,
    [Parameter(Mandatory=$false)][switch]$package
)
# raux_prebuild.ps1
# This script provides methods for CI/CD automation:
# 1. GetVersion --solution-version
# 2. BuildFrontend --build-frontend
# 3. BuildBackend --build-backend
# 4. PackageSolution --package
# Each method prints its name and the received parameter.

function GetVersion {
    Write-Host "[GetVersion] Invoked"
    $packageJsonPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'package.json'
    if (-Not (Test-Path $packageJsonPath)) {
        Write-Host "ERROR: package.json not found at $packageJsonPath"
        exit 1
    }
    $packageJson = Get-Content $packageJsonPath -Raw | ConvertFrom-Json
    $version = $packageJson.version
    Write-Host "Version: $version"
    # For GitHub Actions, output to GITHUB_OUTPUT if set
    if ($env:GITHUB_OUTPUT) {
        "version=$version" | Out-File -FilePath $env:GITHUB_OUTPUT -Encoding utf8 -Append
    }
    return $version
}

function BuildFrontend {
    Write-Host "[BuildFrontend] Invoked"
    $ErrorActionPreference = 'Stop'
    try {
        Push-Location "$PSScriptRoot\.."  # Go to repo root
        npm ci
        npm run build
        Pop-Location
    } catch {
        Write-Host "ERROR: Frontend build failed: $_"
        exit 1
    }
}

function BuildBackend {
    Write-Host "[BuildBackend] Invoked"
    $ErrorActionPreference = 'Stop'
    try {
        Push-Location "$PSScriptRoot\..\backend"
        pip install -r requirements.txt
        Pop-Location
    } catch {
        Write-Host "ERROR: Backend dependency installation failed: $_"
        exit 1
    }
}

function PackageSolution {
    Write-Host "[PackageSolution] Invoked"
    # TODO: Implement logic to package the build artifacts
}

# Main script logic: parse arguments and dispatch to the correct function
if ($solution_version) {
    GetVersion
} elseif ($build_frontend) {
    BuildFrontend
} elseif ($build_backend) {
    BuildBackend
} elseif ($package) {
    PackageSolution
} else {
    Write-Host "No valid parameter provided. Use --solution-version, --build-frontend, --build-backend, or --package."
}
