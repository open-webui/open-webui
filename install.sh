#!/bin/bash

# Function to detect operating system
detect_os() {
    OS="$(uname -s)"
    case "$OS" in
        Linux*)     
            MACHINE="Linux"
            if grep -qi microsoft /proc/version; then
                # Check if we're on WSL (Windows Subsystem for Linux)
                MACHINE="WSL"
            fi
            ;;
        Darwin*)    
            MACHINE="MacOS"
            ;;
        CYGWIN*|MINGW32*|MSYS*|MINGW*)
            MACHINE="Windows"
            ;;
        *)
            MACHINE="UNKNOWN:$OS"
            ;;
    esac
    echo $MACHINE
}

# Run the OS detection
OS=$(detect_os)

# Only proceed with the installation if the machine is plain Linux (not WSL)
if [ "$OS" = "Linux" ]; then
    echo "Detected Linux environment. Starting the Open WebUI installation..."
    
    # Define the URL of the main installation script
    INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/open-webui/open-webui/installer/install-linux.sh"

    # Fetch and execute the installation script
    curl -fsSL "$INSTALL_SCRIPT_URL" | bash

    echo "Thank you for being a user of Open WebUI!"
elif [ "$OS" = "WSL" ]; then
    echo "Detected Windows Subsystem for Linux (WSL). This installer is intended for native Linux environments only."
    exit 1
else
    echo "Detected $OS. This installer only supports Linux environments."
    exit 1
fi
