@echo off
title RAUX Server

REM Set default version and override if provided as parameter
set "version=unknown"
if "%1"=="--version" set "version=%2"

REM Check if Lemonade is installed
if exist "%LOCALAPPDATA%\lemonade_server\lemon_env" (
    echo Starting both RAUX and Lemonade servers...
    REM Start Lemonade in background
    start "Lemonade Server" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_lemonade.ps1"
    REM Start RAUX in current window with version parameter
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$env:RAUX_VERSION='%version%'; & '%~dp0launch_raux.ps1'"
    echo RAUX Server has stopped.
) else (
    echo Starting RAUX Server...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$env:RAUX_VERSION='%version%'; & '%~dp0launch_raux.ps1'"
    echo RAUX Server has stopped.
)

pause