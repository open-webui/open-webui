# PowerShell script to launch RAUX
# This script activates the conda environment, runs the server,
# waits for it to be ready, and opens the browser

# Clear the screen and set title
Clear-Host
$host.UI.RawUI.WindowTitle = "RAUX Server"

Write-Host "=================================================" -ForegroundColor Blue
Write-Host " RAUX Server - AI Web Interface" -ForegroundColor Blue
Write-Host " This window will minimize when the server is ready" -ForegroundColor Blue
Write-Host "=================================================" -ForegroundColor Blue

# Parameters
$condaEnvName = "raux_env"
$condaEnvPath = "$env:LOCALAPPDATA\RAUX\raux_env"
$serverUrl = "http://localhost:8080"
$maxAttempts = 60  # Increased maximum attempts
$waitTimeSeconds = 2  # Increased wait time between attempts

# Set up proper handling for Ctrl+C
$exitRequested = $false

# Store the original setting
$originalTreatControlCAsInput = [Console]::TreatControlCAsInput

# Change the setting to capture Ctrl+C
[Console]::TreatControlCAsInput = $true

Write-Host "Starting RAUX server..." -ForegroundColor Cyan

# Function to check if the server is running
function Test-ServerReady {
    param (
        [string]$Url
    )
    
    try {
        Write-Host "  Trying to connect to $Url..." -ForegroundColor DarkGray
        
        # Try multiple methods to check if server is ready
        # Method 1: Using Invoke-WebRequest
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            Write-Host "  Method 1: Server responded with status code: $($response.StatusCode)" -ForegroundColor DarkGray
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
            Write-Host "  Method 1 failed: $($_.Exception.Message)" -ForegroundColor DarkGray
        }
        
        # Method 2: Using System.Net.WebClient
        try {
            $webClient = New-Object System.Net.WebClient
            $content = $webClient.DownloadString($Url)
            Write-Host "  Method 2: Successfully downloaded content from server" -ForegroundColor DarkGray
            return $true
        }
        catch {
            Write-Host "  Method 2 failed: $($_.Exception.Message)" -ForegroundColor DarkGray
        }
        
        # Method 3: Using System.Net.Sockets.TcpClient to check if port is open
        try {
            $uri = [System.Uri]$Url
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $portOpen = $tcpClient.ConnectAsync($uri.Host, $uri.Port).Wait(3000)
            $tcpClient.Close()
            Write-Host "  Method 3: Port check result: $portOpen" -ForegroundColor DarkGray
            if ($portOpen) {
                return $true
            }
        }
        catch {
            Write-Host "  Method 3 failed: $($_.Exception.Message)" -ForegroundColor DarkGray
        }
        
        return $false
    }
    catch {
        Write-Host "  Error in Test-ServerReady: $($_.Exception.Message)" -ForegroundColor DarkGray
        return $false
    }
}

# Function to stop a process and all its child processes
function Stop-ProcessTree {
    param (
        [int]$ProcessId
    )
    
    Write-Host "Stopping process tree for PID: $ProcessId" -ForegroundColor Yellow
    
    try {
        # Get all child processes
        $childProcesses = Get-CimInstance Win32_Process | 
            Where-Object { $_.ParentProcessId -eq $ProcessId }
        
        # Recursively stop each child process
        foreach ($childProcess in $childProcesses) {
            Stop-ProcessTree -ProcessId $childProcess.ProcessId
        }
        
        # Stop the parent process
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  Stopping process: $($process.Name) (ID: $ProcessId)" -ForegroundColor Yellow
            Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Host "  Error stopping process tree: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Create a process to run the server
$pinfo = New-Object System.Diagnostics.ProcessStartInfo
$pinfo.FileName = "cmd.exe"
$pinfo.Arguments = "/C call conda activate $condaEnvPath && open-webui serve"
$pinfo.RedirectStandardError = $false
$pinfo.RedirectStandardOutput = $false
$pinfo.UseShellExecute = $true
$pinfo.CreateNoWindow = $false  # Show the window

# Store the current time before starting the process
$startTime = Get-Date

$serverProcess = New-Object System.Diagnostics.Process
$serverProcess.StartInfo = $pinfo
$serverProcess.Start() | Out-Null
$serverProcessId = $serverProcess.Id
Write-Host "Server process started with PID: $serverProcessId" -ForegroundColor Cyan

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

# Store potential server-related processes that started after we launched
$pythonProcesses = Get-ProcessesStartedAfter -StartTime $startTime -NamePattern "*python*"
$cmdProcesses = Get-ProcessesStartedAfter -StartTime $startTime -NamePattern "*cmd*"
$nodeProcesses = Get-ProcessesStartedAfter -StartTime $startTime -NamePattern "*node*"

Write-Host "Detected potential server processes:" -ForegroundColor DarkGray
$pythonProcesses | ForEach-Object { Write-Host "  Python process: $($_.Name) (ID: $($_.Id))" -ForegroundColor DarkGray }
$cmdProcesses | ForEach-Object { Write-Host "  CMD process: $($_.Name) (ID: $($_.Id))" -ForegroundColor DarkGray }
$nodeProcesses | ForEach-Object { Write-Host "  Node process: $($_.Name) (ID: $($_.Id))" -ForegroundColor DarkGray }

Write-Host "Server process started. Waiting for server to be ready..." -ForegroundColor Cyan
Write-Host "This may take a minute or two..." -ForegroundColor Yellow

# Wait for the server to be ready
$attempt = 0
$serverReady = $false

# Give the server some initial time to start up before checking
Write-Host "Giving the server some time to start up..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

while (-not $serverReady -and $attempt -lt $maxAttempts -and -not $exitRequested) {
    $attempt++
    Write-Host "Checking if server is ready (attempt $attempt of $maxAttempts)..." -ForegroundColor Yellow
    
    if (Test-ServerReady -Url $serverUrl) {
        $serverReady = $true
        Write-Host "Server is ready!" -ForegroundColor Green
    }
    else {
        Write-Host "Server not ready yet. Waiting $waitTimeSeconds seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds $waitTimeSeconds
    }
}

# If server is still not ready after all attempts, try one more time with a longer timeout
if (-not $serverReady -and -not $exitRequested) {
    Write-Host "Server did not respond in expected time. Trying one more time with longer timeout..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    try {
        $response = Invoke-WebRequest -Uri $serverUrl -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $serverReady = $true
            Write-Host "Server is finally ready!" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "Final check failed: $($_.Exception.Message)" -ForegroundColor DarkGray
    }
}

if ($serverReady -and -not $exitRequested) {
    Write-Host "Opening browser to $serverUrl" -ForegroundColor Green
    Write-Host "RAUX server is now running. You can minimize this window." -ForegroundColor Green
    Write-Host "Do not close this window or the server will stop." -ForegroundColor Yellow
    Start-Process $serverUrl
    
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
    Write-Host "Server did not start in the expected time. You can try accessing $serverUrl manually." -ForegroundColor Red
    Write-Host "Do not close this window or the server will stop." -ForegroundColor Yellow
    # Still try to open the browser as a last attempt
    Start-Process $serverUrl
}

# Keep the window running
Write-Host "`nPress Ctrl+C to stop the server..." -ForegroundColor Cyan

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
        
        Start-Sleep -Milliseconds 100
    }
}
finally {
    # Restore the original setting
    [Console]::TreatControlCAsInput = $originalTreatControlCAsInput
    
    # This will execute when Ctrl+C is pressed or when the script exits
    Write-Host "Stopping RAUX server..." -ForegroundColor Red
    
    # Try to stop the server process tree
    if ($serverProcessId) {
        Stop-ProcessTree -ProcessId $serverProcessId
    }
    
    # Find and kill any remaining open-webui processes
    Write-Host "Checking for any remaining open-webui processes..." -ForegroundColor Yellow
    $webUiProcesses = Get-Process | Where-Object { $_.Name -like "*python*" } -ErrorAction SilentlyContinue
    
    foreach ($proc in $webUiProcesses) {
        try {
            # Get the command line for this process
            $wmiQuery = "SELECT CommandLine FROM Win32_Process WHERE ProcessId = '$($proc.Id)'"
            $commandLine = (Get-WmiObject -Query $wmiQuery -ErrorAction SilentlyContinue).CommandLine
            
            # If the command line contains open-webui, stop the process
            if ($commandLine -and $commandLine -like "*open-webui serve*") {
                Write-Host "  Stopping open-webui process: $($proc.Id)" -ForegroundColor Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
        catch {
            # Continue even if there's an error
        }
    }
    
    Write-Host "Server shutdown complete." -ForegroundColor Green
    Write-Host "Press any key to exit..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} 