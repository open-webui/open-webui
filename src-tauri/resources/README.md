# Bundled Resources

This directory contains resources that are bundled with the Tauri application.

## Python Runtime

The `python/` directory contains platform-specific Python 3.12 runtimes:

- `python/macos/` - Python 3.12 for macOS (arm64 and x86_64)
- `python/windows/` - Python 3.12 embeddable for Windows
- `python/linux/` - Python 3.12 for Linux

### Setup Instructions

To prepare the bundled Python for building:

1. Run the setup script: `npm run python:setup`
2. This will download the appropriate Python 3.12 standalone build for your platform
3. The Python runtime will be extracted to the platform-specific directory

### Download Sources

**macOS**: 
- https://github.com/indygreg/python-build-standalone/releases
- Use the `cpython-3.12.*-aarch64-apple-darwin-install_only.tar.gz` for Apple Silicon
- Use the `cpython-3.12.*-x86_64-apple-darwin-install_only.tar.gz` for Intel

**Windows**:
- https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip

**Linux**:
- https://github.com/indygreg/python-build-standalone/releases
- Use the `cpython-3.12.*-x86_64-unknown-linux-gnu-install_only.tar.gz`

### Note

The Python runtime files are NOT included in the repository due to size.
They must be downloaded during the build process using the setup script.
