#!/usr/bin/env python3
# Copyright(C) 2024-2025 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT

"""
AMD AI UX Installer

This module provides functionality to install AMD AI UX (Open WebUI).
Similar to lemonade-install, it can be invoked from the command line.
"""

import argparse
import os
import sys
import json
import datetime
import subprocess
import platform
import shutil
import tempfile
import time

try:
    import requests
except ImportError:
    print("ERROR: Required package 'requests' is not installed")
    print("Installing requests package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# Global constants
PRODUCT_NAME = "AMD AI UX"
PRODUCT_NAME_CONCAT = "AMD_AI_UX"
GITHUB_REPO = "https://github.com/aigdat/open-webui.git"
CONDA_ENV_NAME = "amd_ai_ux_env"
PYTHON_VERSION = "3.11"
ICON_FILE = "gaia.ico"

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
    formatted_message = f"[{timestamp}] [{PRODUCT_NAME_CONCAT}-Installer] {message}"

    # Print to console if requested
    if print_to_console:
        print(formatted_message)

    # Debugging: Print log file path
    print(f"Log file path: {LOG_FILE_PATH}")

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
        install_dir: Optional installation directory for the environment

    Returns:
        tuple: (bool, str) - (success, env_path)
    """
    log("---------------------")
    log("- Conda Environment -")
    log("---------------------")

    try:
        log(f"Creating a Python {python_version} environment named: {env_name}")

        # Create the conda environment
        cmd = [conda_path, "create", "-n", env_name, f"python={python_version}", "-y"]

        # If install_dir is provided, create the environment in that directory
        if install_dir:
            env_path = os.path.join(install_dir, env_name)
            cmd = [
                conda_path,
                "create",
                "-p",
                env_path,
                f"python={python_version}",
                "-y",
            ]
        else:
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

        log(f"Creating conda environment at: {env_path}")
        log(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            log(f"Failed to create conda environment: {result.stderr}")
            return False, None

        log(f"Successfully created conda environment: {env_name}")

        # Determine the Python executable path in the conda environment
        if install_dir:
            python_path = os.path.join(env_path, "python.exe")
        else:
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
    Creates desktop shortcuts for AMD AI UX.

    Args:
        env_path: Path to the conda environment

    Returns:
        bool: True if successful, False otherwise
    """
    log("Creating shortcuts...")

    try:
        # Create desktop shortcut
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop_path, "AMD-AI-UX.lnk")

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


def safely_remove_directory(directory_path, max_retries=5, retry_delay=3):
    """
    Safely removes a directory with retries and better error handling.

    Args:
        directory_path: Path to the directory to remove
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds

    Returns:
        bool: True if successful, False otherwise
    """
    log(f"Attempting to remove directory: {directory_path}")

    for attempt in range(max_retries):
        try:
            if os.path.exists(directory_path):
                # Try to close any open file handles
                if attempt > 0:
                    log(
                        f"Retry attempt {attempt+1}/{max_retries}. Trying to release file handles..."
                    )
                    # Run garbage collection to release file handles
                    import gc

                    gc.collect()
                    # On Windows, try to run a process to unlock files
                    try:
                        # List all Python processes
                        log("Listing Python processes that might be locking files:")
                        result = subprocess.run(
                            ["tasklist", "/fi", "imagename eq python.exe"],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        log(result.stdout)

                        # Try to kill Python processes
                        log("Attempting to terminate Python processes...")
                        subprocess.run(
                            ["taskkill", "/F", "/IM", "python.exe", "/T"],
                            capture_output=True,
                            check=False,
                        )
                    except Exception as e:
                        log(f"Error while trying to terminate processes: {str(e)}")

                # Try to remove the directory
                log(
                    f"Attempting to remove directory (attempt {attempt+1}/{max_retries}): {directory_path}"
                )

                # Try a different approach on Windows
                if platform.system() == "Windows":
                    try:
                        # First try with shutil
                        shutil.rmtree(directory_path)
                    except Exception as e1:
                        log(f"shutil.rmtree failed: {str(e1)}")
                        try:
                            # Try with system command as fallback
                            log("Trying system command to remove directory...")
                            subprocess.run(
                                ["rd", "/s", "/q", directory_path], check=False
                            )
                        except Exception as e2:
                            log(f"System command failed: {str(e2)}")
                            raise e1
                else:
                    shutil.rmtree(directory_path)

                # Verify it was removed
                if not os.path.exists(directory_path):
                    log(f"Successfully removed directory: {directory_path}")
                    return True
                else:
                    log(
                        f"Directory still exists after removal attempt: {directory_path}"
                    )
            else:
                log(f"Directory does not exist, nothing to remove: {directory_path}")
                return True

        except Exception as e:
            log(
                f"Error removing directory (attempt {attempt+1}/{max_retries}): {str(e)}"
            )

            # Check if it's a file access error
            if "being used by another process" in str(e):
                log(
                    "Files are locked by another process. Trying to identify processes..."
                )
                try:
                    # Try to list processes that might be using the files
                    subprocess.run(
                        ["handle", directory_path], capture_output=True, check=False
                    )
                except Exception:
                    # handle.exe might not be available, so we'll just continue
                    pass

                log(
                    "Please close any applications that might be using files in the directory."
                )
                log(
                    "Common applications to check: Command Prompt, PowerShell, Explorer, Python, etc."
                )

            # Wait before retrying
            if attempt < max_retries - 1:
                log(f"Waiting {retry_delay} seconds before retrying...")
                time.sleep(retry_delay)

    log(f"Failed to remove directory after {max_retries} attempts: {directory_path}")
    return False


def main():
    """Main installation function."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description=f"{PRODUCT_NAME} Installer")
    parser.add_argument(
        "--install-dir",
        dest="install_dir",
        default=os.path.join(
            os.path.expanduser("~"), "AppData", "Local", PRODUCT_NAME_CONCAT
        ),
        type=str,
        help=f"Installation directory (default: %LOCALAPPDATA%\\{PRODUCT_NAME_CONCAT})",
    )
    parser.add_argument(
        "--no-shortcuts",
        dest="no_shortcuts",
        action="store_true",
        help="Do not create desktop shortcuts",
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
    parser.add_argument(
        "--skip-cleanup",
        dest="skip_cleanup",
        action="store_true",
        help="Skip cleanup operations to avoid file access issues",
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
    log(f"Platform: {platform.platform()}")
    log(f"Arguments: {vars(args)}")

    try:
        # Check if directory already exists and has content
        if (
            os.path.exists(install_dir)
            and os.listdir(install_dir)
            and not args.skip_cleanup
        ):
            log(f"An existing installation was found at: {install_dir}")

            if not args.yes and not args.force:
                user_input = input(
                    "Would you like to remove it and continue with the installation? (y/n): "
                )
                if user_input.lower() != "y":
                    log("Installation cancelled by user")
                    return 1
            else:
                log(
                    "Automatically removing existing installation due to '--yes' or '--force' flag"
                )

            # Remove existing installation
            log("Removing existing installation...")

            # Try to remove the conda environment first
            conda_installed, conda_path = check_conda()
            if conda_installed:
                log(f"Removing conda environment: {CONDA_ENV_NAME}")
                subprocess.run(
                    [conda_path, "env", "remove", "-n", CONDA_ENV_NAME, "-y"],
                    check=False,
                )

            # List directory contents before removal
            if args.debug:
                log("Directory contents before removal:")
                try:
                    for root, dirs, files in os.walk(install_dir):
                        log(f"Directory: {root}")
                        for d in dirs:
                            log(f"  Dir: {d}")
                        for f in files:
                            log(f"  File: {f}")
                except Exception as e:
                    log(f"Error listing directory contents: {str(e)}")

            # Remove the installation directory
            if not safely_remove_directory(install_dir):
                if args.force:
                    log(
                        "WARNING: Could not remove existing installation directory, but continuing due to --force flag"
                    )
                    # Try to create the directory again
                    try:
                        # Try to remove any problematic files individually
                        log("Attempting to remove individual files...")
                        for root, dirs, files in os.walk(install_dir, topdown=False):
                            for name in files:
                                try:
                                    file_path = os.path.join(root, name)
                                    log(f"Removing file: {file_path}")
                                    os.remove(file_path)
                                except Exception as e:
                                    log(f"Failed to remove file {name}: {str(e)}")

                            for name in dirs:
                                try:
                                    dir_path = os.path.join(root, name)
                                    log(f"Removing directory: {dir_path}")
                                    os.rmdir(dir_path)
                                except Exception as e:
                                    log(f"Failed to remove directory {name}: {str(e)}")

                        # Try to recreate the directory
                        os.makedirs(install_dir, exist_ok=True)
                    except Exception as e:
                        log(f"Error during forced cleanup: {str(e)}")
                else:
                    log("ERROR: Failed to remove existing installation directory")
                    log("Please close any applications using AMD AI UX and try again")
                    log(
                        "You can also use the --force flag to attempt to continue anyway"
                    )
                    log("Or use --skip-cleanup to skip removal of existing files")
                    return 1
            else:
                # Recreate the directory
                os.makedirs(install_dir, exist_ok=True)
                log("Deleted all contents of install directory")
        elif (
            os.path.exists(install_dir)
            and os.listdir(install_dir)
            and args.skip_cleanup
        ):
            log(f"An existing installation was found at: {install_dir}")
            log("Skipping cleanup as requested with --skip-cleanup flag")
            log("WARNING: This may cause conflicts with existing files")

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

        # Create shortcuts if not disabled
        if not args.no_shortcuts:
            shortcut_success = create_shortcuts(python_path)
            if not shortcut_success:
                log("Warning: Failed to create shortcuts")

        # Installation completed successfully
        log("*** INSTALLATION COMPLETED ***")
        log(f"{PRODUCT_NAME} installation completed successfully!")
        log(f"You can start {PRODUCT_NAME} by running:")
        log(f"  conda activate {CONDA_ENV_NAME}")
        log("  open-webui")
        log("Or by using the desktop shortcut if created")

        if args.skip_cleanup:
            log(
                "NOTE: Cleanup was skipped as requested. Some temporary files may remain."
            )

        return 0
    except Exception as e:
        log(f"ERROR: An exception occurred: {str(e)}")
        import traceback

        log(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
