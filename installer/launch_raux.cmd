@echo off
title RAUX Server

REM Set default version and mode, override if provided as parameters
set "version=unknown"
set "mode=GENERIC"

REM Parse command line parameters
:parse
if "%1"=="--version" (
    set "version=%2"
    shift
    shift
    goto parse
)
if "%1"=="--mode" (
    set "mode=%2"
    shift
    shift
    goto parse
)

REM Check if Lemonade is installed
if exist "%LOCALAPPDATA%\lemonade_server\lemon_env" (
    echo Starting both RAUX and Lemonade servers...
    REM Start Lemonade in background
    start "Lemonade Server" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_lemonade.ps1"
    REM Start RAUX in current window with version and mode parameters
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$env:RAUX_VERSION='%version%'; $env:RAUX_MODE='%mode%'; & '%~dp0launch_raux.ps1'"
    echo RAUX Server has stopped.
) else (
    echo Starting RAUX Server...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$env:RAUX_VERSION='%version%'; $env:RAUX_MODE='%mode%'; & '%~dp0launch_raux.ps1'"
    echo RAUX Server has stopped.
)

pause