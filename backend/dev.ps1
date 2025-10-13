# Use Python 3.12 if PYTHON312_HOME is set
if ($env:PYTHON_HOME) {
    $PythonExe = Join-Path $env:PYTHON_HOME "python.exe"
} else {
    # fallback to whatever 'python' is in PATH
    $PythonExe = "python"
}

# Set environment variables
$env:CORS_ALLOW_ORIGIN = "http://localhost:5173;http://localhost:8080"

# Use default port 8080 if PORT is not set
if (-not $env:PORT) {
    $env:PORT = 8080
}

# Run uvicorn using the correct Python
& $PythonExe -m uvicorn open_webui.main:app --port $env:PORT --host 0.0.0.0 --reload