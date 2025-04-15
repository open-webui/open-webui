@echo off
REM Optionally enable delayed variable expansion if needed (use !VAR! syntax in loops)
setlocal enabledelayedexpansion

REM Check if PORT is defined; if not, set its default value to 8080
if not defined PORT (
    set "PORT=8080"
)

REM Check if uvicorn is available in PATH
where uvicorn >nul 2>&1
if errorlevel 1 (
    echo Uvicorn not found. Please ensure it is installed and available in the PATH.
    exit /b 1
)

REM Start uvicorn with the specified parameters:
REM --port %PORT%       : Use the defined port
REM --host 0.0.0.0      : Bind to all network interfaces
REM --forwarded-allow-ips "^*" : Prevent CMD wildcard expansion (alternatively, you can use "*" with quotes)
REM --reload            : Enable auto-reload for development
uvicorn open_webui.main:app --port %PORT% --host 0.0.0.0 --forwarded-allow-ips "^*" --reload

REM End the local environment changes
endlocal
