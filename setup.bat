@echo off
REM ============================================================
REM  JARVIS (Open WebUI fork) - one-time setup for Windows
REM  Double-click this once. Then double-click run.bat (browser)
REM  or run-desktop.bat (Electron desktop app).
REM ============================================================
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title JARVIS setup

echo.
echo  === JARVIS setup (Open WebUI %~dp0) ===
echo.

REM ---- 1. Python 3.12 / 3.11 (Open WebUI needs 3.11 or 3.12) ----
set "PYEXE="
for %%V in (3.12 3.11) do (
  if not defined PYEXE (
    py -%%V -c "import sys" >nul 2>&1 && set "PYEXE=py -%%V"
  )
)
if not defined PYEXE (
  echo [setup] Python 3.12 not found - installing it with winget...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  py -3.12 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.12"
)
if not defined PYEXE (
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYEXE (
  echo [setup] ERROR: could not find or install Python 3.12. Install it from https://www.python.org/downloads/ and rerun.
  pause & exit /b 1
)
echo [setup] using Python: !PYEXE!

REM ---- 2. Git (for barehands + coding tools) ----
where git >nul 2>&1 || (
  echo [setup] Git not found - installing Git for Windows with winget...
  winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
)

REM ---- 3. Ollama (local models) ----
set "HAVE_OLLAMA="
where ollama >nul 2>&1 && set "HAVE_OLLAMA=1"
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "HAVE_OLLAMA=1"
if not defined HAVE_OLLAMA (
  echo [setup] Ollama not found - installing it with winget...
  winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
)
REM Bigger default context so tool definitions fit (same as the JARVIS app).
setx OLLAMA_CONTEXT_LENGTH 8192 >nul 2>&1

REM ---- 4. Python virtual environment + Open WebUI backend deps ----
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" || (
    echo [setup] existing .venv uses an unsupported Python - recreating it
    rmdir /s /q .venv
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo [setup] creating .venv ...
  !PYEXE! -m venv .venv || ( echo [setup] ERROR: venv creation failed & pause & exit /b 1 )
)
echo [setup] installing Open WebUI backend requirements (first run downloads a few GB, be patient) ...
.venv\Scripts\python.exe -m pip install --upgrade pip wheel >nul
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || ( echo [setup] ERROR: pip install failed - see above & pause & exit /b 1 )
.venv\Scripts\python.exe -m pip install edge-tts || echo [setup] warning: edge-tts not installed, JARVIS voice falls back to the browser voice

REM ---- 5. Frontend, barehands, model, jarvis.env ----
set "FRONT_ARG="
if /I "%~1"=="/buildfrontend" set "FRONT_ARG=--from-source"
.venv\Scripts\python.exe jarvis\bootstrap\setup_helper.py envfile
.venv\Scripts\python.exe jarvis\bootstrap\setup_helper.py secret
.venv\Scripts\python.exe jarvis\bootstrap\setup_helper.py frontend !FRONT_ARG! || (
  echo [setup] ERROR: could not get the web frontend. Try: setup.bat /buildfrontend  ^(needs Node.js 22^)
  pause & exit /b 1
)
.venv\Scripts\python.exe jarvis\bootstrap\setup_helper.py barehands
.venv\Scripts\python.exe jarvis\bootstrap\setup_helper.py model

REM ---- 6. Electron desktop shell (optional, needs Node.js) ----
set "HAVE_NPM="
where npm >nul 2>&1 && set "HAVE_NPM=1"
if defined HAVE_NPM (
  echo [setup] installing the Electron desktop shell ...
  pushd jarvis\electron
  call npm install --no-audit --no-fund
  if errorlevel 1 echo [setup] warning: Electron install failed - run.bat in the browser still works.
  popd
) else (
  echo [setup] Node.js not found - skipping the desktop app. Install Node.js LTS to use run-desktop.bat.
)

echo.
.venv\Scripts\python.exe jarvis\bootstrap\setup_helper.py check
echo.
echo  === Setup finished. Double-click run.bat (browser) or run-desktop.bat (desktop app). ===
echo.
pause
endlocal
