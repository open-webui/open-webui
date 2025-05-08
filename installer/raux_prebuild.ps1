param(
    [Parameter(Mandatory=$false)][switch]$solution_version,
    [Parameter(Mandatory=$false)][switch]$build,
    [Parameter(Mandatory=$false)][switch]$package
)
# raux_prebuild.ps1
# This script provides three main methods for CI/CD automation:
# 1. GetVersion --solution-version
# 2. BuildSolution --build
# 3. PackageSolution --package
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

function BuildSolution {
    Write-Host "[BuildSolution] Invoked"
    # TODO: Implement logic to generate bin folder and return its location
}

function PackageSolution {
    Write-Host "[PackageSolution] Invoked"
    # TODO: Implement logic to package the build artifacts
}

# Main script logic: parse arguments and dispatch to the correct function
if ($solution_version) {
    GetVersion
} elseif ($build) {
    BuildSolution
} elseif ($package) {
    PackageSolution
} else {
    Write-Host "No valid parameter provided. Use --solution-version, --build, or --package."
}
