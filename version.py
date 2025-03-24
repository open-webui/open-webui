# Copyright(C) 2024-2025 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT

import subprocess
import logging
from typing import Optional

# Read version from package.json
def get_package_version() -> str:
    """Get version from package.json."""
    try:
        import json
        with open("package.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception as e:
        print(f"Failed to read version from package.json: {str(e)}")
        return "0.0.0"

def get_git_hash(hash_length: int = 8) -> str:
    """Get the current Git commit hash.

    Args:
        hash_length (int): Number of characters of the hash to return. Defaults to 8.

    Returns:
        str: The Git hash of the current commit, truncated to specified length.
            Returns "unknown" if Git command fails.
    """
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", f"--short={hash_length}", "HEAD"]
            )
            .decode("ascii")
            .strip()
        )
    except subprocess.SubprocessError as e:
        print(f"Failed to get Git hash: {str(e)}")
        return "unknown"
    except Exception as e:
        print(f"Unexpected error while getting Git hash: {str(e)}")
        return "unknown"

def get_github_root() -> Optional[str]:
    """Get the GitHub repository root (organization/user name).

    Returns:
        Optional[str]: The GitHub repository root (e.g., 'amd' from 'github.com/amd/raux').
            Returns None if the command fails or the remote URL is not from GitHub.
    """
    try:
        remote_url = (
            subprocess.check_output(["git", "config", "--get", "remote.origin.url"])
            .decode("ascii")
            .strip()
        )

        # Handle different GitHub URL formats
        if "github.com" in remote_url:
            # Remove .git suffix if present
            remote_url = remote_url.replace(".git", "")

            # Handle SSH format (git@github.com:user/repo)
            if remote_url.startswith("git@"):
                parts = remote_url.split(":")[1].split("/")
            # Handle HTTPS format (https://github.com/user/repo)
            else:
                parts = remote_url.split("github.com/")[1].split("/")

            return parts[0]
    except (subprocess.SubprocessError, IndexError) as e:
        print(f"Failed to get GitHub root: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error while getting GitHub root: {str(e)}")
        return None

def main():
    __version__ = get_package_version()
    github_root = get_github_root()
    git_hash = get_git_hash()

    version_with_hash = (
        f"{github_root}/v{__version__}+{git_hash}"
        if github_root
        else f"v{__version__}+{git_hash}"
    )

    # Write version to version.txt file
    try:
        with open("version.txt", "w", encoding="utf-8") as f:
            f.write(version_with_hash)
        print(f"Version written to version.txt: {version_with_hash}")
    except Exception as e:
        print(f"Failed to write version.txt: {str(e)}")
        raise

if __name__ == "__main__":
    main()
