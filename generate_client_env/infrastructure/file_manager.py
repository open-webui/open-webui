"""
File management for infrastructure layer.

Handles all file I/O operations for environment configuration.
"""

import os
from typing import Dict, Optional, Tuple


class FileManagerError(Exception):
    """Raised when file operations fail."""
    pass


class EnvironmentFileManager:
    """Manages environment file operations."""
    
    DEFAULT_ENV_FILES = ['.env', '.env.example']
    
    def __init__(self, working_directory: str = '.'):
        self.working_directory = working_directory
    
    def read_existing_environment(self, env_files: Optional[list] = None) -> Dict[str, str]:
        """
        Read existing environment variables from .env files.
        
        Args:
            env_files: List of env files to check (uses default if None)
            
        Returns:
            Dictionary of environment variables
        """
        if env_files is None:
            env_files = self.DEFAULT_ENV_FILES
        
        existing_vars = {}
        
        for env_file in env_files:
            file_path = os.path.join(self.working_directory, env_file)
            if os.path.exists(file_path):
                try:
                    file_vars = self._parse_env_file(file_path)
                    # Don't override variables from earlier files
                    for key, value in file_vars.items():
                        if key not in existing_vars:
                            existing_vars[key] = value
                    break  # Use first found file
                except Exception as e:
                    # Log warning but continue
                    print(f"Warning: Could not read {env_file}: {e}")
        
        return existing_vars
    
    def write_environment_file(
        self, 
        content: str, 
        filename: str = '.env'
    ) -> Tuple[bool, Optional[str]]:
        """
        Write environment file content to disk.
        
        Args:
            content: Complete file content
            filename: Target filename (default: .env)
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not content or not content.strip():
            return False, "Environment file content cannot be empty"
        
        try:
            file_path = os.path.join(self.working_directory, filename)
            
            # Create backup if file exists
            if os.path.exists(file_path):
                backup_path = f"{file_path}.backup"
                try:
                    with open(file_path, 'r', encoding='utf-8') as src:
                        with open(backup_path, 'w', encoding='utf-8') as dst:
                            dst.write(src.read())
                except Exception:
                    pass  # Backup is best-effort
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, None
            
        except Exception as e:
            return False, f"Failed to write environment file: {str(e)}"
    
    def get_absolute_path(self, filename: str) -> str:
        """
        Get absolute path for a filename in the working directory.
        
        Args:
            filename: Filename
            
        Returns:
            Absolute path
        """
        file_path = os.path.join(self.working_directory, filename)
        return os.path.abspath(file_path)
    
    def file_exists(self, filename: str) -> bool:
        """
        Check if file exists in working directory.
        
        Args:
            filename: Filename to check
            
        Returns:
            True if file exists, False otherwise
        """
        file_path = os.path.join(self.working_directory, filename)
        return os.path.exists(file_path)
    
    def get_file_info(self, filename: str) -> Dict[str, any]:
        """
        Get file information.
        
        Args:
            filename: Filename
            
        Returns:
            Dictionary with file metadata
        """
        file_path = os.path.join(self.working_directory, filename)
        abs_path = os.path.abspath(file_path)
        
        info = {
            'filename': filename,
            'path': file_path,
            'absolute_path': abs_path,
            'exists': os.path.exists(file_path)
        }
        
        if info['exists']:
            try:
                stat = os.stat(file_path)
                info.update({
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'readable': os.access(file_path, os.R_OK),
                    'writable': os.access(file_path, os.W_OK)
                })
            except Exception as e:
                info['error'] = str(e)
        
        return info
    
    def _parse_env_file(self, file_path: str) -> Dict[str, str]:
        """
        Parse environment file and extract variables.
        
        Args:
            file_path: Path to environment file
            
        Returns:
            Dictionary of environment variables
            
        Raises:
            FileManagerError: If file cannot be parsed
        """
        try:
            variables = {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes from value
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        variables[key] = value
                    else:
                        # Invalid line format - skip with warning
                        print(f"Warning: Invalid line format in {file_path}:{line_num}: {line}")
            
            return variables
            
        except Exception as e:
            raise FileManagerError(f"Failed to parse environment file {file_path}: {str(e)}")
    
    def validate_working_directory(self) -> Tuple[bool, Optional[str]]:
        """
        Validate that working directory is accessible.
        
        Returns:
            Tuple of (valid: bool, error_message: Optional[str])
        """
        if not os.path.exists(self.working_directory):
            return False, f"Working directory does not exist: {self.working_directory}"
        
        if not os.path.isdir(self.working_directory):
            return False, f"Working directory is not a directory: {self.working_directory}"
        
        if not os.access(self.working_directory, os.R_OK | os.W_OK):
            return False, f"Working directory is not readable/writable: {self.working_directory}"
        
        return True, None