@echo off
title RAUX Server

REM Check if Lemonade is installed
if exist "%LOCALAPPDATA%\lemonade_server\lemon_env" (
    echo Starting both RAUX and Lemonade servers...
    REM Start Lemonade in background
    start "Lemonade Server" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_lemonade.ps1"
    REM Start RAUX in current window
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_raux.ps1"
    echo RAUX Server has stopped.
) else (
    echo Starting RAUX Server...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_raux.ps1"
    echo RAUX Server has stopped.
)

pause 