# PowerShell script to launch RAUX and Lemonade
# This script activates the conda environments, runs both servers,
# waits for them to be ready, and opens the browser

# Clear the screen and set title
Clear-Host
$host.UI.RawUI.WindowTitle = "RAUX & Lemonade Servers"

Write-Host "=================================================" -ForegroundColor Blue
Write-Host " RAUX & Lemonade Servers - AI Web Interface" -ForegroundColor Blue
Write-Host " This window will minimize when the servers are ready" -ForegroundColor Blue
Write-Host "=================================================" -ForegroundColor Blue

# Set version with default value
$version = " $($env:RAUX_VERSION)"

# Parameters
$condaEnvPath = $env:RAUX_CONDA_ENV
$lemonadeEnvPath = $env:LEMONADE_CONDA_ENV
$rauxUrl = "http://localhost:8080"
$lemonadeUrl = "http://localhost:8000"
$maxAttempts = 60  # Increased maximum attempts
$waitTimeSeconds = 2  # Increased wait time between attempts

# Set up proper handling for Ctrl+C
$exitRequested = $false

# Store the original setting
$originalTreatControlCAsInput = [Console]::TreatControlCAsInput

# Change the setting to capture Ctrl+C
[Console]::TreatControlCAsInput = $true

# Function to check if a server is running
function Test-ServerReady {
    param (
        [string]$Url,
        [string]$ServerName = "Server"
    )
    
    try {
        # Special handling for Lemonade health check
        if ($ServerName -eq "Lemonade") {
            try {
                $healthUrl = "http://localhost:8000/api/v0/health"
                $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
                
                # Check if we got a response
                if ($response.Content) {
                    try {
                        # Try to parse the JSON
                        $jsonResponse = $response.Content | ConvertFrom-Json
                        
                        # Check if status is "ok"
                        if ($jsonResponse.status -eq "ok") {
                            Write-Host "  Lemonade health check passed - status is 'ok'" -ForegroundColor DarkGray
                            return $true
                        } else {
                            Write-Host "  Lemonade health check failed - status is not 'ok'" -ForegroundColor DarkGray
                            return $false
                        }
                    }
                    catch {
                        Write-Host "  Failed to parse JSON response - $($_.Exception.Message)" -ForegroundColor DarkGray
                        return $false
                    }
                }
            }
            catch {
                Write-Host "  Failed to connect to Lemonade health endpoint - $($_.Exception.Message)" -ForegroundColor DarkGray
                return $false
            }
        }
        else {
            # Regular server check for RAUX
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            return $response.StatusCode -eq 200
        }
    }
    catch {
        Write-Host "  Error checking $ServerName - $($_.Exception.Message)" -ForegroundColor DarkGray
        return $false
    }
    
    return $false
}

# Function to stop a process and all its child processes
function Stop-ProcessTree {
    param (
        [int]$ProcessId,
        [string]$ProcessName = "Process"
    )
    
    Write-Host "Stopping $ProcessName tree for PID - $ProcessId" -ForegroundColor Yellow
    
    try {
        # Get all child processes
        $childProcesses = Get-CimInstance Win32_Process | 
            Where-Object { $_.ParentProcessId -eq $ProcessId }
        
        # Recursively stop each child process
        foreach ($childProcess in $childProcesses) {
            Stop-ProcessTree -ProcessId $childProcess.ProcessId -ProcessName "$ProcessName child"
        }
        
        # Stop the parent process
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  Stopping $ProcessName - $($process.Name) (ID - $ProcessId)" -ForegroundColor Yellow
            Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Host "  Error stopping $ProcessName tree - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Function to launch and test Lemonade server
function Start-LemonadeServer {
    # Verify Lemonade environment exists
    if (-not (Test-Path $lemonadeEnvPath)) {
        Write-Host "ERROR: Lemonade conda environment not found at $lemonadeEnvPath" -ForegroundColor Red
        return $null
    }

    Write-Host "Starting Lemonade server..." -ForegroundColor Cyan
    $lemonadePinfo = New-Object System.Diagnostics.ProcessStartInfo
    $lemonadePinfo.FileName = "cmd.exe"
    $lemonadePinfo.Arguments = "/C call conda activate $lemonadeEnvPath && lemonade serve"
    $lemonadePinfo.RedirectStandardError = $false
    $lemonadePinfo.RedirectStandardOutput = $false
    $lemonadePinfo.UseShellExecute = $true
    $lemonadePinfo.CreateNoWindow = $false

    $lemonadeProcess = New-Object System.Diagnostics.Process
    $lemonadeProcess.StartInfo = $lemonadePinfo
    $lemonadeProcess.Start() | Out-Null
    $lemonadeProcessId = $lemonadeProcess.Id
    Write-Host "Lemonade server process started with PID: $lemonadeProcessId" -ForegroundColor Cyan

    # Wait for Lemonade to be ready
    $attempt = 0
    $lemonadeReady = $false

    Write-Host "Waiting for Lemonade server to be ready..." -ForegroundColor Yellow

    # Give the server some initial time to start up before checking
    Write-Host "Giving the Lemonade server some time to start up..." -ForegroundColor Cyan
    Start-Sleep -Seconds 10

    while (-not $lemonadeReady -and $attempt -lt $maxAttempts -and -not $exitRequested) {
        $attempt++
        Write-Host "Checking if Lemonade server is ready (attempt $attempt of $maxAttempts)..." -ForegroundColor Yellow
        
        if (Test-ServerReady -Url $lemonadeUrl -ServerName "Lemonade") {
            $lemonadeReady = $true
            Write-Host "Lemonade server is ready!" -ForegroundColor Green
        }
        else {
            Write-Host "Lemonade server not ready yet. Waiting $waitTimeSeconds seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds $waitTimeSeconds
        }
    }

    # If Lemonade server is still not ready after all attempts, try one more time with a longer timeout
    if (-not $lemonadeReady -and -not $exitRequested) {
        Write-Host "Lemonade server did not respond in expected time. Trying one more time with longer timeout..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        if (Test-ServerReady -Url $lemonadeUrl -ServerName "Lemonade") {
            $lemonadeReady = $true
            Write-Host "Lemonade server is finally ready!" -ForegroundColor Green
        }
    }

    if (-not $lemonadeReady) {
        Write-Host "WARNING: Lemonade server did not start properly. RAUX may not function correctly." -ForegroundColor Red
        if (-not $exitRequested) {
            Write-Host "Would you like to continue anyway? (Y/N)" -ForegroundColor Yellow
            $response = Read-Host
            if ($response -ne "Y") {
                Write-Host "Aborting startup..." -ForegroundColor Red
                $exitRequested = $true
                exit
            }
        }
    }

    return $lemonadeProcessId
}

# Function to launch and test RAUX server
function Start-RAUXServer {
    # Verify RAUX environment exists
    if (-not (Test-Path $condaEnvPath)) {
        Write-Host "ERROR: RAUX conda environment not found at $condaEnvPath" -ForegroundColor Red
        Write-Host "Please ensure RAUX is properly installed." -ForegroundColor Red
        exit 1
    }

    Write-Host "Starting RAUX$version server..." -ForegroundColor Cyan
    $rauxPinfo = New-Object System.Diagnostics.ProcessStartInfo
    $rauxPinfo.FileName = "cmd.exe"
    $rauxPinfo.Arguments = "/C call conda activate $condaEnvPath && open-webui serve"
    $rauxPinfo.RedirectStandardError = $false
    $rauxPinfo.RedirectStandardOutput = $false
    $rauxPinfo.UseShellExecute = $true
    $rauxPinfo.CreateNoWindow = $false

    # Store the current time before starting the process
    $startTime = Get-Date

    $rauxProcess = New-Object System.Diagnostics.Process
    $rauxProcess.StartInfo = $rauxPinfo
    $rauxProcess.Start() | Out-Null
    $rauxProcessId = $rauxProcess.Id
    Write-Host "RAUX server process started with PID: $rauxProcessId" -ForegroundColor Cyan

    # Store potential server-related processes that started after we launched
    $pythonProcesses = Get-ProcessesStartedAfter -StartTime $startTime -NamePattern "*python*"
    $cmdProcesses = Get-ProcessesStartedAfter -StartTime $startTime -NamePattern "*cmd*"
    $nodeProcesses = Get-ProcessesStartedAfter -StartTime $startTime -NamePattern "*node*"

    Write-Host "Detected potential server processes:" -ForegroundColor DarkGray
    $pythonProcesses | ForEach-Object { Write-Host "  Python process: $($_.Name) (ID: $($_.Id))" -ForegroundColor DarkGray }
    $cmdProcesses | ForEach-Object { Write-Host "  CMD process: $($_.Name) (ID: $($_.Id))" -ForegroundColor DarkGray }
    $nodeProcesses | ForEach-Object { Write-Host "  Node process: $($_.Name) (ID: $($_.Id))" -ForegroundColor DarkGray }

    Write-Host "RAUX server process started. Waiting for server to be ready..." -ForegroundColor Cyan
    Write-Host "This may take a minute or two..." -ForegroundColor Yellow

    # Wait for the RAUX server to be ready
    $attempt = 0
    $rauxReady = $false

    # Give the server some initial time to start up before checking
    Write-Host "Giving the RAUX server some time to start up..." -ForegroundColor Cyan
    Start-Sleep -Seconds 10

    while (-not $rauxReady -and $attempt -lt $maxAttempts -and -not $exitRequested) {
        $attempt++
        Write-Host "Checking if RAUX server is ready (attempt $attempt of $maxAttempts)..." -ForegroundColor Yellow
        
        if (Test-ServerReady -Url $rauxUrl -ServerName "RAUX") {
            $rauxReady = $true
            Write-Host "RAUX server is ready!" -ForegroundColor Green
        }
        else {
            Write-Host "RAUX server not ready yet. Waiting $waitTimeSeconds seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds $waitTimeSeconds
        }
    }

    # If RAUX server is still not ready after all attempts, try one more time with a longer timeout
    if (-not $rauxReady -and -not $exitRequested) {
        Write-Host "RAUX server did not respond in expected time. Trying one more time with longer timeout..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        try {
            $response = Invoke-WebRequest -Uri $rauxUrl -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $rauxReady = $true
                Write-Host "RAUX server is finally ready!" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "Final check failed: $($_.Exception.Message)" -ForegroundColor DarkGray
        }
    }

    if ($rauxReady -and -not $exitRequested) {
        Write-Host "Opening browser to $rauxUrl" -ForegroundColor Green
        Write-Host "RAUX server is now running. You can minimize this window." -ForegroundColor Green
        Write-Host "Do not close this window or the server will stop." -ForegroundColor Yellow
        Start-Process $rauxUrl
        
        # Minimize window if possible
        $code = @'
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
'@
        
        try {
            Add-Type -TypeDefinition $code -ErrorAction SilentlyContinue
            $currentWindow = (Get-Process -Id $pid).MainWindowHandle
            # Minimize window (SW_MINIMIZE = 6)
            [Win32]::ShowWindow($currentWindow, 6) | Out-Null
        }
        catch {
            Write-Host "Could not minimize window: $($_.Exception.Message)" -ForegroundColor DarkGray
        }
    }
    elseif (-not $exitRequested) {
        Write-Host "RAUX server did not start in the expected time. You can try accessing $rauxUrl manually." -ForegroundColor Red
        Write-Host "Do not close this window or the server will stop." -ForegroundColor Yellow
        # Still try to open the browser as a last attempt
        Start-Process $rauxUrl
    }

    return $rauxProcessId
}

# Function to find processes started after a specific time
function Get-ProcessesStartedAfter {
    param (
        [DateTime]$StartTime,
        [string]$NamePattern
    )
    
    Get-Process | Where-Object { 
        $_.StartTime -gt $StartTime -and 
        $_.Name -like $NamePattern 
    }
}

# Launch servers based on parameters
$lemonadeProcessId = $null
$rauxProcessId = $null

if ($env:LAUNCH_LEMONADE -eq "true" -or $env:LAUNCH_LEMONADE -eq "TRUE") {
    $lemonadeProcessId = Start-LemonadeServer
}

$rauxProcessId = Start-RAUXServer

# Keep the window running and monitor both servers
Write-Host "`nPress Ctrl+C to stop the servers..." -ForegroundColor Cyan

try {
    # Loop until exit is requested
    while (-not $exitRequested) {
        # Check for Ctrl+C key press
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            # Check if Ctrl+C was pressed (Ctrl+C has a character value of 3)
            if ($key.Key -eq 'C' -and $key.Modifiers -eq 'Control') {
                Write-Host "`nCtrl+C detected. Initiating shutdown..." -ForegroundColor Yellow
                $exitRequested = $true
            }
        }
        
        # Monitor servers
        if ($lemonadeProcessId -and -not (Test-ServerReady -Url $lemonadeUrl -ServerName "Lemonade")) {
            Write-Host "WARNING - Lemonade server appears to be down!" -ForegroundColor Red
        }
        if (-not (Test-ServerReady -Url $rauxUrl -ServerName "RAUX")) {
            Write-Host "WARNING - RAUX server appears to be down!" -ForegroundColor Red
        }
        
        Start-Sleep -Seconds 5  # Check server status every 5 seconds
    }
}
finally {
    # Restore the original setting
    [Console]::TreatControlCAsInput = $originalTreatControlCAsInput
    
    # This will execute when Ctrl+C is pressed or when the script exits
    Write-Host "Stopping servers..." -ForegroundColor Red
    
    # Try to stop both server process trees
    if ($lemonadeProcessId) {
        Stop-ProcessTree -ProcessId $lemonadeProcessId -ProcessName "Lemonade"
    }
    if ($rauxProcessId) {
        Stop-ProcessTree -ProcessId $rauxProcessId -ProcessName "RAUX"
    }
    
    # Find and kill any remaining open-webui or lemonade processes
    Write-Host "Checking for any remaining server processes..." -ForegroundColor Yellow
    $webUiProcesses = Get-Process | Where-Object { $_.Name -like "*python*" } -ErrorAction SilentlyContinue
    
    foreach ($proc in $webUiProcesses) {
        try {
            # Get the command line for this process
            $wmiQuery = "SELECT CommandLine FROM Win32_Process WHERE ProcessId = '$($proc.Id)'"
            $commandLine = (Get-WmiObject -Query $wmiQuery -ErrorAction SilentlyContinue).CommandLine
            
            # If the command line contains open-webui or lemonade, stop the process
            if ($commandLine -and ($commandLine -like "*open-webui serve*" -or $commandLine -like "*lemonade serve*")) {
                Write-Host "  Stopping process - $($proc.Id)" -ForegroundColor Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
        catch {
            # Continue even if there's an error
        }
    }
    
    Write-Host "Server shutdown complete." -ForegroundColor Green
    Write-Host "Press any key to exit..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
} 