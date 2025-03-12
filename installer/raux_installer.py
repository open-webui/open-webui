# Copyright(C) 2024-2025 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT

import argparse
import os
import sys
import json
import datetime
import subprocess

# Check for required packages
try:
    import requests
except ImportError:
    print("ERROR: Required package 'requests' is not installed")
    print("Installing requests package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# Global log file path
LOG_FILE_PATH = None


def log(message, print_to_console=True):
    """
    Logs a message to both stdout and the log file if specified.

    Args:
        message: The message to log
        print_to_console: Whether to print the message to console
    """
    # Get current timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [AMD-AI-UX-Installer] {message}"

    # Print to console if requested
    if print_to_console:
        print(formatted_message)

    # Write to log file if it's set
    if LOG_FILE_PATH:
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(formatted_message + "\n")
        except Exception as e:
            print(f"WARNING: Failed to write to log file: {str(e)}")


def download_latest_wheel(output_folder, output_filename=None):
    """
    Downloads the latest Open WebUI wheel file from GitHub releases.

    Args:
        output_folder: Folder where to save the wheel file
        output_filename: Optional specific filename for the downloaded wheel

    Returns:
        Path to the downloaded wheel file or None if download failed
    """
    log("Downloading the latest Open WebUI wheel file...")

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # First try to get the latest release info from GitHub API
    api_url = "https://api.github.com/repos/aigdat/open-webui/releases/latest"
    log(f"Fetching latest release information from: {api_url}")

    try:
        response = requests.get(api_url, timeout=30)

        if response.status_code == 200:
            release_info = response.json()

            # Find the first .whl file in the assets
            wheel_asset = None
            for asset in release_info.get("assets", []):
                if asset["name"].endswith(".whl"):
                    wheel_asset = asset
                    break

            if wheel_asset:
                wheel_url = wheel_asset["browser_download_url"]
                wheel_name = wheel_asset["name"]
                log(f"Found wheel file: {wheel_name}")
                log(f"Download URL: {wheel_url}")

                # Use provided output filename or the original filename
                final_filename = output_filename if output_filename else wheel_name
                output_path = os.path.join(output_folder, final_filename)

                # Download the wheel file
                log(f"Downloading wheel file to: {output_path}")
                wheel_response = requests.get(wheel_url, timeout=60)

                if wheel_response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(wheel_response.content)

                    # Verify file size
                    file_size = os.path.getsize(output_path)
                    log(f"Downloaded file size: {file_size} bytes")

                    if file_size < 10000:
                        log(
                            "ERROR: Downloaded file is too small, likely not a valid wheel file"
                        )
                        return None

                    log(f"Successfully downloaded wheel file to: {output_path}")
                    return output_path
                else:
                    log(
                        f"Failed to download wheel file. Status code: {wheel_response.status_code}"
                    )
            else:
                log("No wheel file found in the latest release assets")
        else:
            log(
                f"Failed to fetch release information. Status code: {response.status_code}"
            )
            try:
                error_info = response.json()
                log(f"Error details: {json.dumps(error_info, indent=2)}")
            except Exception as e:
                log(f"Response content: {response.text} with error: {str(e)}")

    except Exception as e:
        log(f"Error during API request or download: {str(e)}")

    return None


def install_wheel(wheel_path):
    """
    Installs the wheel file using pip.

    Args:
        wheel_path: Path to the wheel file to install
        python_path: Optional path to the Python executable to use

    Returns:
        True if installation was successful, False otherwise
    """
    log("******************************")
    log("* Wheel File Installation *")
    log("******************************")

    # Use the provided Python path or the current Python executable
    python_exe = sys.executable

    wheel_path = os.path.normpath(wheel_path)

    try:
        log(f"Installing wheel from: {wheel_path}")
        log("This may take a few minutes. Please wait...")

        # Run pip install command with real-time output
        process = subprocess.Popen(
            [python_exe, "-m", "pip", "install", wheel_path, "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Display output in real-time
        for line in process.stdout:
            line = line.strip()
            if line:
                log(line)

        # Wait for process to complete and get return code
        return_code = process.wait()

        # Check if installation was successful
        if return_code == 0:
            log("Open WebUI wheel file successfully installed")
            log("Installation completed successfully")
            return True
        else:
            log("ERROR: Failed to install Open WebUI wheel file")
            log(f"Pip installation returned error code: {return_code}")
            return False

    except Exception as e:
        log(f"ERROR: Exception during pip installation: {str(e)}")
        return False


def main():
    # Set up argument parser - make install_dir optional with default value
    parser = argparse.ArgumentParser(description="RAUX Installer")
    parser.add_argument(
        "--install-dir",
        dest="install_dir",
        default=f"{os.getcwd()}\\installer",
        type=str,
        help="Installation directory (default: current working directory)",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Hard-coded parameters
    install_dir = os.path.normpath(args.install_dir)

    log_file = os.path.normpath(os.path.join(install_dir, "raux_install.log"))

    # Set the log file path
    log_file_path = log_file

    log(f"Log file path set to: {log_file_path}")
    log(f"Installation directory: {install_dir}")

    # Create wheels directory in the installation folder
    wheels_dir = os.path.normpath(os.path.join(install_dir, "wheels"))
    log(f"Creating wheels directory: {wheels_dir}")
    os.makedirs(wheels_dir, exist_ok=True)

    # Print header for download module
    log("******************************")
    log("* Open WebUI Download Module *")
    log("******************************")

    # Download the wheel file
    wheel_path = download_latest_wheel(output_folder=wheels_dir, output_filename=None)

    # Check if the download was successful
    if not wheel_path or not os.path.isfile(wheel_path):
        error_msg = "Failed to download Open WebUI wheel file. Please check your internet connection and try again."
        log(f"ERROR: {error_msg}")
        sys.exit(1)

    # Install the wheel file
    install_success = install_wheel(wheel_path)

    if not install_success:
        error_msg = "Failed to install Open WebUI wheel file. Please check the logs for details."
        log(f"ERROR: {error_msg}")
        sys.exit(1)

    # Installation completed successfully
    success_msg = "Open WebUI installation completed successfully."
    log(success_msg)

    log("Open WebUI installation process completed")
    sys.exit(0)


if __name__ == "__main__":
    main()
