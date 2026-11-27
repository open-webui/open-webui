@echo off
REM ============================================================
REM  JARVIS (Open WebUI fork) - start everything locally
REM    run.bat               start + open the browser
REM    run.bat --no-browser  start only (used by run-desktop.bat)
REM ============================================================
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title JARVIS - Open WebUI

if not exist ".venv\Scripts\python.exe" (
  echo [run] Not set up yet. Double-click setup.bat first.
  pause & exit /b 1
)
if not exist "build\index.html" (
  echo [run] Web frontend missing. Run setup.bat again.
  pause & exit /b 1
)

set "PY=%~dp0.venv\Scripts\python.exe"
set "JARVIS_HOME=%~dp0"
if "%JARVIS_HOME:~-1%"=="\" set "JARVIS_HOME=%JARVIS_HOME:~0,-1%"

REM ---- settings from jarvis.env (GITHUB_TOKEN, JARVIS_DEFAULT_MODEL, PORT) ----
if exist "jarvis.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("jarvis.env") do (
    if not "%%B"=="" set "%%A=%%B"
  )
)
if not defined PORT set "PORT=8080"

REM ---- Open WebUI configuration (UI unchanged; only the name + local wiring) ----
set "DATA_DIR=%JARVIS_HOME%\jarvis-data"
set "FRONTEND_BUILD_DIR=%JARVIS_HOME%\build"
set "PYTHONPATH=%JARVIS_HOME%\backend"
set "WEBUI_NAME=JARVIS"
set "OLLAMA_BASE_URL=http://127.0.0.1:11434"
set "ENABLE_OLLAMA_API=true"
if not defined ENABLE_OPENAI_API set "ENABLE_OPENAI_API=false"
if not defined DEFAULT_MODELS set "DEFAULT_MODELS=jarvis"
REM Voice: speech-to-text = local faster-whisper, text-to-speech = JARVIS edge-tts sidecar
if not defined WHISPER_MODEL set "WHISPER_MODEL=base"
set "AUDIO_TTS_ENGINE=openai"
set "AUDIO_TTS_OPENAI_API_BASE_URL=http://127.0.0.1:7342/v1"
set "AUDIO_TTS_OPENAI_API_KEY=local"
set "AUDIO_TTS_MODEL=tts-1"
set "AUDIO_TTS_VOICE=en-GB-RyanNeural"
set "OLLAMA_CONTEXT_LENGTH=8192"
set "PYTHONUTF8=1"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
"%PY%" jarvis\bootstrap\setup_helper.py secret >nul
set /p WEBUI_SECRET_KEY=<"%DATA_DIR%\.webui_secret_key"

REM ---- Ollama ----
"%PY%" -c "import urllib.request as u; u.urlopen('http://127.0.0.1:11434/api/version', timeout=2)" >nul 2>&1 || (
  set "OLLAMA_EXE=ollama"
  if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
  echo [run] starting Ollama ...
  start "Ollama" /min "!OLLAMA_EXE!" serve
)

REM ---- JARVIS voice sidecar (edge-tts, port 7342) ----
"%PY%" -c "import urllib.request as u; u.urlopen('http://127.0.0.1:7342/health', timeout=2)" >nul 2>&1 || (
  start "JARVIS voice" /min "%PY%" jarvis\bootstrap\tts_server.py --port 7342
)

REM ---- register JARVIS tools + model (waits for your admin account on first run) ----
start "JARVIS tools installer" /b "%PY%" jarvis\bootstrap\install_jarvis.py --wait 3600 --log "%DATA_DIR%\jarvis-install.log"

REM ---- open the browser once the server answers ----
if /I not "%~1"=="--no-browser" (
  start "" /b "%PY%" jarvis\bootstrap\open_when_ready.py %PORT%
)

echo.
echo  JARVIS is starting on http://localhost:%PORT%   (close this window to stop it)
echo  First time? Create your account in the browser - it becomes the admin, and the
echo  JARVIS tools + "JARVIS" model appear within a few seconds after that.
echo.
cd backend
"%PY%" -m uvicorn open_webui.main:app --host 127.0.0.1 --port %PORT% --forwarded-allow-ips 127.0.0.1 --workers 1 --ws auto
endlocal
