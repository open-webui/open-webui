# Copyright(C) 2024-2025 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import json
import pytest
import subprocess
from unittest.mock import patch, mock_open, call
from pathlib import Path
import sys

# Add the project root to Python path to import version.py
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from version import get_package_version, get_git_hash, get_github_root, main

@pytest.fixture
def mock_package_json():
    """Fixture to provide a mock package.json content."""
    return {
        "name": "raux",
        "version": "1.2.3",
        "description": "RAUX package"
    }

@pytest.fixture
def mock_git_hash():
    """Fixture to provide a mock git hash."""
    return "a1b2c3d4"

@pytest.fixture
def mock_github_root():
    """Fixture to provide a mock GitHub root."""
    return "amd"

def test_get_package_version_success(mock_package_json):
    """Test successful package.json version reading."""
    mock_json = json.dumps(mock_package_json)
    with patch("builtins.open", mock_open(read_data=mock_json)):
        version = get_package_version()
        assert version == "1.2.3"

def test_get_package_version_missing_version(mock_package_json):
    """Test package.json with missing version field."""
    mock_package_json.pop("version")
    mock_json = json.dumps(mock_package_json)
    with patch("builtins.open", mock_open(read_data=mock_json)):
        version = get_package_version()
        assert version == "0.0.0"

def test_get_package_version_file_not_found():
    """Test when package.json doesn't exist."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        version = get_package_version()
        assert version == "0.0.0"

def test_get_git_hash_success(mock_git_hash):
    """Test successful git hash retrieval."""
    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.return_value = mock_git_hash.encode("ascii")
        hash_value = get_git_hash()
        assert hash_value == mock_git_hash

def test_get_git_hash_failure():
    """Test git hash retrieval failure."""
    with patch("subprocess.check_output", side_effect=subprocess.SubprocessError):
        hash_value = get_git_hash()
        assert hash_value == "unknown"

def test_get_github_root_https_success(mock_github_root):
    """Test successful GitHub root retrieval with HTTPS URL."""
    mock_url = f"https://github.com/{mock_github_root}/raux.git"
    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.return_value = mock_url.encode("ascii")
        root = get_github_root()
        assert root == mock_github_root

def test_get_github_root_ssh_success(mock_github_root):
    """Test successful GitHub root retrieval with SSH URL."""
    mock_url = f"git@github.com:{mock_github_root}/raux.git"
    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.return_value = mock_url.encode("ascii")
        root = get_github_root()
        assert root == mock_github_root

def test_get_github_root_non_github_url():
    """Test GitHub root retrieval with non-GitHub URL."""
    mock_url = "https://gitlab.com/org/repo.git"
    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.return_value = mock_url.encode("ascii")
        root = get_github_root()
        assert root is None

def test_get_github_root_failure():
    """Test GitHub root retrieval failure."""
    with patch("subprocess.check_output", side_effect=subprocess.SubprocessError):
        root = get_github_root()
        assert root is None

def test_main_success(mock_package_json, mock_git_hash, mock_github_root):
    """Test successful version generation."""
    # Mock all dependencies
    mock_file = mock_open(read_data=json.dumps(mock_package_json))
    with patch("builtins.open", mock_file), \
         patch("subprocess.check_output") as mock_check_output:
        
        def mock_check_output_side_effect(command, *args, **kwargs):
            if command[1] == "rev-parse":
                return mock_git_hash.encode("ascii")
            elif command[1] == "config":
                return f"https://github.com/{mock_github_root}/raux.git".encode("ascii")
            raise ValueError(f"Unexpected command: {command}")
        
        mock_check_output.side_effect = mock_check_output_side_effect
        
        # Run main function
        main()
        
        # Verify version.txt was written with correct content
        expected_version = f"{mock_github_root}/v{mock_package_json['version']}+{mock_git_hash}"
        mock_file.assert_any_call("version.txt", "w", encoding="utf-8")
        mock_file().write.assert_any_call(expected_version)

def test_main_no_github_root(mock_package_json, mock_git_hash):
    """Test version generation without GitHub root."""
    # Mock all dependencies
    mock_file = mock_open(read_data=json.dumps(mock_package_json))
    with patch("builtins.open", mock_file), \
         patch("subprocess.check_output") as mock_check_output:
        
        def mock_check_output_side_effect(command, *args, **kwargs):
            if command[1] == "rev-parse":
                return mock_git_hash.encode("ascii")
            elif command[1] == "config":
                return "https://gitlab.com/org/repo.git".encode("ascii")
            raise ValueError(f"Unexpected command: {command}")
        
        mock_check_output.side_effect = mock_check_output_side_effect
        
        # Run main function
        main()
        
        # Verify version.txt was written with correct content
        expected_version = f"v{mock_package_json['version']}+{mock_git_hash}"
        mock_file.assert_any_call("version.txt", "w", encoding="utf-8")
        mock_file().write.assert_any_call(expected_version)

def test_main_write_failure(mock_package_json, mock_git_hash, mock_github_root):
    """Test version generation with file write failure."""
    # Mock all dependencies
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_package_json))), \
         patch("subprocess.check_output") as mock_check_output, \
         patch("builtins.open", side_effect=IOError("Write failed")):
        
        def mock_check_output_side_effect(command, *args, **kwargs):
            if command[1] == "rev-parse":
                return mock_git_hash.encode("ascii")
            elif command[1] == "config":
                return f"https://github.com/{mock_github_root}/raux.git".encode("ascii")
            raise ValueError(f"Unexpected command: {command}")
        
        mock_check_output.side_effect = mock_check_output_side_effect
        
        # Run main function and expect it to raise IOError
        with pytest.raises(IOError):
            main() 