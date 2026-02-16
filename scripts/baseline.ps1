param(
    [string]$OutputPath = "artifacts/baselines/baseline-$((Get-Date).ToString('yyyyMMdd')).json",
    [string]$Environment = "local-windows",
    [string]$StartupCommand = "",
    [string]$TestCommand = "npm run -s test:frontend",
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'

function Get-GitCommitHash {
    try {
        return (git rev-parse HEAD).Trim()
    }
    catch {
        return "unknown"
    }
}

function Get-CpuPercent {
    try {
        $sample = Get-Counter '\Processor(_Total)\% Processor Time'
        return [Math]::Round($sample.CounterSamples[0].CookedValue, 2)
    }
    catch {
        return $null
    }
}

function Get-RamUsedMB {
    try {
        $os = Get-CimInstance Win32_OperatingSystem
        $totalKB = [double]$os.TotalVisibleMemorySize
        $freeKB = [double]$os.FreePhysicalMemory
        $usedMB = ($totalKB - $freeKB) / 1024
        return [Math]::Round($usedMB, 2)
    }
    catch {
        return $null
    }
}

function Measure-StartupMs {
    param(
        [string]$Command
    )

    if ([string]::IsNullOrWhiteSpace($Command)) {
        return $null
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        Invoke-Expression $Command | Out-Null
        $sw.Stop()
        return [Math]::Round($sw.Elapsed.TotalMilliseconds, 2)
    }
    catch {
        $sw.Stop()
        return $null
    }
}

function Get-TestPassRate {
    param(
        [string]$Command,
        [bool]$ShouldSkip
    )

    if ($ShouldSkip -or [string]::IsNullOrWhiteSpace($Command)) {
        return $null
    }

    try {
        Invoke-Expression $Command | Out-Null
        return 100
    }
    catch {
        return 0
    }
}

$commitHash = Get-GitCommitHash
$timestampUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

$startupTimeMs = Measure-StartupMs -Command $StartupCommand
$cpuPercent = Get-CpuPercent
$ramMB = Get-RamUsedMB
$testPassRate = Get-TestPassRate -Command $TestCommand -ShouldSkip $SkipTests.IsPresent

$result = [ordered]@{
    commit_hash = $commitHash
    timestamp_utc = $timestampUtc
    environment = $Environment
    metrics = [ordered]@{
        startup_time_ms = $startupTimeMs
        ram_mb = $ramMB
        cpu_percent = $cpuPercent
        test_pass_rate_percent = $testPassRate
    }
}

$targetDir = Split-Path $OutputPath -Parent
if (-not [string]::IsNullOrWhiteSpace($targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$result | ConvertTo-Json -Depth 5 | Set-Content -Path $OutputPath -Encoding UTF8
Write-Output "BASELINE_WRITTEN=$OutputPath"
