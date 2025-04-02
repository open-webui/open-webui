# Copyright(C) 2024-2025 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import json
import pytest
import subprocess
from unittest.mock import patch, mock_open
from pathlib import Path
import sys

# Add the installer directory to Python path to import version.py
project_root = str(Path(__file__).parent.parent.parent)
installer_path = str(Path(project_root) / "installer")
sys.path.insert(0, installer_path)

from version import get_package_version, get_git_hash, main

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

def test_get_package_version_success(mock_package_json):
    """Test successful package.json version reading."""
    mock_json = json.dumps(mock_package_json)
    with patch("os.path.dirname") as mock_dirname, \
         patch("os.path.join", lambda *args: args[-1]), \
         patch("builtins.open", mock_open(read_data=mock_json)) as mock_file:
        # Mock dirname to return the same path twice (simulating parent.parent)
        mock_dirname.side_effect = ["installer", "root"]
        version = get_package_version()
        assert version == "1.2.3"
        # Verify the file was opened with the correct path
        mock_file.assert_called_with("package.json", "r", encoding="utf-8")

def test_get_package_version_missing_version(mock_package_json):
    """Test package.json with missing version field."""
    mock_package_json.pop("version")
    mock_json = json.dumps(mock_package_json)
    with patch("os.path.dirname") as mock_dirname, \
         patch("os.path.join", lambda *args: args[-1]), \
         patch("builtins.open", mock_open(read_data=mock_json)):
        # Mock dirname to return the same path twice (simulating parent.parent)
        mock_dirname.side_effect = ["installer", "root"]
        version = get_package_version()
        assert version == "0.0.0"

def test_get_package_version_file_not_found():
    """Test when package.json doesn't exist."""
    with patch("os.path.dirname") as mock_dirname, \
         patch("os.path.join", lambda *args: args[-1]), \
         patch("builtins.open", side_effect=FileNotFoundError):
        # Mock dirname to return the same path twice (simulating parent.parent)
        mock_dirname.side_effect = ["installer", "root"]
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

def test_main_success(mock_package_json, mock_git_hash):
    """Test successful version generation."""
    mock_json = json.dumps(mock_package_json)
    with patch("os.path.dirname") as mock_dirname, \
         patch("os.path.join", lambda *args: args[-1]), \
         patch("builtins.open", mock_open(read_data=mock_json)) as mock_file, \
         patch("subprocess.check_output") as mock_check_output:
        # Mock dirname to return the same path twice for each file operation
        mock_dirname.side_effect = ["installer", "root", "installer", "root"]
        mock_check_output.return_value = mock_git_hash.encode("ascii")
        
        # Run main function
        main()
        
        # Verify version.txt was written with correct content
        expected_version = f"{mock_package_json['version']}+{mock_git_hash}"
        mock_file.assert_any_call("version.txt", "w", encoding="utf-8")
        mock_file().write.assert_called_with(expected_version)

def test_main_write_failure(mock_package_json, mock_git_hash):
    """Test version generation with file write failure."""
    mock_json = json.dumps(mock_package_json)
    mock_file = mock_open(read_data=mock_json)
    mock_file.side_effect = [mock_file.return_value, IOError("Write failed")]
    
    with patch("os.path.dirname") as mock_dirname, \
         patch("os.path.join", lambda *args: args[-1]), \
         patch("builtins.open", mock_file), \
         patch("subprocess.check_output") as mock_check_output:
        # Mock dirname to return the same path twice for each file operation
        mock_dirname.side_effect = ["installer", "root", "installer", "root"]
        mock_check_output.return_value = mock_git_hash.encode("ascii")
        
        # Run main function and expect it to raise IOError
        with pytest.raises(IOError):
            main() 