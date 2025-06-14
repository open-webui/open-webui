# Open WebUI Homebrew Formula

This directory contains a fully tested and working Homebrew formula for installing Open WebUI on macOS and Linux systems.

## 📁 Files

- **`open-webui.rb`** - The main Homebrew formula (✅ fully tested and working)
- **`test-homebrew-formula.sh`** - Comprehensive test script for the formula
- **`README.md`** - This documentation file

## 🚀 Installation

To install Open WebUI using this formula:

```bash
# Clone or download this repository
cd path/to/open-webui/homebrew

# Install the formula
brew install --formula ./open-webui.rb

# Verify installation
open-webui --help
```

## 📖 Usage

After installation, you can use Open WebUI with these commands:

```bash
# Show help
open-webui --help

# Start the server (default: http://localhost:8080)
open-webui serve

# Start with custom host/port
open-webui serve --host 0.0.0.0 --port 3000
```

## 🧪 Testing

To test the formula locally:

```bash
# Run comprehensive tests
./test-homebrew-formula.sh
```

The test script will:
1. ✅ Check formula syntax
2. ✅ Test installation
3. ✅ Verify CLI functionality  
4. ✅ Test uninstallation
5. ✅ Test reinstallation

## 🗑️ Uninstallation

To remove Open WebUI:

```bash
brew uninstall open-webui
```

This will cleanly remove Open WebUI and all its dependencies.

## 🔧 Technical Details

- **Version**: 0.6.14
- **License**: MIT
- **Dependencies**: 
  - Python 3.12 (runtime)
  - Node.js 22 (build only)
  - ~98 Python packages (installed automatically)
- **Installation size**: ~2.6GB (80,500 files)

## ✨ Formula Features

- ✅ Automatic dependency management
- ✅ Python virtual environment isolation
- ✅ Clean installation/uninstallation
- ✅ Comprehensive testing
- ✅ Follows Homebrew best practices