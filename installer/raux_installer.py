#!/usr/bin/env python3
import logging
import os
import sys
import subprocess
import tempfile
import time
import zipfile
import shutil
from datetime import datetime
import requests

# We'll keep these for reference only
CONDA_ENV_NAME = "raux_env"
PYTHON_VERSION = "3.11"


def install_raux(install_dir, debug=False):
    """
    Install RAUX (Windows-only).

    Args:
        install_dir (str): Directory where RAUX will be installed
        debug (bool): Enable debug logging

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Setup logging to both console and file
    log_file = os.path.join(install_dir, "raux_install.log")

    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [RAUX-Installer] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        # Use filemode='a' to append to the existing log file instead of overwriting it
        handlers=[
            logging.FileHandler(log_file, mode="a"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Start installation
    logging.info("===== RAUX INSTALLER =====")
    logging.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Current directory: {os.getcwd()}")
    logging.info(f"Log file: {log_file}")

    # Verify parameters
    logging.info("Verifying parameters...")
    logging.info(f"INSTALL_DIR set to: {install_dir}")
    logging.info("Using system Python for installation")

    if not install_dir:
        logging.error("ERROR: Installation directory parameter is missing")
        raise ValueError("Installation directory parameter is missing")

    # Check if installation directory exists and is writable
    logging.info(
        f"Checking if installation directory exists and is writable: {install_dir}"
    )
    if not os.path.exists(install_dir):
        logging.error(f"ERROR: Installation directory does not exist: {install_dir}")
        raise ValueError(f"Installation directory does not exist: {install_dir}")

    # Test write permissions
    logging.info("Testing write permissions in installation directory...")
    try:
        test_file = os.path.join(install_dir, "write_test.txt")
        with open(test_file, "w") as f:
            f.write("Test")
        os.remove(test_file)
    except Exception as e:
        logging.error(f"ERROR: Cannot write to installation directory: {install_dir}")
        logging.error(f"Exception: {str(e)}")
        raise ValueError(
            f"Cannot write to installation directory: {install_dir}. Exception: {str(e)}"
        )

    # We'll use the system Python to run install.py
    logging.info("Using system Python for installation")
    logging.info("install.py will handle its own conda environment setup")

    logging.info("Starting RAUX download and installation...")
    logging.info(f"Installation directory: {install_dir}")

    # Just use the current directory - no need to create a new temp directory
    # This avoids any cleanup issues
    temp_dir = os.getcwd()
    logging.info(f"Using current directory for installation: {temp_dir}")

    try:
        # Test file creation in temp directory
        logging.info("Creating a simple test file...")
        try:
            with open("test_file.txt", "w") as f:
                f.write("Test")
            if not os.path.exists("test_file.txt"):
                logging.error("ERROR: Cannot create test file in temporary directory")
                raise ValueError("Cannot create test file in temporary directory")
        except Exception as e:
            logging.error(
                f"ERROR: Cannot create test file in temporary directory: {str(e)}"
            )
            raise ValueError(
                f"Cannot create test file in temporary directory: {str(e)}"
            )

        # Get the latest release URL
        logging.info("Fetching the latest release URL...")
        download_url = get_latest_release_url()
        logging.info(f"Using download URL: {download_url}")

        # Download the zip file
        logging.info(f"Downloading from {download_url}")

        try:
            # Install requests if not already installed
            try:
                subprocess.run(
                    ["python", "-m", "pip", "install", "requests"],
                    check=True,
                    capture_output=True,
                )
                logging.info("Installed requests package")
            except Exception as e:
                logging.error(f"ERROR: Failed to install requests package: {str(e)}")
                raise ValueError(f"Failed to install requests package: {str(e)}")

            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()

            with open("raux.zip", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        except Exception as e:
            logging.error(f"ERROR: Failed to download RAUX zip file: {str(e)}")
            raise ValueError(f"Failed to download RAUX zip file: {str(e)}")

        # Check if zip file exists
        if not os.path.exists("raux.zip"):
            logging.error("ERROR: Failed to download RAUX zip file")

            raise ValueError("Failed to download RAUX zip file")

        # Create extracted_files directory
        extract_dir = os.path.join(temp_dir, "extracted_files")
        os.makedirs(extract_dir, exist_ok=True)

        # Extract files
        logging.info("Extracting files...")

        try:
            with zipfile.ZipFile("raux.zip", "r") as zip_ref:
                zip_ref.extractall(extract_dir)
        except Exception as e:

            logging.error(f"ERROR: Failed to extract RAUX zip file: {str(e)}")
            raise ValueError(f"Failed to extract RAUX zip file: {str(e)}")

        # List extracted files for debugging
        logging.info("Listing extracted files for debugging:")
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                logging.debug(f"  {os.path.join(root, file)}")

        # Find the install.py script
        install_script = None
        for root, dirs, files in os.walk(extract_dir):
            if "install.py" in files and "ux_installer" in root:
                install_script = os.path.join(root, "install.py")
                break

        if not install_script:
            # Look for any install.py
            for root, dirs, files in os.walk(extract_dir):
                if "install.py" in files:
                    install_script = os.path.join(root, "install.py")
                    break

        if not install_script:
            logging.error("ERROR: Could not find install.py in extracted files")
            raise ValueError("Could not find install.py in extracted files")

        # Run installation script using the system Python
        logging.info(f"Found install script: {install_script}")

        # Close log handlers to prevent file locking issues
        logging.info("Closing log handlers to prevent file locking issues...")
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)

        # Reinitialize logging with append mode
        logging.basicConfig(
            level=log_level,
            format="[%(asctime)s] [RAUX-Installer] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.FileHandler(log_file, mode="a"),
                logging.StreamHandler(sys.stdout),
            ],
        )

        # Build the command using the system Python
        # Let install.py handle its own conda environment setup
        cmd = [
            "python",  # Use the system Python to run install.py
            install_script,
            "--install-dir",
            install_dir,
            "--yes",
            "--force",
        ]

        if debug:
            cmd.append("--debug")

        logging.info(f"Running: {' '.join(cmd)}")
        try:
            # Run the command directly
            process = subprocess.run(cmd, check=False, capture_output=True, text=True)
            exit_code = process.returncode

            # Log the output from the installation script
            if process.stdout:
                logging.info("Installation script output:")
                for line in process.stdout.splitlines():
                    logging.info(f"  {line}")

            if process.stderr:
                logging.warning("Installation script errors:")
                for line in process.stderr.splitlines():
                    logging.warning(f"  {line}")

            logging.info(f"Exit code from install.py: {exit_code}")
        except Exception as e:
            logging.error(f"ERROR: Failed to run installation script: {str(e)}")
            raise ValueError(f"Failed to run installation script: {str(e)}")

        # Copy launcher scripts to the installation directory
        logging.info("Copying launcher scripts to the installation directory...")

        # Look for launcher scripts in the extracted files
        launcher_ps1_found = False
        launcher_cmd_found = False

        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == "launch_raux.ps1":
                    launcher_ps1_path = os.path.join(root, file)
                    launcher_ps1_found = True
                    logging.info(f"Found launch_raux.ps1 at: {launcher_ps1_path}")
                    try:
                        shutil.copy2(
                            launcher_ps1_path,
                            os.path.join(install_dir, "launch_raux.ps1"),
                        )
                        logging.info(f"Copied launch_raux.ps1 to {install_dir}")
                    except Exception as e:
                        logging.error(
                            f"ERROR: Failed to copy launch_raux.ps1: {str(e)}"
                        )
                        raise ValueError(f"Failed to copy launch_raux.ps1: {str(e)}")

                if file == "launch_raux.cmd":
                    launcher_cmd_path = os.path.join(root, file)
                    launcher_cmd_found = True
                    logging.info(f"Found launch_raux.cmd at: {launcher_cmd_path}")
                    try:
                        shutil.copy2(
                            launcher_cmd_path,
                            os.path.join(install_dir, "launch_raux.cmd"),
                        )
                        logging.info(f"Copied launch_raux.cmd to {install_dir}")
                    except Exception as e:
                        logging.error(
                            f"ERROR: Failed to copy launch_raux.cmd: {str(e)}"
                        )
                        raise ValueError(f"Failed to copy launch_raux.cmd: {str(e)}")

        # Check if we found and copied the launcher scripts
        if not launcher_ps1_found:
            logging.warning(
                "WARNING: Could not find launch_raux.ps1 in the extracted files"
            )

        if not launcher_cmd_found:
            logging.warning(
                "WARNING: Could not find launch_raux.cmd in the extracted files"
            )

        # Also look for the launcher scripts in the current directory (they might be included separately)
        if not launcher_ps1_found and os.path.exists("launch_raux.ps1"):
            try:
                shutil.copy2(
                    "launch_raux.ps1", os.path.join(install_dir, "launch_raux.ps1")
                )
                logging.info(
                    f"Copied launch_raux.ps1 from current directory to {install_dir}"
                )
                launcher_ps1_found = True
            except Exception as e:
                logging.error(
                    f"ERROR: Failed to copy launch_raux.ps1 from current directory: {str(e)}"
                )
                raise ValueError(
                    f"Failed to copy launch_raux.ps1 from current directory: {str(e)}"
                )

        if not launcher_cmd_found and os.path.exists("launch_raux.cmd"):
            try:
                shutil.copy2(
                    "launch_raux.cmd", os.path.join(install_dir, "launch_raux.cmd")
                )
                logging.info(
                    f"Copied launch_raux.cmd from current directory to {install_dir}"
                )
                launcher_cmd_found = True
            except Exception as e:
                logging.error(
                    f"ERROR: Failed to copy launch_raux.cmd from current directory: {str(e)}"
                )
                raise ValueError(
                    f"Failed to copy launch_raux.cmd from current directory: {str(e)}"
                )

        # Installation summary
        logging.info(f"Installation completed with exit code: {exit_code}")

        if exit_code != 0:
            logging.error(f"Installation failed with error code: {exit_code}")
            logging.error(
                "Please ensure all RAUX applications are closed and try again."
            )
            logging.error(
                "If the problem persists, you may need to restart your computer."
            )
            raise ValueError(f"Installation failed with error code: {exit_code}")
        else:
            logging.info("Installation completed successfully.")
            logging.info("You can start RAUX by running:")
            logging.info("  conda activate raux_env")
            logging.info("  raux")
            logging.info("Or by using the desktop shortcut if created.")

        logging.info("===== INSTALLATION SUMMARY =====")
        logging.info(f"Installation directory: {install_dir}")
        logging.info("Using system Python for installation")
        logging.info(
            f"Launcher scripts copied: PS1={launcher_ps1_found}, CMD={launcher_cmd_found}"
        )
        logging.info(f"Final exit code: {exit_code}")
        logging.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("===============================")

        # Note: We're intentionally NOT cleaning up the temp directory
        logging.info(
            "Temporary directory will not be cleaned up to prevent file-in-use errors"
        )

        return exit_code

    except Exception as e:
        logging.error(f"Unexpected error during installation: {str(e)}")
        raise ValueError(f"Unexpected error during installation: {str(e)}")


def get_latest_release_url():
    """
    Get the URL for the latest release of RAUX.

    Returns:
        str: URL to download the latest release
    """
    try:
        response = requests.get(
            "https://api.github.com/repos/aigdat/raux/releases/latest", timeout=30
        )

        if response.status_code == 200:
            release_info = response.json()
            assets = release_info.get("assets", [])

            # Look for Windows-specific assets first
            for asset in assets:
                if asset["name"].endswith(".zip") and (
                    "win" in asset["name"].lower() or "windows" in asset["name"].lower()
                ):
                    return asset["browser_download_url"]

            # If no Windows-specific zip found, look for any zip
            for asset in assets:
                if asset["name"].endswith(".zip"):
                    return asset["browser_download_url"]

            # If no zip found, use zipball URL
            if "zipball_url" in release_info:
                return release_info["zipball_url"]

        # If we get here, we didn't find a suitable asset
        logging.warning("No suitable release assets found, using default URL")

        return "https://github.com/aigdat/raux/archive/refs/heads/main.zip"

    except Exception as e:
        logging.error(f"Error fetching release info: {str(e)}")

        # Note: When we raise an exception here, the function will exit immediately
        # and the calling code will need to handle the exception.
        # The NSIS installer will see this as a non-zero exit code.
        raise ValueError(f"Error fetching release info: {str(e)}")


if __name__ == "__main__":
    # If run directly, parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="RAUX Installer (Windows-only)")
    parser.add_argument("--install-dir", required=True, help="Installation directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    exit_code = install_raux(args.install_dir, args.debug)
    sys.exit(exit_code)
