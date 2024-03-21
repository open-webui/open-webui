# Define color and formatting codes
$BOLD = [char]::ConvertFromUtf32(0x1b) + '[1m'
$GREEN = [char]::ConvertFromUtf32(0x1b) + '[1;32m'
$WHITE = [char]::ConvertFromUtf32(0x1b) + '[1;37m'
$RED = [char]::ConvertFromUtf32(0x1b) + '[0;31m'
$NC = [char]::ConvertFromUtf32(0x1b) + '[0m' # No Color
# Unicode character for tick mark
$TICK = [char]::ConvertFromUtf32(0x2713)

# Detect GPU driver
function Get-GpuDriver {
    # Detect NVIDIA GPUs using lspci or nvidia-smi
    if ((lspci | Select-String -Pattern 'nvidia' -Quiet) -or (nvidia-smi 2>&1 | Select-String -Pattern 'NVIDIA' -Quiet)) {
        return "nvidia"
    }
    
    # Detect AMD GPUs
    if (lspci | Select-String -Pattern 'amd' -Quiet) {
        # List of known GCN and later architecture cards
        # This is a simplified list, and in a real-world scenario, you'd want a more comprehensive one
        $gcn_and_later = @("Radeon HD 7000", "Radeon HD 8000", "Radeon R5", "Radeon R7", "Radeon R9", "Radeon RX")

        # Get GPU information
        $gpu_info = lspci | Select-String -Pattern 'vga.*amd'

        foreach ($model in $gcn_and_later) {
            if ($gpu_info -match $model) {
                return "amdgpu"
            }
        }

        # Default to radeon if no GCN or later architecture is detected
        return "radeon"
    }

    # Detect Intel GPUs
    if (lspci | Select-String -Pattern 'intel' -Quiet) {
        return "i915"
    }

    # If no known GPU is detected
    Write-Host "Unknown or unsupported GPU driver" -ForegroundColor Red
    exit 1
}

# Function for rolling animation
function Show-Loading {
    $spin = "-\|/"
    $i = 0

    Write-Host " " -NoNewline

    while ($PID -eq $PID) {
        $i = ($i + 1) % 4
        Write-Host "$spin[$i]" -NoNewline
        Start-Sleep -Milliseconds 100
    }

    # Replace the spinner with a tick
    Write-Host "$GREEN$TICK$NC" -NoNewline
}

# Usage information
function Usage {
    Write-Host "Usage: $script:MyInvocation.MyCommand [OPTIONS]"
    Write-Host "Options:"
    Write-Host "  --enable-gpu[count=COUNT]  Enable GPU support with the specified count."
    Write-Host "  --enable-api[port=PORT]    Enable API and expose it on the specified port."
    Write-Host "  --webui[port=PORT]         Set the port for the web user interface."
    Write-Host "  --data[folder=PATH]        Bind mount for ollama data folder (by default will create the 'ollama' volume)."
    Write-Host "  --build                    Build the docker image before running the compose project."
    Write-Host "  --drop                     Drop the compose project."
    Write-Host "  -q, --quiet                Run script in headless mode."
    Write-Host "  -h, --help                 Show this help message."
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  $script:MyInvocation.MyCommand --drop"
    Write-Host "  $script:MyInvocation.MyCommand --enable-gpu[count=1]"
    Write-Host "  $script:MyInvocation.MyCommand --enable-api[port=11435]"
    Write-Host "  $script:MyInvocation.MyCommand --enable-gpu[count=1] --enable-api[port=12345] --webui[port=3000]"
    Write-Host "  $script:MyInvocation.MyCommand --enable-gpu[count=1] --enable-api[port=12345] --webui[port=3000] --data[folder=./ollama-data]"
    Write-Host "  $script:MyInvocation.MyCommand --enable-gpu[count=1] --enable-api[port=12345] --webui[port=3000] --data[folder=./ollama-data] --build"
    Write-Host ""
    Write-Host "This script configures and runs a docker-compose setup with optional GPU support, API exposure, and web UI configuration."
    Write-Host "About the gpu to use, the script automatically detects it using the 'lspci' command."
    Write-Host "In this case, the gpu detected is: $(Get-GpuDriver)"
}

# Default values
$gpu_count = 1
$api_port = 11435
$webui_port = 3000
$headless = $false
