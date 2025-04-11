#!/usr/bin/env python3
# Copyright(C) 2024-2025 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT

"""
RAUX Installer

This module provides functionality to install RAUX (Open WebUI).
Similar to lemonade-install, it can be invoked from the command line.
"""

import argparse
import os
import sys
import json
import datetime
import subprocess
import tempfile
import traceback
import shutil

try:
    import requests
except ImportError:
    print("ERROR: Required package 'requests' is not installed")
    print("Installing requests package...")
    subprocess.check_call(["python", "-m", "pip", "install", "requests"])
    import requests

# Global constants
PRODUCT_NAME = "RAUX"
PRODUCT_NAME_CONCAT = "raux"
GITHUB_REPO = "https://github.com/aigdat/raux.git"
CONDA_ENV_NAME = "raux_env"
PYTHON_VERSION = "3.11"
ICON_FILE = "raux.ico"

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
    formatted_message = f"[{timestamp}] [{PRODUCT_NAME}-Installer] {message}"

    # Print to console if requested
    if print_to_console:
        print(formatted_message)

    # Write to log file if it's set
    if LOG_FILE_PATH:
        try:
            # Open the log file in append mode
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(formatted_message + "\n")
        except Exception as e:
            print(f"WARNING: Failed to write to log file: {str(e)}")


def check_conda():
    """
    Checks if conda is installed and available in the PATH.

    Returns:
        tuple: (bool, str) - (is_installed, conda_executable_path)
    """
    log("Checking if conda is installed...")

    try:
        # Try to find conda in the PATH
        result = subprocess.run(
            ["where", "conda"], capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            conda_path = result.stdout.strip().split("\n")[0]
            log(f"Conda found at: {conda_path}")
            return True, conda_path
        else:
            # Try to find conda in common locations
            common_locations = [
                os.path.join(
                    os.environ.get("USERPROFILE", ""),
                    "miniconda3",
                    "Scripts",
                    "conda.exe",
                ),
                os.path.join(
                    os.environ.get("USERPROFILE", ""),
                    "Anaconda3",
                    "Scripts",
                    "conda.exe",
                ),
                os.path.join("C:", "ProgramData", "miniconda3", "Scripts", "conda.exe"),
                os.path.join("C:", "ProgramData", "Anaconda3", "Scripts", "conda.exe"),
                os.path.join(
                    os.environ.get("LOCALAPPDATA", ""),
                    "Continuum",
                    "miniconda3",
                    "Scripts",
                    "conda.exe",
                ),
                os.path.join(
                    os.environ.get("LOCALAPPDATA", ""),
                    "Continuum",
                    "anaconda3",
                    "Scripts",
                    "conda.exe",
                ),
            ]

            for location in common_locations:
                if os.path.exists(location):
                    log(f"Conda found at: {location}")
                    return True, location

            log("Conda not found in PATH or common locations")
            return False, None

    except Exception as e:
        log(f"Error checking for conda: {str(e)}")
        return False, None


def install_miniconda(install_dir):
    """
    Downloads and installs Miniconda.

    Args:
        install_dir: Directory where to install Miniconda

    Returns:
        tuple: (bool, str) - (success, conda_executable_path)
    """
    log("-------------")
    log("- Miniconda -")
    log("-------------")
    log("Downloading Miniconda installer...")

    try:
        # Determine the appropriate Miniconda installer
        installer_url = (
            "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
        )
        installer_path = os.path.join(
            tempfile.gettempdir(), "Miniconda3-latest-Windows-x86_64.exe"
        )

        # Download the installer
        log(f"Downloading from: {installer_url}")
        response = requests.get(installer_url, stream=True)
        response.raise_for_status()

        with open(installer_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        log(f"Downloaded installer to: {installer_path}")

        # Install Miniconda
        miniconda_path = os.path.join(os.path.expanduser("~"), "miniconda3")
        log(f"Installing Miniconda to: {miniconda_path}")

        # Run the installer silently
        result = subprocess.run(
            [
                installer_path,
                "/InstallationType=JustMe",
                "/AddToPath=1",
                "/RegisterPython=0",
                "/S",
                f"/D={miniconda_path}",
            ],
            check=False,
        )

        if result.returncode != 0:
            log(f"Miniconda installation failed with code: {result.returncode}")
            return False, None

        # Determine the path to conda executable
        conda_path = os.path.join(miniconda_path, "Scripts", "conda.exe")

        log("Miniconda installation completed successfully")

        # Initialize conda
        log("Initializing conda...")
        subprocess.run([conda_path, "init"], check=False)

        return True, conda_path

    except Exception as e:
        log(f"Error installing Miniconda: {str(e)}")
        return False, None


def create_conda_env(
    conda_path, env_name=CONDA_ENV_NAME, python_version=PYTHON_VERSION, install_dir=None
):
    """
    Creates a new conda environment with the specified Python version.

    Args:
        conda_path: Path to the conda executable
        env_name: Name of the conda environment
        python_version: Python version to install
        install_dir: Optional installation directory for the environment (used for environment location)

    Returns:
        tuple: (bool, str) - (success, env_path)
    """
    log("---------------------")
    log("- Conda Environment -")
    log("---------------------")

    try:
        # If install_dir is provided, create the environment at that location
        if install_dir:
            # Create the full path for the environment
            env_path = os.path.join(install_dir, env_name)
            log(f"Creating a Python {python_version} environment at: {env_path}")

            # Create the installation directory if it doesn't exist
            os.makedirs(install_dir, exist_ok=True)

            # Create the environment at the specified path using -p flag
            cmd = [
                conda_path,
                "create",
                "-p",
                env_path,
                f"python={python_version}",
                "-y",
            ]
        else:
            # Fall back to named environment if no install_dir is provided
            log(f"Creating a Python {python_version} environment named: {env_name}")
            cmd = [
                conda_path,
                "create",
                "-n",
                env_name,
                f"python={python_version}",
                "-y",
            ]

        log(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            log(f"Failed to create conda environment: {result.stderr}")
            return False, None

        if install_dir:
            log(f"Successfully created conda environment at: {env_path}")

            # Determine the Python executable path in the conda environment
            python_path = os.path.join(env_path, "python.exe")
            log(f"Python executable in conda environment: {python_path}")

            return True, python_path
        else:
            log(f"Successfully created conda environment: {env_name}")

            # Get the conda environments directory
            conda_info = subprocess.run(
                [conda_path, "info", "--json"],
                capture_output=True,
                text=True,
                check=False,
            )

            if conda_info.returncode == 0:
                conda_info_json = json.loads(conda_info.stdout)
                env_path = os.path.join(conda_info_json["envs_dirs"][0], env_name)
            else:
                # Fallback to default location
                env_path = os.path.join(
                    os.path.dirname(os.path.dirname(conda_path)), "envs", env_name
                )

            log(f"Conda environment created at: {env_path}")

            # Determine the Python executable path in the conda environment
            python_path = os.path.join(env_path, "python.exe")
            log(f"Python executable in conda environment: {python_path}")

            return True, python_path

    except Exception as e:
        log(f"Error creating conda environment: {str(e)}")
        return False, None


def download_latest_wheel(output_folder, output_filename=None):
    """
    Downloads the latest Open WebUI wheel file from GitHub releases.

    Args:
        output_folder: Folder where to save the wheel file
        output_filename: Optional specific filename for the downloaded wheel

    Returns:
        Path to the downloaded wheel file or None if download failed
    """
    log("******************************")
    log("* Open WebUI Download Module *")
    log("******************************")
    log("Downloading the latest Open WebUI wheel file...")

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Get the latest release info from GitHub API
    api_url = "https://api.github.com/repos/aigdat/raux/releases/latest"
    log(f"Fetching latest release information from: {api_url}")

    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()  # Raise exception for HTTP errors

        release_info = response.json()
        log(f"Latest release: {release_info.get('tag_name', 'unknown')}")
        log(f"Release date: {release_info.get('published_at', 'unknown')}")

        # Check if there are assets in the release
        assets = release_info.get("assets", [])
        if not assets:
            log("No assets found in the latest release")
            # If no assets, try to get the tarball or zipball URL
            tarball_url = release_info.get("tarball_url")
            zipball_url = release_info.get("zipball_url")

            if zipball_url:
                log(f"Using zipball URL: {zipball_url}")
                output_path = os.path.join(output_folder, "raux-latest.zip")

                # Download the zipball
                zip_response = requests.get(zipball_url, timeout=60)
                zip_response.raise_for_status()

                with open(output_path, "wb") as f:
                    f.write(zip_response.content)

                log(f"Successfully downloaded zipball to: {output_path}")
                return output_path

            elif tarball_url:
                log(f"Using tarball URL: {tarball_url}")
                output_path = os.path.join(output_folder, "raux-latest.tar.gz")

                # Download the tarball
                tar_response = requests.get(tarball_url, timeout=60)
                tar_response.raise_for_status()

                with open(output_path, "wb") as f:
                    f.write(tar_response.content)

                log(f"Successfully downloaded tarball to: {output_path}")
                return output_path
            else:
                log("No download URLs found in the release")
                return None

        # Find wheel files or any installable assets
        wheel_assets = [asset for asset in assets if asset["name"].endswith(".whl")]
        zip_assets = [asset for asset in assets if asset["name"].endswith(".zip")]

        # Prioritize wheel files, then zip files
        download_asset = None
        if wheel_assets:
            download_asset = wheel_assets[0]
            log(f"Found wheel file: {download_asset['name']}")
        elif zip_assets:
            download_asset = zip_assets[0]
            log(f"Found zip file: {download_asset['name']}")
        else:
            # If no wheel or zip, use the first asset
            if assets:
                download_asset = assets[0]
                log(
                    f"No wheel or zip files found. Using first available asset: {download_asset['name']}"
                )
            else:
                log("No assets found in the release")
                return None

        if download_asset:
            download_url = download_asset["browser_download_url"]
            asset_name = download_asset["name"]
            log(f"Download URL: {download_url}")

            # Use provided output filename or the original filename
            final_filename = output_filename if output_filename else asset_name
            output_path = os.path.join(output_folder, final_filename)

            # Download the file
            log(f"Downloading file to: {output_path}")
            file_response = requests.get(download_url, timeout=60)
            file_response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(file_response.content)

            # Verify file size
            file_size = os.path.getsize(output_path)
            log(f"Downloaded file size: {file_size} bytes")

            if file_size < 10000:
                log("WARNING: Downloaded file is too small, might not be a valid file")
                log("Continuing anyway as the file might be legitimate")

            log(f"Successfully downloaded file to: {output_path}")
            return output_path
        else:
            log("No suitable assets found in the latest release")
            return None

    except requests.exceptions.RequestException as e:
        log(f"Error during API request: {str(e)}")
    except Exception as e:
        log(f"Unexpected error during download: {str(e)}")

    return None


def install_wheel(wheel_path, python_path):
    """
    Installs the wheel file using pip.

    Args:
        wheel_path: Path to the wheel file to install
        python_path: Path to the Python executable to use

    Returns:
        bool: True if installation was successful, False otherwise
    """
    log("******************************")
    log("* Wheel File Installation *")
    log("******************************")

    wheel_path = os.path.normpath(wheel_path)

    try:
        log(f"Installing wheel from: {wheel_path}")
        log(f"Using Python executable: {python_path}")
        log("This may take a few minutes. Please wait...")

        # Run pip install command with real-time output
        process = subprocess.Popen(
            [python_path, "-m", "pip", "install", wheel_path, "--verbose"],
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


def create_shortcuts(env_path):
    """
    Creates desktop shortcuts for RAUX.

    Args:
        env_path: Path to the conda environment

    Returns:
        bool: True if successful, False otherwise
    """
    log("Creating shortcuts...")

    try:
        # Create desktop shortcut
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop_path, "{PRODUCT_NAME}.lnk")

        # Use PowerShell to create the shortcut
        ps_command = f"""
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "cmd.exe"
        $Shortcut.Arguments = "/C conda activate {CONDA_ENV_NAME} > NUL 2>&1 && start \"\" http://localhost:8080"
        $Shortcut.Save()
        """

        # Write the PowerShell script to a temporary file
        ps_script_path = os.path.join(tempfile.gettempdir(), "create_shortcut.ps1")
        with open(ps_script_path, "w", encoding="utf-8") as f:
            f.write(ps_command)

        # Execute the PowerShell script
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script_path],
            capture_output=True,
            text=True,
            check=False,
        )

        # Log the result of the PowerShell script execution
        if result.returncode != 0:
            log(f"PowerShell script failed with return code: {result.returncode}")
            log(f"PowerShell script stdout: {result.stdout}")
            log(f"PowerShell script stderr: {result.stderr}")
        else:
            log("PowerShell script executed successfully")

        # Clean up
        os.remove(ps_script_path)

        log(f"Created desktop shortcut at: {shortcut_path}")
        return True

    except Exception as e:
        log(f"Error creating shortcuts: {str(e)}")
        return False


def main():
    """Main installation function."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description=f"{PRODUCT_NAME} Installer")
    parser.add_argument(
        "--install-dir",
        dest="install_dir",
        default=os.path.join(os.path.expanduser("~"), "AppData", "Local", PRODUCT_NAME),
        type=str,
        help=f"Installation directory (default: %LOCALAPPDATA%\\{PRODUCT_NAME})",
    )
    parser.add_argument(
        "-y",
        "--yes",
        dest="yes",
        action="store_true",
        help="Answer 'yes' to all questions",
    )
    parser.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Force installation even if files are in use",
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Enable detailed debug logging",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Normalize the installation directory path
    install_dir = os.path.normpath(args.install_dir)

    # Set up the log file
    global LOG_FILE_PATH
    LOG_FILE_PATH = os.path.join(install_dir, f"{PRODUCT_NAME_CONCAT}_install.log")

    # Create the installation directory if it doesn't exist
    os.makedirs(install_dir, exist_ok=True)

    # Start the installation process
    log("*** INSTALLATION STARTED ***")
    log(f"Installing {PRODUCT_NAME} to: {install_dir}")
    log(f"Using conda environment: {CONDA_ENV_NAME}")
    log(f"Python version: {sys.version}")
    log(f"Windows version: {os.environ.get('OS', 'Unknown')}")
    log(f"Arguments: {vars(args)}")

    try:
        # Check if directory already exists and has content
        if os.path.exists(install_dir) and os.listdir(install_dir):
            log(f"An existing installation was found at: {install_dir}")
            log("Continuing with installation without removing existing files")
            log("This will add new files alongside existing ones")

        # Check if conda is installed
        conda_installed, conda_path = check_conda()

        if not conda_installed:
            log("Conda not installed")

            if not args.yes:
                user_input = input(
                    "Conda is not installed. Would you like to install Miniconda? (y/n): "
                )
                if user_input.lower() != "y":
                    log("Installation cancelled by user")
                    return 1

            # Install Miniconda
            miniconda_success, conda_path = install_miniconda(install_dir)

            if not miniconda_success:
                log("Failed to install Miniconda. Installation will be aborted.")
                return 1

        # Create conda environment
        env_success, python_path = create_conda_env(
            conda_path, CONDA_ENV_NAME, PYTHON_VERSION, install_dir
        )

        if not env_success:
            log(
                "Failed to create the Python environment. Installation will be aborted."
            )
            return 1

        log(f"Conda found at: {conda_path}")
        log(f"Python executable: {python_path}")

        # Create wheels directory
        wheels_dir = os.path.join(install_dir, "wheels")
        os.makedirs(wheels_dir, exist_ok=True)

        # Download the wheel file
        wheel_path = download_latest_wheel(output_folder=wheels_dir)

        if not wheel_path or not os.path.isfile(wheel_path):
            log(
                "Failed to download Open WebUI wheel file. Please check your internet connection and try again."
            )
            return 1

        # Install the wheel file
        install_success = install_wheel(wheel_path, python_path)

        if not install_success:
            log(
                "Failed to install Open WebUI wheel file. Please check the logs for details."
            )
            return 1

        # Look for .env.example in the extracted files and copy it to raux_env/Lib/.env
        log("Looking for .env.example file...")
        env_example_path = None
        for root, dirs, files in os.walk(install_dir):
            if ".env.example" in files:
                env_example_path = os.path.join(root, ".env.example")
                break
                    
        if env_example_path:
            log(f"Found .env.example at: {env_example_path}")
            env_dest_dir = os.path.join(install_dir, "raux_env", "Lib")
            os.makedirs(env_dest_dir, exist_ok=True)
            env_dest_path = os.path.join(env_dest_dir, ".env")
            try:
                shutil.copy2(env_example_path, env_dest_path)
                log(f"Copied .env.example to {env_dest_path}")
            except Exception as e:
                log(f"WARNING: Failed to copy .env.example to {env_dest_path}: {str(e)}")
        else:
            log("WARNING: Could not find .env.example in the extracted files")

        # Installation completed successfully
        log("*** INSTALLATION COMPLETED ***")
        log(f"{PRODUCT_NAME} installation completed successfully!")
        log(f"You can start {PRODUCT_NAME} by running:")
        log(f"  conda activate {CONDA_ENV_NAME}")
        log("  raux")
        log("Or by using the desktop shortcut if created")

        return 0
    except Exception as e:
        log(f"ERROR: An exception occurred: {str(e)}")

        log(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
