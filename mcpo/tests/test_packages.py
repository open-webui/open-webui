import sys
import importlib

required_packages = [
    'fastapi',
    'pydantic',
    'uvicorn',
    'python-dotenv',
    'pyodbc',
    'anyio',
    'starlette',
    'mcp'
]

def test_imports():
    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError as e:
            missing.append(package)
            print(f"✗ {package}: {str(e)}")
    
    if missing:
        print("\nMissing packages:")
        print("pip install " + " ".join(missing))
        sys.exit(1)
    else:
        print("\nAll packages installed successfully")

if __name__ == "__main__":
    test_imports()