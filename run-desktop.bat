@echo off
REM JARVIS desktop app (Electron shell around the local Open WebUI).
REM Starts run.bat in the background if the server is not already up.
setlocal
cd /d "%~dp0"
where npm >nul 2>&1 || ( echo [desktop] Node.js not found. Install Node.js LTS, rerun setup.bat, or just use run.bat. & pause & exit /b 1 )
if not exist "jarvis\electron\node_modules\electron" (
  pushd jarvis\electron
  call npm install --no-audit --no-fund || ( popd & echo [desktop] npm install failed & pause & exit /b 1 )
  popd
)
set "JARVIS_HOME=%~dp0"
pushd jarvis\electron
call npx electron .
popd
endlocal
